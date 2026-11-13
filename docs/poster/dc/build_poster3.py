"""UCIS poster v3: dark duotone / halftone style (after the reference posters).

Needs DesignCraft running with its control port (see README.md) and the
art from prep_art.py in ./assets:
    python3 docs/poster/dc/prep_art.py
    python3 docs/poster/dc/build_poster3.py
Data comes from sim.json (one match simulated by the hub, seed 25).
"""
import json
import pathlib

from dc import DC

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent
ART = HERE / "assets"
SIM = json.loads((HERE / "sim.json").read_text())

W, H = 1080, 1920
B = 28            # black outer frame, as in the Lain poster
M = 64            # text margin
d = DC()


def c(cid, **p):
    return d.cmd(cid, **p)


def nb(s):
    return len(s.encode())


c("file.new", intent="print", units="points", width=W, height=H, pages=1,
  facingPages=False, margins=0, title="UCIS Poster v3")

SW = {"Frame": "#000000", "Night": "#070A12", "Ice": "#DCEFFA", "Cyan": "#7FC8EA",
      "Blue": "#4F7FE6", "Violet": "#7A5BD6", "Dim": "#56688A", "Deep": "#1A2440"}
for name, hexc in SW.items():
    c("swatch.create", name=name, color=hexc)


def lead(v):
    return {"kind": "points", "value": v}


PS = {
    "Title": dict(fontFamily="Archivo", fontStyle="Medium", size=94, leading=lead(84),
                  tracking=-30, fill="Ice"),
    "Sub": dict(fontFamily="Archivo", fontStyle="Regular", size=22, leading=lead(28), fill="Ice"),
    "Body": dict(fontFamily="Archivo", fontStyle="Regular", size=15.5, leading=lead(21), fill="Ice"),
    "Meta": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=11.5, leading=lead(15),
                 fill="Cyan", tracking=40),
    "Call": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=13, leading=lead(17), fill="Ice"),
    "Layer": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=12, leading=lead(16.5), fill="Ice"),
    "Vert": dict(fontFamily="Barlow Condensed", fontStyle="Bold", size=44, leading=lead(46),
                 fill="Ice", tracking=-10),
    "H3": dict(fontFamily="Archivo", fontStyle="Medium", size=29, leading=lead(30), fill="Ice",
               tracking=-20),
    "Col": dict(fontFamily="Archivo", fontStyle="Regular", size=14.5, leading=lead(19.5), fill="Ice"),
    "Box": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=12.5, leading=lead(16.5),
                fill="Ice"),
    "Echo": dict(fontFamily="Archivo", fontStyle="Bold", size=24, leading=lead(26), fill="Cyan"),
    "Big": dict(fontFamily="Archivo", fontStyle="Bold", size=58, leading=lead(56), fill="Ice",
                tracking=-20),
}
PARA = {"Body": {"spaceAfter": 9, "hyphenate": False}, "Sub": {"hyphenate": False},
        "Col": {"hyphenate": False}, "Box": {"hyphenate": False}, "Meta": {"hyphenate": False}, "H3": {"spaceBefore": 8, "spaceAfter": 10},
        "Echo": {"align": "right"}}
for name, chars in PS.items():
    c("style.paragraph.create", name=name, chars=chars, para=PARA.get(name, {}))
CS = {"B": dict(fontStyle="SemiBold"), "C": dict(fill="Cyan"), "D": dict(fill="Dim"),
      "V": dict(fill="Violet"), "Deep": dict(fill="Deep"), "Blue": dict(fill="Blue"),
      "Sup": dict(size=9.5, baselineShift=5.5)}
for name, chars in CS.items():
    c("style.character.create", name=name, chars=chars)


# ------------------------------------------------------------------ helpers
def rect(x0, y0, x1, y1, fill=None, stroke=None, weight=1):
    r = c("frame.create", rect=[x0, y0, x1, y1], content="unassigned")
    c("object.fill", swatch=fill or "[None]", ids=[r["id"]])
    c("object.stroke", swatch=stroke or "[None]", weight=weight if stroke else 0, ids=[r["id"]])
    return r["id"]


def line(x0, y0, x1, y1, sw="Ice", weight=0.75):
    r = c("line.create", a=[x0, y0], b=[x1, y1])
    c("object.stroke", swatch=sw, weight=weight, ids=[r["id"]])
    return r["id"]


