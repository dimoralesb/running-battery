"""Validation tools (BUILD_PLAN §3, run 3): the calibration check of the typical-pro chance, the
fit of its calibration map, and the ceiling for positions-only tired detection. Constructed
inputs only."""

import numpy as np
import pytest

from secondwind.schema import TrueParams
from secondwind.sim import params as SP
from secondwind.sim.output import prior_settings
from secondwind.validate.calibrate import binned, fit_map, isotonic
from secondwind.validate.ceiling import best_precision, player_prior, tired_series
from secondwind.validate.estimator import calibration, calibration_scores

HZ = round(SP.FRAME_RATE_HZ)


def test_calibrated_chance_has_small_error_and_a_biased_one_does_not():
    """A chance that comes true p of the time gives a reliability table on the diagonal; the
    same outcomes scored with half the chance give an expected calibration error near its
    mean shortfall."""
    rng = np.random.default_rng(0)
    chance = rng.uniform(size=200_000)
    real = rng.uniform(size=chance.size) < chance
    rows = calibration(chance, real, real)
    assert [r["n"] > 0 for r in rows] == [True] * 10
    for r in rows:
        assert r["tired"] == pytest.approx(r["chance"], abs=0.01)
    good, bad = calibration_scores(chance, real), calibration_scores(chance / 2, real)
    assert good["ece"] < 0.01 and bad["ece"] == pytest.approx(0.25, abs=0.02)
    assert good["brier"] == pytest.approx(1 / 6, abs=0.005)  # E[p(1 − p)] for p uniform


def test_calibration_bins_hold_the_ends():
    rows = calibration(np.array([0.0, 0.05, 1.0]), np.array([0, 0, 1], bool), np.zeros(3, bool))
    assert rows[0]["n"] == 2 and rows[-1]["n"] == 1 and rows[-1]["tired"] == 1.0


def test_player_prior_reads_back_the_varied_prior():
    settings = {"varied": True, "tank_m": 1.0} | prior_settings(SP.VARY_PLAYERS)
    assert player_prior(settings) == SP.VARY_PLAYERS
    assert player_prior({"tank_m": 1.0}) is None


def test_best_precision_flags_the_highest_scores_first():
    score = np.array([0.9, 0.8, 0.7, 0.6, 0.1])
    real = np.array([True, False, True, False, False])
    out = best_precision(score, real, (0.5, 1.0))
    assert out[0.5] == 1.0 and out[1.0] == pytest.approx(2 / 3)


def test_tired_series_is_the_generator_physiology():
    """Running far above CS empties the pools (tired); a player standing still never is."""
    p = TrueParams(cs=4.1, d_prime=150.0, a0=7.4, s0=9.3, fast_fraction=0.45, tau_fast=20.0,
                   tau_slow=450.0)  # fmt: skip
    n = 90 * HZ
    speed = np.zeros((n, 2))
    speed[:, 0] = 7.0
    t = np.arange(n) / HZ
    record = np.arange(n) % HZ == 0
    out = tired_series(speed, np.ones(n, int), t, record, [p, p])
    assert out[-1, 0] and not out[:, 1].any() and not out[0, 0]


def test_isotonic_pools_violators_and_keeps_the_weighted_mean():
    y = np.array([0.1, 0.3, 0.2, 0.5, 0.4, 0.4])
    w = np.array([1.0, 1.0, 3.0, 2.0, 1.0, 1.0])
    fit = isotonic(y, w)
    assert np.all(np.diff(fit) >= 0)
    assert fit[1] == fit[2] == pytest.approx((0.3 + 0.6) / 4)  # one violator pooled by weight
    assert fit[3] == fit[4] == fit[5] == pytest.approx(1.8 / 4)
    assert np.average(fit, weights=w) == pytest.approx(np.average(y, weights=w))
    assert np.array_equal(isotonic(np.sort(y), w), np.sort(y))  # already in order: unchanged


def test_fit_map_recovers_a_chance_that_is_twice_too_high():
    """Seconds whose raw chance is p are tired p/2 of the time; most seconds sit at exactly 0
    and are never tired. The fitted knots are non-decreasing and close to p/2."""
    rng = np.random.default_rng(1)
    raw = np.concatenate([np.zeros(300_000), rng.uniform(0.0, 1.0, 400_000)])
    real = rng.uniform(size=raw.size) < raw / 2
    knots = fit_map(raw, real)
    xs, ys = np.array(knots).T
    assert knots[0] == (0.0, 0.0)
    assert np.all(np.diff(xs) > 0) and np.all(np.diff(ys) >= 0)
    assert np.allclose(ys, xs / 2, atol=0.02)
    assert [b[0] for b in binned(raw, real)][0] == 300_000  # exactly 0 is its own bin


def test_idsse_codes_take_the_nearest_earlier_source_frame():
    from secondwind.sim.idsse import _codes

    code = np.arange(10)  # 25 Hz: frames at 0, 0.04, … 0.36 s
    assert _codes(code, 4).tolist() == [0, 2, 5, 7]  # 10 Hz: 0, 0.1, 0.2, 0.3 s


def test_real_data_measures_on_a_constructed_match():
    """The comparison measures run on any io.Match: in the constructed match only the stationary
    players play the whole match, so they never drain, never reach a red zone and use almost no
    energy; the substituted home CF is left out."""
    from test_engine import _match

    from secondwind.validate.real import measure, summarise

    m = measure(_match())
    assert m["players"] == 19  # 22 outfield starters minus the substituted H11, minus 2 GKs
    assert min(m["battery_min"]) == 1.0 and max(m["red_spells"]) == 0
    assert max(m["energy"]) < 0.5 and m["tired_s"] == 0
    s = summarise([m, m])
    assert s["players"] == 38 and s["below_low_battery"] == 0.0
    assert s["energy_mean_sd"][0] == pytest.approx(np.mean(m["energy"]))
