"""Assemble registered ImageGen plates into a sparse, four-appearance Bay atlas."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, maximum_filter, map_coordinates, minimum_filter
from shapely.geometry import LineString, Point
from shapely.ops import substring

from atlas_geometry import CE, ORIGIN_UTM, SE, PixelFrame, camera_point, pack_depth
from bay_illustration_guides import (AREA_SCALE, ART, FRAME, REGIONAL_SCALE, WORK,
                                      boundaries, placements, regional)
from bay_overview import AIRPORTS, DEPTH, point
from corridor_inputs import ROOT, sha
from illustrated_weather import pavement_material, wet_surfaces
from offshore_water import harmonize, water_weight
from regional_tiles import region_for_tile

OUT = ROOT / "public/map/v9-art/bay"
RETAINED = ROOT / "public/map/v8-art/bay/scene.json"
APPEARANCES = ("scene", "night", "rain-day", "rain-night")
TILE = 512
FACTOR = round(AREA_SCALE / REGIONAL_SCALE)
WORLD = PixelFrame("full-bay-detail", FRAME.x * FACTOR, FRAME.y * FACTOR,
                   FRAME.width * FACTOR, FRAME.height * FACTOR)
MAX_LEVEL = math.ceil(math.log2(WORLD.width))
REGIONAL_LEVEL = MAX_LEVEL - int(math.log2(FACTOR))


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
                    encoding="utf-8", newline="\n")


def paint_path(identifier, appearance="scene"):
    suffix = "" if appearance == "scene" else f"-{appearance}"
    return ART / "plates" / f"{identifier}{suffix}.png"


def read_art(identifier, appearance="scene"):
    path = paint_path(identifier, appearance)
    with Image.open(path) as image:
        if image.size != (1536, 1024):
            raise ValueError(f"Wrong ImageGen frame dimensions: {path}: {image.size}")
        return image.convert("RGB")


def ramp(distance, width):
    t = np.clip(distance / width, 0, 1).astype("float32")
    return t * t * (3 - 2 * t)


def regional_day(rows):
    rgb = np.zeros((FRAME.height, FRAME.width, 3), dtype="float32")
    weight = np.zeros(rgb.shape[:2], dtype="float32")
    for row in rows:
        x, y, w, h = row["frame"]
        a = np.ones(w, dtype="float32")
        b = np.ones(h, dtype="float32")
        if x > 0:
            a *= ramp(np.arange(w), 255)
        if x + w < FRAME.width:
            a *= ramp(np.arange(w)[::-1], 255)
        if y > 0:
            b *= ramp(np.arange(h), 150)
        if y + h < FRAME.height:
            b *= ramp(np.arange(h)[::-1], 150)
        alpha = b[:, None] * a[None, :]
        rgb[y:y+h, x:x+w] += np.asarray(read_art(row["id"])) * alpha[..., None]
        weight[y:y+h, x:x+w] += alpha
    if np.any(weight <= 0):
        raise ValueError("The selected regional artwork leaves a gap")
    return Image.fromarray(np.rint(rgb / weight[..., None]).clip(0, 255).astype("uint8"))


def appearance_image(day, land, urban, appearance, *, origin=(0, 0), local=False):
    if appearance == "scene":
        return day
    wet = appearance.startswith("rain")
    night = appearance.endswith("night")
    rgb = np.asarray(day)
    painted_water = (rgb[..., 2] > rgb[..., 1] * 1.10) & (rgb[..., 0] < rgb[..., 1] * .69)
    water = ~land & painted_water
    green = (rgb[..., 1] > rgb[..., 0] * 1.08) & land
    gray = np.asarray(day.convert("L"), dtype="float32")
    hard = urban & ~green
    source = day
    if wet:
        material = pavement_material(day, hard, np.zeros(land.shape, dtype=bool), water)
        source = wet_surfaces(day, material)
    pixels = np.array(source, dtype="float32")
    if not night:
        pixels[water] = rgb[water] * [.74, .84, .86] + [6, 11, 13]
        return Image.fromarray(np.rint(pixels).clip(0, 255).astype("uint8"))
    pixels *= [.31, .38, .51] if wet else [.26, .35, .48]
    pixels += [5, 7, 11]
    pixels[water] = rgb[water] * [.31, .40, .45] + [5, 7, 10]
    # Sample small light sources from painted urban texture on a fixed image grid.
    x = np.arange(day.width, dtype="uint32")[None, :] + origin[0]
    y = np.arange(day.height, dtype="uint32")[:, None] + origin[1]
    seed = (x * np.uint32(374761393)) ^ (y * np.uint32(668265263))
    seed = (seed ^ (seed >> 13)) * np.uint32(1274126177)
    edge = maximum_filter(gray, size=3) - minimum_filter(gray, size=3)
    window = (hard & ~water & (edge > 17) & (gray > 30) & (gray < 165)
              & (seed % (34 if local else 13) == 0))
    energy = window.astype("float32") * (.55 + (seed % 36).astype("float32") / 100)
    glow = gaussian_filter(energy, 1.4 if local else .86)
    pixels += energy[..., None] * [163, 109, 50] + glow[..., None] * [151, 91, 38]
    if wet:
        reflection = gaussian_filter(energy, (3.6, .7)) * (hard | water)
        pixels += reflection[..., None] * [143, 87, 44]
    return Image.fromarray(np.rint(pixels).clip(0, 255).astype("uint8"))


def full_surface(image, weight, appearance):
    rgb = np.array(image)
    for y in range(0, image.height, 256):
        rgb[y:y+256] = harmonize(rgb[y:y+256], weight[y:y+256],
                                 "day" if appearance == "scene" else appearance, (0, y))
    return Image.fromarray(rgb)


def tile_positions(bounds, divisor):
    x0, y0, x1, y1 = bounds
    span = TILE * divisor
    return [(c, r) for r in range(y0 // span, math.ceil(y1 / span))
            for c in range(x0 // span, math.ceil(x1 / span))]


def tile_box(level, column, row):
    divisor = 2 ** (MAX_LEVEL - level)
    width, height = math.ceil(WORLD.width / divisor), math.ceil(WORLD.height / divisor)
    return (max(0, column*TILE-1), max(0, row*TILE-1),
            min(width, (column+1)*TILE+1), min(height, (row+1)*TILE+1))


def tile_layout(rows, details):
    layout = {
        "tileSize": TILE, "overlap": 1, "maxLevel": MAX_LEVEL, "sharedMaxLevel": 11,
        "fallback": "context", "regions": [],
        "detail": {"baseLevel": REGIONAL_LEVEL, "tiles": {}},
    }
    for row in rows:
        x, y, w, h = row["frame"]
        layout["regions"].append({"id": row["id"], "bounds": [
            x * FACTOR, y * FACTOR, (x+w) * FACTOR, (y+h) * FACTOR]})
    tiles = {}
    for level in range(REGIONAL_LEVEL + 1, MAX_LEVEL + 1):
        divisor = 2 ** (MAX_LEVEL - level)
        for detail in details:
            x, y, w, h = detail["frame"]
            for col, row in tile_positions((x, y, x+w, y+h), divisor):
                tiles.setdefault((level, col, row), []).append(detail)
    layout["detail"]["tiles"] = {
        f"{level}/{col}_{row}": details[0]["id"] for (level, col, row), details in tiles.items()
    }
    return layout, tiles


def render_detail(row, appearance, land, urban):
    x, y, w, h = row["frame"]
    if paint_path(row["id"], appearance).is_file():
        return read_art(row["id"], appearance)
    box = (x/FACTOR, y/FACTOR, (x+w)/FACTOR, (y+h)/FACTOR)
    mask = lambda source: np.asarray(source.resize((w, h), Image.Resampling.NEAREST, box=box)) > 0
    return appearance_image(read_art(row["id"]), mask(land), mask(urban), appearance,
                            origin=(x, y), local=True)


def feather(image):
    w, h = image.size
    x, y = np.arange(w), np.arange(h)
    weight = ramp(np.minimum(np.minimum(x, w-1-x)[None, :],
                             np.minimum(y, h-1-y)[:, None]), 96)
    return Image.fromarray(np.rint(weight * 255).astype("uint8"))


def detail_tile(base, level, column, row, patches):
    left, top, right, bottom = tile_box(level, column, row)
    divisor = 2 ** (MAX_LEVEL - level)
    x0, y0, x1, y1 = [v * divisor for v in (left, top, right, bottom)]
    size = (right-left, bottom-top)
    # Rasterize this small native tile in the same coordinates as the shared base.
    background = base.transform((x1-x0, y1-y0), Image.Transform.AFFINE,
                                (1/FACTOR, 0, x0/FACTOR, 0, 1/FACTOR, y0/FACTOR),
                                Image.Resampling.BICUBIC)
    for detail, image, alpha in patches:
        x, y, w, h = detail["frame"]
        x2, y2, x3, y3 = max(x, x0), max(y, y0), min(x+w, x1), min(y+h, y1)
        if x2 < x3 and y2 < y3:
            box = (x2-x, y2-y, x3-x, y3-y)
            background.paste(image.crop(box), (x2-x0, y2-y0), alpha.crop(box))
    return background if divisor == 1 else background.resize(size, Image.Resampling.LANCZOS)


def package_appearance(out, appearance, base, layout, tiles, details, land, urban):
    patches = {}
    for detail in details:
        image = render_detail(detail, appearance, land, urban)
        patches[detail["id"]] = (detail, image, feather(image))
    files = []

    def write(level, col, row, region, tile):
        path = out / f"regions/{region}/{appearance}_files/{level}/{col}_{row}.webp"
        path.parent.mkdir(parents=True, exist_ok=True)
        tile.save(path, quality=88 if level > REGIONAL_LEVEL else 86, method=4)
        return path

    def write_detail(item):
        (level, col, row), visible = item
        tile = detail_tile(base, level, col, row, [patches[p["id"]] for p in visible])
        return write(level, col, row, visible[0]["id"], tile)

    with ThreadPoolExecutor(max_workers=6) as pool:
        for level in range(REGIONAL_LEVEL + 1):
            divisor = 2 ** (REGIONAL_LEVEL - level)
            w, h = math.ceil(FRAME.width / divisor), math.ceil(FRAME.height / divisor)
            image = base if divisor == 1 else base.resize((w, h), Image.Resampling.LANCZOS)

            def write_base(pair):
                col, row = pair
                region = region_for_tile(layout, WORLD.width, WORLD.height, level, col, row)
                return write(level, col, row, region, image.crop(tile_box(level, col, row)))

            files.extend(pool.map(write_base, tile_positions((0, 0, w, h), 1)))
        files.extend(pool.map(write_detail, tiles.items()))
    print(f"{appearance}: {len(files)} regional and visible-detail tiles", flush=True)
    return files


def pack_mask(out, land, urban, elevation):
    # The samples lie at pixel centres, with the same linear depth correction as City.
    terrain = Image.fromarray(elevation).resize((2560, 1792), Image.Resampling.BILINEAR)
    height = np.asarray(terrain)
    y = ((np.arange(height.shape[0])[:, None] + .5) * 2 + FRAME.y) / REGIONAL_SCALE
    q = (y + height * CE) / SE
    flags = ((~land).astype("uint8") * 2 + urban.astype("uint8"))
    flags = np.asarray(Image.fromarray(flags).resize(terrain.size, Image.Resampling.NEAREST))
    packed = pack_depth((q * CE + height * SE).astype("float32"), flags, DEPTH)
    Image.fromarray(packed).save(out / "masks.png", compress_level=5)
    return list(terrain.size)


def make_routes(retained, roads, land, elevation, details):
    def road_height(e, n):
        x, y, _ = camera_point((e, n, 0), REGIONAL_SCALE)
        return float(map_coordinates(elevation, [[y-FRAME.y-.5], [x-FRAME.x-.5]],
                                     order=1, mode="nearest")[0]) + 6

    routes = list(retained["routes"])
    used = set()
    colors = ["#e5b863", "#d9ddc8", "#6a9ea9", "#aa664a"]
    for row in details:
        name = row["id"].removeprefix("detail-")
        centre = Point(*point(*row["lonLat"])[:2])
        nearby = sorted(((line.distance(centre), road or "", line) for road, _, line in roads
                         if line.length > 1800 and line.distance(centre) < 3400),
                        key=lambda item: item[:2])
        for _, _, road in nearby[:4]:
            middle = road.project(centre)
            segment = substring(road, max(0, middle-1600), min(road.length, middle+1600)).simplify(9)
            if segment.length < 1500 or segment.wkb in used:
                continue
            used.add(segment.wkb)
            samples = [segment.interpolate(i / math.ceil(segment.length / 100), normalized=True)
                       for i in range(math.ceil(segment.length / 100)+1)]
            points = [[p.x, p.y, road_height(p.x, p.y)] for p in samples]
            # The two directions share the registered road and advance independently.
            for lane in range(3):
                routes.append({"id": f"regional-{name}-{len(used)}-{lane}", "kind": "car",
                               "points": points+points[-2::-1], "speed": 23+lane*3,
                               "phase": lane*36+len(used)*11, "color": colors[(len(used)+lane)%4]})
    for identifier, a, b, c in [
        ("benicia", (-122.1375, 38.0555), (-122.129, 38.036), (-122.118, 38.021)),
        ("antioch", (-121.7543, 38.0083), (-121.7518, 38.0194), (-121.7559, 38.0364)),
    ]:
        points = [point(*coord, 31) for coord in (a, b, c)]
        routes.append({"id": f"bay-car-{identifier}", "kind": "car", "points": points+points[-2::-1],
                       "speed": 27, "phase": 49, "color": "#d9ddc8"})
    for identifier, kind, coordinates in [
        ("san-pablo", "ferry", [(-122.414, 38.024), (-122.360, 38.045), (-122.296, 38.065)]),
        ("south-bay", "ferry", [(-122.221, 37.610), (-122.197, 37.570), (-122.161, 37.545)]),
        ("pacific", "cargo", [(-123.090, 37.725), (-123.045, 37.667), (-122.950, 37.600)]),
        ("suisun", "ferry", [(-122.095, 38.065), (-122.067, 38.074), (-122.035, 38.074),
                             (-122.010, 38.069), (-121.974, 38.063)]),
    ]:
        points = [point(*coord, .7) for coord in coordinates]
        clearance = LineString([p[:2] for p in points]).distance(land)
        radius = math.hypot(32.5, 7.5) if kind == "cargo" else math.hypot(15.5, 4.5)
        if clearance < radius * 38:
            print(f"{identifier}: {clearance:.0f} m clearance, route withheld", flush=True)
            continue
        routes.append({"id": f"bay-vessel-{identifier}", "kind": kind,
                       "points": points+points[-2::-1], "speed": 15 if kind == "ferry" else 10,
                       "phase": 340 + len(routes)*11, "color": "#ece9d9"})
    for i, (name, lon, lat) in enumerate(AIRPORTS):
        start = point(lon + .097, lat - .075, 1700)
        approach = point(lon + .037, lat - .035, 850)
        end = point(lon, lat, 135)
        routes.append({"id": f"bay-flight-{name.lower()}", "kind": "plane",
                       "points": [start, approach, end], "speed": 144, "phase": 18 + i*19,
                       "color": "#edece1"})
    return routes


def package(out, *, regional_only=False):
    if not (WORK / "layout.json").is_file():
        regional()
    layout_source = json.loads((WORK / "layout.json").read_text(encoding="utf-8"))
    rows = [row for row in placements() if row["kind"] == "regional"]
    details = [] if regional_only else [row for row in placements() if row["kind"] == "detail"]
    out.mkdir(parents=True, exist_ok=True)
    land_geometry, _, roads, _ = boundaries()
    with Image.open(WORK / "land.png") as source:
        land = source.copy()
    with Image.open(WORK / "urban.png") as source:
        urban = source.copy()
    land_bool, urban_bool = np.asarray(land) > 0, np.asarray(urban) > 0
    elevation = np.load(WORK / "elevation.npy")
    day = regional_day(rows)
    day.save(WORK / "assembled-day.webp", quality=93, method=4)
    protected = land.copy()
    bridge_ink = ImageDraw.Draw(protected)
    for _, _, line in roads:
        pixels = [camera_point((*xy, 0), REGIONAL_SCALE) for xy in line.coords]
        bridge_ink.line([(x-FRAME.x, y-FRAME.y) for x, y, _ in pixels], fill=255, width=5)
    weight = water_weight(np.asarray(protected) > 0, near=11, far=58, pixels_per_sample=1)
    layout, tiles = tile_layout(rows, details)
    files = []
    for appearance in APPEARANCES:
        base = full_surface(appearance_image(day, land_bool, urban_bool, appearance), weight, appearance)
        files.extend(package_appearance(out, appearance, base, layout, tiles, details, land, urban))
    mask_size = pack_mask(out, land_bool, urban_bool, elevation)
    retained = json.loads(RETAINED.read_text(encoding="utf-8"))
    routes = make_routes(retained, roads, land_geometry, elevation, details)
    landmarks = [dict(row, viewHeight=4650) for row in retained["landmarks"]]
    for row in details:
        landmarks.append({"id": row["id"].removeprefix("detail-"), "name": row["name"],
                          "p": point(*row["lonLat"]), "viewHeight": 852, "viewWidth": 1270,
                          "detail": True})
    # Napa and Petaluma have both regional labels and closer views with the same id.
    landmarks = list({item["id"]: item for item in landmarks}.values())
    files.append(out / "masks.png")
    metadata = [{"path": path.relative_to(out).as_posix(), "sha256": sha(path),
                 "bytes": path.stat().st_size} for path in sorted(files)]
    revision = hashlib.sha256("".join(file["sha256"] for file in metadata).encode()).hexdigest()[:12]
    scene = {
        "release": "full-bay-v9", "kind": "bay", "assetRoot": "map/v9-art/bay/",
        "width": WORLD.width, "height": WORLD.height, "appearanceRevision": revision,
        "projection": WORLD.projection(AREA_SCALE), "maskSize": mask_size,
        "maskBundle": "map/v9-art/bay/masks.png", "depthEncoding": DEPTH, "clipDepth": 262144,
        "transportScale": 38, "adaptiveTransport": True, "extent": retained["extent"],
        "sourceBuildings": 0, "routes": routes, "landmarks": landmarks,
        "lamps": [], "windows": [], "tileLayout": layout,
        "originUTM": list(ORIGIN_UTM), "crs": "EPSG:32610",
    }
    dump(out / "scene.json", scene)
    source_rows = [dict(row, sha256=sha(paint_path(row["id"]))) for row in [*rows, *details]]
    weather_art = [{"id": row["id"], "appearance": appearance,
                    "sha256": sha(paint_path(row["id"], appearance))}
                   for row in details for appearance in APPEARANCES[1:]
                   if paint_path(row["id"], appearance).is_file()]
    counts = Counter(route["kind"] for route in routes)
    dump(out / "manifest.json", {
        "release": scene["release"], "tileCount": len(files)-1, "bytes": sum(f["bytes"] for f in metadata),
        "revision": revision, "projection": scene["projection"], "artwork": source_rows,
        "weatherArtwork": weather_art, "sources": layout_source["inputs"],
        "aerialGuides": json.loads((ART / "aerial-guide-sha256.json").read_text(encoding="utf-8")),
        "routes": dict(counts), "files": metadata,
    })
    print(f"Full Bay: {len(rows)} regional plates, {len(details)} close-ups, {len(landmarks)} places, "
          f"{dict(counts)}, {sum(f['bytes'] for f in metadata):,} bytes", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--regional-only", action="store_true", help="Preview the continuous artwork while close-ups render")
    args = parser.parse_args()
    package(args.out, regional_only=args.regional_only)


if __name__ == "__main__":
    main()
