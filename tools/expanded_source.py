"""Derive registered citywide and shoreline geometry from the retained inputs."""

from collections import Counter
import gzip
import json
import math

import numpy as np
import rasterio
from scipy.interpolate import RegularGridInterpolator
from shapely import from_geojson, make_valid, prepare, transform
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, unary_union

from atlas_geometry import ORIGIN_UTM, camera_point
from corridor_inputs import ROOT, local_xy, sha
from corridor_source import HEIGHT_CLASSES, lines, number, polygons, rings
from expanded_geometry import OSM_EXTENTS, SOURCE_EXTENT
from expanded_inputs import CACHE

OUT = ROOT / "data/inner-bay"
SNAPSHOT = OUT / "source.json.gz"
ROI = box(*SOURCE_EXTENT)
SEEDS = {
    "sf": (-122.4470, 37.7550),
    "marin": (-122.4970, 37.8540),
    "east": (-122.2790, 37.8230),
    "alameda": (-122.2770, 37.7710),
    "bay-farm": (-122.2480, 37.7355),
    "yerba-buena": (-122.3666, 37.8104),
    "treasure-island": (-122.3702, 37.8251),
    "alcatraz": (-122.4230, 37.8267),
    "angel": (-122.4325, 37.8630),
    "belvedere": (-122.4685, 37.8720),
}
WALKWAYS = {"footway", "path", "steps", "track", "cycleway", "pedestrian", "bridleway"}


def metric_point(lon, lat):
    return Point(*map(float, local_xy(lon, lat)))


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def metric_geometry(geometry):
    return transform(from_geojson(json.dumps(geometry, separators=(",", ":"))), local_xy, interleaved=False)


def geographic_box(west, south, east, north):
    return Polygon([metric_point(lon, lat).coords[0] for lon, lat in
                    ((west, south), (east, south), (east, north), (west, north))])


def terrain(path):
    with rasterio.open(path) as dem:
        z = dem.read(1, masked=True).filled(2.6)[::-1]
        col = np.arange(dem.width) + .5
        row = np.arange(dem.height - 1, -1, -1) + .5
        x = dem.transform.c + col * dem.transform.a - ORIGIN_UTM[0]
        n = dem.transform.f + row * dem.transform.e - ORIGIN_UTM[1]
    z = np.clip(z, -2.5, 650)
    elevation = RegularGridInterpolator((n, x), z, bounds_error=False, fill_value=2.6)
    # Retain centimetre precision on the native 12 m sampling grid.
    return {"x": x.round(3).tolist(), "n": n.round(3).tolist(),
            "z": z.astype("float64").round(2).tolist()}, elevation


def osm_xy(row):
    coordinates = row.get("geometry", ())
    return np.column_stack(local_xy([p["lon"] for p in coordinates], [p["lat"] for p in coordinates]))


def coastline(path):
    shore = []
    for row in read(path)["elements"]:
        xy = osm_xy(row)
        if len(xy) >= 2:
            shore.extend(lines(LineString(xy).intersection(ROI)))
    pieces = list(polygonize(unary_union([ROI.boundary, *shore])))
    parts = {}
    for name, coordinates in SEEDS.items():
        point = metric_point(*coordinates)
        found = [piece for piece in pieces if piece.covers(point)]
        if found:
            parts[name] = found[0]
    required = {"sf", "marin", "east", "alameda", "yerba-buena", "treasure-island", "alcatraz"}
    if not required <= parts.keys():
        raise ValueError(f"Unclosed coastline at {sorted(required - parts.keys())}")
    land = unary_union(list(parts.values()))
    for coordinates in ((-122.385, 37.842), (-122.541, 37.755), (-122.333, 37.778)):
        if land.covers(metric_point(*coordinates)):
            raise ValueError(f"Source coastline classified open water as land at {coordinates}")
    return land, parts


def inland_water(path):
    outer, inner = [], []
    for row in read(path)["elements"]:
        for member in row.get("members", ()):
            xy = osm_xy(member)
            if len(xy) >= 2:
                (inner if member.get("role") == "inner" else outer).append(LineString(xy))
    lake = unary_union(list(polygonize(unary_union(outer)))).difference(
        unary_union(list(polygonize(unary_union(inner))))
    )
    if not lake.covers(metric_point(-122.49776, 37.72754)) or not 1e6 < lake.area < 1.3e6:
        raise ValueError("Lake Merced water polygons did not close")
    return lake


