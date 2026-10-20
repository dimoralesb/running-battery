"""Estimator vs hidden truth for one match (BUILD_PLAN §3, run 3; PLAN §2.4).

``python -m runningbattery.validate.estimator data/synthetic/validation/v1001 [--player H08]``

Validation code: it reads ``truth.json``, which the estimator never does. Compares, per outfield
player-second on the pitch:

- the battery (weighted median and 10–90% band) with the hidden pools, the share of D′ left in
  the two pools together: fast_fraction × fast + (1 − fast_fraction) × slow;
- the tired flag (battery low) with the truth label ``tired`` (short-term tiredness only, PLAN
  §2.3 "Two truth labels"): precision and recall per player-second. The post-peak flag is scored
  the same way for information only: it is not a tired signal (PLAN §7, decision 12). Late-match
  wear (the tank) is a trend, scored with the whole-match load (BUILD_PLAN §3, run 3).
- the typical-pro chance of a low battery (``low_chance``, decision 14) by **calibration**: in
  seconds where it says p, is the player tired (``tired``) about p of the time? A reliability
  table by probability bin, the Brier score and the expected calibration error (the mean gap
  between the chance and the observed share, weighted by the seconds in each bin). The share of
  seconds with the hidden pools below ``LOW_BATTERY`` of D′ is shown next to it: the same
  threshold as the signal, in the generator's two-pool model. The raw chance (the share of the
  draws, ``low_chance_raw``) is scored next to the calibrated one, so the map's effect is visible.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from runningbattery.engine import params as EP
from runningbattery.engine.estimate import Estimate, compute
from runningbattery.engine.signals import red_zone, tired
from runningbattery.io import Match, read_match, read_truth
from runningbattery.schema import MatchTruth


@dataclass(frozen=True)
class Aligned:
    """Truth on the estimator's grid: (S, players), NaN / False where the player was off."""

    pools: np.ndarray
    tank: np.ndarray
    tired: np.ndarray
    outfield: np.ndarray  # (players,)
    cs: np.ndarray  # (players,) true values
    d_prime: np.ndarray


def align(est: Estimate, truth: MatchTruth, goalkeepers: set[str]) -> Aligned:
    s = est.seconds
    offset = {int(p): int(np.flatnonzero(s.period == p)[0]) for p in np.unique(s.period)}
    by_id = {p.player_id: p for p in truth.players}
    shape = s.on.shape
    pools, tank = np.full(shape, np.nan), np.full(shape, np.nan)
    flag = np.zeros(shape, dtype=bool)
    cs, dp = np.empty(shape[1]), np.empty(shape[1])
    for j, pid in enumerate(est.tracks.ids):
        p = by_id[pid]
        q = p.series
        rows = np.array([offset[h] + round(t) for h, t in zip(q.period, q.t, strict=True)])
        ff = p.params.fast_fraction
        pools[rows, j] = ff * np.array(q.fast_pool) + (1 - ff) * np.array(q.slow_pool)
        tank[rows, j] = q.tank
        flag[rows, j] = q.tired
        cs[j], dp[j] = p.params.cs, p.params.d_prime
    outfield = np.array([pid not in goalkeepers for pid in est.tracks.ids])
    return Aligned(pools, tank, flag, outfield, cs, dp)


def goalkeepers(match: Match) -> set[str]:
    return {p.id for team in match.metadata.teams for p in team.players if p.position == "GK"}


CALIBRATION_BINS = np.linspace(0.0, 1.0, 11)  # 0–0.1, 0.1–0.2, … 0.9–1.0


def calibration(
    chance: np.ndarray, real: np.ndarray, pools_low: np.ndarray
) -> list[dict[str, float]]:
    """Reliability table over flat arrays: per probability bin, the seconds, the mean chance,
    the share truly tired and the share with the hidden pools below the threshold."""
    edges = CALIBRATION_BINS
    k = np.clip(np.digitize(chance, edges[1:-1]), 0, len(edges) - 2)
    rows = []
    for b in range(len(edges) - 1):
        m = k == b
        n = int(m.sum())
        rows.append(
            {
                "lo": float(edges[b]),
                "hi": float(edges[b + 1]),
                "n": n,
                "chance": float(chance[m].mean()) if n else np.nan,
                "tired": float(real[m].mean()) if n else np.nan,
                "pools_low": float(pools_low[m].mean()) if n else np.nan,
            }
        )
    return rows


