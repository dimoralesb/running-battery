"""Hidden physiology, what low energy changes, and the shared tempo (BUILD_PLAN "Sat 17").

Behaviours are tested on constructed states (an engine a few seconds into a match, with the
physiology set by hand), because the same seed gives a different match on another machine. The
whole-match truth series are checked in test_sim.py."""

import numpy as np
import pytest

from runningbattery.schema import RunPurpose, TrueParams
from runningbattery.sim import params as P
from runningbattery.sim.match import MatchEngine
from runningbattery.sim.output import draw_tempo
from runningbattery.sim.physiology import Physiology, tau_fast_curve, tau_slow_curve
from runningbattery.sim.roles import Run
from runningbattery.sim.rosters import make_teams


def _params(n: int = 1, **kw) -> list[TrueParams]:
    base = dict(cs=4.0, d_prime=200.0, a0=7.4, s0=9.3, fast_fraction=0.4, tau_fast=20.0)
    return [TrueParams(**(base | {"tau_slow": 450.0} | kw)) for _ in range(n)]


def _body(n: int = 1, **kw) -> Physiology:
    return Physiology(_params(n, **kw), np.random.default_rng(0))


def _engine(body: bool = True, tempo: float | None = None, seconds: float = 5.0) -> MatchEngine:
    """An engine a few seconds into a match, with fatigue on (``body``) or off."""
    rng = np.random.default_rng(0)
    teams = make_teams(rng)
    params = [p.params for team in teams for p in team.players]
    phys = Physiology(params, np.random.default_rng(1)) if body else None
    engine = MatchEngine(rng, teams, phys, tempo)
    engine.run_period(1, round(seconds * P.FRAME_RATE_HZ), 0)
    return engine


# --- Pools, tank and dip ----------------------------------------------------------------------


def test_chorley_time_constants():
    """Eq. 6b–6c [Chorley2023]: about 11 s and 430 s standing still (%D = 100), much slower when
    recovering close to CS (%D = 15: about 37 s and 2,700 s)."""
    assert tau_fast_curve(np.array(100.0)) == pytest.approx(45 * np.exp(-1.4), rel=1e-3)
    assert tau_slow_curve(np.array(100.0)) == pytest.approx(429.6, abs=0.1)
    assert tau_fast_curve(np.array(15.0)) == pytest.approx(36.5, abs=0.1)
    assert tau_slow_curve(np.array(15.0)) == pytest.approx(2728.0, abs=1.0)
    pct = np.linspace(1.0, 100.0, 100)
    assert np.all(np.diff(tau_slow_curve(pct)) < 0) and np.all(np.diff(tau_fast_curve(pct)) < 0)


def test_pools_drain_in_proportion_above_cs():
    """Above CS the pools lose (v − CS) m per second in all, shared by what each holds
    [Chorley2023, Eq. 8a]; the tank loses the same metres over TANK_M."""
    body = _body()
    for k in range(10):  # 1 s at 6 m/s, 2 m/s above CS
        body.step(np.array([6.0]), k * P.DT)
    assert body.fast_m[0] + body.slow_m[0] == pytest.approx(200.0 - 2.0)
    assert body.fast_m[0] / body.slow_m[0] == pytest.approx(0.4 / 0.6)
    assert body.tank[0] == pytest.approx(1.0 - 2.0 / P.TANK_M)


def test_pools_refill_below_cs():
    """Standing still, each pool closes 1 − 1/e of its gap in its own time constant; jogging at
    90% of CS it refills more slowly, the slow pool far more [Chorley2023, Eq. 6b–6c]."""
    body = _body()
    body.fast_m[:], body.slow_m[:] = 30.0, 60.0
    body.refill(np.array([0.0]), 20.0)  # tau_fast
    assert body.fast_m[0] == pytest.approx(80.0 - 50.0 / np.e)
    gap = 120.0 - body.slow_m[0]
    assert gap == pytest.approx(60.0 * np.exp(-20.0 / 450.0))
    # At 90% of CS (%D = 10) the fast pool's τ is about 3.8 times, the slow pool's about 10
    # times its standing value.
    jog = _body()
    jog.fast_m[:], jog.slow_m[:] = 30.0, 60.0
    jog.refill(np.array([3.6]), 20.0)
    assert jog.fast_m[0] - 30.0 < 0.45 * (body.fast_m[0] - 30.0)
    assert jog.slow_m[0] - 60.0 < 0.15 * (body.slow_m[0] - 60.0)
    above = _body()
    above.fast_m[:] = 30.0
    above.refill(np.array([4.5]), 20.0)  # above CS: no refill
    assert above.fast_m[0] == 30.0


