#!/usr/bin/env python3
"""Build the static Tinned Fish Passport site from ../stamps/brands.json + rendered PNGs."""
import json, os, html, shutil
from PIL import Image
SITE = os.path.dirname(os.path.abspath(__file__))
STAMPS = os.environ.get('STAMPS_DIR', '/workspace/stamps')
data = json.load(open(os.path.join(STAMPS, 'brands.json')))
img = os.path.join(SITE, 'img'); shutil.rmtree(img, ignore_errors=True); os.makedirs(img)
W, H = 900, 1250

def conv(src, name):
    im = Image.open(os.path.join(STAMPS, src)).convert('RGB')
    im.save(os.path.join(img, name + '.webp'), 'WEBP', quality=82, method=6)
    im.resize((W*2//3, H*2//3), Image.LANCZOS).save(os.path.join(img, name + '.jpg'), 'JPEG', quality=84, optimize=True, progressive=True)

conv('passport_cover.png', 'cover')
pages = [('cover', 'Tinned Fish Passport — cover')]
for key, (brand, items) in data.items():
    conv(f'passport_{key}.png', key); pages.append((key, f'{brand} visa page'))

e = html.escape
leaves = []
for i, (name, alt) in enumerate(pages):
    leaves.append(f'<div class="leaf" style="z-index:{len(pages)-i}"><div class="front"><picture>'
                  f'<source srcset="img/{name}.webp" type="image/webp"><img src="img/{name}.jpg" alt="{e(alt)}" '
                  f'width="{W}" height="{H}" {"" if i < 2 else "loading=lazy"} draggable="false"></picture></div><div class="back"></div></div>')
rows = sorted(((r, b, f) for b, items in data.values() for f, r in items), key=lambda t: (-t[0], t[1], t[2]))
trs, rank, prev = [], 0, None
for n, (r, b, f) in enumerate(rows, 1):
    if r != prev: rank, prev = n, r
    trs.append(f'<tr><td class="rk">{rank}</td><td><b>{e(f)}</b><span>{e(b.title())}</span></td><td class="rt">{r}<small>/10</small></td></tr>')
dots = ''.join(f'<button class="dot" aria-label="Page {i}"></button>' for i in range(len(pages)))
out = open(os.path.join(SITE, 'tpl.html')).read()
out = out.replace('{{LEAVES}}', '\n'.join(leaves)).replace('{{ROWS}}', '\n'.join(trs)).replace('{{DOTS}}', dots)
out = out.replace('{{COUNT}}', str(len(rows))).replace('{{BRANDS}}', str(len(data)))
open(os.path.join(SITE, 'index.html'), 'w').write(out)
print(f'built index.html: {len(pages)} pages, {len(rows)} tins')
