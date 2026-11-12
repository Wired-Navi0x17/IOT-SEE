"""Port of cricket_scoreboard/winprob.cpp so the CYD and the dashboard show the same number."""
import math

PAR_T20, PAR_ODI = 165, 280


def _capacity(w: int) -> float:
    return 0.001 if w <= 0 else 20.0 * w ** 1.48


def _rate(total_balls: int) -> float:
    return 1.25 if total_balls > 200 else 1.6


def expected_runs(total_balls: int, balls_left: int, wkts_in_hand: int) -> float:
    if balls_left <= 0 or wkts_in_hand <= 0:
        return 0.0
    z = _capacity(wkts_in_hand)
    return z * (1.0 - math.exp(-_rate(total_balls) * balls_left / z))


def par_score(total_balls: int) -> int:
    return PAR_ODI if total_balls > 200 else PAR_T20


def projected_total(runs: int, wkts: int, balls: int, total_balls: int) -> int:
    bl = max(0, total_balls - balls)
    return round(runs + expected_runs(total_balls, bl, 10 - wkts))


def _logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _clamp(v: float) -> float:
    return min(0.97, max(0.03, v))


def win_prob_batting(runs: int, wkts: int, balls: int, total_balls: int, innings: int, target: int) -> float:
    if total_balls <= 0:
        return 0.5
    bl = max(0, total_balls - balls)
    wih = 10 - wkts
    sigma = 2.5 + 1.6 * math.sqrt(bl)
    if innings >= 2 and target > 0:
        need = target - runs
        if need <= 0:
            return 0.99
        if wih <= 0 or bl == 0:
            return 0.5 if need == 1 else 0.01
        e = expected_runs(total_balls, bl, wih)
        return _clamp(_logistic((e - need) / (sigma / 1.8)))
    proj = runs + expected_runs(total_balls, bl, wih)
    return _clamp(_logistic((proj - par_score(total_balls)) / ((sigma + 18.0) / 1.8)))
