"""UCIS poster v6: backlit batter silhouette, stepped mint/blue/violet halftone on black.

Needs DesignCraft running with its control port (see README.md). Art:
    python3 docs/poster/dc/char/draw_batter.py
    python3 docs/poster/dc/char/prep6.py
    python3 docs/poster/dc/build_poster6.py
"""
import pathlib

from dc import DC

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent
ART = HERE / "char"
W, H = 842, 1191          # A3 portrait, points
M = 36
d = DC()


def c(cid, **p):
    return d.cmd(cid, **p)


def nb(s):
    return len(s.encode())


def lead(v):
    return {"kind": "points", "value": v}


c("font.reload")
c("file.new", intent="print", units="points", width=W, height=H, pages=1,
  facingPages=False, margins=0, title="UCIS Poster v6")
for name, hexc in {"Night": "#06070C", "Cyan": "#96E6DA", "Violet": "#7C52E0", "Blue": "#4C7CF0",
                   "Ice": "#E8F6F2", "Mute": "#8A8FA8", "Col": "#0E1122"}.items():
    c("swatch.create", name=name, color=hexc)

PS = {
    "Title": dict(fontFamily="Special Elite", fontStyle="Regular", size=150, leading=lead(130),
                  fill="Cyan", tracking=-20),
    "Full": dict(fontFamily="Archivo", fontStyle="Medium", size=21, leading=lead(23), fill="Ice"),
    "Tag": dict(fontFamily="IBM Plex Mono", fontStyle="SemiBold", size=10.5, leading=lead(14),
                fill="Night", tracking=120),
    "Name": dict(fontFamily="Barlow Condensed", fontStyle="ExtraBold", size=76, leading=lead(66),
                 fill="Cyan", tracking=10),
    "Role": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=10, leading=lead(14),
                 fill="Blue", tracking=80),
    "Body": dict(fontFamily="Archivo", fontStyle="Regular", size=10.2, leading=lead(14.2),
                 fill="Ice"),
    "Head": dict(fontFamily="Barlow Condensed", fontStyle="Bold", size=19, leading=lead(20),
                 fill="Cyan", tracking=30),
    "Quote": dict(fontFamily="Barlow Condensed", fontStyle="ExtraBold", size=44, leading=lead(44),
                  fill="Ice", tracking=-5),
    "Cap": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=8.5, leading=lead(12),
                fill="Mute", tracking=60),
}
PARA = {"Body": {"spaceAfter": 6, "hyphenate": False}, "Full": {"hyphenate": False},
        "Quote": {"align": "left"}}
for name, chars in PS.items():
    c("style.paragraph.create", name=name, chars=chars, para=PARA.get(name, {}))
for name, chars in {"B": dict(fontStyle="SemiBold", fill="Cyan"), "V": dict(fill="Violet"),
                    "Q": dict(fill="Cyan")}.items():
    c("style.character.create", name=name, chars=chars)


def rect(x0, y0, x1, y1, fill=None, stroke=None, weight=0.8, radius=0):
    r = c("frame.create", rect=[x0, y0, x1, y1], content="unassigned")
    c("object.fill", swatch=fill or "[None]", ids=[r["id"]])
    c("object.stroke", swatch=stroke or "[None]", weight=weight if stroke else 0, ids=[r["id"]])
    if radius:
        c("object.cornerOptions", shape="rounded", size=radius, ids=[r["id"]])
    return r["id"]


def line(x0, y0, x1, y1, sw="Cyan", weight=0.8):
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


def vtext(cx, cy, length, paras, h, angle=-90):
    fid = text(cx - length / 2, cy - h / 2, cx + length / 2, paras, h=h)
    c("object.textFrameOptions", ids=[fid], autoSize="off")
    c("transform.rotate", angle=angle, ids=[fid])


def image(path, x0, y0, x1, y1, radius=10, mode="fillProportionally"):
    fid = rect(x0, y0, x1, y1, stroke="Cyan", weight=0.8, radius=radius)
    c("file.place", path=str(path), frame=fid)
    c("object.fit", mode=mode, ids=[fid])
    return fid


# ground
rect(0, 0, W, H, fill="Night")

# ---- title band: huge typewriter word, full name, one reversed tag
text(M - 4, 62, 430, [("Title", ["UCIS"])])
text(440, 52, W - M, [("Full", ["unified cricket"]), ("Full", ["intelligence system"])])
rect(440, 112, 690, 130, fill="Cyan")
text(448, 117, 690, [("Tag", ["EVERY BALL, ON THE BOX"])])
text(440, 142, W - M, [("Cap", ["LIVE · SIMULATE · PREDICT — IoT EXHIBITION 2026"])])
line(M, 186, W - M, 186)

