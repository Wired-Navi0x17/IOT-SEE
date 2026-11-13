"""The 10 IPL franchises and their match colours.

Each team has a primary colour and an alternate, both lifted so they read on the
charcoal background (navy and black brand colours are invisible there). Team A
always shows its primary. Team B shows its primary unless it is too close to
Team A's, in which case it switches to its alternate. MI v DC is blue v red,
RCB v PBKS is red v silver, CSK v MI is yellow v blue.

Keep this table identical to web/src/lib/teams.ts and cricket_scoreboard/ipl_teams.cpp.
"""
from __future__ import annotations

import re

# code: (full name, primary, alternate, extra aliases)
TEAMS: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "CSK": ("Chennai Super Kings", "#F9CD05", "#3E6FD9", ()),
    "DC": ("Delhi Capitals", "#2F6FE0", "#E5323B", ("Delhi Daredevils",)),
    "GT": ("Gujarat Titans", "#6F8FD4", "#D9B65C", ()),
    "KKR": ("Kolkata Knight Riders", "#9B5CF0", "#E0B23A", ()),
    "LSG": ("Lucknow Super Giants", "#2EA8E6", "#F28B30", ()),
    "MI": ("Mumbai Indians", "#1F7FE8", "#D9AE3E", ()),
    "PBKS": ("Punjab Kings", "#E5323B", "#C3CAD1", ("Kings XI Punjab", "KXIP")),
    "RR": ("Rajasthan Royals", "#EA1A85", "#3D6BE0", ()),
    "RCB": ("Royal Challengers Bengaluru", "#D9262C", "#D4AF37", ("Royal Challengers Bangalore",)),
    "SRH": ("Sunrisers Hyderabad", "#F7752A", "#B8BEC4", ()),
}
# National sides (not IPL): label colour, then a deep / bright / hot ramp for the CYD beam. The beam mixes
# jersey colours: India is navy -> blue -> orange trim; New Zealand's black is lifted to steel -> silver
# -> white so it still reads on the dark screen. Beam-only; the IPL table above stays the single source.
JERSEYS: dict[str, tuple[str, tuple[str, str, str]]] = {
    "india": ("#2F7BF0", ("#0B2A6B", "#2F7BF0", "#FFB866")),
    "newzealand": ("#C7CED8", ("#2B323F", "#AEB7C4", "#FFFFFF")),
}
JERSEY_ALIASES = {"ind": "india", "nz": "newzealand", "blackcaps": "newzealand", "nzl": "newzealand"}


def jersey(name: str | None):
    k = re.sub(r"[^a-z]", "", (name or "").lower())
    return JERSEYS.get(JERSEY_ALIASES.get(k, k))


def ramps(a: str | None, b: str | None) -> tuple[str, str]:
    """"deep,bright,hot" hex (no #) per team for the CYD beam; "" = derive from the single colour."""
    def one(n):
        j = jersey(n)
        return ",".join(c[1:] for c in j[1]) if j else ""
    return one(a), one(b)


FALLBACK_A, FALLBACK_B = "#A974E8", "#38C9B4"   # non-IPL or unknown teams
CLASH = 150.0                                      # redmean distance below this = too alike

_ALIAS: dict[str, str] = {}
for _code, (_name, _p, _a, _extra) in TEAMS.items():
    for _k in (_code, _name, *_extra):
        _ALIAS[re.sub(r"[^a-z]", "", _k.lower())] = _code


def code(name_or_short: str | None) -> str | None:
    """'Mumbai Indians', 'MI', 'mi' -> 'MI'. None when it is not an IPL side."""
    return _ALIAS.get(re.sub(r"[^a-z]", "", (name_or_short or "").lower()))


def is_ipl(name: str | None) -> bool:
    return code(name) is not None


def _rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def distance(c1: str, c2: str) -> float:
    (r1, g1, b1), (r2, g2, b2) = _rgb(c1), _rgb(c2)
    rm = (r1 + r2) / 2
    dr, dg, db = r1 - r2, g1 - g2, b1 - b2
    return ((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db) ** 0.5


def pair_colors(a: str | None, b: str | None) -> tuple[str, str]:
    """Display colours for Team A and Team B of one match."""
    ca, cb = code(a), code(b)
    ja, jb = jersey(a), jersey(b)
    col_a = TEAMS[ca][1] if ca else (ja[0] if ja else FALLBACK_A)
    if jb:
        return col_a, jb[0]
    if not cb:
        return col_a, FALLBACK_B if distance(col_a, FALLBACK_B) >= CLASH else FALLBACK_A
    prim, alt = TEAMS[cb][1], TEAMS[cb][2]
    if distance(col_a, prim) >= CLASH:
        return col_a, prim
    return col_a, alt if distance(col_a, alt) >= distance(col_a, prim) else prim


def live_scope() -> str:
    """LIVE_SCOPE: "ipl" (default) = IPL games only; "all" = every match; or team names, e.g. "India,New Zealand",
    = IPL games plus any match one of those teams plays."""
    import os
    return os.environ.get("LIVE_SCOPE", "ipl").strip() or "ipl"


def in_scope(*names: str | None) -> bool:
    scope = live_scope()
    if scope.lower() == "all" or all(is_ipl(n) for n in names):
        return True
    if scope.lower() == "ipl":
        return False
    wanted = {t.strip().lower() for t in scope.split(",") if t.strip()}
    return any((n or "").strip().lower() in wanted for n in names)
