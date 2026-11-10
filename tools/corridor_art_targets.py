"""Extract lossless, native-density edit targets from registered source rasters."""

from PIL import Image
from atlas_geometry import ART_FRAMES, FRAMES
from render_corridor import WORK, ground_texture, load_data


def main():
    data = load_data()
    target_dir = WORK/'art-targets'
    target_dir.mkdir(parents=True, exist_ok=True)
    sources = [(f, Image.open(WORK/f'{f.key}-reference.png')) for f in FRAMES]
    for target in ART_FRAMES:
        if target.key == 'ferry-anchor':
            continue
        rgb, *_ = ground_texture(data, target, 1)
        canvas = Image.fromarray(rgb)
        for source, image in sources:
            left, top = max(source.x, target.x), max(source.y, target.y)
            right, bottom = min(source.right, target.right), min(source.bottom, target.bottom)
            if right <= left or bottom <= top:
                continue
            clip = image.crop((left-source.x, top-source.y, right-source.x, bottom-source.y))
            canvas.paste(clip, (left-target.x, top-target.y))
        canvas.save(target_dir/f'{target.key}.png', compress_level=4)
        print(target.key, canvas.size, flush=True)


if __name__ == '__main__':
    main()