def test_half_time_refill_and_dip():
    """The pools refill standing still over half-time (HALF_TIME_S; the slow pool more slowly
    with the tank at 0.8, SLOW_TAU_PER_TANK), the tank gets back TANK_HALF_TIME_REFILL of its
    loss, and the chance of a hard run starts DIP lower, back to normal after DIP_S."""
    body = _body()
    body.fast_m[:], body.slow_m[:], body.tank[:] = 0.0, 0.0, 0.8
    body.start_period(2)
    assert body.fast_m[0] == pytest.approx(80.0, abs=0.01)
    tau = 450.0 * (1 + P.SLOW_TAU_PER_TANK * 0.2)
    assert body.slow_m[0] == pytest.approx(120.0 * (1 - np.exp(-P.HALF_TIME_S / tau)))
    assert body.tank[0] == pytest.approx(0.8 + P.TANK_HALF_TIME_REFILL * 0.2)
    fresh = _body()
    fresh.start_period(2)
    assert fresh.run_choice[0] == pytest.approx(1.0 - P.DIP)
    fresh.step(np.array([0.0]), P.DIP_S / 2)
    assert fresh.run_choice[0] == pytest.approx(1.0 - P.DIP / 2)
    fresh.step(np.array([0.0]), P.DIP_S)
    assert fresh.run_choice[0] == pytest.approx(1.0)


def test_capacity_loss_capped():
    """Top speed and acceleration fall with the tank, each by at most CAPACITY_MAX_LOSS (about
    5% [Bradley2009, p.163; SilvaJR2018, Table 5])."""
    body = _body(3)
    body.tank[:] = [1.0, 0.9, 0.0]
    body.update_multipliers()
    speed = [
        1.0,
        1.0 - P.TOP_SPEED_PER_TANK * 0.1,
        1.0 - min(P.TOP_SPEED_PER_TANK, P.CAPACITY_MAX_LOSS),
    ]
    accel = [1.0, 1.0 - P.ACCEL_PER_TANK * 0.1, 1.0 - P.CAPACITY_MAX_LOSS]
    assert np.allclose(body.speed_mult, speed) and np.allclose(body.accel_mult, accel)


def test_tired_moments_and_series():
    """``tired`` is the pool term below TIRED_BELOW: low pools are a tired moment, a low tank
    alone is not (late-match fatigue, read from the tank). The series are fractions, one per
    second."""
    body = _body(3)
    body.fast_m[1], body.slow_m[1], body.tank[1] = 0.0, 10.0, 0.7
    body.tank[2] = 0.6  # full pools, low tank
    body.update_multipliers()
    body.record(0.0)
    body.step(np.array([0.0, 0.0, 0.0]), 0.1)
    body.record(1.0)
    fresh, tired, late = body.series(0), body.series(1), body.series(2)
    assert fresh.tired == [False, False] and tired.tired == [True, True]
    assert late.tired == [False, False] and late.tank[0] < P.LATE_TANK_BELOW
    assert late.run_choice_mult[0] < P.TIRED_BELOW <= fresh.run_choice_mult[0]
    assert tired.fast_pool[0] == 0.0 and 0.0 < tired.fast_pool[1] < 0.01
    assert fresh.t == [0.0, 1.0] and fresh.period == [1, 1]


def test_skipped_runs_one_per_situation():
    """A shape run skipped, asked again and skipped again is one skipped run, ending at the last
    ask's planned end; a made run or another purpose in between starts a new one. Only
    situations forecast to be high-intensity runs go to ``truth.json``."""
    body = _body(2)
    reask = P.SHAPE_DECLINE_S
    rec, cov = RunPurpose.RECOVERY_RUN, RunPurpose.COVERING
    body.decide(0, 10.0, 18.0, rec, False, False)
    body.decide(0, 10.0 + reask, 23.0, rec, False, True)  # asked again: same situation
    body.decide(0, 10.0 + 2 * reask, 28.0, rec, False, False)
    body.decide(1, 10.0, 18.0, cov, False, True)
    body.decide(1, 10.0 + reask, 23.0, cov, True, True)  # made on the second ask
    body.decide(1, 30.0, 38.0, cov, False, True)  # a new situation
    body.decide(1, 30.0 + reask, 43.0, rec, False, False)  # another purpose: new, not forecast
    body.decide(0, 60.0, 68.0, rec, False, False)  # too late to join: new, not forecast
    out = body.skipped_runs()
    assert [(d.player, d.t_start, d.t_end) for d in out] == [
        (0, 10.0, 28.0),
        (1, 10.0, 18.0),
        (1, 30.0, 38.0),
    ]
    assert len(body.decisions) == 8


