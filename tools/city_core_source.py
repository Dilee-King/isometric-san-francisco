"""Extend the retained v0.4 source with the selected inland snapshot."""

import argparse
import gzip
import json

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from city_core_geometry import CORE_FRAMES, jump_points
from corridor_inputs import ROOT, crop_lidar, footprints, osm_vectors, sha
from corridor_source import derive
from golden_gate_source import load as load_waterfront

SOURCE_DIR = ROOT / "data/city-core"


def load():
    base = load_waterfront()
    inland = json.loads(gzip.decompress((SOURCE_DIR / "source.json.gz").read_bytes()))
    buildings = {building["id"]: building for building in base["buildings"]}
    for building in inland["buildings"]:
        buildings.setdefault(building["id"], building)
    for identity, name, kind in (
        ("201006.0000687", "Transamerica Pyramid", "pyramid"),
        ("201006.0006230", "Coit Tower", "tower"),
    ):
        building = dict(buildings[identity])
        building["name"] = name
        building["renderKind"] = kind
        building["height"] = round(building["roofMax"] - building["ground"], 2)
        buildings[identity] = building

    road_ids = {road["id"] for road in base["roads"]}
    additional_roads = [road for road in inland["roads"] if road["id"] not in road_ids]
    terrain = base["terrain"]
    elevation = RegularGridInterpolator(
        (terrain["n"], terrain["x"]), terrain["z"], bounds_error=False, fill_value=2.6,
    )
    graded_roads = []
    for road in additional_roads:
        if road["bridge"] or road["tunnel"]:
            graded_roads.append(road)
            continue
        points = []
        for start, end in zip(road["points"], road["points"][1:]):
            length = np.linalg.norm(np.array(end[:2]) - start[:2])
            reference_start = max(1.7, float(elevation([[start[1], start[0]]])[0])) + .18
            reference_end = max(1.7, float(elevation([[end[1], end[0]]])[0])) + .18
            for t in np.linspace(0, 1, max(2, int(length / 10) + 1), endpoint=False):
                easting = start[0] + (end[0] - start[0]) * t
                northing = start[1] + (end[1] - start[1]) * t
                height = max(1.7, float(elevation([[northing, easting]])[0])) + 0.18
                height += (1 - t) * (start[2] - reference_start) + t * (end[2] - reference_end)
                points.append([round(easting, 2), round(northing, 2), round(height, 2)])
        points.append(road["points"][-1])
        graded_roads.append({**road, "points": points})
    existing_trees = {tuple(tree[:2]) for tree in base["trees"]}
    trees = base["trees"] + [tree for tree in inland["trees"] if tuple(tree[:2]) not in existing_trees]
    core_points = jump_points()
    core_ids = {landmark["id"] for landmark in core_points}
    return {
        **base,
        "buildings": list(buildings.values()),
        "roads": base["roads"] + graded_roads,
        "trees": trees,
        "landmarks": core_points + [point for point in base["landmarks"] if point["id"] not in core_ids],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.refresh or not (SOURCE_DIR / "source.json.gz").exists():
        footprints()
        osm_vectors()
        crop_lidar()
        derive(out=SOURCE_DIR, frames=CORE_FRAMES)
    data = load()
    report = {
        "baseSourceSHA256": sha(ROOT / "data/golden-gate/source.json.gz"),
        "inlandSourceSHA256": sha(SOURCE_DIR / "source.json.gz"),
        "buildings": len(data["buildings"]),
        "roads": len(data["roads"]),
        "landmarks": len(data["landmarks"]),
        "sourceCRS": "EPSG:32610",
    }
    (SOURCE_DIR / "assembly.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
