"""Original UCIS mascot ("Yuki Tamane, the scorer"), drawn as SVG.

A quiet girl in an oversized high-collar coat and big over-ear headphones,
looking down at the CYD score screen in her sleeves, an Arduino UNO Q clipped
to her coat strap, cables between them; stadium floodlights and wires behind.
Writes char.svg (greyscale tones only; colour comes later in tone.py).
"""
import math
import pathlib
import random

OUT = pathlib.Path(__file__).resolve().parent
W, H = 1000, 1400
rnd = random.Random(17)


def g(v):
    """Grey tone 0..1 as hex."""
    n = max(0, min(255, round(v * 255)))
    return f"#{n:02x}{n:02x}{n:02x}"


parts = []
add = parts.append

# ---------------------------------------------------------------- background
add(f'<rect width="{W}" height="{H}" fill="{g(0.16)}"/>')
# faint sky banding from the floodlights (drawn as soft ellipses)
for cx, cy, r, v in ((180, 170, 260, 0.30), (860, 120, 300, 0.32), (520, 60, 200, 0.24)):
    add(f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r*0.7}" fill="{g(v)}" opacity="0.55"/>')


def tower(x, top, base_w, head_w, bottom=H):
    """Lattice floodlight tower with a light head."""
    left_b, right_b = x - base_w / 2, x + base_w / 2
    left_t, right_t = x - 8, x + 8
    s = [f'<polygon points="{left_b},{bottom} {left_t},{top} {right_t},{top} {right_b},{bottom}" '
         f'fill="none" stroke="{g(0.04)}" stroke-width="5"/>']
    y = top
    k = 0
    while y < bottom:
        t0 = (y - top) / (bottom - top)
        t1 = min(1, (y + 46 - top) / (bottom - top))
        xl0, xr0 = left_t + (left_b - left_t) * t0, right_t + (right_b - right_t) * t0
        xl1, xr1 = left_t + (left_b - left_t) * t1, right_t + (right_b - right_t) * t1
        a, b = (xl0, xr1) if k % 2 else (xr0, xl1)
        s.append(f'<line x1="{a}" y1="{y}" x2="{b}" y2="{y+46}" stroke="{g(0.04)}" stroke-width="3"/>')
        s.append(f'<line x1="{xl0}" y1="{y}" x2="{xr0}" y2="{y}" stroke="{g(0.04)}" stroke-width="3"/>')
        y += 46
        k += 1
    hx, hy = x - head_w / 2, top - 78
    s.append(f'<rect x="{hx-6}" y="{hy-6}" width="{head_w+12}" height="90" fill="{g(0.04)}"/>')
    for row in range(3):
        for col in range(int(head_w // 26)):
            cx, cy = hx + 13 + col * 26, hy + 14 + row * 26
            s.append(f'<circle cx="{cx}" cy="{cy}" r="10" fill="{g(0.97)}"/>')
    return s


for x, top, bw, hw in ((120, 210, 150, 160), (900, 150, 170, 190), (640, 330, 70, 90)):
    parts += tower(x, top, bw, hw)

# overhead cables strung across
for y0, y1, sag in ((90, 260, 70), (140, 330, 90), (40, 180, 60), (300, 240, 50)):
    add(f'<path d="M -20 {y0} Q 500 {max(y0, y1) + sag} 1020 {y1}" fill="none" '
        f'stroke="{g(0.05)}" stroke-width="3"/>')

# ---------------------------------------------------------------- hair, back mass
add(f'<path d="M 330 330 C 300 520 300 700 250 830 L 760 830 C 720 700 700 520 690 330 Z" '
    f'fill="{g(0.13)}"/>')

# ---------------------------------------------------------------- coat
COAT, COAT_D, COAT_L = g(0.36), g(0.17), g(0.62)
add(f'<path d="M 120 1400 C 130 1100 150 900 230 830 C 300 780 400 760 470 745 '
    f'L 600 740 C 680 755 760 790 820 840 C 880 900 900 1100 900 1400 Z" fill="{COAT}"/>')
# folds
for d in ("M 230 860 C 250 1000 240 1200 260 1400", "M 820 860 C 800 1020 820 1220 790 1400",
          "M 470 1120 C 480 1250 470 1330 480 1400", "M 600 1120 C 590 1250 610 1340 600 1400",
          "M 330 1150 C 340 1250 330 1330 350 1400"):
    add(f'<path d="{d}" fill="none" stroke="{COAT_D}" stroke-width="10" stroke-linecap="round"/>')
add(f'<path d="M 232 836 C 300 790 400 768 470 752" fill="none" stroke="{COAT_L}" stroke-width="5"/>')
add(f'<path d="M 600 748 C 690 765 770 800 818 846" fill="none" stroke="{COAT_L}" stroke-width="5"/>')
# shoulder strap across the chest (UNO Q clips onto it)
add(f'<path d="M 300 800 L 790 1060 L 775 1090 L 285 830 Z" fill="{g(0.1)}"/>')
for t in range(0, 11):
    x = 300 + 49 * t
    y = 800 + 26 * t
    add(f'<line x1="{x}" y1="{y+6}" x2="{x-8}" y2="{y+22}" stroke="{g(0.3)}" stroke-width="2"/>')

# neck
add(f'<path d="M 455 580 L 470 720 L 585 712 L 590 560 Z" fill="{g(0.6)}"/>')
add(f'<path d="M 455 590 C 500 640 560 640 590 600 L 590 640 C 550 680 500 680 462 650 Z" '
    f'fill="{g(0.42)}"/>')

# high collar, open at the front
add(f'<path d="M 400 770 C 395 700 410 650 440 620 L 470 720 L 520 760 Z" fill="{COAT}" '
    f'stroke="{COAT_D}" stroke-width="4"/>')
add(f'<path d="M 650 770 C 660 700 640 640 610 600 L 585 712 L 530 760 Z" fill="{g(0.3)}" '
    f'stroke="{COAT_D}" stroke-width="4"/>')
add(f'<path d="M 520 760 L 520 1400" stroke="{COAT_D}" stroke-width="6"/>')
for y in range(790, 1400, 18):  # zip teeth
    add(f'<line x1="512" y1="{y}" x2="528" y2="{y}" stroke="{g(0.55)}" stroke-width="3"/>')
# UCIS patch on the collar
add(f'<rect x="590" y="690" width="44" height="26" fill="{g(0.85)}" transform="rotate(-18 612 703)"/>')
add(f'<text x="596" y="710" font-family="IBM Plex Mono" font-size="11" font-weight="600" '
    f'fill="{g(0.1)}" transform="rotate(-18 612 703)">UCIS</text>')

# ---------------------------------------------------------------- face
SKIN, SKIN_S, SKIN_D = g(0.84), g(0.62), g(0.40)
face = ("M 600 340 C 610 420 612 480 598 530 C 580 575 540 600 498 612 "
        "C 470 618 450 606 440 590 C 428 572 418 550 414 528 "
        "C 410 515 404 505 398 496 C 394 490 398 484 404 482 "
        "C 402 470 398 455 400 440 C 404 400 412 360 430 330 Z")
add(f'<path d="{face}" fill="{SKIN}"/>')
# shade on the near (right) side of the face and under the hair
add(f'<path d="M 600 340 C 610 420 612 480 598 530 C 585 560 565 580 545 592 '
    f'C 570 540 580 470 570 380 Z" fill="{SKIN_S}"/>')
add(f'<path d="M 430 330 C 480 380 560 390 600 360 L 600 340 Z" fill="{SKIN_D}"/>')
# screen glow from below: a lit band on the chin and cheek
add(f'<path d="M 430 580 C 470 606 520 606 560 590 C 520 612 470 616 440 598 Z" fill="{g(0.98)}"/>')

# eyes, looking down at the screen
def eye(cx, cy, w, tilt):
    s = []
    s.append(f'<path d="M {cx-w/2} {cy} C {cx-w/4} {cy+w*0.32} {cx+w/4} {cy+w*0.32} {cx+w/2} {cy-2} '
             f'C {cx+w/4} {cy+w*0.16} {cx-w/4} {cy+w*0.16} {cx-w/2} {cy} Z" fill="{g(0.06)}"/>')
    # thick upper lid line with a flick
    s.append(f'<path d="M {cx-w/2-4} {cy-2} C {cx-w/4} {cy+w*0.12} {cx+w/4} {cy+w*0.10} '
             f'{cx+w/2+6} {cy-8}" fill="none" stroke="{g(0.03)}" stroke-width="7" stroke-linecap="round"/>')
    s.append(f'<line x1="{cx+w/2+2}" y1="{cy-6}" x2="{cx+w/2+14}" y2="{cy-16+tilt}" '
             f'stroke="{g(0.03)}" stroke-width="4" stroke-linecap="round"/>')
    # lower lashes
    for k in (-0.3, 0, 0.3):
        x = cx + k * w
        s.append(f'<line x1="{x}" y1="{cy+w*0.27}" x2="{x-2}" y2="{cy+w*0.36}" stroke="{g(0.2)}" '
                 f'stroke-width="2"/>')
    # glint from the screen
    s.append(f'<circle cx="{cx+w*0.12}" cy="{cy+w*0.2}" r="3.2" fill="{g(1)}"/>')
    return s


parts += eye(445, 452, 38, 2)
parts += eye(530, 458, 62, 0)
# brows, faint
add(f'<path d="M 425 425 C 440 418 455 418 462 422" fill="none" stroke="{g(0.3)}" stroke-width="3"/>')
add(f'<path d="M 500 428 C 525 420 552 420 570 428" fill="none" stroke="{g(0.3)}" stroke-width="3"/>')
# nose and mouth
add(f'<path d="M 418 470 C 414 486 410 494 418 500" fill="none" stroke="{SKIN_D}" stroke-width="3"/>')
add(f'<path d="M 436 545 C 448 548 460 547 470 543" fill="none" stroke="{g(0.25)}" stroke-width="3.5" '
    f'stroke-linecap="round"/>')
add(f'<path d="M 445 556 C 452 558 458 558 463 556" fill="none" stroke="{SKIN_S}" stroke-width="2"/>')
# a small plaster on the cheek (a detail of her own)
add(f'<rect x="548" y="520" width="34" height="14" rx="4" fill="{g(0.95)}" stroke="{g(0.5)}" '
    f'stroke-width="2" transform="rotate(-24 565 527)"/>')

# ---------------------------------------------------------------- hair, front
HAIR, HAIR_L = g(0.12), g(0.5)
add(f'<path d="M 320 360 C 320 240 420 170 520 168 C 640 168 720 250 712 380 '
    f'C 708 470 720 600 760 720 C 700 690 670 610 650 520 C 640 460 630 420 616 392 '
    f'C 590 430 560 450 540 470 C 545 430 548 410 545 395 C 515 440 480 470 448 490 '
    f'C 456 455 462 430 462 410 C 440 440 412 470 380 500 C 390 460 392 430 388 410 '
    f'C 370 470 350 600 300 700 C 320 600 318 480 320 360 Z" fill="{HAIR}"/>')
# strands: light sheen lines following the fringe
for i in range(26):
    x0 = 360 + rnd.uniform(0, 330)
    y0 = 200 + rnd.uniform(0, 60)
    x1 = x0 - rnd.uniform(40, 120)
    y1 = y0 + rnd.uniform(160, 300)
    add(f'<path d="M {x0:.0f} {y0:.0f} Q {x0-20:.0f} {(y0+y1)/2:.0f} {x1:.0f} {y1:.0f}" fill="none" '
        f'stroke="{HAIR_L}" stroke-width="{rnd.uniform(1.5, 3.5):.1f}" opacity="0.8"/>')
# crown highlight ring
add(f'<path d="M 400 250 C 460 215 560 210 640 245" fill="none" stroke="{g(0.62)}" stroke-width="9" '
    f'stroke-linecap="round"/>')
# long side strands falling past the collar
for x, w_ in ((340, 26), (680, 30), (700, 18)):
    add(f'<path d="M {x} 520 C {x-10} 640 {x+12} 720 {x-4} 800" fill="none" stroke="{HAIR}" '
        f'stroke-width="{w_}" stroke-linecap="round"/>')

# ---------------------------------------------------------------- headphones
add(f'<path d="M 360 300 C 380 150 650 120 690 330" fill="none" stroke="{g(0.05)}" stroke-width="30" '
    f'stroke-linecap="round"/>')
add(f'<path d="M 368 296 C 390 165 640 140 682 320" fill="none" stroke="{g(0.55)}" stroke-width="4"/>')
add(f'<ellipse cx="664" cy="440" rx="62" ry="86" fill="{g(0.07)}"/>')
add(f'<ellipse cx="664" cy="440" rx="44" ry="66" fill="{g(0.22)}" stroke="{g(0.6)}" stroke-width="4"/>')
add(f'<circle cx="664" cy="440" r="12" fill="{g(0.95)}"/>')  # status LED
add(f'<rect x="636" y="330" width="56" height="34" rx="8" fill="{g(0.07)}"/>')
add(f'<ellipse cx="364" cy="372" rx="24" ry="62" fill="{g(0.07)}"/>')  # far cup, mostly hidden
# headphone cable down to the UNO Q
add(f'<path d="M 664 526 C 690 600 700 700 690 780 C 684 830 676 860 690 880" fill="none" '
    f'stroke="{g(0.04)}" stroke-width="7"/>')

# ---------------------------------------------------------------- UNO Q on the strap
def unoq(x, y, rot):
    s = [f'<g transform="translate({x} {y}) rotate({rot})">',
         f'<rect x="0" y="0" width="190" height="124" rx="8" fill="{g(0.42)}" stroke="{g(0.05)}" '
         f'stroke-width="4"/>']
    for i in range(18):                                     # header rows
        s.append(f'<rect x="{12+i*9.4}" y="6" width="7" height="10" fill="{g(0.06)}"/>')
        s.append(f'<rect x="{12+i*9.4}" y="108" width="7" height="10" fill="{g(0.06)}"/>')
    s.append(f'<rect x="54" y="34" width="44" height="44" fill="{g(0.08)}"/>')      # MPU
    s.append(f'<rect x="112" y="40" width="30" height="30" fill="{g(0.1)}"/>')      # MCU
    s.append(f'<rect x="22" y="38" width="22" height="30" fill="{g(0.15)}"/>')
    s.append(f'<rect x="174" y="48" width="22" height="26" rx="4" fill="{g(0.75)}"/>')  # USB-C
    for r_ in range(5):                                     # LED matrix
        for c_ in range(8):
            s.append(f'<circle cx="{60+c_*8}" cy="{88+r_*3.4}" r="1.3" fill="{g(0.95)}"/>')
    s.append(f'<text x="150" y="98" font-family="IBM Plex Mono" font-size="11" font-weight="600" '
             f'fill="{g(0.95)}">UNO Q</text>')
    s.append('</g>')
    return s


parts += unoq(622, 870, 28)

# ---------------------------------------------------------------- CYD in her sleeves
def cyd(x, y, rot):
    s = [f'<g transform="translate({x} {y}) rotate({rot})">',
         f'<rect x="0" y="0" width="330" height="218" rx="10" fill="{g(0.66)}" stroke="{g(0.05)}" '
         f'stroke-width="5"/>',
         f'<rect x="22" y="18" width="272" height="182" fill="{g(0.98)}"/>',
         f'<rect x="300" y="80" width="18" height="44" fill="{g(0.3)}"/>',
         f'<text x="78" y="56" font-family="IBM Plex Mono" font-size="15" fill="{g(0.15)}">MI v CSK · SIM</text>',
         f'<text x="76" y="138" font-family="Barlow Condensed" font-weight="800" font-size="76" '
         f'fill="{g(0.05)}">129/10</text>',
         f'<text x="78" y="176" font-family="IBM Plex Mono" font-size="15" fill="{g(0.2)}">MATCH TIED</text>',
         '</g>']
    return s


parts += cyd(338, 930, -8)
# cables UNO Q -> CYD
for k, v in enumerate((0.05, 0.85, 0.05)):
    add(f'<path d="M {640+k*8} {990+k*4} C 600 1060 560 1080 {640-k*10} 1120" fill="none" '
        f'stroke="{g(v)}" stroke-width="5"/>')
# oversized sleeves holding the board (no visible fingers, just cuffs and tips)
add(f'<path d="M 130 1400 C 150 1220 210 1080 330 1000 L 390 1120 C 330 1200 300 1300 290 1400 Z" '
    f'fill="{COAT}" stroke="{COAT_D}" stroke-width="5"/>')
add(f'<path d="M 900 1400 C 880 1250 820 1130 700 1060 L 650 1170 C 720 1220 750 1320 760 1400 Z" '
    f'fill="{g(0.3)}" stroke="{COAT_D}" stroke-width="5"/>')
add(f'<path d="M 318 1000 C 340 980 372 990 392 1018 L 404 1100 C 380 1120 352 1118 340 1100 Z" '
    f'fill="{g(0.2)}"/>')  # cuff
add(f'<path d="M 640 1062 C 660 1050 690 1056 704 1072 L 668 1172 C 650 1176 632 1168 628 1150 Z" '
    f'fill="{g(0.2)}"/>')
for fx, fy in ((398, 1030), (404, 1052), (636, 1092), (632, 1114)):
    add(f'<ellipse cx="{fx}" cy="{fy}" rx="9" ry="7" fill="{SKIN}"/>')

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
       + "\n".join(parts) + "</svg>")
(OUT / "char.svg").write_text(svg)
print("wrote", OUT / "char.svg")
