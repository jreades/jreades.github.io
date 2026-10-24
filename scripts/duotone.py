"""Duotone the photos in img/scenes/ using the settings in img/duotone/duotone.md.

    python scripts/duotone.py                 # redo anything new or changed
    python scripts/duotone.py IMG_3250.jpg    # just these files

Outputs share one aspect ratio (`aspect`), cropped around `focus`, or around an exact
`crop: [x0, y0, x1, y1]` in pixels of the (upright) original. `skip: true` drops an image.
images.json in the output folder lists the finished files for the site.

    python scripts/duotone.py --force --sheet # redo all and write a contact sheet

Each image is turned into a greyscale, mapped onto a shadow-to-highlight colour ramp
(Pillow's ImageOps.colorize, so black and white points are adjustable) and then laid over
a desaturated copy of the original, so some true colour shows through. Requires Pillow
and PyYAML (scripts/requirements-images.txt).
"""
import argparse
import hashlib
import json
import os
import re
import sys

import yaml
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'img', 'scenes')
OUT = os.path.join(ROOT, 'img', 'duotone')
SETTINGS = os.path.join(OUT, 'duotone.md')
MANIFEST = os.path.join(OUT, '.manifest.json')
EXTS = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')


def load_settings(path):
    text = open(path, encoding='utf-8').read()
    m = re.match(r'^---\s*\n(.*?)\n---\s*(\n|$)', text, re.S)
    if not m:
        sys.exit(f'{path}: expected YAML front matter between --- lines')
    cfg = yaml.safe_load(m.group(1)) or {}
    cfg.setdefault('palette', {})
    cfg.setdefault('defaults', {})
    cfg['images'] = cfg.get('images') or {}
    return cfg


def colour(value, palette):
    if value is None:
        return None
    value = palette.get(value, value)
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', str(value)):
        sys.exit(f'Not a colour or palette name: {value!r}')
    return str(value)


def crop_to_aspect(img, aspect, focus):
    w, h = img.size
    a, b = (float(x) for x in str(aspect).split(':'))
    target = a / b
    if w / h > target:
        nw, nh = int(round(h * target)), h
    else:
        nw, nh = w, int(round(w / target))
    left = min(max(int(round(focus[0] * w - nw / 2)), 0), w - nw)
    top = min(max(int(round(focus[1] * h - nh / 2)), 0), h - nh)
    return img.crop((left, top, left + nw, top + nh))


def duotone(img, s, palette):
    img = ImageOps.exif_transpose(img).convert('RGB')
    if s.get('crop'):
        x0, y0, x1, y1 = s['crop']
        img = img.crop((x0, y0, x1, y1))
    if s.get('aspect'):
        img = crop_to_aspect(img, s['aspect'], s['focus'])
    if img.width > s['width']:
        img = img.resize((s['width'], round(img.height * s['width'] / img.width)), Image.LANCZOS)

    grey = ImageOps.grayscale(img)
    if s['cutoff']:
        grey = ImageOps.autocontrast(grey, cutoff=s['cutoff'])
    if s['gamma'] != 1.0:
        grey = grey.point([round(255 * (i / 255) ** s['gamma']) for i in range(256)])

    mid = colour(s['mid'], palette)
    duo = ImageOps.colorize(
        grey, black=colour(s['shadow'], palette), white=colour(s['highlight'], palette),
        mid=mid, blackpoint=s['blackpoint'], whitepoint=s['whitepoint'], midpoint=s['midpoint'])

    base = ImageEnhance.Color(img).enhance(s['saturation'])
    return Image.blend(base, duo, s['strength'])


def fingerprint(path, settings):
    st = os.stat(path)
    blob = json.dumps([st.st_size, int(st.st_mtime), settings], sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()


def write_index():
    """List every duotone with its size so the site can pick one at random."""
    items = []
    for f in sorted(os.listdir(OUT)):
        if f.lower().endswith('.jpg') and not f.startswith('_'):
            with Image.open(os.path.join(OUT, f)) as im:
                items.append({'file': f, 'width': im.width, 'height': im.height})
    with open(os.path.join(OUT, 'images.json'), 'w') as fh:
        json.dump(items, fh, indent=1)
        fh.write('\n')


def contact_sheet(paths, dest, cols=4, thumb=360):
    thumbs = []
    for p in paths:
        im = Image.open(p)
        im.thumbnail((thumb, thumb))
        thumbs.append((os.path.basename(p), im))
    rows = [thumbs[i:i + cols] for i in range(0, len(thumbs), cols)]
    heights = [max(im.height for _, im in r) + 34 for r in rows]
    sheet = Image.new('RGB', (cols * (thumb + 12) + 12, sum(heights) + 12), '#ECE9E1')
    draw = ImageDraw.Draw(sheet)
    y = 12
    for r, h in zip(rows, heights):
        for c, (name, im) in enumerate(r):
            x = 12 + c * (thumb + 12)
            sheet.paste(im, (x, y))
            draw.text((x, y + im.height + 6), name, fill='#1B2428')
        y += h
    sheet.save(dest, quality=88)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='*', help='file names in img/scenes (default: all)')
    ap.add_argument('--settings', default=SETTINGS)
    ap.add_argument('--force', action='store_true', help='redo even if nothing changed')
    ap.add_argument('--sheet', action='store_true', help='write img/duotone/_contact.jpg')
    args = ap.parse_args()

    cfg = load_settings(args.settings)
    os.makedirs(OUT, exist_ok=True)
    manifest = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}

    names = args.files or sorted(f for f in os.listdir(SRC) if f.lower().endswith(EXTS))
    done = skipped = 0
    outputs = []
    for name in names:
        src = os.path.join(SRC, name)
        if not os.path.exists(src):
            sys.exit(f'{name}: not found in {os.path.relpath(SRC, ROOT)}')
        unknown = set(cfg['images'].get(name) or {}) - set(cfg['defaults'])
        if unknown:
            sys.exit(f'{name}: unknown setting(s) {sorted(unknown)}')
        s = {**cfg['defaults'], **(cfg['images'].get(name) or {})}
        dest = os.path.join(OUT, os.path.splitext(name)[0] + '.jpg')
        if s['skip']:
            if os.path.exists(dest):
                os.remove(dest)
            manifest.pop(name, None)
            continue
        outputs.append(dest)
        fp = fingerprint(src, [s, cfg['palette']])
        if not args.force and manifest.get(name) == fp and os.path.exists(dest):
            skipped += 1
            continue
        duotone(Image.open(src), s, cfg['palette']).save(dest, quality=s['quality'], optimize=True, progressive=True)
        manifest[name] = fp
        done += 1
        print(f'  {name} -> {os.path.relpath(dest, ROOT)}')
    if not args.files:  # full run: drop outputs whose source is gone or skipped
        keep = {os.path.basename(o) for o in outputs}
        for f in os.listdir(OUT):
            if f.lower().endswith('.jpg') and not f.startswith('_') and f not in keep:
                os.remove(os.path.join(OUT, f))
                print(f'  removed stale {f}')
    json.dump(manifest, open(MANIFEST, 'w'), indent=1, sort_keys=True)
    write_index()
    if args.sheet:
        contact_sheet([o for o in outputs if os.path.exists(o)], os.path.join(OUT, '_contact.jpg'))
    print(f'duotone: {done} made, {skipped} unchanged')


if __name__ == '__main__':
    main()
