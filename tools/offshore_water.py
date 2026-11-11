"""Distance-based offshore color harmonization in global image coordinates."""

import numpy as np
from scipy.ndimage import distance_transform_edt

PALETTE = {
    'day': (14.,56.,83.), 'night': (11.,30.,49.),
    'rain-day': (26.,58.,72.), 'rain-night': (11.,28.,43.),
}


def water_weight(protected, near=76., far=360., pixels_per_sample=4.):
    """Keep shore, piers and construction; gradually replace distant water."""
    if not 0 <= near < far:
        raise ValueError('Water blend distances must increase')
    distance = distance_transform_edt(~protected) if protected.any() else np.full(protected.shape, np.inf)
    t = np.clip((distance*pixels_per_sample-near)/(far-near),0,1).astype('float32')
    return t*t*(3-2*t)


def harmonize(rgb, weight, appearance, origin):
    """Composite one strip with repeatable waves and no per-plate colors."""
    h,w = weight.shape
    x = (origin[0]+np.arange(w,dtype='float32'))[None,:]
    y = (origin[1]+np.arange(h,dtype='float32'))[:,None]
    tide = 1.9*np.sin(x*.0022-y*.0009)+1.1*np.cos(x*.0012+y*.0014)
    swells = np.sin(y*.142+x*.037+np.sin(x*.012-y*.027)*1.45)
    wind = np.sin(y*.284-x*.09+np.cos(x*.047+y*.036)*1.2)
    wavelets = np.maximum(0, np.sin(y*.65-x*.27+swells*1.3))**3
    highlights = wavelets*(.48+.52*np.cos(x*.37+y*.025))*(1.3+wind*.9)
    rain = 1.35*np.sin(x*.51-y*.69)*np.sin(x*.34+y*.49) if appearance.startswith('rain') else 0.
    modulation = tide + .95*swells + .48*wind + highlights + rain
    if appearance.endswith('night'):
        modulation *= .72
    sea = np.asarray(PALETTE[appearance],dtype='float32')+modulation[...,None]*[.56,.97,1.20]
    a = weight[...,None]
    return np.rint(rgb*(1-a)+sea*a).clip(0,255).astype('uint8')
