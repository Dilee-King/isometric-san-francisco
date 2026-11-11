"""Render native city references and depth using the published map camera."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import math

import numpy as np
from PIL import Image

from city_core_geometry import CORE_FRAMES
from city_core_source import load
from corridor_inputs import ROOT, local_xy
from render_golden_gate import WestRaster, crop_source

WORK = ROOT / ".local/city-core-frames"


class CoreRaster(WestRaster):
    def draw(self, data):
        ordinary = [building for building in data["buildings"] if not building.get("renderKind")]
        canvas = super().draw({**data, "buildings": ordinary})
        self.rgb = np.array(canvas)
        for building in data["buildings"]:
            kind = building.get("renderKind")
            if kind == "pyramid":
                self.pyramid(building)
            elif kind == "tower":
                self.tower(building)
        return Image.fromarray(self.rgb)

    def pyramid(self, building):
        ring = np.array(building["footprint"][0][0])
        center = (ring[:, :2].min(axis=0) + ring[:, :2].max(axis=0)) / 2
        # The footprint and lidar upper envelope locate the tapering reference.
        ground = building["ground"]
        top = ground + building["height"]
        from render_corridor import good_polygon

        rectangle = good_polygon(building["footprint"][0]).minimum_rotated_rectangle
        base = list(rectangle.exterior.coords)[:-1]
        for i, (a, b) in enumerate(zip(base, base[1:] + base[:1])):
            self.face(
                [[*a, ground], [*b, ground], [*b, ground + 10], [*a, ground + 10]],
                [170, 165, 150], building=True,
            )
            self.face(
                [[*a, ground + 10], [*b, ground + 10], [*center, top]],
                ([187, 185, 168], [153, 161, 158], [174, 179, 165], [201, 199, 180])[i],
                building=True,
            )
            for floor in np.arange(18, building["height"] - 6, 6.1):
                ratio = 1 - (floor - 10) / (building["height"] - 10)
                left = center + (np.array(a) - center) * ratio
                right = center + (np.array(b) - center) * ratio
                for u in np.linspace(0.12, 0.88, 7):
                    pos = left * (1 - u) + right * u
                    self.face(
                        [[pos[0] - .48, pos[1], ground + floor],
                         [pos[0] + .48, pos[1], ground + floor],
                         [pos[0] + .48, pos[1], ground + floor + 1.5],
                         [pos[0] - .48, pos[1], ground + floor + 1.5]],
                        [61, 87, 98], building=True,
                    )

    def tower(self, building):
        center = local_xy(-122.40583, 37.80240)
        ground = building["ground"]
        height = building["height"]
        angles = np.linspace(0, 2 * math.pi, 25)
        for a, b in zip(angles, angles[1:]):
            p = [float(center[0] + 7.6 * math.cos(a)), float(center[1] + 7.6 * math.sin(a))]
            q = [float(center[0] + 7.6 * math.cos(b)), float(center[1] + 7.6 * math.sin(b))]
            brightness = int(191 + 23 * math.cos(a + .8))
            self.face(
                [[*p, ground], [*q, ground], [*q, ground + height], [*p, ground + height]],
                [brightness, brightness - 4, brightness - 17], building=True,
            )
            if math.sin(a) < .45:
                self.face(
                    [[*p, ground + height - 7], [*q, ground + height - 7],
                     [*q, ground + height - 2], [*p, ground + height - 2]],
                    [64, 83, 89], building=True,
                )
        roof = [
            [float(center[0] + 7.8 * math.cos(a)),
             float(center[1] + 7.8 * math.sin(a)), ground + height + .25]
            for a in angles
        ]
        self.face(roof, [211, 205, 185], building=True)


def render_frame(frame):
    data = crop_source(load(), frame)
    raster = CoreRaster(data, frame, frame.width / 1536)
    canvas = raster.draw(data)
    canvas.save(WORK / f"{frame.key}-reference.png", compress_level=3)
    Image.fromarray(raster.hard.astype("uint8") * 255).save(WORK / f"{frame.key}-hard.png")
    Image.fromarray((~raster.land).astype("uint8") * 255).save(WORK / f"{frame.key}-water.png")
    (WORK / f"{frame.key}-windows.json").write_text(
        json.dumps(raster.visible_windows, separators=(",", ":")), encoding="utf-8",
    )
    print(frame.key, len(data["buildings"]), len(data["roads"]), canvas.size, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames", nargs="*")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    frames = [frame for frame in CORE_FRAMES if not args.frames or frame.key in args.frames]
    if not frames or set(args.frames) - {frame.key for frame in frames}:
        parser.error("Unknown reference frame")
    WORK.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(render_frame, frames))


if __name__ == "__main__":
    main()
