"""Render georeferenced western art targets and inspectable reference layers."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json

import numpy as np
from scipy.ndimage import map_coordinates
from PIL import Image

from atlas_geometry import CE, SE, SCALE
from corridor_inputs import ROOT
from golden_gate_geometry import WEST_ART, WEST_CONTEXT
from golden_gate_source import load
from render_corridor import Raster, projected

WORK = ROOT/'.local/golden-gate-frames'


class WestRaster(Raster):
    """Project terrain relief in the same vertical image axis as structures."""

    def __init__(self,data,frame,divisor=1):
        super().__init__(data,frame,divisor)
        y,x=np.indices(self.height.shape,dtype='float32')
        height=np.maximum(0,self.height)
        offset=height*0
        for _ in range(8):
            z=map_coordinates(height,[y+offset,x],order=1,mode='nearest')
            offset=.37*offset+.63*(z-2.6)*(SCALE*CE/divisor)
        ry=np.clip(np.rint(y+offset).astype('int32'),0,self.h-1)
        rx=np.arange(self.w)[None,:]
        self.land=self.land[ry,rx]
        self.green=self.green[ry,rx]
        self.hard=self.hard[ry,rx]
        self.rgb=self.rgb[ry,rx]
        self.height=self.height[ry,rx]
        self.depth=((frame.y+y*divisor)/SCALE*CE/SE + self.height/SE).astype('float32')


def intersects(points, frame, margin=5):
    xy,_=projected(points,frame)
    lo,hi=xy.min(axis=0),xy.max(axis=0)
    return (hi[0]>=-margin and lo[0]<=frame.width+margin
            and hi[1]>=-margin and lo[1]<=frame.height+margin)


def crop_source(data,frame):
    roads=[r for r in data['roads'] if intersects(r['points'],frame,24)]
    buildings=[b for b in data['buildings'] if any(
        intersects([[*p,b['ground']+b['height']] for p in poly[0]],frame,28+b['height']*SCALE*CE)
        for poly in b['footprint'])]
    trees=data['trees']
    projected_trees,_=projected([[x,n,g+h*.65] for x,n,h,g in trees],frame)
    keep=(projected_trees[:,0]>=-10)&(projected_trees[:,0]<frame.width+10)&(
          projected_trees[:,1]>=-10)&(projected_trees[:,1]<frame.height+10)
    return {**data,'roads':roads,'buildings':buildings,'trees':[trees[i] for i in np.flatnonzero(keep)]}


def render_frame(frame):
    data=crop_source(load(),frame)
    r=WestRaster(data,frame,frame.width//1536)
    im=r.draw(data)
    im.save(WORK/f'{frame.key}-reference.png',compress_level=3)
    Image.fromarray(r.hard.astype('uint8')*255).save(WORK/f'{frame.key}-hard.png')
    Image.fromarray((~r.land).astype('uint8')*255).save(WORK/f'{frame.key}-water.png')
    (WORK/f'{frame.key}-windows.json').write_text(json.dumps(r.visible_windows,separators=(',',':')),encoding='utf-8')
    print(frame.key,len(data['buildings']),len(data['roads']),im.size,flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('keys',nargs='*')
    p.add_argument('--jobs',type=int,default=4)
    args=p.parse_args()
    all_frames=(*WEST_ART,*WEST_CONTEXT)
    frames=[f for f in all_frames if not args.keys or f.key in args.keys]
    if not frames or set(args.keys)-{f.key for f in frames}:
        p.error('Unknown art frame')
    WORK.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(render_frame,frames))


if __name__=='__main__':
    main()
