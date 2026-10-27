"""Calibration tools: the batch statistics (speed and acceleration bands, effort counts, team
totals, running by phase, JSON report) and the IDSSE comparison. The IDSSE tests
skip when the data was never downloaded and derived here
(``python -m runningbattery.sim.idsse``)."""

import json

import numpy as np
import pytest

from runningbattery.sim import params as P
from runningbattery.sim.batch import (
    BAND_TOLERANCE,
    TEAM_TARGETS,
    build_report,
    format_report,
    main,
    run_batch,
)
from runningbattery.sim.idsse import load_derived, player_kinematics, resample
from runningbattery.sim.summary import (
    ACCEL_EDGES,
    SPEED_CAP,
    SPEED_EDGES,
    band_seconds,
    effort_count,
    kinematics,
    smooth,
)

SEEDS = [1, 2]


@pytest.fixture(scope="module")
def stats() -> list[dict]:
    return run_batch(SEEDS)


@pytest.fixture(scope="module")
def idsse() -> list[dict]:
    matches = load_derived()
    if not matches:
        pytest.skip("IDSSE not derived here (python -m runningbattery.sim.idsse)")
    return matches


def _straight(speed: float, seconds: float = 30.0, players: int = 1) -> np.ndarray:
    """(frames, players, 2) positions at a constant speed along x, 10 Hz."""
    t = np.arange(0.0, seconds, P.DT)
    xy = np.zeros((len(t), players, 2))
    xy[..., 0] = (speed * t)[:, None]
    return xy


# --- Statistics ----------------------------------------------------------------------------------


def test_kinematics_constant_speed():
    speed, acc = kinematics(smooth(_straight(6.0)))
    # Away from the ends, where the zero-lag filter has edge effects.
    assert np.allclose(speed[50:-50], 6.0, atol=0.01)
    assert np.allclose(acc[50:-50], 0.0, atol=0.01)
    seconds = band_seconds(speed, SPEED_EDGES)
    assert seconds[4] == pytest.approx(30.0)  # 6.0 m/s is in the 5.28–6.11 m/s band
    assert band_seconds(acc, ACCEL_EDGES).sum() == pytest.approx(30.0)


def test_kinematics_drops_tracking_errors():
    """A 30 m jump is a tracking error: those frames come back as NaN [Deutsch2025]."""
    xy = _straight(2.0)
    xy[150:, 0, 0] += 30.0
    speed, acc = kinematics(smooth(xy))
    assert np.isnan(speed[150]) and np.isnan(acc[150])
    assert np.nanmax(speed) <= SPEED_CAP
    assert np.isfinite(speed[:100]).all()
    # NaN frames are left out of the band seconds.
    assert band_seconds(speed, SPEED_EDGES).sum() < 30.0


def test_effort_count_needs_0_7_s():
    v = np.full(300, 3.0)
    v[10:20] = 7.5  # 1.0 s: counts
    v[50:56] = 7.5  # 0.6 s: too short
    v[100:130] = 8.0  # 3.0 s: counts once
    assert effort_count(v, "sprint") == 2
    a = np.zeros(300)
    a[200:210] = -4.0  # 1 s below -3 m/s²
    assert effort_count(-a, "high_decel") == 1


def test_batch_report(stats, tmp_path):
    rep = build_report(stats)
    assert rep["n"] == len(SEEDS)
    for key in ("speed_s_outfield", "speed_s_GK", "accel_s_outfield", "accel_s_GK"):
        assert sum(rep["bands"][key]["synthetic_pct"]) == pytest.approx(100.0)
    assert set(rep["team"]) == set(TEAM_TARGETS) | {"observed_distance"}
    assert rep["team"]["distance"]["target"] == TEAM_TARGETS["distance"][0]
    for pos, d in rep["positions"].items():
        assert d["n"] == len(SEEDS) * (2 if pos in ("CB", "FB", "WM") else 1) * 2
        assert {"off_pct", "se_pct"} <= set(d["distance"])
        assert d["top_speed"]["max"] < 12.0
    assert set(rep["phase_hid"]) == {"in_possession", "out_of_possession"}
    pct = sum(d["pct"] for d in rep["purposes"].values())
    assert pct == pytest.approx(100.0)
    text = format_report(rep)
    assert "Team totals" in text and "Time in band" in text
    json.dumps(rep)  # JSON-ready


def test_batch_cli_writes_json(tmp_path, capsys):
    out = tmp_path / "report.json"
    main(["--seeds", "3", "--json", str(out)])
    rep = json.loads(out.read_text())
    assert rep["seeds"] == [3] and "positions" in rep
    assert "Movement by position" in capsys.readouterr().out


def test_movement_near_targets(stats):
    """A coarse guard on the calibration (the full check is 30+ seeds with sim.batch): team
    distance within ±10% of Allen2025, and goalkeepers who really move (4,720 m, ±20%)."""
    rep = build_report(stats)
    assert abs(rep["team"]["distance"]["off_pct"]) < 10.0
    assert abs(rep["team"]["hid"]["off_pct"]) < 25.0
    assert abs(rep["positions"]["GK"]["distance"]["off_pct"]) < 20.0
    for pos, d in rep["positions"].items():
        if pos != "GK":
            assert 7.5 < d["top_speed"]["mean"] < 9.3, (pos, d["top_speed"])


# --- IDSSE ----------------------------------------------------------------------------------------


