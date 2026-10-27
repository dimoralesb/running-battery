"""Fatigue estimator (BUILD_PLAN "Mon 19"): battery maths on constructed speed series, the
per-player update's band, the no-truth rule, and substitutes. Constructed inputs only, because
the same seed gives a different match on another machine."""

import ast
import builtins
import io
import json
from pathlib import Path

import numpy as np
import pytest

from runningbattery.engine import params as P
from runningbattery.engine.__main__ import main as engine_main
from runningbattery.engine.battery import prior_draws, run, tau, weighted_quantiles
from runningbattery.engine.estimate import chance_map, compute, estimate
from runningbattery.engine.signals import Seconds, calibrate_chance, metabolic_power, red_zone
from runningbattery.io import SIGNALS, Match, read_signals, write_match
from runningbattery.schema import (
    Ball,
    ClubTestValues,
    Generator,
    MatchMetadata,
    PeriodInfo,
    PlayerInfo,
    PlayerPosition,
    Substitution,
    TeamInfo,
    TrackingFrame,
)

ENGINE = Path(__file__).resolve().parents[1] / "src" / "runningbattery" / "engine"
HZ = round(P.FRAME_RATE_HZ)


NO_WEAR = (0.0, P.WEAR_SCALE_M, P.WEAR_HALF_KEEP)


def _battery(speed: np.ndarray, cs: float = 4.0, dp: float = 200.0, k: float = P.K, period=None,
             wear=NO_WEAR):
    """Run one player's battery at 10 Hz with one (CS, D′); returns the result. Without wear by
    default, so the battery maths below hold exactly; wear has its own tests."""
    speed = np.asarray(speed, dtype=float)[:, None]
    period = np.ones(len(speed), dtype=int) if period is None else period
    record = np.arange(len(speed)) % HZ == HZ - 1  # the end of each second
    return run(speed, period, record, np.array([[cs]]), np.array([[dp]]), k, wear=wear)


# --- Battery maths ------------------------------------------------------------------------------


def test_drains_metre_for_metre_above_cs():
    """1 s at 6 m/s with CS 4 m/s uses 2 m of D′ [Skiba2021]."""
    res = _battery(np.full(10 * HZ, 6.0))
    assert res.median[-1, 0] == pytest.approx((200.0 - 2.0 * 10) / 200.0)
    assert np.all(np.diff(res.median[:, 0]) < 0)


def test_refills_with_tau_k_dprime_over_gap():
    """Standing still, τ = k·D′/CS: with k = 4, D′ 200 m and CS 4 m/s, τ = 200 s, so after 200 s
    the deficit is down to 1/e (exact exponential step)."""
    drain = np.full(25 * HZ, 6.0)  # 50 m below full
    rest = np.zeros(200 * HZ)
    res = _battery(np.concatenate([drain, rest]))
    deficit = 1.0 - res.median[-1, 0]
    assert deficit == pytest.approx(0.25 * np.exp(-1.0), rel=1e-6)
    assert tau(np.array(0.0), np.array(4.0), np.array(200.0), 4.0) == pytest.approx(200.0)


def test_wear_slows_the_refill_by_its_factor():
    """Decision 56: after 50 m above CS the refill time is τ × (1 + α (1 − e^(−50/scale))); with
    the defaults (α 1, scale 400 m) that is ×1.1175, so 200 s standing leaves 0.25·e^(−1/1.1175)."""
    drain = np.full(25 * HZ, 6.0)
    rest = np.zeros(200 * HZ)
    wear = (P.WEAR_ALPHA, P.WEAR_SCALE_M, P.WEAR_HALF_KEEP)
    res = _battery(np.concatenate([drain, rest]), wear=wear)
    slow = 1.0 + P.WEAR_ALPHA * (1.0 - np.exp(-50.0 / P.WEAR_SCALE_M))
    assert 1.0 - res.median[-1, 0] == pytest.approx(0.25 * np.exp(-1.0 / slow), rel=1e-4)
    # the drain itself is unchanged: metre for metre
    assert _battery(drain, wear=wear).median[-1, 0] == pytest.approx(0.75)


