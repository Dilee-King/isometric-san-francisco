import math
import unittest

import numpy as np

from atlas_geometry import ATLAS, FRAMES, ART_FRAMES, DEPTH_ENCODING, camera_point, ground_point, pack_depth, unpack_depth


class AtlasGeometryTest(unittest.TestCase):
    def test_all_production_frames_share_one_camera(self):
        p = (102.5, -1802.3, 18.6)
        gx, gy, depth = camera_point(p)
        for frame in FRAMES:
            lx, ly = frame.local(gx, gy)
            self.assertAlmostEqual(gx, lx + frame.x)
            self.assertAlmostEqual(gy, ly + frame.y)
        self.assertAlmostEqual(ATLAS.local(gx, gy)[0], gx - ATLAS.x)
        self.assertGreater(depth, 1000)

    def test_ground_inverse_preserves_metre_axes(self):
        for p in [(-2227, 1351, 3), (53, 0, 3), (726, -3346, 3)]:
            x, y, _ = camera_point(p)
            e, n = ground_point(x, y, p[2])
            self.assertAlmostEqual(e, p[0], places=8)
            self.assertAlmostEqual(n, p[1], places=8)

    def test_continuous_coverage_between_both_waterfront_endpoints(self):
        path = [(-1801, -2825), (-484, -2356), (239, -1520), (313, -858), (79, 32),
                (78, 966), (-259, 1598), (-1399, 2067), (-2055, 2953), (-2447, 3286), (-2646, 3628)]
        for a, b in zip(path, path[1:]):
            for t in np.linspace(0, 1, 41):
                x, y = (a[i] + (b[i] - a[i]) * t for i in (0, 1))
                self.assertTrue(any(f.contains(x, y) for f in ART_FRAMES), (x, y))

    def test_packed_depth_distinguishes_southern_structures(self):
        samples = np.array([[-4700., -12., 0.], [1800., 2775., 3110.]])
        structure = np.array([[0, 0, 0], [255, 255, 0]], dtype='uint8')
        packed = pack_depth(samples, structure, DEPTH_ENCODING)
        np.testing.assert_array_equal(packed[:, :, 2], structure)
        np.testing.assert_allclose(unpack_depth(packed, DEPTH_ENCODING), samples, atol=.13, rtol=0)
        self.assertLess(math.ceil(ATLAS.height / 4), 2048)


if __name__ == '__main__':
    unittest.main()
