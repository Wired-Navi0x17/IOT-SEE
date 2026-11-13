"""Poster v6 art: stepped mint / blue / violet halftone on black (no gradient fills)."""
import pathlib
import subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageOps

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
INK = (6, 7, 12)
STEPS = ((0.30, (108, 64, 204)),   # violet: shadows
         (0.62, (76, 124, 240)),   # royal blue: mids
         (0.86, (150, 230, 218)),  # mint: highs
         (1.01, (232, 246, 242)))  # near white: hot spots


def ink_for(v):
    for edge, col in STEPS:
        if v < edge:
            return col
    return STEPS[-1][1]


def halftone(gray, cell=7, angle=30):
    gr = gray.rotate(angle, expand=True, resample=Image.BICUBIC, fillcolor=0)
    w, h = gr.size
    small = gr.resize((w // cell, h // cell), Image.BOX)
    out = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(out)
    px = small.load()
    for y in range(small.height):
        for x in range(small.width):
            v = px[x, y] / 255
            if v < 0.07:
                continue
            r = cell * 0.74 * v ** 0.55
            cx, cy = x * cell + cell / 2, y * cell + cell / 2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ink_for(v))
    out = out.rotate(-angle, resample=Image.BICUBIC)
    ox, oy = (w - gray.width) // 2, (h - gray.height) // 2
    return out.crop((ox, oy, ox + gray.width, oy + gray.height))


def batter():
    big = HERE / "batter_2x.png"
    subprocess.run(["magick", "-density", "108", str(HERE / "batter.svg"), str(big)], check=True)
    src = Image.open(big).convert("L")
    tone = halftone(src.filter(ImageFilter.GaussianBlur(1.0)), cell=8)
    solid = src.point(lambda v: 255 if v < 12 else 0)
    tone.paste(Image.new("RGB", tone.size, INK), mask=solid)   # the silhouette stays solid black
    tone.save(HERE / "batter_toned.png")
    big.unlink()


def cyd():
    im = Image.open(ROOT / "docs/img/cyd_board.jpg").convert("RGB").crop((150, 100, 1050, 680))
    im = ImageOps.fit(im, (1200, 780), Image.LANCZOS)
    g = ImageOps.grayscale(im).filter(ImageFilter.UnsharpMask(radius=30, percent=220, threshold=0))
    g = ImageOps.autocontrast(g, cutoff=2).point(lambda v: int(255 * (v / 255) ** 1.5))
    halftone(g, cell=6).save(HERE / "cyd6.png")


def unoq():
    subprocess.run(["python3", str(HERE / "prep5.py")], check=True)   # rebuilds unoq.svg
    subprocess.run(["magick", "-density", "72", str(HERE / "unoq.svg"), str(HERE / "u.png")], check=True)
    g = Image.open(HERE / "u.png").convert("L").filter(ImageFilter.GaussianBlur(1))
    halftone(g, cell=6).save(HERE / "unoq6.png")
    (HERE / "u.png").unlink()


batter()
cyd()
unoq()