def test_wear_builds_with_hard_running():
    """The same 50 m spell and 60 s rest leave the battery lower the sixth time than the first,
    with wear; without it the battery after each rest is the same steady cycle or higher."""
    wear = (P.WEAR_ALPHA, P.WEAR_SCALE_M, P.WEAR_HALF_KEEP)
    spell = np.concatenate([np.full(25 * HZ, 6.0), np.zeros(60 * HZ)])
    six = np.concatenate([spell] * 6)
    worn, plain = _battery(six, wear=wear), _battery(six)
    end_of = lambda res, n: res.median[n * len(spell) // HZ - 1, 0]  # noqa: E731
    assert end_of(worn, 6) < end_of(plain, 6)
    assert end_of(plain, 6) - end_of(worn, 6) > end_of(plain, 1) - end_of(worn, 1)


def test_tau_clipped_and_k_scales_it():
    assert tau(np.array(3.99), np.array(4.0), np.array(200.0), 4.0) == P.TAU_RANGE[1]
    assert tau(np.array(0.0), np.array(4.0), np.array(20.0), 1.0) == P.TAU_RANGE[0]
    drain_rest = np.concatenate([np.full(25 * HZ, 6.0), np.zeros(60 * HZ)])
    fast, slow = _battery(drain_rest, k=1.0), _battery(drain_rest, k=4.0)
    assert fast.median[-1, 0] > slow.median[-1, 0]  # k = 1 refills about 4× faster


def test_one_way_correction_raises_d_prime_only():
    """Running 300 m above CS with D′ 200 m: the battery stops at zero and D′ rises by the
    100 m shortfall; it is never lowered and CS does not move (PLAN §3.2)."""
    res = _battery(np.full(150 * HZ, 6.0))
    assert res.median[-1, 0] == 0.0
    assert res.d_prime[0, 1] == pytest.approx(300.0)
    assert res.cs[0, 1] == 4.0
    light = _battery(np.full(60 * HZ, 3.0))
    assert light.d_prime[0, 1] == 200.0 and light.median[-1, 0] == 1.0


def test_half_time_rest_refills():
    speed = np.concatenate([np.full(25 * HZ, 6.0), np.full(1 * HZ, 0.0)])
    period = np.array([1] * (25 * HZ) + [2] * HZ)
    res = _battery(speed, period=period)
    # 900 s standing with τ = 200 s, plus the first second of the second half.
    expected = 1.0 - 0.25 * np.exp(-(P.HALF_TIME_S + 1.0) / 200.0)
    assert res.median[-1, 0] == pytest.approx(expected, rel=1e-6)


def test_metabolic_power_constant_speed_and_clamp():
    """On grass at constant speed P = 3.6 × 1.29 × v: 25.5 W/kg at 5.5 m/s (synthesis §3.3)."""
    assert metabolic_power(np.array(5.5), np.array(0.0)) == pytest.approx(25.5, abs=0.05)
    hard = metabolic_power(np.array(3.0), np.array(20.0))
    assert hard == metabolic_power(np.array(3.0), np.array(P.ES_LIMIT * P.G))
    assert metabolic_power(np.array(3.0), np.array(-4.0)) > 0  # braking still costs energy


# --- Per-player update and band -----------------------------------------------------------------


def test_prior_draws_seeded_per_player_and_in_range():
    a, b = prior_draws("H08"), prior_draws("H08")
    assert np.array_equal(a, b) and a.shape == (P.N_DRAWS, 2)
    assert not np.array_equal(a, prior_draws("H09"))
    for name, prior in P.PRIORS.items():
        d = prior_draws("H08", prior=prior)
        assert prior.cs_range[0] <= d[:, 0].min() and d[:, 0].max() <= prior.cs_range[1], name
        assert prior.d_prime_range[0] <= d[:, 1].min() and d[:, 1].max() <= prior.d_prime_range[1]
        assert np.mean(d[:, 0]) == pytest.approx(prior.cs_mean, abs=0.05), name
        assert np.mean(d[:, 1]) == pytest.approx(prior.d_prime_mean, rel=0.1), name


def test_pro_prior_drains_less_than_university():
    """A professional's typical CS (4.1 m/s) is above the university one (3.7 m/s): the same
    running at 4 m/s drains the university battery and leaves the pro battery's median full."""
    speed = np.full(60 * HZ, 4.0)
    period, record = np.ones(len(speed), dtype=int), np.arange(len(speed)) % HZ == HZ - 1
    level = {}
    for name, prior in P.PRIORS.items():
        d = prior_draws("H08", prior=prior)
        level[name] = run(speed[:, None], period, record, d[None, :, 0], d[None, :, 1]).median
    assert level["pro"][-1, 0] == 1.0 and level["university"][-1, 0] < 0.95


def test_weighted_quantiles_equal_weights_match_numpy():
    x = np.random.default_rng(0).normal(size=(3, 200))
    q = weighted_quantiles(x, np.ones_like(x), (0.1, 0.5, 0.9))
    for k, level in enumerate((0.1, 0.5, 0.9)):
        assert np.allclose(q[:, k], np.quantile(x, level, axis=1, method="inverted_cdf"))


def _draws_battery(speed: np.ndarray):
    d = prior_draws("H08")
    period = np.ones(len(speed), dtype=int)
    record = np.arange(len(speed)) % HZ == HZ - 1
    return run(speed[:, None], period, record, d[None, :, 0], d[None, :, 1]), d


def test_band_from_draws_without_contradiction():
    """Jogging below every draw's CS: nothing contradicts the prior, so the band is full and the
    capacity estimate is the prior's own weighted quantiles."""
    res, d = _draws_battery(np.full(120 * HZ, 3.0))
    assert np.all(res.lo == 1.0) and np.all(res.hi == 1.0)
    prior = weighted_quantiles(d[None, :, 1], np.ones((1, len(d))), (0.1, 0.5, 0.9))
    assert np.allclose(res.d_prime, prior)


def test_band_narrows_and_moves_up_when_running_contradicts_small_d_prime():
    """Hard running (7 m/s for 90 s, about 290–340 m above CS) contradicts the draws with small
    D′: they are down-weighted, the estimated D′ moves above the prior median, and the band stays
    ordered (lo ≤ median ≤ hi) every second."""
    speed = np.concatenate([np.full(90 * HZ, 7.0), np.zeros(60 * HZ)])
    res, d = _draws_battery(speed)
    assert np.all(res.lo <= res.median) and np.all(res.median <= res.hi)
    assert res.d_prime[0, 1] > np.median(d[:, 1]) + 50
    mid = 80  # 80 s into the run: the band is wide and the median is low
    assert res.hi[mid, 0] - res.lo[mid, 0] > 0.05
    assert res.median[mid, 0] < 0.3


def test_low_chance_is_the_share_of_draws_below_low_battery():
    """5 m/s for 60 s drains every draw (CS ≤ 4.7 m/s) by at most 90 m, less than any D′, so no
    draw is down-weighted: the chance is the plain share of draws below LOW_BATTERY. Standing
    still it is 0; with one value (club mode) there is no chance."""
    res, d = _draws_battery(np.full(60 * HZ, 5.0))
    level = 1.0 - (5.0 - d[:, 0]) * 60.0 / d[:, 1]
    assert res.low_chance[-1, 0] == pytest.approx(np.mean(level < P.LOW_BATTERY), abs=0.011)
    assert 0.0 < res.low_chance[-1, 0] < 1.0
    assert np.all(np.diff(res.low_chance[:, 0]) >= 0)  # draining only: the chance only grows
    still, _ = _draws_battery(np.zeros(60 * HZ))
    assert np.all(still.low_chance == 0.0)
    assert _battery(np.full(60 * HZ, 5.0)).low_chance is None


def test_calibration_map_is_monotone_and_interpolates():
    """The fitted map (engine/params.py) is a valid monotone map on [0, 1]; between knots the
    chance is linear, beyond the ends it holds the end values."""
    xs, ys = np.array(P.LOW_CHANCE_MAP).T
    assert np.all(np.diff(xs) > 0) and np.all(np.diff(ys) >= 0)
    assert 0.0 <= ys.min() and ys.max() <= 1.0 and xs[0] == 0.0
    table = ((0.0, 0.0), (0.5, 0.2), (0.8, 0.6))
    out = calibrate_chance(np.array([0.0, 0.25, 0.65, 0.8, 1.0]), table)
    assert out == pytest.approx([0.0, 0.1, 0.4, 0.6, 0.6])


def test_calibration_map_only_for_the_settings_it_was_fitted_with():
    assert chance_map("broadcast", "draws", "pro", P.K) is P.LOW_CHANCE_MAP
    assert chance_map("broadcast", "draws", "pro", 3.0) is None
    assert chance_map("broadcast", "draws", "university", P.K) is None
    assert chance_map("club", "correction", "pro", P.K) is None


# --- Red-zone spells and the post-peak flag ----------------------------------------------------


def test_post_peak_flag_lasts_two_minutes_after_a_one_minute_peak_and_ends_at_half_time():
    n = 600
    period = np.array([1] * 400 + [2] * 200)
    t = np.concatenate([np.arange(400), np.arange(200)])
    hsr = np.zeros((n, 1))
    hsr[100] = 80.0  # one 1-min window above the published peak (62 m)
    hsr[390] = 80.0  # a second one, 10 s before half-time
    full = {w: np.ones((n, 1), dtype=bool) for w in P.HSR_WINDOWS_S}
    s = Seconds(
        period=period,
        t=t,
        on=np.ones((n, 1), dtype=bool),
        speed=np.zeros((n, 1)),
        power=np.zeros((n, 1)),
        power_avg={},
        energy=np.zeros((n, 1)),
        hsr={60: hsr, 120: np.zeros((n, 1)), 300: np.zeros((n, 1))},
        full=full,
        in_play={},
        battery=np.ones((n, 1)),
        battery_lo=None,
        battery_hi=None,
    )
    hot, post = red_zone(s)
    assert hot[60][100, 0] and hot[60][390, 0] and hot[60].sum() == 2
    assert post[100 : 100 + 121, 0].all() and not post[100 + 121 : 390, 0].any()
    assert post[390:400, 0].all() and not post[400:, 0].any()


# --- Constructed match: no-truth rule and substitutes ------------------------------------------

POSITIONS = ["GK", "CB", "CB", "FB", "FB", "DM", "CM", "AM", "WM", "WM", "CF"]
TESTS = ClubTestValues(cs=5.9, d_prime=590, a0=7.4, s0=9.3)  # far from the prior on purpose


def _team(side: str, tests: bool) -> TeamInfo:
    letter = side[0].upper()
    players = [
        PlayerInfo(
            id=f"{letter}{i:02d}",
            name=f"Player {letter}{i}",
            shirt=i,
            position=pos,
            starter=True,
            test_values=TESTS if tests and pos != "GK" else None,
        )
        for i, pos in enumerate(POSITIONS, start=1)
    ]
    players.append(
        PlayerInfo(
            id=f"{letter}12",
            name=f"Sub {letter}",
            shirt=12,
            position="CF",
            starter=False,
            test_values=TESTS if tests else None,
        )
    )
    return TeamInfo(
        id=side,
        name=side,
        side=side,
        formation="4-2-3-1",
        attacks_positive_x_in_period_1=side == "home",
        players=players,
    )


SUB_T = 30.0  # the home CF (H11) goes off for H12 at 30 s into the second half
DURATION = (150.0, 60.0)


def _match(tests: bool = False) -> Match:
    """Two short halves. Everyone stands still in their own spot except the home CF, who runs
    circles at 6 m/s (2 m/s above CS) in the first half. H12 comes on for H11 in the second
    half, at the spot where H11 stood."""
    teams = [_team("home", tests), _team("away", tests)]
    starters = [p.id for team in teams for p in team.players if p.starter]
    spots = {pid: (-40.0 + 4.0 * k, -30.0 + 2.5 * k) for k, pid in enumerate(starters)}
    frames, frame = [], 0
    for period, duration in enumerate(DURATION, start=1):
        for k in range(round(duration * HZ)):
            t = round(k / HZ, 1)
            players = []
            for pid in starters:
                x, y = spots[pid]
                if pid == "H11" and period == 1:
                    angle = 6.0 * t / 15.0  # 15 m radius at 6 m/s
                    x, y = 15.0 * np.cos(angle), 15.0 * np.sin(angle)
                if pid == "H11" and period == 2 and t >= SUB_T:
                    pid = "H12"
                players.append(PlayerPosition(id=pid, x=round(x, 2), y=round(y, 2)))
            frames.append(
                TrackingFrame(
                    frame=frame,
                    period=period,
                    t=t,
                    clock=t + (2700.0 if period == 2 else 0.0),
                    ball_status="alive",
                    possession_team="home",
                    ball=Ball(x=0.0, y=0.0, z=0.0),
                    players=players,
                )
            )
            frame += 1
    n1 = round(DURATION[0] * HZ)
    meta = MatchMetadata(
        match_id="constructed",
        generator=Generator(version="test", seed=0),
        periods=[
            PeriodInfo(period=1, start_frame=0, end_frame=n1 - 1, duration_s=DURATION[0]),
            PeriodInfo(period=2, start_frame=n1, end_frame=frame - 1, duration_s=DURATION[1]),
        ],
        teams=teams,
        substitutions=[
            Substitution(period=2, t=SUB_T, team_id="home", player_out="H11", player_in="H12")
        ],
    )
    return Match(metadata=meta, frames=frames, events=[])


@pytest.fixture(scope="module")
def constructed() -> Match:
    return _match()


def test_engine_never_imports_truth():
    """Static check: no engine module imports or uses the truth reader or the truth models, or
    names truth.json in code (docstrings may mention it)."""
    banned = {"read_truth", "MatchTruth", "PlayerTruth", "TruthSeries", "TrueParams", "TRUTH"}
    for path in ENGINE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom | ast.Import):
                names = {a.name for a in node.names}
                assert not names & banned, (path.name, names & banned)
                assert "validate" not in (getattr(node, "module", "") or ""), path.name
            used = getattr(node, "id", None) or getattr(node, "attr", None)
            assert used not in banned, (path.name, used)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not node.value.strip().endswith("truth.json"), path.name


