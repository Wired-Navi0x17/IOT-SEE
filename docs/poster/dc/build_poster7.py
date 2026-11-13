"""UCIS poster v7: faceless batter silhouette, mint/blue/violet halftone on black.

Art: python3 char/draw_batter.py && python3 char/prep6.py ; then run this with DesignCraft open.
"""
import json
import pathlib

from dc import DC

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent
ART = HERE / "char"
W, H = 842, 1191
M = 30
d = DC()


def c(cid, **p):
    return d.cmd(cid, **p)


def nb(s):
    return len(s.encode())


def lead(v):
    return {"kind": "points", "value": v}


c("font.reload")
c("file.new", intent="print", units="points", width=W, height=H, pages=1,
  facingPages=False, margins=0, title="UCIS Poster v7")
for name, hexc in {"Night": "#06070C", "Mint": "#96E6DA", "Blue": "#4C7CF0", "Violet": "#7C52E0",
                   "Ice": "#E8F6F2", "Mute": "#8A8FA8"}.items():
    c("swatch.create", name=name, color=hexc)

PS = {
    "Title": dict(fontFamily="Barlow Condensed", fontStyle="ExtraBold", size=250, leading=lead(205),
                  fill="Blue", tracking=-10),
    "Name": dict(fontFamily="Barlow Condensed", fontStyle="Bold", size=36, leading=lead(34), fill="Ice"),
    "List": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=13, leading=lead(26), fill="Ice",
                 tracking=120),
    "Lead": dict(fontFamily="Archivo", fontStyle="Regular", size=12.5, leading=lead(16.5), fill="Ice"),
    "H": dict(fontFamily="Barlow Condensed", fontStyle="ExtraBold", size=23, leading=lead(25), fill="Mint"),
    "Body": dict(fontFamily="Archivo", fontStyle="Regular", size=9.6, leading=lead(13), fill="Ice"),
    "Cap": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=9, leading=lead(13), fill="Mute",
                tracking=80),
    "Big": dict(fontFamily="Barlow Condensed", fontStyle="ExtraBold", size=46, leading=lead(44), fill="Ice"),
    "Big2": dict(fontFamily="Barlow Condensed", fontStyle="ExtraBold", size=32, leading=lead(32), fill="Ice"),
    "Box": dict(fontFamily="IBM Plex Mono", fontStyle="SemiBold", size=10, leading=lead(13), fill="Mint",
                tracking=100),
    "Stat": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=9.5, leading=lead(16), fill="Ice"),
}
for name, chars in PS.items():
    c("style.paragraph.create", name=name, chars=chars, para={"hyphenate": False})
c("style.character.create", name="M", chars=dict(fill="Mint"))
c("style.character.create", name="V", chars=dict(fill="Violet"))


def rect(x0, y0, x1, y1, fill=None, stroke=None, weight=0.9, radius=0):
    r = c("frame.create", rect=[x0, y0, x1, y1], content="unassigned")
    c("object.fill", swatch=fill or "[None]", ids=[r["id"]])
    c("object.stroke", swatch=stroke or "[None]", weight=weight if stroke else 0, ids=[r["id"]])
    if radius:
        c("object.cornerOptions", shape="rounded", size=radius, ids=[r["id"]])
    return r["id"]


def line(x0, y0, x1, y1, sw="Blue", weight=0.9):
    r = c("line.create", a=[x0, y0], b=[x1, y1])
    c("object.stroke", swatch=sw, weight=weight, ids=[r["id"]])


def text(x0, y0, x1, paras, h=30):
    plain = "\n".join("".join(r if isinstance(r, str) else r[0] for r in runs) for _, runs in paras)
    r = c("frame.create", rect=[x0, y0, x1, y0 + h], content="text", text=plain)
    fid, story = r["id"], r["story"]
    c("object.textFrameOptions", ids=[fid], autoSize="heightOnly", autoSizeReference="topLeft",
      firstBaseline="capHeight", inset=0)
    pos = 0
    for style, runs in paras:
        ptxt = "".join(x if isinstance(x, str) else x[0] for x in runs)
        c("text.select", story=story, anchor=pos, focus=pos + nb(ptxt))
        c("style.paragraph.apply", name=style, clearOverrides=True)
        q = pos
        for run in runs:
            s, cs = (run, None) if isinstance(run, str) else run
            if cs:
                c("text.select", story=story, anchor=q, focus=q + nb(s))
                c("style.character.apply", name=cs)
            q += nb(s)
        pos += nb(ptxt) + 1
    return fid


