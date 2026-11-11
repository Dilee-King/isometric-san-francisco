"""Render native city blocks and exact landmark art references."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw
from shapely.affinity import affine_transform
from shapely.geometry import box
from shapely.ops import unary_union

from atlas_geometry import CE, SE, SCALE, PixelFrame, camera_point, pack_depth
from corridor_inputs import ROOT, sha
from expanded_bridge import BayBridge
from expanded_geometry import BLOCK, DEPTH_ENCODING, HALO, MASK_DIVISOR, WORLD, art_frames
from expanded_source import SNAPSHOT, load
from golden_gate_geometry import BRIDGE_FRAME, DETAIL_FRAMES
from golden_gate_lighting import lamps_for
from city_core_geometry import CORE_ART
from render_corridor import good_polygon, projected
from render_golden_gate import WestRaster

WORK = ROOT / ".local/inner-bay-render"
REFERENCE = WORK / "references"
LEGACY_FRAMES = (*DETAIL_FRAMES, *CORE_ART, BRIDGE_FRAME)
CONTEXT_ROADS = {"motorway", "motorway_link", "trunk", "primary", "secondary"}
DATA = None


def geometry(rings):
    return unary_union([good_polygon(polygon) for polygon in rings])


def projection_shape(geometry):
    return affine_transform(geometry, [.8 * SCALE, .6 * SCALE,
                                       .6 * SCALE * SE, -.8 * SCALE * SE, 0, -2.6 * CE * SCALE])


def frame_box(frame):
    return box(frame.x, frame.y, frame.right, frame.bottom)


def block_frame(column, row):
    return PixelFrame(f"{column}_{row}", WORLD.x + column * BLOCK, WORLD.y + row * BLOCK, BLOCK, BLOCK)


def padded(frame, halo=HALO):
    return PixelFrame(frame.key, frame.x - halo, frame.y - halo,
                      frame.width + 2 * halo, frame.height + 2 * halo)


def blocks():
    for row in range(WORLD.height // BLOCK):
        for column in range(WORLD.width // BLOCK):
            yield block_frame(column, row)


def coverages(data, bridge):
    land = {int(key): projection_shape(geometry(rings)).buffer(300)
            for key, rings in data["coverage"].items()}
    land[6] = unary_union([land[6], *bridge.coverage(), *(frame_box(frame) for frame in LEGACY_FRAMES)])
    for frame in art_frames():
        version = 7 if frame.key in ("oakland-port", "jack-london", "alameda-main") else (
            8 if frame.key in ("fort-baker", "sausalito") else 6
        )
        land[version] = land[version].union(frame_box(frame))
    return land


def region_blocks(data, bridge):
    coverage = coverages(data, bridge)
    region = {}
    for frame in blocks():
        box = frame_box(frame)
        if coverage[6].intersects(box):
            x = frame.x + BLOCK / 2
            if x > 5100:
                name = "bay-bridge"
            elif x > -2200:
                name = "east-san-francisco"
            elif x > -12900:
                name = "central-san-francisco"
            else:
                name = "west-san-francisco"
            region[frame.key] = [6, name]
        elif coverage[7].intersects(box):
            region[frame.key] = [7, "east-bay-waterfront"]
        elif coverage[8].intersects(box):
            region[frame.key] = [8, "sausalito-shore"]
    return region


def crossing_road(road):
    return road["kind"] == "motorway" and "I 80" in road["ref"].split(";") and (
        road["bridge"] or road["tunnel"] or road["name"] == "Dwight D. Eisenhower Highway"
    )


class RenderSource:
    def __init__(self, include_bridge):
        self.data = load()
        self.signature = hashlib.sha256("".join(sha(path) for path in (
            SNAPSHOT, ROOT / "tools/expanded_render.py", ROOT / "tools/expanded_bridge.py",
            ROOT / "tools/expanded_geometry.py", ROOT / "tools/render_corridor.py",
            ROOT / "tools/render_golden_gate.py",
        )).encode()).hexdigest()
        self.data["terrain"]["z"] = np.asarray(self.data["terrain"]["z"], dtype="float32")
        self.bridge = BayBridge(self.data["roads"]) if include_bridge else None
        self.roads = [road for road in self.data["roads"] if not self.bridge or not crossing_road(road)]
        self.buildings = self.data["buildings"]
        self.road_bounds = np.asarray([road["bounds"] for road in self.roads])
        self.building_bounds = np.asarray([building["bounds"] for building in self.buildings])
        self.trees = np.asarray(self.data["trees"])
        self.tree_positions = projected(np.c_[self.trees[:, :2], self.trees[:, 3] + self.trees[:, 2] * .65], WORLD)[0]

    def crop(self, frame, coarse=False):
        def intersect(bounds, padding):
            return np.flatnonzero((bounds[:, 2] >= frame.x - padding) & (bounds[:, 0] < frame.right + padding)
                                  & (bounds[:, 3] >= frame.y - padding) & (bounds[:, 1] < frame.bottom + padding))

        roads = [self.roads[index] for index in intersect(self.road_bounds, 45)
                 if not coarse or self.roads[index]["kind"] in CONTEXT_ROADS]
        buildings = [] if coarse else [self.buildings[index] for index in intersect(self.building_bounds, 18)]
        trees = []
        if not coarse:
            xy = self.tree_positions
            lo, up = WORLD.local(frame.x - 14, frame.y - 14), WORLD.local(frame.right + 14, frame.bottom + 14)
            keep = (xy[:, 0] >= lo[0]) & (xy[:, 0] < up[0]) & (xy[:, 1] >= lo[1]) & (xy[:, 1] < up[1])
            trees = self.trees[keep].tolist()
        return {**self.data, "roads": roads, "buildings": buildings, "trees": trees}


def init_render(include_bridge):
    global DATA
    DATA = RenderSource(include_bridge)


def ocean(frame, divisor, shape):
    h, w = shape
    x = (frame.x + np.arange(w, dtype="float32") * divisor)[None, :]
    y = (frame.y + np.arange(h, dtype="float32") * divisor)[:, None]
    swell = np.sin(x * .006 + y * .032 + np.sin(y * .012))
    ripple = np.sin(x * .066 - y * .22 + swell * 1.2) * .44 + np.cos(x * .157 + y * .39) * .14
    texture = swell * .31 + ripple
    return np.clip(np.stack((17 + texture * 3, 64 + texture * 5, 95 + texture * 6), axis=-1), 0, 255).astype("uint8")


def material(raster, image):
    rgb = np.asarray(image, dtype="uint8").copy()
    # A geographic sand surface remains registered to the projected coast.
    sand = Image.new("1", image.size)
    draw = ImageDraw.Draw(sand)
    for polygon in DATA.data["beaches"]:
        for index, ring in enumerate(polygon):
            xy, _ = projected([[*point, 2.6] for point in ring], raster.frame, raster.divisor)
            draw.polygon([tuple(point) for point in xy], fill=index == 0)
    sand = np.asarray(sand) & raster.land & (raster.structure == 0) & (rgb[:, :, 0] > 145)
    rgb[sand] = (216, 198, 162)
    x = (raster.frame.x + np.arange(raster.w) * raster.divisor)[None, :]
    y = (raster.frame.y + np.arange(raster.h) * raster.divisor)[:, None]
    grain = ((x * 61 + y * 37 + (x ^ y) * 13) % 11 - 5).astype("int16")
    for channel in range(3):
        rgb[:, :, channel] = (rgb[:, :, channel].astype("int16") + grain).clip(0, 255)
    rgb[~raster.land] = ocean(raster.frame, raster.divisor, raster.land.shape)[~raster.land]
    return Image.fromarray(rgb)


def render(frame, divisor, coarse=False):
    source = DATA.crop(frame, coarse)
    raster = WestRaster(source, frame, divisor)
    image = raster.draw(source)
    if DATA.bridge:
        original = np.asarray(image)
        raster.rgb = original.copy()
        DATA.bridge.draw(raster)
        if divisor == 1:
            raster.bridge_pixels = np.any(raster.rgb != original, axis=-1)
        image = Image.fromarray(raster.rgb)
    return raster, material(raster, image), source


def save_appearance_inputs(folder, frame, raster, image):
    folder.mkdir(parents=True, exist_ok=True)
    image.save(folder / f"{frame.key}-day.png", compress_level=2)
    Image.fromarray(raster.hard.astype("uint8") * 255).save(folder / f"{frame.key}-hard.png")
    Image.fromarray((~raster.land).astype("uint8") * 255).save(folder / f"{frame.key}-water.png")
    (folder / f"{frame.key}-windows.json").write_text(
        json.dumps(raster.visible_windows, separators=(",", ":")), encoding="utf-8",
    )


def reference(frame):
    # Project the ground from a halo before cropping to the exact art frame.
    margin = 480
    extended = padded(frame, margin)
    raster, image, source = render(extended, 1)
    crop = (margin, margin, margin + frame.width, margin + frame.height)
    REFERENCE.mkdir(parents=True, exist_ok=True)
    image.crop(crop).save(REFERENCE / f"{frame.key}-reference.png", compress_level=3)
    Image.fromarray((~raster.land).astype("uint8") * 255).crop(crop).save(REFERENCE / f"{frame.key}-water.png")
    print(f"Reference {frame.key}: {len(source['buildings']):,} footprints", flush=True)


def mask_pixels(raster, frame, divisor):
    start = (HALO + MASK_DIVISOR // 2) // divisor
    stride = MASK_DIVISOR // divisor
    end = start + frame.height // MASK_DIVISOR * stride
    right = start + frame.width // MASK_DIVISOR * stride
    area = np.s_[start:end:stride, start:right:stride]
    flags = ((raster.structure[area] > 0).astype("uint8") << 7
             | (~raster.land[area]).astype("uint8") << 1
             | raster.hard[area].astype("uint8"))
    return Image.fromarray(pack_depth(raster.depth[area], flags, DEPTH_ENCODING))


def block(frame, divisor):
    extended = padded(frame)
    folder = WORK / ("native" if divisor == 1 else "context") / frame.key
    marker = folder / "complete"
    if marker.is_file() and marker.read_text(encoding="ascii").strip() == DATA.signature:
        return
    raster, image, source = render(extended, divisor, coarse=divisor != 1)
    save_appearance_inputs(folder, frame, raster, image)
    lamps = lamps_for(source, ("Street", "Avenue", "Boulevard", "Road", "Drive", "Bridgeway", "Way"))
    if DATA.bridge:
        lamps.extend(point for point in DATA.bridge.lamps if extended.contains(*camera_point(point)[:2]))
    (folder / "lamps.json").write_text(json.dumps(lamps, separators=(",", ":")), encoding="utf-8")
    if divisor == 1:
        Image.fromarray(raster.bridge_pixels.astype("uint8") * 255).save(folder / "bridge.png")
    mask_pixels(raster, frame, divisor).save(folder / "mask.png", compress_level=2)
    marker.write_text(DATA.signature + "\n", encoding="ascii")
    print(f"{'Native' if divisor == 1 else 'Context'} {frame.key}: {len(source['buildings']):,} buildings", flush=True)


def native(frame):
    block(frame, 1)


def context(frame):
    block(frame, 4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("references", "native", "context"))
    parser.add_argument("keys", nargs="*")
    parser.add_argument("--jobs", type=int, default=5)
    args = parser.parse_args()
    if args.stage == "references":
        frames, operation = art_frames(), reference
    else:
        source = load()
        bridge = BayBridge(source["roads"])
        active = region_blocks(source, bridge)
        WORK.mkdir(parents=True, exist_ok=True)
        (WORK / "blocks.json").write_text(json.dumps(active, indent=2) + "\n", encoding="utf-8")
        frames = [frame for frame in blocks() if args.stage == "context" or frame.key in active]
        operation = native if args.stage == "native" else context
        del source, bridge
    frames = [frame for frame in frames if not args.keys or frame.key in args.keys]
    if not frames:
        parser.error("No matching frames")
    with ProcessPoolExecutor(max_workers=args.jobs, initializer=init_render,
                             initargs=(args.stage != "references",)) as pool:
        list(pool.map(operation, frames))


if __name__ == "__main__":
    main()