def test_hi_run_forecast():
    """``forecast_hi_run``: a long run at full speed is a high-intensity run, a short gap or a
    wanted speed below HI_SPEED is not, and a run already at speed needs only HI_MIN_S."""
    from runningbattery.sim.movement import forecast_hi_run

    a0, s0 = 7.4, 9.3
    assert forecast_hi_run(30.0, 9.0, 0.0, a0, s0, 8.0)
    assert not forecast_hi_run(6.0, 9.0, 0.0, a0, s0, 8.0)
    assert not forecast_hi_run(40.0, P.HI_SPEED - 0.1, 3.0, a0, s0, 8.0)
    assert not forecast_hi_run(30.0, 9.0, 0.0, a0, s0, 0.5)
    assert forecast_hi_run(20.0, 7.0, 7.0, a0, s0, P.HI_MIN_S + 0.2)
    assert not forecast_hi_run(20.0, 7.0, 7.0, a0, s0, 8.0, stop=19.0)


# --- What low energy changes --------------------------------------------------------------------


def _tire(engine: MatchEngine, run_choice: float, tiredness: float | None = None) -> None:
    body = engine.physiology
    body.run_choice = np.full(22, run_choice)
    body.tiredness = np.full(22, 1.0 - run_choice if tiredness is None else tiredness)


def test_tired_players_skip_hard_runs():
    """A hard run (wanted speed above HARD_RUN_SPEED) is skipped with the player's tiredness as
    the chance; a skipped high-intensity run is logged, and the player is not asked again until
    its planned end (``Roles.free``). Fresh players make every run."""
    engine = _engine()
    roles, body = engine.roles, engine.physiology
    i, t = 5, 10.0
    _tire(engine, 0.6)
    made = 0
    for _ in range(2000):
        roles.clear()
        roles.start(i, Run(RunPurpose.COVERING, t + 4.0, 0.9), t)
        made += i in roles.runs
    assert 0.55 < made / 2000 < 0.65
    mine = [d for d in body.decisions if d.player == i and d.t_start == t]
    assert len(mine) == 2000 and sum(d.made for d in mine) == made
    assert all(d.purpose == RunPurpose.COVERING and d.t_end == t + 4.0 for d in mine)
    roles.clear()
    while i in roles.runs or not roles.declined:
        roles.clear()
        roles.start(i, Run(RunPurpose.COVERING, t + 4.0, 0.9), t)
    assert not roles.free(i)
    _tire(engine, 1.0)
    for _ in range(200):
        roles.clear()
        roles.start(i, Run(RunPurpose.RECOVERY_RUN, t + 4.0, 0.9), t)
        assert i in roles.runs


def test_easy_runs_are_never_skipped():
    """A run below HARD_RUN_SPEED is not a hard run: always made, at its planned length."""
    engine = _engine()
    _tire(engine, 0.0)
    slow = P.HARD_RUN_SPEED / engine.s0[5] / engine.roles.effort[5] * 0.9
    for _ in range(50):
        engine.roles.clear()
        engine.roles.start(5, Run(RunPurpose.SUPPORT_PLAY, 14.0, slow), 10.0)
        assert engine.roles.runs[5].t_end == 14.0


def test_tired_runs_are_shorter():
    engine = _engine()
    _tire(engine, 1.0, tiredness=0.5)
    engine.roles.start(5, Run(RunPurpose.RUN_IN_BEHIND, 14.0, 1.0), 10.0)
    assert engine.roles.runs[5].t_end == pytest.approx(10.0 + 4.0 * (1 - 0.5 * P.SHORTEN))


