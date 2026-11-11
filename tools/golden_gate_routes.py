"""Extend the existing simulation with western road loops and a strait passage."""

from collections import Counter, defaultdict
import json
import math
import random

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from atlas_geometry import camera_point
from corridor_inputs import ROOT
from golden_gate_geometry import WEST_ART, BridgeProfile
from package_corridor import CAR_COLORS, CAR_TYPES, geo_point, image_point
from render_corridor import good_polygon


def side_lane(points,offset=1.35):
    result=[]
    for i,p in enumerate(points):
        a,b=points[max(0,i-1)],points[min(i+1,len(points)-1)]
        e,n=b[0]-a[0],b[1]-a[1]
        d=math.hypot(e,n) or 1.
        result.append([round(p[0]+n/d*offset,3),round(p[1]-e/d*offset,3),round(p[2]+.29,3)])
    return result


def west_cars(data, *, frames=WEST_ART, prefix="west"):
    graph=defaultdict(set)
    two_way=[]
    for r in data['roads']:
        if r['kind'] not in CAR_TYPES or r['tunnel']:
            continue
        oneway=r['oneway']
        for a,b in zip(r['points'],r['points'][1:]):
            a,b=tuple(round(v,1) for v in a),tuple(round(v,1) for v in b)
            if math.dist(a,b)<.8:
                continue
            if oneway!='-1':
                graph[a].add(b)
            if oneway not in ('yes','true','1'):
                graph[b].add(a)
        if oneway in ('no','false','0') and r['name']:
            two_way.append(r['points'])
    # Sort neighbours so the checked-in routes reproduce across Python builds.
    graph={p:sorted(edges) for p,edges in graph.items()}
    rng=random.Random(20261110)
    routes=[]
    report={}
    for f in frames:
        if f.key=='marin-landing':
            continue
        def inside(p):
            x,y,_=camera_point(p)
            return f.x+40<=x<f.right-40 and f.y+40<=y<f.bottom-40
        starts=[p for p in graph if inside(p)]
        loops=[];seen=set()
        for _ in range(1700 if starts else 0):
            path=[rng.choice(starts)]
            for _ in range(52):
                options=[x for x in graph.get(path[-1],()) if len(path)<2 or x!=path[-2]]
                if not options:
                    break
                p=rng.choice(options)
                if p in path:
                    loop=path[path.index(p):]+[p]
                    length=sum(math.dist(a,b) for a,b in zip(loop,loop[1:]))
                    key=tuple(sorted(loop[:-1]))
                    if len(loop)>4 and 75<length<1250 and key not in seen and sum(inside(x) for x in loop)/len(loop)>.75:
                        loops.append(loop);seen.add(key)
                    break
                path.append(p)
            if len(loops)>=10:
                break
        report[f.key]=len(loops)
        if not loops:
            candidates=[p for p in two_way if len(p)>2 and sum(inside(x) for x in p)>.62*len(p)]
            candidates=sorted(candidates,key=lambda p:sum(math.dist(a,b) for a,b in zip(p,p[1:])),reverse=True)[:3]
            loops=[[*p,*p[-2::-1]] for p in candidates]
        if not loops:
            continue
        count=20 if len(loops)>=6 else max(7,len(loops)*3)
        for i in range(count):
            loop=loops[i%len(loops)]
            lane=side_lane(loop)
            lane[-1]=lane[0]
            routes.append({'id':f'{prefix}-{f.key}-car-{i}','kind':'car','points':lane,
                           'speed':4.8+(i%4)*.73,'phase':rng.random()*130,'dwell':1.4+(i%3)*.37,
                           'color':CAR_COLORS[i%len(CAR_COLORS)]})
    return routes,report


def bridge_cars(profile):
    routes=[]
    for i in range(48):
        lane=profile.lanes[i%6]
        a=profile.approach_start+5.;b=profile.approach_end-5.
        stations=[a+(b-a)*j/180 for j in range(181)]
        if lane<0:
            stations.reverse()
        points=[list(profile.point(s,lane,profile.deck(s)+.33)) for s in stations]
        routes.append({'id':f'golden-gate-car-{i}','kind':'car','points':points,
                       'speed':17.4+i%4*1.4,'phase':6.+i//6*17.+i%6*1.81,
                       'color':CAR_COLORS[i%len(CAR_COLORS)]})
    return routes


def build_routes(data):
    old=json.loads((ROOT/'public/map/v3/waterfront/scene.json').read_text(encoding='utf-8'))
    profile=BridgeProfile()
    cars,loops=west_cars(data)
    routes=old['routes']+cars+bridge_cars(profile)
    for key,kind,geo,speed,phase in [
        ('golden-gate-cargo','cargo',[(-122.4970,37.8176),(-122.4805,37.8189),(-122.4665,37.8176),(-122.4395,37.8161)],6.4,244.),
        ('marina-ferry','ferry',[(-122.4665,37.8129),(-122.4465,37.8138),(-122.4304,37.8134),(-122.4159,37.8142)],8.4,123.),
    ]:
        pts=[geo_point(*p,.7) for p in geo]
        routes.append({'id':key,'kind':kind,'points':pts+pts[-2::-1],
                       'speed':speed,'phase':phase,'dwell':0,'color':'#e8e6db'})
    routes.append({'id':'golden-gate-overflight','kind':'plane',
                   'points':[image_point(-10950,-8240,335),image_point(-4900,-5890,335)],
                   'speed':53.,'phase':2.6,'color':'#efede3'})

    land=unary_union([good_polygon(r) for r in data['land']])
    obstacles=land.union(unary_union([Point(profile.point(s,z=0)[:2]).buffer(30)
                                      for s in (0,1280)]))
    clearance=[]
    for r in routes:
        if r['kind'] not in ('ferry','cargo'):
            continue
        radius=math.hypot(15.5,4.5) if r['kind']=='ferry' else math.hypot(32.5,7.5)
        minimum=LineString([p[:2] for p in r['points']]).distance(obstacles)
        if minimum<=radius:
            raise ValueError(f'{r["id"]}: {minimum:.2f} m source clearance <= {radius:.2f} m hull radius')
        clearance.append({'id':r['id'],'minSourceLandMetres':round(minimum,3),'hullRadiusMetres':round(radius,3)})
    print(f'Traffic: {dict(Counter(r["kind"] for r in routes))}; {len(cars)} new city cars; {loops}',flush=True)
    return routes,loops,clearance
