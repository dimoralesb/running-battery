"""The battery: a D′ balance per player (PLAN §3.2–3.3, decisions 2 and 9).

Above CS the balance drains by (v − CS) metres per second; below CS it refills towards D′ with
recharge time τ = k·D′/(CS − v), clipped to 30–900 s [Skiba2021; Jones2017, p.S76; Bellenger2025].
The refill uses the exact exponential step, so it does not depend on the frame rate. Over
half-time the balance refills standing still for ``HALF_TIME_S``.

**One-way correction.** If the balance would go below zero, the player has shown that D′ is
larger: D′ is raised by the shortfall and the balance stays at zero. D′ is never lowered and CS
never moves (PLAN §3.2).

**Per-player update (broadcast mode).** Each player gets ``N_DRAWS`` (CS, D′) draws from the
shared prior. Every draw runs its own battery, with the one-way correction. A draw whose D′ had to
be raised is contradicted by the running: its weight is exp(−½ (raise / (width · D′))²), a soft
penalty rather than a cut-off. The battery shown is the weighted median of the draws, with a
weighted 10–90% band, and the weighted share of the draws below ``LOW_BATTERY``: the chance that a
typical player of the prior's population would be that low after this running (decision 14).
Weights only use the running so far, so the battery at minute 30 does not
know what the player does at minute 60 (it works live).

Match data mostly gives a lower bound on capacity [Sutcliffe2025, Fig. 3; Mizelman2024, p.2064]:
draws with too much capacity are never contradicted, so for most players the band stays close to
the prior's. The main gain is an honest band per player.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass

import numpy as np

from secondwind.engine import params as P


@dataclass(frozen=True)
class BatteryResult:
    """Battery per player at each whole second (rows of ``seconds``)."""

    seconds: np.ndarray  # (S,) frame index of each recorded second
    median: np.ndarray  # (S, players) fraction of D′
    lo: np.ndarray | None  # (S, players) 10% band; None without draws (club mode, fallback)
    hi: np.ndarray | None
    low_chance: np.ndarray | None  # (S, players) weighted share of the draws below ``low``
    cs: np.ndarray  # (players, 3) weighted 10%, median, 90% of CS at the end of the match
    d_prime: np.ndarray  # (players, 3) the same for D′ after the correction


def prior_draws(
    player_id: str,
    n: int = P.N_DRAWS,
    seed: int = P.DRAW_SEED,
    prior: P.Prior = P.PRIORS[P.DEFAULT_PRIOR],
) -> np.ndarray:
    """(n, 2) draws of (CS, D′) from the shared prior, clipped as in the generator. Seeded by the
    player's id, so a player's draws do not depend on who else played."""
    rng = np.random.default_rng([seed, zlib.crc32(player_id.encode())])
    cs = np.clip(rng.normal(prior.cs_mean, prior.cs_sd, n), *prior.cs_range)
    dp = np.clip(rng.normal(prior.d_prime_mean, prior.d_prime_sd, n), *prior.d_prime_range)
    return np.stack([cs, dp], axis=1)


def tau(speed: np.ndarray, cs: np.ndarray, d_prime: np.ndarray, k: float) -> np.ndarray:
    """Recharge time below CS, τ = k·D′/(CS − v), clipped to ``TAU_RANGE`` (s)."""
    gap = np.maximum(cs - speed, 1e-9)
    return np.clip(k * d_prime / gap, *P.TAU_RANGE)


def step(
    bal: np.ndarray, dp: np.ndarray, v: np.ndarray, cs: np.ndarray, k: float, dt: float
) -> tuple[np.ndarray, np.ndarray]:
    """One time step of the balance ``bal`` (m) with the one-way correction; returns the new
    balance and D′. ``v`` NaN (off the pitch) leaves both unchanged."""
    off = np.isnan(v)
    v = np.where(off, 0.0, v)
    drained = bal - (v - cs) * dt
    refilled = dp - (dp - bal) * np.exp(-dt / tau(v, cs, dp, k))
    new = np.where(v > cs, drained, refilled)
    new_dp = dp + np.maximum(-new, 0.0)
    new = np.maximum(new, 0.0)
    return np.where(off, bal, new), np.where(off, dp, new_dp)


def weights(raise_m: np.ndarray, d_prime0: np.ndarray, width: float) -> np.ndarray:
    """Normalised weights of the draws (last axis) from how much D′ each had to be raised."""
    logw = -0.5 * (raise_m / (width * d_prime0)) ** 2
    w = np.exp(logw - logw.max(axis=-1, keepdims=True))
    return w / w.sum(axis=-1, keepdims=True)


def weighted_quantiles(values: np.ndarray, w: np.ndarray, qs: tuple[float, ...]) -> np.ndarray:
    """Weighted quantiles over the last axis: (..., len(qs)). The value where the cumulative
    weight first reaches q (no interpolation; 1e-9 absorbs rounding in the cumulative sum)."""
    order = np.argsort(values, axis=-1)
    v = np.take_along_axis(values, order, axis=-1)
    cw = np.cumsum(np.take_along_axis(w, order, axis=-1), axis=-1)
    cw /= cw[..., -1:]
    idx = [np.minimum((cw < q - 1e-9).sum(axis=-1), values.shape[-1] - 1) for q in qs]
    return np.stack([np.take_along_axis(v, i[..., None], axis=-1)[..., 0] for i in idx], axis=-1)


def run(
    speed: np.ndarray,
    period: np.ndarray,
    record: np.ndarray,
    cs: np.ndarray,
    d_prime: np.ndarray,
    k: float = P.K,
    width: float | None = P.PENALTY_WIDTH,
    low: float = P.LOW_BATTERY,
) -> BatteryResult:
    """Run the battery over a match.

    ``speed`` (frames, players), NaN off the pitch; ``period`` (frames,); ``record`` (frames,)
    bool, the frames to report. ``cs`` and ``d_prime`` are (players, draws). With one draw per
    player (club mode, or the fallback) there is no band; with several, ``width`` sets the soft
    penalty and the battery is the weighted median with a 10–90% band, and ``low_chance`` the
    weighted share of the draws whose balance is below ``low`` of their D′.
    """
    banded = cs.shape[1] > 1
    bal = d_prime.astype(float).copy()
    dp = bal.copy()
    rows = np.flatnonzero(record)
    med = np.empty((len(rows), cs.shape[0]))
    lo = np.empty_like(med) if banded else None
    hi = np.empty_like(med) if banded else None
    chance = np.empty_like(med) if banded else None
    qs = (P.BAND[0], 0.5, P.BAND[1])
    r = 0
    for f in range(len(speed)):
        if f > 0 and period[f] != period[f - 1]:  # half-time: rest standing still
            bal = dp - (dp - bal) * np.exp(-P.HALF_TIME_S / tau(np.zeros(1), cs, dp, k))
        bal, dp = step(bal, dp, speed[f][:, None], cs, k, P.DT)
        if r < len(rows) and rows[r] == f:
            level = bal / dp
            if banded:
                w = weights(dp - d_prime, d_prime, width)
                q = weighted_quantiles(level, w, qs)
                lo[r], med[r], hi[r] = q[:, 0], q[:, 1], q[:, 2]
                chance[r] = (w * (level < low)).sum(axis=-1)
            else:
                med[r] = level[:, 0]
            r += 1
    w = weights(dp - d_prime, d_prime, width) if banded else np.ones_like(dp)
    return BatteryResult(
        seconds=rows,
        median=med,
        lo=lo,
        hi=hi,
        low_chance=chance,
        cs=weighted_quantiles(cs, w, qs),
        d_prime=weighted_quantiles(dp, w, qs),
    )
