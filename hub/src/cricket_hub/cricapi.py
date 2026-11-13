"""CricketData.org poller. The hub is the only caller, so the credit counter is authoritative."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx
from sqlmodel import select

from . import ipl
from .db import get_setting, log_activity, session
from .models import ApiUsage, Match, now
from .winprob import par_score, projected_total, win_prob_batting

log = logging.getLogger("cricapi")
URL = "https://api.cricapi.com/v1/currentMatches"
POLL_LIVE, POLL_IDLE = 90, 600


def api_key() -> str:
    return os.environ.get("CRICAPI_KEY", "").strip()


def latest_usage() -> dict:
    with session() as s:
        row = s.exec(select(ApiUsage).order_by(ApiUsage.id.desc())).first()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if row is None or row.day != today:
        return {"hitsToday": 0, "hitsLimit": row.hits_limit if row else 100, "day": today,
                "lastCall": row.ts.isoformat() if row else None, "ok": True, "configured": bool(api_key())}
    return {"hitsToday": row.hits_today, "hitsLimit": row.hits_limit, "day": row.day, "lastCall": row.ts.isoformat(),
            "ok": row.ok, "detail": row.detail, "configured": bool(api_key())}


def usage_by_day(days: int = 14) -> list[dict]:
    with session() as s:
        rows = list(s.exec(select(ApiUsage).order_by(ApiUsage.id)))
    by: dict[str, int] = {}
    for r in rows:
        by[r.day] = max(by.get(r.day, 0), r.hits_today)
    return [{"day": d, "hits": h} for d, h in sorted(by.items())[-days:]]


def _short(team_info: list, name: str) -> str:
    c = ipl.code(name)
    if c:
        return c
    for ti in team_info or []:
        if ti.get("name") == name and ti.get("shortname"):
            return ti["shortname"].upper()[:5]
    return name[:3].upper()


def _balls(o) -> int:
    o = float(o or 0)
    whole = int(o)
    return whole * 6 + round((o - whole) * 10)


def normalise(m: dict, prev: dict | None) -> dict:
    teams = m.get("teams") or ["Team A", "Team B"]
    t0, t1 = teams[0], teams[1] if len(teams) > 1 else "Team B"
    mt = (m.get("matchType") or "t20").lower()
    total = 300 if mt == "odi" else (0 if mt == "test" else 120)
    score = m.get("score") or []
    last = score[-1] if score else {}
    inning = last.get("inning", "")
    bat_a = inning.startswith(t0) if score else True
    innings = 2 if len(score) >= 2 else 1
    runs, wkts, balls = int(last.get("r", 0)), int(last.get("w", 0)), _balls(last.get("o", 0))
    target = int(score[-2].get("r", 0)) + 1 if len(score) >= 2 and total else 0
    bl = max(0, total - balls)
    need = max(0, target - runs) if target else 0
    ended = bool(m.get("matchEnded"))
    p_bat = win_prob_batting(runs, wkts, balls, total, innings, target)
    name = m.get("name", "")
    parts = [p.strip() for p in name.split(",")]
    series = parts[2] if len(parts) > 2 else name
    st = {
        "format": mt.upper() if mt != "t20" else "T20", "series": series, "venue": m.get("venue", ""),
        "teamA": {"id": None, "name": t0, "short": _short(m.get("teamInfo"), t0)},
        "teamB": {"id": None, "name": t1, "short": _short(m.get("teamInfo"), t1)},
        "battingIsA": bat_a, "innings": innings, "runs": runs, "wkts": wkts, "balls": balls, "totalBalls": total,
        "target": target, "need": need, "ballsLeft": bl,
        "crr": round(runs * 6 / balls, 2) if balls else 0.0,
        "rrr": round(need * 6 / bl, 2) if target and bl else None,
        "projected": projected_total(runs, wkts, balls, total) if not target and total else None,
        "par": par_score(total),
        "striker": {"name": ""}, "nonStriker": {"name": ""}, "bowler": {"name": ""},
        "partnership": None, "nextBat": "", "nextBowl": "",
        "thisOver": [], "recent": [], "status": m.get("status", ""), "result": m.get("status", "") if ended else "",
        "live": bool(m.get("matchStarted")) and not ended, "ended": ended, "hasPlayers": False,
        "winA": round(p_bat if bat_a else 1 - p_bat, 4), "lastEvent": "none", "eventSeq": 0,
        "cards": [{"team": s.get("inning", ""), "runs": s.get("r", 0), "wkts": s.get("w", 0), "balls": _balls(s.get("o"))}
                  for s in score],
        "source": "api",
    }
    # derive this-over chips + events from the previous poll
    if prev and prev.get("innings") == innings and prev.get("battingIsA") == bat_a:
        st["thisOver"] = list(prev.get("thisOver", []))
        st["recent"] = list(prev.get("recent", []))
        st["eventSeq"] = prev.get("eventSeq", 0)
        db, dr, dw = balls - prev["balls"], runs - prev["runs"], wkts - prev["wkts"]
        if balls > 0 and (balls - 1) // 6 != ((prev["balls"] - 1) // 6 if prev["balls"] > 0 else -1):
            st["thisOver"] = []
        if db == 1:
            chip = "W" if dw > 0 else ("." if dr == 0 else str(dr))
            st["thisOver"].append(chip)
            st["recent"] = (st["recent"] + [chip])[-18:]
        if dw > 0:
            st["lastEvent"], st["eventSeq"] = "wicket", st["eventSeq"] + 1
        elif db == 1 and dr in (4, 6):
            st["lastEvent"], st["eventSeq"] = ("four" if dr == 4 else "six"), st["eventSeq"] + 1
    return st


async def poll_once(client: httpx.AsyncClient) -> list[int]:
    """Fetch currentMatches, upsert api matches. Returns ids of matches whose state changed."""
    key = api_key()
    r = await client.get(URL, params={"apikey": key, "offset": 0}, timeout=20)
    data = r.json()
    info = data.get("info") or {}
    ok = data.get("status") == "success"
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with session() as s:
        s.add(ApiUsage(day=day, hits_today=int(info.get("hitsToday", 0)), hits_limit=int(info.get("hitsLimit", 100)),
                       ok=ok, detail="" if ok else str(data.get("reason", "failure"))[:200]))
        s.commit()
    if not ok:
        log_activity("api", f"CricketData refused the request: {data.get('reason', 'unknown')}")
        return []
    changed = []
    with session() as s:
        for m in data.get("data") or []:
            api_id = m.get("id")
            if not api_id:
                continue
            teams = m.get("teams") or []
            if len(teams) < 2 or not ipl.in_scope(*teams[:2]):
                continue                                  # IPL only unless LIVE_SCOPE=all
            row = s.exec(select(Match).where(Match.api_id == api_id)).first()
            prev = row.state if row else None
            st = normalise(m, prev)
            status = "completed" if st["ended"] else ("live" if m.get("matchStarted") else "scheduled")
            if row is None:
                row = Match(source="api", api_id=api_id, team_a_name=st["teamA"]["name"], team_b_name=st["teamB"]["name"],
                            team_a_short=st["teamA"]["short"], team_b_short=st["teamB"]["short"],
                            overs=(st["totalBalls"] // 6) or 90, series=st["series"], venue=st["venue"])
                when = m.get("dateTimeGMT")
                if when:
                    try:
                        row.scheduled_at = datetime.fromisoformat(when).replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass
            if prev != st or row.status != status:
                row.state, row.status, row.result, row.updated_at = st, status, st["result"], now()
                s.add(row)
                s.commit()
                s.refresh(row)
                st["matchId"] = row.id
                row.state = st
                s.add(row)
                s.commit()
                changed.append(row.id)
    return changed


async def poller(on_change, on_usage) -> None:
    async with httpx.AsyncClient() as client:
        while True:
            delay = 30
            try:
                forced = _force[0]
                _force[0] = False
                if api_key() and (forced or get_setting("api_polling", True)):
                    use = latest_usage()
                    if use["hitsToday"] >= use["hitsLimit"] - 2 and not forced:
                        delay = 1800
                    else:
                        changed = await poll_once(client)
                        await on_usage()
                        for mid in changed:
                            await on_change(mid)
                        with session() as s:
                            any_live = s.exec(select(Match).where(Match.source == "api", Match.status == "live")).first()
                        delay = POLL_LIVE if any_live else POLL_IDLE
            except Exception as e:  # network trouble must never kill the hub
                log.warning("poll failed: %s", e)
                delay = 120
            await _sleep_or_wake(delay)


_wake = asyncio.Event()
_force = [False]


def wake(force: bool = False) -> None:
    if force:
        _force[0] = True
    _wake.set()


async def _sleep_or_wake(seconds: float) -> None:
    _wake.clear()
    try:
        await asyncio.wait_for(_wake.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        pass
