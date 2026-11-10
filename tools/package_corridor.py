"""Package the registered corridor and regional overview as immutable DZI tiles."""

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import json
import math
from pathlib import Path
import random

import numpy as np
from PIL import Image
from shapely.geometry import LineString
from shapely.ops import unary_union

from atlas_geometry import ATLAS, ART_FRAMES, FRAMES, DEPTH_ENCODING, ORIGIN_UTM, camera_point, ground_point, pack_depth
from corridor_inputs import CACHE, ROOT, local_xy, sha
from render_corridor import Raster, WORK, good_polygon, load_data

OUT = ROOT/'public/map/v3'
APPEARANCES = {'scene':'day','night':'night','rain-day':'rain-day','rain-night':'rain-night'}
CAR_TYPES = {'motorway','motorway_link','trunk','trunk_link','primary','primary_link','secondary','secondary_link',
             'tertiary','tertiary_link','residential','unclassified','living_street'}
CAR_COLORS = ['#e9dfc8','#c6a370','#a75c42','#6f929b','#294552','#a5afaa','#d4aa43']


def save_json(path,value):
    path.write_text(json.dumps(value,separators=(',',':'),allow_nan=False),encoding='utf-8')


def pyramid(im, folder, stem):
    width,height=im.size
    tile=512; overlap=1
    top=math.ceil(math.log2(max(width,height)))
    for level in range(top+1):
        factor=2**(top-level)
        size=(math.ceil(width/factor),math.ceil(height/factor))
        base=im.resize(size,Image.Resampling.LANCZOS) if factor>1 else im
        directory=folder/f'{stem}_files'/str(level)
        directory.mkdir(parents=True,exist_ok=True)
        for row in range(math.ceil(size[1]/tile)):
            for col in range(math.ceil(size[0]/tile)):
                clip=(max(0,col*tile-overlap),max(0,row*tile-overlap),
                      min(size[0],(col+1)*tile+overlap),min(size[1],(row+1)*tile+overlap))
                base.crop(clip).save(directory/f'{col}_{row}.webp',quality=93,method=4)
    (folder/f'{stem}.dzi').write_text(
        f'<?xml version="1.0" encoding="utf-8"?><Image TileSize="{tile}" Overlap="{overlap}" Format="webp" xmlns="http://schemas.microsoft.com/deepzoom/2008"><Size Width="{width}" Height="{height}"/></Image>',encoding='utf-8')
    print(f'  {stem}: {width} x {height}, {top+1} levels',flush=True)


def geo_point(lon,lat,z=0):
    return [*map(float,local_xy(lon,lat)),z]

def image_point(x,y,z):
    return [*ground_point(x,y,z),z]


