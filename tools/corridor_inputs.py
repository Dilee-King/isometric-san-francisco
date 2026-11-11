"""Bounded public-source acquisition. Raw responses stay in the local cache."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import laspy
import numpy as np
from pyproj import Transformer
import requests

from atlas_geometry import ORIGIN_UTM

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.local/corridor-inputs'
EXTENT = (-3300., -4300., 2150., 2250.)
FOOTPRINTS = 'https://data.sfgov.org/resource/ynuv-fyni.geojson'
EPT = 'https://s3-us-west-2.amazonaws.com/usgs-lidar-public/CA_SanFrancisco_1_B23/'
OVERPASS = ('https://overpass.kumi.systems/api/interpreter', 'https://overpass-api.de/api/interpreter')
OSM_MAP = 'https://api.openstreetmap.org/api/0.6/map'
NE = {
    'land': 'https://naturalearth.s3.amazonaws.com/10m_physical/ne_10m_land.zip',
    'urban': 'https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_urban_areas.zip',
}
TO_UTM = Transformer.from_crs(4326, 32610, always_xy=True)
TO_GEO = Transformer.from_crs(32610, 4326, always_xy=True)
TO_MERC = Transformer.from_crs(32610, 3857, always_xy=True)
MERC_TO_UTM = Transformer.from_crs(3857, 32610, always_xy=True)
HEADERS = {'User-Agent': 'IsometricSanFrancisco/0.3 (bounded open-data waterfront atlas; https://github.com/Dilee-King/isometric-san-francisco)',
           'Accept-Encoding': 'gzip, deflate'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url, name, params=None, retries=2, *, cache=CACHE):
    path = cache / name
    if path.is_file():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=(12, 70))
            r.raise_for_status()
            temp = path.with_suffix(path.suffix + '.part')
            temp.write_bytes(r.content)
            temp.replace(path)
            return path
        except requests.RequestException:
            if attempt + 1 == retries:
                raise
            time.sleep(1 + attempt)
    raise AssertionError('request retry loop failed')


def local_xy(lon, lat, _z=None):
    x, y = TO_UTM.transform(lon, lat)
    return np.asarray(x)-ORIGIN_UTM[0], np.asarray(y)-ORIGIN_UTM[1]


def geographic_bbox(transformer=TO_GEO, *, extent=EXTENT):
    points = [transformer.transform(ORIGIN_UTM[0]+x, ORIGIN_UTM[1]+y)
              for x in extent[::2] for y in extent[1::2]]
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def footprints(*, cache=CACHE, extent=EXTENT):
    w, s, e, n = geographic_bbox(extent=extent)
    p = fetch(FOOTPRINTS, 'footprints.geojson',
              {'$where': f'within_box(shape,{n},{w},{s},{e})', '$limit': 30000, '$order': 'sf16_bldgid'}, cache=cache)
    data = json.loads(p.read_text(encoding='utf-8'))
    if data.get('type') != 'FeatureCollection' or not data['features'] or len(data['features']) >= 30000:
        raise ValueError('Unexpected or truncated DataSF footprint response')
    print(f'DataSF: {len(data["features"]):,} footprint records', flush=True)
    return p


def map_subset(w, s, e, n, suffix, *, cache=CACHE):
    path = fetch(OSM_MAP, f'osm/{suffix}.xml', {'bbox': f'{w},{s},{e},{n}'}, cache=cache)
    root = ET.parse(path).getroot()
    nodes = {n.attrib['id']: n for n in root.findall('node')}
    result = []
    for item in root:
        if item.tag not in ('node', 'way'):
            continue
        tags = {x.attrib['k']: x.attrib['v'] for x in item.findall('tag')}
        if item.tag == 'node' and tags.get('natural') == 'tree':
            result.append({'type': 'node', 'id': int(item.attrib['id']), 'tags': tags,
                           'lat': float(item.attrib['lat']), 'lon': float(item.attrib['lon'])})
        if item.tag != 'way' or not set(tags) & {'natural', 'man_made', 'highway', 'railway', 'leisure', 'landuse', 'building'}:
            continue
        refs = [n.attrib['ref'] for n in item.findall('nd')]
        if len(refs) < 2 or any(ref not in nodes for ref in refs):
            continue
        geom = [{'lat': float(nodes[ref].attrib['lat']), 'lon': float(nodes[ref].attrib['lon'])} for ref in refs]
        result.append({'type': 'way', 'id': int(item.attrib['id']), 'tags': tags, 'geometry': geom})
    return result


def osm_vectors(*, cache=CACHE, extent=EXTENT):
    dest = cache / 'osm.json'
    if not dest.is_file():
        w, s, e, n = geographic_bbox(extent=extent)
        bbox = f'({s},{w},{n},{e})'
        query = ('[out:json][timeout:55];('
                 + ''.join(f'way{tag}{bbox};' for tag in (
                     '["natural"~"^(coastline|water|wood|scrub)$"]',
                     '["man_made"~"^(pier|breakwater|groyne)$"]',
                     '["highway"]', '["railway"~"^(rail|tram|light_rail)$"]',
                     '["leisure"~"^(park|pitch|stadium|marina|garden)$"]',
                     '["landuse"~"^(grass|forest|meadow|recreation_ground|village_green|brownfield)$"]',
                     '["building"]'))
                 + f'node["natural"="tree"]{bbox};);out geom;')
        for k, server in enumerate(OVERPASS):
            try:
                raw = fetch(server, f'overpass-{k}.json', {'data': query}, retries=1, cache=cache)
                data = json.loads(raw.read_text(encoding='utf-8'))
                if len(data.get('elements', [])) > 100 and 'remark' not in data:
                    data['acquisition'] = {'endpoint': server, 'query': query}
                    dest.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
                    break
            except (requests.RequestException, ValueError):
                continue
        if not dest.is_file():
            # A bounded subdivision prevents the editing API's per-request
            # node ceiling. Request one small part at a time.
            elements = {}
            for row in range(4):
                for col in range(4):
                    for item in map_subset(w+(e-w)*col/4, s+(n-s)*row/4,
                                           w+(e-w)*(col+1)/4, s+(n-s)*(row+1)/4,
                                           f'{col}-{row}', cache=cache):
                        elements[(item['type'], item['id'])] = item
            data = {'elements': list(elements.values()), 'acquisition': {'endpoint': OSM_MAP, 'bbox': [w, s, e, n]}}
            dest.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    data = json.loads(dest.read_text(encoding='utf-8'))
    print(f'OSM: {len(data["elements"]):,} selected local elements', flush=True)
    return dest


def cube_bounds(bounds, key):
    depth, i, j, k = map(int, key.split('-'))
    size = (bounds[3]-bounds[0]) / 2**depth
    low = [bounds[d] + index*size for d, index in enumerate((i,j,k))]
    return low + [x+size for x in low]


def crop_lidar(reuse=None):
    dest = CACHE / 'corridor-lidar-d6.npz'
    if dest.is_file():
        return dest
    metadata = json.loads(fetch(EPT+'ept.json', 'ept.json').read_text(encoding='utf-8'))
    w, s, e, n = geographic_bbox(TO_MERC)
    query = (w, s, -20, e, n, 350)
    selected, seen, pending = set(), set(), ['0-0-0-0']
    while pending:
        parent = pending.pop()
        if parent in seen:
            continue
        seen.add(parent)
        hierarchy = json.loads(fetch(EPT+f'ept-hierarchy/{parent}.json', f'ept-hierarchy/{parent}.json').read_text(encoding='utf-8'))
        for key, count in hierarchy.items():
            if int(key.split('-')[0]) > 6:
                continue
            cube = cube_bounds(metadata['bounds'], key)
            if not all(cube[d] <= query[d+3] and query[d] <= cube[d+3] for d in range(3)):
                continue
            if count == -1:
                pending.append(key)
            elif count > 0:
                selected.add(key)
    if not selected:
        raise ValueError('No USGS EPT nodes intersect the corridor')
    print(f'USGS lidar: {len(selected)} intersecting depth <= 6 nodes', flush=True)

    def decode(key):
        previous = reuse / f'{key}.laz' if reuse else None
        path = previous if previous and previous.is_file() else fetch(EPT+f'ept-data/{key}.laz', f'ept-data/{key}.laz')
        laz = laspy.read(path)
        x, y, z = np.asarray(laz.x), np.asarray(laz.y), np.asarray(laz.z)
        keep = (x >= w) & (x <= e) & (y >= s) & (y <= n) & (z >= -20) & (z <= 350) & ~np.asarray(laz.withheld, dtype=bool)
        x, y = MERC_TO_UTM.transform(x[keep], y[keep])
        x, y = x-ORIGIN_UTM[0], y-ORIGIN_UTM[1]
        keep2 = (x >= EXTENT[0]) & (x <= EXTENT[2]) & (y >= EXTENT[1]) & (y <= EXTENT[3])
        return np.c_[x[keep2], y[keep2], z[keep][keep2]].astype('float32'), np.asarray(laz.classification)[keep][keep2], path.stat().st_size

    with ThreadPoolExecutor(max_workers=8) as pool:
        tiles = list(pool.map(decode, sorted(selected)))
    points = np.concatenate([t[0] for t in tiles])
    classes = np.concatenate([t[1] for t in tiles])
    audit = {'nodes': len(tiles), 'nodeBytes': sum(t[2] for t in tiles), 'points': len(points),
             'classCounts': {str(k): int(v) for k,v in zip(*np.unique(classes, return_counts=True))},
             'maxEptDepth': 6, 'sourceHorizontalCRS': 'EPSG:3857',
             'horizontalCRS': 'EPSG:32610', 'verticalDatum': 'NAVD88 metres; Z not reprojected'}
    np.savez(dest, points=points, classes=classes, audit=json.dumps(audit))
    print(f'USGS lidar: {len(points):,} clipped returns', flush=True)
    return dest


def acquire(reuse_ept=None):
    with ThreadPoolExecutor(max_workers=5) as pool:
        tasks = {'footprints': pool.submit(footprints, cache=CACHE),
                 'osm': pool.submit(osm_vectors, cache=CACHE),
                 'lidar': pool.submit(crop_lidar, reuse_ept)}
        tasks.update({k: pool.submit(fetch, url, f'ne-{k}.zip', cache=CACHE) for k,url in NE.items()})
        paths = {k: f.result() for k,f in tasks.items()}
    audit = {'retrievedUTC': datetime.now(timezone.utc).isoformat(), 'bboxLonLat': list(geographic_bbox()),
             'inputs': {k: {'name': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for k,p in paths.items()},
             'sources': {'footprints': FOOTPRINTS, 'lidar': EPT, **NE}}
    (CACHE/'inputs.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-ept', type=Path, help='Optional existing read-only LAZ directory')
    args = parser.parse_args()
    print(json.dumps(acquire(args.reuse_ept), indent=2))


if __name__ == '__main__':
    main()
