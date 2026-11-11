"""Package the v0.5 city core and the existing coast as demand-loaded regions."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import json

import numpy as np
from PIL import Image, ImageChops
from shapely.geometry import LineString

from atlas_geometry import ART_FRAMES, DEPTH_ENCODING, PixelFrame, camera_point, pack_depth
from bay_overview import build as render_bay
from city_core_geometry import CORE_ART, CORE_CONTEXT, CORE_FRAMES, in_core
from city_core_source import load
from corridor_inputs import ROOT, sha
from golden_gate_geometry import ATLAS, DETAIL_FRAMES, WEST_ART, BridgeProfile
from golden_gate_lighting import lamps_for, tone
from golden_gate_routes import west_cars
from package_corridor import APPEARANCES, feather, pyramid as ordinary_pyramid, save_json, write_manifest
from package_corridor import image_point
from paint_golden_gate import stamp_depth
from regional_tiles import layout, pyramid, read_native
from render_city_core import CoreRaster, WORK

OUT = ROOT / "public/map/v5"
BASE = ROOT / "public/map/v4"
ART = ROOT / "assets/city-core"
STAGE = ROOT / ".local/city-core-package"
PATCH = PixelFrame(
    "city-core-patch",
    min(frame.x for frame in CORE_FRAMES),
    min(frame.y for frame in CORE_FRAMES),
    max(frame.right for frame in CORE_FRAMES) - min(frame.x for frame in CORE_FRAMES),
    max(frame.bottom for frame in CORE_FRAMES) - min(frame.y for frame in CORE_FRAMES),
)
LIT_ROADS = (
    "Montgomery", "Kearny", "Grant", "Stockton", "Columbus", "Powell", "Geary",
    "Post Street", "Market Street", "Sutter", "California", "Bush Street", "Broadway",
    "Vallejo", "Pacific Avenue", "Union Street", "Green Street", "Mason", "Taylor",
)


def prepare():
    STAGE.mkdir(parents=True, exist_ok=True)
    destination = OUT / "waterfront"
    destination.mkdir(parents=True, exist_ok=True)
    data = load()
    old = json.loads((BASE / "waterfront/scene.json").read_text(encoding="utf-8"))
    raster = CoreRaster(data, ATLAS, 4)
    raster.draw(data)
    stamp_depth(raster)
    Image.fromarray(pack_depth(raster.depth, raster.structure, DEPTH_ENCODING)).save(destination / "depth.png")
    Image.fromarray((~raster.land).astype("uint8") * 255).save(destination / "water.png")
    Image.fromarray(raster.hard.astype("uint8") * 255).save(destination / "hard.png")

    cars, loops = west_cars(data, frames=CORE_ART, prefix="core")
    overflight = {
        "id": "core-overflight", "kind": "plane",
        "points": [image_point(-3700, -1480, 390), image_point(1420, -1050, 390)],
        "speed": 55, "phase": 1.5, "color": "#e8ece9",
    }
    windows = {tuple(point["p"]): point for point in old["windows"]}
    for frame in CORE_ART:
        points = json.loads((WORK / f"{frame.key}-windows.json").read_text(encoding="utf-8"))
        for point in points:
            windows[tuple(point["p"])] = point
    lamps = [point for point in lamps_for(data, LIT_ROADS) if in_core(point, margin=40)]
    save_json(STAGE / "lamps.json", lamps)
    save_json(STAGE / "routes-audit.json", {"coreLoops": loops, "addedCars": len(cars)})
    landmarks = {point["id"]: point for point in data["landmarks"]}
    route_order = ["ferry-building", "financial-district", "chinatown", "north-beach", "wharf", "union-square"]
    ordered = [landmarks.pop(identity) for identity in route_order]
    scene = {
        **old,
        "release": "city-core-v5",
        "assetRoot": "map/v5/waterfront/",
        "sourceBuildings": len(data["buildings"]),
        "routes": old["routes"] + cars + [overflight],
        "windows": list(windows.values()),
        "lamps": old["lamps"] + [[e, n, z + 4.7] for e, n, z in lamps],
        "landmarks": ordered + list(landmarks.values()),
        "detailFrames": old["detailFrames"] + [asdict(frame) for frame in CORE_ART],
        "tileLayout": layout(),
    }
    save_json(destination / "scene.json", scene)
    print(
        f"Prepared {raster.w} × {raster.h} masks, {len(cars)} core cars, "
        f"{len(scene['landmarks'])} places", flush=True,
    )


def selected_art(frame, appearance):
    folder = ART / ("context" if frame in CORE_CONTEXT else "") / frame.key
    return folder / f"{appearance}.png"


def frame_mask(frame, land, protection=None):
    mask = feather(frame, 150 if frame in CORE_CONTEXT else 78)
    left, top = frame.x - PATCH.x, frame.y - PATCH.y
    box = (left, top, left + frame.width, top + frame.height)
    mask = ImageChops.multiply(mask, land.crop(box))
    if protection is not None:
        mask = ImageChops.multiply(mask, ImageChops.invert(protection.crop(box)))
    return mask


def compose(appearance):
    image = read_native(BASE / "waterfront", "scene" if appearance == "day" else appearance, ATLAS.width, ATLAS.height)
    left, top = ATLAS.local(PATCH.x, PATCH.y)
    bounds = (left, top, left + PATCH.width, top + PATCH.height)
    patch = image.crop(bounds)
    mask = Image.open(OUT / "waterfront/water.png")
    mask_box = (
        bounds[0] * mask.width / ATLAS.width, bounds[1] * mask.height / ATLAS.height,
        bounds[2] * mask.width / ATLAS.width, bounds[3] * mask.height / ATLAS.height,
    )
    land = ImageChops.invert(mask.resize(patch.size, Image.Resampling.NEAREST, box=mask_box))
    protection = Image.new("L", patch.size)
    for frame in (*ART_FRAMES, *WEST_ART):
        if frame.right <= PATCH.x or frame.x >= PATCH.right or frame.bottom <= PATCH.y or frame.y >= PATCH.bottom:
            continue
        local = Image.new("L", patch.size)
        local.paste(feather(frame, 78), (frame.x - PATCH.x, frame.y - PATCH.y))
        protection = ImageChops.lighter(protection, local)
    lamps = json.loads((STAGE / "lamps.json").read_text(encoding="utf-8"))
    by_key = {frame.key: frame for frame in CORE_ART}
    # Each landmark stays with the plate that contains its full silhouette.
    order = [by_key[key] for key in (
        "market-corridor", "north-beach-link", "north-beach", "telegraph-hill",
        "union-square", "chinatown", "financial-core",
    )]
    for frame in (*CORE_CONTEXT, *order):
        path = selected_art(frame, appearance)
        if path.exists():
            art = Image.open(path).convert("RGB")
        else:
            day = Image.open(selected_art(frame, "day")).convert("RGB")
            art = tone(day, appearance, frame, lamps, work=WORK)
        if art.size != (1536, 1024):
            raise ValueError(f"Artwork must be native 1536 × 1024: {path}")
        art = art.resize((frame.width, frame.height), Image.Resampling.BICUBIC)
        alpha = frame_mask(frame, land, protection if frame in CORE_CONTEXT else None)
        patch.paste(art, (frame.x - PATCH.x, frame.y - PATCH.y), alpha)
    image.paste(patch, bounds[:2])
    return image


def build_appearance(item):
    stem, appearance = item
    image = compose(appearance)
    thumbnail = image.crop((
        PATCH.x - ATLAS.x, PATCH.y - ATLAS.y,
        PATCH.right - ATLAS.x, PATCH.bottom - ATLAS.y,
    ))
    thumbnail.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
    thumbnail.save(STAGE / f"assembled-{appearance}.jpg", quality=93)
    left, top = ATLAS.local(PATCH.x, PATCH.y)
    counts, retained = pyramid(
        image, OUT / "waterfront", stem, layout(), previous=BASE / "waterfront",
        changed_bounds=(left, top, left + PATCH.width, top + PATCH.height),
    )
    return {"appearance": stem, "regions": counts, "retainedTiles": retained}


def finalize(results):
    destination = OUT / "waterfront"
    scene = json.loads((destination / "scene.json").read_text(encoding="utf-8"))
    records = []
    for frame in CORE_FRAMES:
        for appearance in APPEARANCES.values():
            path = selected_art(frame, appearance)
            if path.exists():
                with Image.open(path) as art:
                    size = list(art.size)
                records.append({
                    "frame": frame.key, "appearance": appearance,
                    "path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "size": size,
                })
    for region in sorted({name for result in results for name in result["regions"]}):
        files = [
            {"path": path.relative_to(destination).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in sorted((destination / "regions" / region).rglob("*.webp"))
        ]
        save_json(destination / "regions" / region / "manifest.json", {"id": region, "files": files})
    return write_manifest(destination, {
        "release": scene["release"], "size": [ATLAS.width, ATLAS.height],
        "maskSize": scene["maskSize"], "projection": scene["projection"],
        "tileLayout": scene["tileLayout"], "artwork": records,
        "baseManifestSHA256": sha(BASE / "waterfront/manifest.json"),
        "coreSourceSHA256": sha(ROOT / "data/city-core/source.json.gz"),
        "regionPackages": results,
        "routes": dict(Counter(route["kind"] for route in scene["routes"])),
        **json.loads((STAGE / "routes-audit.json").read_text(encoding="utf-8")),
    })


def build_bay():
    source = STAGE / "bay"
    source.mkdir(parents=True, exist_ok=True)
    destination = OUT / "bay"
    destination.mkdir(parents=True, exist_ok=True)
    profile = BridgeProfile()
    bridge = LineString([
        camera_point(profile.point(station))[:2]
        for station in range(profile.start, profile.end, 15)
    ]).buffer(64)
    render_bay(
        source, detail_frames=(*DETAIL_FRAMES, *CORE_ART), extra_coverage=bridge,
        release="bay-overview-v5", asset_root="map/v5/bay/",
    )
    for name in ("scene.json", "depth.png", "water.png", "hard.png"):
        (destination / name).write_bytes((source / name).read_bytes())
    for stem in APPEARANCES:
        with Image.open(source / f"{stem}.png") as image:
            ordinary_pyramid(image.convert("RGB"), destination, stem)
    scene = json.loads((destination / "scene.json").read_text(encoding="utf-8"))
    return write_manifest(destination, {
        "release": scene["release"], "size": [scene["width"], scene["height"]],
        "maskSize": scene["maskSize"], "projection": scene["projection"],
        "appearances": list(APPEARANCES), "sources": scene["sources"],
    })


def write_atlas():
    entries = []
    for key in ("waterfront", "bay"):
        manifest = json.loads((OUT / key / "manifest.json").read_text(encoding="utf-8"))
        entries.append({
            "id": key, "release": manifest["release"], "path": f"{key}/scene.json",
            "manifest": f"{key}/manifest.json", "size": manifest["size"],
            "tileCount": manifest["tileCount"], "bytes": manifest["bytes"],
        })
    save_json(OUT / "atlas.json", {"version": "0.5.0", "defaultScene": "waterfront", "scenes": entries})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", nargs="?", default="all", choices=("all", "prepare", "tiles", "bay", "manifest"))
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    if args.stage in ("all", "prepare"):
        prepare()
    if args.stage in ("all", "tiles"):
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(build_appearance, APPEARANCES.items()))
        finalize(results)
    if args.stage in ("all", "bay"):
        build_bay()
    if args.stage in ("all", "manifest"):
        write_atlas()


if __name__ == "__main__":
    main()
