"""Package continuous native blocks, a shared backdrop and the retained v0.5 art."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math

import numpy as np
from PIL import Image, ImageChops, ImageFilter
from scipy.ndimage import distance_transform_edt

from atlas_geometry import PixelFrame, pack_depth, unpack_depth
from corridor_inputs import ROOT, sha
from expanded_geometry import BLOCK, DEPTH_ENCODING, HALO, MASK_DIVISOR, WORLD, art_frames
from expanded_render import LEGACY_FRAMES, REFERENCE, WORK, block_frame, blocks, padded
from golden_gate_lighting import tone
from package_corridor import APPEARANCES, feather, write_manifest
from regional_tiles import region_for_tile

RUNTIME = ROOT / "public/map"
SHARED = RUNTIME / "inner-bay"
LEGACY = RUNTIME / "v5/waterfront"
ART = ROOT / "assets/inner-bay"
MAX_LEVEL = math.ceil(math.log2(max(WORLD.width, WORLD.height)))
SHARED_LEVEL = MAX_LEVEL - 2
TILE = 512
OLD = None
ART_FRAMES = art_frames()
SHORE_PLATES = {"ocean-beach", "oakland-port", "jack-london", "alameda-main", "fort-baker", "sausalito"}


def intersection(a, b):
    left, top = max(a.x, b.x), max(a.y, b.y)
    right, bottom = min(a.right, b.right), min(a.bottom, b.bottom)
    return (left, top, right, bottom) if right > left and bottom > top else None


def local_box(frame, box):
    return (box[0] - frame.x, box[1] - frame.y, box[2] - frame.x, box[3] - frame.y)


def lay(image, frame, patch, patch_frame, alpha):
    overlap = intersection(frame, patch_frame)
    if overlap:
        dest = local_box(frame, overlap)
        crop = local_box(patch_frame, overlap)
        image.paste(patch.crop(crop), dest[:2], alpha.crop(crop))


class RetainedArtwork:
    def __init__(self):
        self.scene = json.loads((LEGACY / "scene.json").read_text(encoding="utf-8"))
        x, y = self.scene["projection"]["origin"]
        self.frame = PixelFrame("v5", -int(x), -int(y), self.scene["width"], self.scene["height"])
        self.layout = self.scene["tileLayout"]
        self.water = Image.open(LEGACY / "water.png").convert("L")
        self.hard = np.asarray(Image.open(LEGACY / "hard.png"), dtype="uint8")
        self.depth = np.asarray(Image.open(LEGACY / "depth.png"), dtype="uint8")

    def mask(self, frame, bridge):
        overlap = intersection(frame, self.frame)
        if not overlap:
            return None, None
        alpha = Image.new("L", (frame.width, frame.height))
        for patch in LEGACY_FRAMES:
            area = intersection(frame, patch)
            if area:
                target = local_box(frame, area)
                fade = feather(patch, 110).crop(local_box(patch, area))
                alpha.paste(ImageChops.lighter(alpha.crop(target), fade), target[:2])
        crop = local_box(self.frame, overlap)
        sx, sy = self.water.width / self.frame.width, self.water.height / self.frame.height
        source = (crop[0] * sx, crop[1] * sy, crop[2] * sx, crop[3] * sy)
        size = (crop[2] - crop[0], crop[3] - crop[1])
        land = ImageChops.invert(self.water.resize(size, Image.Resampling.NEAREST, box=source))
        dest = local_box(frame, overlap)
        keep = ImageChops.multiply(alpha.crop(dest), land)
        keep = ImageChops.multiply(keep, ImageChops.invert(bridge.crop(dest).filter(ImageFilter.MaxFilter(5))))
        return overlap, keep

    def crop(self, appearance, bounds):
        left, top, right, bottom = local_box(self.frame, bounds)
        image = Image.new("RGB", (right - left, bottom - top))
        maximum = self.layout["maxLevel"]
        for row in range(top // TILE, math.ceil(bottom / TILE)):
            for column in range(left // TILE, math.ceil(right / TILE)):
                region = region_for_tile(self.layout, self.frame.width, self.frame.height, maximum, column, row)
                path = LEGACY / "regions" / region / f"{appearance}_files" / str(maximum) / f"{column}_{row}.webp"
                x, y = column * TILE, row * TILE
                lo, up = max(left, x), max(top, y)
                hi, low = min(right, x + TILE), min(bottom, y + TILE)
                xoff, yoff = x - int(column > 0), y - int(row > 0)
                with Image.open(path) as tile:
                    image.paste(tile.crop((lo - xoff, up - yoff, hi - xoff, low - yoff)), (lo - left, up - top))
        return image

    def restore_depth(self, image, block, extended, overlap, alpha):
        if overlap is None:
            return image
        height, width = image.height, image.width
        xs = block.x + (np.arange(width) + .5) * MASK_DIVISOR
        ys = block.y + (np.arange(height) + .5) * MASK_DIVISOR
        keep = Image.new("L", (extended.width, extended.height))
        keep.paste(alpha, local_box(extended, overlap)[:2])
        yy = (ys - extended.y).astype(int)
        xx = (xs - extended.x).astype(int)
        take = np.asarray(keep)[np.ix_(yy, xx)] >= 128
        rows = np.clip(((ys - self.frame.y) * self.depth.shape[0] / self.frame.height).astype(int), 0, self.depth.shape[0] - 1)
        columns = np.clip(((xs - self.frame.x) * self.depth.shape[1] / self.frame.width).astype(int), 0, self.depth.shape[1] - 1)
        vintage = self.depth[np.ix_(rows, columns)]
        depth = unpack_depth(vintage, self.scene["depthEncoding"])
        flags = ((vintage[:, :, 2] > 128).astype("uint8") << 7) | (self.hard[np.ix_(rows, columns)] > 128).astype("uint8")
        encoded = pack_depth(depth, flags, DEPTH_ENCODING)
        result = np.asarray(image).copy()
        result[take] = encoded[take]
        return Image.fromarray(result)


def init_pack():
    global OLD
    OLD = RetainedArtwork()


def authored(frame):
    return [patch for patch in ART_FRAMES if intersection(frame, patch) and (ART / patch.key / "day.png").is_file()]


def signature(folder, frames):
    hashes = [sha(folder / "complete"), sha(LEGACY / "manifest.json"), sha(ROOT / "tools/expanded_tiles.py"),
              sha(ROOT / "tools/golden_gate_lighting.py")]
    for frame in frames:
        art_folder = ART / frame.key
        hashes.extend((sha(art_folder / "day.png"), sha(REFERENCE / f"{frame.key}-water.png")))
        if (art_folder / "rain-night.png").is_file():
            hashes.append(sha(art_folder / "rain-night.png"))
    return hashlib.sha256("".join(hashes).encode()).hexdigest()


def small_crop(image, divisor):
    margin = HALO // divisor
    size = BLOCK // divisor
    return image.crop((margin, margin, margin + size, margin + size))


def write_native(image, frame, region, appearance):
    for divisor in (1, 2):
        level = MAX_LEVEL - (divisor - 1)
        count = BLOCK // divisor // TILE
        margin = HALO // divisor
        start_column = (frame.x - WORLD.x) // (divisor * TILE)
        start_row = (frame.y - WORLD.y) // (divisor * TILE)
        scaled = image if divisor == 1 else image.resize(
            (image.width // divisor, image.height // divisor), Image.Resampling.LANCZOS)
        destination = SHARED / "regions" / region / f"{appearance}_files" / str(level)
        destination.mkdir(parents=True, exist_ok=True)
        for row in range(count):
            for column in range(count):
                x, y = column + start_column, row + start_row
                left = margin + column * TILE - int(x > 0)
                top = margin + row * TILE - int(y > 0)
                right = margin + (column + 1) * TILE + int((x + 1) * TILE * divisor < WORLD.width)
                bottom = margin + (row + 1) * TILE + int((y + 1) * TILE * divisor < WORLD.height)
                scaled.crop((left, top, right, bottom)).save(destination / f"{x}_{y}.webp", quality=88, method=3)


def native(item):
    key, region = item
    frame = block_frame(*map(int, key.split("_")))
    extended = padded(frame)
    folder = WORK / "native" / key
    plates = authored(extended)
    fingerprint = signature(folder, plates)
    marker = folder / "pack-complete"
    if marker.is_file() and marker.read_text(encoding="ascii").strip() == fingerprint:
        # A new checkout can reuse the derived work cache only when its output exists.
        x = (frame.x - WORLD.x) // TILE
        y = (frame.y - WORLD.y) // TILE
        if (SHARED / "regions" / region / "rain-night_files" / str(MAX_LEVEL) / f"{x}_{y}.webp").is_file():
            return
    with Image.open(folder / f"{key}-day.png") as source:
        day = source.convert("RGB")
    lamps = json.loads((folder / "lamps.json").read_text(encoding="utf-8"))
    wet_nights = []
    for patch in plates:
        with Image.open(ART / patch.key / "day.png") as source:
            art = source.convert("RGB")
        if art.size != (patch.width, patch.height):
            raise ValueError(f"Invalid native art dimensions for {patch.key}: {art.size}")
        with Image.open(REFERENCE / f"{patch.key}-water.png") as water:
            water = water.convert("L")
            if patch.key in SHORE_PLATES:
                distance = distance_transform_edt(np.asarray(water) > 128)
                near_shore = Image.fromarray(np.rint(255 * np.clip((128 - distance) / 90, 0, 1)).astype("uint8"))
            else:
                near_shore = ImageChops.invert(water)
            alpha = ImageChops.multiply(feather(patch, 160), near_shore)
        lay(day, extended, art, patch, alpha)
        wet = ART / patch.key / "rain-night.png"
        if wet.is_file():
            wet_nights.append((patch, wet, alpha.point(lambda value: round(value * .86))))
    with Image.open(folder / "bridge.png") as bridge:
        bounds, alpha = OLD.mask(extended, bridge.convert("L"))
    for stem, appearance in APPEARANCES.items():
        image = tone(day, appearance, extended, lamps, work=folder)
        if appearance == "day":
            image = image.copy()
        if appearance == "rain-night":
            for patch, wet, wet_alpha in wet_nights:
                with Image.open(wet) as source:
                    if source.size != (patch.width, patch.height):
                        raise ValueError(f"Invalid native wet-night art dimensions for {patch.key}")
                    lay(image, extended, source.convert("RGB"), patch, wet_alpha)
        if bounds is not None and alpha.getbbox():
            image.paste(OLD.crop(stem, bounds), local_box(extended, bounds)[:2], alpha)
        write_native(image, frame, region, stem)
        coarse = image.resize((image.width // 4, image.height // 4), Image.Resampling.LANCZOS)
        small_crop(coarse, 4).save(folder / f"{stem}-overview.png", compress_level=2)
    with Image.open(folder / "mask.png") as mask:
        restored = OLD.restore_depth(mask, frame, extended, bounds, alpha)
        restored.save(folder / "runtime-mask.png", compress_level=3)
    marker.write_text(fingerprint + "\n", encoding="ascii")
    print(f"Packaged {region} {key}, {len(plates)} nearby art plates", flush=True)


def context(frame):
    key = frame.key
    folder = WORK / "context" / key
    fingerprint = signature(folder, ())
    marker = folder / "pack-complete"
    if marker.is_file() and marker.read_text(encoding="ascii").strip() == fingerprint:
        return
    with Image.open(folder / f"{key}-day.png") as source:
        day = source.convert("RGB")
    lamps = json.loads((folder / "lamps.json").read_text(encoding="utf-8"))
    for stem, appearance in APPEARANCES.items():
        image = tone(day, appearance, padded(frame), lamps, work=folder)
        small_crop(image, 4).save(folder / f"{stem}-overview.png", compress_level=2)
    marker.write_text(fingerprint + "\n", encoding="ascii")


def write_backdrop(version, stem, active):
    image = Image.new("RGB", (WORLD.width // 4, WORLD.height // 4))
    for frame in blocks():
        native = frame.key in active and active[frame.key][0] <= version
        path = WORK / ("native" if native else "context") / frame.key / f"{stem}-overview.png"
        with Image.open(path) as patch:
            image.paste(patch, ((frame.x - WORLD.x) // 4, (frame.y - WORLD.y) // 4))
    root = RUNTIME / f"v{version}/waterfront/regions/overview" / f"{stem}_files"
    for level in range(SHARED_LEVEL + 1):
        divisor = 2 ** (MAX_LEVEL - level)
        size = (math.ceil(WORLD.width / divisor), math.ceil(WORLD.height / divisor))
        scaled = image if level == SHARED_LEVEL else image.resize(size, Image.Resampling.LANCZOS)
        folder = root / str(level)
        folder.mkdir(parents=True, exist_ok=True)
        for row in range(math.ceil(size[1] / TILE)):
            for column in range(math.ceil(size[0] / TILE)):
                crop = (max(0, column * TILE - 1), max(0, row * TILE - 1),
                        min(size[0], (column + 1) * TILE + 1), min(size[1], (row + 1) * TILE + 1))
                scaled.crop(crop).save(folder / f"{column}_{row}.webp", quality=83, method=3)
    print(f"v0.{version} {stem} backdrop", flush=True)


def write_masks(active):
    image = Image.new("RGB", (WORLD.width // MASK_DIVISOR, WORLD.height // MASK_DIVISOR))
    for frame in blocks():
        path = (WORK / "native" / frame.key / "runtime-mask.png" if frame.key in active else
                WORK / "context" / frame.key / "mask.png")
        with Image.open(path) as patch:
            image.paste(patch, ((frame.x - WORLD.x) // MASK_DIVISOR, (frame.y - WORLD.y) // MASK_DIVISOR))
    image.save(SHARED / "masks.png", compress_level=5)


def backdrop_task(item):
    write_backdrop(*item)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("native", "context", "backdrops"))
    parser.add_argument("--jobs", type=int, default=5)
    parser.add_argument("--version", type=int, choices=(6, 7, 8))
    parser.add_argument("--blocks", nargs="+")
    parser.add_argument("--appearance", choices=tuple(APPEARANCES))
    args = parser.parse_args()
    active = json.loads((WORK / "blocks.json").read_text(encoding="utf-8"))
    if args.stage == "native":
        if args.blocks and set(args.blocks) - active.keys():
            parser.error("An explicit block is outside native coverage")
        with ProcessPoolExecutor(max_workers=args.jobs, initializer=init_pack) as pool:
            list(pool.map(native, [(key, region) for key, (version, region) in active.items()
                                   if not args.blocks or key in args.blocks]))
    elif args.stage == "context":
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            list(pool.map(context, blocks()))
    else:
        write_masks(active)
        write_manifest(SHARED, {"size": [WORLD.width, WORLD.height], "maskSize": [WORLD.width // MASK_DIVISOR, WORLD.height // MASK_DIVISOR],
                                "nativeBlocks": active, "tileSize": TILE, "nativeLevels": [MAX_LEVEL - 1, MAX_LEVEL]})
        versions = [args.version] if args.version else (6, 7, 8)
        appearances = [args.appearance] if args.appearance else APPEARANCES
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            list(pool.map(backdrop_task, [(version, stem, active) for version in versions for stem in appearances]))


if __name__ == "__main__":
    main()
