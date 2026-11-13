"""Tone the character: halftone dots coloured by brightness (violet mids, ice-cyan highs), plus grain."""
import pathlib
import random
import subprocess
from PIL import Image, ImageDraw, ImageFilter

HERE = pathlib.Path(__file__).resolve().parent
INK = (10, 9, 16)
VIOLET = (104, 72, 200)
CYAN = (150, 226, 236)


def ink_for(v):
    """Brightness 0..1 -> dot colour: violet in the mids, cyan in the highs."""
    if v < 0.55:
        return VIOLET
    t = min(1.0, (v - 0.55) / 0.3)
    return tuple(int(VIOLET[i] + (CYAN[i] - VIOLET[i]) * t) for i in range(3))


def halftone(gray, cell=7, angle=30):
    g = gray.rotate(angle, expand=True, resample=Image.BICUBIC, fillcolor=0)
    w, h = g.size
    small = g.resize((w // cell, h // cell), Image.BOX)
    out = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(out)
    px = small.load()
    for y in range(small.height):
        for x in range(small.width):
            v = px[x, y] / 255
            if v < 0.06:
                continue
            r = cell * 0.74 * v ** 0.55
            cx, cy = x * cell + cell / 2, y * cell + cell / 2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ink_for(v))
    out = out.rotate(-angle, resample=Image.BICUBIC)
    ox, oy = (w - gray.width) // 2, (h - gray.height) // 2
    return out.crop((ox, oy, ox + gray.width, oy + gray.height))


def main():
    big = HERE / "char_2x.png"
    subprocess.run(["magick", "-density", "144", str(HERE / "char.svg"), str(big)], check=True)
    src = Image.open(big).convert("L")
    # line art stays solid: keep darkest strokes as ink, halftone the rest
    curve = src.filter(ImageFilter.GaussianBlur(1.2)).point(
        lambda v: int(255 * max(0.0, (v / 255 - 0.16) / 0.84) ** 1.0))   # night stays black
    tone = halftone(curve)
    lines = src.point(lambda v: 255 if v < 22 else 0).filter(ImageFilter.MaxFilter(3))
    tone.paste(Image.new("RGB", tone.size, INK), mask=lines)
    rnd = random.Random(3)
    p = tone.load()
    for _ in range(tone.width * tone.height // 14):   # print grain
        x, y = rnd.randrange(tone.width), rnd.randrange(tone.height)
        r, g_, b = p[x, y]
        k = rnd.choice((-28, 22))
        p[x, y] = (max(0, min(255, r + k)), max(0, min(255, g_ + k)), max(0, min(255, b + k)))
    tone.save(HERE / "character_toned.png")
    big.unlink()
    print(tone.size)


main()
