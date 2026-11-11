"""Render the entire bridge in one pass, including display-depth geometry."""

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from atlas_geometry import CE, SE, SCALE, PixelFrame
from golden_gate_geometry import BRIDGE_FRAME, BridgeProfile
from render_corridor import Raster, point


BASE = {
    'steel':(189,73,45),'edge':(237,119,77),'shade':(103,44,37),
    'cable':(223,112,78),'concrete':(176,155,134),'deck':(82,87,87),
    'walk':(166,151,134),'stripe':(205,202,181),'gold':(198,158,82),'lamp':(251,196,108),
}


def colors(appearance):
    wet=appearance.startswith('rain')
    dark=appearance.endswith('night')
    palette={}
    for name,color in BASE.items():
        a=np.array(color,dtype='float32')
        if wet:
            a=a*np.array([.83,.89,.95])+[2,4,8]
        if dark:
            a=a*np.array([.45,.43,.46])+[9,8,11]
        palette[name]=np.rint(a).clip(0,255).astype('uint8')
    if dark:
        palette.update(lamp=(255,200,123),edge=(183,85,52),
                       stripe=(139,129,109),gold=(166,129,71))
    return palette


def paint(r,appearance='day'):
    p=BridgeProfile()
    ink=colors(appearance)
    def face(coords,key,*,road=False):
        r.face([p.point(s,a,z) for s,a,z in coords],ink[key],building=not road,deck=road)

    def box(s0,s1,a0,a1,z0,z1,key='steel',lid='edge',shadow='shade'):
        face([(s0,a0,z0),(s1,a0,z0),(s1,a0,z1),(s0,a0,z1)],shadow)
        face([(s0,a1,z0),(s1,a1,z0),(s1,a1,z1),(s0,a1,z1)],key)
        face([(s0,a0,z0),(s0,a1,z0),(s0,a1,z1),(s0,a0,z1)],shadow)
        face([(s1,a0,z0),(s1,a1,z0),(s1,a1,z1),(s1,a0,z1)],key)
        face([(s0,a0,z1),(s1,a0,z1),(s1,a1,z1),(s0,a1,z1)],lid)

    def line(a,b,width,key):
        s0,w0,z0=a;s1,w1,z1=b
        ds,dw,dz=s1-s0,w1-w0,z1-z0
        if abs(ds)>.15 or abs(dw)>.15:
            face([(s0,w0-width,z0),(s1,w1-width,z1),(s1,w1+width,z1),(s0,w0+width,z0)],key)
        if abs(dz)>.15:
            face([(s0-width,w0,z0),(s1-width,w1,z1),(s1+width,w1,z1),(s0+width,w0,z0)],key)

    # Deck, parapets, travel lanes and the repeating underdeck truss.
    stations=np.unique(np.r_[np.arange(p.approach_start,p.approach_end,14),p.start,p.end,
                             p.approach_end,-343,0,1280,1623])
    for i,(a,b) in enumerate(zip(stations,stations[1:])):
        h,j=p.deck(a),p.deck(b)
        face([(a,-13.5,h),(b,-13.5,j),(b,13.5,j),(a,13.5,h)],'walk',road=True)
        face([(a,-9.5,h+.04),(b,-9.5,j+.04),(b,9.5,j+.04),(a,9.5,h+.04)],'deck',road=True)
        for side in (-1,1):
            u=side*13.4
            face([(a,u,h-7),(b,u,j-7),(b,u,j+.6),(a,u,h+.6)],'shade')
            line((a,u,h-6.5),(b,u,j-6.5),.8,'steel')
            line((a,u,h-.9),(b,u,j-.9),1.,'edge')
            if -535 < a < 1890:
                line((a,u,h-6.1 if i%2 else h-.9),(b,u,j-.9 if i%2 else j-6.1),.7,'steel')
            line((a,u,h+1.3),(b,u,j+1.3),.45,'edge')
            line((a,u,h),(a,u,h+1.4),.27,'steel')
        for lane in (-6,-3,0,3,6):
            end=b if lane==0 else a+(b-a)*.43
            if end-a<.6: continue
            k=p.deck(end)
            w=.14 if lane==0 else .115
            face([(a,lane-w,h+.12),(end,lane-w,k+.12),
                  (end,lane+w,k+.12),(a,lane+w,h+.12)],'gold' if lane==0 else 'stripe',road=True)
    for s in (-674,-611,-540,-493,-429,-367,1670,1744,1820,1900,1964):
        h=p.deck(s)
        for a in (-9.5,9.5):
            box(s-2.8,s+2.8,a-2.4,a+2.4, max(0,h-37),h-5,'concrete','walk','shade')
    for s in (0,1280):
        for u in (-11.3,11.3):
            box(s-18,s+18,u-7.4,u+7.4,.2,10.,'concrete','walk','shade')
            # The tapered legs use inset panels and cap each vertical stage.
            for low,high,long,wide in [(9,73,8.,4.5),(73,121,7.2,4.0),(121,171,6.3,3.6),
                                       (171,211,5.5,3.25),(211,227,4.8,3.0)]:
                box(s-long,s+long,u-wide,u+wide,low,high)
                box(s-long-.28,s+long+.28,u-wide-.45,u+wide+.45,high-2,high-1,'edge','steel')
                for a in (-.58,.58):
                    face([(s-long-.32,u+a*wide,low+1),(s-long-.32,u+a*wide,high-2),
                          (s-long-.32,u+(a+.12)*wide,high-2),(s-long-.32,u+(a+.12)*wide,low+1)],'edge')
            box(s-5.1,s+5.1,u-3.2,u+3.2,225.9,228.1,'edge','lamp' if appearance.endswith('night') else 'edge')
        for z in (53,103,141,177,211):
            box(s-5.9,s+5.9,-11.3,11.3,z-3.6,z+1.9)
            box(s-6.4,s+6.4,-11.3,11.3,z+1.9,z+3.1,'edge')
    for s in (-343,1623):
        box(s-9,s+9,-14.5,14.5,p.deck(s)-12,p.deck(s)+5,'concrete','walk')

    # A shallow steel arch leaves the historic fort clear below the approach.
    for a in (-10.6,10.6):
        for s in range(-441,-298,5):
            t=s+5
            def arch(k):
                return p.deck(k)-9-32*((k+369)/73.)**2
            line((s,a,arch(s)),(t,a,arch(t)),1.7,'steel')
            if s%4==3:
                line((s,a,arch(s)),(s,a,p.deck(s)-6),.8,'shade')

    for a in (-11.25,11.25):
        knots=np.unique(np.r_[np.arange(-343,1624,10),-343,0,1280,1623])
        for s,t in zip(knots,knots[1:]):
            line((s,a,p.cable(s)),(t,a,p.cable(t)),.58,'cable')
        for s in np.arange(-327,1620,16.):
            line((s,a,p.deck(s)+.55),(s,a,p.cable(s)),.31,'cable')
    lamps=[]
    for s in np.arange(p.start+30,p.end-20,37.):
        for a in (-12.1,12.1):
            h=p.deck(s)
            line((s,a,h+.5),(s,a,h+5.7),.24,'shade')
            line((s,a,h+5.7),(s,a-math.copysign(1.35,a),h+5.7),.43,'lamp' if appearance.endswith('night') else 'edge')
            lamps.append(p.point(s,a-math.copysign(1.35,a),h+5.7))
    return lamps


