"""Offline source reference rasterizer; all frames share the published camera."""

import argparse
import gzip
import json
import math
from pathlib import Path
import zlib

import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import RegularGridInterpolator
from shapely import make_valid
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from atlas_geometry import ATLAS, FRAMES, CE, SE, SCALE, DEPTH_ENCODING, pack_depth

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.local/corridor-frames'
SOURCE = ROOT / 'data/corridor/source.json.gz'


def projected(points, frame, divisor=1):
    p = np.asarray(points, dtype='float64')
    q = .6*p[:,0]-.8*p[:,1]
    return (np.column_stack((SCALE*(.8*p[:,0]+.6*p[:,1])-frame.x,
                             SCALE*(q*SE-p[:,2]*CE)-frame.y))/divisor, q*CE+p[:,2]*SE)


def good_polygon(rings):
    p = Polygon(rings[0], rings[1:])
    return p if p.is_valid else make_valid(p)


def load_data():
    return json.loads(gzip.decompress(SOURCE.read_bytes()))


def ground_texture(data, frame, divisor):
    w,h = math.ceil(frame.width/divisor),math.ceil(frame.height/divisor)
    land_img, green_img = Image.new('L',(w,h)), Image.new('L',(w,h))
    def draw_polygons(image, polygons, height):
        draw = ImageDraw.Draw(image)
        for polygon in polygons:
            for i,ring in enumerate(polygon):
                xy,_ = projected([[*p,height] for p in ring],frame,divisor)
                draw.polygon([tuple(p) for p in xy],fill=255 if i==0 else 0)
    draw_polygons(land_img,data['land'],2.6)
    draw_polygons(green_img,data['greens'],2.8)
    land,green = np.asarray(land_img)>0,np.asarray(green_img)>0
    x = (frame.x+np.arange(w,dtype='float32')*divisor)[None,:]
    y = (frame.y+np.arange(h,dtype='float32')*divisor)[:,None]
    u, q = x/SCALE, (y/SCALE+2.6*CE)/SE
    gx,gn = .8*u+.6*q,.6*u-.8*q
    dem=data['terrain']
    terrain=RegularGridInterpolator((dem['n'],dem['x']),np.array(dem['z']),bounds_error=False,fill_value=2.6)
    height=terrain(np.stack((gn,gx),axis=-1)).astype('float32')
    height=np.where(land,height,0.)
    shade=np.clip((np.roll(height,1,axis=1)-height)*1.6 + (np.roll(height,1,axis=0)-height)*.6,-19,13)
    grain = np.sin(x*1.79+y*.91)+np.sin(x*.63-y*.37)
    ripple=np.sin(x*.52+y*1.45)*np.sin(x*.13+y*.029)+np.cos(x*.72-y*.62)*.48
    water_color=np.stack([17+3*ripple,68+6*ripple,99+8*ripple],axis=-1)
    soil_color=np.array([192,182,160])+((shade+grain*2.4)[...,None])
    green_color=np.array([113,143,90])+((shade+grain*3.)[...,None])
    rgb=np.where(land[...,None],np.where(green[...,None],green_color,soil_color),water_color).clip(0,255).astype('uint8')
    depth=((y/SCALE+height*CE)/SE*CE+height*SE).astype('float32')
    return rgb, depth, land, green, height


