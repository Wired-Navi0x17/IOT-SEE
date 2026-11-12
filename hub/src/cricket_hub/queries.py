"""Read models for the dashboard."""
from __future__ import annotations

from collections import defaultdict

from sqlmodel import select

from .db import recent_activity, session
from .models import Ball, Match, Player, Team, Tournament, TournamentTeam


def match_row(m: Match) -> dict:
    st = m.state or {}
    return {
        "id": m.id, "source": m.source, "status": m.status, "tournamentId": m.tournament_id,
        "teamA": {"id": m.team_a_id, "name": m.team_a_name, "short": m.team_a_short},
        "teamB": {"id": m.team_b_id, "name": m.team_b_name, "short": m.team_b_short},
        "venue": m.venue, "scheduledAt": m.scheduled_at.isoformat() if m.scheduled_at else None,
        "overs": m.overs, "result": m.result, "series": m.series, "toss": m.toss,
        "summary": _mini(st), "updatedAt": m.updated_at.isoformat() if m.updated_at else None,
    }


def _mini(st: dict) -> dict | None:
    if not st:
        return None
    return {k: st.get(k) for k in ("runs", "wkts", "balls", "totalBalls", "target", "battingIsA", "innings", "winA",
                                    "status", "live", "ended", "crr", "rrr", "cards")}


def list_matches(status: str | None = None, source: str | None = None, limit: int = 50) -> list[dict]:
    with session() as s:
        q = select(Match)
        if status:
            q = q.where(Match.status == status)
        if source:
            q = q.where(Match.source == source)
        if status == "scheduled":
            q = q.order_by(Match.scheduled_at)
        else:
            q = q.order_by(Match.updated_at.desc())
        return [match_row(m) for m in s.exec(q.limit(limit))]


def player_stats() -> dict[int, dict]:
    """Career aggregates from every scored/simulated delivery."""
    with session() as s:
        balls = list(s.exec(select(Ball)))
        names = {p.id: (p.name, p.team_id, p.role) for p in s.exec(select(Player))}
        teams = {t.id: t.short for t in s.exec(select(Team))}
    agg: dict[int, dict] = defaultdict(lambda: {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "outs": 0,
                                                "bballs": 0, "conceded": 0, "wkts": 0, "matches": set()})
    for b in balls:
        bt = agg[b.batter]
        bt["matches"].add(b.match_id)
        bt["runs"] += b.runs_bat
        if b.extra_type != "wd":
            bt["balls"] += 1
        if b.runs_bat == 4 and b.extra_type in (None, "nb"):
            bt["fours"] += 1
        if b.runs_bat == 6 and b.extra_type in (None, "nb"):
            bt["sixes"] += 1
        if b.wicket and b.dismissed:
            agg[b.dismissed]["outs"] += 1
        bw = agg[b.bowler]
        bw["matches"].add(b.match_id)
        if b.extra_type not in ("wd", "nb"):
            bw["bballs"] += 1
        if b.extra_type not in ("b", "lb"):
            bw["conceded"] += b.runs_bat + b.extras
        if b.wicket and (b.wicket_kind or "") not in ("run out", "retired", "obstructing"):
            bw["wkts"] += 1
    out = {}
    for pid, a in agg.items():
        if pid not in names:
            continue
        n, tid, role = names[pid]
        out[pid] = {
            "id": pid, "name": n, "team": teams.get(tid, ""), "teamId": tid, "role": role,
            "matches": len(a["matches"]), "runs": a["runs"], "balls": a["balls"], "fours": a["fours"],
            "sixes": a["sixes"], "outs": a["outs"],
            "avg": round(a["runs"] / a["outs"], 2) if a["outs"] else None,
            "sr": round(a["runs"] * 100 / a["balls"], 1) if a["balls"] else None,
            "wkts": a["wkts"], "overs": f"{a['bballs'] // 6}.{a['bballs'] % 6}", "conceded": a["conceded"],
            "econ": round(a["conceded"] * 6 / a["bballs"], 2) if a["bballs"] else None,
        }
    return out


def top_performers(limit: int = 6) -> dict:
    st = list(player_stats().values())
    batters = sorted([p for p in st if p["balls"] >= 6], key=lambda p: (-p["runs"], -(p["sr"] or 0)))[:limit]
    bowlers = sorted([p for p in st if p["wkts"] > 0], key=lambda p: (-p["wkts"], p["econ"] or 99))[:limit]
    strikers = sorted([p for p in st if p["balls"] >= 30], key=lambda p: -(p["sr"] or 0))[:limit]
    return {"batters": batters, "bowlers": bowlers, "strikeRate": strikers}


