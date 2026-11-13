"""Build the UCIS presentation poster inside a running DesignCraft app.

Start the app with its control port, then run this script:
    designcraft --control 47815          (see docs/poster/README for the launcher)
    python3 docs/poster/dc/build_poster.py
Data comes from sim.json (one match simulated by the hub, seed 25).
"""
import json
import pathlib
import re

from dc import DC

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE.parent

W, H, M = 1080, 1920, 64
CW = W - 2 * M  # content width 952

d = DC()


def c(cid, **p):
    return d.cmd(cid, **p)


def nb(s):
    return len(s.encode())


# ---------------------------------------------------------------- document
c("file.new", intent="print", units="points", width=W, height=H, pages=1,
  facingPages=False, margins=0, title="UCIS Poster")

SW = {"Paper": "#ECEAE4", "Ink": "#1B1D20", "Grey": "#5E6166",
      "Rule": "#C9C6BE", "Red": "#A3302A"}
TEAMS = re.findall(r'"([A-Z]+)": \("[^"]+", "(#[0-9A-F]{6})"',
                   (ROOT / "hub/src/cricket_hub/ipl.py").read_text())
for code, hexc in TEAMS:
    SW["T_" + code] = hexc
for name, hexc in SW.items():
    c("swatch.create", name=name, color=hexc)

PS = {
    "Display": dict(fontFamily="Barlow Condensed", fontStyle="ExtraBold", size=210,
                    leading={"kind": "points", "value": 180}, tracking=-10, fill="Ink"),
    "Kicker": dict(fontFamily="Barlow Condensed", fontStyle="SemiBold", size=34,
                   leading={"kind": "points", "value": 38}, fill="Ink"),
    "H2": dict(fontFamily="Barlow Condensed", fontStyle="Bold", size=50,
               leading={"kind": "points", "value": 52}, fill="Ink"),
    "H3": dict(fontFamily="Barlow Condensed", fontStyle="Bold", size=30,
               leading={"kind": "points", "value": 34}, fill="Ink"),
    "Lede": dict(fontFamily="IBM Plex Sans", fontStyle="Regular", size=25,
                 leading={"kind": "points", "value": 34}, fill="Ink"),
    "Body": dict(fontFamily="IBM Plex Sans", fontStyle="Regular", size=17.5,
                 leading={"kind": "points", "value": 25}, fill="Ink"),
    "Mono": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=13.5,
                 leading={"kind": "points", "value": 19}, fill="Grey"),
    "Score": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=14.5,
                  leading={"kind": "points", "value": 17.5}, fill="Ink", tracking=40),
    "Wire": dict(fontFamily="IBM Plex Mono", fontStyle="Regular", size=14.5,
                 leading={"kind": "points", "value": 22}, fill="Ink"),
}
PARA = {"H3": {"spaceAfter": 8}, "Body": {"spaceAfter": 9, "hyphenate": False},
        "Lede": {"hyphenate": False}, "H2": {"spaceAfter": 4}}
for name, chars in PS.items():
    c("style.paragraph.create", name=name, chars=chars, para=PARA.get(name, {}))
CS = {"B": dict(fontStyle="SemiBold"),
      "Wkt": dict(fontFamily="IBM Plex Mono", fontStyle="SemiBold", fill="Red"),
      "Bdy": dict(fontFamily="IBM Plex Mono", fontStyle="SemiBold", fill="Ink"),
      "G": dict(fill="Grey"), "R": dict(fill="Red"),
      "Sup": dict(size=11, baselineShift=6)}
for name, chars in CS.items():
    c("style.character.create", name=name, chars=chars)


# ---------------------------------------------------------------- helpers
def rect(x0, y0, x1, y1, fill=None, stroke=None, weight=1, shape="rectangle"):
    r = c("frame.create", rect=[x0, y0, x1, y1], content="unassigned", shape=shape)
    c("object.fill", swatch=fill or "[None]", ids=[r["id"]])
    c("object.stroke", swatch=stroke or "[None]", weight=weight if stroke else 0, ids=[r["id"]])
    return r["id"]


def line(x0, y0, x1, y1, sw="Rule", weight=1.0, dash=None):
    r = c("line.create", a=[x0, y0], b=[x1, y1])
    p = dict(swatch=sw, weight=weight, ids=[r["id"]])
    if dash:
        p["type"] = {"kind": "dashed", "pattern": dash}
    c("object.stroke", **p)
    return r["id"]


def text(x0, y0, x1, paras, h=40):
    """paras: list of (paragraph style, [str | (str, char style)])."""
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


def bounds(fid):
    for it in c("document.inspect")["spreads"][0]["items"]:
        if it["id"] == fid:
            return it["bounds"]
    raise KeyError(fid)


# ---------------------------------------------------------------- background
rect(0, 0, W, H, fill="Paper")