class Raster:
    def __init__(self,data,frame,divisor=1):
        self.frame,self.divisor=frame,divisor
        self.rgb,self.depth,self.land,self.green,self.height=ground_texture(data,frame,divisor)
        self.h,self.w=self.depth.shape
        self.structure=np.zeros_like(self.depth,dtype='uint8')
        self.hard=self.land & ~self.green
        self.window_pixels=[]
        self.visible_windows=[]

    def face(self, points, color, *, building=False, pavement=False, deck=False, detail=False, lamps=None):
        xy,z=projected(points,self.frame,self.divisor)
        x0,y0=np.maximum(0,np.floor(xy.min(axis=0)).astype(int))
        x1,y1=np.minimum((self.w,self.h),np.ceil(xy.max(axis=0)).astype(int)+1)
        if x1<=x0 or y1<=y0 or x1-x0+y1-y0<4:
            return
        local=xy-[x0,y0]
        mask=Image.new('L',(int(x1-x0),int(y1-y0)))
        draw=ImageDraw.Draw(mask)
        draw.polygon([tuple(p) for p in local],fill=255)
        design=np.c_[local,np.ones(len(local))]
        plane,*_=np.linalg.lstsq(design,z,rcond=None)
        yy,xx=np.ogrid[:y1-y0,:x1-x0]
        depth=(plane[0]*xx+plane[1]*yy+plane[2]).astype('float32')
        region=np.s_[y0:y1,x0:x1]
        # Terrain is a coarse grid; road surfaces can replace its local proxy.
        active=(np.asarray(mask)>0)&(depth>=self.depth[region]-(2.4 if pavement else .34))
        if pavement and not deck:
            active &= self.land[region]
        if not active.any():
            return
        self.depth[region][active]=depth[active]
        self.rgb[region][active]=color
        if building:
            self.structure[region][active]=255
            self.hard[region][active]=False
            self.land[region][active]=True
        if deck:
            self.land[region][active]=True
            self.hard[region][active]=True
        if lamps:
            self.window_pixels.extend(lamps)

    def draw(self,data):
        walkers={'footway','pedestrian','cycleway','steps','path','track','bridleway','corridor'}
        for road in sorted(data['roads'],key=lambda r:(r['bridge'],r['width'])):
            if road.get('tunnel') or road['kind'] in ('rail','tram','light_rail'):
                continue
            walk=road['kind'] in walkers
            for a,b in zip(road['points'],road['points'][1:]):
                dx,dn=b[0]-a[0],b[1]-a[1]
                length=math.hypot(dx,dn)
                if length<.3:
                    continue
                nx,ny=-dn/length,dx/length
                def strip(width, lift, color):
                    nxw,nyw=nx*width/2,ny*width/2
                    self.face([(a[0]+nxw,a[1]+nyw,a[2]+lift),(a[0]-nxw,a[1]-nyw,a[2]+lift),
                               (b[0]-nxw,b[1]-nyw,b[2]+lift),(b[0]+nxw,b[1]+nyw,b[2]+lift)],color,
                              pavement=True,deck=road['bridge'])
                if not walk:
                    strip(road['width']+1.3,.025,[181,174,158])
                strip(road['width']*.88,.06,[203,194,170] if walk else [99,107,111])
                if not walk and road['width']>11 and length>5:
                    strip(.28,.08,[174,174,150])
        for pitch in data['ballfields']:
            self.face([[*p,4.] for p in pitch[0]],[98,142,78],pavement=True)
        stone=[[192,177,149],[171,167,153],[188,155,126],[208,191,163],[171,152,135],[163,162,149]]
        glass=[[127,154,164],[126,140,156],[148,164,166],[102,135,151]]
        for b in data['buildings']:
            h=b['height'];g=b['ground'];z=g+h
            seed=zlib.crc32(b['id'].encode())
            palette=glass if h>31 else stone
            base=palette[seed%len(palette)]
            for footprint in b['footprint']:
                shape=good_polygon(footprint)
                pieces=[shape] if shape.geom_type=='Polygon' else [p for p in getattr(shape,'geoms',()) if p.geom_type=='Polygon']
                for p in pieces:
                    ring=list(orient(p,sign=1.).exterior.coords)
                    xy,_=projected([[*a,z] for a in ring],self.frame,self.divisor)
                    if xy[:,0].max()<-1 or xy[:,0].min()>self.w+1 or xy[:,1].min()>self.h+1 or xy[:,1].max()+h*SCALE*CE/self.divisor<-1:
                        continue
                    for a,c in zip(ring,ring[1:]):
                        dx,dn=c[0]-a[0],c[1]-a[1]
                        length=math.hypot(dx,dn)
                        if length<.45 or .6*dn+.8*dx<0:
                            continue
                        shade=.65+.21*abs(dx/length)
                        windows=[]
                        if length>=5 and h>4:
                            step=3.4 if h>16 else 3.
                            for floor in range(1,1+int((h-1)/step)):
                                for col in range(1,1+int((length-1)/3.2)):
                                    t=col*3.2/length
                                    if t>.95:
                                        continue
                                    win=(a[0]+dx*t,a[1]+dn*t,g+floor*step-.6)
                                    windows.append((win,(seed+floor*13+col*17)%100,math.atan2(dn,dx),h>24))
                        self.face([[*a,g],[*c,g],[*c,z],[*a,z]],[int(v*shade) for v in base],building=True,lamps=windows)
                    self.face([[*a,z] for a in ring], [min(225,int(v*1.06)) for v in base],building=True)
                    if p.area>75 and h>5:
                        inner=p.buffer(-1.35)
                        if inner.geom_type=='Polygon' and not inner.is_empty:
                            roof=[list(a) for a in inner.exterior.coords]
                            self.face([[*a,z+.15] for a in roof],[int(v*.85) for v in base],building=True,detail=True)
                        c=p.representative_point()
                        span=min(2.8,math.sqrt(p.area)*.11)
                        self.face([[c.x-span,c.y-span,z+.9],[c.x+span,c.y-span,z+.9],
                                   [c.x+span,c.y+span,z+.9],[c.x-span,c.y+span,z+.9]],
                                  [155,158,150],building=True,detail=True)
            for part in b.get('parts',[]):
                if part['roof']>z+1.5:
                    for rings in part['polygons']:
                        self.face([[*p,part['roof']] for p in rings[0]],[int(v*.95) for v in base],building=True)
        canvas=Image.fromarray(self.rgb)
        draw=ImageDraw.Draw(canvas)
        for p,seed,angle,glass_window in self.window_pixels:
            x,y,d = point(p,self.frame,self.divisor)
            ix,iy=int(x),int(y)
            if not (2<=ix<self.w-2 and 2<=iy<self.h-2 and abs(self.depth[iy,ix]-d)<2.6):
                continue
            if self.divisor==1:
                draw.rectangle((ix-1,iy-1,ix+1,iy+1),fill=(58,85,102) if glass_window else (84,96,100))
                if seed%4==0:
                    self.visible_windows.append({'p':list(p),'seed':seed,'angle':angle})
        for x,n,h,g in data['trees']:
            sx,sy,d=point((x,n,g+h*.65),self.frame,self.divisor)
            ix,iy=int(sx),int(sy)
            if not (3<=ix<self.w-3 and 3<=iy<self.h-3 and d>=self.depth[iy,ix]-1.5):
                continue
            r=max(1.6,5.5/self.divisor)
            draw.ellipse((sx-r,sy-r*.82,sx+r,sy+r*.70),fill=(67,98,58),outline=(49,77,52))
            draw.ellipse((sx-r*.67,sy-r*.72,sx+r*.47,sy+r*.16),fill=(108,138,67))
        return canvas


