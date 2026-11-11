"""Write the cumulative v0.6, v0.7 and v0.8 release descriptors and overview."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json

from PIL import Image
from shapely.ops import unary_union

from bay_overview import build as render_bay
from corridor_inputs import ROOT, local_xy, sha
from expanded_bridge import BayBridge
from expanded_geometry import BLOCK, DEPTH_ENCODING, MASK_DIVISOR, SOURCE_EXTENT, WORLD, art_frames, places
from expanded_render import WORK, coverages, region_blocks
from expanded_routes import FERRIES, build_routes
from expanded_source import SNAPSHOT, load
from expanded_tiles import ART, LEGACY, MAX_LEVEL, RUNTIME, SHARED, SHARED_LEVEL, TILE
from package_corridor import APPEARANCES, pyramid, save_json, write_manifest

DETAIL_VIEW_HEIGHT = {"golden-gate-park": 940, "ocean-beach": 980, "alamo-square": 960,
                      "mission-dolores": 960, "bayview": 1020, "oakland-port": 1010,
                      "jack-london": 1050, "sausalito": 1120}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def scene_inputs():
    data = load()
    bridge = BayBridge(data["roads"])
    active = region_blocks(data, bridge)
    source_signature = hashlib.sha256("".join(sha(path) for path in (
        SNAPSHOT, ROOT / "tools/expanded_routes.py", ROOT / "tools/expanded_bridge.py",
        ROOT / "tools/expanded_render.py", ROOT / "tools/expanded_geometry.py",
    )).encode()).hexdigest()
    cache = WORK / "routes.json"
    existing = read(cache) if cache.is_file() else {}
    if existing.get("signature") == source_signature:
        routes = {int(key): value for key, value in existing["routes"].items()}
        audit = existing["audit"]
    else:
        routes, audit = build_routes(data, bridge, active)
        save_json(cache, {"signature": source_signature, "routes": routes, "audit": audit})
    return data, bridge, active, routes, audit


def write_city(version, source, active, routes, audit):
    previous = read(LEGACY / "scene.json")
    destination = RUNTIME / f"v{version}/waterfront"
    destination.mkdir(parents=True, exist_ok=True)
    native = {key: region for key, (release, region) in active.items() if release <= version}
    selected = [route for release in range(6, version + 1) for route in routes[release]]
    new_places = places(version)
    terminal_coordinates = {identity.removesuffix("-ferry"): point for _, identity, point, _ in FERRIES}
    terminal_coordinates["bay-bridge-east"] = (-122.3555, 37.8166)
    for place in new_places:
        place["viewHeight"] = DETAIL_VIEW_HEIGHT.get(place["id"], place["viewHeight"])
        if place["id"] in terminal_coordinates:
            lon, lat = terminal_coordinates[place["id"]]
            place["p"] = [*map(float, local_xy(lon, lat)), place["p"][2]]
            place["lonLat"] = [lon, lat]
    landmarks = previous["landmarks"] + new_places
    scene = {
        **previous, "release": f"inner-bay-v{version}", "assetRoot": f"map/v{version}/waterfront/",
        "width": WORLD.width, "height": WORLD.height, "projection": WORLD.projection(),
        "maskSize": [WORLD.width // MASK_DIVISOR, WORLD.height // MASK_DIVISOR],
        "maskBundle": "map/inner-bay/masks.png", "depthEncoding": DEPTH_ENCODING, "clipDepth": 32768,
        "extent": SOURCE_EXTENT, "sourceBuildings": len(source["buildings"]), "landmarks": landmarks,
        "routes": previous["routes"] + selected,
        "tileLayout": {"tileSize": TILE, "overlap": 1, "maxLevel": MAX_LEVEL,
                       "sharedMaxLevel": SHARED_LEVEL, "fallback": "overview", "regions": [],
                       "sparse": {"root": "../../inner-bay/", "blockSize": BLOCK, "blocks": native}},
    }
    save_json(destination / "scene.json", scene)
    routes_by_kind = dict(Counter(route["kind"] for route in scene["routes"]))
    artwork = []
    place_ids = {place["id"] for place in places(version)}
    for frame in art_frames():
        if frame.key not in place_ids:
            continue
        path = ART / frame.key / "day.png"
        if not path.is_file():
            raise ValueError(f"Missing selected art for {frame.key}")
        for selected in (path, path.with_name("rain-night.png")):
            if selected.is_file():
                artwork.append({"frame": frame.key, "appearance": selected.stem,
                                "path": selected.relative_to(ROOT).as_posix(), "sha256": sha(selected),
                                "size": [1536, 1024], "origin": [frame.x, frame.y]})
    save_json(destination / "release-info.json", {"routes": routes_by_kind, "places": len(landmarks), "artwork": artwork})
    print(f"v0.{version}: {len(native)} native blocks, {len(landmarks)} places, {routes_by_kind}", flush=True)
    return write_manifest(destination, {
        "release": scene["release"], "size": [WORLD.width, WORLD.height], "maskSize": scene["maskSize"],
        "projection": scene["projection"], "tileLayout": scene["tileLayout"],
        "sharedManifest": "../../inner-bay/manifest.json", "sharedManifestSHA256": sha(SHARED / "manifest.json"),
        "sourceSHA256": sha(SNAPSHOT), "legacyManifestSHA256": sha(LEGACY / "manifest.json"),
        "artwork": artwork, "routes": routes_by_kind,
        "vesselClearance": {key: value for key, value in audit.items() if "minClearanceMetres" in value
                            and (version == 8 or version == 7 and key != "sausalito-ferry")},
    })


def write_bay(version, footprint):
    source = WORK / f"bay-v{version}"
    destination = RUNTIME / f"v{version}/bay"
    destination.mkdir(parents=True, exist_ok=True)
    render_bay(source, detail_frames=(), extra_coverage=footprint,
               release=f"bay-overview-v{version}", asset_root=f"map/v{version}/bay/")
    for filename in ("scene.json", "depth.png", "water.png", "hard.png"):
        (destination / filename).write_bytes((source / filename).read_bytes())
    for stem in APPEARANCES:
        with Image.open(source / f"{stem}.png") as image:
            pyramid(image.convert("RGB"), destination, stem)
    scene = read(destination / "scene.json")
    return write_manifest(destination, {"release": scene["release"], "size": [scene["width"], scene["height"]],
                                        "maskSize": scene["maskSize"], "projection": scene["projection"],
                                        "appearances": list(APPEARANCES), "sources": scene["sources"]})


def overview_task(args):
    return write_bay(*args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", nargs="?", default="all", choices=("routes", "overview", "all"))
    parser.add_argument("--version", choices=(6, 7, 8), type=int)
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    versions = [args.version] if args.version else [6, 7, 8]
    if args.stage == "overview":
        source = load()
        bridge = BayBridge(source["roads"])
    else:
        source, bridge, active, routes, audit = scene_inputs()
        if args.stage == "routes":
            print(json.dumps(audit, indent=2), flush=True)
            return
    coverage = coverages(source, bridge)
    if args.stage == "overview" or not all((RUNTIME / f"v{version}/bay/manifest.json").is_file() for version in versions):
        arguments = [(version, unary_union([coverage[key] for key in range(6, version + 1)])) for version in versions]
        with ProcessPoolExecutor(max_workers=3) as pool:
            list(pool.map(overview_task, arguments))
    if args.stage == "overview":
        return
    for version in versions:
        city = write_city(version, source, active, routes, audit)
        bay = read(RUNTIME / f"v{version}/bay/manifest.json")
        entries = [{"id": name, "release": row["release"], "path": f"{name}/scene.json",
                    "manifest": f"{name}/manifest.json", "size": row["size"], "tileCount": row["tileCount"],
                    "bytes": row["bytes"]} for name, row in (("waterfront", city), ("bay", bay))]
        save_json(RUNTIME / f"v{version}/atlas.json", {"version": f"0.{version}.0", "defaultScene": "waterfront", "scenes": entries})


if __name__ == "__main__":
    main()
