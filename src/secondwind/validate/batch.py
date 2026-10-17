"""Estimator vs hidden truth over many matches (BUILD_PLAN §3, runs 3 and 5).

``python -m secondwind.validate.batch data/synthetic/validation [--k 4] [--mode club]``

Validation code: it reads ``truth.json``. Runs the estimator on every match folder and pools the
outfield player-seconds (``validate.estimator``): battery against the hidden pools (error, bias,
correlation, 10–90% band coverage), the tired flag's precision and recall against ``tired``, the
calibration of the typical-pro chance, raw and calibrated (reliability table, Brier score,
expected calibration error), and late-match wear as a trend: the hidden tank against the estimator's
energy since kick-off (load), per player-second and at each whole-match player's last second.
Per-match values are summarised too (median and 10–90% range), because the varied batch draws
its own assumptions per match (PLAN §2.6, point 3).
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np

from secondwind import default_workers
from secondwind.engine import params as EP
from secondwind.engine.estimate import compute
from secondwind.engine.signals import tired
from secondwind.io import read_match, read_truth
from secondwind.sim import params as SP
from secondwind.validate.estimator import (
    align,
    calibration,
    calibration_scores,
    format_calibration,
    goalkeepers,
    keep_mask,
    precision_recall,
    scores,
)

FLAT = (
    "battery",
    "lo",
    "hi",
    "pools",
    "tired",
    "flag",
    "low_chance",
    "low_chance_raw",
    "energy",
    "tank",
)
CHANCES = (("low_chance_raw", "raw"), ("low_chance", "calibrated"))


def match_arrays(folder: Path, **kw) -> dict:
    """Flat arrays over one match's outfield player-seconds, its own scores, and each
    whole-match outfield player's energy and tank at their last second."""
    match = read_match(folder)
    est = compute(match, **kw)
    truth = align(est, read_truth(folder), goalkeepers(match))
    s = est.seconds
    keep = keep_mask(est, truth)
    band = s.battery_lo is not None and s.battery_hi is not None
    nan = np.full(s.battery.shape, np.nan)
    out = {
        "battery": s.battery[keep],
        "lo": (s.battery_lo if band else nan)[keep],
        "hi": (s.battery_hi if band else nan)[keep],
        "pools": truth.pools[keep],
        "tired": truth.tired[keep],
        "flag": tired(s, est.settings.low_battery)[keep],
        "low_chance": (s.low_chance if s.low_chance is not None else nan)[keep],
        "low_chance_raw": (s.low_chance_raw if s.low_chance_raw is not None else nan)[keep],
        "energy": s.energy[keep],
        "tank": truth.tank[keep],
    }
    whole = truth.outfield & s.on.all(axis=0)
    out["end_energy"] = s.energy[-1, whole]
    out["end_tank"] = truth.tank[-1, whole]
    out["scores"] = scores(est, truth)
    return out


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def pooled(parts: list[dict], low_battery: float = EP.LOW_BATTERY) -> dict:
    a = {k: np.concatenate([p[k] for p in parts]) for k in (*FLAT, "end_energy", "end_tank")}
    precision, recall = precision_recall(a["flag"], a["tired"])
    b, p = a["battery"], a["pools"]
    out: dict = {
        "matches": len(parts),
        "player_s": int(len(b)),
        "tired_share": float(a["tired"].mean()),
        "flag_share": float(a["flag"].mean()),
        "precision": precision,
        "recall": recall,
        "battery_mae": float(np.mean(np.abs(b - p))),
        "battery_bias": float(np.mean(b - p)),
        "battery_r": float(np.corrcoef(b, p)[0, 1]),
    }
    if np.isfinite(a["lo"]).all():
        out["band_coverage"] = float(np.mean((p >= a["lo"]) & (p <= a["hi"])))
        out["band_below"] = float(np.mean(p < a["lo"]))
        out["band_above"] = float(np.mean(p > a["hi"]))
        out["band_width"] = float(np.mean(a["hi"] - a["lo"]))
    for name, _ in CHANCES:
        if np.isfinite(a[name]).all():
            out |= {f"{name}_{k}": v for k, v in calibration_scores(a[name], a["tired"]).items()}
            out[f"calibration_{name}"] = calibration(a[name], a["tired"], a["pools"] < low_battery)
    # Late-match wear: the tank falls as work piles up; the load (energy since kick-off) is the
    # estimator's measure of that work (PLAN §2.3, "Two truth labels").
    out["late_share"] = float(np.mean(a["tank"] < SP.LATE_TANK_BELOW))
    out["load_vs_tank_rho"] = spearman(a["energy"], -a["tank"])
    out["end_load_vs_tank_rho"] = spearman(a["end_energy"], -a["end_tank"])
    per = {k: [pt["scores"].get(k, np.nan) for pt in parts] for k in parts[0]["scores"]}
    out["per_match"] = {
        k: tuple(float(x) for x in np.nanquantile(v, (0.1, 0.5, 0.9))) for k, v in per.items()
    }
    return out


def run(folders: list[Path], jobs: int | None = None, **kw) -> dict:
    with ProcessPoolExecutor(max_workers=jobs or min(len(folders), default_workers())) as ex:
        parts = list(ex.map(partial(match_arrays, **kw), folders))
    return pooled(parts)


def format_pooled(out: dict) -> str:
    skip = {"per_match", "matches", "player_s"}
    lines = [f"{out['matches']} matches, {out['player_s']} outfield player-seconds"]
    lines += [
        f"  {k:>24} {v:.3f}"
        for k, v in out.items()
        if k not in skip and not k.startswith("calibration_")
    ]
    for name, label in CHANCES:
        if f"calibration_{name}" in out:
            lines.append(f"calibration of the typical-pro chance ({label}) against `tired`:")
            lines.append(format_calibration(out[f"calibration_{name}"]))
    lines.append("per match, 10% / median / 90%:")
    for k in (
        "tired_share",
        "precision",
        "recall",
        "battery_mae",
        "band_coverage",
        "low_chance_raw_ece",
        "low_chance_ece",
    ):
        if k in out["per_match"]:
            lo, mid, hi = out["per_match"][k]
            lines.append(f"  {k:>24} {lo:.3f} / {mid:.3f} / {hi:.3f}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m secondwind.validate.batch", description=__doc__
    )
    parser.add_argument("folder", type=Path, help="a folder of match folders")
    parser.add_argument("--matches", type=int, help="only the first N")
    parser.add_argument("--mode", choices=["broadcast", "club"], default="broadcast")
    parser.add_argument("--k", type=float, default=EP.K)
    parser.add_argument("--prior", choices=sorted(EP.PRIORS), default=EP.DEFAULT_PRIOR)
    parser.add_argument("--jobs", type=int)
    parser.add_argument("--json", type=Path, help="also write the pooled results here")
    args = parser.parse_args(argv)
    folders = sorted(p for p in args.folder.iterdir() if p.is_dir())[: args.matches]
    out = run(folders, args.jobs, mode=args.mode, k=args.k, prior=args.prior)
    print(f"mode {args.mode}, k {args.k:g}, prior {args.prior}")
    print(format_pooled(out))
    if args.json:
        args.json.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
