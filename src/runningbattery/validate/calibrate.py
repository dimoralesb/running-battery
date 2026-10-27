"""Fit the calibration map of the typical-pro chance (``engine/params.py``
``LOW_CHANCE_MAP``).

``python -m runningbattery.validate.calibrate data/synthetic/dev``

Validation code: it reads ``truth.json``. Run it on the dev seeds 1–60 only; the validation
seeds 1001–1050 are for scoring the map, never for fitting it (``validate.batch``).

The raw chance (the weighted share of the prior draws whose battery is below ``LOW_BATTERY``,
``low_chance_raw``) is binned: exactly 0, then steps of 0.05. A weighted isotonic regression
(pool adjacent violators) of the share of ``tired`` on the bins gives a non-decreasing step
function; each block of bins becomes one knot (its mean raw chance, its share tired), and the
engine interpolates linearly between knots. Outfield player-seconds on the pitch, as everywhere
in ``validate``.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from runningbattery import default_workers
from runningbattery.engine import params as EP
from runningbattery.engine.estimate import compute
from runningbattery.io import read_match, read_truth
from runningbattery.validate.estimator import align, goalkeepers, keep_mask

BIN_EDGES = np.linspace(0.0, 1.0, 21)  # (0, 0.05), [0.05, 0.1), … with 0 kept apart


def isotonic(y: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted non-decreasing least-squares fit of ``y`` (pool adjacent violators)."""
    blocks: list[list[float]] = []  # [value, weight, count]
    for yi, wi in zip(y.tolist(), w.tolist(), strict=True):
        blocks.append([yi, wi, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            v2, w2, n2 = blocks.pop()
            v1, w1, n1 = blocks.pop()
            blocks.append([(v1 * w1 + v2 * w2) / (w1 + w2), w1 + w2, n1 + n2])
    return np.concatenate([np.full(n, v) for v, _, n in blocks])


def binned(raw: np.ndarray, real: np.ndarray) -> list[tuple[int, float, float]]:
    """(seconds, mean raw chance, share tired) of each non-empty bin, in order."""
    k = np.where(raw <= 0.0, 0, 1 + np.clip(np.digitize(raw, BIN_EDGES[1:-1]), 0, 19))
    out = []
    for b in range(21):
        m = k == b
        if m.any():
            out.append((int(m.sum()), float(raw[m].mean()), float(real[m].mean())))
    return out


def fit_map(raw: np.ndarray, real: np.ndarray) -> tuple[tuple[float, float], ...]:
    """Knots (raw chance, calibrated chance) of the isotonic map, rounded to 3 decimals."""
    bins = binned(raw, real)
    n = np.array([b[0] for b in bins], dtype=float)
    x = np.array([b[1] for b in bins])
    fit = isotonic(np.array([b[2] for b in bins]), n)
    knots = []
    for v in np.unique(fit):
        m = fit == v
        knots.append((round(float(np.average(x[m], weights=n[m])), 3), round(float(v), 3)))
    return tuple(knots)


def match_chance(folder: Path) -> tuple[np.ndarray, np.ndarray]:
    """Raw typical-pro chance and the truth label over one match's outfield player-seconds."""
    match = read_match(folder)
    est = compute(match)
    if est.seconds.low_chance_raw is None:
        raise ValueError(f"{folder}: no typical-pro chance (broadcast mode with draws needed)")
    truth = align(est, read_truth(folder), goalkeepers(match))
    keep = keep_mask(est, truth)
    return est.seconds.low_chance_raw[keep], truth.tired[keep]


def run(folders: list[Path], jobs: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    with ProcessPoolExecutor(max_workers=jobs or min(len(folders), default_workers())) as ex:
        parts = list(ex.map(match_chance, folders))
    return np.concatenate([p[0] for p in parts]), np.concatenate([p[1] for p in parts])


def format_map(knots: tuple[tuple[float, float], ...]) -> str:
    rows = "".join(f"    ({x:.3f}, {y:.3f}),\n" for x, y in knots)
    return f"LOW_CHANCE_MAP = (\n{rows})"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m runningbattery.validate.calibrate", description=__doc__
    )
    parser.add_argument("folder", type=Path, help="the dev batch (seeds 1–60) only")
    parser.add_argument("--matches", type=int, help="only the first N")
    parser.add_argument("--jobs", type=int)
    args = parser.parse_args(argv)
    folders = sorted(p for p in args.folder.iterdir() if p.is_dir())[: args.matches]
    raw, real = run(folders, args.jobs)
    print(f"{len(folders)} matches, {len(raw)} outfield player-seconds, tired {real.mean():.2%}")
    print(f"  {'seconds':>9} {'raw':>6} {'tired':>6}")
    for n, x, y in binned(raw, real):
        print(f"  {n:>9} {x:>6.3f} {y:>6.3f}")
    print(f"settings: {EP.LOW_CHANCE_MAP_FOR}")
    print(format_map(fit_map(raw, real)))


if __name__ == "__main__":
    main()
