"""Derive reproducible local-metre shoreline, footprints, terrain and routes."""

from collections import Counter
from datetime import datetime, timezone
import gzip
import json
import math
from pathlib import Path

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.spatial import cKDTree
from shapely import contains_xy, make_valid
from shapely.geometry import LineString, Point, Polygon, box, shape
from shapely.ops import polygonize, transform, unary_union
from shapely.strtree import STRtree

from atlas_geometry import FRAMES, ORIGIN_LON_LAT, ORIGIN_UTM, camera_point
from corridor_inputs import CACHE, EXTENT, ROOT, local_xy, sha

OUT = ROOT / 'data/corridor'
ROI = box(*EXTENT)
LANDMARKS = [
    ('wharf', "Fisherman's Wharf", -122.4195, 37.8078, 8),
    ('pier-39', 'Pier 39', -122.4103, 37.8087, 8),
    ('pier-27', 'Pier 27', -122.4019, 37.8056, 12),
    ('exploratorium', 'Exploratorium', -122.3977, 37.8017, 11),
    ('ferry-building', 'Ferry Building', -122.3937, 37.7955, 22),
    ('financial-district', 'Financial District', -122.3980, 37.7948, 55),
    ('bay-bridge', 'Bay Bridge approach', -122.388414, 37.788288, 42),
    ('pier-30', 'Pier 30/32', -122.3854, 37.7847, 5),
    ('oracle-park', 'Oracle Park', -122.3892, 37.7786, 8),
    ('mission-rock', 'Mission Rock', -122.3873, 37.7712, 8),
    ('chase-center', 'Chase Center', -122.3873, 37.7680, 16),
    ('mission-bay', 'Mission Bay', -122.3863, 37.7653, 5),
]
HEIGHT_CLASSES = {'motorway': 22, 'trunk': 19, 'primary': 17, 'secondary': 13,
                  'tertiary': 10, 'residential': 8, 'unclassified': 8,
                  'living_street': 6, 'service': 5, 'footway': 2.7,
                  'pedestrian': 6, 'steps': 3, 'cycleway': 2.4, 'path': 2.2}


def polygons(geom):
    if geom.geom_type == 'Polygon':
        return [geom] if not geom.is_empty else []
    if hasattr(geom, 'geoms'):
        return [p for g in geom.geoms for p in polygons(g)]
    return []


def lines(geom):
    if geom.geom_type == 'LineString':
        return [geom] if not geom.is_empty else []
    if hasattr(geom, 'geoms'):
        return [p for g in geom.geoms for p in lines(g)]
    return []


def rings(geom, min_area=1.):
    return [[[[round(x, 2), round(y, 2)] for x,y in r.coords]
             for r in [p.exterior, *p.interiors]] for p in polygons(geom) if p.area >= min_area]


def number(value, default):
    try:
        v = float(str(value).strip().split()[0])
        return v if math.isfinite(v) else default
    except (TypeError, ValueError, IndexError):
        return default