def point(p,frame,divisor=1):
    x,n,z=p; q=.6*x-.8*n
    return ((SCALE*(.8*x+.6*n)-frame.x)/divisor,
            (SCALE*(q*SE-z*CE)-frame.y)/divisor, q*CE+z*SE)


def render(keys):
    data=load_data()
    WORK.mkdir(parents=True,exist_ok=True)
    for frame in FRAMES:
        if keys and frame.key not in keys:
            continue
        print(f'Rendering {frame.key} {frame.width} x {frame.height}',flush=True)
        raster=Raster(data,frame)
        canvas=raster.draw(data)
        canvas.save(WORK/f'{frame.key}-reference.png',compress_level=4)
        Image.fromarray(pack_depth(raster.depth,raster.structure,DEPTH_ENCODING)).save(WORK/f'{frame.key}-depth.png',compress_level=4)
        Image.fromarray((~raster.land).astype('uint8')*255).save(WORK/f'{frame.key}-water.png')
        Image.fromarray(raster.hard.astype('uint8')*255).save(WORK/f'{frame.key}-hard.png')
        (WORK/f'{frame.key}-windows.json').write_text(json.dumps(raster.visible_windows,separators=(',',':')),encoding='utf-8')
        print(f'{frame.key}: {len(raster.visible_windows):,} visible window samples',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('frames',nargs='*',choices=[f.key for f in FRAMES])
    render(parser.parse_args().frames)
