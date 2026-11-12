"""Ball-by-ball scoring engine. Pure Python (no framework imports) so it runs unchanged on the UNO Q.

Conventions for a delivery:
  extra_type None : runs_bat off the bat, legal ball
  'wd'            : wide, extras = 1 + runs run, not a legal ball, not faced
  'nb'            : no-ball, extras = 1, runs_bat = runs off the bat, not legal, counts as faced
  'b' / 'lb'      : byes / leg-byes, extras = runs run, legal, not charged to bowler
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .winprob import par_score, projected_total, win_prob_batting

NOT_BOWLER_WICKETS = {"run out", "retired", "obstructing"}


@dataclass
class Delivery:
    innings: int
    batter: int
    non_striker: int
    bowler: int
    runs_bat: int = 0
    extra_type: str | None = None
    extras: int = 0
    wicket: bool = False
    wicket_kind: str | None = None
    dismissed: int | None = None

    @property
    def legal(self) -> bool:
        return self.extra_type not in ("wd", "nb")

    @property
    def total(self) -> int:
        return self.runs_bat + self.extras

    @property
    def bowler_runs(self) -> int:
        if self.extra_type in ("b", "lb"):
            return 0
        return self.runs_bat + self.extras

    @property
    def ran(self) -> int:
        """Runs physically run (drives strike rotation)."""
        if self.extra_type == "wd":
            return max(0, self.extras - 1)
        if self.extra_type in ("b", "lb"):
            return self.extras
        if self.runs_bat in (4, 6):
            return 0
        return self.runs_bat

    def chip(self) -> str:
        if self.wicket:
            return "W"
        if self.extra_type == "wd":
            return "Wd"
        if self.extra_type == "nb":
            return "Nb"
        if self.extra_type == "b":
            return f"{self.extras}b"
        if self.extra_type == "lb":
            return f"{self.extras}lb"
        return "." if self.runs_bat == 0 else str(self.runs_bat)


@dataclass
class Side:
    id: int | None
    name: str
    short: str
    xi: list[dict[str, Any]]            # [{id, name, bat, bowl, role}]


@dataclass
class MatchMeta:
    overs: int
    a: Side
    b: Side
    batting_first: str = "A"            # "A" or "B"
    series: str = ""
    format: str = "T20"
    pending_bowler: int | None = None   # scorer's choice for the next over
    swap_pending: bool = False          # scorer pressed "swap strike"
    bowlers_a: list = field(default_factory=list)   # ids allowed to bowl for A (empty = whole XI)
    bowlers_b: list = field(default_factory=list)


@dataclass
class InningsState:
    batting: str
    runs: int = 0
    wkts: int = 0
    legal: int = 0
    extras: int = 0
    striker: int | None = None
    non_striker: int | None = None
    next_idx: int = 2
    bat: dict = field(default_factory=dict)      # id -> {runs, balls, fours, sixes, out, how}
    bowl: dict = field(default_factory=dict)     # id -> {balls, runs, wkts, maidens}
    order: list = field(default_factory=list)    # batting order seen
    over_runs: list = field(default_factory=list)
    over_wkts: list = field(default_factory=list)
    fow: list = field(default_factory=list)
    part_runs: int = 0
    part_balls: int = 0
    current_over: list = field(default_factory=list)   # chips
    last_over_bowler: int | None = None
    current_bowler: int | None = None
    over_conceded: int = 0
    current_over_done: bool = False
    complete: bool = False


class Engine:
    def __init__(self, meta: MatchMeta):
        self.m = meta
        self.total_balls = meta.overs * 6
        self.max_overs_per_bowler = max(1, (meta.overs + 4) // 5)
        self.names: dict[int, str] = {}
        self.rating: dict[int, dict] = {}
        for p in meta.a.xi + meta.b.xi:
            self.names[p["id"]] = p["name"]
            self.rating[p["id"]] = p

    # --- helpers -------------------------------------------------------------
    def side(self, key: str) -> Side:
        return self.m.a if key == "A" else self.m.b

    @staticmethod
    def other(key: str) -> str:
        return "B" if key == "A" else "A"

    def _new_innings(self, batting: str) -> InningsState:
        xi = self.side(batting).xi
        inn = InningsState(batting=batting)
        if len(xi) >= 2:
            inn.striker, inn.non_striker = xi[0]["id"], xi[1]["id"]
            for pid in (inn.striker, inn.non_striker):
                inn.bat[pid] = {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": False, "how": ""}
                inn.order.append(pid)
        return inn

    def pick_bowler(self, inn: InningsState, exclude: int | None) -> int | None:
        fielding = self.other(inn.batting)
        xi = self.side(fielding).xi
        allowed = set(self.m.bowlers_a if fielding == "A" else self.m.bowlers_b)
        pool = [p for p in xi if p["id"] in allowed] if allowed else xi
        best = self._best_bowler(inn, pool, exclude)
        if best is None and allowed:        # chosen bowlers ran out of overs: fall back to the rest of the XI
            best = self._best_bowler(inn, xi, exclude)
        return best

    def _best_bowler(self, inn: InningsState, pool: list, exclude: int | None) -> int | None:
        best, best_score = None, -1e9
        for p in pool:
            pid = p["id"]
            if pid == exclude:
                continue
            done = inn.bowl.get(pid, {}).get("balls", 0) // 6
            if done >= self.max_overs_per_bowler:
                continue
            score = p.get("bowl", 30) - 9 * done
            if score > best_score:
                best, best_score = pid, score
        return best

    # --- replay --------------------------------------------------------------
    def replay(self, balls: list[Delivery]) -> dict:
        first = self.m.batting_first
        inns = [self._new_innings(first)]
        target = 0
        for d in balls:
            inn = inns[-1]
            if d.innings > len(inns):
                target = inns[0].runs + 1
                inns.append(self._new_innings(self.other(first)))
                inn = inns[-1]
            self._apply(inn, d)
            if self._innings_over(inn, target if len(inns) == 2 else 0):
                inn.complete = True
        return self._state(inns, target, balls)

    def _apply(self, inn: InningsState, d: Delivery) -> None:
        if inn.legal % 6 == 0 and (not inn.current_over or inn.current_over_done):
            inn.current_over = []
            inn.over_conceded = 0
            inn.over_runs.append(0)
            inn.over_wkts.append(0)
        inn.current_over_done = False
        inn.current_bowler = d.bowler
        bat = inn.bat.setdefault(d.batter, {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": False, "how": ""})
        if d.batter not in inn.order:
            inn.order.append(d.batter)
        bw = inn.bowl.setdefault(d.bowler, {"balls": 0, "runs": 0, "wkts": 0, "maidens": 0})

        inn.runs += d.total
        inn.extras += d.extras
        inn.part_runs += d.total
        bat["runs"] += d.runs_bat
        if d.runs_bat == 4 and d.extra_type in (None, "nb"):
            bat["fours"] += 1
        if d.runs_bat == 6 and d.extra_type in (None, "nb"):
            bat["sixes"] += 1
        if d.extra_type != "wd":
            bat["balls"] += 1
        bw["runs"] += d.bowler_runs
        inn.over_conceded += d.bowler_runs
        inn.over_runs[-1] += d.total
        if d.legal:
            inn.legal += 1
            bw["balls"] += 1
            inn.part_balls += 1
        inn.current_over.append(d.chip())

        striker, non = d.batter, d.non_striker
        if d.ran % 2 == 1:
            striker, non = non, striker

        if d.wicket:
            inn.wkts += 1
            inn.over_wkts[-1] += 1
            out = d.dismissed or d.batter
            ob = inn.bat.setdefault(out, {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": False, "how": ""})
            ob["out"] = True
            ob["how"] = d.wicket_kind or "out"
            if (d.wicket_kind or "") not in NOT_BOWLER_WICKETS:
                bw["wkts"] += 1
            inn.fow.append({"runs": inn.runs, "wkts": inn.wkts, "balls": inn.legal, "player": self.names.get(out, "?")})
            inn.part_runs = 0
            inn.part_balls = 0
            xi = self.side(inn.batting).xi
            incoming = None
            while inn.next_idx < len(xi):
                cand = xi[inn.next_idx]["id"]
                inn.next_idx += 1
                if cand not in inn.bat:
                    incoming = cand
                    break
            if incoming is not None:
                inn.bat[incoming] = {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": False, "how": ""}
                inn.order.append(incoming)
            if out == striker:
                striker = incoming
            elif out == non:
                non = incoming

        if d.legal and inn.legal % 6 == 0:
            if inn.over_conceded == 0:
                bw["maidens"] += 1
            striker, non = non, striker
            inn.last_over_bowler = d.bowler
            inn.current_over_done = True
        inn.striker, inn.non_striker = striker, non

    def _innings_over(self, inn: InningsState, target: int) -> bool:
        if inn.wkts >= 10 or inn.striker is None or inn.non_striker is None:
            return True
        if inn.legal >= self.total_balls:
            return True
        return bool(target and inn.runs >= target)

    # --- state ---------------------------------------------------------------
    def next_delivery_context(self, balls: list[Delivery]) -> dict | None:
        """Who faces and who bowls the next ball (None when the match is over)."""
        st = self._last
        if st["ended"]:
            return None
        inn: InningsState = self._inns[-1]
        innings_no = len(self._inns)
        if inn.complete:
            if innings_no == 2:
                return None
            nxt = self._new_innings(self.other(inn.batting))
            striker, non = nxt.striker, nxt.non_striker
            bowler = self.m.pending_bowler or self.pick_bowler(nxt, None)
            return {"innings": 2, "striker": striker, "non_striker": non, "bowler": bowler, "new_over": True}
        striker, non = inn.striker, inn.non_striker
        if self.m.swap_pending:
            striker, non = non, striker
        new_over = inn.legal % 6 == 0 and (not inn.current_over or inn.current_over_done)
        if new_over or inn.current_bowler is None:
            bowler = self.m.pending_bowler or self.pick_bowler(inn, inn.last_over_bowler)
        else:
            bowler = inn.current_bowler
        return {"innings": innings_no, "striker": striker, "non_striker": non, "bowler": bowler, "new_over": new_over}

    def _state(self, inns: list[InningsState], target: int, balls: list[Delivery]) -> dict:
        self._inns = inns
        inn = inns[-1]
        bat_key = inn.batting
        batting, bowling = self.side(bat_key), self.side(self.other(bat_key))
        innings_no = len(inns)
        tgt = target if innings_no == 2 else 0
        ended = innings_no == 2 and inn.complete
        result = ""
        winner = None
        if ended:
            if inn.runs >= tgt:
                winner = bat_key
                result = f"{batting.short} won by {10 - inn.wkts} wkts"
            elif inn.runs == tgt - 1:
                result = "Match tied"
            else:
                winner = self.other(bat_key)
                result = f"{bowling.short} won by {tgt - 1 - inn.runs} runs"
        if inn.complete and innings_no == 1:
            # first innings over, second not started: present the chase at 0/0
            target = inn.runs + 1

        p_bat = win_prob_batting(inn.runs, inn.wkts, inn.legal, self.total_balls, innings_no, tgt)
        if ended:
            p_bat = 0.98 if winner == bat_key else (0.5 if winner is None else 0.02)
        win_a = p_bat if bat_key == "A" else 1 - p_bat

        def batter(pid):
            if pid is None:
                return {"id": None, "name": "", "runs": 0, "balls": 0, "fours": 0, "sixes": 0}
            b = inn.bat.get(pid, {})
            return {"id": pid, "name": self.names.get(pid, "?"), "runs": b.get("runs", 0), "balls": b.get("balls", 0),
                    "fours": b.get("fours", 0), "sixes": b.get("sixes", 0)}

        bowler_id = inn.current_bowler
        bw = inn.bowl.get(bowler_id, {}) if bowler_id else {}
        self._last = {"ended": ended}
        ctx = None if ended else self.next_delivery_context(balls)
        nb_id = None
        if ctx and ctx["new_over"]:
            nb_id = ctx["bowler"]
        else:
            nb_id = self.pick_bowler(inn, bowler_id) if not ended else None
        xi = batting.xi
        next_bat = ""
        for p in xi[inn.next_idx:]:
            if p["id"] not in inn.bat:
                next_bat = p["name"]
                break

        balls_left = max(0, self.total_balls - inn.legal)
        need = max(0, tgt - inn.runs) if tgt else 0
        recent = []
        for d in balls[-18:]:
            recent.append(d.chip())
        last = balls[-1] if balls else None
        if ended:
            status = result
        elif tgt:
            status = f"{batting.short} need {need} runs off {balls_left} balls"
        elif inn.complete:
            status = f"Innings break. {bowling.short} need {inn.runs + 1} to win"
        else:
            status = f"{batting.short} batting, 1st innings"

        def card(i: InningsState):
            sd = self.side(i.batting)
            return {
                "batting": i.batting, "team": sd.short, "runs": i.runs, "wkts": i.wkts, "balls": i.legal,
                "extras": i.extras,
                "batters": [dict(batter_row(i, pid)) for pid in i.order],
                "bowlers": [{"id": pid, "name": self.names.get(pid, "?"), **v} for pid, v in i.bowl.items()],
                "over_runs": i.over_runs, "over_wkts": i.over_wkts, "fow": i.fow,
                "worm": _cumulative(i.over_runs),
            }

        def batter_row(i, pid):
            b = i.bat[pid]
            return {"id": pid, "name": self.names.get(pid, "?"), **b}

        return {
            "format": self.m.format, "series": self.m.series,
            "teamA": {"id": self.m.a.id, "name": self.m.a.name, "short": self.m.a.short},
            "teamB": {"id": self.m.b.id, "name": self.m.b.name, "short": self.m.b.short},
            "battingIsA": bat_key == "A", "innings": innings_no,
            "runs": inn.runs, "wkts": inn.wkts, "balls": inn.legal, "totalBalls": self.total_balls,
            "target": tgt, "need": need, "ballsLeft": balls_left,
            "crr": round(inn.runs * 6 / inn.legal, 2) if inn.legal else 0.0,
            "rrr": round(need * 6 / balls_left, 2) if tgt and balls_left else None,
            "projected": projected_total(inn.runs, inn.wkts, inn.legal, self.total_balls) if not tgt else None,
            "par": par_score(self.total_balls),
            "striker": batter(inn.striker if not inn.complete else None),
            "nonStriker": batter(inn.non_striker if not inn.complete else None),
            "bowler": {"id": bowler_id, "name": self.names.get(bowler_id, ""), "balls": bw.get("balls", 0),
                       "maidens": bw.get("maidens", 0), "runs": bw.get("runs", 0), "wkts": bw.get("wkts", 0)},
            "partnership": {"runs": inn.part_runs, "balls": inn.part_balls},
            "nextBat": next_bat, "nextBowl": self.names.get(nb_id, "") if nb_id else "",
            "thisOver": list(inn.current_over), "recent": recent,
            "status": status, "result": result, "winner": winner,
            "live": not ended, "ended": ended, "hasPlayers": True,
            "winA": round(win_a, 4),
            "lastEvent": _event(last), "eventSeq": sum(1 for d in balls if _event(d) != "none"),
            "next": ctx, "inningsBreak": inn.complete and innings_no == 1,
            "cards": [card(i) for i in inns],
            "seq": len(balls),
        }


def _cumulative(xs):
    out, s = [], 0
    for x in xs:
        s += x
        out.append(s)
    return out


def _event(d: Delivery | None) -> str:
    if d is None:
        return "none"
    if d.wicket:
        return "wicket"
    if d.runs_bat == 6:
        return "six"
    if d.runs_bat == 4:
        return "four"
    return "none"
