"""Acquire only the new western corridor's public source inputs."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json

import rasterio

from atlas_geometry import ORIGIN_UTM
from bay_overview import DEM_URL
from corridor_inputs import FOOTPRINTS, ROOT, fetch, geographic_bbox, osm_vectors, sha

CACHE = ROOT / '.local/golden-gate-inputs'
# Includes the Pacific bluffs, bridge landfalls, and an overlap with v0.3.
EXTENT = (-9800., -2450., -2100., 5550.)


def buildings():
    dest = CACHE/'western-footprints.geojson'
    if dest.is_file():
        return dest
    w,s,e,n = geographic_bbox(extent=EXTENT)
    features = []
    size = 12500
    for index in range(10):
        path = fetch(FOOTPRINTS,f'footprints-page-{index}.geojson',{
            '$where':f'within_box(shape,{n},{w},{s},{e})',
            '$limit':size,'$offset':index*size,'$order':'sf16_bldgid',
        },cache=CACHE)
        page = json.loads(path.read_text(encoding='utf-8'))
        if page.get('type') != 'FeatureCollection':
            raise ValueError('Expected a DataSF FeatureCollection')
        features.extend(page['features'])
        if len(page['features']) < size:
            break
    else:
        raise ValueError('DataSF footprint pagination did not terminate')
    ids = {f['properties'].get('sf16_bldgid',f.get('id')) for f in features}
    if not features or len(ids)!=len(features):
        raise ValueError(f'Nonunique DataSF footprint IDs ({len(ids)} for {len(features)})')
    dest.write_text(json.dumps({'type':'FeatureCollection','features':features},separators=(',',':')),encoding='utf-8')
    print(f'DataSF: {len(features):,} footprint records across {index+1} pages',flush=True)
    return dest


def terrain():
    e, n = ORIGIN_UTM
    west, south, east, north = EXTENT
    bounds = [west+e-30, south+n-30, east+e+30, north+n+30]
    path = fetch(DEM_URL, 'terrain.tif', {
        'bbox': ','.join(map(str, bounds)), 'bboxSR': 32610, 'imageSR': 32610,
        'size': '778,808', 'format': 'tiff', 'pixelType': 'F32',
        'interpolation': 'RSP_BilinearInterpolation', 'f': 'image',
    }, cache=CACHE)
    with rasterio.open(path) as ds:
        if ds.crs.to_epsg() != 32610 or min(ds.shape) < 700 or ds.count != 1:
            raise ValueError(f'Unexpected DEM grid {ds.crs} {ds.shape} with {ds.count} bands')
    return path


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = {
            'footprints': pool.submit(buildings),
            'osm': pool.submit(osm_vectors, cache=CACHE, extent=EXTENT),
            'terrain': pool.submit(terrain),
        }
        paths = {key: task.result() for key, task in tasks.items()}
    audit = {
        'retrievedUTC': datetime.now(timezone.utc).isoformat(),
        'bboxLonLat': list(geographic_bbox(extent=EXTENT)),
        'extentLocalMetres': list(EXTENT),
        'inputs': {k: {'name': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)}
                   for k, p in paths.items()},
        'sources': {'footprints': FOOTPRINTS, 'terrain': DEM_URL},
    }
    (CACHE/'inputs.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == '__main__':
    main()
