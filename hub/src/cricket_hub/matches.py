"""Glue between the database and the pure engine: build state, add/undo deliveries."""
from __future__ import annotations

from sqlmodel import select

from .db import session
from .engine import Delivery, Engine, MatchMeta, Side
from .models import Ball, Match, Player, Team, Tournament, now


class ScoringError(ValueError):
    pass


def _player_dict(p: Player) -> dict:
    return {"id": p.id, "name": p.name, "bat": p.bat, "bowl": p.bowl, "role": p.role, "style": p.style}


def default_xi(team_id: int) -> list[int]:
    """Best 11 by role balance: keeper, top bats, all-rounders, bowlers, in a sensible batting order."""
    with session() as s:
        ps = list(s.exec(select(Player).where(Player.team_id == team_id)))
    if len(ps) <= 11:
        return [p.id for p in sorted(ps, key=lambda p: -p.bat)]
    wk = sorted([p for p in ps if p.role == "WK"], key=lambda p: -p.bat)[:1]
    bowlers = sorted([p for p in ps if p.role == "BOWL"], key=lambda p: -p.bowl)[:4]
    ars = sorted([p for p in ps if p.role == "AR"], key=lambda p: -(p.bat + p.bowl))[:2]
    chosen = {p.id for p in wk + bowlers + ars}
    rest = sorted([p for p in ps if p.id not in chosen], key=lambda p: -p.bat)
    xi = wk + bowlers + ars + rest[: 11 - len(chosen)]
    return [p.id for p in sorted(xi, key=lambda p: -(p.bat * 2 - p.bowl * 0.3))]


def meta_for(m: Match) -> MatchMeta:
    with session() as s:
        ids = list(m.xi_a or []) + list(m.xi_b or [])
        players = {p.id: p for p in s.exec(select(Player).where(Player.id.in_(ids)))} if ids else {}
        t = s.get(Tournament, m.tournament_id) if m.tournament_id else None
    a = Side(m.team_a_id, m.team_a_name, m.team_a_short, [_player_dict(players[i]) for i in m.xi_a if i in players])
    b = Side(m.team_b_id, m.team_b_name, m.team_b_short, [_player_dict(players[i]) for i in m.xi_b if i in players])
    return MatchMeta(bowlers_a=list(m.bowlers_a or []), bowlers_b=list(m.bowlers_b or []),
                     overs=m.overs, a=a, b=b, batting_first=m.batting_first,
                     series=(t.name if t else m.series), format="T20" if m.overs <= 20 else "ODI",
                     pending_bowler=m.pending_bowler, swap_pending=m.swap_pending)


def deliveries(match_id: int) -> list[Delivery]:
    with session() as s:
        rows = list(s.exec(select(Ball).where(Ball.match_id == match_id).order_by(Ball.seq)))
    return [Delivery(r.innings, r.batter, r.non_striker, r.bowler, r.runs_bat, r.extra_type, r.extras,
                     r.wicket, r.wicket_kind, r.dismissed) for r in rows]


def compute(match_id: int) -> dict:
    with session() as s:
        m = s.get(Match, match_id)
        if m is None:
            raise ScoringError("match not found")
        if m.source == "api":
            return m.state or {}
        if m.status == "scheduled":
            return m.state or {}
        eng = Engine(meta_for(m))
        st = eng.replay(deliveries(match_id))
        st["matchId"] = m.id
        st["source"] = m.source
        st["venue"] = m.venue
        m.state = st
        if st["ended"] and m.status != "completed":
            m.status = "completed"
            m.result = st["result"]
        m.updated_at = now()
        s.add(m)
        s.commit()
        return st


def create_match(team_a_id: int, team_b_id: int, *, source: str = "local", tournament_id: int | None = None,
                 overs: int = 20, venue: str = "", scheduled_at=None) -> Match:
    with session() as s:
        ta, tb = s.get(Team, team_a_id), s.get(Team, team_b_id)
        if not ta or not tb or ta.id == tb.id:
            raise ScoringError("pick two different registered teams")
        m = Match(source=source, tournament_id=tournament_id, team_a_id=ta.id, team_b_id=tb.id,
                  team_a_name=ta.name, team_b_name=tb.name, team_a_short=ta.short, team_b_short=tb.short,
                  overs=overs, venue=venue, scheduled_at=scheduled_at)
        s.add(m)
        s.commit()
        s.refresh(m)
        return m


