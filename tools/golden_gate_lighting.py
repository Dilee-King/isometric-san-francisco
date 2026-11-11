"""Bake wet materials and night illumination over registered western daylight art."""

import json
import math
import zlib

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

from atlas_geometry import SCALE, camera_point
from render_golden_gate import WORK


LIT_ROADS = ('Beach Street','North Point','Van Ness','Marina Boulevard','Mason Street',
             'Baker Street','Jefferson','Bay Street','Laguna','Lincoln Boulevard',
             'Marine Drive','Long Avenue','Torpedo Wharf','Hyde Street Pier',
             'Municipal Pier','Fort Mason','Yacht Road')


def lamps_for(data, lit_roads=LIT_ROADS):
    lamps={}
    for road in data['roads']:
        if road['tunnel'] or not any(name in road['name'] for name in lit_roads):
            continue
        identity=zlib.crc32(road['id'].encode())
        for a,b in zip(road['points'],road['points'][1:]):
            dx,dn=b[0]-a[0],b[1]-a[1]
            length=math.hypot(dx,dn)
            if length<13:
                continue
            count=max(1,round(length/24))
            off=(1 if identity%2==0 else -1)*min(5.5,road['width']*.46)
            for i in range(count):
                t=(i+.5)/count
                p=[a[0]+dx*t+dn/length*off,a[1]+dn*t-dx/length*off,a[2]+(b[2]-a[2])*t]
                key=tuple(round(v/4) for v in p)
                lamps[key]=p
    return list(lamps.values())


def tone(day, appearance, frame, lamps, *, work=WORK):
    """The four appearances keep precisely the same native pixels and silhouettes."""
    if appearance=='day':
        return day
    wet=appearance.startswith('rain')
    night=appearance.endswith('night')
    w,h=day.size
    scale=frame.width/w
    day=np.asarray(day,dtype='float32')
    hard=np.asarray(Image.open(work/f'{frame.key}-hard.png'))>0
    coast=np.asarray(Image.open(work/f'{frame.key}-water.png'))>0
    water=coast & (day[...,2]>day[...,1]*1.035)&(day[...,2]>day[...,0]*1.08)
    vegetation=(day[...,1]>day[...,0]*1.03)&(day[...,1]>day[...,2]*1.18)&~water
    y=(frame.y+np.arange(h,dtype='float32')*scale)[:,None]
    x=(frame.x+np.arange(w,dtype='float32')*scale)[None,:]
    gray=day@[.28,.58,.14]
    if wet:
        out=day*np.array([.73,.78,.86],dtype='float32')+np.array([6.,8.,10.],dtype='float32')
        out=.83*out+.17*gray[...,None]*np.array([.77,.82,.91],dtype='float32')
        bands=(.5+.5*np.sin(y*.078+x*.014+1.8*np.sin(x*.021-y*.012)))**7
        gloss=(~water&~vegetation)*(3+bands*16)*(0.35+.65*hard)
        out+=gloss[...,None]*np.array([.51,.82,1.25],dtype='float32')
        # Rain changes the water's surface color even when animation is paused.
        out[water]=day[water]*[.77,.76,.75]+[10,10,13]
    else:
        out=day.copy()
    if not night:
        return Image.fromarray(np.rint(out).clip(0,255).astype('uint8'))

    out=out*np.array([.24,.33,.46],dtype='float32')+[5,6,8]
    out[water]=out[water]*[.90,1.03,1.04]+[2,4,7]
    out[vegetation]*=[.73,.86,.93]
    sharp=Image.new('L',(w,h)); soft=Image.new('L',(w,h)); reflection=Image.new('L',(w,h))
    ds,dp,dr=(ImageDraw.Draw(m) for m in (sharp,soft,reflection))
    # A source sample can move to the nearest dark window in the illustration.
    # A maximum offset of three pixels avoids glowing dots over empty roofs.
    windows=json.loads((work/f'{frame.key}-windows.json').read_text(encoding='utf-8'))
    for row in windows:
        if row['seed']%5 in (2,4):
            continue
        u,v,_=camera_point(row['p'])
        u,v=round((u-frame.x)/scale),round((v-frame.y)/scale)
        if not (4<u<w-5 and 4<v<h-5):
            continue
        chip=gray[v-2:v+3,u-2:u+3]
        dy,dx=np.unravel_index(int(np.argmin(chip)),chip.shape)
        a,b=u+dx-2,v+dy-2
        if water[b,a] or vegetation[b,a] or chip.max()-chip.min()<11 or gray[b,a]>165:
            continue
        strength=159+row['seed']%70
        ds.rounded_rectangle((a-1,b-1,a+1,b+1),radius=.55,fill=strength)
        dp.ellipse((a-3,b-3,a+3,b+3),fill=strength//2)
    for k,p in enumerate(lamps):
        gx,gy,_=camera_point((p[0],p[1],p[2]+4.7))
        ax,ay=(gx-frame.x)/scale,(gy-frame.y)/scale
        _,ground_y,_=camera_point(p)
        by=(ground_y-frame.y)/scale
        if not (5<=ax<w-5 and 5<=ay<h-26):
            continue
        m=max(1.,1.7/scale)
        ds.ellipse((ax-m,ay-m,ax+m,ay+m),fill=233)
        radius=8.5/scale if wet else 6/scale
        dp.ellipse((ax-radius,by-radius*.63,ax+radius,by+radius*.8),fill=204)
        # Reflections are only composited onto pixels that read as water.
        if wet and coast[max(0,round(by-3)),round(ax)]:
            for j in range(8,64,4):
                yy=by+j/scale
                a=1.4/scale+2.6*(1-j/64)/scale
                dx=math.sin(k*.79+j*.45)*2.4/scale
                dr.line((ax+dx-a,yy,ax+dx+a,yy),fill=int(163*(1-j/68)),width=1)

    a=np.asarray(sharp,dtype='float32')/255
    b=gaussian_filter(np.asarray(soft,dtype='float32')/255,max(.8,4.1/scale))
    c=gaussian_filter(np.asarray(reflection,dtype='float32')/255,.68)*water
    out+=a[...,None]*np.array([202,142,65])
    out+=b[...,None]*np.array([99,63,28] if wet else [78,47,20])
    out+=c[...,None]*np.array([154,96,39])
    return Image.fromarray(np.rint(out).clip(0,255).astype('uint8'))
