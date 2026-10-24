#!/usr/bin/env python3
"""Favicon / app icons = the seal from the front passport cover.
Source: icons/cover-source.svg (copy of stamps/build/passport_cover.svg made by passport.py --cover).
The seal is cut out of the cover SVG by cropping its viewBox to the emblem (cx=450, cy=585), so it
uses the cover's own leather, foil filters and geometry. Small sizes drop the fine ring text + hairlines.
Run: python3 icons/make_icons.py"""
import os, re, subprocess, tempfile
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); SITE = os.path.dirname(HERE)
SRC = open(os.path.join(HERE, 'cover-source.svg')).read()
CX, CY = 450, 585


def variant(name, half, small=False, px=1024):
    s = SRC
    if small:   # keep the outer ring, inner ring, wreath and scene; drop text ring and hairline circles
        s = re.sub(r'<text[^>]*><textPath.*?</textPath></text>', '', s)
        s = re.sub(r'<circle cx="450\.0" cy="585" r="(196|159)"[^>]*/>', '', s)
        s = s.replace('r="205" fill="none" stroke="url(#gold)" stroke-width="5"', 'r="200" fill="none" stroke="url(#gold)" stroke-width="16"')
        s = s.replace('r="166" fill="none" stroke="url(#gold)" stroke-width="3"', 'r="166" fill="none" stroke="url(#gold)" stroke-width="9"')
    s = re.sub(r'<svg [^>]*>', f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" '
               f'viewBox="{CX-half} {CY-half} {2*half} {2*half}">', s, count=1)
    path = os.path.join(HERE, f'seal-{name}.svg'); open(path, 'w').write(s)
    out = os.path.join(tempfile.gettempdir(), f'tfp-seal-{name}.png')
    subprocess.run(['google-chrome', '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
                    '--force-device-scale-factor=1', f'--window-size={px},{px}', f'--screenshot={out}', 'file://' + path],
                   check=True, capture_output=True)
    return Image.open(out).convert('RGBA')


def rounded(im, r=.2):
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.size[0]-1, im.size[1]-1), int(im.size[0]*r), fill=255)
    im = im.copy(); im.putalpha(m); return im


R = lambda im, n: im.resize((n, n), Image.LANCZOS)
full = variant('full', 262)        # whole seal incl. wreath, small margin
mask = variant('maskable', 335)    # seal inside the 80% safe zone
small = variant('small', 246, small=True)
rounded(R(full, 512)).save(os.path.join(SITE, 'icon-512.png'))
rounded(R(full, 192)).save(os.path.join(SITE, 'icon-192.png'))
R(mask, 512).convert('RGB').save(os.path.join(SITE, 'icon-maskable-512.png'))
R(full, 180).convert('RGB').save(os.path.join(SITE, 'apple-touch-icon.png'))
s32 = rounded(R(small, 32), .18); s32.save(os.path.join(SITE, 'favicon-32.png'))
rounded(R(small, 48), .18).save(os.path.join(SITE, 'favicon.ico'), sizes=[(16, 16), (32, 32), (48, 48)])
print('icons written')
