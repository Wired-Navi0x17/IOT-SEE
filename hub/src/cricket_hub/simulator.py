"""Ball outcome model for simulated matches. Pure Python; ported to the UNO Q in stage 2."""
from __future__ import annotations

import random
from dataclasses import dataclass

# Base T20 distribution per delivery
BASE = {"0": 0.335, "1": 0.335, "2": 0.08, "3": 0.008, "4": 0.11, "6": 0.052, "W": 0.05, "wd": 0.025, "nb": 0.005}


@dataclass
class Situation:
    bat: int            # striker batting rating 1..100
    bowl: int           # bowler rating 1..100
    over: int           # 0-based over number
    overs: int          # match overs
    wkts: int
    rrr: float | None   # required rate in a chase
    balls_left: int


def outcome_probs(s: Situation) -> dict[str, float]:
    edge = (s.bat - s.bowl) / 100.0                       # -1..1
    death = s.over >= s.overs - 4
    powerplay = s.over < max(1, round(s.overs * 0.3))
    aggr = 1.0
    if powerplay:
        aggr *= 1.12
    if death:
        aggr *= 1.3
    if s.rrr is not None:
        aggr *= min(1.8, max(0.75, 1 + (s.rrr - 8.5) * 0.09))
    if s.wkts >= 7 and not death:
        aggr *= 0.85                                      # tail protects wickets
    p = dict(BASE)
    p["4"] *= (1 + edge * 0.9) * aggr
    p["6"] *= (1 + edge * 1.1) * aggr ** 1.3
    p["W"] *= max(0.25, (1 - edge * 1.1)) * aggr ** 0.8
    p["0"] *= max(0.4, 1 - edge * 0.6) / aggr ** 0.5
    p["1"] *= 1 + (0.15 if not death else -0.05)
    total = sum(p.values())
    return {k: v / total for k, v in p.items()}


WICKET_KINDS = [("caught", 0.58), ("bowled", 0.19), ("lbw", 0.12), ("run out", 0.07), ("stumped", 0.04)]


def roll(s: Situation, rng: random.Random) -> dict:
    """Return kwargs for matches.add_ball."""
    probs = outcome_probs(s)
    r, acc = rng.random(), 0.0
    pick = "0"
    for k, v in probs.items():
        acc += v
        if r <= acc:
            pick = k
            break
    if pick == "wd":
        return {"extra_type": "wd", "extras": 1 if rng.random() > 0.08 else 5}
    if pick == "nb":
        return {"extra_type": "nb", "runs_bat": rng.choice([0, 1, 1, 4])}
    if pick == "W":
        r2, acc2 = rng.random(), 0.0
        kind = "caught"
        for k, v in WICKET_KINDS:
            acc2 += v
            if r2 <= acc2:
                kind = k
                break
        dismissed = "non_striker" if kind == "run out" and rng.random() < 0.35 else "striker"
        return {"wicket": True, "wicket_kind": kind, "dismissed": dismissed}
    runs = int(pick)
    if runs in (1, 2) and rng.random() < 0.04:
        return {"extra_type": "lb", "extras": runs}
    return {"runs_bat": runs}


def situation_for(engine, state: dict, ctx: dict) -> Situation:
    bat = engine.rating.get(ctx["striker"], {}).get("bat", 40)
    bowl = engine.rating.get(ctx["bowler"], {}).get("bowl", 40)
    in_chase = ctx["innings"] == 2
    rrr = state.get("rrr") if in_chase and not state.get("inningsBreak") else None
    return Situation(bat=bat, bowl=bowl, over=(state["balls"] // 6) if not state.get("inningsBreak") else 0,
                     overs=engine.m.overs, wkts=state["wkts"] if not state.get("inningsBreak") else 0,
                     rrr=rrr, balls_left=state["ballsLeft"])


def simulate_pure(meta, seed: int | None = None, limit: int = 2000):
    """Run a whole match in memory (tests / instant sims). Returns (state, deliveries)."""
    from .engine import Delivery, Engine
    rng = random.Random(seed)
    eng = Engine(meta)
    balls: list = []
    state = eng.replay(balls)
    for _ in range(limit):
        ctx = eng.next_delivery_context(balls)
        if ctx is None:
            break
        kw = roll(situation_for(eng, state, ctx), rng)
        out = None
        if kw.get("wicket"):
            out = ctx["non_striker"] if kw.get("dismissed") == "non_striker" else ctx["striker"]
        extras = kw.get("extras", 0)
        if kw.get("extra_type") == "nb":
            extras = 1
        balls.append(Delivery(ctx["innings"], ctx["striker"], ctx["non_striker"], ctx["bowler"],
                              kw.get("runs_bat", 0), kw.get("extra_type"), extras,
                              kw.get("wicket", False), kw.get("wicket_kind"), out))
        state = eng.replay(balls)
    return state, balls
