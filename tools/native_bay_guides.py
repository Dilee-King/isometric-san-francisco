"""Prepare native-scale ImageGen guides at the named full-Bay close-ups."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import math

import numpy as np
from PIL import Image

from atlas_geometry import ORIGIN_UTM, SCALE, PixelFrame, camera_point, ground_point
from bay_illustration_guides import AREA_SCALE, FRAME, NAIP, REGIONAL_SCALE, placements, source_bounds, source_raster
from corridor_inputs import ROOT, TO_GEO, fetch, local_xy, sha

WORK = ROOT / ".local/native-bay"
ART = ROOT / "assets/native-bay"
RATIO = SCALE / REGIONAL_SCALE
ALIGN = 4096
X0 = math.floor(FRAME.x * RATIO / ALIGN) * ALIGN
Y0 = math.floor(FRAME.y * RATIO / ALIGN) * ALIGN
X1 = math.ceil(FRAME.right * RATIO / ALIGN) * ALIGN
Y1 = math.ceil(FRAME.bottom * RATIO / ALIGN) * ALIGN
WORLD = PixelFrame("native-bay", X0, Y0, X1-X0, Y1-Y0)

# Focus points in the registered v0.9 aerial guides, before conversion to native pixels.
FOCUS = {
    "sfo": ((537, 528), "SFO Terminal"),
    "san-mateo-bridge": ((511, 421), "Foster City & San Mateo Bridge"),
    "redwood-shores": ((721, 352), "Redwood Shores"),
    "dumbarton-bridge": ((470, 551), "Dumbarton Bridge west landing"),
    "alviso": ((715, 721), "Alviso Village & salt ponds"),
    "san-jose": ((825, 851), "Downtown San Jose"),
    "oakland-airport": ((675, 734), "Oakland Airport Terminal"),
    "berkeley-marina": ((808, 355), "Berkeley Marina"),
    "richmond-bridge": ((841, 451), "Richmond Bridge east landing"),
    "san-rafael": ((995, 566), "San Rafael Canal"),
    "vallejo": ((957, 669), "Vallejo & Mare Island Strait"),
    "benicia-martinez": ((935, 433), "Benicia–Martinez Bridge north landing"),
    "napa": ((786, 533), "Downtown Napa & Napa River"),
    "petaluma": ((792, 535), "Downtown Petaluma"),
    "half-moon-bay": ((920, 285), "Pillar Point Harbor"),
}


def detail_rows():
    rows = []
    for row in placements():
        if row["kind"] != "detail":
            continue
        identity = row["id"].removeprefix("detail-")
        if identity == "point-reyes":
            # NPS: https://www.nps.gov/places/point-reyes-lighthouse.htm
            x, y, _ = camera_point((*local_xy(-123.0232, 37.9956), 0))
            name = "Point Reyes Lighthouse"
        else:
            (u, v), name = FOCUS[identity]
            left, top, _, _ = row["frame"]
            x = (left + u + FRAME.x * 8) * SCALE / AREA_SCALE
            y = (top + v + FRAME.y * 8) * SCALE / AREA_SCALE
        x0 = round(x - 768)
        y0 = round(y - 512)
        e, n = ground_point(x0 + 768, y0 + 512)
        rows.append({"id": identity, "name": name,
                     "frame": [x0-WORLD.x, y0-WORLD.y, 1536, 1024],
                     "p": [e, n, 0], "lonLat": list(TO_GEO.transform(e+ORIGIN_UTM[0], n+ORIGIN_UTM[1]))})
    return rows


def guide(row, size, *, work=WORK):
    left, top, width, height = row["frame"]
    frame = PixelFrame(row["id"], left+WORLD.x, top+WORLD.y, width, height)
    bounds, _ = source_bounds(frame, SCALE)
    w, s, e, n = bounds
    density = min(1.62, size / max(e-w, n-s))
    source = fetch(NAIP, f"{row['id']}-{left}-{top}-{size}.tif", {
        "bbox": ",".join(str(value) for value in bounds),
        "bboxSR": "32610", "imageSR": "32610",
        "size": f"{round((e-w)*density)},{round((n-s)*density)}",
        "format": "tiff", "interpolation": "RSP_BilinearInterpolation", "f": "image",
    }, cache=work / "aerial")
    pixels = np.stack(source_raster(source, frame, SCALE, (1, 2, 3)), axis=-1).astype("uint8")
    destination = work / "guides" / row["id"]
    Image.fromarray(pixels).save(destination.with_suffix(".png"))
    destination.with_suffix(".sha256").write_text(sha(source) + "\n", encoding="ascii")
    return row["id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--size", type=int, default=1900)
    args = parser.parse_args()
    (WORK / "guides").mkdir(parents=True, exist_ok=True)
    rows = [row for row in detail_rows() if not args.ids or row["id"] in args.ids]
    failures = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        tasks = {pool.submit(guide, row, args.size): row["id"] for row in rows}
        for task in as_completed(tasks):
            try:
                print(task.result(), flush=True)
            except (OSError, ValueError) as error:
                failures.append(tasks[task])
                print(f"{tasks[task]}: {error}", flush=True)
    if failures:
        raise SystemExit(f"Unavailable aerial guides: {', '.join(failures)}")


if __name__ == "__main__":
    main()
