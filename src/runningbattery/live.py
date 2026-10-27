"""The live runner (decision 58): the estimator fed one tracking frame at a time, as a stadium feed
would send them, with nothing from the future.

``python -m runningbattery.live <match folder> [--out live.jsonl] [--realtime] [--check]``

The replay (``engine.estimate``) smooths each half's positions forwards and backwards (a zero-lag
filter, ``sim.summary.smooth``), which needs the whole half. Live, the same 4th-order 1 Hz
Butterworth filter runs one way only, frame by frame (``scipy.signal.sosfilt`` with its state
kept), so a speed is known as soon as its frame arrives, a little behind the zero-lag one. Speed is
the backward difference of the filtered position; a frame over the replay's speed or acceleration
caps keeps the speed before it. A player missing from a frame keeps his last position. Who is on
the pitch comes from the line-ups and substitutions at their times, as in the replay.

The battery is the engine's own: ``engine.battery.step`` each frame for every (CS, D′) draw, with
wear, the one-way correction and the soft penalty, and at each whole second the weighted median,
the 10–90% band and the typical-pro chance (raw and calibrated). Fed the replay's speeds it gives
the replay's battery exactly (tests/test_live.py). The hardest minutes (red zone) are the engine's
rule, computed second by second from the high-speed distance so far, so a spell is reported at the
second it starts.

Each whole second writes one JSON line: ``{"period", "t", "battery": {id: [median, lo, hi,
chance]}, "red_zone": [ids whose spell started this second]}``. ``--realtime`` paces the frames at
10 Hz. ``--check`` also runs the replay on the same match and prints how far the live battery is
from it, how far behind the live speed is, how long each second's update took, and whether the
hardest-minutes spells agree.

Not here: the connection to a tracking provider's feed and to a broadcaster's graphics, and the
commentary, which the agents write and the Verifier checks per moment (``agents.feed``).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi

from runningbattery.engine import params as P
from runningbattery.engine.battery import prior_draws, step, tau, weighted_quantiles, weights
from runningbattery.engine.signals import calibrate_chance
from runningbattery.io import TRACKING, _read_jsonl
from runningbattery.schema import MatchMetadata, TrackingFrame
from runningbattery.sim.summary import ACCEL_CAP, FILTER_HZ, FILTER_ORDER, SPEED_CAP

SOS = butter(FILTER_ORDER, FILTER_HZ, fs=P.FRAME_RATE_HZ, output="sos")


def frames(folder: Path) -> Iterator[TrackingFrame]:
    """The tracking frames in order, read one line at a time (the stand-in for a live feed)."""
    yield from _read_jsonl(folder / TRACKING, TrackingFrame)


def players(meta: MatchMetadata) -> list[str]:
    """Every player who played, starters first, in metadata order (as ``engine.preprocess``)."""
    came_on = {sub.player_in for sub in meta.substitutions}
    return [p.id for team in meta.teams for p in team.players if p.starter or p.id in came_on]


def on_pitch(meta: MatchMetadata, ids: list[str]):
    """A function (period, t) -> (players,) bool, the replay's rule (``engine.preprocess``)."""
    start = {p.id: (1, 0.0) for team in meta.teams for p in team.players if p.starter}
    stop: dict[str, tuple[int, float]] = {}
    for sub in meta.substitutions:
        stop[sub.player_out] = (sub.period, sub.t)
        start[sub.player_in] = (sub.period, sub.t)
    a = np.array([start[i][0] * 1e6 + start[i][1] for i in ids])
    b = np.array([stop.get(i, (3, 0.0))[0] * 1e6 + stop.get(i, (3, 0.0))[1] for i in ids])
    return lambda period, t: (period * 1e6 + t >= a) & (period * 1e6 + t < b)


