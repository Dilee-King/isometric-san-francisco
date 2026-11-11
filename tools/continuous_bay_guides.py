"""Make registered aerial and neighboring artwork guides for continuous Bay infill."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math

import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import Window, from_bounds
import requests

from atlas_geometry import SCALE, PixelFrame
from bay_illustration_guides import source_bounds, source_raster
from corridor_inputs import ROOT, TO_GEO, sha
from expanded_tiles import intersection, local_box
from native_bay_guides import ART as NATIVE_ART, WORLD, detail_rows, guide

WORK = ROOT / ".local/continuous-bay"
ART = ROOT / "assets/continuous-bay"
PLATES = ART / "plates"
CITY_ART = ROOT / "assets/illustrated-expansion"
CITY_SCENE = ROOT / "public/map/v8-art/waterfront/scene.json"
CATALOG = "https://planetarycomputer.microsoft.com/api/stac/v1"
TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/naipeuwest/naip"


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def rows():
    layout = read(ART / "layout.json")
    width, height = layout["plateSize"]
    for row in layout["rows"]:
        for col, wave in zip(row["columns"], row["waves"], strict=True):
            name = f"{row['name']}-{col + 1:02d}"
            yield {"id": name, "frame": [layout["columnOrigins"][col]-WORLD.x, row["y"]-WORLD.y, width, height],
                   "wave": wave, "region": "east-bay-waterfront", "reuseCity": name in layout["reuseCity"]}


def frame_for(row):
    left, top, width, height = row["frame"]
    return PixelFrame(row["id"], left + WORLD.x, top + WORLD.y, width, height)


def paste_city(image, frame, scene, approved):
    layout = scene["tileLayout"]
    sparse = layout["sparse"]
    tile_size, overlap = layout["tileSize"], layout["overlap"]
    level = layout["maxLevel"]
    x0, y0 = (-x for x in scene["projection"]["origin"])
    root = ROOT / "public" / scene["assetRoot"] / sparse["root"]
    used = set()
    for anchor in approved:
        area = intersection(frame, anchor)
        if area is None:
            continue
        left, top, right, bottom = area
        for row in range((top-y0)//tile_size, (bottom-1-y0)//tile_size+1):
            for col in range((left-x0)//tile_size, (right-1-x0)//tile_size+1):
                block = sparse["blockSize"]
                name = f"{col}_{row}"
                region = sparse.get("appearanceOverrides", {}).get(f"scene/{level}/{name}")
                region = region or sparse["blocks"].get(f"{col*tile_size//block}_{row*tile_size//block}")
                if region is None:
                    continue
                path = root / f"regions/{region}/scene_files/{level}/{name}.webp"
                with Image.open(path) as tile:
                    tx, ty = x0 + max(0, col*tile_size-overlap), y0 + max(0, row*tile_size-overlap)
                    crop = (max(left, tx), max(top, ty), min(right, tx+tile.width), min(bottom, ty+tile.height))
                    image.paste(tile.crop((crop[0]-tx, crop[1]-ty, crop[2]-tx, crop[3]-ty)),
                                (crop[0]-frame.x, crop[1]-frame.y))
                used.add(anchor.key)
    return used


def paste_plate(image, frame, other, path):
    area = intersection(frame, other)
    if area is None or not path.is_file():
        return False
    with Image.open(path) as plate:
        image.paste(plate.crop(local_box(other, area)), local_box(frame, area)[:2])
    return True


def context_guides(targets):
    scene = read(CITY_SCENE)
    approved = [PixelFrame(row["id"], *row["frame"]) for row in read(CITY_ART / "layout.json")["frames"]
                if (CITY_ART / "plates" / f"{row['id']}.png").is_file()]
    retained = [(frame_for(row), NATIVE_ART / "plates" / f"{row['id']}.png") for row in detail_rows()]
    neighbors = [(row["wave"], frame_for(row), PLATES / f"{row['id']}.png") for row in rows()]
    target_dir = WORK / "context"
    target_dir.mkdir(parents=True, exist_ok=True)
    for row in targets:
        frame = frame_for(row)
        source = WORK / "guides" / f"{frame.key}.png"
        with Image.open(source) as aerial:
            image = aerial.convert("RGB")
        used = paste_city(image, frame, scene, approved)
        for other, path in retained:
            if paste_plate(image, frame, other, path):
                used.add(other.key)
        for wave, other, path in neighbors:
            if wave < row["wave"] and paste_plate(image, frame, other, path):
                used.add(other.key)
        if not used:
            raise ValueError(f"Missing a completed edge for {frame.key}")
        image.save(target_dir / f"{frame.key}.png")
        record = {"aerialSha256": source.with_suffix(".sha256").read_text(encoding="ascii").strip(),
                  "guideSha256": sha(target_dir / f"{frame.key}.png"), "anchors": sorted(used)}
        (target_dir / f"{frame.key}.json").write_text(json.dumps(record) + "\n", encoding="utf8")
        print(f"{frame.key}: {', '.join(sorted(used))}", flush=True)


def fetch_guides(targets, size):
    (WORK / "guides").mkdir(parents=True, exist_ok=True)
    failures = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        tasks = {pool.submit(guide, row, size, work=WORK): row["id"] for row in targets}
        for task in as_completed(tasks):
            try:
                print(task.result(), flush=True)
            except (OSError, ValueError) as error:
                failures.append(tasks[task])
                print(f"{tasks[task]}: {error}", flush=True)
    if failures:
        raise SystemExit("Unavailable aerial guides: " + ", ".join(failures))


def fetch_cutout(targets):
    frames = list(map(frame_for, targets))
    x0, y0 = min(frame.x for frame in frames), min(frame.y for frame in frames)
    x1, y1 = max(frame.right for frame in frames), max(frame.bottom for frame in frames)
    bounds, _ = source_bounds(PixelFrame("cutout", x0, y0, x1-x0, y1-y0), SCALE)
    local = WORK / f"naip-{x0}-{y0}-{x1}-{y1}.tif"
    source_record = local.with_suffix(".json")
    if not local.is_file() or not source_record.is_file():
        response = requests.get(f"{CATALOG}/search", params={
            "collections": "naip", "bbox": ",".join(map(str, TO_GEO.transform_bounds(*bounds))),
            "datetime": "2022-01-01/2022-12-31", "limit": 80,
        }, timeout=25)
        response.raise_for_status()
        items = sorted(response.json()["features"], key=lambda item: item["id"])
        if not items:
            raise ValueError("The NAIP catalog returned no scenes for the drawing window")
        token_response = requests.get(TOKEN, timeout=25)
        token_response.raise_for_status()
        access = token_response.json()["token"]
        temp = local.with_suffix(".part.tif")
        west, south, east, north = bounds
        width, height = math.ceil((east-west)/.6), math.ceil((north-south)/.6)
        transform = from_origin(west, north, .6, .6)
        rgb = np.zeros((3, height, width), dtype="uint8")
        try:
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="30"):
                for item in items:
                    href = item["assets"]["image"]["href"]
                    with rasterio.open(href + "?" + access) as source:
                        area = transform_bounds("EPSG:32610", source.crs, *bounds)
                        window = from_bounds(*area, source.transform).intersection(Window(0, 0, source.width, source.height))
                        window = window.round_offsets().round_lengths()
                        pixels = source.read((1, 2, 3), window=window)
                        reproject(pixels, rgb, src_transform=source.window_transform(window), src_crs=source.crs,
                                  dst_transform=transform, dst_crs="EPSG:32610", src_nodata=0, dst_nodata=0,
                                  init_dest_nodata=False, resampling=rasterio.enums.Resampling.bilinear)
                    print(f"Read {item['id']}", flush=True)
            with rasterio.open(temp, "w", driver="GTiff", count=3, height=height, width=width, dtype="uint8",
                               crs="EPSG:32610", transform=transform, tiled=True, compress="deflate") as output:
                output.write(rgb)
        except rasterio.errors.RasterioError as error:
            message = str(error).replace(access, "[access token]")
            raise RuntimeError(f"Could not read the registered NAIP cutout: {message}") from None
        temp.replace(local)
        record = {"sha256": sha(local), "bounds": bounds, "crs": "EPSG:32610",
                  "sources": [{"id": item["id"], "href": item["assets"]["image"]["href"]} for item in items]}
        source_record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf8")
    digest = read(source_record)["sha256"]
    destination = WORK / "guides"
    destination.mkdir(parents=True, exist_ok=True)
    for frame in frames:
        rgb = np.stack(source_raster(local, frame, SCALE, (1, 2, 3)), axis=-1).astype("uint8")
        if np.mean(np.all(rgb == 0, axis=2)) > .02:
            raise ValueError(f"Aerial coverage is incomplete at {frame.key}")
        Image.fromarray(rgb).save(destination / f"{frame.key}.png")
        (destination / f"{frame.key}.sha256").write_text(digest + "\n", encoding="ascii")
        print(frame.key, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--wave", type=int)
    parser.add_argument("--size", type=int, default=1680)
    parser.add_argument("--context", action="store_true")
    parser.add_argument("--cutout", action="store_true")
    args = parser.parse_args()
    targets = [row for row in rows() if (not args.ids or row["id"] in args.ids)
               and (args.wave is None or row["wave"] == args.wave)]
    if not targets:
        parser.error("No matching frames")
    if args.context:
        context_guides(targets)
    elif args.cutout:
        fetch_cutout(targets)
    else:
        fetch_guides(targets, args.size)
