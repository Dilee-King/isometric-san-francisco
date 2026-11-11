"""Make registered drawing guides for ImageGen from retained map coordinates and artwork."""

import argparse
import gzip
import json

import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import RegularGridInterpolator

from atlas_geometry import CE, SCALE, SE, PixelFrame
from city_core_geometry import CORE_FRAMES
from corridor_inputs import ROOT, local_xy
from expanded_geometry import MASK_DIVISOR, WORLD
from expanded_source import load
from expanded_tiles import LEGACY, RetainedArtwork, intersection, local_box
from golden_gate_geometry import BRIDGE_FRAME, DETAIL_FRAMES, WEST_CONTEXT

WORK = ROOT / ".local/illustrated-expansion"
MASK = ROOT / "public/map/inner-bay/masks.png"
REFERENCE_MASK = ROOT / "data/illustrated-expansion/depth-surface-mask.png"
WATER_CORRECTIONS = ROOT / "data/illustrated-expansion/east-bay-water-corrections.geojson"
APPROVED = (*DETAIL_FRAMES, *WEST_CONTEXT, *CORE_FRAMES, BRIDGE_FRAME)
SELECTED = WORK / "selected"
PUBLISHED = ROOT / "assets/illustrated-expansion/plates"


def reference_scene(version):
    snapshot = ROOT / f"data/illustrated-expansion/v{version}-routing.json.gz"
    if snapshot.is_file():
        return json.loads(gzip.decompress(snapshot.read_bytes()))
    return json.loads((ROOT / f"public/map/v{version}/waterfront/scene.json").read_text(encoding="utf-8"))


def reference_mask():
    return REFERENCE_MASK if REFERENCE_MASK.is_file() else MASK


def projected(points, frame):
    e, n, z = np.asarray(points).T
    return np.column_stack((SCALE * (.8 * e + .6 * n) - frame.x,
                            SCALE * ((.6 * e - .8 * n) * SE - z * CE) - frame.y))


def read_packed_mask():
    with Image.open(reference_mask()) as image:
        packed = np.asarray(image).copy()
    if not WATER_CORRECTIONS.is_file():
        return packed
    source = json.loads(WATER_CORRECTIONS.read_text(encoding="utf-8"))
    for feature in source["features"]:
        rings = feature["geometry"]["coordinates"]
        shape = Image.new("1", (packed.shape[1], packed.shape[0]))
        draw = ImageDraw.Draw(shape)
        for rank, ring in enumerate(rings):
            lon, lat = np.asarray(ring).T
            x, n = local_xy(lon, lat)
            pixels = projected(np.c_[x, n, np.full(len(x), 2.6)], WORLD) / MASK_DIVISOR
            draw.polygon([tuple(p) for p in pixels], fill=rank == 0)
        selected = np.asarray(shape)
        if feature["properties"]["water"]:
            packed[selected, 2] = 2
        else:
            packed[selected, 2] &= np.uint8(253)
    return packed


def crop_water(water, frame, outside=255):
    box = ((frame.x - WORLD.x) / MASK_DIVISOR, (frame.y - WORLD.y) / MASK_DIVISOR,
           (frame.right - WORLD.x) / MASK_DIVISOR, (frame.bottom - WORLD.y) / MASK_DIVISOR)
    if box[0] < 0 or box[1] < 0 or box[2] > water.width or box[3] > water.height:
        scale = 1 / MASK_DIVISOR
        return water.transform((frame.width, frame.height), Image.Transform.AFFINE,
                               (scale, 0, box[0], 0, scale, box[1]),
                               resample=Image.Resampling.NEAREST, fillcolor=outside)
    return water.resize((frame.width, frame.height), Image.Resampling.NEAREST, box=box)


