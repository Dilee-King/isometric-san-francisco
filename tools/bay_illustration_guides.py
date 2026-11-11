"""Register full-Bay ImageGen inputs to the existing orthographic camera."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

import numpy as np
from PIL import Image, ImageDraw
import pyogrio
import rasterio
from scipy.ndimage import map_coordinates
from shapely import make_valid
from shapely.geometry import box
from shapely.ops import transform, unary_union

from atlas_geometry import ORIGIN_UTM, SE, PixelFrame, camera_point, ground_point
from bay_overview import BAY, SCALE, earth_geometry, point, regional_dem
from corridor_inputs import ROOT, TO_GEO, fetch, local_xy, sha
from corridor_source import polygons

WORK = ROOT / ".local/full-bay"
ART = ROOT / "assets/full-bay"
FRAME = PixelFrame("full-bay", BAY.x * 2, BAY.y * 2, BAY.width * 2, BAY.height * 2)
REGIONAL_SCALE = SCALE * 2
AREA_SCALE = REGIONAL_SCALE * 8
TIGER = "https://www2.census.gov/geo/tiger/TIGER2025"
NAIP = "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage"
COUNTIES = ("001", "013", "041", "055", "075", "081", "085", "095", "097")
TILE_NAMES = (
    ("sonoma-coast", "petaluma-sonoma", "napa-valley", "solano-uplands"),
    ("point-reyes", "marin-san-pablo", "carquinez-suisun", "delta-north"),
    ("pacific-golden-gate", "central-bay", "diablo-concord", "antioch-delta"),
    ("san-mateo-coast", "peninsula-south-bay", "santa-clara-valley", "tri-valley"),
)
SPOTS = (
    ("sfo", "San Francisco International Airport", -122.3790, 37.6212),
    ("san-mateo-bridge", "San Mateo Bridge & Foster City", -122.2500, 37.5726),
    ("redwood-shores", "Redwood Shores & Bair Island", -122.2305, 37.5269),
    ("dumbarton-bridge", "Dumbarton Bridge & Baylands", -122.1187, 37.5066),
    ("alviso", "Alviso & the South Bay salt ponds", -121.9762, 37.4396),
    ("san-jose", "Downtown San Jose & SJC", -121.9060, 37.3510),
    ("oakland-airport", "Oakland Airport & San Leandro Bay", -122.2198, 37.7252),
    ("berkeley-marina", "Berkeley Marina & Emeryville", -122.3082, 37.8588),
    ("richmond-bridge", "Richmond Bridge & Point Richmond", -122.4090, 37.9290),
    ("san-rafael", "San Rafael & Canal District", -122.5120, 37.9650),
    ("vallejo", "Vallejo & Mare Island", -122.2698, 38.0957),
    ("benicia-martinez", "Benicia–Martinez Bridge", -122.1305, 38.0416),
    ("napa", "Downtown Napa & the Napa River", -122.2837, 38.2981),
    ("petaluma", "Petaluma River & downtown", -122.6386, 38.2310),
    ("point-reyes", "Point Reyes Headlands", -122.9830, 37.9952),
    ("half-moon-bay", "Half Moon Bay & Pillar Point", -122.4810, 37.4880),
)


def source_bounds(frame, scale):
    local = [ground_point(x, y, 0, scale) for x in (frame.x, frame.right)
             for y in (frame.y, frame.bottom)]
    e, n = zip(*local)
    utm = (min(e) + ORIGIN_UTM[0], min(n) + ORIGIN_UTM[1],
           max(e) + ORIGIN_UTM[0], max(n) + ORIGIN_UTM[1])
    lon, lat = zip(*(TO_GEO.transform(x + ORIGIN_UTM[0], y + ORIGIN_UTM[1]) for x, y in local))
    return utm, (min(lon) - .01, min(lat) - .01, max(lon) + .01, max(lat) + .01)


def coordinates(frame, scale):
    x = (np.arange(frame.width, dtype="float32")[None, :] + frame.x + .5) / scale
    y = (np.arange(frame.height, dtype="float32")[:, None] + frame.y + .5) / (scale * SE)
    return .8 * x + .6 * y + ORIGIN_UTM[0], .6 * x - .8 * y + ORIGIN_UTM[1]


def source_raster(path, frame, scale, bands, *, order=1):
    east, north = coordinates(frame, scale)
    with rasterio.open(path) as source:
        if source.crs is None or source.crs.to_epsg() != 32610:
            raise ValueError(f"Expected UTM zone 10 imagery: {path}")
        inverse = ~source.transform
        col = inverse.a * east + inverse.b * north + inverse.c - .5
        row = inverse.d * east + inverse.e * north + inverse.f - .5
        return [map_coordinates(source.read(band), [row, col], order=order, mode="nearest")
                for band in bands]


def mask(geometry, frame, scale):
    out = Image.new("L", (frame.width, frame.height))
    draw = ImageDraw.Draw(out)

    def pixels(ring):
        return [(x - frame.x, y - frame.y) for x, y, _ in
                (camera_point((*xy, 0), scale) for xy in ring.coords)]

    for polygon in polygons(geometry):
        draw.polygon(pixels(polygon.exterior), fill=255)
        for ring in polygon.interiors:
            draw.polygon(pixels(ring), fill=0)
    return out


def boundaries():
    _, bounds = source_bounds(FRAME, REGIONAL_SCALE)
    land = earth_geometry("land", bounds)
    urban = earth_geometry("urban", bounds)
    names = [f"tl_2025_06{county}_areawater.zip" for county in COUNTIES]
    with ThreadPoolExecutor(max_workers=6) as pool:
        paths = list(pool.map(lambda name: fetch(f"{TIGER}/AREAWATER/{name}", name, cache=WORK), names))
    water = []
    for path in paths:
        data = pyogrio.read_dataframe(path, columns=["MTFCC"], bbox=bounds)
        water.extend(transform(local_xy, make_valid(geometry)) for geometry in data.geometry
                     if geometry is not None and not geometry.is_empty)
    roads = fetch(f"{TIGER}/PRIMARYROADS/tl_2025_us_primaryroads.zip",
                  "tl_2025_us_primaryroads.zip", cache=WORK)
    source = pyogrio.read_dataframe(roads, bbox=bounds, columns=["FULLNAME", "RTTYP"])
    lines = []
    for record in source.itertuples():
        geometry = record.geometry
        if geometry is not None:
            geometry = geometry.intersection(box(*bounds))
            for line in geometry.geoms if geometry.geom_type == "MultiLineString" else [geometry]:
                if line.geom_type == "LineString" and line.length > 0:
                    lines.append((record.FULLNAME, record.RTTYP, transform(local_xy, line)))
    return land.difference(unary_union(water)), urban, lines, [*paths, roads]


def placements():
    plates = []
    for row, y in enumerate((0, 856, 1704, 2560)):
        for column, x in enumerate((0, 1192, 2392, 3584)):
            plates.append({"id": TILE_NAMES[row][column], "frame": [x, y, 1536, 1024],
                           "row": row, "column": column, "kind": "regional"})
    for identifier, name, lon, lat in SPOTS:
        x, y, _ = camera_point(point(lon, lat), AREA_SCALE)
        x = round((x - FRAME.x * 8) / 8) * 8
        y = round((y - FRAME.y * 8) / 8) * 8
        plates.append({"id": f"detail-{identifier}", "name": name, "kind": "detail",
                       "frame": [x - 768, y - 512, 1536, 1024], "lonLat": [lon, lat]})
    return plates


def aerial(row):
    left, top, width, height = row["frame"]
    frame = PixelFrame(row["id"], left + FRAME.x * 8, top + FRAME.y * 8, width, height)
    bounds, _ = source_bounds(frame, AREA_SCALE)
    w, s, e, n = bounds
    path = WORK / "aerial" / f"{row['id']}-2200.tif"
    if not path.is_file() or path.stat().st_size < 10000:
        pixels_per_metre = min(.53, 1300 / max(e - w, n - s))
        path = fetch(NAIP, f"{row['id']}-1300.tif", {
        "bbox": ",".join(str(value) for value in bounds), "bboxSR": "32610", "imageSR": "32610",
        "size": f"{round((e-w)*pixels_per_metre)},{round((n-s)*pixels_per_metre)}", "format": "tiff",
        "interpolation": "RSP_BilinearInterpolation", "f": "image",
        }, cache=WORK / "aerial")
    pixels = np.stack(source_raster(path, frame, AREA_SCALE, (1, 2, 3)), axis=-1).astype("uint8")
    Image.fromarray(pixels).save(WORK / "guides" / f"{row['id']}.png")
    return row["id"], sha(path)


def extend(ids):
    """Copy registered overlap bands from the completed neighboring artwork."""
    plates = [row for row in placements() if row["kind"] == "regional"]
    finished = [row for row in plates if (ART / "plates" / f"{row['id']}.png").is_file()]
    for row in plates:
        if row["id"] not in ids:
            continue
        x, y, w, h = row["frame"]
        source = WORK / "guides" / f"{row['id']}.png"
        with Image.open(source) as geometry:
            guide = geometry.convert("RGB")
        for anchor in sorted(finished, key=lambda plate: (
            -(abs(plate["column"] - row["column"]) + abs(plate["row"] - row["row"])), plate["id"]
        )):
            ax, ay, aw, ah = anchor["frame"]
            left, top, right, bottom = max(x, ax), max(y, ay), min(x+w, ax+aw), min(y+h, ay+ah)
            if left >= right or top >= bottom or row["id"] == anchor["id"]:
                continue
            with Image.open(ART / "plates" / f"{anchor['id']}.png") as image:
                guide.paste(image.crop((left-ax, top-ay, right-ax, bottom-ay)), (left-x, top-y))
        guide.save(WORK / "guides" / f"{row['id']}-extend.png")


def regional():
    guide_path = WORK / "guides"
    guide_path.mkdir(parents=True, exist_ok=True)
    land_geometry, urban_geometry, roads, inputs = boundaries()
    land = np.asarray(mask(land_geometry, FRAME, REGIONAL_SCALE)) > 0
    urban = (np.asarray(mask(urban_geometry, FRAME, REGIONAL_SCALE)) > 0) & land
    dem_path, _ = regional_dem()
    elevation, = source_raster(dem_path, FRAME, REGIONAL_SCALE, (1,))
    elevation = np.where(land, elevation.clip(0, 2100), 0)
    dy, dx = np.gradient(elevation)
    slope = (dx * .95 - dy * 1.15).clip(-38, 38)
    relief = (elevation / 850).clip(0, 1)
    terrain = np.array([188, 184, 139]) - relief[..., None] * [77, 54, 54] + slope[..., None]
    cities = np.array([209, 192, 169]) + slope[..., None] * .2
    guide = Image.fromarray(np.where(land[..., None], np.where(urban[..., None], cities, terrain),
                                     [38, 92, 118]).clip(0, 255).astype("uint8"))
    draw = ImageDraw.Draw(guide)
    for _, route_type, line in roads:
        pixels = [camera_point((*xy, 0), REGIONAL_SCALE) for xy in line.coords]
        draw.line([(x - FRAME.x, y - FRAME.y) for x, y, _ in pixels],
                  fill=(130, 116, 95), width=3 if route_type == "I" else 2)
    # Visible runway axes distinguish the airport platforms from nearby salt ponds.
    for a, b in (
        ((-122.3750, 37.6280), (-122.3509, 37.6103)),
        ((-122.3835, 37.6138), (-122.3586, 37.6201)),
        ((-122.2299, 37.7280), (-122.1941, 37.7104)),
        ((-121.9378, 37.3753), (-121.9185, 37.3538)),
    ):
        pixels = [camera_point(point(*xy), REGIONAL_SCALE) for xy in (a, b)]
        draw.line([(x - FRAME.x, y - FRAME.y) for x, y, _ in pixels], fill=(113, 112, 105), width=5)
    guide.save(guide_path / "region.png")
    for row in placements():
        if row["kind"] == "regional":
            x, y, w, h = row["frame"]
            guide.crop((x, y, x + w, y + h)).save(guide_path / f"{row['id']}.png")
    Image.fromarray(land.astype("uint8") * 255).save(WORK / "land.png")
    Image.fromarray(urban.astype("uint8") * 255).save(WORK / "urban.png")
    np.save(WORK / "elevation.npy", elevation)
    data = {
        "originUTM": list(ORIGIN_UTM), "projection": FRAME.projection(REGIONAL_SCALE),
        "frame": [FRAME.x, FRAME.y, FRAME.width, FRAME.height], "plates": placements(),
        "inputs": {path.name: sha(path) for path in [*inputs, dem_path]},
    }
    (WORK / "layout.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Regional guides: {FRAME.width} × {FRAME.height}; {len(roads)} Census road segments", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aerial", nargs="*", help="Prepare these local aerial guides, or all if empty")
    parser.add_argument("--extend", nargs="+", help="Create a guide with accepted neighboring art")
    args = parser.parse_args()
    (WORK / "guides").mkdir(parents=True, exist_ok=True)
    if args.extend:
        extend(args.extend)
        return
    if args.aerial is None:
        regional()
        return
    rows = [row for row in placements() if row["kind"] == "detail"
            and (not args.aerial or row["id"] in args.aerial)]
    provenance = WORK / "aerial-inputs.json"
    results = {}
    failures = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(aerial, row): row["id"] for row in rows}
        for future in as_completed(futures):
            identifier = futures[future]
            try:
                key, digest = future.result()
                results[key] = digest
            except (OSError, ValueError) as error:
                failures.append(identifier)
                print(f"{identifier}: {error}", flush=True)
    previous = json.loads(provenance.read_text(encoding="utf-8")) if provenance.is_file() else {}
    provenance.write_text(json.dumps(previous | results, indent=2), encoding="utf-8")
    print(f"Aerial guides: {len(results)}", flush=True)
    if failures:
        raise SystemExit(f"Missing aerial guides: {', '.join(failures)}")


if __name__ == "__main__":
    main()
