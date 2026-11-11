"""Register retained City tiles and new native ImageGen plates over the regional atlas."""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from shapely.geometry import box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from atlas_geometry import SCALE
from bay_illustration_guides import FRAME, WORK as REGIONAL_WORK, regional
from corridor_inputs import ROOT, sha
from native_bay_guides import ART, RATIO, WORLD, detail_rows
from package_full_bay import APPEARANCES, OUT as REGIONAL, TILE, appearance_image, dump, ramp

OUT = ROOT / "public/map/v9-native"
CITY = ROOT / "public/map/v8-art/waterfront/scene.json"
LEVEL = math.ceil(math.log2(WORLD.width))
FIRST_LEVEL = LEVEL - 5


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def retained_layer(city):
    layout = city["tileLayout"]
    block = layout["sparse"]["blockSize"]
    bounds = []
    for key in layout["sparse"]["blocks"]:
        col, row = map(int, key.split("_"))
        bounds.append([col*block, row*block, min((col+1)*block, city["width"]),
                       min((row+1)*block, city["height"])])
    union = unary_union([box(*bounds) for bounds in bounds])
    polygons = [union] if union.geom_type == "Polygon" else list(union.geoms)
    rings = []
    for polygon in polygons:
        polygon = orient(polygon, sign=1)
        rings.extend(list(ring.coords) for ring in [polygon.exterior, *polygon.interiors])
    return dict({k: city[k] for k in ("width", "height", "projection", "assetRoot", "appearanceRevision")},
                tileLayout=dict(layout, minLevel=11), bounds=bounds, crop=rings,
                revealScale=[.043, .095])


def artwork_path(identifier, appearance="scene"):
    suffix = "" if appearance == "scene" else f"-{appearance}"
    return ART / "plates" / f"{identifier}{suffix}.png"


def read_art(row, appearance, land, urban):
    path = artwork_path(row["id"], appearance)
    if path.is_file() or appearance == "scene":
        with Image.open(path) as image:
            if image.size != (1536, 1024):
                raise ValueError(f"Wrong native artwork dimensions: {path}")
            return image.convert("RGB")
    left, top, w, h = row["frame"]
    x, y = left + WORLD.x, top + WORLD.y
    area = (x/RATIO-FRAME.x, y/RATIO-FRAME.y, (x+w)/RATIO-FRAME.x, (y+h)/RATIO-FRAME.y)
    surface = np.asarray(land.resize((w, h), Image.Resampling.NEAREST, box=area)) > 0
    city = np.asarray(urban.resize((w, h), Image.Resampling.NEAREST, box=area)) > 0
    return appearance_image(read_art(row, "scene", land, urban), surface, city,
                            appearance, origin=(left, top), local=True)


def patch_for_level(image, frame, divisor):
    x, y, w, h = frame
    left, top = x // divisor, y // divisor
    right, bottom = math.ceil((x+w)/divisor), math.ceil((y+h)/divisor)
    padded = Image.new("RGBA", ((right-left)*divisor, (bottom-top)*divisor))
    padded.paste(image, (x-left*divisor, y-top*divisor))
    return left, top, padded.resize((right-left, bottom-top), Image.Resampling.LANCZOS)


