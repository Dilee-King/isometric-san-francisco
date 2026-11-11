"""Draw the source-derived regional atlas and its registered appearances."""

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pyogrio
import rasterio
from scipy.ndimage import distance_transform_edt, map_coordinates
from shapely import make_valid
from shapely.geometry import LineString, Point, box
from shapely.ops import transform, unary_union

from atlas_geometry import ART_FRAMES, CE, SE, ORIGIN_UTM, PixelFrame, camera_point, ground_point, pack_depth
from corridor_inputs import CACHE, NE, TO_GEO, fetch, local_xy, sha
from corridor_source import polygons

BAY = PixelFrame('bay', -1080, -930, 2560, 1792)
SCALE = .017
DEPTH = {'offset':160000,'range':320000}
DEM_URL = 'https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage'
CITIES = [
    ('Santa Rosa',-122.714,38.44),('Sonoma',-122.458,38.291),('Napa',-122.286,38.298),
    ('Petaluma',-122.636,38.233),('Novato',-122.57,38.107),('San Rafael',-122.531,37.974),
    ('Sausalito',-122.486,37.859),('San Francisco',-122.4194,37.7749),
    ('Richmond',-122.3477,37.9358),('Berkeley',-122.2727,37.8715),('Oakland',-122.271,37.804),
    ('Alameda',-122.243,37.766),('Vallejo',-122.256,38.105),('Concord',-122.031,37.978),
    ('Walnut Creek',-122.065,37.91),('Antioch',-121.805,38.005),('Fairfield',-122.041,38.249),
    ('San Mateo',-122.3255,37.563),('Redwood City',-122.236,37.486),('Palo Alto',-122.143,37.441),
    ('Hayward',-122.08,37.669),('Fremont',-121.989,37.548),('Livermore',-121.77,37.68),
    ('San Jose',-121.894,37.338),('Half Moon Bay',-122.429,37.464),('Point Reyes',-122.973,38.0),
]
AIRPORTS = [('SFO',-122.379,37.6212),('OAK',-122.221,37.7212),('SJC',-121.929,37.363)]
BRIDGES = [
    ('Golden Gate Bridge',[(-122.476,37.807),(-122.479,37.832)]),
    ('Bay Bridge',[(-122.386,37.79),(-122.365,37.809),(-122.351,37.818),(-122.318,37.826)]),
    ('Richmond–San Rafael',[(-122.485,37.943),(-122.438,37.931),(-122.387,37.937)]),
    ('San Mateo Bridge',[(-122.258,37.565),(-122.207,37.592),(-122.143,37.620)]),
    ('Dumbarton Bridge',[(-122.149,37.501),(-122.118,37.506),(-122.098,37.527)]),
    ('Carquinez Bridge',[(-122.226,38.050),(-122.221,38.071)]),
]
CONNECTORS = [
    [(-122.42,37.775),(-122.406,37.704),(-122.39,37.65),(-122.3255,37.563),(-122.236,37.486),(-122.143,37.441),(-122.08,37.41),(-121.99,37.391),(-121.894,37.338)],
    [(-122.271,37.804),(-122.24,37.75),(-122.16,37.72),(-122.08,37.669),(-121.989,37.548),(-121.936,37.433),(-121.894,37.338)],
    [(-122.271,37.804),(-122.30,37.87),(-122.3477,37.9358),(-122.32,37.99),(-122.226,38.05),(-122.221,38.071),(-122.256,38.105),(-122.18,38.17),(-122.041,38.249)],
    [(-122.479,37.832),(-122.486,37.859),(-122.531,37.974),(-122.57,38.107),(-122.636,38.233),(-122.714,38.44)],
    [(-122.271,37.804),(-122.205,37.844),(-122.112,37.88),(-122.065,37.91),(-122.031,37.978),(-121.805,38.005)],
    [(-122.065,37.91),(-121.958,37.78),(-121.875,37.70),(-121.77,37.68),(-121.989,37.548)],
]


def point(lon, lat, z=0):
    return [*map(float,local_xy(lon,lat)),z]


