"""Acceptance checks for the continuous western corridor and offshore compositing."""

import math
import unittest

import numpy as np

from atlas_geometry import SCALE, camera_point
from golden_gate_geometry import ATLAS, BRIDGE_FRAME, DETAIL_FRAMES, LANDMARKS, BridgeProfile
from offshore_water import water_weight, harmonize
from paint_golden_gate import BridgeRaster, paint
from render_corridor import point


class GoldenGateTest(unittest.TestCase):
    def test_continuous_native_scale_from_wharf_to_fort_point(self):
        path = [(-1801,-2832), (-2424,-2986), (-3715,-3453), (-4607,-3859),
                (-6041,-4351), (-6363,-4645), (-6994,-4713), (-7600,-5250),
                (-8366,-5985), (-9001,-6649)]
        self.assertEqual(ATLAS.projection()['scale'], SCALE)
        for a,b in zip(path,path[1:]):
            for t in np.linspace(0,1,73):
                x,y = (a[i]+(b[i]-a[i])*t for i in (0,1))
                self.assertTrue(any(f.contains(x,y) for f in DETAIL_FRAMES),(x,y))
        self.assertTrue(all(ATLAS.contains(f.x,f.y) and ATLAS.contains(f.right-1,f.bottom-1)
                            for f in (*DETAIL_FRAMES, BRIDGE_FRAME)))
        self.assertIn('golden-gate-bridge', {key for key,*_ in LANDMARKS})

    def test_towers_bridge_deck_and_route_share_the_same_camera(self):
        profile = BridgeProfile()
        self.assertAlmostEqual(math.dist(profile.point(0), profile.point(1280)), 1280., places=3)
        self.assertEqual(profile.deck(640), 82.0)
        for station in (0,1280):
            x,y,_ = camera_point(profile.point(station,z=227))
            self.assertTrue(BRIDGE_FRAME.contains(x,y), (station,x,y))
        for station in np.linspace(-343,1623,71):
            self.assertGreater(profile.cable(station),profile.deck(station))
        self.assertTrue(all(-9 < lane < 9 for lane in profile.lanes))

    def test_changing_far_water_art_cannot_reveal_panel_edges(self):
        land = np.zeros((210,256), dtype=bool)
        land[:, :30] = True
        land[90:120, 30:63] = True  # pier
        blend = water_weight(land, near=17, far=83, pixels_per_sample=1)
        a = np.full((210,256,3),[24,68,86],dtype='uint8')
        b = a.copy()
        b[40:170,155:230] = [55,117,144]  # artificial rectilinear plate seam
        np.testing.assert_array_equal(harmonize(a,blend,'day',(300,700)),
                                      harmonize(b,blend,'day',(300,700)))
        np.testing.assert_array_equal(harmonize(a,blend,'day',(300,700))[land],a[land])
        self.assertEqual(blend[99,67],0)
        self.assertTrue(0 < blend[99,112] < 1)
        self.assertEqual(blend[99,180],1)

    def test_water_ripple_field_matches_across_chunk_boundaries(self):
        rgb = np.zeros((38,64,3),dtype='uint8')
        blend = np.ones((38,64),dtype='float32')
        for appearance in ('day','night','rain-day','rain-night'):
            complete = harmonize(rgb,blend,appearance,(-70,-320))
            cropped = harmonize(rgb[9:27,17:55],blend[9:27,17:55],appearance,(-53,-311))
            np.testing.assert_array_equal(complete[9:27,17:55],cropped)

    def test_bridge_depth_has_an_unbroken_deck_through_both_approaches(self):
        profile=BridgeProfile()
        raster=BridgeRaster(BRIDGE_FRAME,4)
        paint(raster)
        for station in np.linspace(profile.approach_start+9,profile.approach_end-9,235):
            x,y,z=point(profile.point(station),BRIDGE_FRAME,raster.divisor)
            i,j=round(y),round(x)
            self.assertTrue(raster.occupied[i,j],station)
            self.assertGreaterEqual(raster.depth[i,j],z-4.5,station)


if __name__ == '__main__':
    unittest.main()
