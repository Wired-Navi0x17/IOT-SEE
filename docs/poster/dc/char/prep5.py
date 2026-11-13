"""Board panels for poster v5 in the character's palette (run after draw_character.py)."""
import importlib.util
import pathlib
import subprocess
from PIL import Image, ImageFilter, ImageOps

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location("tone_mod", HERE / "tone.py")
src = (HERE / "tone.py").read_text().replace("\n\nmain()\n", "\n")
ns = {"__file__": str(HERE / "tone.py")}
exec(compile(src, "tone.py", "exec"), ns)
halftone = ns["halftone"]


def cyd_photo():
    im = Image.open(ROOT / "docs/img/cyd_board.jpg").convert("RGB").crop((150, 100, 1050, 680))
    im = ImageOps.fit(im, (1200, 780), Image.LANCZOS)
    g = ImageOps.grayscale(im).filter(ImageFilter.UnsharpMask(radius=30, percent=220, threshold=0))
    g = ImageOps.autocontrast(g, cutoff=2).point(lambda v: int(255 * (v / 255) ** 1.5))
    halftone(g, cell=6).save(HERE / "cyd_toned.png")


def unoq_drawing():
    """A flat drawing of the UNO Q (no photo of the board in the repo)."""
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="780">',
         '<rect width="1200" height="780" fill="#000"/>',
         '<g transform="translate(140 150) rotate(-6 460 240)">',
         '<rect width="920" height="500" rx="26" fill="#6a6a6a" stroke="#111" stroke-width="10"/>']
    for i in range(30):
        s.append(f'<rect x="{60 + i * 27}" y="22" width="18" height="34" fill="#111"/>')
        s.append(f'<rect x="{60 + i * 27}" y="444" width="18" height="34" fill="#111"/>')
    s += ['<rect x="250" y="150" width="210" height="210" fill="#141414"/>',
          '<rect x="275" y="175" width="160" height="160" fill="#2a2a2a"/>',
          '<rect x="520" y="180" width="130" height="130" fill="#1c1c1c"/>',
          '<rect x="90" y="170" width="110" height="150" fill="#3a3a3a"/>',
          '<rect x="860" y="200" width="90" height="110" rx="14" fill="#e6e6e6"/>']
    for r in range(8):
        for c in range(13):
            s.append(f'<circle cx="{700 + c * 11}" cy="{170 + r * 11}" r="4" fill="#f2f2f2"/>')
    s += ['<text x="690" y="370" font-family="Barlow Condensed" font-weight="800" font-size="78" '
          'fill="#f2f2f2">UNO Q</text>',
          '<text x="250" y="410" font-family="IBM Plex Mono" font-size="26" fill="#d0d0d0">'
          'QRB2210 · STM32U585</text>', '</g></svg>']
    (HERE / "unoq.svg").write_text("".join(s))
    subprocess.run(["magick", "-density", "72", str(HERE / "unoq.svg"), str(HERE / "unoq_raw.png")],
                   check=True)
    g = Image.open(HERE / "unoq_raw.png").convert("L").filter(ImageFilter.GaussianBlur(1))
    halftone(g, cell=6).save(HERE / "unoq_toned.png")
    (HERE / "unoq_raw.png").unlink()


cyd_photo()
unoq_drawing()