class BridgeRaster(Raster):
    """Separate depth layer; low-resolution bare-earth terrain cannot cut the deck."""
    def __init__(self,frame,divisor):
        self.frame,self.divisor=frame,divisor
        self.w=math.ceil(frame.width/divisor);self.h=math.ceil(frame.height/divisor)
        size=(self.h,self.w)
        self.sea_depth=((frame.y+np.arange(self.h,dtype='float32')*divisor)/SCALE*CE/SE)[:,None]
        self.depth=np.broadcast_to(self.sea_depth,size).copy()
        self.rgb=np.zeros((*size,3),dtype='uint8')
        self.structure=np.zeros(size,dtype='uint8')
        self.land=np.zeros(size,dtype=bool)
        self.hard=np.zeros(size,dtype=bool)

    @property
    def occupied(self):
        return (self.depth>self.sea_depth+.008) | (self.structure>0)


def stamp_depth(target):
    d=target.divisor
    f=BRIDGE_FRAME
    ix,iy=(f.x-target.frame.x)//d,(f.y-target.frame.y)//d
    x,y=target.frame.x+ix*d,target.frame.y+iy*d
    r=BridgeRaster(PixelFrame(f.key,x,y,f.right-x,f.bottom-y),d)
    lamps=paint(r)
    area=np.s_[iy:iy+r.h,ix:ix+r.w]
    take=r.occupied
    target.depth[area][take]=r.depth[take]
    target.structure[area][take]=r.structure[take]
    target.land[area][take]=True
    target.hard[area][take]=r.hard[take]
    return lamps


def overlay(appearance):
    r=BridgeRaster(BRIDGE_FRAME,1)
    paint(r,appearance)
    rgba=Image.fromarray(r.rgb).convert('RGBA')
    rgba.putalpha(Image.fromarray(r.occupied.astype('uint8')*255))
    return rgba


def add_reflections(im, water, appearance):
    """Softly register tower shadows and wet amber glints over the strait."""
    p=BridgeProfile()
    f=BRIDGE_FRAME
    wet=appearance.startswith('rain')
    night=appearance.endswith('night')
    if not wet and night:
        return im
    m=Image.new('L',im.size)
    d=ImageDraw.Draw(m)
    if night:
        for s in (0,1280):
            for side in (-10.6,10.6):
                x,y,_=point(p.point(s,side,.5),f)
                for k in range(4,116,3):
                    cx=x+math.sin(k*.37+s)*4.7
                    a=(1.-k/134)*(2.2+4.5*(.5+.5*math.sin(k*3.17+s)))
                    d.line((cx-a,y+k,cx+a,y+k),fill=int(145*(1.-k/122)),width=2)
        for i,s in enumerate(range(-343,1624,37)):
            x,y,_=point(p.point(s,11.3,.5),f)
            for k in range(4,43,6):
                shift=math.sin(s+k*2.8)*3.4
                d.line((x-3+shift,y+k,x+3+shift,y+k),fill=65-k,width=1)
        tint=np.array([128,73,22],dtype='float32')
        m=m.filter(ImageFilter.GaussianBlur(.8))
    else:
        def shade(s,a,z):
            x,n,h=p.point(s,a,z)
            return point((x+h*.43,n-h*.34,.2),f)[:2]
        d.line([shade(s,0,p.deck(s)) for s in range(-343,1624,18)],fill=53 if wet else 74,width=32)
        for s in (0,1280):
            for a in (-10.6,10.6):
                d.line([shade(s,a,z) for z in (0,227)],fill=67,width=15)
        tint=np.array([-11,-20,-26],dtype='float32')
        m=m.filter(ImageFilter.GaussianBlur(2.5))
    t=(np.asarray(m,dtype='float32')/255)*(np.asarray(water,dtype='float32')/255)
    rgb=np.asarray(im,dtype='float32')+t[...,None]*tint
    return Image.fromarray(np.rint(rgb).clip(0,255).astype('uint8'))