class GuideSource:
    def __init__(self):
        data = load()
        self.roads = [road for road in data["roads"] if not road["tunnel"]]
        self.road_bounds = np.asarray([road["bounds"] for road in self.roads])
        self.buildings = data["buildings"]
        self.building_bounds = np.asarray([building["bounds"] for building in self.buildings])
        grid = data["terrain"]
        height = RegularGridInterpolator((grid["n"], grid["x"]), grid["z"],
                                         bounds_error=False, fill_value=2.6)
        self.parks = []
        self.park_bounds = []
        for polygon in data["greens"]:
            rings = []
            for ring in polygon:
                xy = np.asarray(ring)
                rings.append(projected(np.c_[xy, height(xy[:, ::-1])], PixelFrame("origin", 0, 0, 0, 0)))
            lo = rings[0].min(axis=0)
            hi = rings[0].max(axis=0)
            self.parks.append(rings)
            self.park_bounds.append([*lo, *hi])
        self.park_bounds = np.asarray(self.park_bounds)
        packed = read_packed_mask()
        self.water = Image.fromarray(((packed[:, :, 2] & 2) > 0).astype("uint8") * 255)
        self.legacy = RetainedArtwork()
        scene = reference_scene(8)
        self.bridge = [next(route for route in scene["routes"]
                            if route["id"] == f"bay-bridge-{side}-2-0")
                       for side in ("westbound", "eastbound")]

    def guide(self, frame):
        def visible(bounds):
            return np.flatnonzero((bounds[:, 0] < frame.right) & (bounds[:, 1] < frame.bottom)
                                  & (bounds[:, 2] >= frame.x) & (bounds[:, 3] >= frame.y))

        water = crop_water(self.water, frame)
        image = Image.new("RGB", water.size, (219, 211, 187))
        image.paste((50, 100, 123), (0, 0, frame.width, frame.height), water)
        draw = ImageDraw.Draw(image)
        for index in visible(self.park_bounds):
            for rank, ring in enumerate(self.parks[index]):
                xy = ring - [frame.x, frame.y]
                draw.polygon([tuple(p) for p in xy], fill=(151, 173, 127) if rank == 0 else (219, 211, 187))
        image.paste((50, 100, 123), (0, 0, frame.width, frame.height), water)
        for index in visible(self.road_bounds):
            road = self.roads[index]
            xy = projected(road["points"], frame)
            major = road["kind"] in ("motorway", "trunk", "primary", "secondary")
            width = max(2, round(road["width"] * SCALE * .58))
            draw.line([tuple(p) for p in xy], width=width,
                      fill=(144, 146, 133) if major else (173, 172, 154), joint="curve")
        for index in visible(self.building_bounds):
            building = self.buildings[index]
            for polygon in building["footprint"]:
                xy = np.asarray(polygon[0])
                roof = projected(np.c_[xy, np.full(len(xy), building["ground"])], frame)
                draw.polygon([tuple(p) for p in roof], fill=(189, 176, 149), outline=(167, 155, 137))
        for route in self.bridge:
            points = projected(route["points"], frame)
            hidden = set(route.get("hiddenSegments", ()))
            for index, (a, b) in enumerate(zip(points, points[1:])):
                if index not in hidden:
                    draw.line([tuple(a), tuple(b)], fill=(224, 201, 145), width=16)
        return image

    def place_anchor(self, image, frame):
        area = intersection(frame, self.legacy.frame)
        if area is None:
            return
        left, top, right, bottom = area
        anchor = Image.new("L", (right - left, bottom - top))
        draw = ImageDraw.Draw(anchor)
        for old in APPROVED:
            overlap = intersection(old, frame)
            if overlap is not None:
                x0, y0, x1, y1 = overlap
                draw.rectangle((x0 - left, y0 - top, x1 - left - 1, y1 - top - 1), fill=255)
        if anchor.getbbox():
            image.paste(self.legacy.crop("scene", area), (left - frame.x, top - frame.y), anchor)


def place_extensions(image, frame, row, rows):
    anchors = []
    for previous in rows:
        if previous["stage"] > row["stage"] or previous["wave"] >= row["wave"] or previous["kind"] != "area":
            continue
        path = PUBLISHED / f"{previous['id']}.png"
        if not path.is_file():
            path = SELECTED / path.name
        if not path.is_file():
            continue
        neighbor = PixelFrame(previous["id"], *previous["frame"])
        area = intersection(frame, neighbor)
        if area is None:
            continue
        with Image.open(path) as prior:
            size = (area[2] - area[0], area[3] - area[1])
            box = local_box(neighbor, area)
            sx, sy = prior.width / neighbor.width, prior.height / neighbor.height
            crop = prior.resize(size, Image.Resampling.LANCZOS,
                                box=(box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy))
            image.paste(crop, local_box(frame, area)[:2])
        anchors.append(previous["id"])
    return anchors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame", nargs=5, action="append", default=[],
                        metavar=("KEY", "X", "Y", "WIDTH", "HEIGHT"))
    parser.add_argument("--ids", nargs="+")
    args = parser.parse_args()
    output = WORK / "guides"
    output.mkdir(parents=True, exist_ok=True)
    source = GuideSource()
    rows = json.loads((ROOT / "assets/illustrated-expansion/layout.json").read_text(encoding="utf-8"))["frames"] if args.ids else []
    targets = [{"id": key, "frame": list(map(int, values)), "stage": 8, "wave": 0}
               for key, *values in args.frame]
    if args.ids:
        targets.extend(row for row in rows if row["id"] in args.ids)
    if not targets:
        parser.error("No matching frames")
    for row in targets:
        frame = PixelFrame(row["id"], *row["frame"])
        image = source.guide(frame)
        anchors = place_extensions(image, frame, row, rows)
        source.place_anchor(image, frame)
        image.save(output / f"{frame.key}.png", compress_level=3)
        (output / f"{frame.key}.json").write_text(json.dumps(anchors) + "\n", encoding="utf-8")
        print(frame.key, len(anchors), flush=True)


if __name__ == "__main__":
    main()
