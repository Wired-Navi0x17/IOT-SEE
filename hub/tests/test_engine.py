from cricket_hub.engine import Delivery, Engine, MatchMeta, Side
from cricket_hub.simulator import simulate_pure
from cricket_hub.winprob import win_prob_batting


def xi(base, bat=55, bowl=45):
    return [{"id": base + i, "name": f"P{base + i}", "bat": bat - i * 3, "bowl": bowl + (i if i > 5 else 0) * 4, "role": "AR"}
            for i in range(11)]


def meta(overs=20):
    return MatchMeta(overs=overs, a=Side(1, "Alpha", "ALP", xi(100)), b=Side(2, "Beta", "BET", xi(200)))


def test_strike_rotation_and_overs():
    e = Engine(meta())
    s, n, bw = 100, 101, 210
    balls = [Delivery(1, s, n, bw, 1)]               # single: swap
    st = e.replay(balls)
    assert st["striker"]["id"] == n and st["runs"] == 1 and st["balls"] == 1
    balls += [Delivery(1, n, s, bw, 0) for _ in range(5)]
    st = e.replay(balls)
    assert st["balls"] == 6
    assert st["striker"]["id"] == s                  # end-of-over swap
    assert st["bowler"]["maidens"] == 0


def test_extras_and_partnership():
    e = Engine(meta())
    balls = [Delivery(1, 100, 101, 210, 0, "wd", 1), Delivery(1, 100, 101, 210, 4, "nb", 1),
             Delivery(1, 100, 101, 210, 0, "lb", 2)]
    st = e.replay(balls)
    assert st["runs"] == 1 + 5 + 2
    assert st["balls"] == 1                          # only the leg-bye was legal
    assert st["bowler"]["runs"] == 6                 # leg-byes not charged
    assert st["partnership"] == {"runs": 8, "balls": 1}
    assert st["striker"]["id"] == 100                # 2 leg-byes: no swap


def test_wicket_brings_next_batter_and_rrr():
    e = Engine(meta())
    st = e.replay([Delivery(1, 100, 101, 210, wicket=True, wicket_kind="bowled", dismissed=100)])
    assert st["wkts"] == 1 and st["striker"]["id"] == 102
    assert st["bowler"]["wkts"] == 1 and st["partnership"]["runs"] == 0


def test_simulated_match_terminates_consistently():
    for seed in range(15):
        st, balls = simulate_pure(meta(), seed=seed)
        assert st["ended"], seed
        c1, c2 = st["cards"]
        assert c1["balls"] <= 120 and c2["balls"] <= 120
        assert c1["runs"] == sum(c1["over_runs"])
        assert sum(b["runs"] for b in c1["batters"]) + c1["extras"] == c1["runs"]
        assert st["result"]


def test_simulated_scores_look_like_t20():
    totals = [simulate_pure(meta(), seed=s)[0]["cards"][0]["runs"] for s in range(40)]
    avg = sum(totals) / len(totals)
    assert 120 < avg < 210, avg


def test_winprob_matches_cpp_reference():
    # 159/5 after 105 balls chasing 181 (stage-1 mockup)
    p = win_prob_batting(159, 5, 105, 120, 2, 181)
    assert 0.45 < p < 0.6
    assert win_prob_batting(181, 5, 105, 120, 2, 181) == 0.99


def test_only_chosen_bowlers_bowl():
    m = meta(overs=10)                           # 2 overs max each
    m.bowlers_b = [201, 202, 203, 204, 205]      # exactly enough for 10 overs
    m.bowlers_a = [101, 102]                     # too few: the rest of the XI must fill in
    _, balls = simulate_pure(m, seed=7)
    used_b = {d.bowler for d in balls if d.innings == 1}
    assert used_b <= set(m.bowlers_b)
    first4 = [d.bowler for d in balls if d.innings == 2 and d.extra_type not in ('wd', 'nb')][:24]
    assert set(first4) <= {101, 102}             # chosen pair bowls the first 4 overs
