"""UCIS poster v4: one blue ink on charcoal, editorial grid (IoT exhibition).

    python3 docs/poster/dc/prep_art4.py      # project photos -> blue halftone
    python3 docs/poster/dc/build_poster4.py  # needs DesignCraft on port 47815

The large left frame (id printed as CHARACTER_FRAME) is left empty for the
owner's character panel: select it in DesignCraft and File > Place the image.
"""
import json
import pathlib

from PIL import Image, ImageDraw

from dc import DC

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent
ART = HERE / "assets4"
SIM = json.loads((HERE / "sim.json").read_text())

W, H, M = 842, 1191, 34          # A3 portrait, points
BG, BLUE, PALE, DIM, PINK = "#141518", "#7096E0", "#A9BDEB", "#34405A", "#D7779A"
d = DC()


def c(cid, **p):
    return d.cmd(cid, **p)


def nb(s):
    return len(s.encode())


def lead(v):
    return {"kind": "points", "value": v}


# barcode: one bar per delivery of the simulated match, width by runs
bars = Image.new("RGB", (1200, 120), BG)
dr = ImageDraw.Draw(bars)
x = 0
for _, g in SIM["ev"]:
    w = {"W": 3, "4": 4, "6": 6}.get(g, 2 if g not in ".wd" else 1)
    dr.rectangle([x, 0, x + w - 1, 119], fill=BLUE)
    x += w + 2
bars.crop((0, 0, x, 120)).save(ART / "barcode.png")

c("file.new", intent="print", units="points", width=W, height=H, pages=1,
  facingPages=False, margins=M, bleed=9, title="UCIS Poster v4")
for n, h in {"Bg": BG, "Blue": BLUE, "Pale": PALE, "Dim": DIM, "Pink": PINK}.items():
    c("swatch.create", name=n, color=h)

PS = {
    "Mast": dict(fontFamily="Barlow Condensed", fontStyle="ExtraBold", size=262,
                 leading=lead(220), tracking=-15, fill="Blue"),
    "Name": dict(fontFamily="Archivo", fontStyle="Regular", size=33, leading=lead(33),
                 tracking=-10, fill="Blue"),
    "Spaced": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=10, leading=lead(22),
                   tracking=380, fill="Pale"),
    "Body": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=10.5, leading=lead(15),
                 fill="Pale"),
    "Word": dict(fontFamily="Barlow Condensed", fontStyle="ExtraBold", size=70,
                 leading=lead(62), tracking=-10, fill="Blue"),
    "Small": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=9, leading=lead(13),
                  tracking=120, fill="Pale"),
    "Score": dict(fontFamily="Barlow Condensed", fontStyle="SemiBold", size=40,
                  leading=lead(40), fill="Blue"),
    "Foot": dict(fontFamily="Archivo", fontStyle="Regular", size=11.5, leading=lead(16),
                 fill="Pale"),
}
for n, ch in PS.items():
    c("style.paragraph.create", name=n, chars=ch, para={"hyphenate": False})
c("style.character.create", name="Dim", chars=dict(fill="Dim"))
c("style.character.create", name="Strong", chars=dict(fill="Blue"))


def rect(x0, y0, x1, y1, fill=None, stroke=None, weight=0.8, r=0):
    f = c("frame.create", rect=[x0, y0, x1, y1], content="unassigned")["id"]
    c("object.fill", swatch=fill or "[None]", ids=[f])
    c("object.stroke", swatch=stroke or "[None]", weight=weight if stroke else 0, ids=[f])
    if r:
        c("object.cornerOptions", shape="rounded", size=r, ids=[f])
    return f


def line(x0, y0, x1, y1, sw="Blue", weight=0.8):
    f = c("line.create", a=[x0, y0], b=[x1, y1])["id"]
    c("object.stroke", swatch=sw, weight=weight, ids=[f])
    return f


def text(x0, y0, x1, paras, h=40):
    plain = "\n".join("".join(r if isinstance(r, str) else r[0] for r in runs) for _, runs in paras)
    r = c("frame.create", rect=[x0, y0, x1, y0 + h], content="text", text=plain)
    fid, story = r["id"], r["story"]
    c("object.textFrameOptions", ids=[fid], autoSize="heightOnly", autoSizeReference="topLeft",
      firstBaseline="capHeight", inset=0)
    pos = 0
    for style, runs in paras:
        pt = "".join(x if isinstance(x, str) else x[0] for x in runs)
        c("text.select", story=story, anchor=pos, focus=pos + nb(pt))
        c("style.paragraph.apply", name=style, clearOverrides=True)
        q = pos
        for run in runs:
            s, cs = (run, None) if isinstance(run, str) else run
            if cs:
                c("text.select", story=story, anchor=q, focus=q + nb(s))
                c("style.character.apply", name=cs)
            q += nb(s)
        pos += nb(pt) + 1
    return fid


