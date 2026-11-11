"""Build the continuous East Bay preview from the completed native-scale panels."""

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from shapely.geometry import box
from shapely.ops import unary_union

from atlas_geometry import SCALE, SE
from continuous_bay_guides import ART, PLATES, frame_for, read, rows
from corridor_inputs import ROOT, local_xy
from expanded_tiles import RetainedArtwork
from native_bay_guides import WORLD
from package_illustrated_expansion import field, sea_samples
from package_native_bay import OUT as RETAINED, dump, pack_patches, ramp

OUT = ROOT / "public/map/v10-continuous"
ASSET_ROOT = "map/v10-continuous/detail/"
MARKS = [
    ("oakland-north-waterfront", "Oakland North Waterfront", -122.3220, 37.8250),
    ("emeryville-marina", "Emeryville Marina", -122.3146048, 37.8387057),
    ("emery-cove", "Emery Cove", -122.3104667, 37.8385333),
    ("berkeley-aquatic-park", "Berkeley Aquatic Park", -122.3010, 37.8520),
]


def rectangle(row, inset=0):
    x, y, w, h = row["frame"]
    return box(x+inset, y+inset, x+w-inset, y+h-inset)


def finish_water(drawn):
    sea = sea_samples(RetainedArtwork())
    masks = {}
    padding = 160
    for row in drawn:
        with Image.open(PLATES / f"{row['id']}.png") as art:
            red, green, blue = np.asarray(art.convert("RGB"), dtype="int16").transpose(2, 0, 1)
        water = (blue > green + 7) & (green > red + 8) & (red < 52)
        distance = distance_transform_edt(np.pad(water, padding, mode="edge"))[padding:-padding, padding:-padding]
        masks[row["id"]] = Image.fromarray(np.rint(255 * ramp(distance - 28, 112)).astype("uint8"))

    def apply(image, row, appearance):
        image.paste(field(sea[appearance], frame_for(row)), mask=masks[row["id"]])

    return apply


def package():
    prior = read(RETAINED / "bay/scene.json")
    city = prior["nativeDetail"]["layers"][0]
    base_x, base_y = (-value for value in city["projection"]["origin"])
    city_coverage = unary_union([box(x0+base_x-WORLD.x, y0+base_y-WORLD.y,
                                     x1+base_x-WORLD.x, y1+base_y-WORLD.y)
                                 for x0, y0, x1, y1 in city["bounds"]])
    jobs = list(rows())
    retained = [row for row in jobs if row["reuseCity"]]
    # Earlier painted edges own overlaps that were used to guide later panels.
    drawn = sorted((row for row in jobs if not row["reuseCity"]), key=lambda row: -row["wave"])
    for row in retained:
        if not city_coverage.covers(rectangle(row)):
            raise ValueError(f"Retained City tiles do not cover {row['id']}")

    receipts = {}
    for row in drawn:
        key = row["id"]
        if not (PLATES / f"{key}.png").is_file() or not (PLATES / f"{key}.prompt.txt").is_file():
            raise ValueError(f"Missing accepted ImageGen artwork for {key}")
        receipts[key] = read(ART / "provenance" / f"{key}.json")
        if not receipts[key]["anchors"]:
            raise ValueError(f"No completed edge was used for {key}")

    coverage = unary_union([rectangle(row) for row in jobs])
    core = unary_union([rectangle(row, 76) for row in drawn] + [rectangle(row) for row in retained])
    if coverage.geom_type != "Polygon" or core.geom_type != "Polygon" or core.interiors:
        raise ValueError("Continuous East Bay coverage contains an interior gap")
    layer = pack_patches(OUT / "detail", drawn, art=ART, asset_root=ASSET_ROOT, aerial_guides=receipts,
                         finish=finish_water(drawn))
    prior["nativeDetail"]["layers"].append(layer)
    prior["release"] = "east-bay-continuous-preview"
    ratio = prior["projection"]["scale"] / SCALE
    for key, name, lon, lat in MARKS:
        east, north = local_xy(lon, lat)
        prior["landmarks"].append({"id": key, "name": name, "p": [float(east), float(north), 0],
                                   "detail": True, "cityDetail": True, "viewHeight": 795*ratio})
    (OUT / "bay").mkdir(parents=True, exist_ok=True)
    dump(OUT / "bay/scene.json", prior)
    area = core.area / (SCALE*SCALE*SE*1_000_000)
    summary = {"area": "East Bay waterfront", "sourcePixelsPerMetre": SCALE, "continuousAreaKm2": area,
               "newPlates": len(drawn), "retainedFrames": [row["id"] for row in retained],
               "completeAtlas": False}
    dump(OUT / "coverage.json", summary)
    print(f"{len(drawn)} illustrated panels, {len(retained)} reused City frames, {area:.2f} sq km of continuous native coverage")


if __name__ == "__main__":
    package()
