"""Backlit batter silhouette (generic, cover drive) under floodlights -> batter.svg (greyscale)."""
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
W, H = 1000, 1400


def g(v):
    v = max(0, min(255, int(v)))
    return f"#{v:02x}{v:02x}{v:02x}"


def limb(a, b, w):
    return (f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="#000" '
            f'stroke-width="{w}" stroke-linecap="round"/>')


s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">', f'<rect width="{W}" height="{H}" fill="#000"/>']
# floodlight wash behind the batter: concentric discs (becomes dot size after halftone)
for i in range(40, 0, -1):
    r = 60 + i * 22
    s.append(f'<circle cx="560" cy="560" r="{r}" fill="{g(250 - i * 5.6)}"/>')
# stadium bowl rings
for k, y in enumerate((1010, 1060, 1120, 1190)):
    s.append(f'<ellipse cx="500" cy="{y + 260}" rx="{760 + k * 60}" ry="{300 + k * 30}" fill="none" '
             f'stroke="{g(30 + k * 10)}" stroke-width="10"/>')
# floodlight towers
for x, top in ((120, 120), (880, 150)):
    s.append(f'<rect x="{x - 70}" y="{top}" width="140" height="80" fill="#000"/>')
    for r in range(3):
        for c in range(5):
            s.append(f'<circle cx="{x - 52 + c * 26}" cy="{top + 16 + r * 24}" r="9" fill="#fff"/>')
    s.append(f'<path d="M{x - 26} {top + 80} L{x - 60} 1400 M{x + 26} {top + 80} L{x + 60} 1400" stroke="#000" stroke-width="10"/>')
    for yy in range(top + 120, 1400, 90):
        f = (yy - top - 80) / (1400 - top - 80)
        hw = 26 + 34 * f
        s.append(f'<path d="M{x - hw} {yy} L{x + hw + 6} {yy + 90} M{x + hw} {yy} L{x - hw - 6} {yy + 90}" stroke="#000" stroke-width="6"/>')
# ground
s.append(f'<rect x="0" y="1090" width="{W}" height="310" fill="{g(26)}"/>')
s.append(f'<ellipse cx="540" cy="1100" rx="330" ry="26" fill="#000"/>')
s.append(f'<line x1="120" y1="1120" x2="900" y2="1120" stroke="{g(150)}" stroke-width="6"/>')  # crease
# batter, cover drive, facing left
B = []
B.append(limb((560, 660), (430, 840), 96))     # front thigh
B.append(limb((430, 840), (405, 1060), 74))    # front shin + pad
B.append('<path d="M350 1060 L470 1060 L470 1092 L340 1092 Z" fill="#000"/>')   # front shoe
B.append(limb((585, 680), (690, 880), 90))     # back thigh
B.append(limb((690, 880), (800, 1060), 66))    # back shin
B.append('<path d="M770 1050 L860 1074 L852 1100 L760 1084 Z" fill="#000"/>')
B.append(limb((470, 450), (570, 660), 150))    # torso, leaning over front knee
B.append(limb((470, 455), (390, 590), 56))     # front upper arm
B.append(limb((390, 590), (330, 700), 48))     # front forearm
B.append(limb((520, 470), (430, 620), 52))     # back upper arm
B.append(limb((430, 620), (338, 708), 46))     # back forearm
B.append('<circle cx="336" cy="706" r="34" fill="#000"/>')                      # gloves
B.append(limb((336, 706), (290, 800), 20))     # handle
B.append('<path d="M262 790 L322 812 L236 1040 Q226 1060 206 1052 L186 1040 Q180 1028 186 1014 Z" fill="#000"/>')  # blade
B.append('<circle cx="430" cy="372" r="58" fill="#000"/>')                     # helmet
B.append('<path d="M378 392 L322 404 L372 368 Z" fill="#000"/>')               # peak
B.append('<path d="M384 410 Q392 450 430 456 L440 424 Z" fill="#000"/>')       # grille
s += B
# the ball, off the face of the bat
s.append('<circle cx="120" cy="1010" r="20" fill="#fff"/>')
s.append('<path d="M150 1000 L230 978 M150 1014 L226 1004" stroke="#bbb" stroke-width="4"/>')
s.append("</svg>")
(HERE / "batter.svg").write_text("\n".join(s))
print("wrote batter.svg")
