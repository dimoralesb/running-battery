"""Spacing: how close players stand to team-mates, opponents and the lines, in our matches and in
IDSSE [Bassek2025], measured the same way.

``uv run python -m runningbattery.sim.spacing --seeds 1-30 --idsse`` prints the table; ``sim.batch``
adds the same table to its report. IDSSE needs the ``calib`` extra the first time (floodlight);
its positions are then cached at 10 Hz next to the raw files, in the git-ignored
``data/raw/idsse/`` (nothing from IDSSE is committed).

Input per period: positions (frames, players, 2) at 10 Hz, NaN when a player is off the pitch;
the team of each player; whether the ball is alive in each frame; the pitch half-sizes. Per match
(``measure``), as percentages of on-pitch player-frames, split by in play and dead ball:

- nearest team-mate and nearest opponent within 1 m and within 0.5 m, and the median distance
  to the nearest opponent;
- episodes of a pair closer than 1 m (a spell of consecutive frames, cut where the ball goes
  dead or comes alive): the share of close pair-time in episodes longer than 5 s and 10 s, the
  95th percentile and the longest episode, s;
- players beyond the lines (more than 0, 1 and 3 m out), and the largest overshoot, m.

Our matches also get, at each restart pass, the nearest opponent to the spot and the share closer
than the legal distance [IFAB2025, Laws 13, 15, 17] (``restarts``). The 1 m, 0.5 m, 5 s, 10 s and
line thresholds are our choice.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from runningbattery import default_workers
from runningbattery.schema import EventType
from runningbattery.sim import params as P

CLOSE_M = (1.0, 0.5)
EPISODE_M = 1.0
EPISODE_S = (5.0, 10.0)
LINE_M = (0.0, 1.0, 3.0)
STATES = ("play", "dead")
BIN_M = 0.05  # histogram bin of the nearest-opponent distance, for its median
MAX_M = 120.0
CHUNK = 4000  # frames per block of pairwise distances
# Legal distance of opponents from the ball at a restart [IFAB2025]: free kick 9.15 m (Law 13),
# corner 9.15 m from the 1 m arc (Laws 1, 17), throw-in 2 m (Law 15).
LEGAL_M = {
    "free_kick": P.RESTART_DISTANCE,
    "corner": P.RESTART_DISTANCE + P.CORNER_ARC,
    "throw_in": P.THROW_IN_DISTANCE,
}
CACHE = "spacing_10hz.npz"


def _episodes(close: np.ndarray) -> np.ndarray:
    """Lengths (frames) of the True spells in each column of (frames, pairs)."""
    padded = np.zeros((close.shape[1], close.shape[0] + 2), dtype=np.int8)
    padded[:, 1:-1] = close.T
    edges = np.diff(padded, axis=1)
    return np.flatnonzero(edges.ravel() == -1) - np.flatnonzero(edges.ravel() == 1)


def period_counts(
    pos: np.ndarray, team: np.ndarray, alive: np.ndarray, half: tuple[float, float]
) -> dict:
    """Raw counts for one period (``measure`` turns them into the match figures)."""
    n_frames, n = pos.shape[:2]
    on = np.isfinite(pos).all(axis=2)
    same = team[:, None] == team[None, :]
    iu, ju = np.triu_indices(n, 1)
    pair_mate = same[iu, ju]
    states = {"play": alive, "dead": ~alive}
    out: dict = {
        "frames": {s: int((on & m[:, None]).sum()) for s in STATES for m in [states[s]]},
        "mate": {(s, c): 0 for s in STATES for c in CLOSE_M},
        "opp": {(s, c): 0 for s in STATES for c in CLOSE_M},
        "opp_hist": {s: np.zeros(int(MAX_M / BIN_M) + 1, dtype=np.int64) for s in STATES},
    }
    close = np.empty((n_frames, len(iu)), dtype=bool)
    for a in range(0, n_frames, CHUNK):
        p = pos[a : a + CHUNK]
        d = np.hypot(*(p[:, :, None, :] - p[:, None, :, :]).transpose(3, 0, 1, 2))
        d = np.where(np.isfinite(d), d, np.inf)
        d[:, np.arange(n), np.arange(n)] = np.inf
        close[a : a + CHUNK] = d[:, iu, ju] < EPISODE_M
        mate = np.where(same, d, np.inf).min(axis=2)
        opp = np.where(~same, d, np.inf).min(axis=2)
        o = on[a : a + CHUNK]
        for s in STATES:
            m = o & states[s][a : a + CHUNK, None]
            for c in CLOSE_M:
                out["mate"][s, c] += int((m & (mate < c)).sum())
                out["opp"][s, c] += int((m & (opp < c)).sum())
            bins = np.minimum(opp[m & np.isfinite(opp)] / BIN_M, MAX_M / BIN_M).astype(int)
            out["opp_hist"][s] += np.bincount(bins, minlength=len(out["opp_hist"][s]))
    for kind, cols in (("mate", pair_mate), ("opp", ~pair_mate)):
        for s in STATES:
            out[f"ep_{kind}", s] = _episodes(close[:, cols] & states[s][:, None])
    over = np.max(np.abs(pos) - np.array(half), axis=2)
    for s in STATES:
        m = on & states[s][:, None]
        out["over", s] = {line: int((m & (over > line)).sum()) for line in LINE_M}
    out["over_max"] = float(np.nanmax(np.where(on, over, np.nan))) if on.any() else 0.0
    return out


def measure(periods: list[tuple[np.ndarray, np.ndarray]], team: np.ndarray, half) -> dict:
    """The match figures (module docstring) from ``(pos, alive)`` per period. Shares in %."""
    counts = [period_counts(pos, team, alive, half) for pos, alive in periods]
    res: dict[str, float] = {}
    for s in STATES:
        frames = max(sum(c["frames"][s] for c in counts), 1)
        for kind in ("mate", "opp"):
            for close in CLOSE_M:
                hits = sum(c[kind][s, close] for c in counts)
                res[f"{kind}_{close:g}m_{s}"] = 100.0 * hits / frames
        hist = np.sum([c["opp_hist"][s] for c in counts], axis=0)
        res[f"opp_median_{s}"] = (
            float(np.searchsorted(np.cumsum(hist), hist.sum() / 2.0) + 0.5) * BIN_M
        )
        for kind in ("mate", "opp"):
            ep = np.concatenate([c[f"ep_{kind}", s] for c in counts]) / P.FRAME_RATE_HZ
            total = max(ep.sum(), 1e-9)
            for longer in EPISODE_S:
                res[f"ep_{kind}_gt{longer:g}s_{s}"] = 100.0 * ep[ep > longer].sum() / total
            res[f"ep_{kind}_p95_{s}"] = float(np.percentile(ep, 95)) if len(ep) else 0.0
            res[f"ep_{kind}_max_{s}"] = float(ep.max()) if len(ep) else 0.0
        for line in LINE_M:
            res[f"over_{line:g}m_{s}"] = 100.0 * sum(c["over", s][line] for c in counts) / frames
    res["over_max"] = max(c["over_max"] for c in counts)
    return res


def restarts(match) -> dict[str, list[float]]:
    """Nearest opponent (m) to the spot at each free kick, corner and throw-in pass of a
    ``SimMatch`` (noise-free positions)."""
    slot = {s.player.id: s.slot for s in match.spells}
    out: dict[str, list[float]] = {kind: [] for kind in LEGAL_M}
    for e in match.events:
        if e.type == EventType.PASS and e.subtype in out:
            taker = slot[e.player_id]
            frame = match.periods[e.period - 1].pos[round(e.t * P.FRAME_RATE_HZ)]
            opponents = frame[11:] if taker < 11 else frame[:11]
            spot = np.array([e.start.x, e.start.y])
            out[e.subtype].append(float(np.hypot(*(opponents - spot).T).min()))
    return out


def sim_measure(match) -> dict:
    """``measure`` on a ``SimMatch``'s noise-free positions, plus its ``restarts``."""
    periods = [(pf.pos, pf.alive) for pf in match.periods]
    res = measure(periods, np.repeat([0, 1], 11), (P.HALF_LENGTH, P.HALF_WIDTH))
    return res | {"restarts": restarts(match)}