class LiveSpeed:
    """One-way filtered positions and backward-difference speed, frame by frame."""

    def __init__(self, n: int):
        self.n = n
        self.reset()

    def reset(self) -> None:  # each kick-off: the filters start again
        self.state: np.ndarray | None = None  # (sections, 2, players, 2)
        self.last_raw = np.full((self.n, 2), np.nan)
        self.last_xy: np.ndarray | None = None
        self.speed = np.zeros(self.n)  # what is reported
        self.measured = np.zeros(self.n)  # the last frame's own speed, capped or not

    def push(self, xy: np.ndarray) -> np.ndarray:
        """``xy`` (players, 2), NaN for a player not in the frame; returns speed (players,)."""
        raw = np.where(np.isnan(xy), self.last_raw, xy)
        new = ~np.isnan(raw[:, 0]) & np.isnan(self.last_raw[:, 0])  # first seen this period
        self.last_raw = raw
        x = np.nan_to_num(raw)
        if self.state is None:
            self.state = np.zeros((SOS.shape[0], 2, self.n, 2))
        if new.any():  # start each new player's filter at rest at his first position
            zi = sosfilt_zi(SOS)[:, :, None, None] * x[None, None, :, :]
            self.state[:, :, new] = zi[:, :, new]
        out, self.state = sosfilt(SOS, x[None], axis=0, zi=self.state)
        f = out[0]
        if self.last_xy is None:
            v = np.zeros(self.n)
        else:
            v = np.hypot(*(f - self.last_xy).T) * P.FRAME_RATE_HZ
            v = np.where(new, 0.0, v)
        # the caps compare a frame with the one measured before it (not with a held value, which
        # would hold the speed for good after one bad frame)
        acc = (v - self.measured) * P.FRAME_RATE_HZ
        bad = (v > SPEED_CAP) | (np.abs(acc) > ACCEL_CAP)
        self.measured = v
        self.speed = np.where(bad, self.speed, v)
        self.last_xy = f
        return self.speed.copy()