def routes_for_corridor(data):
    previous=json.loads((ROOT/'public/map/v2/scene.json').read_text(encoding='utf-8'))
    routes=list(previous['routes'])
    graph=defaultdict(list)
    for road in data['roads']:
        if road['kind'] not in CAR_TYPES or road['tunnel']:
            continue
        for a,b in zip(road['points'],road['points'][1:]):
            a=tuple(round(x,1) for x in a);b=tuple(round(x,1) for x in b)
            if math.dist(a,b)<1:
                continue
            if road['oneway']!='-1':
                graph[a].append(b)
            if road['oneway'] not in ('yes','true','1'):
                graph[b].append(a)
    rng=random.Random(20261110)
    route_counts={}
    for frame in ART_FRAMES:
        if frame.key=='ferry-anchor':
            continue
        def within(p):
            x,y,_=camera_point(p)
            return frame.x+55<=x<frame.right-55 and frame.y+55<=y<frame.bottom-55
        starts=[p for p in graph if within(p)]
        if not starts:
            raise ValueError(f'No source road starts in {frame.key}')
        seen=set(); loops=[]
        for attempt in range(1800):
            path=[rng.choice(starts)]
            for _ in range(65):
                choices=[p for p in graph.get(path[-1],[]) if len(path)<2 or p!=path[-2]]
                if not choices:
                    break
                p=rng.choice(choices)
                if p in path:
                    cycle=path[path.index(p):]+[p]
                    length=sum(math.dist(x,y) for x,y in zip(cycle,cycle[1:]))
                    key=tuple(sorted(cycle[:-1]))
                    if len(cycle)>3 and 82<length<2200 and key not in seen and sum(within(x) for x in cycle)/len(cycle)>.71:
                        loops.append(cycle);seen.add(key)
                    break
                path.append(p)
            if len(loops)>=16:
                break
        if len(loops)<5:
            raise ValueError(f'Only {len(loops)} directed loops in {frame.key}')
        route_counts[frame.key]=len(loops)
        for i in range(32):
            path=loops[i%len(loops)]
            shifted=[]
            for j,p in enumerate(path[:-1]):
                a=path[j-1] if j else path[-2];b=path[j+1]
                e,n=b[0]-a[0],b[1]-a[1]
                l=math.hypot(e,n) or 1
                shifted.append([p[0]+n/l*1.4,p[1]-e/l*1.4,p[2]+.12])
            routes.append({'id':f'{frame.key}-car-{i}','kind':'car','points':shifted+[shifted[0]],
                           'speed':4.8+i%4*.7,'phase':rng.random()*150,'dwell':1.6+i%3*.35,'color':CAR_COLORS[i%len(CAR_COLORS)]})
    ship_specs=[
        ('north-ferry','ferry',[(-122.407,37.8129),(-122.398,37.8108),(-122.390,37.8055),(-122.386,37.798)],6.2,52,6),
        ('mission-cargo','cargo',[(-122.376,37.7905),(-122.3755,37.771),(-122.378,37.764)],4.1,110,0),
    ]
    for key,kind,locations,speed,phase,dwell in ship_specs:
        pts=[geo_point(*p,.7) for p in locations]
        routes.append({'id':key,'kind':kind,'points':pts+pts[-2::-1],'speed':speed,'phase':phase,'dwell':dwell,'color':'#e9e8d9'})
    for key, locations, speed, phase in [
        ('wharf-ferry',[(-2500,-3080),(-2160,-3000)],5.8,24),
        ('south-ferry',[(-1900,3350),(-1960,3660),(-2100,3900)],5.6,45),
    ]:
        pts=[image_point(*p,.7) for p in locations]
        routes.append({'id':key,'kind':'ferry','points':pts+pts[-2::-1],'speed':speed,'phase':phase,'dwell':5,'color':'#e9e8d9'})
    routes.extend([
        {'id':'north-overflight','kind':'plane','points':[image_point(-2850,-2680,290),image_point(1100,-2050,290)],'speed':53,'phase':7,'color':'#ebeddf'},
        {'id':'south-overflight','kind':'plane','points':[image_point(-4200,3150,315),image_point(-1600,3370,315)],'speed':51,'phase':19,'color':'#e9e8dd'},
    ])
    land=unary_union([good_polygon(r) for r in data['land']])
    clearance=[]
    for r in routes:
        if r['kind'] not in ('ferry','cargo'):
            continue
        radius=math.hypot(15.5,4.5) if r['kind']=='ferry' else math.hypot(32.5,7.5)
        distance=LineString([p[:2] for p in r['points']]).distance(land)
        if distance<radius:
            raise ValueError(f'{r["id"]} hull clearance {distance:.2f} m < {radius:.2f} m')
        clearance.append({'id':r['id'],'minSourceLandMetres':round(distance,3),'hullRadiusMetres':round(radius,3)})
    return routes,route_counts,clearance


def feather(frame, rim=None):
    # Transparent overlap rims preserve the full-resolution inner artwork.
    x=np.arange(frame.width);y=np.arange(frame.height)
    d=np.minimum(np.minimum(x,frame.width-1-x)[None,:],np.minimum(y,frame.height-1-y)[:,None])
    rim= rim if rim is not None else 65 if frame.key=='ferry-anchor' else 42
    t=np.clip(d/rim,0,1)
    return Image.fromarray(np.rint(t*t*(3-2*t)*255).astype('uint8'))


def compose_context(context, water, appearance):
    rgb=np.asarray(context).astype('float32')
    if appearance.startswith('rain'):
        rgb*=np.array([.74,.83,.88],dtype='float32')
        rgb+=np.array([1.,5.,8.],dtype='float32')
    if appearance in ('night','rain-night'):
        rgb*=np.array([.29,.39,.55],dtype='float32')
        rgb+=np.array([3.,5.,9.],dtype='float32')
    water_color={'day':(13,61,88),'night':(13,34,52),'rain-day':(31,68,80),'rain-night':(12,30,44)}[appearance]
    rgb[water]=np.asarray(water_color)+rgb[water,1,None]*.012
    return Image.fromarray(rgb.clip(0,255).astype('uint8')).resize((ATLAS.width,ATLAS.height),Image.Resampling.BILINEAR)


def artwork_path(frame, appearance):
    if frame.key=='ferry-anchor':
        return ROOT/f'assets/waterfront-{appearance}.png'
    return ROOT/f'assets/corridor/{frame.key}/{appearance}.png'


