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
    col_a = TEAMS[ca][1] if ca else FALLBACK_A
    if not cb:
        return col_a, FALLBACK_B if distance(col_a, FALLBACK_B) >= CLASH else FALLBACK_A
    prim, alt = TEAMS[cb][1], TEAMS[cb][2]
    if distance(col_a, prim) >= CLASH:
        return col_a, prim
    return col_a, alt if distance(col_a, alt) >= distance(col_a, prim) else prim