def test_tired_players_run_slower_and_carry_slower():
    """Every run and ball role of a tired player is (1 − SLOW × x) slower; calm movement is
    not. Carries are (1 − CARRY_SLOW × x) slower."""
    fresh, tired = _engine(), _engine()
    assert np.array_equal(fresh.pos, tired.pos)
    _tire(fresh, 1.0, tiredness=0.0)
    _tire(tired, 1.0, tiredness=0.4)
    t = 5.0
    _, cap_fresh, _, calm, _ = fresh.roles.targets(t)
    _, cap_tired, _, calm_tired, _ = tired.roles.targets(t)
    assert np.array_equal(calm, calm_tired) and (~calm).any() and calm.any()
    assert np.allclose(cap_tired[~calm], cap_fresh[~calm] * (1 - 0.4 * P.SLOW))
    assert np.allclose(cap_tired[calm], cap_fresh[calm])
    assert tired.physiology.carry(3) == pytest.approx(1 - 0.4 * P.CARRY_SLOW)


def test_capacity_caps_top_speed():
    """Everyone sprints flat out for 20 s: nobody gets faster than S0 × speed_mult."""
    engine = _engine()
    body = engine.physiology
    body.speed_mult = np.full(22, 1.0 - P.CAPACITY_MAX_LOSS)
    body.accel_mult = body.speed_mult.copy()

    def sprint(t):
        none = np.zeros(22, dtype=bool)
        far = engine.pos + np.array([200.0, 0.0])
        return far, engine.s0.copy(), np.full(22, -1, np.int8), none, none

    engine.roles.targets = sprint
    top = 0.0
    for k in range(200):
        engine.move(5.0 + k * P.DT)
        top = max(top, float((np.hypot(*engine.vel.T) / engine.s0).max()))
    assert 1.0 - P.CAPACITY_MAX_LOSS - 0.02 < top <= 1.0 - P.CAPACITY_MAX_LOSS + 1e-9


def test_no_physiology_no_tempo_is_the_old_engine():
    """Fatigue off and tempo 1.0 move exactly as without either (the switch adds nothing)."""
    old, same = _engine(body=False), _engine(body=False, tempo=1.0)
    assert np.array_equal(old.pos, same.pos) and np.array_equal(old.vel, same.vel)


# --- Shared tempo -------------------------------------------------------------------------------


def test_tempo_draw_is_clipped():
    rng = np.random.default_rng(3)
    draws = np.array([draw_tempo(rng) for _ in range(5000)])
    assert draws.min() >= 1 - P.TEMPO_CLIP_SD * P.TEMPO_SD - 1e-9
    assert draws.max() <= 1 + P.TEMPO_CLIP_SD * P.TEMPO_SD + 1e-9
    assert draws.std() == pytest.approx(P.TEMPO_SD, rel=0.1)


def test_tempo_scales_both_teams_work_rate_in_play():
    """The tempo multiplies both teams' work rate on runs and ball roles while the ball is in
    play (still capped at S0); calm movement keeps its speed."""
    plain, fast = _engine(body=False), _engine(body=False)
    fast.roles.tempo = fast.tempo = 1.05
    assert plain.mode != "dead"
    _, cap, _, calm, _ = plain.roles.targets(5.0)
    _, cap_fast, _, _, _ = fast.roles.targets(5.0)
    moving = ~calm
    assert moving[:11].any() and moving[11:].any()
    assert np.allclose(cap_fast[moving], np.minimum(cap[moving] * 1.05, plain.s0[moving]))
    assert np.allclose(cap_fast[calm], cap[calm])


# --- Fatigue checks (sim.fatigue_checks) --------------------------------------------------------


def test_peak_window_and_recovery_after_it():
    """A 60 s spell at 2 m/s per second of high-speed running in an otherwise even 0.1 m/s
    half: the peak window starts there, and the minutes after it are compared with the match
    average without the peak [Leifsson2024]."""
    from runningbattery.sim.fatigue_checks import _leifsson, _peak

    half = np.full((2700, 2), 0.1)
    half[1000:1060, 0] = 2.0
    halves = [half, np.full((2700, 2), 0.1)]
    assert _peak(halves, 60, 300)[0] == (0, 1000)
    out = _leifsson(halves, 60)
    base = 2 * (0.1 * 5400 - 6.0) / ((5400 - 60) / 60.0)  # both players, per minute
    assert out["base"] == pytest.approx(base + 0.0, rel=0.02)
    assert out["after"][0] == pytest.approx(2 * 6.0)  # 0.1 m/s for 60 s, both players


