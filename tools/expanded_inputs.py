"""Fetch bounded public inputs for the expanded atlas and record their hashes."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math

import rasterio
import requests

from atlas_geometry import ORIGIN_UTM
from bay_overview import DEM_URL
from corridor_inputs import FOOTPRINTS, OVERPASS, ROOT, fetch, geographic_bbox, osm_vectors, sha
from expanded_geometry import OSM_EXTENTS, SF_EXTENT, SOURCE_EXTENT

CACHE = ROOT / ".local/inner-bay-inputs"
PARKS = "https://data.sfgov.org/resource/gtr9-ntp6.geojson"


def footprint_pages():
    w, s, e, n = geographic_bbox(extent=SF_EXTENT)
    where = f"within_box(shape,{n},{w},{s},{e})"
    count_path = fetch(FOOTPRINTS.replace(".geojson", ".json"), "sf-footprints-count.json",
                       {"$select": "count(*) as count", "$where": where}, cache=CACHE)
    count = int(json.loads(count_path.read_text(encoding="utf-8"))[0]["count"])
    size = 10000
    fields = "shape,sf16_bldgid,hgt_median_m,gnd_mediancm,p2010_zmaxn88ft,mblr"

    def page(index):
        path = fetch(FOOTPRINTS, f"sf-footprints/page-{index:02d}.geojson",
                     {"$select": fields, "$where": where, "$order": "sf16_bldgid",
                      "$limit": size, "$offset": size * index}, cache=CACHE)
        response = json.loads(path.read_text(encoding="utf-8"))
        expected = min(size, count - index * size)
        if response.get("type") != "FeatureCollection" or len(response["features"]) != expected:
            raise ValueError(f"Footprint page {index} does not contain its {expected} records")
        print(f"DataSF footprint page {index + 1}: {expected:,} records", flush=True)
        return path

    with ThreadPoolExecutor(max_workers=3) as pool:
        pages = list(pool.map(page, range(math.ceil(count / size))))
    if count < 150000:
        raise ValueError(f"Citywide footprint response is incomplete: {count:,}")
    print(f"DataSF: {count:,} citywide records", flush=True)
    return {f"sf-footprints-{i:02d}": path for i, path in enumerate(pages)}


def terrain():
    west, south, east, north = SOURCE_EXTENT
    e, n = ORIGIN_UTM
    path = fetch(DEM_URL, "terrain.tif", {
        "bbox": ",".join(map(str, (west + e, south + n, east + e, north + n))),
        "bboxSR": 32610, "imageSR": 32610,
        "size": f"{math.ceil((east - west) / 12)},{math.ceil((north - south) / 12)}",
        "format": "tiff", "pixelType": "F32", "interpolation": "RSP_BilinearInterpolation", "f": "image",
    }, cache=CACHE)
    with rasterio.open(path) as data:
        if data.crs.to_epsg() != 32610 or min(data.shape) < 2000 or data.count != 1:
            raise ValueError(f"Unexpected inner Bay DEM {data.crs} {data.shape}")
        print(f"USGS terrain: {data.width} × {data.height} at {data.res[0]:.1f} m", flush=True)
    return path


def coastline():
    w, s, e, n = geographic_bbox(extent=SOURCE_EXTENT)
    query = f'[out:json][timeout:55];way["natural"="coastline"]({s},{w},{n},{e});out geom;'
    order = sorted(range(len(OVERPASS)), key=lambda index: not (CACHE / f"coast-{index}.json").is_file())
    for index in order:
        endpoint = OVERPASS[index]
        try:
            path = fetch(endpoint, f"coast-{index}.json", {"data": query}, retries=1, cache=CACHE)
            data = json.loads(path.read_text(encoding="utf-8"))
            if len(data.get("elements", ())) > 70 and "remark" not in data:
                print(f"OSM coastline: {len(data['elements']):,} ways", flush=True)
                return path
        except (requests.RequestException, ValueError):
            continue
    raise RuntimeError("No complete bounded OpenStreetMap coastline response")


def local_vectors():
    def collect(item):
        name, extent = item
        return name, osm_vectors(cache=CACHE / name, extent=extent)

    with ThreadPoolExecutor(max_workers=2) as pool:
        return dict(pool.map(collect, OSM_EXTENTS.items()))


def inland_water():
    query = '[out:json][timeout:35];nwr["name"~"^Lake Merced$"](37.708,-122.506,37.744,-122.471);out geom;'
    path = fetch(OVERPASS[-1], "lake-merced.json", {"data": query}, cache=CACHE)
    if not any(row.get("members") for row in json.loads(path.read_text(encoding="utf-8"))["elements"]):
        raise ValueError("Lake Merced multipolygon members were omitted")
    return path


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        tasks = {
            "footprints": pool.submit(footprint_pages),
            "terrain": pool.submit(terrain),
            "coastline": pool.submit(coastline),
            "inlandWater": pool.submit(inland_water),
            "parks": pool.submit(fetch, PARKS, "sf-parks.geojson", {"$limit": 5000}, cache=CACHE),
            "vectors": pool.submit(local_vectors),
        }
        paths = {name: task.result() for name, task in tasks.items()}
    paths = {**paths.pop("footprints"), **paths.pop("vectors"), **paths}
    manifest = {
        "builtUTC": datetime.now(timezone.utc).isoformat(), "crs": "EPSG:32610",
        "extentLocalMetres": SOURCE_EXTENT, "bboxLonLat": geographic_bbox(extent=SOURCE_EXTENT),
        "inputs": {key: {"path": path.relative_to(CACHE).as_posix(), "bytes": path.stat().st_size,
                         "sha256": sha(path)} for key, path in paths.items()},
        "sources": {"footprints": FOOTPRINTS, "parks": PARKS,
                    "coastlineAndVectors": "https://www.openstreetmap.org/copyright", "terrain": DEM_URL},
    }
    (CACHE / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Retained {len(paths)} source input files", flush=True)


if __name__ == "__main__":
    main()