def calibration_scores(chance: np.ndarray, real: np.ndarray) -> dict[str, float]:
    """Brier score and expected calibration error (bins as in ``calibration``)."""
    rows = calibration(chance, real, real)
    n = max(len(chance), 1)
    ece = sum(r["n"] / n * abs(r["chance"] - r["tired"]) for r in rows if r["n"])
    return {
        "brier": float(np.mean((chance - real) ** 2)),
        "ece": float(ece),
        "chance_mean": float(chance.mean()),
    }


def format_calibration(rows: list[dict[str, float]]) -> str:
    lines = [f"  {'chance':>9} {'seconds':>9} {'mean':>6} {'tired':>6} {'pools<low':>9}"]
    for r in rows:
        if r["n"]:
            lines.append(
                f"  {r['lo']:.1f}–{r['hi']:.1f}  {r['n']:>9} {r['chance']:>6.3f} {r['tired']:>6.3f}"
                f" {r['pools_low']:>9.3f}"
            )
    return "\n".join(lines)


def keep_mask(est: Estimate, truth: Aligned) -> np.ndarray:
    """Outfield player-seconds on the pitch with a truth value: what every score uses."""
    return est.seconds.on & truth.outfield[None, :] & ~np.isnan(truth.pools)


def precision_recall(pred: np.ndarray, real: np.ndarray) -> tuple[float, float]:
    tp = float((pred & real).sum())
    return tp / max(int(pred.sum()), 1), tp / max(int(real.sum()), 1)


def scores(est: Estimate, truth: Aligned, low_battery: float = EP.LOW_BATTERY) -> dict[str, float]:
    """Battery vs pools and tired-moment precision and recall, outfield player-seconds."""
    s = est.seconds
    keep = keep_mask(est, truth)
    flag = tired(s, low_battery)
    _, post = red_zone(s, est.settings.peak_share, est.settings.peak_floor)
    real = truth.tired[keep]
    precision, recall = precision_recall(flag[keep], real)
    post_precision, post_recall = precision_recall(post[keep], real)
    out = {
        "player_s": float(keep.sum()),
        "tired_share": float(real.mean()),
        "flag_share": float(flag[keep].mean()),
        "precision": precision,
        "recall": recall,
        "post_peak_share": float(post[keep].mean()),
        "post_peak_precision": post_precision,
        "post_peak_recall": post_recall,
    }
    b, p = s.battery[keep], truth.pools[keep]
    out |= {
        "battery_mae": float(np.mean(np.abs(b - p))),
        "battery_bias": float(np.mean(b - p)),
        "battery_r": float(np.corrcoef(b, p)[0, 1]),
    }
    if s.battery_lo is not None and s.battery_hi is not None:
        lo, hi = s.battery_lo[keep], s.battery_hi[keep]
        out["band_coverage"] = float(np.mean((p >= lo) & (p <= hi)))
        out["band_width"] = float(np.mean(hi - lo))
    for name in ("low_chance", "low_chance_raw"):
        chance = getattr(s, name)
        if chance is not None:
            out |= {f"{name}_{k}": v for k, v in calibration_scores(chance[keep], real).items()}
    return out


def player_table(est: Estimate, truth: Aligned, pid: str, step_s: int = 300) -> str:
    """One player's battery and band next to the hidden pools, every ``step_s`` seconds."""
    s = est.seconds
    j = est.tracks.ids.index(pid)
    flag = tired(s, est.settings.low_battery)
    _, post = red_zone(s, est.settings.peak_share, est.settings.peak_floor)
    rows = np.flatnonzero(s.on[:, j])
    cs, dp = est.battery.cs[j], est.battery.d_prime[j]
    lines = [
        f"{pid}: true CS {truth.cs[j]:.2f} m/s, D′ {truth.d_prime[j]:.0f} m; estimated CS "
        f"{cs[1]:.2f} ({cs[0]:.2f}–{cs[2]:.2f}), D′ {dp[1]:.0f} ({dp[0]:.0f}–{dp[2]:.0f}) m",
        f"  {'half':>4} {'min':>5} {'battery':>8} {'band':>11} {'pools':>6} {'tank':>5}"
        f" {'flag':>5} {'truth':>6}",
    ]
    for r in rows[::step_s]:
        band = (
            f"{s.battery_lo[r, j]:.2f}–{s.battery_hi[r, j]:.2f}"
            if s.battery_lo is not None and s.battery_hi is not None
            else "-"
        )
        why = "tired" if flag[r, j] else "peak" if post[r, j] else ""
        lines.append(
            f"  {s.period[r]:>4} {s.t[r] / 60:>5.1f} {s.battery[r, j]:>8.2f} {band:>11}"
            f" {truth.pools[r, j]:>6.2f} {truth.tank[r, j]:>5.2f} {why:>5}"
            f" {'tired' if truth.tired[r, j] else '':>6}"
        )
    battery, pools = s.battery[rows, j], truth.pools[rows, j]
    lines.append(
        f"  lowest battery {battery.min():.2f}, lowest pools {np.nanmin(pools):.2f}; flagged tired"
        f" {flag[rows, j].mean():.1%} of seconds, truth tired {truth.tired[rows, j].mean():.1%}"
    )
    return "\n".join(lines)


