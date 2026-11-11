"""Apply the v0.5 lighting to the same pixels in the expanded illustrations."""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import distance_transform_edt, uniform_filter

from atlas_geometry import camera_point, ground_point


# Retain the v0.5 wet material pass and bring its overcast daylight down to
# the painted Wharf, Pier 39 and Mission Bay rain-day exposure.
OVERCAST_EXPOSURE = (.68, .69, .72)
OVERVIEW_DIMMING = .70


def legacy_lighting(artwork):
    """Retain exactly the lights visible with the original four-pixel depth mask."""
    scene = artwork.scene
    mask_height, mask_width = artwork.depth.shape[:2]
    encoding = scene["depthEncoding"]

    def visible(point):
        x, y, depth = camera_point(point)
        x, y = artwork.frame.local(x, y)
        if not (0 <= x < scene["width"] and 0 <= y < scene["height"]):
            return False
        column = int(x / scene["width"] * mask_width)
        row = int(y / scene["height"] * mask_height)
        high, low = artwork.depth[row, column, :2]
        surface = (int(high) * 256 + int(low)) / 65535 * encoding["range"] - encoding["offset"]
        return depth + 4.5 >= surface

    return {
        "windows": [window for window in scene["windows"] if visible(window["p"])],
        "lamps": [point for point in scene["lamps"] if visible(point)],
        "lightsPreFiltered": True,
    }


def painted_windows(day, frame, buildings, water, keep):
    """Sample dark painted window details for the v0.5 light-baking pass."""
    # Anchor the sampling grid in map coordinates so adjacent block halos agree.
    step = 16
    x = np.arange((step // 2 - frame.x) % step, frame.width, step)
    y = np.arange((step // 2 - frame.y) % step, frame.height, step)
    x, y = (axis.ravel() for axis in np.meshgrid(x, y))
    interior = (x > 4) & (y > 4) & (x < frame.width - 5) & (y < frame.height - 5)
    support = interior & buildings[y, x] & ~water[y, x] & (keep[y, x] > 175)
    x, y = x[support], y[support]
    gray = np.asarray(day.convert("L"))
    offsets = np.arange(-2, 3)
    chips = gray[y[:, None, None] + offsets[None, :, None], x[:, None, None] + offsets]
    dark, bright = chips.min(axis=(1, 2)), chips.max(axis=(1, 2))
    # Flat rooftops, deep shadows and bright concrete carry no window light.
    detailed = (dark >= 24) & (dark < 140) & (bright - dark > 26)
    windows = []
    for u, v in zip(x[detailed] + frame.x, y[detailed] + frame.y):
        seed = ((int(u) // step * 73856093) ^ (int(v) // step * 19349663)) & 0xFFFFFFFF
        windows.append({"p": [*ground_point(int(u), int(v)), 0], "seed": seed})
    return windows


def pavement_material(day, hard, buildings, water):
    """Find wet paving and its sheen on the painted surface."""
    colors = np.asarray(day)
    gray = np.asarray(day.convert("L"), dtype="float32")
    neutral = np.ptp(colors, axis=2) < 51
    paving = (hard & ~buildings & ~water & neutral) * np.clip((177 - gray) / 49, 0, 1)
    paving *= np.clip((gray - 38) / 22, 0, 1)
    paving = uniform_filter(paving, size=3)
    broad = uniform_filter(gray, size=(5, 13))
    sheen = paving * np.clip((gray - broad + 5) / 24, 0, 1)
    return paving, sheen


def puddle_reflections(frame, lamps, paving):
    """Extend the existing lamp pools into nearby wet pavement."""
    mask = Image.new("L", (frame.width, frame.height))
    draw = ImageDraw.Draw(mask)
    for point in lamps:
        x, y = frame.local(*camera_point(point)[:2])
        draw.ellipse((x - 4, y - 2, x + 4, y + 24), fill=202)
        draw.ellipse((x - 1, y + 3, x + 1, y + 22), fill=255)
    return (np.asarray(mask.filter(ImageFilter.GaussianBlur(2.2)), dtype="float32") / 255) * paving


def wet_surfaces(image, material, reflections=None):
    paving, sheen = material
    pixels = np.array(image)
    if reflections is None:
        exposure = OVERCAST_EXPOSURE
        absorption, highlights = (.26, .20, .11), (13, 21, 30)
    else:
        exposure = (1., 1., 1.)
        absorption, highlights = (.17, .13, .07), (6, 9, 14)
    for channel, (darken, glint) in enumerate(zip(absorption, highlights)):
        color = pixels[..., channel] * exposure[channel] * (1 - darken * paving) + glint * sheen
        if reflections is not None:
            color += reflections * (113, 75, 37)[channel]
        pixels[..., channel] = np.rint(color).clip(0, 255).astype("uint8")
    return Image.fromarray(pixels)


def overcast_overview_mask(rain, clear, water):
    """Smooth exposure across older and newer art at distant zoom."""
    wet = np.asarray(rain.resize(clear.size, Image.Resampling.BOX).convert("L"), dtype="float32")
    dry = np.asarray(clear.convert("L"), dtype="float32")
    wet = uniform_filter(wet, size=5)
    dry = uniform_filter(dry, size=5)
    gain = np.clip(.61 * dry / np.maximum(1, wet), OVERVIEW_DIMMING, 1)
    sea = np.asarray(water.resize(clear.size, Image.Resampling.BOX), dtype="float32") / 255
    alpha = (1 - gain) * (1 - sea) / (1 - OVERVIEW_DIMMING)
    return Image.fromarray(np.rint(alpha * 255).clip(0, 255).astype("uint8"))


def legacy_night_edge_mask(frame, artwork, divisor):
    """Fade the extra painted amber at the outside of the retained districts."""
    support = Image.new("1", (frame.width // divisor, frame.height // divisor))
    draw = ImageDraw.Draw(support)
    for patch in artwork:
        left, top = frame.local(patch.x, patch.y)
        right, bottom = frame.local(patch.right, patch.bottom)
        draw.rectangle((left / divisor, top / divisor, right / divisor, bottom / divisor), fill=1)
    land = np.asarray(support)
    distance = distance_transform_edt(land) * divisor
    edge = (1 - np.clip((distance - 100) / 1100, 0, 1)) * land
    return Image.fromarray(np.rint(255 * edge).astype("uint8"))


def blend_night_edge(image, alpha):
    pixels = np.array(image)
    warm = np.maximum(0, pixels[..., 0].astype("float32") - pixels[..., 2] - 5)
    fade = warm * (np.asarray(alpha, dtype="float32") / 255)
    pixels[..., 0] = np.rint(pixels[..., 0] - .90 * fade).clip(0, 255).astype("uint8")
    pixels[..., 1] = np.rint(pixels[..., 1] - .55 * fade).clip(0, 255).astype("uint8")
    return Image.fromarray(pixels)
