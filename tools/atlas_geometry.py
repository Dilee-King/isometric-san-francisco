"""Shared camera and immutable pixel frames for the waterfront atlas."""

from dataclasses import dataclass
import math

import numpy as np

ORIGIN_LON_LAT = (-122.3943, 37.7955)
ORIGIN_UTM = (553326.4257226175, 4183298.4609667137)
SCALE = 2.55 * 1536 / 2112
SE = math.sin(math.radians(39))
CE = math.cos(math.radians(39))
EAST = (.8, .6)
NORTH = (.6, -.8)
DEPTH_ENCODING = {'offset': 8000, 'range': 16000}


@dataclass(frozen=True)
class PixelFrame:
    key: str
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    def local(self, x, y):
        return x - self.x, y - self.y

    def contains(self, x, y):
        return self.x <= x < self.right and self.y <= y < self.bottom

    def projection(self, scale=SCALE):
        return {'scale': scale, 'origin': [-self.x, -self.y], 'sinElevation': SE,
                'cosElevation': CE, 'east': list(EAST), 'north': list(NORTH)}


FRAMES = (
    PixelFrame('wharf', -2600, -3150, 3072, 2048),
    PixelFrame('embarcadero', -1250, -1250, 3072, 2048),
    PixelFrame('south-beach', -2150, 550, 3072, 2048),
    PixelFrame('mission-bay', -3550, 2200, 3072, 2048),
)
ATLAS = PixelFrame('waterfront', -3550, -3150, 5372, 7398)
FERRY_ANCHOR = PixelFrame('ferry-anchor', -652, -671, 1536, 1024)
ART_FRAMES = (
    PixelFrame('wharf', -2600, -3150, 1536, 1024),
    PixelFrame('pier-39', -1280, -2800, 1536, 1024),
    PixelFrame('pier-27', -690, -2090, 1536, 1024),
    PixelFrame('exploratorium', -460, -1420, 1536, 1024),
    FERRY_ANCHOR,
    PixelFrame('rincon', -730, 155, 1536, 1024),
    PixelFrame('pier-30', -1270, 930, 1536, 1024),
    PixelFrame('oracle-park', -2150, 1600, 1536, 1024),
    PixelFrame('mission-rock', -2890, 2390, 1536, 1024),
    PixelFrame('mission-bay', -3400, 3080, 1536, 1024),
)


def camera_point(p, scale=SCALE):
    """Global pixel coordinates plus signed camera-depth metres."""
    x, n, z = p
    u, q = .8*x + .6*n, .6*x - .8*n
    return scale*u, scale*(q*SE-z*CE), q*CE+z*SE


def ground_point(x, y, height=0., scale=SCALE):
    """Inverse projected pixel at a specified Z, in local ENU metres."""
    u, q = x/scale, (y/scale + height*CE)/SE
    return .8*u + .6*q, .6*u - .8*q


def pack_depth(depth, structure, encoding):
    code = np.clip(np.rint((depth+encoding['offset'])/encoding['range']*65535), 0, 65535).astype('uint16')
    return np.stack((code >> 8, code & 255, structure), axis=-1).astype('uint8')


def unpack_depth(pixels, encoding):
    return (pixels[..., 0].astype('float32')*256+pixels[..., 1])/65535*encoding['range']-encoding['offset']