def image(path, x0, y0, x1, y1, stroke="Blue", radius=8):
    fid = rect(x0, y0, x1, y1, stroke=stroke, radius=radius)
    c("file.place", path=str(path), frame=fid)
    c("object.fit", mode="fillProportionally", ids=[fid])
    return fid


rect(0, 0, W, H, fill="Night")

# ---- batter: big, bleeding off the left edge, behind the title
image(ART / "batter_toned.png", 0, 190, 480, 860, stroke=None, radius=0)

# ---- title block
text(M - 6, 26, 480, [("Title", ["UCIS"])])
text(494, 34, 690, [("Name", ["UNIFIED"]), ("Name", ["CRICKET"]), ("Name", ["INTELLIGENCE"]),
                    ("Name", ["SYSTEM"])])
line(700, 30, 700, 200)
text(714, 36, W - M, [("List", ["LIVE"]), ("List", ["SIMULATE"]), ("List", ["PREDICT"])])
for y in (62, 88):
    line(714, y, W - M, y, sw="Mute", weight=0.5)

# ---- right column
RX, RX1 = 494, W - M
half = (RX1 - RX - 10) / 2
image(ART / "cyd6.png", RX, 222, RX + half, 352)
image(ART / "unoq6.png", RX + half + 10, 222, RX1, 352)
text(RX + 2, 358, RX + half + 4, [("Cap", ["CYD · ESP32 TOUCH"])])
text(RX + half + 18, 358, RX1, [("Cap", ["ARDUINO UNO Q · THE HUB"])])
text(RX, 392, RX1, [("Lead", ["A battery-powered IoT box that follows live IPL scores, plays matches "
                              "ball by ball and predicts the winner after every delivery. All of it "
                              "runs on one ", ("Arduino UNO Q", "M"), "."])])
line(RX, 466, RX1, 466)
cw = (RX1 - RX - 20) / 3
cols = [("LIVE", "IPL scores from CricketData.org, two calls under the free 100 a day."),
        ("SIMULATE", "Pick two IPL teams; the board bowls every ball itself."),
        ("PREDICT", "Win chance after each ball, held between 3% and 97%.")]
for i, (h, b) in enumerate(cols):
    x = RX + i * (cw + 10)
    text(x, 480, x + cw, [("H", [h]), ("Body", [b])])
    if i:
        line(x - 5, 480, x - 5, 560, sw="Mute", weight=0.5)

# win-chance chart from the simulated match
sim = json.loads((HERE / "sim.json").read_text())
wp = sim["wp"]
GY0, GY1 = 580, 712
rect(RX, GY0, RX1, GY1, stroke="Blue", radius=8)
text(RX + 12, GY0 + 10, RX1 - 12, [("Box", ["MI WIN CHANCE · BALL BY BALL"])])
px0, px1, py0, py1 = RX + 12, RX1 - 112, GY0 + 34, GY1 - 14
anchors = [{"p": [px0 + (px1 - px0) * i / (len(wp) - 1), py1 - (py1 - py0) * v]} for i, v in enumerate(wp)]
pth = c("path.create", anchors=anchors, closed=False)
c("object.stroke", swatch="Mint", weight=1.2, ids=[pth["id"]])
c("object.fill", swatch="[None]", ids=[pth["id"]])
line(px0, (py0 + py1) / 2, px1, (py0 + py1) / 2, sw="Violet", weight=0.5)
text(RX1 - 104, GY0 + 34, RX1 - 6, [("Big2", ["129/10"])])
rect(RX1 - 102, GY0 + 80, RX1 - 12, GY0 + 100, stroke="Ice", weight=0.7)
text(RX1 - 94, GY0 + 86, RX1 - 14, [("Box", ["MATCH TIED"])])

# architecture
AY0, AY1 = 726, 860
rect(RX, AY0, RX1, AY1, stroke="Blue", radius=8)
text(RX + 12, AY0 + 10, RX1, [("Box", ["HOW IT CONNECTS"])])
nodes = [("API", "live scores"), ("UNO Q", "hub + sim"),
         ("CYD", "UART link"), ("Phone", "Wi-Fi")]
