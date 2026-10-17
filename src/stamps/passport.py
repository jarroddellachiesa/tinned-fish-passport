#!/usr/bin/env python3
"""Tinned Fish Passport renderer.

Reads brands.json and writes, next to this script:
  passport_<key>.png   one visa page per brand (900x1250)
  passport_cover.png   the passport book cover (900x1250)
Intermediate SVGs go to ./build/.

Usage:  python3 passport.py            # pages + cover
        python3 passport.py --pages    # pages only
        python3 passport.py --cover    # cover only
        python3 passport.py --back     # back cover only
"""
import html, json, math, os, subprocess, sys, zlib
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
W, H = 900, 1250

NAVY = '#1f3f73'
RED = '#b3261e'
FONTS = {
    'sans': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    'sansb': '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    'serifb': '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
    'cond': '/usr/share/fonts/truetype/sand-box/google/Barlow Condensed/BarlowCondensed-Bold.ttf',
}
_fc = {}


def tw(text, font, size, spacing=0):
    """Text advance width in px (matches Chrome's rendering of the same TTF)."""
    k = (font, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONTS[font], size)
    return _fc[k].getlength(text) + spacing * len(text)


def esc(s):
    return html.escape(str(s), quote=True)


def f(v):
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def render(svg, out_png):
    os.makedirs(BUILD, exist_ok=True)
    svg_path = os.path.join(BUILD, os.path.splitext(os.path.basename(out_png))[0] + '.svg')
    with open(svg_path, 'w') as fh:
        fh.write(svg)
    subprocess.run(['google-chrome', '--headless=new', '--no-sandbox', '--disable-gpu',
                    '--hide-scrollbars', '--force-device-scale-factor=1',
                    f'--window-size={W},{H}', f'--screenshot={out_png}',
                    'file://' + svg_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('wrote', out_png)


# ----------------------------------------------------------------- shared art
SALMON = ('M108,2 C96,-12 72,-24 40,-28 C10,-31 -30,-26 -62,-14 C-75,-9 -84,-6 -90,-6 '
          'L-114,-27 Q-104,0 -116,25 L-90,6 C-70,10 -50,18 -20,22 C20,26 60,22 85,14 '
          'C98,10 106,6 108,2 Z '
          'M-6,-31 C-12,-42 -22,-49 -36,-48 L-40,-27 Z '
          'M-63,-14 L-71,-22 L-74,-11 Z '
          'M50,17 L33,32 L29,19 Z M-12,22 L-24,34 L-30,21 Z M-52,16 L-62,28 L-68,13 Z')
SALMON_DETAIL = 'M70,-18 Q61,0 71,16'


def star_pts(cx, cy, r1, r2, n=8, rot=-90):
    p = []
    for i in range(2 * n):
        r = r1 if i % 2 == 0 else r2
        a = math.radians(rot + i * 180 / n)
        p.append(f'{f(cx + r * math.cos(a))},{f(cy + r * math.sin(a))}')
    return ' '.join(p)


def tin_icon(w, h, sw, dash=True):
    """Sardine tin outline centred at origin, pull tab on the left."""
    rx = h * 0.42
    s = (f'<rect x="{f(-w/2)}" y="{f(-h/2)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" stroke-width="{f(sw)}"/>'
         f'<ellipse cx="{f(-w/2 - h*0.12)}" cy="0" rx="{f(h*0.2)}" ry="{f(h*0.14)}" stroke-width="{f(sw)}"/>'
         f'<path d="M{f(-w/2 + h*0.06)},{f(-h*0.06)} H{f(-w/2 + h*0.3)} M{f(-w/2 + h*0.06)},{f(h*0.06)} H{f(-w/2 + h*0.3)}" stroke-width="{f(sw*0.8)}"/>')
    if dash:
        i = h * 0.12
        s += (f'<rect x="{f(-w/2 + i)}" y="{f(-h/2 + i)}" width="{f(w - 2*i)}" height="{f(h - 2*i)}" '
              f'rx="{f(rx - i)}" stroke-width="{f(sw*0.5)}" stroke-dasharray="{f(sw*1.6)} {f(sw*1.3)}"/>')
    return s


def spruce(x, base, hgt, tiers=5):
    """Simple stacked-triangle spruce tree path."""
    w = hgt * 0.42
    d = f'M{f(x - 2)},{f(base)} h4 v{f(-hgt*0.12)} h-4 Z '
    for t in range(tiers):
        top = base - hgt * 0.12 - (hgt * 0.88) * (t + 1) / tiers - hgt * 0.06
        bot = base - hgt * 0.10 - (hgt * 0.88) * t / tiers
        ww = w * (1 - t / (tiers + 0.6))
        d += f'M{f(x)},{f(top)} L{f(x + ww/2)},{f(bot)} L{f(x - ww/2)},{f(bot)} Z '
    return d


def wave_path(x0, x1, y, amp, period, phase, step=6, amp2=0, period2=1):
    pts = []
    x = x0
    while x <= x1 + 0.01:
        yy = y + amp * math.sin(2 * math.pi * x / period + phase) + amp2 * math.sin(2 * math.pi * x / period2 + phase * 1.7)
        pts.append(f'{f(x)},{f(yy)}')
        x += step
    return 'M' + ' L'.join(pts)


def rosette(cx, cy, R, A, k, copies, step_deg=1.0):
    """Classic guilloche: rotated copies of r = R + A cos(k t)."""
    out = []
    n = int(360 / step_deg)
    for c in range(copies):
        off = 2 * math.pi * c / (k * copies)
        pts = []
        for i in range(n + 1):
            t = 2 * math.pi * i / n
            r = R + A * math.cos(k * (t + off))
            pts.append(f'{f(cx + r * math.cos(t))},{f(cy + r * math.sin(t))}')
        out.append('M' + ' L'.join(pts) + 'Z')
    return ' '.join(out)


def ring_braid(cx, cy, R, A, k, copies=2, step_deg=1.0):
    return rosette(cx, cy, R, A, k, copies, step_deg)


# ----------------------------------------------------------------- visa page
def page_background(pageno):
    s = []
    s.append(f'''<defs>
<linearGradient id="paper" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#f6efdc"/><stop offset=".45" stop-color="#eef0e2"/>
  <stop offset=".75" stop-color="#f3ecdc"/><stop offset="1" stop-color="#f4e5da"/>
</linearGradient>
<radialGradient id="tint" cx=".5" cy=".5" r=".6">
  <stop offset="0" stop-color="#dbe9e6" stop-opacity=".55"/><stop offset="1" stop-color="#dbe9e6" stop-opacity="0"/>
</radialGradient>
<linearGradient id="aur1" gradientUnits="userSpaceOnUse" x1="40" y1="0" x2="860" y2="0"><stop offset="0" stop-color="#3fb08a" stop-opacity="0"/><stop offset=".3" stop-color="#3fb08a"/><stop offset=".7" stop-color="#3a9fb0"/><stop offset="1" stop-color="#7d6fc0" stop-opacity="0"/></linearGradient>
<linearGradient id="aur2" gradientUnits="userSpaceOnUse" x1="40" y1="0" x2="860" y2="0"><stop offset="0" stop-color="#7d6fc0" stop-opacity="0"/><stop offset=".4" stop-color="#5aa6b8"/><stop offset=".8" stop-color="#4fbf8f"/><stop offset="1" stop-color="#4fbf8f" stop-opacity="0"/></linearGradient>
<linearGradient id="mtn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4f7a8c"/><stop offset="1" stop-color="#4f7a8c" stop-opacity=".2"/></linearGradient>
<filter id="blur8" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="7"/></filter>
<filter id="fiber" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="11"/>
  <feColorMatrix type="matrix" values="0 0 0 0 .45  0 0 0 0 .38  0 0 0 0 .25  0 0 0 -1.1 .62"/>
</filter>
<symbol id="salmon" viewBox="-120 -52 232 88" overflow="visible"><path d="{SALMON}"/><path d="{SALMON_DETAIL}" fill="none"/><circle cx="88" cy="-4" r="3"/></symbol>
<pattern id="wm" width="420" height="250" patternUnits="userSpaceOnUse" patternTransform="rotate(-14) translate(-40 10)">
  <g font-family="Cinzel" font-weight="700" fill="#2f5d6e">
    <text x="18" y="46" font-size="26" letter-spacing="7">ALASKA</text>
    <text x="228" y="171" font-size="15" letter-spacing="4">TINNED FISH</text>
  </g>
  <g fill="none" stroke="#2f5d6e" stroke-width="1.6">
    <use href="#salmon" x="250" y="14" width="120" height="46" fill="none"/>
    <g transform="translate(100 150)">{tin_icon(96, 50, 2.2)}</g>
  </g>
  <path d="{spruce(395, 236, 52, 4)} {spruce(372, 236, 36, 3)}" fill="#2f5d6e"/>
  <polygon points="{star_pts(195, 96, 9, 3.5)}" fill="#2f5d6e"/>
</pattern>
</defs>''')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#paper)"/>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#tint)"/>')
    # fine wave field (two interleaved tints -> moiré)
    a = []
    b = []
    y = 44
    while y < H - 40:
        a.append(wave_path(40, W - 40, y, 3.2, 150, y * 0.045, 7, 1.2, 41))
        b.append(wave_path(40, W - 40, y + 3.5, 3.2, 150, -y * 0.045 + 1.3, 7, 1.2, 53))
        y += 8
    s.append(f'<path d="{" ".join(a)}" fill="none" stroke="#7fa7a6" stroke-width=".55" opacity=".32"/>')
    s.append(f'<path d="{" ".join(b)}" fill="none" stroke="#c9a3a0" stroke-width=".5" opacity=".28"/>')
    # aurora: curtain rays masked by soft ribbons + faint glow
    rays1, rays2 = [], []
    for xx in range(46, W - 44, 3):
        b1 = 238 + 26 * math.sin(xx / 95 + .6) + 9 * math.sin(xx / 31)
        h1 = 70 + 30 * math.sin(xx / 57 + 1.3)
        rays1.append(f'M{xx},{f(b1)} V{f(b1 - h1)}')
        b2 = 300 + 20 * math.sin(xx / 120 + 2.4) + 7 * math.sin(xx / 37 + 1)
        h2 = 55 + 22 * math.sin(xx / 43)
        rays2.append(f'M{xx + 1.5},{f(b2)} V{f(b2 - h2)}')
    s.append('<defs><mask id="aurm" maskUnits="userSpaceOnUse" x="0" y="0" width="900" height="500">'
             f'<path d="{wave_path(40, W-40, 205, 26, 600, .6, 10, 9, 197)}" stroke="#fff" stroke-width="60" fill="none" filter="url(#blur8)"/>'
             f'<path d="{wave_path(40, W-40, 272, 20, 750, 2.4, 10, 7, 232)}" stroke="#fff" stroke-width="44" fill="none" filter="url(#blur8)"/>'
             '</mask></defs>')
    s.append('<g filter="url(#blur8)" opacity=".13" fill="none">'
             f'<path d="{wave_path(40, W-40, 222, 26, 600, .6, 10, 9, 197)}" stroke="url(#aur1)" stroke-width="40"/>'
             f'<path d="{wave_path(40, W-40, 290, 20, 750, 2.4, 10, 7, 232)}" stroke="url(#aur2)" stroke-width="26"/></g>')
    s.append(f'<g mask="url(#aurm)" opacity=".42" fill="none" stroke-width=".9">'
             f'<path d="{" ".join(rays1)}" stroke="url(#aur1)"/><path d="{" ".join(rays2)}" stroke="url(#aur2)"/></g>')
    # repeating watermark tile
    s.append(f'<rect x="40" y="40" width="{W-80}" height="{H-80}" fill="url(#wm)" opacity=".075"/>')
    # central guilloche rosette
    cx, cy = W / 2, 572
    s.append(f'<path d="{rosette(cx, cy, 285, 34, 22, 7, .8)}" fill="none" stroke="#5f9298" stroke-width=".5" opacity=".40"/>')
    s.append(f'<path d="{rosette(cx, cy, 190, 26, 16, 6, .9)}" fill="none" stroke="#b07f86" stroke-width=".5" opacity=".26"/>')
    s.append(f'<path d="{rosette(cx, cy, 105, 18, 12, 5, 1)}" fill="none" stroke="#5f9298" stroke-width=".5" opacity=".26"/>')
    # big faint North Star at rosette centre
    s.append(f'<polygon points="{star_pts(cx, cy, 46, 14)}" fill="#5f9298" opacity=".08"/>')
    # Denali range + spruce forest along the bottom
    rng = [(40, 1150), (95, 1100), (140, 1112), (205, 1050), (250, 1074), (300, 1012), (340, 1040),
           (395, 965), (430, 990), (452, 948), (490, 985), (535, 1002), (585, 1040), (630, 1020),
           (690, 1068), (740, 1046), (800, 1095), (860, 1120), (860, 1170), (40, 1170)]
    s.append('<polygon points="' + ' '.join(f'{x},{y}' for x, y in rng) +
             '" fill="url(#mtn)" opacity=".10" stroke="#335f70" stroke-width="1.2" stroke-opacity="1"/>')
    snow = ('M395,965 L410,978 L420,972 L430,990 M430,990 L441,968 L452,948 L466,970 L478,966 L490,985 '
            'M300,1012 L312,1030 L322,1022 L340,1040 M205,1050 L220,1064 L232,1058 L250,1074 '
            'M630,1020 L648,1038 L660,1032 L690,1068')
    s.append(f'<path d="{snow}" fill="none" stroke="#335f70" stroke-width="1.4" opacity=".16"/>')
    trees = ''
    import random
    rnd = random.Random(7)
    x = 52
    while x < W - 52:
        hh = rnd.uniform(38, 74)
        trees += spruce(x, 1172, hh, 5)
        x += rnd.uniform(15, 27)
    s.append(f'<path d="{trees}" fill="#2f5d5a" opacity=".11"/>')
    s.append(f'<rect width="{W}" height="{H}" filter="url(#fiber)" opacity=".35"/>')
    # border: outer line, braided guilloche band, inner line, corner rosettes
    m1, m2 = 26, 44
    s.append(f'<rect x="{m1}" y="{m1}" width="{W-2*m1}" height="{H-2*m1}" fill="none" stroke="#3d6a78" stroke-width="1.4" opacity=".55"/>')
    s.append(f'<rect x="{m2}" y="{m2}" width="{W-2*m2}" height="{H-2*m2}" fill="none" stroke="#3d6a78" stroke-width=".9" opacity=".55"/>')
    mid = (m1 + m2) / 2
    amp = (m2 - m1) / 2 - 2
    band = []
    for ph in (0, math.pi):
        band.append(wave_path(m2, W - m2, mid, amp, 18, ph, 1.5))
        band.append(wave_path(m2, W - m2, H - mid, amp, 18, ph, 1.5))
        # vertical sides: generate then swap coords
        pts = []
        yy = m2
        while yy <= H - m2 + .01:
            pts.append((mid + amp * math.sin(2 * math.pi * yy / 18 + ph), yy))
            yy += 1.5
        band.append('M' + ' L'.join(f'{f(px)},{f(py)}' for px, py in pts))
        band.append('M' + ' L'.join(f'{f(W - px)},{f(py)}' for px, py in pts))
    s.append(f'<path d="{" ".join(band)}" fill="none" stroke="#5f8f96" stroke-width=".6" opacity=".6"/>')
    for (qx, qy) in ((mid, mid), (W - mid, mid), (mid, H - mid), (W - mid, H - mid)):
        s.append(f'<circle cx="{f(qx)}" cy="{f(qy)}" r="13" fill="#f3eddc"/>')
        s.append(f'<path d="{rosette(qx, qy, 9, 3, 8, 3, 3)}" fill="none" stroke="#3d6a78" stroke-width=".6" opacity=".7"/>')
    # header
    s.append(f'<text x="{W/2}" y="96" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="25" '
             f'letter-spacing="5" fill="#2b4f6e">TINNED FISH PASSPORT · VISAS</text>')
    micro = 'ALASKA · TINNED FISH · ' * 6 + 'ALASKA'
    s.append(f'<line x1="120" y1="114" x2="{W-120}" y2="114" stroke="#2b4f6e" stroke-width=".8" opacity=".6"/>')
    s.append(f'<text x="{W/2}" y="126" text-anchor="middle" font-family="DejaVu Sans" font-size="6.2" letter-spacing=".6" '
             f'fill="#2b4f6e" opacity=".55" textLength="{W-240}" lengthAdjust="spacingAndGlyphs">{micro}</text>')
    s.append(f'<line x1="120" y1="132" x2="{W-120}" y2="132" stroke="#2b4f6e" stroke-width=".8" opacity=".6"/>')
    # page number
    s.append(f'<text x="{W/2}" y="{H-62}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="20" '
             f'fill="#2b4f6e" letter-spacing="2">{pageno}</text>')
    s.append(f'<path d="M{W/2-60},{H-69} h34 M{W/2+26},{H-69} h34" stroke="#2b4f6e" stroke-width=".9" opacity=".6"/>')
    return '\n'.join(s)


def wrap(text, font, size, maxw):
    words, lines, cur = text.split(), [], ''
    for w_ in words:
        t = (cur + ' ' + w_).strip()
        if cur and tw(t, font, size) > maxw:
            lines.append(cur); cur = w_
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines or ['']


# ---- individual NPS-style cancellation stamps -----------------------------
INKS = ['#22407a', '#74331f', '#2c6a44', '#5b3d8c']      # navy, red-brown, green, purple
RATING_RED = '#c8201a'
SHAPES = ['circle']
ICONS = ['fish', 'mountain', 'tin', 'spruce']
# 2 x 4 grid of slots, filled in a zig-zag so 1-3 stamps already look scattered.
# slot index -> (row, col).  Entry i always lands in slot i, so adding entries
# never moves the stamps that are already on the page.
SLOT_CELL = [(0, 0), (1, 1), (2, 0), (3, 1), (0, 1), (1, 0), (2, 1), (3, 0)]
COL_X = [262, 638]
ROW_Y = [350, 582, 814, 1046]   # top band (y 140-232) is reserved for the brand logo
SAFE = (60, 236, W - 60, 1170)          # stamps stay inside: x0, y0, x1, y1


def h32(*parts):
    return zlib.crc32('|'.join(map(str, parts)).encode())


def fit_block(text, font, maxw, maxh, smax, smin=11, max_lines=3, lh=1.08):
    for s in range(smax, smin - 1, -1):
        lines = wrap(text, font, s, maxw)
        hh = s * 0.74 + (len(lines) - 1) * s * lh
        if len(lines) <= max_lines and hh <= maxh and all(tw(l, font, s) <= maxw for l in lines):
            return s, lines
    return smin, wrap(text, font, smin, maxw)


def name_block(text, cx, cy, maxw, maxh, smax, color):
    """Fish name, uppercase condensed bold, centred on (cx, cy)."""
    text = text.upper()
    s, lines = fit_block(text, 'cond', maxw, maxh, smax)
    lh = 1.08
    hh = s * 0.74 + (len(lines) - 1) * s * lh
    y0 = cy - hh / 2 + s * 0.74
    return ''.join(f'<text x="{f(cx)}" y="{f(y0 + i*s*lh)}" text-anchor="middle" font-family="Barlow Condensed" '
                   f'font-weight="700" font-size="{s}" letter-spacing=".5" fill="{color}">{esc(l)}</text>'
                   for i, l in enumerate(lines))


ABBR = [(' AND ', ' & '), ('COMPANY', 'CO.'), ('CORPORATION', 'CORP.'), ('INCORPORATED', 'INC.'),
        ('LIMITED', 'LTD.'), ('MOUNTAIN', 'MTN.'), ('BROTHERS', 'BROS.'), ('INTERNATIONAL', "INT'L")]


def fit_line(text, font, maxw, smax, spacing, smin=9.5):
    """Shrink (size, then tracking) to fit; if still too long, abbreviate, drop a leading THE,
    then trim trailing words with an ellipsis.  Returns (size, spacing, text)."""
    def fits(t, s, sp):
        return tw(t, font, s, sp) <= maxw
    s = smax
    while s > smin and not fits(text, s, spacing):
        s -= 0.5
    for sp in (spacing, spacing * 0.6, 0.8):
        if fits(text, s, sp):
            return s, sp, text
    sp = 0.8
    t = ' ' + text.upper() + ' '
    for x, y in ABBR:
        t = t.replace(' ' + x.strip() + ' ', ' ' + y.strip() + ' ')
    t = ' '.join(t.split())
    if t.startswith('THE ') and not fits(t, s, sp):
        t = t[4:]
    if fits(t, s, sp):
        return s, sp, t
    words = t.split()
    while len(words) > 1:
        words.pop()
        while len(words) > 1 and words[-1] in ('&', 'OF', 'THE', 'AND', '-', '·'):
            words.pop()
        if fits(' '.join(words) + '…', s, sp):
            return s, sp, ' '.join(words) + '…'
    return s, sp, ' '.join(words)


def straight(text, cx, y, maxw, smax, color, spacing=2.5, font='sansb'):
    s, spacing, text = fit_line(text, font, maxw, smax, spacing)
    fam = 'DejaVu Sans' if font.startswith('sans') else 'Barlow Condensed'
    return (f'<text x="{f(cx)}" y="{f(y)}" text-anchor="middle" font-family="{fam}" font-weight="bold" '
            f'font-size="{f(s)}" letter-spacing="{f(spacing)}" fill="{color}">{esc(text)}</text>')


def arc_text(text, pid, length, smax, color, spacing=2.5):
    s, spacing, text = fit_line(text, 'sansb', length, smax, spacing)
    return (f'<text font-family="DejaVu Sans" font-weight="bold" font-size="{f(s)}" letter-spacing="{f(spacing)}" fill="{color}">'
            f'<textPath href="#{pid}" startOffset="50%" text-anchor="middle">{esc(text)}</textPath></text>')


def rating(r, cx, y, size, ink, deco=True):
    t = f'{r}/10'
    w_ = tw(t, 'sansb', size)
    s = (f'<text x="{f(cx)}" y="{f(y)}" text-anchor="middle" font-family="DejaVu Sans" font-weight="bold" '
         f'font-size="{size}" fill="{RATING_RED}">{esc(t)}</text>')
    if deco:
        yy = y - size * 0.36
        for sg in (-1, 1):
            x = cx + sg * (w_ / 2 + 13)
            s += f'<polygon points="{star_pts(x, yy, 6.5, 2.6, 5)}" fill="{ink}"/>'
    return s


def icon(kind, cx, cy, w, c):
    if kind == 'fish':
        k = w / 224
        return (f'<g transform="translate({f(cx)} {f(cy + 4*k)}) scale({k:.3f})"><path d="{SALMON}" fill="{c}"/>'
                f'<circle cx="88" cy="-4" r="5" fill="#f4eedd"/></g>')
    if kind == 'mountain':
        k = w / 100
        pts = [(-50, 14), (-26, -6), (-16, 2), (2, -22), (14, -10), (22, -16), (50, 14)]
        p = ' '.join(f'{f(cx + x*k)},{f(cy + y*k)}' for x, y in pts)
        snow = [(-5, -11), (2, -22), (9, -14), (5, -9), (0, -13)]
        q = ' '.join(f'{f(cx + x*k)},{f(cy + y*k)}' for x, y in snow)
        return (f'<polygon points="{p}" fill="none" stroke="{c}" stroke-width="{f(2.6*k)}" stroke-linejoin="round"/>'
                f'<polygon points="{q}" fill="{c}"/>'
                f'<polygon points="{star_pts(cx + 34*k, cy - 18*k, 5*k, 2*k, 5)}" fill="{c}"/>'
                f'<path d="M{f(cx-50*k)},{f(cy+19*k)} H{f(cx+50*k)}" stroke="{c}" stroke-width="{f(2*k)}"/>')
    if kind == 'tin':
        h = w * 0.5
        return f'<g transform="translate({f(cx + h*0.18)} {f(cy)})" fill="none" stroke="{c}">{tin_icon(w*0.88, h, max(2.2, w/22))}</g>'
    if kind == 'spruce':
        hgt = w * 0.55
        d = spruce(cx, cy + hgt / 2, hgt, 4) + spruce(cx - w * 0.3, cy + hgt / 2, hgt * 0.72, 3) + spruce(cx + w * 0.3, cy + hgt / 2, hgt * 0.78, 3)
        return f'<path d="{d}" fill="{c}"/>'
    return ''


def shp_circle(brand, fish, r, c, ic, uid):
    R = 112
    g = [f'<circle r="{R}" fill="none" stroke="{c}" stroke-width="5"/>',
         f'<circle r="{R-8}" fill="none" stroke="{c}" stroke-width="1.6"/>',
         f'<circle r="80" fill="none" stroke="{c}" stroke-width="2.6"/>',
         f'<defs><path id="{uid}t" d="M-88,0 A88,88 0 0 1 88,0"/><path id="{uid}b" d="M-98,0 A98,98 0 0 0 98,0"/></defs>',
         arc_text(brand, f'{uid}t', 0.70 * math.pi * 88, 16, c),
         arc_text('TINNED FISH PASSPORT', f'{uid}b', 0.62 * math.pi * 98, 10.5, c, 2),
         f'<polygon points="{star_pts(-92, 0, 6, 2.4, 5)}" fill="{c}"/><polygon points="{star_pts(92, 0, 6, 2.4, 5)}" fill="{c}"/>',
         species_icon(fish, 0, -51, 66, c),
         name_block(fish, 0, 0, 134, 58, 30, c),
         rating(r, 0, 57, 25, c, deco=False)]
    return ''.join(g), (-R - 3, -R - 3, R + 3, R + 3)


def shp_oval(brand, fish, r, c, ic, uid):
    a, b = 160, 106
    g = [f'<ellipse rx="{a}" ry="{b}" fill="none" stroke="{c}" stroke-width="5"/>',
         f'<ellipse rx="{a-8}" ry="{b-8}" fill="none" stroke="{c}" stroke-width="1.6"/>',
         f'<ellipse rx="126" ry="74" fill="none" stroke="{c}" stroke-width="2.6"/>',
         f'<defs><path id="{uid}t" d="M-136,0 A136,82 0 0 1 136,0"/><path id="{uid}b" d="M-143,0 A143,90 0 0 0 143,0"/></defs>',
         arc_text(brand, f'{uid}t', 250, 16, c),
         arc_text('TINNED FISH PASSPORT', f'{uid}b', 210, 10.5, c, 2),
         f'<polygon points="{star_pts(-139, 0, 6, 2.4, 5)}" fill="{c}"/><polygon points="{star_pts(139, 0, 6, 2.4, 5)}" fill="{c}"/>',
         icon(ic, 0, -50, 64, c),
         name_block(fish, 0, -1, 204, 56, 34, c),
         rating(r, 0, 58, 26, c)]
    return ''.join(g), (-a - 3, -b - 3, a + 3, b + 3)


def shp_rect(brand, fish, r, c, ic, uid):
    w2, h2 = 160, 98
    g = [f'<rect x="{-w2}" y="{-h2}" width="{2*w2}" height="{2*h2}" rx="18" fill="none" stroke="{c}" stroke-width="5"/>',
         f'<rect x="{-w2+9}" y="{-h2+9}" width="{2*w2-18}" height="{2*h2-18}" rx="11" fill="none" stroke="{c}" stroke-width="1.6"/>',
         straight(brand, 0, -62, 268, 17, c),
         f'<path d="M-138,-51 H138" stroke="{c}" stroke-width="2.2"/>',
         f'<path d="M-76,-36 V78" stroke="{c}" stroke-width="1.6"/>',
         icon(ic, -114, 16, 64, c),
         name_block(fish, 32, -1, 204, 66, 36, c),
         rating(r, 32, 71, 27, c)]
    return ''.join(g), (-w2 - 3, -h2 - 3, w2 + 3, h2 + 3)


def shp_tin(brand, fish, r, c, ic, uid):
    w2, h2 = 145, 88
    g = [f'<rect x="{-w2}" y="{-h2}" width="{2*w2}" height="{2*h2}" rx="56" fill="none" stroke="{c}" stroke-width="9"/>',
         f'<rect x="{-w2+18}" y="{-h2+18}" width="{2*w2-36}" height="{2*h2-36}" rx="40" fill="none" stroke="{c}" stroke-width="2.6" stroke-dasharray="7 5"/>',
         f'<g fill="none" stroke="{c}"><ellipse cx="-168" cy="0" rx="32" ry="23" stroke-width="7"/>'
         f'<ellipse cx="-168" cy="0" rx="15" ry="9" stroke-width="3"/>'
         f'<path d="M-139,-9 H-100 M-139,9 H-100" stroke-width="6"/></g><circle cx="-97" cy="0" r="8" fill="{c}"/>',
         f'<path d="M-74,-46 V46" stroke="{c}" stroke-width="2"/>',
         straight(brand, 26, -42, 168, 15, c, 2),
         f'<path d="M-52,-32 H104" stroke="{c}" stroke-width="2"/>',
         name_block(fish, 26, -2, 172, 48, 32, c),
         rating(r, 26, 55, 25, c)]
    return ''.join(g), (-203, -h2 - 5, w2 + 5, h2 + 5)


def _hex(sx, sy):
    return ' '.join(f'{f(x*sx)},{f(y*sy)}' for x, y in [(-168, 0), (-108, -104), (108, -104), (168, 0), (108, 104), (-108, 104)])


def shp_hex(brand, fish, r, c, ic, uid):
    g = [f'<polygon points="{_hex(1, 1)}" fill="none" stroke="{c}" stroke-width="5" stroke-linejoin="round"/>',
         f'<polygon points="{_hex(.92, .91)}" fill="none" stroke="{c}" stroke-width="1.6" stroke-linejoin="round"/>',
         straight(brand, 0, -66, 206, 15, c),
         f'<path d="M-92,-56 H92" stroke="{c}" stroke-width="2"/>',
         icon(ic, 0, -33, 60, c),
         name_block(fish, 0, 11, 228, 48, 32, c),
         rating(r, 0, 70, 25, c)]
    return ''.join(g), (-171, -107, 171, 107)


def _shield(k, dy=0):
    pts = [(-112, -96), (-112, -112), (-96, -112), (96, -112), (112, -112), (112, -96), (112, 24),
           (112, 72), (60, 100), (0, 118), (-60, 100), (-112, 72), (-112, 24)]
    P = [(x * k, y * k + dy) for x, y in pts]
    s = lambda i: f'{f(P[i][0])},{f(P[i][1])}'
    return (f'M{s(0)} Q{s(1)} {s(2)} L{s(3)} Q{s(4)} {s(5)} L{s(6)} C{s(7)} {s(8)} {s(9)} '
            f'C{s(10)} {s(11)} {s(12)} Z')


def shp_shield(brand, fish, r, c, ic, uid):
    g = [f'<path d="{_shield(1)}" fill="none" stroke="{c}" stroke-width="5" stroke-linejoin="round"/>',
         f'<path d="{_shield(.915, -1)}" fill="none" stroke="{c}" stroke-width="1.6" stroke-linejoin="round"/>',
         straight(brand, 0, -82, 176, 14, c, 2),
         f'<path d="M-90,-71 H90" stroke="{c}" stroke-width="2"/>',
         icon(ic, 0, -47, 58, c),
         name_block(fish, 0, -3, 180, 50, 30, c),
         rating(r, 0, 54, 25, c),
         f'<polygon points="{star_pts(0, 82, 8, 3.2, 5)}" fill="{c}"/>']
    return ''.join(g), (-115, -115, 115, 121)


SHAPE_FN = {'circle': shp_circle, 'oval': shp_oval, 'rect': shp_rect, 'tin': shp_tin,
            'hex': shp_hex, 'shield': shp_shield}


def ink_filter(fid, seed):
    return f'''<filter id="{fid}" x="-6%" y="-6%" width="112%" height="112%" color-interpolation-filters="sRGB">
  <feGaussianBlur in="SourceGraphic" stdDeviation=".4" result="soft"/>
  <feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2" seed="{seed}" result="fine"/>
  <feDisplacementMap in="soft" in2="fine" scale="2.6" xChannelSelector="R" yChannelSelector="G" result="rough"/>
  <feTurbulence type="fractalNoise" baseFrequency=".03" numOctaves="3" seed="{seed+5}" result="blot"/>
  <feColorMatrix in="blot" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -1.8 0 0 0 1.9" result="blotA"/>
  <feTurbulence type="fractalNoise" baseFrequency="1.2" numOctaves="1" seed="{seed+9}" result="speck"/>
  <feColorMatrix in="speck" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -9 0 0 0 6.7" result="speckA"/>
  <feComposite in="blotA" in2="speckA" operator="arithmetic" k1="1" result="mask"/>
  <feComposite in="rough" in2="mask" operator="in"/>
</filter>'''


# ---- species icons (head points right, drawn in a ~224 x 90 box centred on 0,0) ----
PAPER = '#f4eedd'


def _fish(top=30, bot=26, tail='fork', snout=108, back=-92):
    t = {'fork': f'L-116,-30 L-104,0 L-116,28',
         'square': f'L-112,-26 L-112,24',
         'crescent': f'L-120,-42 Q-100,0 -120,40'}[tail]
    return (f'M{snout},0 C{snout-18},{-top} 40,{-top-8} -30,{-top+6} C-62,{-top/2} -80,-10 {back},-5 {t} '
            f'L{back},5 C-80,10 -62,{bot/2} -30,{bot-4} C40,{bot+6} {snout-18},{bot} {snout},0 Z')


def _eye(x, y=-4, r=5):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{PAPER}"/>'


def sp_salmon(c):
    return f'<path d="{SALMON}" fill="{c}"/>' + _eye(88)


def sp_sockeye(c):
    d = ('M106,4 C104,-10 92,-22 74,-34 C58,-46 26,-46 -20,-30 C-52,-22 -78,-10 -92,-5 L-116,-30 L-104,0 L-116,28 '
         'L-92,5 C-70,14 -40,26 0,30 C40,32 76,26 96,16 C104,14 112,20 115,28 C118,14 113,6 106,4 Z')
    fins = 'M-6,-38 L-26,-58 L-36,-33 Z M-50,20 L-62,36 L-40,24 Z'
    return f'<path d="{d} {fins}" fill="{c}"/>' + _eye(86, -6) + f'<path d="M70,-24 Q62,-4 70,14" stroke="{PAPER}" stroke-width="4" fill="none"/>'


def sp_trout(c):
    d = _fish(26, 24, 'square')
    fins = 'M10,-28 L-4,-44 L-26,-26 Z M-62,-12 L-68,-24 L-74,-10 Z M-20,22 L-34,36 L-40,20 Z M40,22 L30,36 L22,24 Z'
    spots = ''.join(_eye(x, y, 3.6) for x, y in [(-60, -8), (-40, -16), (-20, -10), (0, -18), (20, -12), (-48, 6), (-10, 2), (40, -18), (-78, -2)])
    return (f'<path d="{d} {fins}" fill="{c}"/>' + _eye(90, -3) +
            f'<path d="M-90,0 C-40,4 30,4 80,-2" stroke="{PAPER}" stroke-width="3.5" fill="none"/>' + spots +
            f'<path d="M76,-18 Q68,0 76,16" stroke="{PAPER}" stroke-width="3.5" fill="none"/>')


def sp_cod(c):
    d = _fish(34, 32, 'square', 106, -94)
    fins = ('M74,-30 Q66,-52 50,-36 Z M36,-38 Q20,-62 -2,-38 Z M-14,-36 Q-36,-58 -58,-26 Z '
            'M20,34 Q0,52 -16,32 Z M-24,30 Q-44,50 -62,22 Z')
    return (f'<path d="{d} {fins}" fill="{c}"/>' + _eye(84, -8) +
            f'<path d="M98,14 Q100,26 94,34" stroke="{c}" stroke-width="4" fill="none" stroke-linecap="round"/>'
            f'<path d="M-84,-2 C-40,-10 30,-12 70,-6" stroke="{PAPER}" stroke-width="3" fill="none"/>'
            f'<path d="M72,-22 Q62,0 72,20" stroke="{PAPER}" stroke-width="3.5" fill="none"/>')


def sp_tuna(c):
    d = _fish(38, 34, 'crescent', 110, -96)
    fins = ('M30,-42 L10,-70 L-6,-38 Z M14,36 L0,60 L-14,32 Z ' +
            ' '.join(f'M{x},-{18-k*2} l-6,-9 l-4,8 Z M{x},{16-k*2} l-6,9 l-4,-8 Z' for k, x in enumerate(range(-30, -90, -14))))
    return (f'<path d="{d} {fins}" fill="{c}"/>' + _eye(88, -6) +
            f'<path d="M66,-28 Q56,0 66,24" stroke="{PAPER}" stroke-width="3.5" fill="none"/>')


def sp_mackerel(c):
    d = _fish(22, 20, 'fork', 110)
    fins = 'M20,-24 L6,-40 L-8,-20 Z M-30,-18 L-38,-30 L-46,-14 Z M-30,16 L-40,28 L-46,12 Z'
    stripes = ''.join(f'<path d="M{x},-20 q6,6 0,12 q-6,6 0,12" stroke="{PAPER}" stroke-width="3" fill="none"/>' for x in range(-60, 70, 18))
    return f'<path d="{d} {fins}" fill="{c}"/>' + stripes + _eye(92, -2, 4.5)


def sp_sardine(c, slim=18):
    d = _fish(slim, slim - 2, 'fork', 110)
    fins = f'M10,-{slim} L-4,-{slim+16} L-16,-{slim-2} Z M-40,{slim-6} L-50,{slim+8} L-56,{slim-8} Z'
    return (f'<path d="{d} {fins}" fill="{c}"/>' + _eye(94, -2, 4.5) +
            f'<path d="M-86,0 C-30,-6 40,-6 80,-2" stroke="{PAPER}" stroke-width="3" fill="none"/>'
            f'<path d="M80,-12 Q74,0 80,10" stroke="{PAPER}" stroke-width="3" fill="none"/>')


def sp_herring(c):
    """Atlantic herring (also kippers / sild): slim, silvery, single mid dorsal, deeply forked tail, gill line."""
    d = _fish(21, 23, 'fork', 110)
    fins = 'M2,-21 L-10,-40 L-24,-19 Z M-44,19 L-54,32 L-60,16 Z M30,22 L22,32 L16,22 Z'
    return (f'<path d="{d} {fins}" fill="{c}"/>' + _eye(93, -3, 5) +
            f'<path d="M78,-15 Q70,0 78,14" stroke="{PAPER}" stroke-width="3.5" fill="none"/>'
            f'<path d="M-84,4 C-40,8 30,8 70,4" stroke="{PAPER}" stroke-width="2.6" fill="none" stroke-dasharray="7 5"/>')


def sp_anchovy(c):
    return sp_sardine(c, 13)


def sp_octopus(c):
    arms = ''.join(f'<path d="M{x},6 C{x+dx*0.4},30 {x+dx},34 {x+dx*1.2},{20+abs(dx)/4} q{dx/6},-10 {dx/4},-2" '
                   f'stroke="{c}" stroke-width="9" fill="none" stroke-linecap="round"/>'
                   for x, dx in [(-24, -70), (-14, -40), (-4, -14), (4, 14), (14, 40), (24, 70)])
    return (f'<ellipse cx="0" cy="-18" rx="30" ry="30" fill="{c}"/><rect x="-28" y="-18" width="56" height="26" fill="{c}"/>'
            + arms + _eye(-11, -8, 4.5) + _eye(11, -8, 4.5))


def sp_mussel(c):
    d = 'M-70,24 C-90,6 -60,-30 0,-38 C60,-44 98,-26 92,-6 C86,14 30,34 -20,36 C-44,37 -62,32 -70,24 Z'
    ridges = ''.join(f'<path d="M-66,22 C{-40+k*14},{-6-k*8} {30+k*8},{-14-k*6} {88-k*2},{-4-k*8}" stroke="{PAPER}" stroke-width="3" fill="none"/>' for k in range(3))
    return f'<path d="{d}" fill="{c}"/>' + ridges


def sp_shell(c):
    d = 'M0,40 L-62,-14 C-56,-40 -24,-48 0,-48 C24,-48 56,-40 62,-14 Z M-14,40 L-26,48 L26,48 L14,40 Z'
    ribs = ''.join(f'<path d="M0,38 L{x},-40" stroke="{PAPER}" stroke-width="3"/>' for x in (-44, -22, 0, 22, 44))
    return f'<path d="{d}" fill="{c}"/>' + ribs


def sp_generic(c):
    d = _fish(28, 26, 'fork', 108)
    return (f'<path d="{d} M10,-30 L-6,-46 L-24,-26 Z M-30,22 L-40,36 L-48,18 Z" fill="{c}"/>' + _eye(88, -4) +
            f'<path d="M72,-20 Q64,0 72,18" stroke="{PAPER}" stroke-width="3.5" fill="none"/>')


# keyword -> icon; first match wins (checked in order, on the lower-cased fish name).
SPECIES = [
    (('sockeye', 'red salmon'), sp_sockeye),
    (('trout', 'char', 'steelhead'), sp_trout),
    (('salmon', 'king', 'chinook', 'coho', 'keta', 'chum', 'lox'), sp_salmon),
    (('cod', 'pollock', 'haddock', 'hake', 'sablefish'), sp_cod),
    (('tuna', 'albacore', 'bonito', 'skipjack', 'ventresca'), sp_tuna),
    (('mackerel', 'caballa'), sp_mackerel),
    (('anchov', 'boquer'), sp_anchovy),
    (('herring', 'kipper', 'sild', 'bloater'), sp_herring),
    (('sardine', 'sardinha', 'sprat', 'brisling', 'pilchard'), sp_sardine),
    (('octopus', 'squid', 'calamar', 'pulpo', 'cuttlefish'), sp_octopus),
    (('mussel',), sp_mussel),
    (('oyster', 'clam', 'scallop', 'cockle', 'razor', 'berberecho', 'zamburi'), sp_shell),
]


def species_icon(fish, cx, cy, w, c):
    n = fish.lower()
    fn = next((f_ for keys, f_ in SPECIES if any(k in n for k in keys)), sp_generic)
    k = w / 224
    return f'<g transform="translate({f(cx)} {f(cy)}) scale({k:.3f})">{fn(c)}</g>'


# ---- brand logos (sidecar logos.json: {"brand_key": "logos/file.svg|png"}; missing -> no logo) ----
def brand_logo(key, box=(450, 186, 340, 74)):
    import base64
    try:
        mp = json.load(open(os.path.join(HERE, 'logos.json')))
    except FileNotFoundError:
        return ''
    rel = mp.get(key)
    p = rel and os.path.join(HERE, rel)
    if not p or not os.path.exists(p):
        return ''
    cx, cy, bw, bh = box
    if p.endswith('.svg'):
        import re
        s = open(p).read()
        vb = re.search(r'viewBox="([\d.\s-]+)"', s)
        iw, ih = map(float, vb.group(1).split()[2:4])
        mime = 'image/svg+xml'
    else:
        from PIL import Image
        iw, ih = Image.open(p).size
        mime = 'image/png'
    sc = min(bw / iw, bh / ih)
    w_, h_ = iw * sc, ih * sc
    data = base64.b64encode(open(p, 'rb').read()).decode()
    return (f'<g opacity=".9" style="mix-blend-mode:multiply" filter="url(#logoInk)">'
            f'<image x="{f(cx-w_/2)}" y="{f(cy-h_/2)}" width="{f(w_)}" height="{f(h_)}" href="data:{mime};base64,{data}"/></g>')


LOGO_FILTER = '''<filter id="logoInk" x="-5%" y="-10%" width="110%" height="120%">
  <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="1" seed="4" result="n"/>
  <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -4 0 0 0 3.4" result="nA"/>
  <feComposite in="SourceGraphic" in2="nA" operator="in"/>
</filter>'''


def place_stamp(key, name, slot, fish, r):
    """Deterministic placement/styling for entry number `slot` of a brand."""
    hb = h32(key) % 997
    row, col = SLOT_CELL[slot % 8]
    shape = SHAPES[(slot + hb) % len(SHAPES)]
    ink = INKS[(row + 2 * col + hb) % len(INKS)]
    ic = ICONS[(slot + hb // 7) % len(ICONS)]
    hs = h32(key, slot, 'jitter')
    ang = 2.5 + (hs % 1000) / 1000 * 5.5
    ang = -ang if (hs >> 10) & 1 else ang
    jx = ((hs >> 11) % 57) - 28
    jy = ((hs >> 17) % 25) - 12
    body, (bx0, by0, bx1, by1) = SHAPE_FN[shape](name, fish, r, ink, ic, f's{slot}')
    # centre the stamp's bounding box on the slot, then clamp the rotated box inside SAFE
    ox, oy = -(bx0 + bx1) / 2, -(by0 + by1) / 2
    cx, cy = COL_X[col] + jx, ROW_Y[row] + jy
    a = math.radians(ang)
    corners = [(x + ox, y + oy) for x in (bx0, bx1) for y in (by0, by1)]
    rx = [x * math.cos(a) - y * math.sin(a) for x, y in corners]
    ry = [x * math.sin(a) + y * math.cos(a) for x, y in corners]
    cx = min(max(cx, SAFE[0] - min(rx)), SAFE[2] - max(rx))
    cy = min(max(cy, SAFE[1] - min(ry)), SAFE[3] - max(ry))
    op = 0.84 + (hs % 7) / 70
    fid = f'ink{slot}'
    return (f'<defs>{ink_filter(fid, (hs % 500) + 3)}</defs>'
            f'<g style="mix-blend-mode:multiply" opacity="{op:.2f}" filter="url(#{fid})">'
            f'<g transform="translate({f(cx)} {f(cy)}) rotate({ang:.2f}) translate({f(ox)} {f(oy)})">{body}</g></g>')


def visa_page(key, name, items, pageno):
    if len(items) > 8:
        print(f'warning: {key} has {len(items)} entries; only the first 8 fit on one page')
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    svg.append(page_background(pageno))
    svg.append(f'<defs>{LOGO_FILTER}</defs>' + brand_logo(key))
    for i, (fish, r) in enumerate(items[:8]):
        svg.append(place_stamp(key, name, i, fish, r))
    svg.append('</svg>')
    render('\n'.join(svg), os.path.join(HERE, f'passport_{key}.png'))


# ----------------------------------------------------------------- cover
COVER_DEFS = '''<defs>
<radialGradient id="leather" cx=".42" cy=".38" r=".85">
  <stop offset="0" stop-color="#18325a"/><stop offset=".55" stop-color="#0f2342"/><stop offset="1" stop-color="#07142a"/>
</radialGradient>
<filter id="grain" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency=".55" numOctaves="4" seed="4" result="t"/>
  <feDiffuseLighting in="t" surfaceScale="2.2" diffuseConstant="1" lighting-color="#ffffff" result="l">
    <feDistantLight azimuth="235" elevation="58"/>
  </feDiffuseLighting>
  <feColorMatrix in="l" type="matrix" values=".33 .33 .33 0 -.3  .33 .33 .33 0 -.3  .33 .33 .33 0 -.3  0 0 0 0 1"/>
</filter>
<filter id="mottle" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency=".006" numOctaves="3" seed="9"/>
  <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.2 .75"/>
</filter>
<linearGradient id="gold" x1="0" y1="0" x2=".35" y2="1">
  <stop offset="0" stop-color="#f6e3a1"/><stop offset=".22" stop-color="#c99a3f"/>
  <stop offset=".45" stop-color="#f3d989"/><stop offset=".62" stop-color="#a87a2a"/>
  <stop offset=".82" stop-color="#e6c46e"/><stop offset="1" stop-color="#9a6e24"/>
</linearGradient>
<linearGradient id="goldH" x1="0" y1="0" x2="1" y2=".25">
  <stop offset="0" stop-color="#a87a2a"/><stop offset=".25" stop-color="#f3d989"/>
  <stop offset=".5" stop-color="#c3923a"/><stop offset=".75" stop-color="#f6e3a1"/><stop offset="1" stop-color="#9a6e24"/>
</linearGradient>
<filter id="foil" x="-10%" y="-10%" width="120%" height="120%" color-interpolation-filters="sRGB">
  <feGaussianBlur in="SourceAlpha" stdDeviation="1.1" result="b"/>
  <feSpecularLighting in="b" surfaceScale="2.4" specularConstant=".85" specularExponent="18" lighting-color="#fff6d8" result="spec">
    <feDistantLight azimuth="230" elevation="42"/>
  </feSpecularLighting>
  <feComposite in="spec" in2="SourceAlpha" operator="in" result="specIn"/>
  <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="1" seed="3" result="n"/>
  <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -6 0 0 0 5.3" result="nA"/>
  <feComposite in="SourceGraphic" in2="nA" operator="in" result="worn"/>
  <feComposite in="worn" in2="specIn" operator="arithmetic" k2="1" k3=".55" result="lit"/>
  <feOffset in="SourceAlpha" dx="0" dy="-1.2" result="o"/>
  <feFlood flood-color="#050d1c" flood-opacity=".75"/><feComposite in2="o" operator="in" result="sh"/>
  <feMerge><feMergeNode in="sh"/><feMergeNode in="lit"/></feMerge>
</filter>
<filter id="deboss" x="-5%" y="-5%" width="110%" height="110%">
  <feOffset in="SourceAlpha" dx="0" dy="1.4" result="lo"/>
  <feFlood flood-color="#6f8fb8" flood-opacity=".28"/><feComposite in2="lo" operator="in" result="light"/>
  <feOffset in="SourceAlpha" dx="0" dy="-1.2" result="dk"/>
  <feFlood flood-color="#000" flood-opacity=".55"/><feComposite in2="dk" operator="in" result="dark"/>
  <feMerge><feMergeNode in="light"/><feMergeNode in="dark"/></feMerge>
</filter>
<radialGradient id="vig" cx=".5" cy=".5" r=".72"><stop offset=".62" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".45"/></radialGradient>
<linearGradient id="spine" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".45"/><stop offset=".06" stop-color="#000" stop-opacity=".12"/><stop offset=".09" stop-color="#9fb6d8" stop-opacity=".06"/><stop offset=".14" stop-color="#000" stop-opacity="0"/></linearGradient>
'''


def cover():
    cx, cy = W / 2, 585
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    s.append(COVER_DEFS)
    s.append(f'<symbol id="salmon" viewBox="-120 -52 232 88" overflow="visible"><path d="{SALMON}"/></symbol>')
    R_out, R_in = 205, 166
    s.append(f'<path id="arcTop" d="M{f(cx-174)},{f(cy)} A174,174 0 0 1 {f(cx+174)},{f(cy)}"/>')
    s.append(f'<path id="arcBot" d="M{f(cx-189)},{f(cy)} A189,189 0 0 0 {f(cx+189)},{f(cy)}"/>')
    s.append('</defs>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#leather)"/>')
    s.append(f'<rect width="{W}" height="{H}" filter="url(#grain)" style="mix-blend-mode:soft-light" opacity=".9"/>')
    s.append(f'<rect width="{W}" height="{H}" filter="url(#mottle)" opacity=".25"/>')
    # debossed frame
    s.append(f'<g filter="url(#deboss)" fill="none" stroke="#000" stroke-width="2.2"><rect x="46" y="46" width="{W-92}" height="{H-92}" rx="18"/>'
             f'<rect x="58" y="58" width="{W-116}" height="{H-116}" rx="12" stroke-width="1"/></g>')
    gold = []
    # Title
    gold.append(f'<text x="{cx}" y="196" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="68" letter-spacing="9" fill="url(#goldH)">TINNED FISH</text>')
    gold.append(f'<path d="M{cx-200},232 H{cx-28} M{cx+28},232 H{cx+200}" stroke="url(#goldH)" stroke-width="2"/>')
    gold.append(f'<polygon points="{star_pts(cx, 232, 13, 4.5, 4)}" fill="url(#gold)"/>')
    gold.append(f'<text x="{cx}" y="985" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="84" letter-spacing="14" fill="url(#goldH)">PASSPORT</text>')
    gold.append(f'<text x="{cx}" y="1036" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="20" letter-spacing="9" fill="url(#goldH)">ALASKA · NORTH PACIFIC</text>')
    # Emblem ---------------------------------------------------------
    e = []
    e.append(f'<circle cx="{cx}" cy="{cy}" r="{R_out}" fill="none" stroke="url(#gold)" stroke-width="5"/>')
    e.append(f'<circle cx="{cx}" cy="{cy}" r="{R_out-9}" fill="none" stroke="url(#gold)" stroke-width="1.4"/>')
    e.append(f'<circle cx="{cx}" cy="{cy}" r="{R_in}" fill="none" stroke="url(#gold)" stroke-width="3"/>')
    e.append(f'<circle cx="{cx}" cy="{cy}" r="{R_in-7}" fill="none" stroke="url(#gold)" stroke-width="1"/>')
    e.append(f'<text font-family="Cinzel" font-weight="700" font-size="23" letter-spacing="6" fill="url(#gold)">'
             f'<textPath href="#arcTop" startOffset="50%" text-anchor="middle">IN OLEO VERITAS</textPath></text>')
    e.append(f'<text font-family="Cinzel" font-weight="700" font-size="19" letter-spacing="6" fill="url(#gold)">'
             f'<textPath href="#arcBot" startOffset="50%" text-anchor="middle">SEA · SMOKE · SALT</textPath></text>')
    for a in (180, 0):
        rr = 181
        e.append(f'<polygon points="{star_pts(cx + rr*math.cos(math.radians(a)), cy, 9, 3, 4)}" fill="url(#gold)"/>')
    # inner scene clipped to inner disc
    sc = []
    sc.append(f'<clipPath id="disc"><circle cx="{cx}" cy="{cy}" r="{R_in-12}"/></clipPath>')
    sc.append(f'<g clip-path="url(#disc)">')
    # aurora rays
    for i, a in enumerate(range(-70, 71, 10)):
        r1, r2 = 30, 150
        ang = math.radians(a - 90)
        x0, y0 = cx + r1 * math.cos(ang), cy - 95 + r1 * math.sin(ang)
        x1, y1 = cx + r2 * math.cos(ang), cy - 95 + r2 * math.sin(ang)
        sc.append(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" stroke="url(#gold)" stroke-width="{1.6 if i%2 else .8}" opacity=".7"/>')
    sc.append(f'<polygon points="{star_pts(cx, cy-95, 26, 7, 8)}" fill="url(#gold)"/>')
    sc.append(f'<circle cx="{cx}" cy="{cy-95}" r="5" fill="#13294a"/>')
    # mountains
    mts = [(-170, 40), (-128, 4), (-108, 14), (-70, -30), (-48, -14), (-12, -62), (6, -48), (22, -56), (52, -16), (78, -30), (118, 6), (170, 40)]
    pts = ' '.join(f'{f(cx+x)},{f(cy+y)}' for x, y in mts)
    sc.append(f'<polygon points="{pts} {f(cx+170)},{f(cy+42)} {f(cx-170)},{f(cy+42)}" fill="url(#gold)"/>')
    snow = [(-12, -62), (-2, -44), (6, -48)]
    sc.append(f'<path d="M{f(cx-24)},{f(cy-46)} L{f(cx-12)},{f(cy-62)} L{f(cx+6)},{f(cy-48)} L{f(cx+22)},{f(cy-56)} L{f(cx+36)},{f(cy-38)} '
              f'L{f(cx+22)},{f(cy-42)} L{f(cx+10)},{f(cy-34)} L{f(cx-2)},{f(cy-42)} L{f(cx-14)},{f(cy-32)} Z" fill="#13294a" opacity=".55"/>')
    sc.append(f'<path d="M{f(cx-80)},{f(cy-18)} L{f(cx-70)},{f(cy-30)} L{f(cx-56)},{f(cy-18)} L{f(cx-64)},{f(cy-20)} L{f(cx-70)},{f(cy-14)} Z" fill="#13294a" opacity=".55"/>')
    # spruce trees at foot of mountains
    tp = ''
    for x, hh in [(-140, 50), (-124, 38), (-110, 46), (112, 46), (126, 36), (140, 52), (-150, 34), (152, 32)]:
        tp += spruce(cx + x, cy + 42, hh, 4)
    sc.append(f'<path d="{tp}" fill="url(#gold)" stroke="#13294a" stroke-width=".8"/>')
    # water band
    for k in range(5):
        sc.append(f'<path d="{wave_path(cx-170, cx+170, cy+52+k*11, 2.5, 34, k*1.1, 3)}" fill="none" stroke="url(#gold)" stroke-width="{1.8 - k*.2}"/>')
    # leaping salmon
    sc.append(f'<g transform="translate({cx+4} {cy+20}) rotate(-24) scale(.9)">'
              f'<path d="{SALMON}" fill="url(#gold)" stroke="#13294a" stroke-width="2.2"/>'
              f'<path d="{SALMON_DETAIL} M-50,-6 Q0,-12 60,-4" fill="none" stroke="#13294a" stroke-width="2"/>'
              f'<circle cx="88" cy="-4" r="3.6" fill="#13294a"/></g>')
    # sardine tin at base
    tw_, th_ = 132, 52
    sc.append(f'<g transform="translate({cx+14} {cy+112})">'
              f'<rect x="{-tw_/2}" y="{-th_/2}" width="{tw_}" height="{th_}" rx="21" fill="url(#gold)" stroke="#13294a" stroke-width="2"/>'
              f'<rect x="{-tw_/2+7}" y="{-th_/2+7}" width="{tw_-14}" height="{th_-14}" rx="15" fill="none" stroke="#13294a" stroke-width="1.6" stroke-dasharray="4 3"/>'
              f'<ellipse cx="{-tw_/2-9}" cy="0" rx="12" ry="8.5" fill="none" stroke="url(#gold)" stroke-width="4"/>'
              f'<path d="M{-tw_/2+2},-4 H{-tw_/2+14} M{-tw_/2+2},4 H{-tw_/2+14}" stroke="url(#gold)" stroke-width="3"/>'
              f'</g>')
    sc.append('</g>')
    e.extend(sc)
    # spruce-bough wreath hugging the lower half of the ring
    rr = R_out + 20
    bough, stems = [], []
    for side in (-1, 1):
        a0, a1 = 97, 192                      # degrees (SVG, y down): bottom -> left side
        pts = []
        steps = 46
        for i in range(steps + 1):
            t = a0 + (a1 - a0) * i / steps
            a = math.radians(t if side < 0 else 180 - t)
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        stems.append('M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in pts))
        for i in range(1, steps + 1):
            (xa, ya), (xb, yb) = pts[i - 1], pts[i]
            dx, dy = xb - xa, yb - ya
            dl = math.hypot(dx, dy); dx, dy = dx / dl, dy / dl
            taper = 1 - (i / steps) ** 2 * 0.55
            for sgn in (1, -1):
                ang = math.atan2(dy, dx) + sgn * math.radians(42)
                ln = 15 * taper * (0.85 if i % 2 else 1)
                bough.append(f'M{f(xb)},{f(yb)} l{f(ln*math.cos(ang))},{f(ln*math.sin(ang))}')
        # tip
        bough.append(f'M{f(pts[-1][0])},{f(pts[-1][1])} l{f((pts[-1][0]-pts[-2][0])*2.2)},{f((pts[-1][1]-pts[-2][1])*2.2)}')
    e.append(f'<path d="{" ".join(stems)}" stroke="url(#gold)" stroke-width="2.6" fill="none" stroke-linecap="round"/>')
    e.append(f'<path d="{" ".join(bough)}" stroke="url(#gold)" stroke-width="1.7" stroke-linecap="round" fill="none"/>')
    # small knot of a ribbon where boughs meet at the bottom
    e.append(f'<circle cx="{cx}" cy="{cy+rr}" r="7" fill="url(#gold)"/>')
    gold.extend(e)
    # chip symbol
    gold.append(f'<g transform="translate({cx} 1118)" fill="none" stroke="url(#gold)" stroke-width="3.2">'
                f'<rect x="-34" y="-22" width="68" height="44" rx="3"/><circle r="11"/>'
                f'<path d="M-34,0 H-11 M11,0 H34"/></g>')
    s.append('<g filter="url(#foil)">' + '\n'.join(gold) + '</g>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#spine)"/>')
    s.append('</svg>')
    render('\n'.join(s), os.path.join(HERE, 'passport_cover.png'))


def back_cover():
    """Plain back cover: same leather + foil as the front, a small tin mark and one line of text."""
    cx = W / 2
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', COVER_DEFS,
         '<linearGradient id="spineR" x1="1" x2="0"><stop offset="0" stop-color="#000" stop-opacity=".45"/><stop offset=".06" stop-color="#000" stop-opacity=".12"/>'
         '<stop offset=".09" stop-color="#9fb6d8" stop-opacity=".06"/><stop offset=".14" stop-color="#000" stop-opacity="0"/></linearGradient></defs>']
    s.append(f'<rect width="{W}" height="{H}" fill="url(#leather)"/>')
    s.append(f'<rect width="{W}" height="{H}" filter="url(#grain)" style="mix-blend-mode:soft-light" opacity=".9"/>')
    s.append(f'<rect width="{W}" height="{H}" filter="url(#mottle)" opacity=".25"/>')
    s.append(f'<g filter="url(#deboss)" fill="none" stroke="#000" stroke-width="2.2"><rect x="46" y="46" width="{W-92}" height="{H-92}" rx="18"/>'
             f'<rect x="58" y="58" width="{W-116}" height="{H-116}" rx="12" stroke-width="1"/></g>')
    g, my = [], 1010
    g.append(f'<circle cx="{cx}" cy="{my}" r="54" fill="none" stroke="url(#gold)" stroke-width="3"/>')
    g.append(f'<circle cx="{cx}" cy="{my}" r="47" fill="none" stroke="url(#gold)" stroke-width="1"/>')
    tw_, th_ = 58, 30
    g.append(f'<g transform="translate({cx+5} {my})">'
             f'<rect x="{-tw_/2}" y="{-th_/2}" width="{tw_}" height="{th_}" rx="12" fill="none" stroke="url(#gold)" stroke-width="3"/>'
             f'<rect x="{-tw_/2+5}" y="{-th_/2+5}" width="{tw_-10}" height="{th_-10}" rx="8" fill="none" stroke="url(#gold)" stroke-width="1.2" stroke-dasharray="3 2.5"/>'
             f'<ellipse cx="{-tw_/2-8}" cy="0" rx="7" ry="5" fill="none" stroke="url(#gold)" stroke-width="2.4"/>'
             f'<path d="M{-tw_/2-1},-2.5 H{-tw_/2+5} M{-tw_/2-1},2.5 H{-tw_/2+5}" stroke="url(#gold)" stroke-width="2"/>'
             f'<g transform="scale(.15)"><path d="{SALMON}" fill="url(#gold)"/></g></g>')
    for a_ in (180, 0):
        g.append(f'<polygon points="{star_pts(cx + 51*math.cos(math.radians(a_)), my, 5, 1.8, 4)}" fill="url(#gold)"/>')
    g.append(f'<text x="{cx}" y="{my+100}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="13" '
             f'letter-spacing="5" fill="url(#goldH)">IN OLEO VERITAS · TINNED FISH PASSPORT</text>')
    s.append('<g filter="url(#foil)">' + '\n'.join(g) + '</g>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#spineR)"/>')
    s.append('</svg>')
    render('\n'.join(s), os.path.join(HERE, 'passport_back.png'))


def main():
    args = set(sys.argv[1:])
    do_pages = not args or '--pages' in args or any(a.startswith('--page=') for a in args)
    do_cover = not args or '--cover' in args
    do_back = not args or '--back' in args
    if do_pages:
        data = json.load(open(os.path.join(HERE, 'brands.json')))
        only = [a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--page=')]
        for i, (key, (name, items)) in enumerate(data.items(), start=1):
            if not only or key in only:
                visa_page(key, name, items, i)
    if do_cover:
        cover()
    if do_back:
        back_cover()


if __name__ == '__main__':
    main()
