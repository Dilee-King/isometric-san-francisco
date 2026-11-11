"""Write independent region packages in one Deep Zoom coordinate system."""

from collections import Counter
import math
import shutil

from PIL import Image

from golden_gate_geometry import ATLAS

REGIONS = (
    ("city-core", (-3670, -2690, -520, 810)),
    ("golden-gate", (-10900, -10160, -6000, -5600)),
    ("marina", (-10900, -5600, -3400, -2000)),
    ("north-waterfront", (-3400, -4000, 1822, -1500)),
    ("embarcadero", (-3600, -1500, 1822, 1600)),
    ("south-waterfront", (-4500, 1600, 1822, 4248)),
)


def layout():
    return {
        "tileSize": 512,
        "overlap": 1,
        "maxLevel": math.ceil(math.log2(max(ATLAS.width, ATLAS.height))),
        "sharedMaxLevel": 11,
        "fallback": "context",
        "regions": [
            {"id": identity, "bounds": [x0 - ATLAS.x, y0 - ATLAS.y, x1 - ATLAS.x, y1 - ATLAS.y]}
            for identity, (x0, y0, x1, y1) in REGIONS
        ],
    }


def region_for_tile(config, width, height, level, column, row):
    if level <= config["sharedMaxLevel"]:
        return "overview"
    divisor = 2 ** (config["maxLevel"] - level)
    level_width = math.ceil(width / divisor)
    level_height = math.ceil(height / divisor)
    tile_size = config["tileSize"]
    left, top = column * tile_size, row * tile_size
    right = min(left + tile_size, level_width)
    bottom = min(top + tile_size, level_height)
    x = (left + right) / 2 * width / level_width
    y = (top + bottom) / 2 * height / level_height
    for region in config["regions"]:
        x0, y0, x1, y1 = region["bounds"]
        if x0 <= x < x1 and y0 <= y < y1:
            return region["id"]
    return config["fallback"]


def read_native(folder, stem, width, height):
    """Reassemble the retained native tiles without changing their pixel scale."""
    top = math.ceil(math.log2(max(width, height)))
    output = Image.new("RGB", (width, height))
    for row in range(math.ceil(height / 512)):
        for column in range(math.ceil(width / 512)):
            path = folder / f"{stem}_files" / str(top) / f"{column}_{row}.webp"
            with Image.open(path) as tile:
                left = 1 if column else 0
                upper = 1 if row else 0
                clip_width = min(512, width - column * 512)
                clip_height = min(512, height - row * 512)
                clip = tile.crop((left, upper, left + clip_width, upper + clip_height))
                output.paste(clip, (column * 512, row * 512))
    return output


def pyramid(image, destination, stem, config, *, previous, changed_bounds):
    """Encode changed tiles and retain source bytes outside the new inland area."""
    width, height = image.size
    counts = Counter()
    retained = 0
    x0, y0, x1, y1 = changed_bounds
    tile_size = config["tileSize"]
    overlap = config["overlap"]
    for level in range(config["maxLevel"] + 1):
        divisor = 2 ** (config["maxLevel"] - level)
        size = (math.ceil(width / divisor), math.ceil(height / divisor))
        level_image = None
        for row in range(math.ceil(size[1] / tile_size)):
            for column in range(math.ceil(size[0] / tile_size)):
                region = region_for_tile(config, width, height, level, column, row)
                folder = destination / "regions" / region / f"{stem}_files" / str(level)
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / f"{column}_{row}.webp"
                left = max(0, column * tile_size - overlap)
                top = max(0, row * tile_size - overlap)
                right = min(size[0], (column + 1) * tile_size + overlap)
                bottom = min(size[1], (row + 1) * tile_size + overlap)
                scale_x, scale_y = width / size[0], height / size[1]
                halo = 4 * divisor
                touches = (
                    right * scale_x + halo > x0 and left * scale_x - halo < x1
                    and bottom * scale_y + halo > y0 and top * scale_y - halo < y1
                )
                old = previous / f"{stem}_files" / str(level) / f"{column}_{row}.webp"
                if not touches:
                    shutil.copyfile(old, path)
                    retained += 1
                else:
                    if level_image is None:
                        level_image = image if divisor == 1 else image.resize(size, Image.Resampling.LANCZOS)
                    level_image.crop((left, top, right, bottom)).save(path, quality=93, method=4)
                counts[region] += 1
    print(f"{stem}: {sum(counts.values())} regional tiles, {retained} source tiles retained", flush=True)
    return dict(counts), retained
