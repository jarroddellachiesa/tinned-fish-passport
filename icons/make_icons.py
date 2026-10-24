#!/usr/bin/env python3
"""Tinned Fish Passport favicon / app icons. Writes SVG sources + PNG/ICO via headless Chrome.
Run: python3 icons/make_icons.py   (outputs into the site root)"""
import os, subprocess, tempfile
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); SITE = os.path.dirname(HERE)
SALMON = ('M108,2 C96,-12 72,-24 40,-28 C10,-31 -30,-26 -62,-14 C-75,-9 -84,-6 -90,-6 '
          'L-114,-27 Q-104,0 -116,25 L-90,6 C-70,10 -50,18 -20,22 C20,26 60,22 85,14 '
          'C98,10 106,6 108,2 Z M-6,-31 C-12,-42 -22,-49 -36,-48 L-40,-27 Z '
          'M-63,-14 L-71,-22 L-74,-11 Z M50,17 L33,32 L29,19 Z M-12,22 L-24,34 L-30,21 Z M-52,16 L-62,28 L-68,13 Z')
DEFS = '''<defs>
<radialGradient id="lea" cx=".42" cy=".36" r=".85"><stop offset="0" stop-color="#1d3a66"/><stop offset=".55" stop-color="#11264a"/><stop offset="1" stop-color="#07142a"/></radialGradient>
<linearGradient id="g" x1="0" y1="0" x2=".4" y2="1"><stop offset="0" stop-color="#f8e7a8"/><stop offset=".3" stop-color="#d2a54a"/>
<stop offset=".55" stop-color="#f3d989"/><stop offset=".8" stop-color="#b0832f"/><stop offset="1" stop-color="#e2bf68"/></linearGradient>
<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" seed="4"/>
<feDiffuseLighting surfaceScale="1.6" lighting-color="#fff"><feDistantLight azimuth="235" elevation="58"/></feDiffuseLighting>
<feColorMatrix type="matrix" values=".33 .33 .33 0 -.3  .33 .33 .33 0 -.3  .33 .33 .33 0 -.3  0 0 0 0 1"/></filter>
<filter id="emb"><feOffset dy="-3" in="SourceAlpha"/><feFlood flood-color="#020814" flood-opacity=".7"/><feComposite operator="in" in2="SourceAlpha" result="x"/>
<feGaussianBlur in="SourceAlpha" stdDeviation="2" result="b"/><feSpecularLighting in="b" surfaceScale="3" specularConstant=".7" specularExponent="16" lighting-color="#fff6d8" result="s"><feDistantLight azimuth="230" elevation="45"/></feSpecularLighting>
<feComposite in="s" in2="SourceAlpha" operator="in" result="si"/><feComposite in="SourceGraphic" in2="si" operator="arithmetic" k2="1" k3=".5"/></filter>
</defs>'''


def tin(cx, cy, w, h, sw, k, dash=True):
    s = (f'<rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" rx="{h*.38}" fill="none" stroke="url(#g)" stroke-width="{sw}"/>'
         f'<ellipse cx="{cx-w/2-h*.27}" cy="{cy}" rx="{h*.21}" ry="{h*.15}" fill="none" stroke="url(#g)" stroke-width="{sw*.7}"/>'
         f'<path d="M{cx-w/2-h*.08},{cy-h*.06} H{cx-w/2+sw*.6} M{cx-w/2-h*.08},{cy+h*.06} H{cx-w/2+sw*.6}" stroke="url(#g)" stroke-width="{sw*.55}"/>'
         f'<g transform="translate({cx+w*.02} {cy+h*.04}) scale({k})"><path d="{SALMON}" fill="url(#g)"/></g>')
    if dash:
        i = sw * 1.4
        s = (f'<rect x="{cx-w/2+i}" y="{cy-h/2+i}" width="{w-2*i}" height="{h-2*i}" rx="{h*.38-i}" fill="none" stroke="url(#g)" '
             f'stroke-width="{sw*.3}" stroke-dasharray="{sw*.9} {sw*.7}"/>') + s
    return s


def svg(kind):
    bg_rx = {'rounded': 104, 'square': 0, 'mask': 0, 'small': 96}[kind]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">', DEFS,
         f'<rect width="512" height="512" rx="{bg_rx}" fill="url(#lea)"/>']
    if kind != 'small':
        o.append(f'<clipPath id="bgc"><rect width="512" height="512" rx="{bg_rx}"/></clipPath>'
                 f'<g clip-path="url(#bgc)" style="mix-blend-mode:soft-light" opacity=".7"><rect width="512" height="512" filter="url(#grain)"/></g>')
    if kind == 'small':        # bold, no ring: survives 16px
        o.append('<g filter="url(#emb)">' + tin(296, 258, 360, 236, 40, 1.12, dash=False) + '</g>')
    else:
        s = .78 if kind == 'mask' else 1.0      # maskable: emblem inside the 80% safe circle
        o.append(f'<g transform="translate(256 256) scale({s}) translate(-256 -256)" filter="url(#emb)">'
                 f'<circle cx="256" cy="256" r="206" fill="none" stroke="url(#g)" stroke-width="12"/>'
                 f'<circle cx="256" cy="256" r="188" fill="none" stroke="url(#g)" stroke-width="3"/>'
                 + tin(282, 262, 250, 150, 17, .78) +
                 ''.join(f'<path d="M{x},{y} l7,-7 l7,7 l-7,7 Z" fill="url(#g)"/>' for x, y in [(43, 256), (455, 256)]) +
                 '</g>')
    o.append('</svg>')
    return '\n'.join(o)


def render(kind, size):
    path = os.path.join(HERE, f'icon-{kind}.svg')
    open(path, 'w').write(svg(kind))
    out = os.path.join(tempfile.gettempdir(), f'tfp-{kind}.png')
    subprocess.run(['google-chrome', '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
                    '--default-background-color=00000000', '--force-device-scale-factor=1', '--window-size=512,512',
                    f'--screenshot={out}', 'file://' + path], check=True, capture_output=True)
    return Image.open(out).convert('RGBA')


big, sq, mask, small = (render(k, 512) for k in ('rounded', 'square', 'mask', 'small'))
R = lambda im, n: im.resize((n, n), Image.LANCZOS)
big.save(os.path.join(SITE, 'icon-512.png')); R(big, 192).save(os.path.join(SITE, 'icon-192.png'))
mask.convert('RGB').save(os.path.join(SITE, 'icon-maskable-512.png'))
R(sq, 180).convert('RGB').save(os.path.join(SITE, 'apple-touch-icon.png'))
R(small, 32).save(os.path.join(SITE, 'favicon-32.png'))
R(small, 48).save(os.path.join(SITE, 'favicon.ico'), sizes=[(16, 16), (32, 32), (48, 48)])
print('icons written')
