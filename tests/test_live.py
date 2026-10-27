"""The live runner (decision 58): the engine's battery fed one frame at a time, a one-way speed
filter that never reads ahead, and the same output as the replay up to the filter's lag."""

import io
import json

import numpy as np
from test_engine import _match

from runningbattery.engine import params as P
from runningbattery.engine.battery import prior_draws, run
from runningbattery.engine.estimate import compute
from runningbattery.io import read_match, write_match
from runningbattery.live import LiveBattery, LiveSpeed
from runningbattery.live import run as live_run

HZ = round(P.FRAME_RATE_HZ)


def test_live_battery_equals_the_engines_battery():
    """Fed the same speeds frame by frame, the live battery gives the replay's battery, band and
    raw chance at every whole second, across half-time and with wear."""
    rng = np.random.default_rng(7)
    n, frames = 3, 400 * HZ
    speed = np.clip(rng.normal(3.5, 2.5, (frames, n)), 0, 9.5)
    speed[: 30 * HZ, 2] = np.nan  # a substitute, off at first
    period = np.where(np.arange(frames) < frames // 2, 1, 2)
    record = np.arange(frames) % HZ == 0
    draws = np.stack([prior_draws(f"P{j}", 60) for j in range(n)])
    cs, dp = draws[..., 0], draws[..., 1]
    batch = run(speed, period, record, cs, dp)
    live = LiveBattery(cs, dp, chance_map=None)
    med, lo, hi, chance = [], [], [], []
    for f in range(frames):
        live.push(int(period[f]), speed[f])
        if record[f]:
            m, a, b, raw, _ = live.read()
            med.append(m), lo.append(a), hi.append(b), chance.append(raw)
    np.testing.assert_allclose(np.array(med), batch.median, atol=1e-12)
    np.testing.assert_allclose(np.array(lo), batch.lo, atol=1e-12)
    np.testing.assert_allclose(np.array(hi), batch.hi, atol=1e-12)
    np.testing.assert_allclose(np.array(chance), batch.low_chance, atol=1e-12)


def test_live_speed_never_reads_ahead():
    """Changing the frames after frame k leaves every speed up to frame k unchanged."""
    rng = np.random.default_rng(3)
    path = np.cumsum(rng.normal(0, 0.3, (300, 2, 2)), axis=0)
    other = path.copy()
    other[200:] += 25.0  # a different future
    a, b = LiveSpeed(2), LiveSpeed(2)
    va = np.array([a.push(x) for x in path])
    vb = np.array([b.push(x) for x in other])
    np.testing.assert_array_equal(va[:200], vb[:200])
    assert not np.allclose(va[200:], vb[200:])


def test_live_speed_recovers_after_a_bad_frame():
    """A one-frame tracking jump is ignored, and the speed follows the player again after it (a
    held speed must not stay held: the caps compare a frame with the one measured before it)."""
    s = LiveSpeed(1)
    x = np.zeros((600, 1, 2))
    x[:, 0, 0] = np.concatenate([np.zeros(100), np.linspace(0, 6.0 * 50, 500)])  # then 6 m/s
    x[300, 0, 0] += 15.0  # one bad frame
    v = np.array([s.push(f) for f in x])[:, 0]
    assert v[450:].min() > 5.5 and v[450:].max() < 6.5


def test_live_run_matches_the_replay_and_never_opens_truth(tmp_path, monkeypatch):
    """End to end on a constructed match: the per-second JSON lines, a battery within a couple of
    points of the replay's, and no truth.json opened."""
    m = _match()
    write_match(tmp_path, m.metadata, m.frames, m.events)
    (tmp_path / "truth.json").write_text(json.dumps({"secret": True}))
    opened: list[str] = []
    real_open = io.open

    def spy(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", spy)
    monkeypatch.setattr(io, "open", spy)
    buf = io.StringIO()
    live = live_run(tmp_path, out=buf)
    monkeypatch.undo()
    assert not any(f.endswith("truth.json") for f in opened)
    lines = [json.loads(x) for x in buf.getvalue().splitlines()]
    assert lines and {"period", "t", "battery", "red_zone"} <= set(lines[0])
    est = compute(read_match(tmp_path))
    med = np.array([r["_med"] for r in live["rows"]])
    on = np.array([r["_on"] for r in live["rows"]]) & est.seconds.on
    assert np.abs(med - est.seconds.battery)[on].mean() < 0.02