# ---- the character, large, left
CX0, CY0, CX1 = M, 204, 466
CY1 = CY0 + (CX1 - CX0) * 2100 / 1500
image(ART / "batter_toned.png", CX0, CY0, CX1, CY1)

# ---- black right column with the big vertical line (Lain-ref) and the story
RX0 = 482
rect(RX0, CY0, W - M, CY1, fill="Col", radius=10)
vtext(W - M - 32, (CY0 + CY1) / 2, CY1 - CY0 - 40,
      [("Quote", ["THE MATCH LIVES ", ("ON THE BOARD.", "Q")])], h=48)
BX0, BX1 = RX0 + 16, W - M - 70
text(BX0, CY0 + 18, BX1, [
    ("Head", ["WHAT IT IS"]),
    ("Body", ["A battery-powered box that follows live IPL matches, plays new ones ball by "
              "ball, and works out who is likely to win after every delivery."]),
    ("Body", ["Everything runs on one ", ("Arduino UNO Q", "B"), ". No laptop, no cloud "
              "server: the board is the hub."]),
    ("Head", ["SCREEN 1 · LIVE"]),
    ("Body", ["Scores from CricketData.org, checked every 150 s during a match and every "
              "15 min otherwise, two calls short of the free plan's 100 a day. No IPL game "
              "on? It shows the next fixture."]),
    ("Head", ["SCREEN 2 · SIMULATE"]),
    ("Body", ["Pick two IPL teams and the board bowls every ball itself: dot 33.5%, four "
              "11%, six 5.2%, wicket 5%, bent by batter v bowler, the powerplay and the "
              "death overs."]),
    ("Head", ["EVERY BALL · PREDICT"]),
    ("Body", ["Runs still in reach with n balls and w wickets left, against the runs "
              "needed, gives a win chance held between 3% and 97%. Display and hub do the "
              "same maths."]),
])
bc = rect(BX0, CY1 - 74, BX1, CY1 - 40)
c("file.place", path=str(HERE / "assets4" / "barcode.png"), frame=bc)
c("object.fit", mode="fitContentToFrame", ids=[bc])
text(BX0, CY1 - 32, BX1, [("Cap", ["240 BALLS · MI v CSK · 129/10 EACH · TIED"])])

# ---- the mascot's name under her (Lucy-ref)
NY = CY1 + 16
text(M - 2, NY, 700, [("Name", ["BALL BY BALL."])])
text(M, NY + 66, 520, [("Role", ["THE BOX FOLLOWS THE MATCH, PLAYS ITS OWN, AND CALLS THE WINNER"])])

# ---- the two boards
PY0 = NY + 96
PY1 = H - 116
PW = (W - 2 * M - 16) / 2
image(ART / "unoq6.png", M, PY0, M + PW, PY1)
image(ART / "cyd6.png", M + PW + 16, PY0, W - M, PY1)
for x0, head, cap in ((M, "ARDUINO UNO Q", "QRB2210 Linux + STM32U585 · hub, simulator, hotspot"),
                      (M + PW + 16, "CHEAP YELLOW DISPLAY", "ESP32 · 2.8in touch · tap to switch screens")):
    rect(x0 + 1, PY1 - 40, x0 + PW - 1, PY1 - 1, fill="Night")
    text(x0 + 12, PY1 - 34, x0 + PW - 10, [("Head", [head]), ("Cap", [cap])])

# ---- footer
FY = H - 104
line(M, FY, W - M, FY)
text(M, FY + 14, 600, [
    ("Body", ["Join Wi-Fi ", ("UCIS-Cricket", "B"), " and open ", ("10.42.0.1:8000", "B"),
              " for the dashboard. The board talks to the display over UART, 115200 baud."]),
    ("Cap", ["RV UNIVERSITY · KHUSHI KRISHNA · HARSHUL KALA · MEGHNA PANT · MEDHA UMESH"]),
    ("Cap", ["github.com/Wired-Navi0x17/IOT-SEE"]),
])
c("object.qrCode", type="url", content="http://10.42.0.1:8000",
  rect=[W - M - 72, FY + 12, W - M, FY + 84], color="Cyan")

info = c("document.inspect")
print("overset:", [(s["id"], s["preview"][:30]) for s in info["stories"] if s["overset"]])
c("file.saveAs", path=str(OUT / "UCIS_Poster_v6.designcraft"))
c("file.exportPdf", path=str(OUT / "UCIS_Poster_v6.pdf"))
