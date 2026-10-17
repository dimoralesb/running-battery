"""Per-second signals from 10 Hz kinematics (PLAN §3.3): load, recent intensity, red-zone spells
and post-peak flags, and tired moments (battery low; the post-peak flag is separate, decision 12).

All rolling windows look back only (they work live) and stay inside a period: half-time is a
rest, so a window never spans it and a post-peak flag ends at half-time. At the start of a
player's time on the pitch a window holds what there is so far; only full windows can set or
reach a peak.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from secondwind.engine import params as P
from secondwind.engine.battery import BatteryResult
from secondwind.engine.preprocess import Tracks


def metabolic_power(speed: np.ndarray, accel: np.ndarray) -> np.ndarray:
    """Metabolic power, W/kg, from speed (m/s) and tangential acceleration (m/s²)
    [diPrampero2005, Eq. 1–4; Osgnach2010, Eq. 2–4; synthesis §3.3]."""
    es = np.clip(accel / P.G, -P.ES_LIMIT, P.ES_LIMIT)
    em = np.sqrt(es**2 + 1.0)
    ec = np.polyval(P.EC_POLY, es) * em * P.KT
    return ec * speed


@dataclass
class Seconds:
    """Signals at each whole second of the match (rows), for every player (columns)."""

    period: np.ndarray  # (S,)
    t: np.ndarray  # (S,) whole seconds since the period's kick-off
    on: np.ndarray  # (S, players)
    speed: np.ndarray  # mean over the last second, m/s
    power: np.ndarray  # mean over the last second, W/kg
    power_avg: dict[int, np.ndarray]  # rolling mean, W/kg, by window (s)
    energy: np.ndarray  # since kick-off, kJ/kg
    hsr: dict[int, np.ndarray]  # metres above HI_SPEED in the window, by window (s)
    full: dict[int, np.ndarray]  # the player was on the pitch for the whole window
    in_play: dict[int, np.ndarray]  # share of the window with the ball in play
    battery: np.ndarray
    battery_lo: np.ndarray | None
    battery_hi: np.ndarray | None
    low_chance: np.ndarray | None = None  # typical-pro chance of a battery below LOW_BATTERY


def _window_start(period: np.ndarray, t: np.ndarray, w: int) -> np.ndarray:
    """Row index of the second ``w`` s back, or of the period's first second."""
    rows = np.arange(len(t))
    return rows - np.minimum(w, t).astype(int)


def per_second(tr: Tracks, bat: BatteryResult) -> Seconds:
    rows = bat.seconds
    period, t = tr.period[rows], np.round(tr.t[rows]).astype(int)
    for p in np.unique(period):  # whole seconds 0, 1, 2 … in each period
        if not np.array_equal(t[period == p], np.arange((period == p).sum())):
            raise ValueError(f"period {p}: missing whole-second frames in the tracking")
    on10 = tr.on
    v = np.nan_to_num(tr.speed)
    step = v * P.DT
    kinds = {
        "dist": step,
        "hsr": np.where(v > P.HI_SPEED, step, 0.0),
        "energy": metabolic_power(v, np.nan_to_num(tr.accel)) * P.DT,
        "on_s": on10 * P.DT,
        "alive_s": (on10 & tr.alive[:, None]) * P.DT,
    }
    cum = {}
    for name, x in kinds.items():
        c = np.zeros_like(x)
        for p in np.unique(tr.period):  # restart at each kick-off
            m = tr.period == p
            c[m] = np.cumsum(x[m], axis=0)
        cum[name] = c[rows]
    total_energy = np.cumsum(kinds["energy"], axis=0)[rows] / 1000.0

    def over(name: str, w: int) -> np.ndarray:
        return cum[name] - cum[name][_window_start(period, t, w)]

    def per_on_s(name: str, w: int) -> np.ndarray:
        return over(name, w) / np.maximum(over("on_s", w), P.DT)

    windows = sorted(set(P.LOAD_WINDOWS_S) | set(P.HSR_WINDOWS_S))
    on = on10[rows]
    return Seconds(
        period=period,
        t=t,
        on=on,
        speed=np.where(on, over("dist", 1), np.nan),
        power=np.where(on, over("energy", 1), np.nan),
        power_avg={w: per_on_s("energy", w) for w in P.LOAD_WINDOWS_S},
        energy=total_energy,
        hsr={w: over("hsr", w) for w in P.HSR_WINDOWS_S},
        full={w: over("on_s", w) >= w - 0.5 * P.DT for w in windows},
        in_play={w: per_on_s("alive_s", w) for w in P.HSR_WINDOWS_S},
        battery=bat.median,
        battery_lo=bat.lo,
        battery_hi=bat.hi,
        low_chance=bat.low_chance,
    )


def red_zone(
    s: Seconds, share: float = P.PEAK_SHARE, floor: float = P.PEAK_FLOOR
) -> tuple[dict[int, np.ndarray], np.ndarray]:
    """Red-zone spells per window length, and the post-peak flag.

    A second is in a red-zone spell for window w when the full window's high-speed distance
    reaches ``share`` of the player's reference peak: their own best full window so far, but at
    least ``floor`` × the published mean peak (``PUBLISHED_PEAK_M_PER_MIN``). The post-peak flag
    is on during a spell and for ``POST_PEAK_HOLD_S`` after it, within the period."""
    hot: dict[int, np.ndarray] = {}
    post = np.zeros_like(s.on)
    rows = np.arange(len(s.t))[:, None]
    for w, pub, hold in zip(
        P.HSR_WINDOWS_S, P.PUBLISHED_PEAK_M_PER_MIN, P.POST_PEAK_HOLD_S, strict=True
    ):
        x = np.where(s.full[w] & s.on, s.hsr[w], -np.inf)
        best = np.maximum.accumulate(x, axis=0)
        ref = np.maximum(best, floor * pub * w / 60.0)
        hot[w] = (x >= share * ref) & np.isfinite(x)
        last = np.where(hot[w], rows, -(10**9))
        for p in np.unique(s.period):
            m = s.period == p
            last[m] = np.maximum.accumulate(last[m], axis=0)
        post |= (rows - last) <= hold
    return hot, post & s.on


def tired(s: Seconds, low_battery: float = P.LOW_BATTERY) -> np.ndarray:
    """Tired moments per second and player: the median battery below ``low_battery`` of the
    player's estimated D′ (PLAN §7, decision 12)."""
    return (s.battery < low_battery) & s.on


def spells(flag: np.ndarray) -> list[tuple[int, int]]:
    """(first, last) rows of each run of True in a 1-D flag."""
    edges = np.diff(np.concatenate([[0], flag.astype(np.int8), [0]]))
    starts, stops = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return list(zip(starts.tolist(), (stops - 1).tolist(), strict=True))
