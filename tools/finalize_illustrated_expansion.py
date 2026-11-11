"""Finalize regional routing and share identical illustrated backdrops."""

import argparse
import filecmp
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from shapely import contains_xy
from shapely.geometry import box
from shapely.ops import unary_union

import expanded_tiles as deep_zoom
from expanded_geometry import MASK_DIVISOR, WORLD
from expanded_render import block_frame
from illustrated_guides import APPROVED, projected
from illustrated_layout import rectangle
from package_corridor import save_json, write_manifest


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def share_backdrop(overview, latest):
    kept = []
    reused = 0
    for path in sorted(overview.rglob("*.webp")):
        relative = path.relative_to(overview)
        common = latest / relative
        if common.is_file() and filecmp.cmp(path, common, shallow=False):
            reused += path.stat().st_size
            path.unlink()
        else:
            appearance, level, tile = relative.parts
            kept.append(f"{appearance.removesuffix('_files')}/{level}/{Path(tile).stem}")
    return kept, reused


def hide_unpainted_roads(routes, original_count, artwork, flags):
    suppressed = 0
    for route in routes[original_count:]:
        if route["kind"] != "car" or len(route["points"]) < 2:
            continue
        points = np.asarray(route["points"])
        start = points[:-1]
        end = points[1:]
        supported = np.ones(len(start), dtype=bool)
        for progress in (.1, .5, .9):
            x, y = projected(start + (end - start) * progress, WORLD).T
            supported &= contains_xy(artwork, x + WORLD.x, y + WORLD.y)
            if not route["id"].startswith("bay-bridge-"):
                column = np.clip((x / MASK_DIVISOR).astype(int), 0, flags.shape[1] - 1)
                row = np.clip((y / MASK_DIVISOR).astype(int), 0, flags.shape[0] - 1)
                supported &= (flags[row, column] & 2) == 0
        original = set(route.get("hiddenSegments", []))
        hidden = original | set(np.flatnonzero(~supported).tolist())
        if hidden:
            route["hiddenSegments"] = sorted(hidden)
        suppressed += len(hidden - original)
    return suppressed


def remove_stale_native_tiles(shared, manifest):
    deep_zoom.SHARED = shared
    expected = set()
    for key, (_, region) in manifest["nativeBlocks"].items():
        frame = block_frame(*map(int, key.split("_")))
        expected.update(path for appearance in deep_zoom.APPEARANCES
                        for *_, tiles in deep_zoom.native_batches(frame, region, appearance)
                        for _, _, path in tiles)
    for overrides in manifest["appearanceOverrides"].values():
        for key, region in overrides.items():
            appearance, level, xy = key.split("/")
            expected.add(shared / f"regions/{region}/{appearance}_files/{level}/{xy}.webp")
    actual = set((shared / "regions").rglob("*.webp"))
    if expected - actual:
        raise ValueError(f"Missing expected native tile: {min(expected - actual)}")
    stale = actual - expected
    for path in stale:
        path.unlink()
    return len(stale)


def finalize(root):
    latest = root / "v8-art/waterfront/regions/overview"
    if not any(latest.rglob("*.webp")):
        raise ValueError(f"Missing common backdrop: {latest}")
    original = read(deep_zoom.LEGACY / "scene.json")
    shared = root / "illustrated-bay"
    manifest = read(shared / "manifest.json")
    stale = remove_stale_native_tiles(shared, manifest)
    if stale:
        write_manifest(shared, {k: v for k, v in manifest.items() if k not in ("files", "tileCount", "bytes")})
    shared_sha = deep_zoom.sha(shared / "manifest.json")
    backdrop_overrides = {}
    for version in (6, 7):
        overview = root / f"v{version}-art/waterfront/regions/overview"
        kept, reused = share_backdrop(overview, latest)
        backdrop_overrides[version] = kept
        print(f"v0.{version}: {len(kept)} distinct backdrop tiles, {reused:,} duplicate bytes shared", flush=True)
    revision = hashlib.sha256(bytes.fromhex(shared_sha))
    for version in (6, 7, 8):
        overview = root / f"v{version}-art/waterfront/regions/overview"
        for tile in sorted(overview.rglob("*.webp")):
            if tile.relative_to(overview).parts[0] != "scene_files":
                revision.update(bytes.fromhex(deep_zoom.sha(tile)))
    appearance_revision = revision.hexdigest()[:12]
    with Image.open(shared / "masks.png") as packed:
        flags = np.asarray(packed)[:, :, 2].copy()
    legacy = [box(f.x + 24, f.y + 24, f.right - 24, f.bottom - 24) for f in APPROVED]
    for version in (6, 7, 8):
        release = root / f"v{version}-art"
        city = release / "waterfront"
        scene_path = city / "scene.json"
        scene = read(scene_path)
        scene["appearanceRevision"] = appearance_revision
        manifest = read(city / "manifest.json")
        if version < 8:
            scene["tileLayout"]["sparse"]["backdropRoot"] = "../../v8-art/waterfront/"
            scene["tileLayout"]["sparse"]["backdropOverrides"] = backdrop_overrides[version]
        artwork = unary_union([*legacy, *(rectangle(row["frame"], 28) for row in manifest["artwork"])])
        count = hide_unpainted_roads(scene["routes"], len(original["routes"]), artwork, flags)
        save_json(scene_path, scene)
        manifest["tileLayout"] = scene["tileLayout"]
        manifest["sharedManifestSHA256"] = shared_sha
        manifest = write_manifest(city, {k: v for k, v in manifest.items()
                                         if k not in ("files", "tileCount", "bytes")})
        atlas_path = release / "atlas.json"
        atlas = read(atlas_path)
        waterfront = next(row for row in atlas["scenes"] if row["id"] == "waterfront")
        waterfront.update({key: manifest[key] for key in ("tileCount", "bytes")})
        save_json(atlas_path, atlas)
        print(f"v0.{version}: {count} unillustrated road segments hidden", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    finalize(parser.parse_args().root)
