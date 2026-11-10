"""Rasterize reviewed vector/height geometry under one orthographic camera.

This creates an offline structural reference, not the final AI illustration.
The same projection and depth raster drive transport and compositing.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
W, H, SCALE = 3072, 2048, 2.55
SE, CE = math.sin(math.radians(39)), math.cos(math.radians(39))
OX, OY = 1696, 1050
CROP = (800, 128, 2912, 1536)


def project(p):
    x, n, z = p
    return [OX + SCALE * (.8*x + .6*n), OY + SCALE * ((.6*x-.8*n)*SE-z*CE)]


def depth(p):
    x, n, z = p
    return (.6*x-.8*n)*CE+z*SE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--osm', type=Path)
    args = parser.parse_args()
    d = json.loads(args.source.read_text(encoding='utf-8'))
    out = ROOT/'data/source'
    out.mkdir(parents=True, exist_ok=True)
    (ROOT/'data/source').mkdir(parents=True, exist_ok=True)
    (ROOT/'data/source/ferry.json').write_bytes(args.source.read_bytes())
    raw_tags = {}
    if args.osm:
        osm = json.loads(args.osm.read_text(encoding='utf-8'))
        raw_tags = {str(e['id']): e.get('tags', {}) for e in osm['elements'] if e['type']=='way'}
    elif (ROOT/'data/source/road-tags.json').exists():
        raw_tags=json.loads((ROOT/'data/source/road-tags.json').read_text(encoding='utf-8'))
    road_tags = {r['id']: {k:v for k,v in raw_tags.get(r['id'], {}).items() if k in ['oneway','lanes','highway','junction','name']} for r in d['roads']}
    (ROOT/'data/source/road-tags.json').write_text(json.dumps(road_tags,separators=(',',':')),encoding='utf-8')
    rgb = np.zeros((H, W, 3), dtype=np.uint8)
    rgb[:] = [35, 99, 119]
    depths = np.full((H,W), -3000, dtype=np.float32)
    structural = np.zeros((H,W), dtype=np.uint8)
    water = np.full((H,W), 255, dtype=np.uint8)
    surfaces = []
    lamps, windows = [], []

    def face(points, color, kind=0):
        if len(points)<3: return
        surfaces.append((points, color, kind))

    # Ground polygons and road surfaces are actual source geometry.
    for poly in d['land']:
        face([[x,n,2.5] for x,n in poly[0]], [184,183,165], 1)
    for poly in d['greens']:
        face([[x,n,2.65] for x,n in poly[0]], [112,141,101], 1)
    roads=[]
    for road in d['roads']:
        pts=road['path']
        if len(pts)<2:continue
        walk=road['kind'] in ['footway','pedestrian','steps','cycleway','path']
        if road['kind']=='tram':continue
        width=road['width']*.82
        for a,b in zip(pts,pts[1:]):
            ln=math.hypot(b[0]-a[0],b[1]-a[1])
            if ln<.1:continue
            nx,nn=-(b[1]-a[1])/ln*width/2,(b[0]-a[0])/ln*width/2
            face([[a[0]+nx,a[1]+nn,2.95],[a[0]-nx,a[1]-nn,2.95],[b[0]-nx,b[1]-nn,2.95],[b[0]+nx,b[1]+nn,2.95]], [207,202,183] if walk else [115,123,121],1)
        length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
        tags=road_tags[road['id']]
        if not walk and length>2 and road['kind'] not in ['service','construction']:
            roads.append({'id':road['id'],'name':road['name'],'points':[[*p,3.3] for p in pts],'length':round(length,2),'width':width,'oneway':tags.get('oneway','no'),'lanes':tags.get('lanes'),'kind':road['kind']})
        if road['name'] in ['The Embarcadero','Market Street','California Street','Drumm Street','Davis Street'] and length>40:
            for i,p in enumerate(pts):
                if i%2==0:lamps.append([p[0]+width*.45,p[1],8.0])

    # One stable facade volume plus source LiDAR roof terraces.
    palette=[[187,178,157],[169,168,158],[152,167,169],[194,185,165],[158,161,153],[173,153,135],[142,158,165]]
    for bi,b in enumerate(d['buildings']):
        ground=b['ground']
        roof=ground+b['height']
        color=palette[bi%len(palette)]
        for poly in b['footprint']:
            ring=list(Polygon(poly[0]).simplify(.7,preserve_topology=True).exterior.coords)
            for ai,(a,c) in enumerate(zip(ring,ring[1:])):
                shade=.69+.23*abs((c[0]-a[0])/(math.dist(a,c) or 1))
                face([[*a,ground],[*c,ground],[*c,roof],[*a,roof]],[int(v*shade) for v in color],2)
                length=math.dist(a,c)
                if length<6:continue
                # A sparse, deterministic subset of source facade windows becomes
                # a reviewed illustrative emission layer; not a window inventory.
                for floor in range(2,int(b['height']/3.5)):
                    for j in range(1,int(length/4.0)):
                        if (bi*17+floor*7+j*13)%5:continue
                        t=j*4/length
                        if t>=.97:continue
                        p=[a[0]+(c[0]-a[0])*t,a[1]+(c[1]-a[1])*t,ground+floor*3.5]
                        windows.append({'p':p,'seed':(bi*131+floor*17+j)%100,'angle':math.atan2(c[1]-a[1],c[0]-a[0])})
            face([[x,n,roof] for x,n in ring],[min(240,int(v*1.06)) for v in color],2)
        for part in b['parts']:
            if part['roof']<roof+1.5:continue
            for poly in part['polygons']:
                if Polygon(poly[0]).area<10:continue
                face([[x,n,part['roof']] for x,n in poly[0]],[int(v*.95) for v in color],2)
                for a,c in zip(poly[0],poly[0][1:]):
                    face([[*a,roof],[*c,roof],[*c,part['roof']],[*a,part['roof']]],[int(v*.77) for v in color],2)
        if b['id']=='201006.0000058':
            center=Polygon(b['footprint'][0][0]).centroid
            # Recognizable heritage silhouette, illustrative facade supplement.
            for poly in b['footprint']:
                face([[x,n,roof+.4] for x,n in poly[0]],[161,91,52],2)
            x,n=center.x,center.y
            ring=[[x-5,n-5],[x+5,n-5],[x+5,n+5],[x-5,n+5],[x-5,n-5]]
            for a,c in zip(ring,ring[1:]):
                face([[*a,roof],[*c,roof],[*c,53],[*a,53]],[194,179,146],2)
            face([[xx,nn,53] for xx,nn in ring],[155,122,86],2)
    # Rasterize every source face using a real camera-depth test.
    for points,color,kind in surfaces:
        xy=np.array([project(p) for p in points])
        x0=max(0,int(np.floor(xy[:,0].min())));x1=min(W,int(np.ceil(xy[:,0].max()))+1)
        y0=max(0,int(np.floor(xy[:,1].min())));y1=min(H,int(np.ceil(xy[:,1].max()))+1)
        if x1<=x0 or y1<=y0:continue
        mask=Image.new('L',(x1-x0,y1-y0));draw=ImageDraw.Draw(mask)
        draw.polygon([(float(x-x0),float(y-y0)) for x,y in xy],fill=255)
        plane,_,_,_=np.linalg.lstsq(np.c_[xy,np.ones(len(xy))],np.array([depth(p) for p in points]),rcond=None)
        yy,xx=np.mgrid[y0:y1,x0:x1]
        z=plane[0]*xx+plane[1]*yy+plane[2]
        active=(np.asarray(mask)>0)&(z>=depths[y0:y1,x0:x1]-.1)
        rgb[y0:y1,x0:x1][active]=color
        depths[y0:y1,x0:x1][active]=z[active]
        structural[y0:y1,x0:x1][active]=255 if kind==2 else 0
        water[y0:y1,x0:x1][active]=0
    # Draw source windows and trees, keeping depth consistent.
    canvas=Image.fromarray(rgb);draw=ImageDraw.Draw(canvas)
    visible_windows=[]
    for win in windows:
        x,y=project(win['p']);ix,iy=int(x),int(y)
        if 1<ix<W-2 and 1<iy<H-2 and abs(depths[iy,ix]-depth(win['p']))<3:
            draw.rectangle((ix-1,iy-2,ix+1,iy+1),fill=(74,98,105))
            visible_windows.append(win)
    for x,n,h,*_ in d['trees']:
        p=[x,n,float(h)*.65+3];sx,sy=project(p);ix,iy=int(sx),int(sy)
        if not(5<ix<W-5 and 5<iy<H-5) or depth(p)<depths[iy,ix]-2:continue
        radius=6+int(h*.12)
        draw.ellipse((sx-radius,sy-radius*1.25,sx+radius,sy+radius*.7),fill=(75,111,74),outline=(60,93,66),width=1)
    canvas.crop(CROP).save(out/'source-structure.png')
    # Depth is packed RG16 in an ordinary PNG for JS and WebGL to decode alike.
    code=np.clip(np.round((depths+2000)/4000*65535),0,65535).astype(np.uint16)
    packed=np.zeros((H,W,3),dtype=np.uint8);packed[:,:,0]=code//256;packed[:,:,1]=code%256;packed[:,:,2]=structural
    Image.fromarray(packed).crop(CROP).save(out/'depth.png')
    Image.fromarray(water).crop(CROP).save(out/'water.png')
    ferry=next(b for b in d['buildings'] if b['id']=='201006.0000058')
    cp=Polygon(ferry['footprint'][0][0]).centroid
    metadata={'schemaVersion':1,'release':'waterfront-v1','width':CROP[2]-CROP[0],'height':CROP[3]-CROP[1],'sourceImageCrop':CROP,'extent':d['extent'],'crs':d['crs'],'originLonLat':d['originLonLat'],'originUTM':d['originUTM'],'projection':{'scale':SCALE,'origin':[OX-CROP[0],OY-CROP[1]],'sinElevation':SE,'cosElevation':CE,'east':[.8,.6],'north':[.6,-.8]},'depthEncoding':{'offset':2000,'range':4000,'channels':'RG16; B=source structural mask'},'sourceBuildings':len(d['buildings']),'roads':roads,'lamps':lamps,'windows':visible_windows,'land':d['land'],'landmarks':[{'name':'Ferry Building','nameZh':'渡轮大厦','p':[cp.x,cp.y,22]},{'name':'Financial District','nameZh':'金融区','p':[-380,-50,110]},{'name':'Embarcadero','nameZh':'滨海大道','p':[105,190,4]}]}
    (out/'scene.json').write_text(json.dumps(metadata,separators=(',',':')),encoding='utf-8')
    provenance={'sourceSnapshotDate':'2026-11-09','sourceSHA256':hashlib.sha256(args.source.read_bytes()).hexdigest(),'geometry':['DataSF Building Footprints (PDDL)','USGS San Francisco 2023 lidar (public domain)','OpenStreetMap 2026-11-09 snapshot (ODbL 1.0)'],'sourceAudit':d['audit'],'camera':'orthographic; azimuth implicit in east/north basis; elevation 39 degrees','renderedSize':[W,H],'displayRegistration':'Single source projection. Imagegen may introduce local deviations; source depth and windows are display proxies, not measured final-art geometry.'}
    provenance_path=ROOT/'data/provenance.json'
    if provenance_path.exists():
        previous=json.loads(provenance_path.read_text(encoding='utf-8'));previous.update(provenance);provenance=previous
    provenance_path.write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    print(f'Prepared {W}x{H}; {len(surfaces)} faces; {len(roads)} road segments; {len(visible_windows)} facade light samples')


if __name__=='__main__':main()
