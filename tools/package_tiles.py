"""Package original artwork, deterministic DZI tiles and reviewed source routes."""
import hashlib
import json
import math
import random
import heapq
from pathlib import Path

from PIL import Image,ImageDraw
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union
from shapely import make_valid

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public/map/v2'


def water_route(start,end,land,clearance=7,in_view=lambda p:True):
    """A* plus visibility simplification; hull clearance includes every pier."""
    obstacle=land.buffer(clearance)
    grid=5
    nodes=[(x,n) for x in range(140,541,grid) for n in range(-500,551,grid) if in_view((x,n)) and not obstacle.contains(Point(x,n))]
    allowed=set(nodes)
    a=min(nodes,key=lambda p:math.dist(p,start));b=min(nodes,key=lambda p:math.dist(p,end))
    queue=[(0,a)];cost={a:0};parent={}
    while queue:
        _,p=heapq.heappop(queue)
        if p==b:break
        for dx,dn in [(grid,0),(-grid,0),(0,grid),(0,-grid),(grid,grid),(-grid,grid),(grid,-grid),(-grid,-grid)]:
            q=(p[0]+dx,p[1]+dn)
            if q not in allowed or LineString([p,q]).intersects(obstacle):continue
            c=cost[p]+math.hypot(dx,dn)
            if c<cost.get(q,float('inf')):
                cost[q]=c;parent[q]=p;heapq.heappush(queue,(c+math.dist(q,b),q))
    if b not in cost:raise ValueError('No navigable route with hull clearance')
    path=[b]
    while path[-1]!=a:path.append(parent[path[-1]])
    path.reverse();simple=[path[0]];i=0
    while i<len(path)-1:
        j=len(path)-1
        while j>i+1 and LineString([path[i],path[j]]).intersects(obstacle):j-=1
        simple.append(path[j]);i=j
    points=[[x,n,.7] for x,n in simple]
    return points+points[-2::-1]


