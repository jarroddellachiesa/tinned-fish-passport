#!/usr/bin/env python3
"""Build the static Tinned Fish Passport site from ../stamps/brands.json + rendered PNGs."""
import json, os, html, shutil, sys
from PIL import Image

SITE = os.path.dirname(os.path.abspath(__file__))
STAMPS = os.environ.get('STAMPS_DIR', '/workspace/stamps')
sys.path.insert(0, STAMPS)
import passport as passport_mod  # noqa: E402

data = json.load(open(os.path.join(STAMPS, 'brands.json')))
packaging = {}
pkg_path = os.path.join(STAMPS, 'packaging.json')
if os.path.exists(pkg_path):
    packaging = json.load(open(pkg_path))

# Always refresh hotspot coords from the same layout math as the renderer
hotspots = passport_mod.export_stamp_hotspots(data)

img = os.path.join(SITE, 'img')
shutil.rmtree(img, ignore_errors=True)
os.makedirs(img)
# Copy packaging photos into the site
pkg_src = os.path.join(STAMPS, 'packaging')
pkg_dst = os.path.join(img, 'packaging')
if os.path.isdir(pkg_src):
    shutil.copytree(pkg_src, pkg_dst)

W, H = 900, 1250


def conv(src, name):
    im = Image.open(os.path.join(STAMPS, src)).convert('RGB')
    im.save(os.path.join(img, name + '.webp'), 'WEBP', quality=82, method=6)
    im.resize((W * 2 // 3, H * 2 // 3), Image.LANCZOS).save(
        os.path.join(img, name + '.jpg'), 'JPEG', quality=84, optimize=True, progressive=True)


conv('passport_cover.png', 'cover')
pages = [('cover', 'Tinned Fish Passport — cover', None)]
for key, (brand, items) in data.items():
    conv(f'passport_{key}.png', key)
    pages.append((key, f'{brand} visa page', key))
conv('passport_back.png', 'back')
pages.append(('back', 'Tinned Fish Passport — back cover', None))

e = html.escape


def tin_meta(brand_key, fish, rating, brand_name):
    """Lookup packaging photo + buy URL for one tin."""
    entry = (packaging.get(brand_key) or {}).get(fish) or {}
    file_ = entry.get('file') or ''
    # site-relative path: packaging/... -> img/packaging/...
    photo = ('img/' + file_[len('packaging/'):] if file_.startswith('packaging/')
             else (f'img/packaging/{os.path.basename(file_)}' if file_ else ''))
    # Prefer copied basename under img/packaging/
    if file_:
        base = os.path.basename(file_)
        photo = f'img/packaging/{base}'
    return {
        'brand_key': brand_key,
        'brand': brand_name,
        'fish': fish,
        'rating': rating,
        'photo': photo,
        'url': entry.get('url') or '',
        'button': entry.get('button') or ('Reorder' if entry.get('url') else ''),
    }


def hotspot_html(brand_key, brand_name, items):
    spots = hotspots.get(brand_key) or []
    bits = []
    for i, spot in enumerate(spots):
        fish = spot['fish']
        rating = spot['rating']
        meta = tin_meta(brand_key, fish, rating, brand_name)
        # percent of page for center + diameter
        left = spot['cx'] / W * 100
        top = spot['cy'] / H * 100
        size = spot['r'] * 2 / W * 100  # width % of page; height uses aspect later via aspect-ratio
        size_h = spot['r'] * 2 / H * 100
        payload = e(json.dumps(meta, ensure_ascii=False))
        bits.append(
            f'<button type="button" class="hotspot" style="left:{left:.2f}%;top:{top:.2f}%;'
            f'width:{size:.2f}%;height:{size_h:.2f}%" data-tin="{payload}" '
            f'aria-label="{e(fish)} {rating}/10"></button>'
        )
    return ''.join(bits)


leaves = []
for i, (name, alt, brand_key) in enumerate(pages):
    hs = ''
    if brand_key:
        brand_name, items = data[brand_key]
        hs = f'<div class="hotspots">{hotspot_html(brand_key, brand_name, items)}</div>'
    leaves.append(
        f'<div class="leaf" style="z-index:{len(pages)-i}"><div class="front"><picture>'
        f'<source srcset="img/{name}.webp" type="image/webp"><img src="img/{name}.jpg" alt="{e(alt)}" '
        f'width="{W}" height="{H}" {"" if i < 2 else "loading=lazy"} draggable="false"></picture>'
        f'{hs}</div><div class="back"></div></div>'
    )

rows = sorted(((r, b, f, k) for k, (b, items) in data.items() for f, r in items),
              key=lambda t: (-t[0], t[1], t[2]))
trs, rank, prev = [], 0, None
for n, (r, b, f, k) in enumerate(rows, 1):
    if r != prev:
        rank, prev = n, r
    meta = tin_meta(k, f, r, b)
    payload = e(json.dumps(meta, ensure_ascii=False))
    trs.append(
        f'<tr class="tin-row" data-tin="{payload}" tabindex="0" role="button" '
        f'aria-label="View packaging for {e(f)}">'
        f'<td class="rk">{rank}</td><td><b>{e(f)}</b><span>{e(b.title())}</span></td>'
        f'<td class="rt">{r}<small>/10</small></td></tr>'
    )

dots = ''.join(f'<button class="dot" aria-label="Page {i}"></button>' for i in range(len(pages)))
out = open(os.path.join(SITE, 'tpl.html')).read()
out = out.replace('{{LEAVES}}', '\n'.join(leaves)).replace('{{ROWS}}', '\n'.join(trs)).replace('{{DOTS}}', dots)
out = out.replace('{{COUNT}}', str(len(rows))).replace('{{BRANDS}}', str(len(data)))
open(os.path.join(SITE, 'index.html'), 'w').write(out)
print(f'built index.html: {len(pages)} pages, {len(rows)} tins, packaging={len(os.listdir(pkg_dst)) if os.path.isdir(pkg_dst) else 0}')
