"""Check the city corridor and source-tile reconstruction at region boundaries."""

import math
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from atlas_geometry import ART_FRAMES
from city_core_geometry import CORE_ART
from regional_tiles import layout, read_native, region_for_tile


class CityCoreTest(unittest.TestCase):
    def test_main_route_and_union_square_have_continuous_native_coverage(self):
        path = [
            (79, 5), (-490, -170), (-1366, -228), (-1590, -632),
            (-1604, -748), (-1307, -1009), (-1431, -1561),
            (-1800, -2010), (-1801, -2832),
        ]
        south_branch = [(-1590, -632), (-2091, -213), (-2642, -71), (-3107, 266)]
        frames = (*CORE_ART, *ART_FRAMES)
        for branch in (path, south_branch):
            for start, end in zip(branch, branch[1:]):
                for t in np.linspace(0, 1, 81):
                    x, y = (start[i] + t * (end[i] - start[i]) for i in (0, 1))
                    self.assertTrue(any(frame.contains(x, y) for frame in frames), (x, y))
        self.assertTrue(all((frame.width, frame.height) == (1536, 1024) for frame in CORE_ART))

    def test_region_routing_uses_partial_tile_centers(self):
        config = layout()
        config["regions"] = [{"id": "edge", "bounds": [12288, 0, 12520, 14408]}]
        self.assertEqual(region_for_tile(config, 12722, 14408, 14, 24, 0), "edge")
        self.assertEqual(region_for_tile(config, 12722, 14408, 11, 0, 0), "overview")

    def test_native_reassembly_retains_pixels_across_tile_overlap(self):
        width, height = 819, 619
        y, x = np.indices((height, width))
        pixels = np.stack((x % 256, y % 256, (x + y) % 256), axis=-1).astype("uint8")
        source = Image.fromarray(pixels)
        level = math.ceil(math.log2(max(width, height)))
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            folder = root / "scene_files" / str(level)
            folder.mkdir(parents=True)
            for row in range(math.ceil(height / 512)):
                for column in range(math.ceil(width / 512)):
                    box = (
                        max(0, column * 512 - 1), max(0, row * 512 - 1),
                        min(width, (column + 1) * 512 + 1), min(height, (row + 1) * 512 + 1),
                    )
                    source.crop(box).save(folder / f"{column}_{row}.webp", lossless=True)
            rebuilt = read_native(root, "scene", width, height)
            np.testing.assert_array_equal(np.asarray(rebuilt), pixels)


if __name__ == "__main__":
    unittest.main()
