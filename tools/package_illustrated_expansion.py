"""Assemble the ImageGen atlas from the accepted v0.5 tiles and registered illustrations."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import distance_transform_edt
from shapely.geometry import box
from shapely.ops import unary_union

import expanded_tiles as deep_zoom
from atlas_geometry import ORIGIN_UTM, PixelFrame, camera_point, ground_point
from corridor_inputs import ROOT, TO_GEO, sha
from expanded_geometry import BLOCK, HALO, MASK_DIVISOR, WORLD
from expanded_render import block_frame, blocks, padded
from golden_gate_lighting import lamps_for, tone
from illustrated_guides import (APPROVED, SELECTED, WATER_CORRECTIONS, WORK, crop_water,
                                read_packed_mask, reference_mask, reference_scene)
from illustrated_layout import ART, DETAIL_FOCUS, LAYOUT, bridge_area, map_geometry, rectangle
from illustrated_weather import (OVERCAST_EXPOSURE, OVERVIEW_DIMMING, blend_night_edge,
                                 legacy_lighting, legacy_night_edge_mask, overcast_overview_mask,
                                 painted_windows, pavement_material, puddle_reflections, wet_surfaces)
from package_corridor import APPEARANCES, save_json, write_manifest

SOURCE_MAP = ROOT / "public/map"
PUBLISHED = ART / "plates"
OUTPUT = WORK / "public/map"
COMPOSED = WORK / "blocks"
SOUTH_FRAME = PixelFrame("southern-context", -27648, -3072, 27648, 18432)
PAINTED_WEATHER = {"night": "-dry-night", "rain-day": "-rain-day", "rain-night": "-night"}
LEGACY = None
PACKED = None
WATER = None
SEA = None
SHORE = None
LAMPS = None
LAMP_PIXELS = None
BRIDGES = None
ROWS = None
PACK_SIGNATURE = None
SOUTH = None
SOUTH_ALPHA = None


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def plate(row, appearance="scene"):
    key = row["id"] + PAINTED_WEATHER.get(appearance, "")
    for folder in (PUBLISHED, SELECTED):
        path = folder / f"{key}.png"
        if path.is_file():
            return path
    return None


def distance_to_edge(target, area):
    left, top, right, bottom = deep_zoom.local_box(target, area)
    x = np.arange(left, right, dtype="float32") + .5
    y = np.arange(top, bottom, dtype="float32") + .5
    return np.minimum(np.minimum(x, target.width - x)[None, :],
                      np.minimum(y, target.height - y)[:, None])


def field(image, frame, divisor=1):
    rgb = np.asarray(image)
    h, w = rgb.shape[:2]
    x = np.mod(frame.x + np.arange(frame.width // divisor) * divisor, w * 2)
    y = np.mod(frame.y + np.arange(frame.height // divisor) * divisor, h * 2)
    x = np.minimum(x, w * 2 - 1 - x)
    y = np.minimum(y, h * 2 - 1 - y)
    return Image.fromarray(rgb[np.ix_(y, x)])


def land_alpha(rgb):
    red, green, blue = np.asarray(rgb, dtype="int16").transpose(2, 0, 1)
    water_color = np.minimum(green - red - 7, blue - green - 4)
    return np.rint(255 * np.clip((11 - water_color) / 14, 0, 1)).astype("uint8")


def south_appearances(day):
    colors = np.asarray(day, dtype="float32")
    wet = colors * [.73, .78, .86] + [6, 8, 10]
    night = np.array([.24, .33, .46])
    convert = lambda value: Image.fromarray(np.clip(value, 0, 255).astype("uint8"))
    return {"scene": day, "rain-day": convert(wet * OVERCAST_EXPOSURE),
            "night": convert(colors * night + [5, 6, 8]),
            "rain-night": convert(wet * night + [5, 6, 8])}


def background(frame, appearance, divisor=1):
    image = field(SEA[appearance], frame, divisor)
    area = deep_zoom.intersection(frame, SOUTH_FRAME)
    if area is None:
        return image
    crop = deep_zoom.local_box(SOUTH_FRAME, area)
    sx = SOUTH["scene"].width / SOUTH_FRAME.width
    sy = SOUTH["scene"].height / SOUTH_FRAME.height
    source = (crop[0] * sx, crop[1] * sy, crop[2] * sx, crop[3] * sy)
    size = ((area[2] - area[0]) // divisor, (area[3] - area[1]) // divisor)
    art = SOUTH[appearance].resize(size, Image.Resampling.BILINEAR, box=source)
    alpha = SOUTH_ALPHA.resize(size, Image.Resampling.BILINEAR, box=source)
    image.paste(art, ((area[0] - frame.x) // divisor, (area[1] - frame.y) // divisor), alpha)
    return image


def source_mask(flags, frame):
    return crop_water(Image.fromarray(((PACKED[:, :, 2] & flags) > 0).astype("uint8") * 255), frame, outside=0)


def sea_samples(legacy):
    sample = (-1550, -8400, -526, -7376)
    sx = legacy.water.width / legacy.frame.width
    sy = legacy.water.height / legacy.frame.height
    a = deep_zoom.local_box(legacy.frame, sample)
    water = legacy.water.crop((round(a[0] * sx), round(a[1] * sy), round(a[2] * sx), round(a[3] * sy)))
    if water.getextrema() != (255, 255):
        raise ValueError("The v0.5 sea sample contains land")
    return {appearance: legacy.crop(appearance, sample) for appearance in APPEARANCES}


def initialize(rows, output, lamps, offshore_bridge, signature):
    global COMPOSED, LEGACY, PACKED, WATER, SEA, SHORE, ROWS, BRIDGES, LAMPS, LAMP_PIXELS, PACK_SIGNATURE
    global SOUTH, SOUTH_ALPHA
    COMPOSED = WORK / ("blocks-" + hashlib.sha256(str(Path(output).resolve()).encode()).hexdigest()[:12])
    deep_zoom.SHARED = Path(output) / "illustrated-bay"
    LEGACY = deep_zoom.RetainedArtwork()
    PACKED = read_packed_mask()
    WATER = Image.fromarray(((PACKED[:, :, 2] & 2) > 0).astype("uint8") * 255)
    SEA = sea_samples(LEGACY)
    with Image.open(PUBLISHED / "southern-context.png") as source:
        south = source.convert("RGB")
    SOUTH = south_appearances(south)
    alpha = land_alpha(south)
    top = np.minimum(1, np.arange(alpha.shape[0]) / 12)
    right = np.minimum(1, np.arange(alpha.shape[1] - 1, -1, -1) / 12)
    SOUTH_ALPHA = Image.fromarray((alpha * top[:, None] * right[None, :]).astype("uint8"))
    SHORE = Image.fromarray(np.clip((156 - distance_transform_edt(np.asarray(WATER) > 128) * MASK_DIVISOR)
                                     / 120 * 255, 0, 255).astype("uint8"))
    ROWS = rows
    BRIDGES = offshore_bridge
    LAMPS = lamps
    LAMP_PIXELS = np.asarray([camera_point(p)[:2] for p in lamps])
    PACK_SIGNATURE = signature


def legacy_mask(frame, fresh, version):
    overlap = deep_zoom.intersection(frame, LEGACY.frame)
    if overlap is None:
        return None, None
    alpha = Image.new("L", (overlap[2] - overlap[0], overlap[3] - overlap[1]))
    legacy_frame = PixelFrame("overlap", *overlap[:2], alpha.width, alpha.height)
    draw = ImageDraw.Draw(alpha)
    for old in APPROVED:
        area = deep_zoom.intersection(frame, old)
        if area is not None:
            x0, y0, x1, y1 = deep_zoom.local_box(legacy_frame, area)
            draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    mask_box = deep_zoom.local_box(LEGACY.frame, overlap)
    sx, sy = LEGACY.water.width / LEGACY.frame.width, LEGACY.water.height / LEGACY.frame.height
    water = LEGACY.water.resize(alpha.size, Image.Resampling.NEAREST,
                                box=(mask_box[0] * sx, mask_box[1] * sy, mask_box[2] * sx, mask_box[3] * sy))
    edge = np.pad(np.asarray(alpha) > 0, 1, constant_values=False)
    distance = distance_transform_edt(edge)[1:-1, 1:-1]
    left, top, right, bottom = deep_zoom.local_box(frame, overlap)
    replacement = fresh[top:bottom, left:right] > .8
    weight = np.where(replacement, np.clip((distance - 110) / 30, 0, 1),
                      np.clip(distance / 44, 0, 1))
    for row, target, area in rows_in(legacy_frame, version, "detail"):
        if row.get("replaceLegacy"):
            x0, y0, x1, y1 = deep_zoom.local_box(legacy_frame, area)
            fade = np.clip((distance_to_edge(target, area) - 40) / 144, 0, 1)
            weight[y0:y1, x0:x1] *= 1 - fade
    shore = np.clip((180 - distance_transform_edt(np.asarray(water) > 128)) / 144, 0, 1)
    return overlap, Image.fromarray(np.rint(255 * weight * shore).astype("uint8"))


def rows_in(frame, version, kind):
    for row in ROWS:
        if row["stage"] > version or row["kind"] != kind:
            continue
        target = PixelFrame(row["id"], *row["frame"])
        overlap = deep_zoom.intersection(frame, target)
        if overlap is not None:
            yield row, target, overlap


def bridge_keep(frame):
    region = BRIDGES.intersection(box(frame.x, frame.y, frame.right, frame.bottom))
    result = Image.new("L", (frame.width, frame.height))
    draw = ImageDraw.Draw(result)
    for part in getattr(region, "geoms", (region,)):
        if part.geom_type == "Polygon" and not part.is_empty:
            draw.polygon([(x - frame.x, y - frame.y) for x, y in part.exterior.coords], fill=255)
    return np.asarray(result)


def image_crop(path, target, area):
    with Image.open(path) as source:
        sx, sy = source.width / target.width, source.height / target.height
        x0, y0, x1, y1 = deep_zoom.local_box(target, area)
        return source.convert("RGB").resize((x1 - x0, y1 - y0), Image.Resampling.LANCZOS,
                                            box=(x0 * sx, y0 * sy, x1 * sx, y1 * sy))


def land_art(frame, version):
    artwork = field(SEA["scene"], frame)
    width, height = artwork.size
    colors = np.zeros((height, width, 3), dtype="float32")
    weights = np.zeros((height, width), dtype="float32")
    coverage = np.zeros((height, width), dtype="float32")
    for row, target, area in rows_in(frame, version, "area"):
        path = plate(row)
        if path is None:
            continue
        left, top, right, bottom = deep_zoom.local_box(frame, area)
        window = np.s_[top:bottom, left:right]
        distance = distance_to_edge(target, area)
        # Prefer one image outside a narrow overlap where edges may shift in generation.
        weight = (distance / 256) ** 15
        colors[window] += np.asarray(image_crop(path, target, area), dtype="float32") * weight[..., None]
        weights[window] += weight
        coverage[window] = np.maximum(coverage[window], np.clip(distance / 28, 0, 1))
    mix = np.divide(colors, weights[..., None], out=colors, where=weights[..., None] > 0)
    alpha = coverage * 255
    artwork.paste(Image.fromarray(mix.clip(0, 255).astype("uint8")), mask=Image.fromarray(alpha.astype("uint8")))
    details = list(rows_in(frame, version, "detail"))
    for row, target, area in details:
        path = plate(row)
        if path is not None:
            place_plate(artwork, frame, target, area, path)
    shore = np.asarray(crop_water(SHORE, frame, outside=0)).copy()
    offshore = bridge_keep(frame) > 0
    if np.any(offshore):
        shore[offshore] = land_alpha(artwork)[offshore]
    # Keep the painted crane booms and boarding float above the offshore water field.
    for row, target, _ in details:
        for left, top, right, bottom in row.get("overwater", ()):
            feature = PixelFrame(row["id"], target.x + left, target.y + top, right - left, bottom - top)
            overlap = deep_zoom.intersection(frame, feature)
            if overlap is None:
                continue
            bounds = deep_zoom.local_box(frame, overlap)
            alpha = Image.fromarray(land_alpha(artwork.crop(bounds))).filter(ImageFilter.MaxFilter(3))
            x0, y0, x1, y1 = bounds
            shore[y0:y1, x0:x1] = np.maximum(shore[y0:y1, x0:x1], np.asarray(alpha))
    keep = (shore * coverage).astype("uint8")
    return artwork, keep, coverage


def place_plate(image, frame, target, area, path, keep=None, transition=48):
    left, top, right, bottom = deep_zoom.local_box(frame, area)
    fade = np.clip((distance_to_edge(target, area) - 24) / transition, 0, 1)
    support = keep[top:bottom, left:right] if keep is not None else 255
    alpha = Image.fromarray((fade * support).astype("uint8"))
    image.paste(image_crop(path, target, area), (left, top), alpha)


def compose(frame, version, folder):
    extended = padded(frame)
    day, keep, coverage = land_art(extended, version)
    old, old_alpha = legacy_mask(extended, coverage, version)
    water = crop_water(WATER, extended)
    hard = source_mask(1, extended)
    buildings = np.asarray(source_mask(128, extended)) > 0
    water_mask = np.asarray(water) > 0
    material = pavement_material(day, np.asarray(hard) > 0, buildings, water_mask)
    folder.mkdir(parents=True, exist_ok=True)
    water.save(folder / f"{frame.key}-water.png")
    hard.save(folder / f"{frame.key}-hard.png")
    save_json(folder / f"{frame.key}-windows.json", painted_windows(day, extended, buildings, water_mask, keep))
    use = (LAMP_PIXELS[:, 0] >= extended.x) & (LAMP_PIXELS[:, 0] < extended.right)
    use &= (LAMP_PIXELS[:, 1] >= extended.y) & (LAMP_PIXELS[:, 1] < extended.bottom)
    lamps = [LAMPS[index] for index in np.flatnonzero(use)]
    reflections = puddle_reflections(extended, lamps, material[0])
    for stem, appearance in APPEARANCES.items():
        image = tone(day, appearance, extended, lamps, work=folder).copy()
        if stem.startswith("rain-"):
            image = wet_surfaces(image, material, reflections if stem == "rain-night" else None)
        # The sampled v0.5 water keeps the offshore field uniform at every zoom.
        image.paste(background(extended, stem), mask=Image.fromarray(255 - keep))
        if stem in PAINTED_WEATHER:
            for row, target, area in rows_in(extended, version, "detail"):
                path = plate(row, stem)
                if path is not None:
                    place_plate(image, extended, target, area, path, keep, transition=116)
        if old is not None and old_alpha.getbbox():
            image.paste(LEGACY.crop(stem, old), deep_zoom.local_box(extended, old)[:2], old_alpha)
        yield stem, image


def area_name(frame, first):
    if first == 7:
        return "east-bay-waterfront"
    if first == 8:
        return "sausalito-shore"
    x = frame.x + BLOCK / 2
    if x > 5100:
        return "bay-bridge"
    if x > -2200:
        return "east-san-francisco"
    if x > -12900:
        return "central-san-francisco"
    return "west-san-francisco"


def schedule(rows):
    approved = unary_union([box(f.x, f.y, f.right, f.bottom) for f in APPROVED])
    groups = {stage: unary_union([rectangle(row["frame"], 64)
                                 for row in rows if row["stage"] == stage]) for stage in (6, 7, 8)}
    result = []
    for frame in blocks():
        area = box(frame.x, frame.y, frame.right, frame.bottom)
        phases = [stage for stage, region in groups.items() if region.intersects(area)]
        if approved.intersects(area) and 6 not in phases:
            phases.insert(0, 6)
        if phases:
            result.append((frame, phases, area_name(frame, phases[0])))
    return result


def pack_block(item):
    frame, phases, region = item
    folder = COMPOSED / frame.key
    extended = padded(frame)
    local = [row for kind in ("area", "detail") for row, _, _ in rows_in(extended, 8, kind)]
    fingerprint = hashlib.sha256(json.dumps([PACK_SIGNATURE, frame.key, phases, region, local],
                                           sort_keys=True).encode()).hexdigest()
    marker = folder / "pack-complete"
    routing = folder / "routing.json"
    if routing.is_file():
        cached = read(routing)
        variants = {int(version): value for version, value in cached.items()}
        if deep_zoom.cached_pack(marker, fingerprint, block_outputs(frame, folder, region, variants)):
            return frame.key, phases[0], region, variants
    for stem, image in compose(frame, 8, folder / "latest"):
        deep_zoom.write_native(image, frame, region, stem)
        deep_zoom.save_overview(image, folder / "latest", stem)
    alternate = {}
    first = phases[0]
    for phase in phases[1:]:
        through = phase - 1
        stamp = f"through-v{through}"
        tiles = {}
        for stem, image in compose(frame, through, folder / stamp):
            tiles.update(deep_zoom.write_native(image, frame, stamp, stem, base_region=region))
            deep_zoom.save_overview(image, folder / stamp, stem)
        for version in range(first, phase):
            alternate[version] = (stamp, tiles)
        first = phase
    print(frame.key, region, flush=True)
    save_json(routing, alternate)
    deep_zoom.save_pack_cache(marker, fingerprint, block_outputs(frame, folder, region, alternate))
    return frame.key, phases[0], region, alternate


def block_outputs(frame, folder, region, alternate):
    paths = [folder / "latest" / f"{stem}-overview.png" for stem in APPEARANCES]
    paths.extend(path for stem in APPEARANCES for *_, tiles in deep_zoom.native_batches(frame, region, stem)
                 for _, _, path in tiles)
    seen = set()
    for stamp, tiles in alternate.values():
        if stamp in seen:
            continue
        seen.add(stamp)
        paths.extend(folder / stamp / f"{stem}-overview.png" for stem in APPEARANCES)
        for tile, root in tiles.items():
            stem, level, xy = tile.split("/")
            paths.append(deep_zoom.SHARED / f"regions/{root}/{stem}_files/{level}/{xy}.webp")
    return paths


def backdrop(item):
    version, stem, output, packed = item
    image = background(WORLD, stem, 4)
    reference_divisor = 32
    reference = background(WORLD, "scene", reference_divisor) if stem == "rain-day" else None
    for key, first, _, alternatives in packed:
        if first > version:
            continue
        stamp = alternatives[version][0] if version in alternatives else "latest"
        path = COMPOSED / key / stamp / f"{stem}-overview.png"
        frame = block_frame(*map(int, key.split("_")))
        with Image.open(path) as patch:
            image.paste(patch, ((frame.x - WORLD.x) // 4, (frame.y - WORLD.y) // 4))
        if reference is not None:
            with Image.open(path.with_name("scene-overview.png")) as dry:
                size = (frame.width // reference_divisor, frame.height // reference_divisor)
                reference.paste(dry.resize(size, Image.Resampling.BOX),
                                ((frame.x - WORLD.x) // reference_divisor,
                                 (frame.y - WORLD.y) // reference_divisor))
    if reference is not None:
        grade = overcast_overview_mask(image, reference, WATER)
    elif stem.endswith("night"):
        grade = legacy_night_edge_mask(WORLD, APPROVED, reference_divisor)
    else:
        grade = None
    root = output / f"v{version}-art/waterfront/regions/overview/{stem}_files"
    for level in range(deep_zoom.SHARED_LEVEL + 1):
        divisor = 2 ** (deep_zoom.MAX_LEVEL - level)
        size = ((WORLD.width + divisor - 1) // divisor, (WORLD.height + divisor - 1) // divisor)
        scaled = image if level == deep_zoom.SHARED_LEVEL else image.resize(size, Image.Resampling.LANCZOS)
        folder = root / str(level)
        folder.mkdir(parents=True, exist_ok=True)
        tile = deep_zoom.TILE
        for row in range((size[1] + tile - 1) // tile):
            for col in range((size[0] + tile - 1) // tile):
                crop = (max(0, col * tile - 1), max(0, row * tile - 1),
                        min(size[0], (col + 1) * tile + 1), min(size[1], (row + 1) * tile + 1))
                tile_image = scaled.crop(crop)
                if grade is not None:
                    bounds = tuple(value * grade.size[index % 2] / size[index % 2]
                                   for index, value in enumerate(crop))
                    alpha = grade.resize(tile_image.size, Image.Resampling.BILINEAR, box=bounds)
                    strength = min(1, (deep_zoom.SHARED_LEVEL + 1 - level) / 3)
                    if strength < 1:
                        alpha = alpha.point(lambda value: round(value * strength))
                    if alpha.getbbox():
                        if stem == "rain-day":
                            darker = tile_image.point([round(value * OVERVIEW_DIMMING) for value in range(256)] * 3)
                            tile_image = Image.composite(darker, tile_image, alpha)
                        else:
                            tile_image = blend_night_edge(tile_image, alpha)
                tile_image.save(folder / f"{col}_{row}.webp", quality=82, method=3)
    print(f"v0.{version} {stem} backdrop", flush=True)


def describe(output, packed, rows, preview):
    shared = output / "illustrated-bay"
    Image.fromarray(read_packed_mask()).save(shared / "masks.png", compress_level=5)
    native = {key: [first, region] for key, first, region, _ in packed}
    overrides = {stage: {name: region for _, _, _, alternatives in packed if stage in alternatives
                         for name, region in alternatives[stage][1].items()} for stage in (6, 7, 8)}
    weather_art = [{"id": row["id"], "appearance": appearance, "sha256": digest}
                   for row in rows for appearance, digest in row["weatherSHA256"].items()]
    common = write_manifest(shared, {"size": [WORLD.width, WORLD.height], "nativeBlocks": native,
                                     "appearanceOverrides": overrides,
                                     "layoutSHA256": sha(LAYOUT), "artwork": len(rows),
                                     "weatherArtwork": weather_art,
                                     "southernContextSHA256": sha(PUBLISHED / "southern-context.png")})
    lights = legacy_lighting(deep_zoom.RetainedArtwork())
    for stage in (6, 7, 8):
        root = output / f"v{stage}-art"
        city = reference_scene(stage)
        city.update(lights)
        for mark in city["landmarks"]:
            if mark["id"] in DETAIL_FOCUS:
                height = mark["p"][2]
                e, n = ground_point(*DETAIL_FOCUS[mark["id"]], height)
                mark["p"] = [e, n, height]
                mark["lonLat"] = TO_GEO.transform(e + ORIGIN_UTM[0], n + ORIGIN_UTM[1])
        active = {key: region for key, (first, region) in native.items() if first <= stage}
        city["assetRoot"] = f"map/v{stage}-art/waterfront/"
        city["maskBundle"] = "map/illustrated-bay/masks.png"
        city["tileLayout"]["sparse"] = {"root": "../../illustrated-bay/", "blockSize": BLOCK,
                                          "blocks": active, "appearanceOverrides": overrides[stage]}
        if preview:
            city["landmarks"] = [mark for mark in city["landmarks"]
                                 if f"{int((camera_point(mark['p'])[0] - WORLD.x) // BLOCK)}_"
                                    f"{int((camera_point(mark['p'])[1] - WORLD.y) // BLOCK)}" in active]
        save_json(root / "waterfront/scene.json", city)
        city_manifest = write_manifest(root / "waterfront", {
            "release": city["release"], "size": [city["width"], city["height"]],
            "tileLayout": city["tileLayout"], "sharedManifestSHA256": sha(shared / "manifest.json"),
            "artwork": [{"id": row["id"], "frame": row["frame"], "kind": row["kind"], "sha256": sha(plate(row))}
                        for row in rows if row["stage"] <= stage],
        })
        old_bay = SOURCE_MAP / f"v{stage}/bay"
        shutil.copytree(old_bay, root / "bay", dirs_exist_ok=True)
        bay = read(root / "bay/scene.json")
        bay["assetRoot"] = f"map/v{stage}-art/bay/"
        save_json(root / "bay/scene.json", bay)
        bay_manifest = write_manifest(root / "bay", {"release": bay["release"], "size": [bay["width"], bay["height"]]})
        save_json(root / "atlas.json", {"version": f"0.{stage}.1", "defaultScene": "waterfront", "scenes": [
            {"id": kind, "path": f"{kind}/scene.json", "manifest": f"{kind}/manifest.json",
             **{key: manifest[key] for key in ("release", "size", "tileCount", "bytes")}}
            for kind, manifest in (("waterfront", city_manifest), ("bay", bay_manifest))
        ]})
    print(f"{common['tileCount']} verified image tiles in {len(native)} shared artwork blocks", flush=True)


def drawing_references():
    from expanded_source import load

    data = load()
    lamps = lamps_for(data, ("Street", "Avenue", "Boulevard", "Road", "Drive", "Bridgeway", "Way"))
    land = map_geometry(data["land"]).buffer(30)
    offshore_bridge = bridge_area(reference_scene(6)).difference(land)
    return lamps, offshore_bridge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    rows = read(LAYOUT)["frames"]
    missing = [row["id"] for row in rows if plate(row) is None]
    if missing and not args.preview:
        parser.error(f"{len(missing)} ImageGen plates are missing: {', '.join(missing[:12])}")
    rows = [row for row in rows if plate(row) is not None]
    for row in rows:
        row["daySHA256"] = sha(plate(row))
        row["weatherSHA256"] = {appearance: sha(path) for appearance in PAINTED_WEATHER
                                if (path := plate(row, appearance)) is not None}
    args.out.mkdir(parents=True, exist_ok=True)
    lamps, offshore_bridge = drawing_references()
    inputs = (
        Path(__file__), ROOT / "tools/expanded_tiles.py", ROOT / "tools/golden_gate_lighting.py",
        ROOT / "tools/illustrated_weather.py",
        ROOT / "data/inner-bay/source.json.gz", reference_mask(), WATER_CORRECTIONS,
        ROOT / "tools/illustrated_guides.py", SOURCE_MAP / "v5/waterfront/manifest.json",
        PUBLISHED / "southern-context.png",
    )
    signature = hashlib.sha256("".join(map(sha, inputs)).encode() + offshore_bridge.normalize().wkb).hexdigest()
    with ProcessPoolExecutor(max_workers=args.jobs, initializer=initialize,
                             initargs=(rows, args.out, lamps, offshore_bridge, signature)) as pool:
        packed = list(pool.map(pack_block, schedule(rows)))
        list(pool.map(backdrop, [(stage, stem, args.out, packed) for stage in (6, 7, 8) for stem in APPEARANCES]))
    describe(args.out, packed, rows, args.preview)


if __name__ == "__main__":
    main()