def points_table(tid: int) -> list[dict]:
    with session() as s:
        team_ids = [tt.team_id for tt in s.exec(select(TournamentTeam).where(TournamentTeam.tournament_id == tid))]
        teams = {t.id: t for t in s.exec(select(Team).where(Team.id.in_(team_ids)))} if team_ids else {}
        ms = list(s.exec(select(Match).where(Match.tournament_id == tid, Match.status == "completed")))
    rows = {i: {"teamId": i, "team": teams[i].name, "short": teams[i].short, "p": 0, "w": 0, "l": 0, "t": 0, "pts": 0,
                "rf": 0, "bf": 0, "ra": 0, "ba": 0} for i in teams}
    for m in ms:
        st = m.state or {}
        cards = st.get("cards") or []
        win = st.get("winner")
        ids = {"A": m.team_a_id, "B": m.team_b_id}
        for key in ("A", "B"):
            tid_ = ids[key]
            if tid_ not in rows:
                continue
            r = rows[tid_]
            r["p"] += 1
            if win is None:
                r["t"] += 1
                r["pts"] += 1
            elif win == key:
                r["w"] += 1
                r["pts"] += 2
            else:
                r["l"] += 1
            for c in cards:
                balls = c.get("balls", 0) if c.get("wkts", 0) < 10 else m.overs * 6
                if c.get("batting") == key:
                    r["rf"] += c.get("runs", 0)
                    r["bf"] += balls
                else:
                    r["ra"] += c.get("runs", 0)
                    r["ba"] += balls
    out = []
    for r in rows.values():
        nrr = (r["rf"] * 6 / r["bf"] if r["bf"] else 0) - (r["ra"] * 6 / r["ba"] if r["ba"] else 0)
        out.append({**{k: r[k] for k in ("teamId", "team", "short", "p", "w", "l", "t", "pts")}, "nrr": round(nrr, 3)})
    return sorted(out, key=lambda r: (-r["pts"], -r["nrr"]))


def overview() -> dict:
    with session() as s:
        tournaments = list(s.exec(select(Tournament).where(Tournament.status != "completed").order_by(Tournament.id)))
        n_teams = len(list(s.exec(select(Team.id))))
        n_players = len(list(s.exec(select(Player.id))))
        n_matches = len(list(s.exec(select(Match.id).where(Match.source != "api"))))
    tours = []
    for t in tournaments:
        with session() as s:
            ms = list(s.exec(select(Match).where(Match.tournament_id == t.id)))
            nteams = len(list(s.exec(select(TournamentTeam).where(TournamentTeam.tournament_id == t.id))))
        done = sum(1 for m in ms if m.status == "completed")
        tours.append({**t.model_dump(mode="json"), "teams": nteams, "played": done, "fixtures": len(ms),
                      "leader": (points_table(t.id) or [{}])[0].get("short") if done else None})
    return {
        "live": list_matches("live", limit=12),
        "upcoming": list_matches("scheduled", limit=8),
        "recent": list_matches("completed", limit=8),
        "tournaments": tours,
        "counts": {"teams": n_teams, "players": n_players, "matches": n_matches},
        "top": top_performers(5),
        "activity": [a.model_dump(mode="json") for a in recent_activity(20)],
    }


def match_analytics(match_id: int) -> dict:
    with session() as s:
        m = s.get(Match, match_id)
    st = (m.state if m else {}) or {}
    cards = st.get("cards") or []
    out = []
    for c in cards:
        overs = c.get("over_runs") or []
        phases = {"powerplay": overs[:6], "middle": overs[6:max(6, len(overs) - 4)] if len(overs) > 10 else overs[6:],
                  "death": overs[-4:] if len(overs) > 10 else []}
        out.append({
            "team": c.get("team"), "batting": c.get("batting"), "runs": c.get("runs"), "wkts": c.get("wkts"),
            "worm": c.get("worm") or [], "manhattan": overs, "wicketsPerOver": c.get("over_wkts") or [],
            "phases": {k: {"runs": sum(v), "overs": len(v), "rate": round(sum(v) / len(v), 2) if v else None}
                       for k, v in phases.items()},
            "fow": c.get("fow") or [],
        })
    return {"match": match_row(m) if m else None, "innings": out}