BATTERY_COLOR, POOLS_COLOR, TANK_COLOR = "#2a78d6", "#eb6834", "#52514e"  # dataviz palette


def plot_player(est: Estimate, truth: Aligned, pid: str, path: Path | None = None, ax=None) -> None:
    """One player's battery, band, hidden pools and tired seconds (needs matplotlib): a PNG at
    ``path``, or drawn into ``ax``."""
    import matplotlib

    if ax is None:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = est.seconds
    j = est.tracks.ids.index(pid)
    flag = tired(s, est.settings.low_battery)
    # Playing minutes, added time included: the second half starts where the first ended.
    first_half = (s.period == 1).sum() / 60.0
    minute = s.t / 60.0 + np.where(s.period == 2, first_half, 0.0)
    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(11, 3.6))
    for half in (1, 2):
        rows = np.flatnonzero(s.on[:, j] & (s.period == half))
        if not len(rows):
            continue
        first = half == 1 or not (s.on[:, j] & (s.period == 1)).any()
        x = minute[rows]
        if s.battery_lo is not None and s.battery_hi is not None:
            ax.fill_between(
                x,
                s.battery_lo[rows, j],
                s.battery_hi[rows, j],
                color=BATTERY_COLOR,
                alpha=0.2,
                lw=0,
                label="battery 10–90% band" if first else None,
            )
        ax.plot(
            x, s.battery[rows, j], color=BATTERY_COLOR, lw=1.5, label="battery" if first else None
        )
        ax.plot(
            x,
            truth.pools[rows, j],
            color=POOLS_COLOR,
            lw=1.0,
            label="hidden pools" if first else None,
        )
        ax.plot(
            x,
            truth.tank[rows, j],
            color=TANK_COLOR,
            lw=0.8,
            ls="--",
            label="hidden tank" if first else None,
        )
    rows = np.flatnonzero(s.on[:, j])
    marks = (
        ("truth tired", -0.06, truth.tired, POOLS_COLOR),
        ("flagged tired", -0.12, flag, BATTERY_COLOR),
    )
    for name, y, x, c in marks:
        on = x[rows, j]
        ax.scatter(minute[rows][on], np.full(on.sum(), y), s=2, color=c, marker="|", label=name)
    ax.axvline(first_half, color="0.7", lw=0.8)
    ax.set_ylim(-0.16, 1.02)
    ax.set_xlabel("playing minute (added time included; line = half-time)")
    ax.set_ylabel("share of D′")
    ax.set_title(f"{pid}: battery vs hidden pools")
    ax.legend(loc="lower left", fontsize=7, ncol=3)
    if fig is not None:
        fig.tight_layout()
        fig.savefig(path, dpi=130)
        plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m runningbattery.validate.estimator", description=__doc__
    )
    parser.add_argument("folder", type=Path)
    parser.add_argument("--player", help="player for the battery table (default: most tired)")
    parser.add_argument("--plot", type=Path, help="also save the player's chart as a PNG")
    parser.add_argument("--mode", choices=["broadcast", "club"], default="broadcast")
    parser.add_argument("--k", type=float, default=EP.K)
    args = parser.parse_args(argv)
    match = read_match(args.folder)
    est = compute(match, mode=args.mode, k=args.k)
    truth = align(est, read_truth(args.folder), goalkeepers(match))
    for name, value in scores(est, truth).items():
        print(f"{name:>22} {value:.3f}")
    keep = keep_mask(est, truth)
    for name, label in (("low_chance_raw", "raw"), ("low_chance", "calibrated")):
        chance = getattr(est.seconds, name)
        if chance is not None:
            rows = calibration(
                chance[keep], truth.tired[keep], truth.pools[keep] < est.settings.low_battery
            )
            print(f"calibration of the typical-pro chance ({label}) against `tired`:")
            print(format_calibration(rows))
    pid = args.player
    if pid is None:
        share = np.where(truth.outfield, truth.tired.mean(axis=0), -1)
        pid = est.tracks.ids[int(np.argmax(share))]
    print(player_table(est, truth, pid))
    if args.plot:
        plot_player(est, truth, pid, args.plot)
        print(f"chart: {args.plot}")


if __name__ == "__main__":
    main()