def panel(x0, y0, x1, y1, img=None, r=12):
    f = rect(x0, y0, x1, y1, fill="Bg", stroke="Blue", r=r)
    if img:
        c("file.place", path=str(ART / img), frame=f)
        c("object.fit", mode="fillProportionally", ids=[f])
    return f


rect(-9, -9, W + 9, H + 9, fill="Bg")

# ---- masthead: its own band, nothing else overlaps it
text(M - 6, 40, 470, [("Mast", ["UCIS"])])
text(488, 46, 690, [("Name", ["unified"]), ("Name", ["cricket"]), ("Name", ["intelligence"]),
                    ("Name", ["system"])])
line(700, 46, 700, 196)
text(716, 52, W - M, [("Spaced", ["LIVE"]), ("Spaced", ["SIMULATE"]), ("Spaced", ["PREDICT"])])

# ---- main row
TOP, BOT = 236, 800
char = panel(M, TOP, 490, BOT)                     # owner's character panel goes here
RX = 506
panel(RX, TOP, W - M, 420, "board_close.png")
box = panel(RX, 436, W - M, BOT)
text(RX + 16, 456, W - M - 16, [("Body", ["A battery-powered box that follows live IPL matches, "
                                         "plays new ones ball by ball and works out who is "
                                         "likely to win after every delivery."])])
line(RX, 566, W - M, 566)
bc = rect(RX + 16, 584, W - M - 16, 628)
c("file.place", path=str(ART / "barcode.png"), frame=bc)
c("object.fit", mode="fitContentToFrame", ids=[bc])
line(RX, 646, W - M, 646)
text(RX + 16, 666, W - M - 16, [("Body", ["All of it runs on an Arduino UNO Q. A 2.8-inch touch "
                                         "screen shows the score, overs left and the win "
                                         "chance; any phone on its Wi-Fi gets the dashboard."])])

# ---- bottom row
B0, B1 = 818, 1040
panel(M, B0, 290, B1, "board.png")
text(306, B0 + 40, 540, [("Word", ["CRICKET"])])
rect(308, B0 + 118, 320, B0 + 130, fill="Pink")
text(330, B0 + 120, 540, [("Small", ["ON A SMALL BOARD."])])

CX0, CX1 = 556, W - M
panel(CX0, B0, CX1, B1)
text(CX0 + 14, B0 + 16, CX1 - 14, [("Small", ["MATCH SIMULATION"])])
text(CX1 - 120, B0 + 40, CX1 - 14, [("Score", ["129/10"])])
gx0, gx1, gy0, gy1 = CX0 + 14, CX1 - 14, B0 + 96, B1 - 40
wp = SIM["wp"]
pts = [{"p": [round(gx0 + (gx1 - gx0) * i / (len(wp) - 1), 2), round(gy1 - v * (gy1 - gy0), 2)]}
       for i, v in enumerate(wp)]
p = c("path.create", anchors=pts, closed=False)["id"]
c("object.stroke", swatch="Pale", weight=1, ids=[p])
c("object.fill", swatch="[None]", ids=[p])
line(gx0, gy1 + 0.5, gx1, gy1 + 0.5, sw="Dim")
t = rect(gx1 - 86, B1 - 30, gx1, B1 - 12, stroke="Blue", weight=0.6)
text(gx1 - 80, B1 - 25, gx1 - 4, [("Small", ["MATCH TIED"])])

# ---- footer
text(M, 1068, 640, [("Foot", ["Join the Wi-Fi ", ("UCIS-Cricket", "Strong"),
                              " and open ", ("10.42.0.1:8000", "Strong"), " on your phone."]),
                    ("Small", [("RV UNIVERSITY · IOT EXHIBITION 2026", "Dim")]),
                    ("Small", [("KHUSHI KRISHNA · HARSHUL KALA · MEGHNA PANT · MEDHA UMESH", "Dim")])])
c("object.qrCode", type="url", content="http://10.42.0.1:8000",
  rect=[W - M - 86, 1064, W - M, 1150], color="Blue")

info = c("document.inspect")
print("overset:", [s["id"] for s in info["stories"] if s["overset"]])
print("CHARACTER_FRAME", char)
c("file.saveAs", path=str(OUT / "UCIS_Poster_v4.designcraft"))
c("file.exportPdf", path=str(OUT / "UCIS_Poster_v4.pdf"))