def image_bounds(geometry, lower, upper):
    west, south, east, north = geometry.bounds
    points = [camera_point((x, n, z)) for x in (west, east)
              for n in (south, north) for z in (lower, upper)]
    return [math.floor(min(point[0] for point in points)), math.floor(min(point[1] for point in points)),
            math.ceil(max(point[0] for point in points)), math.ceil(max(point[1] for point in points))]


def building(identity, geometry, height, ground, source):
    return {"id": identity, "footprint": rings(geometry), "ground": round(ground, 2),
            "height": round(height, 2), "source": source,
            "bounds": image_bounds(geometry, ground, ground + height)}


def datasf_buildings(paths, elevation, valid_area):
    result, seen = [], set()
    prepare(valid_area)
    for path in paths:
        features = read(path)["features"]
        valid = [row for row in features if row["geometry"]]
        geometries = from_geojson([json.dumps(row["geometry"], separators=(",", ":")) for row in valid])
        geometries = transform(geometries, local_xy, interleaved=False)
        for row, geometry in zip(valid, geometries):
            properties = row["properties"]
            identity = properties["sf16_bldgid"]
            if identity in seen:
                raise ValueError(f"Duplicate DataSF footprint {identity}")
            seen.add(identity)
            if geometry.is_empty or geometry.area < 9:
                continue
            center = geometry.representative_point()
            if not valid_area.covers(center):
                continue
            if not geometry.is_valid:
                geometry = make_valid(geometry)
            ground = float(elevation([[center.y, center.x]])[0])
            default_height = number(properties.get("p2010_zmaxn88ft"), (ground + 8) / .3048) * .3048 - ground
            height = float(np.clip(number(properties.get("hgt_median_m"), default_height), 2.7, 270))
            record = building(identity, geometry, height, max(1.1, ground), "DataSF footprint height")
            if record["footprint"]:
                result.append(record)
        print(f"{path.name}: {len(result):,} retained city structures", flush=True)
    return result, len(seen)


def osm_vectors(paths, land, sf_land, elevation):
    seen = set()
    prepare(land)
    prepare(sf_land)
    roads, buildings, trees, greens, pitches, beaches, piers, lakes = [], [], [], [], [], [], [], []
    for path in paths:
        for row in read(path)["elements"]:
            identity = (row["type"], row["id"])
            if identity in seen:
                continue
            seen.add(identity)
            tags = row.get("tags", {})
            if row["type"] == "node":
                if tags.get("natural") == "tree":
                    e, n = map(float, local_xy(row["lon"], row["lat"]))
                    if ROI.covers(Point(e, n)):
                        trees.append([round(e, 2), round(n, 2), 7.5, round(float(elevation([[n, e]])[0]), 2)])
                continue
            xy = osm_xy(row)
            if len(xy) < 2:
                continue
            line = LineString(xy)
            if not line.intersects(ROI):
                continue
            polygon = Polygon(xy) if len(xy) >= 4 and line.is_ring else None
            if polygon is not None and not polygon.is_valid:
                polygon = make_valid(polygon)
            if tags.get("man_made") in ("pier", "breakwater", "groyne"):
                pier = polygon if polygon is not None else line.buffer(number(tags.get("width"), 8) / 2, cap_style="flat")
                piers.extend(polygons(pier.intersection(ROI)))
            if polygon is not None:
                if tags.get("natural") == "water":
                    lakes.extend(polygons(polygon))
                if tags.get("natural") in ("beach", "sand"):
                    beaches.extend(polygons(polygon))
                if (tags.get("natural") in ("wood", "scrub")
                        or tags.get("leisure") in ("park", "garden", "pitch")
                        or tags.get("landuse") in ("grass", "forest", "meadow", "village_green", "recreation_ground")):
                    greens.extend(polygons(polygon))
                if tags.get("sport") in ("baseball", "soccer") and tags.get("leisure") == "pitch":
                    pitches.extend(polygons(polygon))
                if tags.get("building") and polygon.area > 16:
                    center = polygon.representative_point()
                    if land.covers(center) and not sf_land.covers(center):
                        ground = max(1.1, float(elevation([[center.y, center.x]])[0]))
                        height = float(np.clip(number(tags.get("height"), 3.3 * number(tags.get("building:levels"), 2.3)), 3, 160))
                        buildings.append(building(f"osm-{row['id']}", polygon, height, ground, "OpenStreetMap height or levels"))
            kind = tags.get("highway") or (tags.get("railway") if tags.get("railway") in ("tram", "rail", "light_rail") else None)
            if not kind or kind in ("construction", "proposed", "abandoned", "razed", "platform"):
                continue
            bridge = tags.get("bridge") not in (None, "no")
            tunnel = tags.get("tunnel") not in (None, "no")
            width = float(np.clip(number(tags.get("width"), HEIGHT_CLASSES.get(kind, 7)), 1.4, 32))
            for index, section in enumerate(lines(line.intersection(ROI))):
                if section.length < (5 if kind in WALKWAYS else 2):
                    continue
                points = np.asarray(section.coords)
                height = elevation(points[:, ::-1]).clip(1.05) + (.32 if kind not in WALKWAYS else .19)
                if bridge:
                    height += 2.5
                roads.append({"id": f"{row['id']}-{index}", "name": tags.get("name", ""),
                              "ref": tags.get("ref", ""), "kind": kind, "bridge": bridge, "tunnel": tunnel,
                              "layer": number(tags.get("layer"), 0), "width": round(width, 2),
                              "oneway": tags.get("oneway", "yes" if kind in ("motorway", "motorway_link") or tags.get("junction") == "roundabout" else "no"),
                              "points": np.column_stack((points, height)).round(2).tolist(),
                              "bounds": image_bounds(section, float(height.min()), float(height.max()))})
        print(f"{path.parent.name}: {len(roads):,} cumulative road segments, {len(trees):,} mapped trees", flush=True)
    return roads, buildings, trees, greens, pitches, beaches, piers, lakes