def idsse_periods(folder: Path) -> tuple[list[tuple[np.ndarray, np.ndarray]], np.ndarray, tuple]:
    """An IDSSE match at 10 Hz: ``(pos, alive)`` per half, the team of each player (home 0,
    away 1) and the pitch half-sizes. Cached in the match folder (``CACHE``)."""
    from runningbattery.sim.idsse import SOURCE_HZ, resample

    cache = folder / CACHE
    if not cache.exists():
        from floodlight.io.dfl import read_position_data_xml

        xy, _, status, _, pitch = read_position_data_xml(
            folder / "positions.xml", folder / "info.xml"
        )
        arrays: dict[str, np.ndarray] = {"half": np.array([pitch.xlim[1], pitch.ylim[1]])}
        for k, seg in enumerate(xy):
            cols = [xy[seg][side].xy for side in ("Home", "Away")]
            n = min(len(c) for c in cols)
            pos = resample(np.concatenate([c[:n] for c in cols], axis=1))
            arrays[f"pos_{k}"] = pos.reshape(len(pos), -1, 2)
            code = np.asarray(status[seg].code)[:n]
            at = np.minimum(np.round(np.arange(len(pos)) * SOURCE_HZ / P.FRAME_RATE_HZ), n - 1)
            arrays[f"alive_{k}"] = code[at.astype(int)] == 1
            arrays["team"] = np.repeat([0, 1], [c.shape[1] // 2 for c in cols])
        np.savez_compressed(cache, **arrays)
    with np.load(cache) as data:
        n = sum(1 for key in data.files if key.startswith("pos_"))
        periods = [(data[f"pos_{k}"], data[f"alive_{k}"]) for k in range(n)]
        return periods, data["team"], tuple(data["half"].tolist())


def idsse_measures(cached_only: bool = False) -> list[dict]:
    """``measure`` on every downloaded IDSSE match (empty if none); with ``cached_only``, only
    the matches already cached at 10 Hz (no floodlight needed)."""
    from runningbattery.sim.idsse import RAW

    if not RAW.exists():
        return []
    out = []
    need = CACHE if cached_only else "positions.xml"
    for folder in sorted(p for p in RAW.iterdir() if (p / need).exists()):
        periods, team, half = idsse_periods(folder)
        out.append(measure(periods, team, half) | {"match_id": folder.name})
    return out


# --- Report ---------------------------------------------------------------------------------------

ROWS = [
    ("mate_1m_play", "team-mate within 1 m, in play", "%"),
    ("mate_1m_dead", "team-mate within 1 m, dead ball", "%"),
    ("mate_0.5m_play", "team-mate within 0.5 m, in play", "%"),
    ("mate_0.5m_dead", "team-mate within 0.5 m, dead ball", "%"),
    ("opp_1m_play", "opponent within 1 m, in play", "%"),
    ("opp_1m_dead", "opponent within 1 m, dead ball", "%"),
    ("opp_0.5m_play", "opponent within 0.5 m, in play", "%"),
    ("opp_0.5m_dead", "opponent within 0.5 m, dead ball", "%"),
    ("opp_median_play", "median nearest opponent, in play", "m"),
    ("opp_median_dead", "median nearest opponent, dead ball", "m"),
    ("ep_mate_gt5s_play", "team-mate <1 m time in episodes >5 s, in play", "%"),
    ("ep_mate_gt10s_play", "team-mate <1 m time in episodes >10 s, in play", "%"),
    ("ep_mate_p95_play", "team-mate <1 m episode p95, in play", "s"),
    ("ep_mate_max_play", "team-mate <1 m longest episode, in play", "s"),
    ("ep_mate_gt5s_dead", "team-mate <1 m time in episodes >5 s, dead", "%"),
    ("ep_mate_gt10s_dead", "team-mate <1 m time in episodes >10 s, dead", "%"),
    ("ep_mate_p95_dead", "team-mate <1 m episode p95, dead", "s"),
    ("ep_mate_max_dead", "team-mate <1 m longest episode, dead", "s"),
    ("ep_opp_gt5s_play", "opponent <1 m time in episodes >5 s, in play", "%"),
    ("ep_opp_p95_play", "opponent <1 m episode p95, in play", "s"),
    ("ep_opp_gt5s_dead", "opponent <1 m time in episodes >5 s, dead", "%"),
    ("ep_opp_p95_dead", "opponent <1 m episode p95, dead", "s"),
    ("over_0m_play", "beyond the lines, in play", "%"),
    ("over_1m_play", "beyond the lines by >1 m, in play", "%"),
    ("over_3m_play", "beyond the lines by >3 m, in play", "%"),
    ("over_0m_dead", "beyond the lines, dead ball", "%"),
    ("over_1m_dead", "beyond the lines by >1 m, dead ball", "%"),
    ("over_3m_dead", "beyond the lines by >3 m, dead ball", "%"),
    ("over_max", "largest overshoot", "m"),
]


def summarise(per_match: list[dict]) -> dict:
    """Mean and SD over matches of every figure; restarts pooled over matches."""
    out: dict = {"n": len(per_match)}
    for key, _, _ in ROWS:
        v = np.array([m[key] for m in per_match])
        out[key] = {"mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0}
    if per_match and "restarts" in per_match[0]:
        out["restarts"] = {}
        for kind, legal in LEGAL_M.items():
            d = np.concatenate([m["restarts"][kind] for m in per_match])
            out["restarts"][kind] = {
                "n": len(d),
                "legal_m": legal,
                "closer_pct": 100.0 * float(np.mean(d < legal)) if len(d) else 0.0,
                "median_m": float(np.median(d)) if len(d) else 0.0,
            }
    return out


def format_table(ours: dict, idsse: dict | None = None) -> str:
    head = f"  {'measure':<48}{'ours mean ± SD':>18}"
    lines = [head + (f"{'IDSSE':>10}" if idsse else "")]
    for key, label, unit in ROWS:
        d = ours[key]
        fmt = ".2f" if unit == "%" else ".1f"
        row = f"  {label:<48}{d['mean']:>10{fmt}} ± {d['sd']:<5{fmt}}"
        if idsse:
            row += f"{idsse[key]['mean']:>10{fmt}}"
        lines.append(row + f" {unit}")
    for kind, r in ours.get("restarts", {}).items():
        lines.append(
            f"  {kind}: {r['n']} passes, nearest opponent median {r['median_m']:.1f} m, "
            f"{r['closer_pct']:.1f}% closer than {r['legal_m']:.2f} m"
        )
    return "\n".join(lines)


def _sim_one(seed: int) -> dict:
    from runningbattery.sim.output import simulate

    return sim_measure(simulate(seed, f"spacing{seed:04d}"))


def main(argv: list[str] | None = None) -> None:
    from runningbattery.sim.batch import parse_seeds

    parser = argparse.ArgumentParser(
        prog="python -m runningbattery.sim.spacing", description=__doc__
    )
    parser.add_argument("--seeds", default="1-10", help="e.g. 1-30 (default 1-10)")
    parser.add_argument(
        "--jobs", type=int, help="worker processes (default: one per physical core)"
    )
    parser.add_argument("--idsse", action="store_true", help="also measure the IDSSE matches")
    args = parser.parse_args(argv)
    seeds = parse_seeds(args.seeds)
    with ProcessPoolExecutor(max_workers=args.jobs or min(len(seeds), default_workers())) as ex:
        ours = summarise(list(ex.map(_sim_one, seeds)))
    idsse = summarise(idsse_measures()) if args.idsse else None
    print(f"{len(seeds)} matches" + (f"; IDSSE {idsse['n']} matches" if idsse else ""))
    print(format_table(ours, idsse))


if __name__ == "__main__":
    main()