def node(x, y, s=7, fill="Ice"):
    """Small square node where hairlines meet (Lain poster)."""
    return rect(x - s / 2, y - s / 2, x + s / 2, y + s / 2, fill=fill)


def text(x0, y0, x1, paras, h=40):
    plain = "\n".join("".join(r if isinstance(r, str) else r[0] for r in runs)
                      for _, runs in paras)
    r = c("frame.create", rect=[x0, y0, x1, y0 + h], content="text", text=plain)
    fid, story = r["id"], r["story"]
    c("object.textFrameOptions", ids=[fid], autoSize="heightOnly",
      autoSizeReference="topLeft", firstBaseline="capHeight", inset=0)
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


def vtext(cx, cy, length, paras, angle=90, h=80):
    """Text rotated a quarter turn about (cx, cy); `length` runs along the page."""
    fid = text(cx - length / 2, cy - h / 2, cx + length / 2, paras, h=h)
    c("object.textFrameOptions", ids=[fid], autoSize="off")
    c("transform.rotate", angle=angle, ids=[fid])
    return fid


def image(path, x0, y0, x1, y1, mode="fillProportionally", stroke="Ice", weight=0.75):
    fid = rect(x0, y0, x1, y1, stroke=stroke, weight=weight)
    c("file.place", path=str(path), frame=fid)
    c("object.fit", mode=mode, ids=[fid])
    return fid


# ------------------------------------------------------------------ ground
rect(0, 0, W, H, fill="Frame")
rect(B, B, W - B, H - B, fill="Night")

# hero: the CYD board, keyed and half-toned cyan to violet (Lucy poster)
HX0, HY0, HX1 = 586, 34, 1036
hero_w = HX1 - HX0
hero_h = hero_w * 2400 / 1558
image(ART / "hero_cyd.png", HX0, HY0, HX1, HY0 + hero_h, mode="fitProportionally",
      stroke=None)


def HP(fx, fy):
    """A point on the board, as fractions of the hero image."""
    return HX0 + fx * hero_w, HY0 + fy * hero_h


# top metadata, tiny mono like "1998 · TV SERIES · 13 EPISODES"
text(M + 52, 56, 520, [("Meta", ["2026 · IPL · T20 · RV UNIVERSITY IOT PROJECT"]),
                       ("Meta", [("ARDUINO UNO Q / ESP32 / BATTERY POWERED", "D")])])

# vertical English down the left edge (the Lain poster's vertical column)
vtext(84, 330, 580, [("Vert", ["LIVE · SIMULATE · PREDICT"])], angle=-90, h=52)

# hairline callouts into the board, square nodes at both ends
CALL = [
    (150, ["ESP32-WROOM-32", ("the Cheap Yellow Display", "D")], HP(0.263, 0.281)),
    (262, ["2.8in ILI9341 · 320×240", ("XPT2046 touch", "D")], HP(0.513, 0.433)),
    (374, ["tap  → live / simulation", ("hold → QR to the dashboard", "D")], HP(0.413, 0.606)),
    (486, ["P3 UART  IO35 ← D1", ("IO22 → D0 · GND", "D")], HP(0.293, 0.779)),
]
for y, lines_, (bx, by) in CALL:
    text(M + 80, y, 420, [("Call", [r]) for r in lines_])
    line(420, y + 6, bx, y + 6)
    line(bx, y + 6, bx, by)
    node(420, y + 6)
    node(bx, by, s=9, fill="Cyan")

# title, overlapping the bottom of the hero like the Lain title
text(M, 628, 1000, [("Title", ["unified cricket"]), ("Title", ["intelligence system"])])
text(M, 806, W - M - 40, [("Sub", [
    "A battery-powered box that follows live IPL matches, plays new ones ball by ball "
    "and shows who is likely to win after every delivery. All of it runs on one "
    "Arduino UNO Q: a 2.8-inch touch screen shows the match at the table, and any "
    "phone on its Wi-Fi gets the full dashboard."])])