def intersects_frame(geom, h=240, frames=FRAMES):
    x0, y0, x1, y1 = geom.bounds
    xy = [camera_point((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (0, h)]
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    return any(max(xs) >= f.x and min(xs) <= f.right and max(ys) >= f.y and min(ys) <= f.bottom for f in frames)


def terrain_from_lidar(ground):
    gx = np.linspace(EXTENT[0], EXTENT[2], math.ceil((EXTENT[2]-EXTENT[0])/24)+1)
    gy = np.linspace(EXTENT[1], EXTENT[3], math.ceil((EXTENT[3]-EXTENT[1])/24)+1)
    xx, yy = np.meshgrid(gx, gy)
    tree = cKDTree(ground[:, :2])
    dist, ix = tree.query(np.c_[xx.ravel(), yy.ravel()], k=8, workers=4)
    surface = np.median(ground[ix, 2], axis=1)
    surface[dist[:,0] > 130] = 2.5
    grid = np.clip(surface.reshape(xx.shape), -1.5, 180)
    interp = RegularGridInterpolator((gy, gx), grid, bounds_error=False, fill_value=2.5)

    def elevation(x, y):
        xy = np.broadcast_arrays(x, y)
        values = interp(np.stack((xy[1], xy[0]), axis=-1))
        return values.item() if xy[0].ndim == 0 else values

    return {'x': gx.tolist(), 'n': gy.tolist(), 'z': np.round(grid, 2).tolist()}, elevation


def derive(*, out=OUT, frames=FRAMES):
    out.mkdir(parents=True, exist_ok=True)
    def retained(geom, height=240):
        return intersects_frame(geom, height, frames)
    original = json.loads((ROOT/'data/source/ferry.json').read_text(encoding='utf-8'))
    former = {b['id']: b for b in original['buildings']}
    raw_osm = json.loads((CACHE/'osm.json').read_text(encoding='utf-8'))
    raw = json.loads((CACHE/'footprints.geojson').read_text(encoding='utf-8'))
    with np.load(CACHE/'corridor-lidar-d6.npz') as lidar:
        pts, cls = lidar['points'], lidar['classes']
        lidar_audit = json.loads(str(lidar['audit']))
    terrain, elevation = terrain_from_lidar(pts[cls == 2])
    selected_class = 6 if (cls == 6).sum() > 1000 else 1
    roof = pts[cls == selected_class]
    roof_tree = cKDTree(roof[:, :2])
    print('Terrain grid and roof search index ready', flush=True)

    coasts, piers, inland_water, green, parks, roads, trees, supplements = [], [], [], [], [], [], [], []
    repairs = Counter()
    for item in raw_osm['elements']:
        tags = item.get('tags', {})
        if item['type'] == 'node':
            if tags.get('natural') == 'tree':
                x, n = map(float, local_xy(item['lon'], item['lat']))
                if ROI.contains(Point(x,n)):
                    trees.append([round(x,2), round(n,2), 8., round(float(elevation(x,n)),2)])
            continue
        if item['type'] != 'way':
            continue
        geo = item.get('geometry', [])
        if len(geo) < 2:
            continue
        xy = np.column_stack(local_xy([c['lon'] for c in geo], [c['lat'] for c in geo])).tolist()
        line = LineString(xy)
        if not line.intersects(ROI):
            continue
        if tags.get('natural') == 'coastline':
            coasts.extend(lines(line.intersection(ROI)))
        polygon = Polygon(xy) if len(xy) >= 4 and xy[0] == xy[-1] else None
        if polygon is not None and not polygon.is_valid:
            polygon = make_valid(polygon)
            repairs['osmPolygons'] += 1
        if tags.get('man_made') in ('pier', 'breakwater', 'groyne'):
            pier = polygon if polygon is not None else line.buffer(number(tags.get('width'), 8.)/2, cap_style='flat')
            piers.extend(polygons(pier.intersection(ROI)))
        if polygon is not None and tags.get('natural') == 'water':
            inland_water.extend(polygons(polygon.intersection(ROI)))
        if polygon is not None and (
            tags.get('landuse') in ('grass','forest','meadow','recreation_ground','village_green')
            or tags.get('natural') in ('wood','scrub')
            or tags.get('leisure') in ('park','garden','pitch')
        ):
            green.extend(polygons(polygon.intersection(ROI)))
            if tags.get('sport') == 'baseball':
                parks.extend(polygons(polygon.intersection(ROI)))
        if polygon is not None and tags.get('building') and retained(polygon):
            supplements.append((item['id'], polygon.intersection(ROI), tags))
        kind = tags.get('highway') or (tags.get('railway') if tags.get('railway') in ('tram','rail','light_rail') else None)
        if kind and kind not in ('construction', 'proposed', 'razed', 'abandoned'):
            width = np.clip(number(tags.get('width'), HEIGHT_CLASSES.get(kind, 7)), 1.4, 30.)
            bridge = tags.get('bridge') not in (None, 'no')
            bridge_height = 42. if bridge and (tags.get('ref') == 'I 80' or 'Bay Bridge' in tags.get('name','')) else 0.
            for segment in lines(line.intersection(ROI)):
                if segment.length < 2 or not retained(segment, 55):
                    continue
                a = np.array(segment.coords)
                zs = np.asarray(elevation(a[:,0], a[:,1])).clip(1.7) + .18
                if bridge:
                    zs = np.maximum(zs+2.5, bridge_height)
                roads.append({'id': str(item['id']), 'name': tags.get('name',''), 'kind': kind,
                              'oneway': tags.get('oneway', 'yes' if tags.get('junction') == 'roundabout' else 'no'),
                              'bridge': bridge, 'tunnel': tags.get('tunnel') not in (None,'no'),
                              'width': round(float(width),2), 'points': np.round(np.c_[a,zs],2).tolist()})

    if not coasts:
        raise ValueError('Missing source coastline')
    pieces = list(polygonize(unary_union([ROI.boundary, *coasts])))
    main = [p for p in pieces if p.covers(Point(-2700, -1100))]
    if len(main) != 1 or not .22 < main[0].area/ROI.area < .85:
        raise ValueError(f'Coastline did not separate land and bay: {[round(p.area) for p in pieces]}')
    land = unary_union([main[0], *piers]).difference(unary_union(inland_water)).intersection(ROI)
    if not land.covers(Point(*map(float, local_xy(-122.4077,37.8005)))):
        raise ValueError('Mainland geometry does not contain North Beach control point')
    greens = unary_union(green).intersection(land)

    buildings, footprints = [], []
    def add_building(identity, geom, prop, source):
        if geom.is_empty or geom.area < 20 or not retained(geom, 260):
            return
        # Keep existing calibrated geometry where its Ferry reference applies.
        if identity in former:
            b = former[identity]
            buildings.append({**b, 'source': 'v0.2 calibrated source'})
            footprints.append(geom)
            return
        center = geom.representative_point()
        ground = max(1.7, float(elevation(center.x, center.y)))
        base_h = max(3., number(prop.get('hgt_median_m', prop.get('height')), number(prop.get('building:levels'), 3)*3.3))
        x0,y0,x1,y1 = geom.bounds
        x,y = (x0+x1)/2,(y0+y1)/2
        radius = math.hypot(x1-x0,y1-y0)/2
        ii = roof_tree.query_ball_point([x,y],radius)
        found = roof[ii]
        if len(found):
            found = found[contains_xy(geom, found[:,0], found[:,1]) & (found[:,2] > ground+2)]
        support = len(found)
        if support >= 8:
            typical, upper = np.quantile(found[:,2],[.52,.94])
            height = float(typical-ground)
            roof_max = float(upper)
        else:
            height, roof_max = base_h, ground+base_h
        buildings.append({'id': identity,'name': prop.get('name',''),'footprint': rings(geom),
                          'ground': round(ground,2),'height':round(max(2.8,height),2),
                          'roofMax':round(roof_max,2),'roofSupport':support,
                          'source': f'{source} / lidar envelope' if support >= 8 else f'{source} / height fallback',
                          'parts': []})
        footprints.append(geom)

    for f in raw['features']:
        geom = transform(local_xy, shape(f['geometry']))
        if not geom.is_valid:
            geom = make_valid(geom)
            repairs['DataSFPolygons'] += 1
        prop = f['properties']
        add_building(str(prop.get('sf16_bldgid', f.get('id',len(buildings)))),geom.intersection(ROI),prop,'DataSF')
    index = STRtree(footprints)
    for identity, geom, tags in supplements:
        if geom.is_empty or geom.area < 45:
            continue
        nearby = [footprints[i] for i in index.query(geom, predicate='intersects')]
        if nearby and geom.intersection(unary_union(nearby)).area > .28*geom.area:
            continue
        add_building(f'osm-{identity}',geom,tags,'OSM supplement')
    landmarks = [{'id': key, 'name': name, 'p': [*map(float,local_xy(lon,lat)),z], 'lonLat': [lon,lat]}
                 for key,name,lon,lat,z in LANDMARKS]
    audit = {'crs': 'EPSG:32610', 'originLonLat': list(ORIGIN_LON_LAT), 'originUTM': list(ORIGIN_UTM),
             'extentLocalMetres': list(EXTENT), 'builtUTC': datetime.now(timezone.utc).isoformat(),
             'inputManifest': json.loads((CACHE/'inputs.json').read_text(encoding='utf-8')),
             'osmAcquisition': raw_osm.get('acquisition'), 'osmBase': raw_osm.get('osm3s',{}).get('timestamp_osm_base'),
             'lidar': {**lidar_audit, 'roofClass': selected_class, 'roofMethod': 'class-filtered points inside footprints; median envelope, 94th percentile upper height'},
             'counts': {'buildings': len(buildings), 'roads':len(roads),'trees':len(trees),
                        'sourceFootprintRecords':len(raw['features']), 'buildingSupport':dict(Counter(b['source'] for b in buildings)),
                        'landPolygons':len(polygons(land)), 'pierPolygons':len(piers), 'landmarkPins':len(landmarks)},
             'sourceValidityRepairs':dict(repairs), 'landAreaM2':round(land.area,1),
             'licenses': {'DataSF':'PDDL','USGS':'US Government public domain','OSM':'ODbL 1.0','NaturalEarth':'public domain'}}
    result = {'crs':'EPSG:32610','originLonLat':list(ORIGIN_LON_LAT),'originUTM':list(ORIGIN_UTM),
              'extent':list(EXTENT),'terrain':terrain,'land':rings(land),'piers':rings(unary_union(piers)),
              'greens':rings(greens),'ballfields':rings(unary_union(parks)), 'buildings':buildings,
              'roads':roads,'trees':trees,'landmarks':landmarks}
    path = out/'source.json.gz'
    path.write_bytes(gzip.compress(json.dumps(result,separators=(',',':'),allow_nan=False).encode(),mtime=0))
    audit['derivedSourceSHA256'] = sha(path)
    (out/'provenance.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps({**audit['counts'],'derivedBytes':path.stat().st_size,'repairs':dict(repairs)},indent=2))


if __name__ == '__main__':
    derive()