# ---------------------------------------------------------------- header
text(M, 76, 470, [("Display", ["UCIS"])], h=200)
text(492, 84, W - M, [
    ("Kicker", ["Unified Cricket Intelligence System"]),
    ("Lede", ["A battery-powered cricket box. One Arduino UNO Q fetches live IPL "
              "scores, plays out whole matches ball by ball and serves a phone "
              "dashboard. A 2.8-inch touch screen keeps the score at the table."]),
])

# IPL colour strip: the one place the ten team colours appear together
y = 300
cell = CW / len(TEAMS)
for i, (code, _) in enumerate(TEAMS):
    x = M + i * cell
    rect(x, y, x + cell, y + 12, fill="T_" + code)
    text(x, y + 20, x + cell - 4, [("Mono", [code])], h=20)
line(M, 360, W - M, 360, sw="Ink", weight=2)

# ---------------------------------------------------------------- signature: one match
sim = json.loads((HERE / "sim.json").read_text())
ev, wp, cards = sim["ev"], sim["wp"], sim["cards"]


def overs(balls):
    return f"{balls // 6}.{balls % 6}" if balls % 6 else str(balls // 6)


a, b = cards
text(M, 384, W - M, [
    ("H2", ["One simulated match, ball by ball"]),
    ("Body", ["Mumbai Indians v Chennai Super Kings, generated on the UNO Q by the hub's "
              "simulator (seed 25). The line is the win chance the box shows after every "
              f"delivery. MI made {a['runs']} all out in {overs(a['balls'])} overs. CSK needed "
              f"{a['runs'] + 1} and were {b['runs']} all out with {120 - b['balls']} balls left: ",
              ("a tie.", "B")]),
])

# chart
CX0, CX1, CY0, CY1 = M + 92, W - M, 520, 740
n = len(wp)
X = lambda i: CX0 + (CX1 - CX0) * i / (n - 1)  # noqa: E731
Y = lambda p: CY1 - (CY1 - CY0) * p  # noqa: E731
line(CX0, Y(0.5), CX1, Y(0.5), sw="Grey", weight=0.75, dash=[3, 4])
line(CX0, CY0, CX1, CY0, sw="Rule", weight=0.75)
line(CX0, CY1, CX1, CY1, sw="Rule", weight=0.75)
brk = next(i for i, (inn, _) in enumerate(ev) if inn == 2)
line(X(brk - 0.5), CY0 - 8, X(brk - 0.5), CY1 + 8, sw="Grey", weight=0.75)
text(M, Y(1) - 7, CX0 - 12, [("Mono", ["MI win"])], h=20)
text(M, Y(0.5) - 7, CX0 - 12, [("Mono", ["even"])], h=20)
text(M, Y(0) - 7, CX0 - 12, [("Mono", ["CSK win"])], h=20)
text(CX0, CY1 + 14, X(brk) - 10, [("Mono", [f"1st innings · MI {a['runs']}/10 ({overs(a['balls'])})"])], h=20)
text(X(brk) + 10, CY1 + 14, CX1, [("Mono", [f"2nd innings · CSK {b['runs']}/10 ({overs(b['balls'])}) · target {a['runs'] + 1}"])], h=20)
path = c("path.create", anchors=[{"p": [round(X(i), 2), round(Y(p), 2)]} for i, p in enumerate(wp)], closed=False)
c("object.fill", swatch="[None]", ids=[path["id"]])
c("object.stroke", swatch="Ink", weight=2.4, join="round", ids=[path["id"]])
for i, (_, g) in enumerate(ev):
    if g == "W":
        r = 4.2
        rect(X(i) - r, Y(wp[i]) - r, X(i) + r, Y(wp[i]) + r, fill="Red", shape="ellipse")
# annotate the low point of the chase and the last ball
lo = min(range(brk, n - 1), key=lambda i: wp[i])
text(X(lo) - 46, Y(wp[lo]) - 26, X(lo) + 70, [("Mono", [
    (f"CSK at {round((1 - wp[lo]) * 100)}%", "R")])], h=20)
text(X(n - 1) - 210, Y(wp[-1]) - 34, X(n - 1), [("Mono", ["last wicket, scores level"])], h=20)
rect(CX0, 784, CX0 + 9, 793, fill="Red", shape="ellipse")
text(CX0 + 16, 782, CX1, [("Mono", ["wicket      line: chance MI win after each ball (a wide counts as a step)"])], h=20)


# scorebook
def over_lines(inn):
    lines, cur, legal = [], [], 0
    for i, g in ev:
        if i != inn:
            continue
        cur.append(g)
        if g not in ("wd", "nb"):
            legal += 1
            if legal % 6 == 0:
                lines.append(cur)
                cur = []
    if cur:
        lines.append(cur)
    return lines


def book(x0, x1, inn, team, title):
    rect(x0, 822, x0 + 14, 836, fill="T_" + team)
    text(x0 + 24, 820, x1, [("H3", [title])], h=30)
    paras = []
    for k, balls in enumerate(over_lines(inn), 1):
        runs = [(f"{k:>2}  ", "G")]
        for g in balls:
            sym = {".": "·", "wd": "wd"}.get(g, g)
            runs.append((sym, "Wkt" if g == "W" else "Bdy" if g in ("4", "6") else None))
            runs.append(" ")
        paras.append(("Score", [r if isinstance(r, str) or r[1] else r[0] for r in runs]))
    return text(x0, 866, x1, paras, h=400)


half = (CW - 40) / 2
b1 = book(M, M + half, 1, "MI", "MI batting")
b2 = book(M + half + 40, W - M, 2, "CSK", "CSK chasing")
book_end = max(bounds(b1)[3], bounds(b2)[3])
line(M + half + 20, 822, M + half + 20, book_end, sw="Rule", weight=0.75)

# ---------------------------------------------------------------- how it is built
Y2 = book_end + 30
line(M, Y2, W - M, Y2, sw="Ink", weight=2)
col = (CW - 2 * 36) / 3
cx = [M, M + col + 36, M + 2 * (col + 36)]
cols = [None, None, None]
cols[0] = text(cx[0], Y2 + 22, cx[0] + col, [
    ("H3", ["Hardware"]),
    ("Body", [("Arduino UNO Q", "B"), " runs the hub, simulator, win model and "
              "dashboard on battery. No laptop at match time."]),
    ("Body", [("ESP32 “Cheap Yellow Display”", "B"), ", 2.8-inch touch screen, is the "
              "scoreboard. It talks to the UNO Q over three wires:"]),
    ("Wire", ["UNO Q D1  →  IO35  blue"]),
    ("Wire", ["UNO Q D0  ←  IO22  yellow"]),
    ("Wire", ["GND       —  GND   black"]),
    ("Mono", ["UART 115200 8N1 · CYD port P3"]),
])
cols[1] = text(cx[1], Y2 + 22, cx[1] + col, [
    ("H3", ["Two screens"]),
    ("Body", [("Live. ", "B"), "The current IPL match from CricketData.org. With no live "
              "game it says so and shows the next fixture."]),
    ("Body", [("Simulation. ", "B"), "A full T20 played out ball by ball, with the "
              "win-chance line drawn above."]),
    ("Body", ["Tap the screen to switch. Hold it for a QR code that opens the dashboard."]),
])
cols[2] = text(cx[2], Y2 + 22, cx[2] + col, [
    ("H3", ["Dashboard"]),
    ("Body", ["The UNO Q runs its own Wi-Fi hotspot. Phones join it and open the "
              "dashboard: no app store, no internet needed for the simulation."]),
    ("Body", ["Pages: overview, live centre, scoring, simulation, analytics, teams, "
              "tournaments and device control."]),
    ("Mono", ["FastAPI hub in Docker on the board · React front end"]),
])

# ---------------------------------------------------------------- the model
Y3 = max(bounds(f)[3] for f in cols) + 30
line(M, Y3, W - M, Y3, sw="Rule", weight=1)
m1 = text(M, Y3 + 20, M + 660, [
    ("H3", ["How the win chance is worked out"]),
    ("Body", ["Wickets in hand w give a run capacity z = 20·w", ("1.48", "Sup"),
              ". With b balls left the side can expect z(1 − e", ("−1.6b/z", "Sup"),
              ") more runs. In a chase, expected runs minus runs needed goes through a "
              "logistic curve scaled by σ = 2.5 + 1.6√b, held between 3% and 97%. The CYD "
              "(C++) and the hub (Python) run the same code, so both show the same number."]),
])
m2 = text(M + 700, Y3 + 20, W - M, [
    ("H3", ["Data path"]),
    ("Wire", ["CricketData.org"]),
    ("Wire", ["  ↓ hub on UNO Q"]),
    ("Wire", ["  ↓ UART → CYD screen"]),
    ("Wire", ["  ↓ Wi-Fi → phones"]),
])

# ---------------------------------------------------------------- footer
YF = H - 106
model_end = max(bounds(m1)[3], bounds(m2)[3])
print("model ends", model_end, "footer rule", YF - 14)
line(M, YF - 14, W - M, YF - 14, sw="Ink", weight=2)
text(M, YF, W - M - 120, [
    ("Body", [("Try it: ", "B"), "join Wi-Fi ", ("UCIS-Cricket", "B"),
              ", then scan the code or open 10.42.0.1:8000."]),
    ("Mono", ["github.com/Wired-Navi0x17/IOT-SEE · live data: CricketData.org · "
              "player ratings are placeholders until the 2026 squads are loaded"]),
])
c("object.qrCode", type="url", content="http://10.42.0.1:8000",
  rect=[W - M - 92, YF - 4, W - M, YF + 88], color="Ink")

# ---------------------------------------------------------------- report
info = c("document.inspect")
over = [s for s in info["stories"] if s["overset"]]
print("overset stories:", [(s["id"], s["preview"][:30]) for s in over])
c("file.saveAs", path=str(OUT / "UCIS_Poster.designcraft"))
c("file.exportPdf", path=str(OUT / "UCIS_Poster.pdf"))