def pixel(p):
    x,y,_=camera_point(p,SCALE)
    return x-BAY.x,y-BAY.y


def font(size, bold=False):
    for path in [Path('C:/Windows/Fonts')/('segoeuib.ttf' if bold else 'segoeui.ttf'),
                 Path('/usr/share/fonts/truetype/dejavu')/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')]:
        if path.is_file():
            return ImageFont.truetype(path,size)
    return ImageFont.load_default(size=size)


def earth_geometry(kind, bounds):
    path=fetch(NE[kind],f'ne-{kind}.zip',cache=CACHE)
    data=pyogrio.read_dataframe(str(path),bbox=bounds)
    clip=box(*bounds)
    return unary_union([transform(local_xy,make_valid(g).intersection(clip)) for g in data.geometry if g is not None])


def mask(geom):
    im=Image.new('L',(BAY.width,BAY.height))
    draw=ImageDraw.Draw(im)
    for p in polygons(geom):
        draw.polygon([pixel((*q,0)) for q in p.exterior.coords],fill=255)
        for ring in p.interiors:
            draw.polygon([pixel((*q,0)) for q in ring.coords],fill=0)
    return np.asarray(im)>0


def regional_dem():
    corners=[ground_point(x,y,0,SCALE) for x in (BAY.x,BAY.right) for y in (BAY.y,BAY.bottom)]
    e,n=zip(*corners)
    bbox=[min(e)+ORIGIN_UTM[0]-900,min(n)+ORIGIN_UTM[1]-900,max(e)+ORIGIN_UTM[0]+900,max(n)+ORIGIN_UTM[1]+900]
    path=fetch(DEM_URL,'bay-dem.tif',{'bbox':','.join(map(str,bbox)),'bboxSR':'32610','imageSR':'32610',
               'size':'1600,1600','format':'tiff','pixelType':'F32','interpolation':'RSP_BilinearInterpolation','f':'image'},retries=1)
    return path,bbox


def build(out, *, detail_frames=ART_FRAMES, extra_coverage=None,
          release='bay-overview-v3', asset_root='map/v3/bay/'):
    out.mkdir(parents=True,exist_ok=True)
    corners=[ground_point(x,y,0,SCALE) for x in (BAY.x,BAY.right) for y in (BAY.y,BAY.bottom)]
    geo=[TO_GEO.transform(x+ORIGIN_UTM[0],y+ORIGIN_UTM[1]) for x,y in corners]
    lons,lats=zip(*geo);bounds=(min(lons)-.025,min(lats)-.025,max(lons)+.025,max(lats)+.025)
    land_geo=earth_geometry('land',bounds);urban_geo=earth_geometry('urban',bounds)
    land=mask(land_geo);urban=mask(urban_geo)&land
    if land.mean()<.25 or land.mean()>.95 or land_geo.covers(Point(*point(-122.32,37.84)[:2])):
        raise ValueError('Regional land/water geometry failed a Bay control point')
    dem_path,bbox=regional_dem()
    x=(np.arange(BAY.width,dtype='float32')+BAY.x)[None,:]
    y=(np.arange(BAY.height,dtype='float32')+BAY.y)[:,None]
    u,q=x/SCALE,y/(SCALE*SE)
    gx,gn=.8*u+.6*q,.6*u-.8*q
    with rasterio.open(dem_path) as ds:
        if ds.crs.to_epsg()!=32610:
            raise ValueError('Regional DEM did not use EPSG:32610')
        dem=ds.read(1,masked=True).filled(0)
        aff=~ds.transform
        cols=aff.a*(gx+ORIGIN_UTM[0])+aff.b*(gn+ORIGIN_UTM[1])+aff.c
        rows=aff.d*(gx+ORIGIN_UTM[0])+aff.e*(gn+ORIGIN_UTM[1])+aff.f
        h=map_coordinates(dem,[rows,cols],order=1,mode='constant',cval=0).clip(0,2100)
    h=np.where(land,h,0)
    dy,dx=np.gradient(h)
    relief=np.clip((dx*.48-dy*.71),-32,32)
    shelf=np.exp(-distance_transform_edt(~land)/18)
    grain=np.sin(x*.43+y*.21)*np.sin(x*.91-y*.63)
    bands=np.sin(h*.051)*2.3
    glint=np.sin(x*.63+y*1.28)*np.sin(x*.24-y*.056)
    top=np.minimum(h/780,1)
    terrain=(np.array([180,186,136])[None,None,:]-(top[...,None]*np.array([78,57,59]))
             +(relief+grain*2+bands)[...,None])
    city=np.array([202,191,163])+(relief*.25+grain*7)[...,None]
    day_land=np.where(urban[...,None],city,terrain)
    labels=[{'id':name.lower().replace(' ','-'),'name':name,'p':point(lon,lat,0)} for name,lon,lat in CITIES]
    bridge_names={name:[pixel(point(lon,lat,0)) for lon,lat in coords] for name,coords in BRIDGES}
    footprint=unary_union([box(f.x,f.y,f.right,f.bottom) for f in detail_frames])
    if extra_coverage is not None:
        footprint=footprint.union(extra_coverage)
    factor=SCALE/(2.55*1536/2112)
    coverage=[[(x*factor-BAY.x,y*factor-BAY.y) for x,y in p.exterior.coords] for p in polygons(footprint)]
    routes=[]
    for i,(name,coords) in enumerate(BRIDGES):
        pts=[point(*p,25) for p in coords]
        routes.append({'id':f'bay-car-{i}','kind':'car','points':pts+pts[-2::-1],'speed':32,'phase':11+i*13,
                       'color':['#e5b863','#d9ddc8','#6a9ea9'][i%3]})
    for i,(kind,coords) in enumerate([
        ('ferry',[(-122.398,37.821),(-122.386,37.849),(-122.349,37.846)]),
        ('cargo',[(-122.400,37.848),(-122.363,37.868),(-122.351,37.886)]),
        ('ferry',[(-122.347,37.692),(-122.295,37.669),(-122.239,37.643)]),
    ]):
        pts=[point(*p,.7) for p in coords]
        radius=(math.hypot(32.5,7.5) if kind=='cargo' else math.hypot(15.5,4.5))*38
        if LineString([p[:2] for p in pts]).distance(land_geo) < radius:
            raise ValueError(f'Regional vessel {i} has insufficient source-land clearance')
        routes.append({'id':f'bay-vessel-{i}','kind':kind,'points':pts+pts[-2::-1],
                       'speed':13 if kind=='ferry' else 8,'phase':300+i*255,'color':'#f1e5cc'})
    routes.extend([
        {'id':'bay-plane-0','kind':'plane','points':[point(-122.81,37.50,550),point(-121.89,38.08,1250)],'speed':150,'phase':16,'color':'#eee9d8'},
        {'id':'bay-plane-1','kind':'plane','points':[point(-121.67,37.49,850),point(-122.59,38.1,980)],'speed':150,'phase':8,'color':'#dfe5e1'},
    ])
    variants={'scene':(False,False),'night':(True,False),'rain-day':(False,True),'rain-night':(True,True)}
    for key,(night,wet) in variants.items():
        water_base=np.array([18,64,91] if not wet else [35,71,84])
        water=water_base+(shelf*13+glint*2.5)[...,None]*np.array([.45,1,1])
        ground=day_land.copy()
        if wet:
            ground=ground*np.array([.82,.87,.91]) + (grain*2.4)[...,None]
        if night:
            ground=ground*np.array([.32,.40,.54])
            water=water*np.array([.48,.54,.69])
            lamps=urban & ((np.sin(x*2.87+y*1.32)*np.cos(y*.91-x*1.69))>.82)
            ground[lamps]+=np.array([101,66,24])*(1.25 if wet else 1.)
        rgb=np.where(land[...,None],ground,water).clip(0,255).astype('uint8')
        im=Image.fromarray(rgb); draw=ImageDraw.Draw(im)
        for route in CONNECTORS:
            pp=[pixel(point(*p)) for p in route]
            draw.line(pp,fill=(96,101,83) if not night else (85,76,57),width=5,joint='curve')
            draw.line(pp,fill=(229,210,153) if not night else (176,132,69),width=2,joint='curve')
        for name,pp in bridge_names.items():
            draw.line(pp,fill=(43,62,69),width=7,joint='curve')
            draw.line(pp,fill=(224,206,160) if name!='Golden Gate Bridge' else (208,107,77),width=3,joint='curve')
        for ring in coverage:
            draw.line(ring,fill=(255,196,93),width=4,joint='curve')
        for label in labels:
            px,py=pixel(label['p'])
            primary=label['name'] in ('San Francisco','Oakland','San Jose','Santa Rosa','Napa','Fremont')
            r=4 if primary else 2.6
            ink=(243,240,221) if night else (29,44,43)
            outline=(17,30,36) if night else (215,219,177)
            draw.ellipse((px-r,py-r,px+r,py+r),fill=(245,200,111) if primary else ink)
            delta=(-11,-9) if label['name'] in ('San Francisco','San Mateo','Redwood City','Palo Alto','Half Moon Bay','Point Reyes','San Rafael') else (10,-7)
            draw.text((px+delta[0],py+delta[1]),label['name'],font=font(24 if primary else 19,primary),fill=ink,
                      anchor='ra' if delta[0]<0 else 'la',stroke_width=2,stroke_fill=outline)
        for name,lon,lat in AIRPORTS:
            px,py=pixel(point(lon,lat))
            draw.rounded_rectangle((px-21,py-12,px+21,py+12),radius=4,fill=(19,42,52),outline=(226,214,175))
            draw.text((px,py),name,font=font(16,True),fill=(240,232,204),anchor='mm')
        draw.text(pixel(point(-122.323,37.720)),'SAN FRANCISCO\nBAY',font=font(23,True),align='center',anchor='ma',fill=(184,211,213),stroke_width=1,stroke_fill=(28,64,78))
        draw.text((245,1170),'P A C I F I C  O C E A N',font=font(25),fill=(146,189,196))
        ax,ay=2380,1602
        draw.line((ax,ay,ax+45,ay-38),fill=(240,226,185),width=3)
        draw.polygon([(ax+45,ay-38),(ax+35,ay-36),(ax+42,ay-27)],fill=(240,226,185))
        draw.text((ax+51,ay-52),'N',font=font(21,True),fill=(240,226,185))
        im.save(out/f'{key}.png',compress_level=4)
    d=((y/SCALE+h*CE)/SE*CE+h*SE).astype('float32')
    Image.fromarray(pack_depth(d,np.zeros_like(h,dtype='uint8'),DEPTH)).resize((1280,896),Image.Resampling.NEAREST).save(out/'depth.png')
    Image.fromarray((~land).astype('uint8')*255).resize((1280,896),Image.Resampling.NEAREST).save(out/'water.png')
    Image.fromarray(urban.astype('uint8')*255).resize((1280,896),Image.Resampling.NEAREST).save(out/'hard.png')
    scene={'release':release,'kind':'bay','assetRoot':asset_root,'width':BAY.width,'height':BAY.height,
           'projection':BAY.projection(SCALE),'maskSize':[1280,896],'depthEncoding':DEPTH,
           'clipDepth':262144,'transportScale':38,'extent':bbox,'sourceBuildings':0,'routes':routes,'landmarks':labels,
           'lamps':[],'windows':[],'overviewCoverage':coverage,'originUTM':list(ORIGIN_UTM),'crs':'EPSG:32610',
           'sources':{'land':'Natural Earth 1:10m land','urban':'Natural Earth 1:10m urban areas',
                      'dem':DEM_URL,'demSHA256':sha(dem_path),'connectors':'illustrative named regional links'}}
    (out/'scene.json').write_text(json.dumps(scene,separators=(',',':')),encoding='utf-8')
    print(f'Bay overview: {BAY.width} × {BAY.height}, {len(labels)} towns, {len(routes)} simulated routes',flush=True)


if __name__=='__main__':
    build(CACHE/'bay-render')