def test_cli_never_opens_truth_json(tmp_path, monkeypatch, constructed):
    """Dynamic check: run the CLI on a folder that has a truth.json and record every file it
    opens."""
    write_match(tmp_path, constructed.metadata, constructed.frames, constructed.events)
    (tmp_path / "truth.json").write_text(json.dumps({"secret": True}))
    opened: list[str] = []
    real_open = io.open

    def spy(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(io, "open", spy)
    engine_main([str(tmp_path)])
    monkeypatch.undo()
    names = {Path(p).name for p in opened}
    assert "truth.json" not in names
    assert {"tracking.jsonl", "events.jsonl", "metadata.json"} <= names
    assert read_signals(tmp_path / SIGNALS).match_id == "constructed"


def test_broadcast_mode_ignores_club_test_values(constructed):
    """Test values far from the prior change nothing in broadcast mode and everything in club
    mode."""
    with_tests = _match(tests=True)
    plain = estimate(constructed)
    assert estimate(with_tests) == plain
    club = compute(with_tests, mode="club")
    assert club.settings.update == "correction" and club.battery.lo is None
    j = club.tracks.ids.index("H11")
    assert club.battery.cs[j, 1] == TESTS.cs and club.battery.d_prime[j, 1] == TESTS.d_prime


def test_signals_keep_the_raw_chance_next_to_the_calibrated_one(constructed):
    """The calibrated chance is the raw one through the map; with settings the map was not
    fitted for, the two are the same and no map is named."""
    sig = estimate(constructed)
    assert sig.engine.low_chance_map == P.LOW_CHANCE_MAP_SOURCE
    s = {p.player_id: p.series for p in sig.players}["H11"]
    expected = calibrate_chance(np.array(s.low_chance_raw), P.LOW_CHANCE_MAP)
    # both rounded to 3 decimals, and the map is up to about twice as steep as the raw chance
    assert s.low_chance == pytest.approx(expected, abs=0.002)
    assert max(s.low_chance_raw) > 0.0
    other = estimate(constructed, k=3.0)
    assert other.engine.low_chance_map is None
    for p in other.players:
        assert p.series.low_chance == p.series.low_chance_raw


def test_substitutes_get_their_own_time_on_the_pitch(constructed):
    sig = estimate(constructed)
    by_id = {p.player_id: p for p in sig.players}
    assert set(by_id) == {f"H{i:02d}" for i in range(1, 13)} | {f"A{i:02d}" for i in range(1, 12)}
    off, on = by_id["H11"].series, by_id["H12"].series
    n1 = round(DURATION[0])
    assert off.period == [1] * n1 + [2] * round(SUB_T)
    assert on.period == [2] * round(DURATION[1] - SUB_T) and on.t[0] == SUB_T
    assert by_id["H12"].starter is False
    # H11 ran 2 m/s above CS for most of the first half: a deep, banded drain; the substitute
    # comes on fresh.
    assert min(off.battery) < 0.5 and off.battery_lo is not None
    assert on.battery[0] == 1.0 and min(on.battery) == 1.0
    assert all(on.energy[k] <= on.energy[k + 1] for k in range(len(on.energy) - 1))
    assert on.energy[0] < 0.01  # energy counts from the substitute's own kick-off
    for spell in sig.tired_spells:
        if spell.player_id == "H12":
            assert spell.period == 2 and spell.t_start >= SUB_T
    stationary = by_id["A05"].series
    assert max(stationary.speed) < 0.05 and min(stationary.battery) == 1.0