def derive():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = read(CACHE / "inputs.json")
    paths = {key: CACHE / row["path"] for key, row in manifest["inputs"].items()}
    surface, elevation = terrain(paths["terrain"])
    land, parts = coastline(paths["coastline"])
    # The mainland city limit follows the south side of the retained urban area.
    city = parts["sf"].intersection(geographic_box(-122.56, 37.7078, -122.34, 37.838))
    sf_land = unary_union([city, *(parts[name] for name in ("yerba-buena", "treasure-island", "alcatraz"))])
    roads, osm, trees, green, pitches, beaches, piers, lakes = osm_vectors(
        [paths[name] for name in OSM_EXTENTS], land, sf_land, elevation,
    )
    parks = [metric_geometry(row["geometry"]) for row in read(paths["parks"])["features"] if row["geometry"]]
    if len(parks) < 200:
        raise ValueError("Incomplete DataSF park layer")
    lake = inland_water(paths["inlandWater"])
    land = unary_union([land, *piers]).difference(unary_union([lake, *lakes]))
    green = unary_union([*green, *parks]).intersection(land)
    footprint_paths = [path for key, path in sorted(paths.items()) if key.startswith("sf-footprints-")]
    buildings, candidates = datasf_buildings(footprint_paths, elevation, sf_land.buffer(70))
    buildings.extend(osm)
    east_extent = geographic_box(-122.349, 37.763, -122.259, 37.830)
    marin_extent = geographic_box(-122.508, 37.824, -122.468, 37.876)
    coverage = {
        "6": rings(sf_land),
        "7": rings(land.intersection(east_extent)),
        "8": rings(land.intersection(marin_extent)),
    }
    result = {"crs": "EPSG:32610", "originUTM": ORIGIN_UTM, "extent": SOURCE_EXTENT,
              "terrain": surface, "land": rings(land), "greens": rings(green),
              "ballfields": rings(unary_union(pitches)), "beaches": rings(unary_union(beaches)),
              "piers": rings(unary_union(piers)), "coverage": coverage,
              "roads": roads, "buildings": buildings, "trees": trees}
    encoded = json.dumps(result, separators=(",", ":"), allow_nan=False).encode()
    pending = SNAPSHOT.with_suffix(".part")
    pending.write_bytes(gzip.compress(encoded, compresslevel=5, mtime=0))
    pending.replace(SNAPSHOT)
    report = {"inputManifest": manifest, "sourceSHA256": sha(SNAPSHOT), "footprintCandidates": candidates,
              "buildings": dict(Counter(record["source"] for record in buildings)),
              "roads": len(roads), "trees": len(trees), "parks": len(parks),
              "areaSFMainlandKm2": round(city.area / 1e6, 3), "terrainSpacingMetres": 12}
    (OUT / "provenance.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "inputManifest"}, indent=2), flush=True)


def load():
    return json.loads(gzip.decompress(SNAPSHOT.read_bytes()))


if __name__ == "__main__":
    derive()
