"""Blue one-ink halftone art for poster v4 (matches the supplied character panel)."""
import pathlib
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageEnhance

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent / "assets4"
INK, BLUE = (14, 13, 13), (112, 150, 224)


def screen(gray, cell=5, angle=45):
    """Classic dot screen: each cell gets a blue dot sized by its brightness."""
    g = gray.rotate(angle, expand=True, resample=Image.BICUBIC, fillcolor=0)
    w, h = g.size
    small = g.resize((w // cell, h // cell), Image.BOX)
    out = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(out)
    px = small.load()
    for y in range(small.height):
        for x in range(small.width):
            v = px[x, y] / 255
            if v < 0.04:
                continue
            r = cell * 0.72 * v ** 0.6
            cx, cy = x * cell + cell / 2, y * cell + cell / 2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLUE)
    out = out.rotate(-angle, resample=Image.BICUBIC)
    ox, oy = (w - gray.width) // 2, (h - gray.height) // 2
    return out.crop((ox, oy, ox + gray.width, oy + gray.height))


def prep(src, name, crop=None, size=None, invert=False, contrast=1.6, gamma=1.0, cell=5):
    im = Image.open(ROOT / src).convert("RGB")
    if crop:
        im = im.crop(crop)
    if size:
        im = ImageOps.fit(im, size, Image.LANCZOS)
    g = ImageOps.grayscale(im)
    if invert:
        g = ImageOps.invert(g)
    g = ImageOps.autocontrast(g, cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(contrast)
    if gamma != 1:
        g = g.point(lambda v: int(255 * (v / 255) ** gamma))
    screen(g, cell=cell).save(OUT / f"{name}.png")




def local(src, name, crop=None, size=None, cell=5, gamma=1.6):
    """Halftone with strong local contrast, for flat product shots."""
    im = Image.open(ROOT / src).convert("RGB")
    if crop:
        im = im.crop(crop)
    if size:
        im = ImageOps.fit(im, size, Image.LANCZOS)
    g = ImageOps.grayscale(im).filter(ImageFilter.UnsharpMask(radius=40, percent=300, threshold=0))
    g = ImageOps.autocontrast(g, cutoff=2).point(lambda v: int(255 * (v / 255) ** gamma))
    screen(g, cell=cell).save(OUT / f"{name}.png")


local("docs/img/cyd_board.jpg", "board_close", crop=(200, 150, 800, 600), size=(1000, 800))
local("docs/img/cyd_board.jpg", "board", crop=(560, 330, 1000, 640), size=(900, 800))