def start_match(match_id: int, *, toss_winner: str = "A", elected: str = "bat",
                xi_a: list[int] | None = None, xi_b: list[int] | None = None,
                bowlers_a: list[int] | None = None, bowlers_b: list[int] | None = None) -> dict:
    with session() as s:
        m = s.get(Match, match_id)
        if m is None:
            raise ScoringError("match not found")
        if m.status == "completed":
            raise ScoringError("match already completed")
        m.xi_a = xi_a or m.xi_a or default_xi(m.team_a_id)
        m.xi_b = xi_b or m.xi_b or default_xi(m.team_b_id)
        if len(m.xi_a) < 2 or len(m.xi_b) < 2:
            raise ScoringError("each team needs at least 2 registered players")
        if len(set(m.xi_a)) != len(m.xi_a) or len(set(m.xi_b)) != len(m.xi_b):
            raise ScoringError("a player is listed twice in the batting order")
        for xi, bw, side in ((m.xi_a, bowlers_a, "A"), (m.xi_b, bowlers_b, "B")):
            if bw and not set(bw) <= set(xi):
                raise ScoringError(f"team {side}: every bowler must be in the XI")
        m.bowlers_a, m.bowlers_b = list(bowlers_a or []), list(bowlers_b or [])
        bats_first = toss_winner if elected == "bat" else ("B" if toss_winner == "A" else "A")
        m.batting_first = bats_first
        winner_name = m.team_a_short if toss_winner == "A" else m.team_b_short
        m.toss = f"{winner_name} won the toss and chose to {elected}"
        m.status = "live"
        s.add(m)
        s.commit()
    return compute(match_id)


def add_ball(match_id: int, *, runs_bat: int = 0, extra_type: str | None = None, extras: int = 0,
             wicket: bool = False, wicket_kind: str | None = None, dismissed: str = "striker",
             bowler: int | None = None) -> dict:
    with session() as s:
        m = s.get(Match, match_id)
        if m is None or m.status != "live":
            raise ScoringError("match is not live")
        if extra_type not in (None, "wd", "nb", "b", "lb"):
            raise ScoringError("bad extra type")
        if extra_type == "wd" and extras < 1:
            extras = 1
        if extra_type == "nb":
            extras = 1
        eng = Engine(meta_for(m))
        balls = deliveries(match_id)
        eng.replay(balls)
        ctx = eng.next_delivery_context(balls)
        if ctx is None:
            raise ScoringError("match is over")
        if ctx["striker"] is None or ctx["non_striker"] is None:
            raise ScoringError("no batters left")
        bw = bowler or ctx["bowler"]
        if bw is None:
            raise ScoringError("no eligible bowler")
        out = None
        if wicket:
            out = ctx["non_striker"] if dismissed == "non_striker" else ctx["striker"]
        s.add(Ball(match_id=match_id, seq=len(balls) + 1, innings=ctx["innings"], batter=ctx["striker"],
                   non_striker=ctx["non_striker"], bowler=bw, runs_bat=runs_bat, extra_type=extra_type,
                   extras=extras, wicket=wicket, wicket_kind=wicket_kind if wicket else None, dismissed=out))
        m.pending_bowler = None
        m.swap_pending = False
        s.add(m)
        s.commit()
    return compute(match_id)


def undo(match_id: int) -> dict:
    with session() as s:
        last = s.exec(select(Ball).where(Ball.match_id == match_id).order_by(Ball.seq.desc())).first()
        if last is None:
            raise ScoringError("nothing to undo")
        s.delete(last)
        m = s.get(Match, match_id)
        if m.status == "completed" and m.source == "local":
            m.status = "live"
            m.result = ""
        s.add(m)
        s.commit()
    return compute(match_id)


def set_pending(match_id: int, *, bowler: int | None = None, swap: bool | None = None) -> dict:
    with session() as s:
        m = s.get(Match, match_id)
        if m is None:
            raise ScoringError("match not found")
        if bowler is not None:
            if bowler not in (m.xi_a + m.xi_b):
                raise ScoringError("bowler not in the playing XI")
            m.pending_bowler = bowler
        if swap is not None:
            m.swap_pending = not m.swap_pending if swap else False
        s.add(m)
        s.commit()
    return compute(match_id)