# ------------------------------------------------------------------ what it does
CY = 948
COLS = [
    ("LIVE · SCREEN 1", "the real match", [[
        "The hub asks CricketData.org for the score every 150 s while a match is on "
        "and every 15 min otherwise, and stops two calls short of the free plan's 100 "
        "a day. With no IPL game on, Screen 1 shows the next fixture."]]),
    ("SIMULATE · SCREEN 2", "a match nobody played", [[
        "Pick two IPL franchises and the board bowls every delivery itself: dot 33.5%, "
        "four 11%, six 5.2%, wicket 5%, shifted by batter v bowler rating, the powerplay "
        "and the death overs. Each ball goes through the same scoring engine as a "
        "hand-scored one."]]),
    ("PREDICT · EVERY BALL", "who wins from here", [[
        "Runs still in reach with n balls and w wickets left: E = Z(1 − e",
        ("−1.6n/Z", "Sup"), "), where Z = 20·w", ("1.48", "Sup"),
        ". A logistic turns E against the runs needed into a win chance, held between "
        "3% and 97%. The display (C++) and the hub (Python) run the same maths."]]),
]
cw = (W - 2 * M - 2 * 32) / 3
for k, (meta, head_, paras) in enumerate(COLS):
    x0 = M + k * (cw + 32)
    line(x0, CY, x0 + cw, CY)
    node(x0, CY)
    text(x0, CY + 14, x0 + cw, [("Meta", [meta]), ("H3", [head_])] +
         [("Col", runs) for runs in paras])

# ------------------------------------------------------------------ the match
PY0, PY1 = 1222, 1500
rect(M, PY0, W - M, PY1, stroke="Ice", weight=0.75)
text(M + 18, PY0 + 16, 760, [("Meta", ["ONE SIMULATED MATCH · MI v CSK · SEED 25 · "
                                       "MI WIN CHANCE AFTER EVERY BALL"])])
CX0, CX1, CY0, CY1 = M + 24, 700, PY0 + 54, PY1 - 36
for f in (0.25, 0.5, 0.75):
    yy = CY1 - f * (CY1 - CY0)
    line(CX0, yy, CX1, yy, sw="Deep", weight=0.75)
text(CX1 + 6, CY1 - 0.5 * (CY1 - CY0) - 6, CX1 + 60, [("Meta", [("50%", "D")])])
wp, ev = SIM["wp"], SIM["ev"]
n = len(wp)


def X(i):
    return CX0 + (CX1 - CX0) * i / (n - 1)


def Y(v):
    return CY1 - v * (CY1 - CY0)


brk = next(i for i, (inn, _) in enumerate(ev) if inn == 2)
line(X(brk), CY0 - 4, X(brk), CY1 + 4, sw="Dim", weight=0.75)
pts = [{"p": [round(X(i), 2), round(Y(v), 2)]} for i, v in enumerate(wp)]
r = c("path.create", anchors=pts, closed=False)
c("object.stroke", swatch="Cyan", weight=2.2, ids=[r["id"]])
c("object.fill", swatch="[None]", ids=[r["id"]])
for i, (_, g_) in enumerate(ev):
    if g_ == "W":
        node(X(i), Y(wp[i]), s=6, fill="Ice")
lo = min(range(brk, n), key=lambda i: wp[i])
node(X(lo), Y(wp[lo]), s=9, fill="Cyan")
line(X(lo), Y(wp[lo]), X(lo), CY0 + 4)
text(X(lo) - 200, CY0 + 2, X(lo) - 8, [("Meta", ["CSK AT 97%"]),
                                      ("Meta", [("MI AT 3%", "D")])])
text(CX0, CY1 + 10, 600, [("Meta", [("1ST INNINGS · MI 129/10", "D")])])
text(X(brk) + 6, CY1 + 10, CX1, [("Meta", [("2ND INNINGS · CSK 129/10", "D")])])

# echoed, fading repetition on the right (Monogatari "weightless?")
EX0, EX1 = 740, W - M - 18
text(EX0, PY0 + 44, EX1, [("Big", ["129/10"]), ("Big", [("129/10", "C")])])
for k, cs in enumerate(["Deep", "Blue", "Blue", None]):
    x1 = EX1 - 24 * (3 - k)      # staircase, like "weightless?"
    text(EX0 - 90, PY0 + 168 + 26 * k, x1, [("Echo", [("match tied.", cs) if cs else "match tied."])])