class LiveBattery:
    """``engine.battery.run``, one frame at a time: the same steps, the same output per second."""

    def __init__(
        self,
        cs: np.ndarray,
        d_prime: np.ndarray,
        k: float = P.K,
        width: float = P.PENALTY_WIDTH,
        low: float = P.LOW_BATTERY,
        wear: tuple[float, float, float] = (P.WEAR_ALPHA, P.WEAR_SCALE_M, P.WEAR_HALF_KEEP),
        chance_map: tuple | None = P.LOW_CHANCE_MAP,
    ):
        self.cs, self.d0, self.k, self.width, self.low = cs, d_prime, k, width, low
        self.alpha, self.scale, self.keep = wear
        self.bal = d_prime.astype(float).copy()
        self.dp = self.bal.copy()
        self.work = np.zeros_like(self.bal)
        self.period: int | None = None
        self.chance_map = chance_map

    def push(self, period: int, v: np.ndarray) -> None:
        """One frame: ``v`` (players,) m/s, NaN off the pitch."""
        if self.period is not None and period != self.period:  # half-time: rest standing still
            self.bal = self.dp - (self.dp - self.bal) * np.exp(
                -P.HALF_TIME_S / tau(np.zeros(1), self.cs, self.dp, self.k)
            )
            self.work *= self.keep
        self.period = period
        v = v[:, None]
        if self.alpha:
            self.work += np.where(np.isnan(v), 0.0, np.maximum(v - self.cs, 0.0)) * P.DT
            slow = 1.0 + self.alpha * (1.0 - np.exp(-self.work / self.scale))
        else:
            slow = 1.0
        self.bal, self.dp = step(self.bal, self.dp, v, self.cs, self.k, P.DT, slow)

    def read(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """(median, lo, hi, chance raw, chance calibrated) per player, now."""
        level = self.bal / self.dp
        w = weights(self.dp - self.d0, self.d0, self.width)
        q = weighted_quantiles(level, w, (P.BAND[0], 0.5, P.BAND[1]))
        raw = (w * (level < self.low)).sum(axis=-1)
        cal = calibrate_chance(raw, self.chance_map) if self.chance_map is not None else raw
        return q[:, 1], q[:, 0], q[:, 2], raw, cal


@dataclass
class LiveRedZone:
    """The engine's red-zone rule (``engine.signals.red_zone``) second by second: a window's
    high-speed distance at ``PEAK_SHARE`` of the player's best full window so far (at least
    ``PEAK_FLOOR`` × the published mean peak)."""

    n: int
    cum_hsr: list[np.ndarray] = field(default_factory=list)  # this period, per whole second
    cum_on: list[np.ndarray] = field(default_factory=list)
    best: dict[int, np.ndarray] = field(default_factory=dict)
    hot: dict[int, np.ndarray] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.frame_hsr = np.zeros(self.n)
        self.frame_on = np.zeros(self.n)
        for w in P.HSR_WINDOWS_S:
            self.best[w] = np.full(self.n, -np.inf)
            self.hot[w] = np.zeros(self.n, dtype=bool)

    def kick_off(self) -> None:
        self.cum_hsr, self.cum_on = [], []
        self.frame_hsr[:] = 0.0
        self.frame_on[:] = 0.0

    def push(self, v: np.ndarray, on: np.ndarray) -> None:
        s = np.nan_to_num(v) * P.DT
        self.frame_hsr += np.where(np.nan_to_num(v) > P.HI_SPEED, s, 0.0)
        self.frame_on += on * P.DT

    def second(self, t: int, on: np.ndarray) -> np.ndarray:
        """At a whole second (frame t of the period's whole seconds): the players whose spell
        starts now, in any window."""
        self.cum_hsr.append(self.frame_hsr.copy())
        self.cum_on.append(self.frame_on.copy())
        r = len(self.cum_hsr) - 1
        started = np.zeros(self.n, dtype=bool)
        for w, pub in zip(P.HSR_WINDOWS_S, P.PUBLISHED_PEAK_M_PER_MIN, strict=True):
            back = r - min(w, t)
            hsr = self.cum_hsr[r] - self.cum_hsr[back]
            full = (self.cum_on[r] - self.cum_on[back]) >= w - 0.5 * P.DT
            x = np.where(full & on, hsr, -np.inf)
            self.best[w] = np.maximum(self.best[w], x)
            ref = np.maximum(self.best[w], P.PEAK_FLOOR * pub * w / 60.0)
            now = (x >= P.PEAK_SHARE * ref) & np.isfinite(x)
            started |= now & ~self.hot[w]
            self.hot[w] = now
        return started


def run(folder: Path, realtime: bool = False, out=None) -> dict:
    """Stream a match folder through the live estimator; returns timings and the per-second
    output as arrays (for ``check``)."""
    meta = MatchMetadata.model_validate_json((folder / "metadata.json").read_text())
    ids = players(meta)
    col = {pid: j for j, pid in enumerate(ids)}
    # broadcast mode: each player's 200 (CS, D′) draws from the typical-pro prior, as the replay
    draws = np.stack([prior_draws(i, P.N_DRAWS, prior=P.PRIORS[P.DEFAULT_PRIOR]) for i in ids])
    cs, dp = draws[..., 0], draws[..., 1]
    speed, bat, red = LiveSpeed(len(ids)), LiveBattery(cs, dp), LiveRedZone(len(ids))
    pitch = on_pitch(meta, ids)
    rows: list[dict] = []
    second_ms: list[float] = []
    live_v: list[np.ndarray] = []
    period = None
    spent = 0.0  # ms of work since the last whole second (its ten frames)
    t0 = time.perf_counter()
    for k, f in enumerate(frames(folder)):
        tick = time.perf_counter()
        if f.period != period:
            speed.reset()
            red.kick_off()
            period = f.period
        xy = np.full((len(ids), 2), np.nan)
        for p in f.players:
            xy[col[p.id]] = (p.x, p.y)
        on = pitch(f.period, f.t)
        v = np.where(on, speed.push(xy), np.nan)
        live_v.append(v)
        bat.push(f.period, v)
        red.push(v, on)
        whole = round(f.t * P.FRAME_RATE_HZ) % round(P.FRAME_RATE_HZ) == 0
        if whole:
            ts = int(round(f.t))
            med, lo, hi, raw, cal = bat.read()
            started = red.second(ts, on)
            row = {
                "period": f.period,
                "t": ts,
                "battery": {
                    ids[j]: [
                        round(float(med[j]), 3),
                        round(float(lo[j]), 3),
                        round(float(hi[j]), 3),
                        round(float(cal[j]), 3),
                    ]
                    for j in np.flatnonzero(on)
                },
                "red_zone": [ids[j] for j in np.flatnonzero(started & on)],
            }
            rows.append(row | {"_med": med, "_on": on, "_hot": started})
            if out is not None:
                out.write(json.dumps(row) + "\n")
        spent += (time.perf_counter() - tick) * 1000.0
        if whole:
            second_ms.append(spent)  # one second of match: its frames and the output
            spent = 0.0
        if realtime:
            time.sleep(max(0.0, (k + 1) * P.DT - (time.perf_counter() - t0)))
    return {
        "ids": ids,
        "rows": rows,
        "second_ms": np.array(second_ms),
        "speed": np.array(live_v),
        "seconds": time.perf_counter() - t0,
    }


def check(folder: Path, live: dict) -> dict:
    """The live output against the replay's (``engine.estimate.compute``) on the same match."""
    from runningbattery.engine.estimate import compute
    from runningbattery.engine.signals import red_zone
    from runningbattery.io import read_match

    est = compute(read_match(folder))
    s = est.seconds
    assert est.tracks.ids == live["ids"]
    med = np.array([r["_med"] for r in live["rows"]])
    on = np.array([r["_on"] for r in live["rows"]]) & s.on
    gap = np.abs(med - s.battery)[on]
    # speed: how far behind the zero-lag speed the live one runs (the lag of best correlation)
    v_live, v_rep = np.nan_to_num(live["speed"]), np.nan_to_num(est.tracks.speed)
    lags = range(0, 31)
    corr = [np.corrcoef(v_rep[: len(v_rep) - L].ravel(), v_live[L:].ravel())[0, 1] for L in lags]
    lag = int(np.argmax(corr))
    # hardest minutes: spell starts, live against the replay
    hot, _ = red_zone(s)
    rep_any = np.logical_or.reduce(list(hot.values()))
    rep_start = rep_any & ~np.vstack([np.zeros((1, rep_any.shape[1]), bool), rep_any[:-1]])
    live_start = np.array([r["_hot"] for r in live["rows"]])
    matched = []
    for j in range(rep_start.shape[1]):
        for r in np.flatnonzero(rep_start[:, j]):
            near = np.flatnonzero(live_start[max(r - 30, 0) : r + 31, j])
            matched.append(int(near.size > 0))
    return {
        "player_seconds": int(on.sum()),
        "battery_gap_mean_pts": float(gap.mean() * 100),
        "battery_gap_p95_pts": float(np.quantile(gap, 0.95) * 100),
        "battery_gap_max_pts": float(gap.max() * 100),
        "speed_lag_s": lag * P.DT,
        "speed_corr_at_lag": float(corr[lag]),
        "update_ms_mean": float(live["second_ms"].mean()),
        "update_ms_p99": float(np.quantile(live["second_ms"], 0.99)),
        "match_minutes": len(live["rows"]) / 60.0,
        "run_seconds": live["seconds"],
        "red_zone_spells_replay": len(matched),
        "red_zone_spells_found_live_within_30s": int(sum(matched)),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m runningbattery.live", description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path, help="write the per-second JSON lines here")
    parser.add_argument("--realtime", action="store_true", help="pace the frames at 10 Hz")
    parser.add_argument("--check", action="store_true", help="compare with the replay")
    parser.add_argument("--json", type=Path, help="write the check's numbers here")
    args = parser.parse_args(argv)
    out = args.out.open("w") if args.out else (sys.stdout if not args.check else None)
    live = run(args.folder, args.realtime, out)
    if args.out:
        out.close()
    if args.check:
        result = check(args.folder, live)
        for k, v in result.items():
            print(f"{k:>40} {v:.3f}" if isinstance(v, float) else f"{k:>40} {v}")
        if args.json:
            args.json.write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
