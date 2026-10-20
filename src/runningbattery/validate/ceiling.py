"""The ceiling for telling who is tired from positions (PLAN §3.3 "As built").

``python -m runningbattery.validate.ceiling data/synthetic/dev --matches 20``

Validation code: it reads ``truth.json``. For every outfield player who played the whole match,
the generator's own two-pool physiology (``sim.physiology``, with this match's effect sizes from
``truth.json`` ``settings``) is run on the speed the estimator sees, once for each of ``n`` hidden
values drawn from the population the match's players came from (``sim.rosters.true_params``; the
wider prior for a varied match). The share of draws that are tired at a second is
P(tired | running): what a detector could know if it had the generator exactly and only the
player's own values were unknown. Its best precision at a given recall is the ceiling for any
positions-only tired detector. The estimator's battery and its typical-pro low-battery chance
(raw: the calibration map keeps its order) are scored the same way, and so is the physiology
run with the player's true values (how much of the gap is the unknown player, and how much the
smoothed speed).
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np

from runningbattery import default_workers
from runningbattery.engine.estimate import compute
from runningbattery.io import read_match, read_truth
from runningbattery.schema import TrueParams
from runningbattery.sim.physiology import Physiology
from runningbattery.sim.rosters import true_params
from runningbattery.validate.estimator import align, goalkeepers

N_DRAWS = 200
RECALLS = (0.1, 0.3, 0.5)
DRAW_SEED = 1


def player_prior(settings: dict) -> dict | None:
    """The player prior a match was drawn from: ``params.VARY_PLAYERS`` as written into
    ``settings`` by a varied match (``output.prior_settings``), else None (the default prior)."""
    if not settings.get("varied"):
        return None
    out: dict = {}
    for key, value in settings.items():
        if not key.startswith("prior_"):
            continue
        name = key.removeprefix("prior_")
        if name.endswith(("_lo", "_hi")):
            base = f"{name[:-3]}_range"
            lo_hi = out.setdefault(base, [None, None])
            lo_hi[name.endswith("_hi")] = value
        else:
            out[name] = value
    return {k: tuple(v) if isinstance(v, list) else v for k, v in out.items()}


def tired_series(
    speed: np.ndarray,
    period: np.ndarray,
    t: np.ndarray,
    record: np.ndarray,
    params: list[TrueParams],
    settings: dict | None = None,
) -> np.ndarray:
    """(seconds, players) ``tired`` from the generator's physiology run on ``speed`` (frames,
    players), one column per entry of ``params``."""
    body = Physiology(params, np.random.default_rng(0), settings)
    out, current = [], int(period[0])
    for f in range(len(speed)):
        if period[f] != current:
            current = int(period[f])
            body.start_period(current)
        body.step(speed[f], float(t[f]))
        if record[f]:
            out.append(body.pools < body.s["tired_below"])
    return np.array(out)


def match_arrays(folder: Path, n: int = N_DRAWS, seed: int = DRAW_SEED) -> dict[str, np.ndarray]:
    """Flat arrays over the whole-match outfield player-seconds of one match: the truth label,
    P(tired | running), tired with the true values, the estimator's battery and its typical-pro
    low-battery chance."""
    match, truth = read_match(folder), read_truth(folder)
    est = compute(match)
    a = align(est, truth, goalkeepers(match))
    tr, s = est.tracks, est.seconds
    whole = [j for j in range(len(tr.ids)) if a.outfield[j] and s.on[:, j].all()]
    speed = np.nan_to_num(tr.speed[:, whole])
    rng = np.random.default_rng([seed, int(match.metadata.generator.seed)])
    prior = player_prior(truth.settings)
    draws = [true_params(rng, prior) for _ in range(n * len(whole))]
    sims = tired_series(
        np.repeat(speed, n, axis=1), tr.period, tr.t, tr.whole_second, draws, truth.settings
    )
    chance = sims.reshape(len(sims), len(whole), n).mean(axis=2)
    by_id = {p.player_id: p.params for p in truth.players}
    exact = tired_series(
        speed, tr.period, tr.t, tr.whole_second, [by_id[tr.ids[j]] for j in whole], truth.settings
    )
    raw = s.low_chance_raw
    low = raw[:, whole] if raw is not None else np.full_like(chance, np.nan)
    return {
        "real": a.tired[:, whole].ravel(),
        "ceiling": chance.ravel(),
        "exact": exact.ravel(),
        "battery": s.battery[:, whole].ravel(),
        "low_chance": low.ravel(),
    }


def best_precision(
    score: np.ndarray, real: np.ndarray, recalls: tuple[float, ...] = RECALLS
) -> dict[float, float]:
    """Best precision reachable at each recall by flagging the highest scores first (ties
    broken by order, so a coarse score is judged a little generously)."""
    order = np.argsort(-score, kind="stable")
    hit = real[order]
    tp = np.cumsum(hit)
    precision = tp / np.arange(1, len(hit) + 1)
    recall = tp / max(int(real.sum()), 1)
    return {
        r: float(precision[recall >= r].max()) if (recall >= r).any() else np.nan for r in recalls
    }


def summary(arrays: dict[str, np.ndarray], low_battery: float) -> dict:
    """Best precision at each recall for the ceiling and our signals; precision and recall of
    the true-value run and of our tired flag (battery below ``low_battery``)."""
    real = arrays["real"]

    def pr(pred: np.ndarray) -> tuple[float, float]:
        tp = float((pred & real).sum())
        return tp / max(int(pred.sum()), 1), tp / max(int(real.sum()), 1)

    out = {
        "player_s": int(len(real)),
        "tired_share": float(real.mean()),
        "ceiling": best_precision(arrays["ceiling"], real),
        "battery": best_precision(-arrays["battery"], real),
        "exact": pr(arrays["exact"]),
        "flag": pr(arrays["battery"] < low_battery),
    }
    if np.isfinite(arrays["low_chance"]).all():
        out["low_chance"] = best_precision(arrays["low_chance"], real)
    return out


def run(folders: list[Path], n: int = N_DRAWS, jobs: int | None = None) -> dict[str, np.ndarray]:
    """``match_arrays`` for each folder, in parallel, concatenated."""
    with ProcessPoolExecutor(max_workers=jobs or min(len(folders), default_workers())) as ex:
        parts = list(ex.map(partial(match_arrays, n=n), folders))
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def format_summary(out: dict) -> str:
    def cells(d: dict) -> str:
        return " / ".join(f"{v:.2f}" for v in d.values())

    rec = " / ".join(f"{r:g}" for r in RECALLS)
    return "\n".join(
        [
            f"{out['player_s']} whole-match outfield player-seconds, "
            f"tired {out['tired_share']:.1%}",
            f"best precision at recall {rec}:",
            f"  ceiling, P(tired | running)     {cells(out['ceiling'])}",
            f"  our battery                     {cells(out['battery'])}",
            *(
                [f"  our typical-pro low chance      {cells(out['low_chance'])}"]
                if "low_chance" in out
                else []
            ),
            f"physiology with the true values: precision {out['exact'][0]:.3f}, "
            f"recall {out['exact'][1]:.3f}",
            f"our tired flag: precision {out['flag'][0]:.2f}, recall {out['flag'][1]:.2f}",
        ]
    )


def main(argv: list[str] | None = None) -> None:
    from runningbattery.engine import params as EP

    parser = argparse.ArgumentParser(
        prog="python -m runningbattery.validate.ceiling", description=__doc__
    )
    parser.add_argument("folder", type=Path, help="a folder of match folders")
    parser.add_argument("--matches", type=int, default=20, help="the first N (default 20)")
    parser.add_argument("--draws", type=int, default=N_DRAWS)
    parser.add_argument("--jobs", type=int)
    args = parser.parse_args(argv)
    folders = sorted(p for p in args.folder.iterdir() if p.is_dir())[: args.matches]
    print(format_summary(summary(run(folders, args.draws, args.jobs), EP.LOW_BATTERY)))


if __name__ == "__main__":
    main()
