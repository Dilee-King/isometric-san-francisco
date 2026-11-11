"""Count and list uncovered native-scale artwork across the existing Bay Area frame."""

import argparse
import gzip
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from shapely import box, covers, prepare, union_all

from atlas_geometry import SCALE, SE
from bay_illustration_guides import FRAME, REGIONAL_SCALE, WORK as REGIONAL_WORK, regional
from corridor_inputs import ROOT
from native_bay_guides import RATIO

STEP_X, STEP_Y = 1152, 768
PUBLIC = ROOT / "public/map"


def ready_art(scene):
    shape = []
    for index, layer in enumerate(scene["nativeDetail"]["layers"]):
        assert layer["projection"]["scale"] == SCALE
        dx, dy = layer["projection"]["origin"]
        inset = 0 if index == 0 else 76
        shape.extend(box(x0-dx+inset, y0-dy+inset, x1-dx-inset, y1-dy-inset)
                     for x0, y0, x1, y1 in layer["bounds"])
    coverage = union_all(shape)
    prepare(coverage)
    return coverage


def plan(scene_file, output):
    scene = json.loads(scene_file.read_text(encoding="utf8"))
    if not (REGIONAL_WORK / "land.png").is_file():
        regional()
    with Image.open(REGIONAL_WORK / "land.png") as source:
        land = np.asarray(source) > 0
    y0, y1 = math.floor(FRAME.y*RATIO), math.ceil(FRAME.bottom*RATIO)
    x0, x1 = math.floor(FRAME.x*RATIO), math.ceil(FRAME.right*RATIO)
    left = np.arange(x0, x1, STEP_X)
    top = np.arange(y0, y1, STEP_Y)
    x, y = np.meshgrid(left, top)
    right, bottom = np.minimum(x+STEP_X, x1), np.minimum(y+STEP_Y, y1)
    on_hand = covers(ready_art(scene), box(x, y, right, bottom))
    land_cells = np.zeros(x.shape, dtype=bool)
    for row, col in np.ndindex(x.shape):
        west = max(0, math.floor(x[row, col]/RATIO-FRAME.x))
        east = min(FRAME.width, math.ceil(right[row, col]/RATIO-FRAME.x))
        north = max(0, math.floor(y[row, col]/RATIO-FRAME.y))
        south = min(FRAME.height, math.ceil(bottom[row, col]/RATIO-FRAME.y))
        land_cells[row, col] = land[north:south, west:east].any()

    remaining = land_cells & ~on_hand
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(output, "wt", encoding="utf8") as queue:
            for row, col in zip(*np.nonzero(remaining), strict=True):
                p = [int(x[row, col]), int(y[row, col]), int(right[row, col]), int(bottom[row, col])]
                job = {"id": f"bay-{row:03d}-{col:03d}", "core": p,
                       "guideFrame": [p[0]-192, p[1]-128, 1536, 1024]}
                queue.write(json.dumps(job, separators=(",", ":")) + "\n")
    result = {
        "sourcePixelsPerMetre": SCALE,
        "projectedAtlas": [x0, y0, x1, y1],
        "landKm2": round(float(land.sum()) / (REGIONAL_SCALE**2 * SE * 1e6), 2),
        "coreSize": [STEP_X, STEP_Y],
        "gridCells": int(x.size),
        "landAndShoreCells": int(land_cells.sum()),
        "landAndShoreReady": int((land_cells & on_hand).sum()),
        "landAndShoreRemaining": int(remaining.sum()),
        "offshoreWaterRemaining": int((~land_cells & ~on_hand).sum()),
        "release": scene["release"],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, default=PUBLIC / "v9-native/bay/scene.json")
    parser.add_argument("--queue", type=Path, help="Write unpainted land and shore windows as gzip JSON Lines")
    args = parser.parse_args()
    plan(args.scene, args.queue)