def write_level(out, level, appearance, rows, images, pool):
    divisor = 2 ** (LEVEL - level)
    width, height = math.ceil(WORLD.width / divisor), math.ceil(WORLD.height / divisor)
    tiles = defaultdict(list)
    for row in rows:
        left, top, patch = patch_for_level(images[row["id"]], row["frame"], divisor)
        right, bottom = left + patch.width, top + patch.height
        for tile_y in range(top//TILE, math.ceil(bottom/TILE)):
            for tile_x in range(left//TILE, math.ceil(right/TILE)):
                tiles[(tile_x, tile_y)].append((row["id"], left, top, patch))

    def write_tile(item):
        (col, row), patches = item
        left, top = max(0, col*TILE-1), max(0, row*TILE-1)
        right, bottom = min(width, (col+1)*TILE+1), min(height, (row+1)*TILE+1)
        tile = Image.new("RGBA", (right-left, bottom-top))
        for _, x, y, image in patches:
            x0, y0, x1, y1 = max(x, left), max(y, top), min(x+image.width, right), min(y+image.height, bottom)
            tile.alpha_composite(image.crop((x0-x, y0-y, x1-x, y1-y)), (x0-left, y0-top))
        region = patches[0][0]
        name = f"{level}/{col}_{row}"
        path = out / f"regions/{region}/{appearance}_files/{name}.webp"
        path.parent.mkdir(parents=True, exist_ok=True)
        tile.save(path, quality=92, method=4)
        return name, region, path

    return list(pool.map(write_tile, sorted(tiles.items())))


def pack_patches(out, rows):
    if not (REGIONAL_WORK / "land.png").is_file():
        regional()
    with Image.open(REGIONAL_WORK / "land.png") as source:
        land = source.copy()
    with Image.open(REGIONAL_WORK / "urban.png") as source:
        urban = source.copy()
    x, y = np.arange(1536), np.arange(1024)
    edge = np.minimum(np.minimum(x, 1535-x)[None, :], np.minimum(y, 1023-y)[:, None])
    alpha = Image.fromarray(np.rint(ramp(edge, 76)*255).astype("uint8"))
    index, files = {}, []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for appearance in APPEARANCES:
            images = {}
            for row in rows:
                image = read_art(row, appearance, land, urban)
                image.putalpha(alpha)
                images[row["id"]] = image
            for level in range(FIRST_LEVEL, LEVEL+1):
                for name, region, path in write_level(out, level, appearance, rows, images, pool):
                    index[name] = region
                    files.append({"path": path.relative_to(out).as_posix(), "sha256": sha(path),
                                  "bytes": path.stat().st_size})
            print(f"{appearance}: {len(index)} visible native tiles", flush=True)
    revision = hashlib.sha256("".join(row["sha256"] for row in files).encode()).hexdigest()[:12]
    bounds = [[x, y, x+w, y+h] for x, y, w, h in (row["frame"] for row in rows)]
    layer = {"width": WORLD.width, "height": WORLD.height, "projection": WORLD.projection(),
             "assetRoot": "map/v9-native/detail/", "appearanceRevision": revision,
             "revealScale": [.08, .23], "bounds": bounds,
             "tileLayout": {"tileSize": TILE, "overlap": 1, "minLevel": FIRST_LEVEL,
                            "maxLevel": LEVEL, "sharedMaxLevel": 0, "fallback": "context", "regions": [],
                            "detail": {"baseLevel": 0, "tiles": index}}}
    artwork = [dict(row, sha256=sha(artwork_path(row["id"]))) for row in rows]
    weather = [{"id": row["id"], "appearance": key, "sha256": sha(artwork_path(row["id"], key))}
               for row in rows for key in APPEARANCES[1:] if artwork_path(row["id"], key).is_file()]
    dump(out / "manifest.json", {"revision": revision, "artwork": artwork, "weather": weather,
                                  "aerialGuides": read(ART / "aerial-guide-sha256.json"), "files": files})
    return layer


def package(out):
    city, bay = read(CITY), read(REGIONAL / "scene.json")
    medium = [row["frame"] for row in read(REGIONAL / "manifest.json")["artwork"] if row["kind"] == "detail"]
    rows = detail_rows()
    layers = [retained_layer(city), pack_patches(out / "detail", rows)]
    bay["nativeDetail"] = {"layers": layers, "regionalBounds": [[x, y, x+w, y+h] for x, y, w, h in medium]}
    ratio = bay["projection"]["scale"] / SCALE
    marks = {mark["id"]: mark for mark in bay["landmarks"]}
    for mark in city["landmarks"]:
        marks[mark["id"]] = dict(mark, detail=True, cityDetail=True,
                                  viewHeight=mark.get("viewHeight", 1080)*ratio,
                                  viewWidth=mark.get("viewWidth", 0)*ratio)
    for row in rows:
        marks[row["id"]] = {"id": row["id"], "name": row["name"], "p": row["p"], "detail": True,
                             "viewHeight": 820*ratio}
    bay["landmarks"] = list(marks.values())
    bay["release"] = "full-bay-native-v9"
    (out / "bay").mkdir(parents=True, exist_ok=True)
    dump(out / "bay/scene.json", bay)
    print(f"{len(layers[0]['bounds'])} retained native blocks and {len(rows)} new close-ups", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    package(args.out)