def test_resample_25_to_10_hz():
    t = np.arange(0.0, 10.0, 1 / 25)
    xy = np.stack([3.0 * t, np.zeros_like(t)], axis=1)[:, None, :]
    xy[100:110] = np.nan  # off the pitch for 0.4 s
    out = resample(xy)
    assert out.shape == (100, 1, 2)
    ok = np.isfinite(out[:, 0, 0])
    assert np.allclose(np.diff(out[ok, 0, 0])[:30] * P.FRAME_RATE_HZ, 3.0)
    assert not ok[40:44].any() and ok[:39].all() and ok[45:].all()


def test_player_kinematics_smooths_each_spell():
    """A substitute: two separate spells on the pitch, never joined across the gap."""
    xy = _straight(4.0, 60.0)[:, 0, :]
    xy[200:400] = np.nan
    spells = player_kinematics(xy)
    assert [len(v) for v, _ in spells] == [200, 200]
    for v, _ in spells:
        assert np.allclose(v[50:-50], 4.0, atol=0.01)


def test_idsse_bands_close_to_synthetic(stats, idsse):
    """Time in each speed band within ±3 percentage points of IDSSE, from our noisy
    tracking through the same pipeline."""
    rep = build_report(stats, idsse)
    assert len(rep["idsse_matches"]) == len(idsse)
    for group in ("outfield", "GK"):
        band = rep["bands"][f"speed_s_{group}"]
        assert sum(band["idsse_pct"]) == pytest.approx(100.0)
        diff = np.subtract(band["synthetic_pct"], band["idsse_pct"])
        assert np.all(np.abs(diff) <= BAND_TOLERANCE), (group, diff)
    for pos, d in rep["idsse_positions"].items():
        assert d["n"] >= 1 and 3000.0 < d["distance"] < 14000.0, pos


def test_calibrate_fits_the_surface_and_steps_inside_its_bounds():
    """Then (``sim.calibrate``): the least-squares surface recovers a known linear model
    from noisy rows, the Levenberg–Marquardt step stays in the trust region and the knobs'
    bounds, and with room to move it is the least-squares step, give or take the damping."""
    from runningbattery.sim import calibrate as C

    rng = np.random.default_rng(0)
    jac = np.array([[2.0, 0.0], [0.5, -1.0], [0.0, 1.5]])
    g0 = np.array([1.0, -2.0, 0.5])
    x = rng.uniform(-1.0, 1.0, (400, 2))
    gaps = g0 + x @ jac.T + rng.normal(0.0, 0.1, (400, 3))
    g0_fit, jac_fit, se0 = C.fit(x, gaps)
    assert np.allclose(g0_fit, g0, atol=0.03) and np.allclose(jac_fit, jac, atol=0.05)
    assert np.all(se0 < 0.02)
    knobs = [C.Knob("A", 0.0, 2.0, 0.1), C.Knob("B", 0.0, 2.0, 0.1)]
    centre, radius = np.array([1.0, 1.0]), np.array([0.1, 0.1])
    d = C.step(g0, jac, centre, radius, knobs, trust=10.0)
    best = np.linalg.lstsq(jac, -g0, rcond=None)[0]  # the undamped least-squares step
    assert np.sum((g0 + jac @ d) ** 2) < np.sum((g0 + jac @ best) ** 2) + 0.05
    d = C.step(g0, jac, centre, radius, knobs, trust=0.5)
    assert np.all(np.abs(d) <= 0.5 + 1e-9)
    tight = [C.Knob("A", 0.98, 1.02, 0.1), C.Knob("B", 0.0, 2.0, 0.1)]
    d = C.step(g0, jac, centre, radius, tight, trust=10.0)
    assert 0.98 - 1e-9 <= centre[0] + d[0] * radius[0] <= 1.02 + 1e-9


def test_dithering_counts_back_and_forth_in_play():
    """``calibrate.dither``: a player going 3 m out and back for 4 s is one episode; walking
    straight on, or the same back-and-forth with the ball dead, is none."""
    from runningbattery.sim import calibrate as C

    t = np.arange(200) / P.FRAME_RATE_HZ
    xy = np.zeros((200, 3, 2))
    xy[:, 0, 0] = 1.5 * np.sin(2 * np.pi * t / 1.0)  # 6 m a second, back and forth
    xy[:, 1, 0] = 1.5 * t  # straight on
    xy[:, 2, 0] = xy[:, 0, 0]
    xy[:, 2, 1] = 20.0
    alive = np.ones(200, dtype=bool)
    n, hours = C.dither(xy[:, :2], alive)
    assert n == 1 and hours == pytest.approx(2 * 20.0 / 3600.0)
    assert C.dither(xy[:, :1], np.zeros(200, dtype=bool))[0] == 0


def test_run_shape_counts_short_close_and_turn_back_runs():
    """``calibrate.run_shape``: from 1-s mean speeds, a 2-s run then a 4-s run back
    the other way 5 s later is two runs, one short, one close to the last and one turn-back; a
    player off the pitch (NaN) adds nothing."""
    from runningbattery.sim import calibrate as C

    speed = np.r_[np.full(10, 2.0), np.full(2, 7.0), np.full(5, 1.0), np.full(4, -7.0),
                  np.full(9, 1.0)]  # fmt: skip
    x = np.cumsum(np.repeat(speed, 10)) / 10.0
    xy = np.stack([np.c_[x, np.zeros_like(x)], np.full((len(x), 2), np.nan)], axis=1)
    hours, runs, short, close, back = C.run_shape(xy, [0, 1])
    assert (runs, short, close, back) == (2, 1, 1, 1)
    assert hours == pytest.approx(30 / 3600)