def build_routes(scene):
    rng=random.Random(3821)
    graph={}
    for road in scene['roads']:
        points=road['points']
        for a,b in zip(points,points[1:]):
            a=tuple(round(v,1) for v in a[:2]);b=tuple(round(v,1) for v in b[:2])
            if math.dist(a,b)<2:continue
            if road['oneway']!='-1':graph.setdefault(a,[]).append(b)
            if road['oneway'] not in ['yes','1','true']:graph.setdefault(b,[]).append(a)
    nodes=list(graph);cycles=[];seen=set()
    def in_frame(p):
        cam=scene['projection'];x=cam['origin'][0]+cam['scale']*(.8*p[0]+.6*p[1]);y=cam['origin'][1]+cam['scale']*((.6*p[0]-.8*p[1])*cam['sinElevation']-3.4*cam['cosElevation'])
        return 15<x<scene['width']-15 and 15<y<scene['height']-15
    for attempt in range(6000):
        path=[rng.choice(nodes)]
        for _ in range(90):
            options=[v for v in graph.get(path[-1],[]) if len(path)<2 or v!=path[-2]]
            if not options:break
            nextp=rng.choice(options)
            if nextp in path:
                cycle=path[path.index(nextp):]+[nextp]
                length=sum(math.dist(a,b) for a,b in zip(cycle,cycle[1:]))
                key=tuple(sorted(cycle[:-1]))
                if len(cycle)>=4 and 90<length<1700 and key not in seen and sum(in_frame(p) for p in cycle)/len(cycle)>.65:
                    seen.add(key);cycles.append(cycle)
                break
            path.append(nextp)
        if len(cycles)>=40:break
    if not cycles:raise ValueError('No directed road cycles were found')
    routes=[]
    colors=['#f1e9d7','#d8c18d','#607d8b','#2d485c','#a55b48','#b5c0bf','#d29b44']
    for i in range(72):
        path=cycles[i%len(cycles)]
        shifted=[]
        for j,p in enumerate(path[:-1]):
            a=path[j-1] if j else path[-2];b=path[j+1]
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy) or 1
            shifted.append([p[0]+dy/length*1.55,p[1]-dx/length*1.55,3.4])
        shifted.append(shifted[0])
        routes.append({'id':f'car-{i}','kind':'car','points':shifted,'speed':4.5+i%5*.65,'phase':rng.random()*130,'dwell':2+i%4*.4,'color':colors[i%len(colors)]})
    ships=[('ferry-a','ferry',[[200,100,.7],[340,260,.7],[200,100,.7]],5.5,22,9),('ferry-b','ferry',[[240,-30,.7],[360,100,.7],[240,-30,.7]],5.9,50,11),('cargo-a','cargo',[[350,-75,.7],[400,210,.7],[350,-75,.7]],3.3,30,0)]
    land=unary_union([Polygon(p[0],p[1:]) for p in scene['land']])
    for name,kind,points,speed,phase,dwell in ships:
        points=water_route(points[0][:2],points[len(points)//2][:2],land,18 if kind=='ferry' else 35,in_frame)
        line=LineString([p[:2] for p in points])
        if line.intersection(land).length>.25:raise ValueError(f'{name} intersects source land/pier: {line.intersection(land).length:.1f} m')
        routes.append({'id':name,'kind':kind,'points':points,'speed':speed,'phase':phase,'dwell':dwell,'color':'#ebe8d9'})
    routes.append({'id':'plane-0','kind':'plane','points':[[-650,-620,270],[660,450,270]],'speed':49,'phase':17,'color':'#ecede6'})
    return routes,len(cycles)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    artwork=ROOT/'assets/waterfront-day.png'
    image=Image.open(artwork).convert('RGB')
    scene=json.loads((ROOT/'data/source/scene.json').read_text())
    w,h=image.size;sx,sy=w/scene['width'],h/scene['height']
    if abs(sx-sy)>1e-6:raise ValueError('Artwork changed aspect ratio; explicit registration required')
    scene['sourceRegistration']={'method':'same aspect frame scaling from offline geometry; local AI drawing drift remains','scale':[sx,sy],'independentAccuracy':None}
    scene['width'],scene['height']=w,h
    scene['release']='waterfront-v2'
    for landmark in scene['landmarks']:landmark.pop('nameZh',None)
    scene['projection']['scale']*=sx
    scene['projection']['origin']=[v*sx for v in scene['projection']['origin']]
    scene['routes'],cycles=build_routes(scene)
    for name in ['depth','water']:
        im=Image.open(ROOT/f'data/source/{name}.png')
        im.resize((w,h),Image.Resampling.NEAREST).save(OUT/f'{name}.png')
    source=json.loads((ROOT/'data/source/ferry.json').read_text())
    land=unary_union([Polygon(p[0],p[1:]) for p in source['land']])
    green=unary_union([Polygon(p[0],p[1:]) for p in source['greens']])
    footprints=[Polygon(p[0],p[1:]) for b in source['buildings'] for p in b['footprint']]
    mask_repairs=sum(not p.is_valid for p in footprints)
    buildings=unary_union([make_valid(p) if not p.is_valid else p for p in footprints])
    paved=land.difference(green).difference(buildings)
    hard=Image.new('L',(w,h));draw=ImageDraw.Draw(hard);cam=scene['projection']
    def px(p):
        x,n=p
        return (cam['origin'][0]+cam['scale']*(.8*x+.6*n),cam['origin'][1]+cam['scale']*((.6*x-.8*n)*cam['sinElevation']-3*cam['cosElevation']))
    for polygon in (list(paved.geoms) if hasattr(paved,'geoms') else [paved]):
        if polygon.is_empty:continue
        draw.polygon([px(p) for p in polygon.exterior.coords],fill=255)
        for ring in polygon.interiors:draw.polygon([px(p) for p in ring.coords],fill=0)
    hard.save(OUT/'hard.png')
    image.save(OUT/'day.webp',quality=94,method=6)
    tile_size=512;overlap=1;max_level=math.ceil(math.log2(max(w,h)))
    files=[]
    appearances=[]
    for stem,asset in [('scene','day'),('night','night'),('rain-day','rain-day'),('rain-night','rain-night')]:
        asset_path=ROOT/f'assets/waterfront-{asset}.png'
        layer=Image.open(asset_path).convert('RGB')
        if layer.size!=image.size:raise ValueError(f'{asset} dimensions differ from the registered frame')
        layer.save(OUT/f'{asset}.webp',quality=94,method=6)
        appearances.append({'stem':stem,'asset':str(asset_path.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(asset_path.read_bytes()).hexdigest(),'descriptor':f'{stem}.dzi','size':[w,h]})
        for level in range(max_level+1):
            divisor=2**(max_level-level)
            size=(math.ceil(w/divisor),math.ceil(h/divisor))
            scaled=layer.resize(size,Image.Resampling.LANCZOS)
            folder=OUT/f'{stem}_files'/str(level);folder.mkdir(parents=True,exist_ok=True)
            for row in range(math.ceil(size[1]/tile_size)):
                for col in range(math.ceil(size[0]/tile_size)):
                    box=(max(0,col*tile_size-overlap),max(0,row*tile_size-overlap),min(size[0],(col+1)*tile_size+overlap),min(size[1],(row+1)*tile_size+overlap))
                    path=folder/f'{col}_{row}.webp';scaled.crop(box).save(path,quality=94,method=6)
                    files.append({'path':str(path.relative_to(OUT)).replace('\\','/'),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        (OUT/f'{stem}.dzi').write_text(f'<?xml version="1.0" encoding="utf-8"?><Image TileSize="{tile_size}" Overlap="{overlap}" Format="webp" xmlns="http://schemas.microsoft.com/deepzoom/2008"><Size Width="{w}" Height="{h}"/></Image>',encoding='utf-8')
    (OUT/'scene.json').write_text(json.dumps(scene,separators=(',',':')),encoding='utf-8')
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name!='manifest.json':files.append({'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest={'release':'waterfront-v2','imageSize':[w,h],'generation':'Original dry day/night retained; registered wet day/night edits. All vehicle vertices are projected from world ENU.','appearances':appearances,'nativeDetailTilesPerAppearance':math.ceil(w/tile_size)*math.ceil(h/tile_size),'files':files,'sourceRoadCycles':cycles,'routeCounts':{k:sum(r['kind']==k for r in scene['routes']) for k in ['car','ferry','cargo','plane']},'shipClearanceMetres':{'ferry':18,'cargo':35},'hardSurfaceMask':'Illustrative paved ground from source land minus source greens/buildings, not measured imperviousness.'}
    manifest['maskGeometryRepairCount']=mask_repairs
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Packaged',image.size,len(files),'runtime assets /',sum('_files/' in f['path'] for f in files),'DZI tiles;',cycles,'directed road cycles; ship centreline/land check PASS')


if __name__=='__main__':main()