def test_legacy_engine_uses_the_fatigue_off_calibration():
    """With fatigue and tempo both off the engine uses ``PRE_FATIGUE`` (81f023d's work rates and
    run chances); the no-fatigue control keeps the current ones."""
    rng = np.random.default_rng(0)
    legacy = MatchEngine(rng, make_teams(rng), pre_fatigue=True)
    control = MatchEngine(rng, make_teams(rng))
    pre = P.PRE_FATIGUE
    assert legacy.roles.effort.tolist() == [pre["POSITION_EFFORT"][p] for p in legacy.positions]
    assert legacy.roles.overlap_chance == pre["OVERLAP_CHANCE"]
    assert control.roles.effort.tolist() == [P.POSITION_EFFORT[p] for p in control.positions]
    assert control.roles.mid_support_chance == P.MID_SUPPORT_CHANCE


# --- Substitutions ------------------------------------------------------------------------------


def test_substitution_plans():
    """3–5 per team, like for like, never the goalkeeper, each slot once, in the windows (a
    window before HALF_TIME_SUB_BEFORE is made at half-time), ids 12 and up."""
    from runningbattery.sim.rosters import plan_substitutions

    counts = []
    for seed in range(200):
        rng = np.random.default_rng(seed)
        teams = make_teams(rng)
        plans = plan_substitutions(rng, teams)
        for k, team in enumerate(teams):
            mine = [s for s in plans if s.team == k]
            counts.append(len(mine))
            slots = [s.slot for s in mine]
            assert len(set(slots)) == len(slots) and all(11 * k < j < 11 * k + 11 for j in slots)
            for s in mine:
                off = team.players[s.slot - 11 * k]
                assert s.player.position == off.position and not s.player.starter
                assert s.clock_s == 2700.0 or P.HALF_TIME_SUB_BEFORE * 60 <= s.clock_s <= 5400.0
            assert sorted(int(s.player.id[1:]) for s in mine) == list(range(12, 12 + len(mine)))
    assert set(counts) == set(P.SUBS_CHOICES)


def test_substitution_at_a_stoppage():
    """A substitution due at a dead ball: the slot gets the substitute's id, A0, S0 and full
    pools and tank; the event names both players; the frames record the change."""
    from runningbattery.schema import EventType
    from runningbattery.sim.rosters import SimPlayer, SubPlan

    rng = np.random.default_rng(0)
    teams = make_teams(rng)
    params = [p.params for team in teams for p in team.players]
    body = Physiology(params, np.random.default_rng(1))
    body.tank[:], body.fast_m[:] = 0.6, 0.0
    old = teams[0].players[9]
    new = SimPlayer(
        "H12", "Sub Stitute", 12, old.position, old.slot, _params(cs=3.5)[0], None, False
    )
    engine = MatchEngine(rng, teams, body, subs=[SubPlan(0, 9, 0.0, new)])
    frames = engine.run_period(1, 20, 0)  # the kick-off is a dead ball
    assert engine.ids[9] == "H12" and engine.s0[9] == new.params.s0 and not engine.pending
    assert body.cs[9] == 3.5 and body.tank[9] > 0.99 and body.tank[8] <= 0.6  # 2 s of play
    assert frames.subs == [(0, 9, "H12")]
    assert engine.sub_log == [(1, 0.0, 9, old.id, "H12")]
    sub = [e for e in engine.events if e["type"] == EventType.SUBSTITUTION]
    assert len(sub) == 1 and (sub[0]["player_id"], sub[0]["related_player_id"]) == (old.id, "H12")


# --- Validation spread ----------------------------------------------------------------------------


def test_wider_prior_reaches_outside_the_estimator_prior():
    """``VARY_PLAYERS`` draws some CS and D′ outside the estimator's prior ranges (PLAN §3.2);
    the default prior never does. Overrides reach the physiology's settings."""
    rng = np.random.default_rng(0)
    from runningbattery.sim.rosters import true_params

    wide = [true_params(rng, P.VARY_PLAYERS) for _ in range(2000)]
    plain = [true_params(rng) for _ in range(2000)]
    outside = lambda ps: np.mean(  # noqa: E731
        [
            not (P.CS_RANGE[0] <= p.cs <= P.CS_RANGE[1])
            or not (P.D_PRIME_RANGE[0] <= p.d_prime <= P.D_PRIME_RANGE[1])
            for p in ps
        ]
    )
    assert outside(plain) == 0.0 and 0.05 < outside(wide) < 0.5
    body = Physiology(_params(), np.random.default_rng(0), {"tank_m": 1500.0, "nope": 1.0})
    assert body.settings()["tank_m"] == 1500.0 and "nope" not in body.settings()