nw = (RX1 - RX - 24 - 3 * 14) / 4
for i, (a, b) in enumerate(nodes):
    x = RX + 12 + i * (nw + 14)
    rect(x, AY0 + 40, x + nw, AY0 + 92, stroke="Mint", weight=0.7, radius=4)
    text(x + 6, AY0 + 50, x + nw - 4, [("Body", [(a, "M")]), ("Cap", [b])])
    if i:
        line(x - 12, AY0 + 66, x - 2, AY0 + 66, sw="Ice", weight=1)
text(RX + 12, AY0 + 104, RX1 - 12, [("Cap", ["NO PC AT RUNTIME. THE BOARD IS THE HUB AND THE HOTSPOT."])])

# ---- bottom row
BY0, BY1 = 880, 1080
rect(M, BY0, 470, BY1, stroke="Blue", radius=8)
text(M + 12, BY0 + 10, 470, [("Box", ["THE SIMULATED MATCH"])])
sw = (470 - M - 24) / 3
for i, (n, l) in enumerate((("240", "BALLS BOWLED"), ("129", "RUNS EACH SIDE"), ("3–97%", "WIN CHANCE RANGE"))):
    x = M + 12 + i * sw
    text(x, BY0 + 40, x + sw - 8, [("Big", [n]), ("Cap", [l])])
    if i:
        line(x - 6, BY0 + 40, x - 6, BY0 + 100, sw="Mute", weight=0.5)
bc = rect(M + 12, BY0 + 122, 458, BY0 + 160)
c("file.place", path=str(HERE / "assets4" / "barcode.png"), frame=bc)
c("object.fit", mode="fitContentToFrame", ids=[bc])
text(M + 12, BY0 + 166, 458, [("Cap", ["ONE BAR PER BALL · MI v CSK · SEED 25"])])

rect(RX - 12, BY0, RX1, BY1, stroke="Blue", radius=8)
text(RX, BY0 + 10, RX1, [("Box", ["STATUS"])])
text(RX, BY0 + 32, RX1 - 100, [
    ("Stat", [("+ ", "M"), "Scoring engine — working"]),
    ("Stat", [("+ ", "M"), "Match simulation — working"]),
    ("Stat", [("+ ", "M"), "Win chance — working"]),
    ("Stat", [("+ ", "M"), "Live feed (API) — working"]),
    ("Stat", [("– ", "V"), "Wireless CYD link — planned"]),
    ("Stat", [("– ", "V"), "Android app — planned"]),
])
c("object.qrCode", type="url", content="http://10.42.0.1:8000",
  rect=[RX1 - 92, BY0 + 34, RX1 - 10, BY0 + 116], color="Mint")
text(RX1 - 94, BY0 + 124, RX1 - 2, [("Cap", ["SCAN FOR"]), ("Cap", ["DASHBOARD"])])

# ---- footer strip
FY = 1100
for i in range(9):
    x = M + i * 14
    p = c("path.create", anchors=[{"p": [x, FY + 30]}, {"p": [x + 14, FY]}, {"p": [x + 22, FY]},
                                   {"p": [x + 8, FY + 30]}], closed=True)
    c("object.fill", swatch="Blue", ids=[p["id"]])
    c("object.stroke", swatch="[None]", weight=0, ids=[p["id"]])
text(M + 150, FY + 10, 600, [("List", ["AN IoT CRICKET ANALYTICS BOX"])])
line(580, FY, 580, FY + 32, sw="Mute", weight=0.6)
text(594, FY + 10, W - M, [("List", ["RV UNIVERSITY / 2026"])])
text(M, FY + 48, W - M, [("Cap", ["KHUSHI KRISHNA · HARSHUL KALA · MEGHNA PANT · MEDHA UMESH · "
                                  "github.com/Wired-Navi0x17/IOT-SEE"])])

info = c("document.inspect")
print("overset:", [(s["id"], s["preview"][:30]) for s in info["stories"] if s["overset"]])
c("file.saveAs", path=str(OUT / "UCIS_Poster_v7.designcraft"))
c("file.exportPdf", path=str(OUT / "UCIS_Poster_v7.pdf"))
