"""Turn project photos into the poster's blue duotone / halftone art."""
import json
import pathlib
import random

from PIL import Image, ImageDraw, ImageFilter, ImageOps

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "assets"
OUT.mkdir(exist_ok=True)

DARK = (6, 8, 13)
BLUE = (47, 79, 196)
ICE = (190, 236, 250)
VIOLET = (122, 91, 214)
CYAN = (127, 200, 234)


def ramp(stops):
    lut = []
    for i in range(256):
        t = i / 255
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= t <= p1:
                u = (t - p0) / (p1 - p0)
                lut.append(tuple(round(a + (b - a) * u) for a, b in zip(c0, c1)))
                break
    return lut


def duotone(im, stops=((0, DARK), (0.55, BLUE), (1, ICE)), contrast=2.0):
    g = ImageOps.autocontrast(im.convert("L"), cutoff=contrast)
    lut = ramp(stops)
    r = g.point([c[0] for c in lut]); gg = g.point([c[1] for c in lut]); b = g.point([c[2] for c in lut])
    return Image.merge("RGB", (r, gg, b))


def grain(im, amount=22, seed=1):
    rnd = random.Random(seed)
    px = im.load()
    w, h = im.size
    for _ in range(w * h // 3):
        x, y = rnd.randrange(w), rnd.randrange(h)
        d = rnd.randint(-amount, amount)
        r, g, b = px[x, y]
        px[x, y] = (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)))
    return im


def yellow_key(im):
    """Board is yellow on teal: R+G-B lifts the board and sinks the background."""
    r, g, b = im.split()
    from PIL import ImageChops
    k = ImageChops.subtract(ImageChops.add(r, g, scale=2), b, scale=1, offset=0)
    return ImageOps.autocontrast(k, cutoff=1)


def halftone(im, cell=9, top=CYAN, bottom=VIOLET, gray=None):
    g = gray if gray is not None else ImageOps.autocontrast(im.convert("L"), cutoff=2)
    w, h = g.size
    small = g.resize((w // cell, h // cell), Image.LANCZOS)
    out = Image.new("RGB", (w, h), DARK)
    dr = ImageDraw.Draw(out)
    sw, sh = small.size
    for j in range(sh):
        t = j / max(1, sh - 1)
        col = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        for i in range(sw):
            v = small.getpixel((i, j)) / 255
            r = (v ** 0.8) * cell * 0.72
            if r < 0.6:
                continue
            cx, cy = i * cell + cell / 2, j * cell + cell / 2
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return out


def save(im, name):
    im.save(OUT / name, quality=92)
    print(name, im.size)


# hero: CYD board, rotated to portrait, halftone cyan->violet
cyd = Image.open(ROOT / "docs/img/cyd_board.jpg").convert("RGB").rotate(90, expand=True)
cyd = cyd.resize((cyd.width * 2, cyd.height * 2), Image.LANCZOS)
save(halftone(cyd, cell=10, gray=yellow_key(cyd)), "hero_cyd.png")

# panels: duotone + grain
panels = {
    "uq_headers": ("docs/img/uq_headers.png", None),
    "device": ("paper/figs/device.png", (0, 0, 1440, 900)),
}
for name, (src, crop) in panels.items():
    im = Image.open(ROOT / src).convert("RGB")
    if crop:
        im = im.crop(crop)
    if name == "uq_headers":
        im = ImageOps.invert(im)  # white diagram -> dark ground, like the other panels
    save(grain(duotone(im)), f"{name}.png")

# grain overlay for the whole page (white specks, mostly transparent)
W, H = 1080, 1920
rnd = random.Random(7)
gr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
p = gr.load()
for _ in range(W * H // 9):
    x, y = rnd.randrange(W), rnd.randrange(H)
    p[x, y] = (210, 235, 250, rnd.randint(10, 45))
for y in range(0, H, 3):  # faint scanlines, as on the Lain poster
    for x in range(W):
        if p[x, y][3] == 0:
            p[x, y] = (0, 0, 0, 38)
save(gr, "grain.png")

# barcode from the real match: one bar per delivery, width by runs
sim = json.loads((HERE / "sim.json").read_text())
bars, x = [], 0
wid = {".": 1, "1": 2, "2": 3, "3": 3, "4": 4, "6": 6, "W": 7, "wd": 1, "nb": 1}
for _, g in sim["ev"]:
    w = wid.get(g, 2)
    bars.append((x, w, g))
    x += w + 2
bc = Image.new("RGBA", (x, 120), (0, 0, 0, 0))
d = ImageDraw.Draw(bc)
for bx, w, g in bars:
    d.rectangle([bx, 0, bx + w - 1, 119], fill=(255, 255, 255, 255) if g != "W" else (127, 200, 234, 255))
save(bc, "barcode.png")