def write_manifest(out, extra):
    files=[{'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
           for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json']
    manifest={**extra,'files':files,'tileCount':sum('_files/' in f['path'] for f in files),
              'bytes':sum(f['bytes'] for f in files)}
    save_json(out/'manifest.json',manifest)
    return manifest


def build_waterfront():
    data=load_data()
    out=OUT/'waterfront';out.mkdir(parents=True,exist_ok=True)
    routes,cycles,clearance=routes_for_corridor(data)
    print('Source routes:',dict(Counter(r['kind'] for r in routes)),flush=True)
    raster=Raster(data,ATLAS,4)
    context=raster.draw(data)
    water=~raster.land
    Image.fromarray(pack_depth(raster.depth,raster.structure,DEPTH_ENCODING)).save(out/'depth.png')
    Image.fromarray(water.astype('uint8')*255).save(out/'water.png')
    Image.fromarray(raster.hard.astype('uint8')*255).save(out/'hard.png')
    windows={}
    for f in FRAMES:
        for w in json.loads((WORK/f'{f.key}-windows.json').read_text(encoding='utf-8')):
            windows[tuple(round(x,1) for x in w['p'])]=w
    lamps=[]
    for r in data['roads']:
        if not any(word in r['name'] for word in ('Embarcadero','Terry A Francois','King Street','North Point','Jefferson')):
            continue
        for a,b in zip(r['points'],r['points'][1:]):
            l=math.dist(a,b)
            for i in range(1,int(l/22)+1):
                t=min(.95,i*22/l)
                lamps.append([a[0]+(b[0]-a[0])*t+2.4,a[1]+(b[1]-a[1])*t,a[2]+5.1])
    scene={'release':'waterfront-v3','kind':'waterfront','assetRoot':'map/v3/waterfront/',
           'width':ATLAS.width,'height':ATLAS.height,'projection':ATLAS.projection(),
           'maskSize':[raster.w,raster.h],'depthEncoding':DEPTH_ENCODING,'clipDepth':8192,
           'extent':data['extent'],'originUTM':list(ORIGIN_UTM),'crs':'EPSG:32610',
           'sourceBuildings':len(data['buildings']),'routes':routes,'windows':list(windows.values()),
           'lamps':lamps,'landmarks':data['landmarks'],'defaultLocation':'ferry-building',
           'detailFrames':[asdict(f) for f in ART_FRAMES]}
    save_json(out/'scene.json',scene)
    art=[];context_art=[]
    # Draw the approved Ferry center last. Its inner image stays unchanged.
    frames=sorted(ART_FRAMES,key=lambda f:f.key=='ferry-anchor')
    for stem,appearance in APPEARANCES.items():
        im=compose_context(context,water,appearance)
        for frame in FRAMES:
            p=ROOT/f'assets/corridor/context/{frame.key}/{appearance}.png'
            tile=Image.open(p).convert('RGB')
            if tile.size!=(1536,1024):
                raise ValueError(f'Context appearance has wrong dimensions: {p}')
            context_art.append({'frame':frame.key,'appearance':appearance,'path':p.relative_to(ROOT).as_posix(),
                                'sha256':sha(p),'size':list(tile.size)})
            tile=tile.resize((frame.width,frame.height),Image.Resampling.BICUBIC)
            im.paste(tile,(frame.x-ATLAS.x,frame.y-ATLAS.y),feather(frame,32))
        for frame in frames:
            p=artwork_path(frame,appearance)
            tile=Image.open(p).convert('RGB')
            if tile.size!=(frame.width,frame.height):
                raise ValueError(f'Artwork must be native-size: {p.name}: {tile.size}')
            im.paste(tile,(frame.x-ATLAS.x,frame.y-ATLAS.y),feather(frame))
            art.append({'frame':frame.key,'appearance':appearance,'path':p.relative_to(ROOT).as_posix(),
                        'sha256':sha(p),'size':list(tile.size)})
        pyramid(im,out,stem)
    return write_manifest(out,{'release':scene['release'],'size':[ATLAS.width,ATLAS.height],
                  'maskSize':scene['maskSize'],'projection':scene['projection'],'artwork':art,'contextArtwork':context_art,
                  'detailFrames':[asdict(f) for f in ART_FRAMES],'routeCounts':dict(Counter(r['kind'] for r in routes)),
                  'newDirectedLoops':cycles,'shipClearance':clearance,'appearances':list(APPEARANCES)})


def build_bay():
    from bay_overview import build
    source=CACHE/'bay-render'
    build(source)
    out=OUT/'bay';out.mkdir(parents=True,exist_ok=True)
    for name in ('scene.json','depth.png','water.png','hard.png'):
        (out/name).write_bytes((source/name).read_bytes())
    for key in APPEARANCES:
        pyramid(Image.open(source/f'{key}.png').convert('RGB'),out,key)
    scene=json.loads((out/'scene.json').read_text(encoding='utf-8'))
    return write_manifest(out,{'release':scene['release'],'size':[scene['width'],scene['height']],
                     'maskSize':scene['maskSize'],'projection':scene['projection'],
                     'appearances':list(APPEARANCES),'sources':scene['sources']})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--only', choices=['bay','waterfront'])
    args=p.parse_args()
    if args.only!='bay':
        build_waterfront()
    if args.only!='waterfront':
        build_bay()
    if all((OUT/k/'manifest.json').exists() for k in ('waterfront','bay')):
        manifests={k:json.loads((OUT/k/'manifest.json').read_text(encoding='utf-8')) for k in ('waterfront','bay')}
        save_json(OUT/'atlas.json',{'version':'0.3.0','defaultScene':'waterfront','scenes':[
            {'id':k,'release':v['release'],'path':f'{k}/scene.json','manifest':f'{k}/manifest.json',
             'size':v['size'],'tileCount':v['tileCount'],'bytes':v['bytes']} for k,v in manifests.items()]})
    print('Atlas packaging complete',flush=True)


if __name__=='__main__':
    main()