# ------------------------------------------------------------------ system flow
FY0, FY1 = 1536, 1712
text(M, FY0, 500, [("Meta", ["HOW IT IS WIRED"])])


def box(x0, y0, x1, y1, paras, fill=None):
    rect(x0, y0, x1, y1, stroke="Ice", weight=0.75, fill=fill)
    text(x0 + 12, y0 + 12, x1 - 12, [("Box", runs) for runs in paras])


box(M, FY0 + 34, 262, FY0 + 104, [["CricketData.org"], [("live IPL scores", "D")]])
ux0, ux1 = 340, 640
u = rect(ux0, FY0 + 24, ux1, FY1)
c("object.gradient", kind="linear", angle=0,
  stops=[{"location": 0, "color": "#22708E"}, {"location": 100, "color": "#2E2770"}], ids=[u])
text(ux0 + 14, FY0 + 38, ux1 - 14, [
    ("Box", [("ARDUINO UNO Q", "B")]),
    ("Box", ["Debian · Docker · port 8000"]),
    ("Box", ["hub: FastAPI + WebSocket"]),
    ("Box", ["simulator · win model · SQLite"]),
    ("Box", ["Wi-Fi hotspot UCIS-Cricket"]),
])
box(720, FY0 + 24, W - M, FY0 + 86, [["CYD 2.8in display"], [("two screens, touch", "D")]])
box(720, FY0 + 104, W - M, FY1, [["Phone dashboard, 8 pages"],
                                 [("live centre · scoring · simulation", "D")],
                                 [("teams · tournaments · device", "D")]])
for (xa, ya, xb, yb, lab) in [
    (262, FY0 + 69, ux0, FY0 + 69, "HTTPS"),
    (ux1, FY0 + 55, 720, FY0 + 55, "UART"),
    (ux1, FY0 + 140, 720, FY0 + 140, "WI-FI"),
]:
    line(xa, ya, xb, yb)
    node(xa, ya)
    node(xb, yb, fill="Cyan")
    text(xa + 10, ya - 20, xb + 40, [("Meta", [(lab, "D")])])

# ------------------------------------------------------------------ bottom
LY = 1740
text(M, LY, 410, [("Layer", [f"LAYER:{i:02d} — ", (s, "C")]) for i, s in enumerate([
    "UNO Q MPU · DEBIAN · DOCKER",
    "HUB · FASTAPI + WEBSOCKET",
    "SIM · BALL-BY-BALL ENGINE",
    "WIN MODEL · Z = 20·W^1.48",
    "LINK · UART 115200 8N1",
    "CYD · ESP32 + ILI9341",
    "HOTSPOT · UCIS-CRICKET",
    "DASHBOARD · REACT, PHONE",
], start=1)])
text(440, LY, 890, [
    ("Body", ["Join Wi-Fi ", ("UCIS-Cricket", "B"), " and scan the code, or open ",
              ("10.42.0.1:8000", "B"), "."]),
    ("Body", [("Next: player rating cards, a what-if replay, a crowd prediction game, LED "
               "flashes on fours, sixes and wickets, an Android app and a wireless "
               "display link.", "D")]),
])
c("object.qrCode", type="url", content="http://10.42.0.1:8000",
  rect=[W - M - 104, LY, W - M, LY + 104], color="Ice")
image(ART / "barcode.png", 440, 1858, 850, 1880, mode="fitContentToFrame", stroke=None)
text(866, 1864, W - M, [("Meta", [("ONE BAR PER BALL", "D")])])

# vertical tag on the right edge, over the hero (Lain's rotated column)
vtext(1036, 330, 560, [("Meta", ["KHUSHI KRISHNA · HARSHUL KALA · MEGHNA PANT · MEDHA UMESH"])],
      angle=-90, h=16)

# grain + scanlines over everything
gr = c("file.place", path=str(ART / "grain.png"), x=0, y=0, width=W)
c("object.effects", opacity=0.55, blend="screen", ids=[gr["id"]])

info = c("document.inspect")
print("overset:", [(s["id"], s["preview"][:30]) for s in info["stories"] if s["overset"]])
c("file.saveAs", path=str(OUT / "UCIS_Poster_v3.designcraft"))
c("file.exportPdf", path=str(OUT / "UCIS_Poster_v3.pdf"))
