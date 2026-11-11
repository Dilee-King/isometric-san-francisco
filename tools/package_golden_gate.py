"""Package the continuous v4 waterfront, bridge and overview with immutable tiles."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import json

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from shapely.geometry import LineString

from atlas_geometry import ART_FRAMES, FRAMES, DEPTH_ENCODING, camera_point, pack_depth
from bay_overview import build as render_bay
from corridor_inputs import ROOT, sha
from golden_gate_geometry import ATLAS, BRIDGE_FRAME, DETAIL_FRAMES, WEST_ART, WEST_CONTEXT, BridgeProfile, coverage_frames
from golden_gate_lighting import lamps_for, tone
from golden_gate_routes import build_routes
from golden_gate_source import load
from offshore_water import water_weight, harmonize
from package_corridor import APPEARANCES, artwork_path, feather, pyramid, save_json, write_manifest
from paint_golden_gate import stamp_depth, overlay, add_reflections
from render_golden_gate import WORK, WestRaster

OUT = ROOT/'public/map/v4'
ART = ROOT/'assets/golden-gate'
STAGE = ROOT/'.local/golden-gate-package'
WATER_BLEND = {'nearPx':70,'farPx':285,'maskDivisor':4}


def crop_box(frame):
    x,y=ATLAS.local(frame.x,frame.y)
    return x,y,x+frame.width,y+frame.height


def prepare_waterfront():
    STAGE.mkdir(parents=True,exist_ok=True)
    out=OUT/'waterfront';out.mkdir(parents=True,exist_ok=True)
    data=load()
    routes,loops,clearance=build_routes(data)
    divisor=WATER_BLEND['maskDivisor']
    raster=WestRaster(data,ATLAS,divisor)
    context=raster.draw(data)
    rgb=np.asarray(context,dtype='float32')
    # Carry the terrain beyond the illustrated strip in a quieter palette.
    elevation=gaussian_filter(np.maximum(raster.height,0),2.3)
    dy,dx=np.gradient(elevation)
    relief=np.clip((dx*.64-dy*.81)*5.4,-44,38)
    earth=raster.land&(raster.structure==0)&(rgb[...,0]>rgb[...,2]*1.06)
    y,x=np.indices(raster.land.shape,dtype='float32')
    scrub=np.clip(elevation/155,0,1)
    grain=1.8*np.sin(x*.79+y*.54)+1.25*np.sin(x*.15-y*.29)
    modifier=np.dstack((relief+grain-27*scrub,relief+grain-12*scrub,relief+grain-17*scrub))
    rgb[earth]+=modifier[earth]
    Image.fromarray(np.rint(rgb).clip(0,255).astype('uint8')).save(STAGE/'context.png',compress_level=2)
    water=~raster.land
    Image.fromarray(water.astype('uint8')*255).save(STAGE/'sea.png')
    weights=water_weight(~water,WATER_BLEND['nearPx'],WATER_BLEND['farPx'],divisor)
    Image.fromarray(np.rint(weights*255).astype('uint8')).save(STAGE/'water-weight.png')
    bridge_lamps=stamp_depth(raster)
    Image.fromarray(pack_depth(raster.depth,raster.structure,DEPTH_ENCODING)).save(out/'depth.png')
    Image.fromarray((~raster.land).astype('uint8')*255).save(out/'water.png')
    Image.fromarray(raster.hard.astype('uint8')*255).save(out/'hard.png')
    old=json.loads((ROOT/'public/map/v3/waterfront/scene.json').read_text(encoding='utf-8'))
    windows={tuple(round(x,1) for x in w['p']):w for w in old['windows']}
    for frame in WEST_ART:
        for w in json.loads((WORK/f'{frame.key}-windows.json').read_text(encoding='utf-8')):
            key=tuple(round(x,1) for x in w['p'])
            windows.setdefault(key,w)
    lamps=lamps_for(data)
    save_json(STAGE/'lamps.json',lamps)
    save_json(STAGE/'routes-audit.json',{'newDirectedLoops':loops,'shipClearance':clearance})
    scene={'release':'waterfront-v4','kind':'waterfront','assetRoot':'map/v4/waterfront/',
           'width':ATLAS.width,'height':ATLAS.height,'projection':ATLAS.projection(),
           'maskSize':[raster.w,raster.h],'depthEncoding':DEPTH_ENCODING,'clipDepth':8192,
           'extent':data['extent'],'originUTM':data['originUTM'],'crs':data['crs'],
           'sourceBuildings':len(data['buildings']),'routes':routes,'windows':list(windows.values()),
           'lamps':old['lamps']+[[x,n,z+4.7] for x,n,z in lamps]+bridge_lamps,
           'landmarks':data['landmarks'],'defaultLocation':'ferry-building',
           'detailFrames':[asdict(f) for f in coverage_frames()]}
    save_json(out/'scene.json',scene)
    print(f'Masks and shared geometry prepared at {raster.w} × {raster.h}',flush=True)


def read_rgb(path,expected=(1536,1024)):
    im=Image.open(path).convert('RGB')
    if im.size!=expected:
        raise ValueError(f'{path}: expected {expected} but found {im.size}')
    return im


def base(appearance):
    rgb=np.asarray(Image.open(STAGE/'context.png'),dtype='float32')
    if appearance.startswith('rain'):
        rgb*=np.array([.76,.83,.89],dtype='float32')
        rgb+=np.array([2.,6.,9.],dtype='float32')
    if appearance.endswith('night'):
        rgb*=np.array([.30,.40,.52],dtype='float32')
        rgb+=np.array([3.,5.,8.],dtype='float32')
    return Image.fromarray(rgb.clip(0,255).astype('uint8')).resize((ATLAS.width,ATLAS.height),Image.Resampling.BILINEAR)


def paste(im,frame,tile,rim):
    if tile.size!=(frame.width,frame.height):
        tile=tile.resize((frame.width,frame.height),Image.Resampling.BICUBIC)
    im.paste(tile,ATLAS.local(frame.x,frame.y),feather(frame,rim))


def assemble(appearance, *, draft=False, blend=True):
    im=base(appearance)
    lamps=json.loads((STAGE/'lamps.json').read_text(encoding='utf-8'))
    for frame in FRAMES:
        old=ROOT/f'assets/corridor/context/{frame.key}/{appearance}.png'
        paste(im,frame,read_rgb(old),145)
    for frame in WEST_CONTEXT:
        path=ART/'context'/frame.key/'day.png'
        if path.is_file() or not draft:
            paste(im,frame,tone(read_rgb(path),appearance,frame,lamps),260)
    for frame in WEST_ART:
        day=ART/frame.key/'day.png'
        if day.is_file() or not draft:
            specific=ART/frame.key/f'{appearance}.png'
            selected=read_rgb(specific) if specific.is_file() else tone(read_rgb(day),appearance,frame,lamps)
            paste(im,frame,selected,79)
    for frame in sorted(ART_FRAMES,key=lambda f:f.key=='ferry-anchor'):
        paste(im,frame,read_rgb(artwork_path(frame,appearance), (frame.width,frame.height)),78 if frame.key!='ferry-anchor' else 65)
    if blend:
        alpha=Image.open(STAGE/'water-weight.png').resize(im.size,Image.Resampling.BILINEAR)
        for y in range(0,ATLAS.height,384):
            box=(0,y,ATLAS.width,min(y+384,ATLAS.height))
            w=np.asarray(alpha.crop(box),dtype='float32')/255
            if w.max()==0:
                continue
            rgb=np.asarray(im.crop(box))
            im.paste(Image.fromarray(harmonize(rgb,w,appearance,(ATLAS.x,ATLAS.y+y))),(0,y))
    box=crop_box(BRIDGE_FRAME)
    sea=Image.open(STAGE/'sea.png').resize(im.size,Image.Resampling.NEAREST).crop(box)
    patch=add_reflections(im.crop(box),sea,appearance)
    bridge=overlay(appearance)
    patch.paste(bridge,(0,0),bridge)
    im.paste(patch,box[:2])
    return im


def assemble_tiles(item):
    stem,appearance=item
    im=assemble(appearance)
    thumb=im.copy()
    thumb.thumbnail((1520,1520),Image.Resampling.LANCZOS)
    thumb.save(STAGE/f'assembled-{appearance}.jpg',quality=90)
    pyramid(im,OUT/'waterfront',stem)


def art_record(frame,appearance,path):
    return {'frame':frame.key,'appearance':appearance,'path':path.relative_to(ROOT).as_posix(),
            'sha256':sha(path),'size':list(read_rgb(path).size)}


def finalize_waterfront():
    out=OUT/'waterfront'
    scene=json.loads((out/'scene.json').read_text(encoding='utf-8'))
    audit=json.loads((STAGE/'routes-audit.json').read_text(encoding='utf-8'))
    east=[art_record(f,a,artwork_path(f,a)) for f in ART_FRAMES for a in APPEARANCES.values()]
    east_context=[art_record(f,a,ROOT/f'assets/corridor/context/{f.key}/{a}.png')
                  for f in FRAMES for a in APPEARANCES.values()]
    west=[art_record(f,a,ART/f.key/f'{a}.png') for f in WEST_ART for a in APPEARANCES.values()
          if (ART/f.key/f'{a}.png').is_file()]
    west_context=[art_record(f,'day',ART/'context'/f.key/'day.png') for f in WEST_CONTEXT]
    return write_manifest(out,{'release':scene['release'],'size':[ATLAS.width,ATLAS.height],
                          'maskSize':scene['maskSize'],'projection':scene['projection'],
                          'artwork':east,'contextArtwork':east_context,
                          'westernArtwork':west,'westernContextArtwork':west_context,
                          'westernSurfaceLighting':'registered lights and wet materials',
                          'detailFrames':[asdict(f) for f in coverage_frames()],
                          'bridgeProfile':asdict(BridgeProfile()),'waterBlend':WATER_BLEND,
                          'routeCounts':dict(Counter(r['kind'] for r in scene['routes'])),
                          'appearances':list(APPEARANCES),**audit})


def build_bay():
    source=STAGE/'bay';source.mkdir(parents=True,exist_ok=True)
    out=OUT/'bay';out.mkdir(parents=True,exist_ok=True)
    p=BridgeProfile()
    shape=LineString([camera_point(p.point(s))[:2] for s in range(p.start,p.end,15)]).buffer(64)
    render_bay(source,detail_frames=DETAIL_FRAMES,extra_coverage=shape,
               release='bay-overview-v4',asset_root='map/v4/bay/')
    for name in ('scene.json','depth.png','water.png','hard.png'):
        (out/name).write_bytes((source/name).read_bytes())
    for stem in APPEARANCES:
        pyramid(Image.open(source/f'{stem}.png').convert('RGB'),out,stem)
    scene=json.loads((out/'scene.json').read_text(encoding='utf-8'))
    return write_manifest(out,{'release':scene['release'],'size':[scene['width'],scene['height']],
                          'maskSize':scene['maskSize'],'projection':scene['projection'],
                          'appearances':list(APPEARANCES),'sources':scene['sources']})


def manifest():
    rows=[]
    for key in ('waterfront','bay'):
        m=json.loads((OUT/key/'manifest.json').read_text(encoding='utf-8'))
        rows.append({'id':key,'release':m['release'],'path':f'{key}/scene.json',
                     'manifest':f'{key}/manifest.json','size':m['size'],'tileCount':m['tileCount'],'bytes':m['bytes']})
    save_json(OUT/'atlas.json',{'version':'0.4.0','defaultScene':'waterfront','scenes':rows})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',nargs='?',default='all',choices=['all','prepare','tiles','bay','manifest','inspect'])
    p.add_argument('--jobs',type=int,default=4)
    args=p.parse_args()
    if args.stage in ('all','prepare'):
        prepare_waterfront()
    if args.stage in ('all','tiles'):
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            list(pool.map(assemble_tiles,APPEARANCES.items()))
        finalize_waterfront()
    if args.stage in ('all','bay'):
        build_bay()
    if args.stage in ('all','manifest'):
        manifest()
    if args.stage=='inspect':
        for a in ('day','rain-night'):
            im=assemble(a,draft=True)
            im.crop(crop_box(BRIDGE_FRAME)).resize((1400,1480),Image.Resampling.LANCZOS).save(STAGE/f'bridge-{a}.jpg',quality=93)
            im.thumbnail((1600,1600),Image.Resampling.LANCZOS)
            im.save(STAGE/f'draft-{a}.jpg',quality=92)


if __name__=='__main__':
    main()
