"""Calibrate the generator's tuned knobs to the reference data, by algorithm, not by hand:
``python -m runningbattery.sim.calibrate --rounds 3 --json out.json`` (decision 42).

The method of simulated moments (our implementation): pick the knobs (``KNOBS``) that minimise
the sum of squared, tolerance-scaled gaps between the batch statistics of simulated matches and
their targets (``moment_targets``): distance, high-speed running and sprint
distance per position (synthesis §4.2), running and high-speed running by phase [Allen2026b],
event counts (``summary.TARGETS``), and the outfield speed bands and "dithering" (``dither``) of
IDSSE [Bassek2025]. A gap of
1 is the edge of its tolerance, so the loss counts how many tolerances off the batch is.

A match takes about 10 s and its statistics are noisy (one match's sprint distance per position
varies by a quarter), so the loss is never evaluated point by point. Each round:

1. Around the current knobs, a scrambled Sobol design of ``--design`` points spread over
   ± ``radius`` of each knob (``scipy.stats.qmc``), plus the centre, each point simulated on its
   own ``--seeds-per-point`` seeds (all distinct, from ``SEED_BASE``: the level is averaged over
   every match of the round, not over one small seed set's rosters).
2. A linear response surface of every moment on the scaled knobs, by least squares over all the
   matches of the round: the gaps at the centre and their Jacobian, each with its standard error.
3. A Levenberg–Marquardt step on that surface: bounded linear least squares
   (``scipy.optimize.lsq_linear``) with a damping term and a trust region of ``TRUST`` radii,
   inside the knobs' bounds.

The next round is centred on the step's knobs, so its fitted gaps at the centre check the last
round's prediction. A round whose loss at the centre is worse than the best round's rejects that
step: the next step is taken again from the best round's surface, with half the trust region (a
trust-region method; decision 42's first run went 62 → 43 → 101 → 31 without it). The design
radius shrinks when the steps get small. The result is a set of knob
values to write into ``params.py`` (by hand, with the decision's comment), then judged on the
usual 120-seed ``sim.batch`` (seeds 1–120, never used here). Fatigue, tempo and substitutions
are on, as in ``simulate``. ``--start`` continues from an earlier run's result;
``--line-search`` instead backtracks along an earlier run's last step (``line_search``).

Where it stops: decision 42 ran 3 + 3 + 2 rounds and a line search (about 4,000 matches). The loss
fell from 62 (the hand-tuned values) to about 29 on the calibration seeds; after that, steps the
surface predicted at 10–13 came out at 27–43, and the line search's points differed by less than
the noise of 64 seeds (central midfielders' sprint distance alone moved 2 tolerances between seed
sets). What is left: ball in play (60% against 55%) and the running while the ball is dead
(−10%), which no knob here moves, and central midfielders' sprint distance (+15–20% with their
high-speed running on target: one work rate cannot fit both).
"""

from __future__ import annotations

import argparse
import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import lsq_linear
from scipy.stats import qmc

from runningbattery import default_workers
from runningbattery.schema import Position
from runningbattery.sim import params as P
from runningbattery.sim.batch import (
    PHASE_HID_TARGETS,
    PHASE_TARGETS,
    POSITION_TARGETS,
)
from runningbattery.sim.summary import (
    SPEED_CAP,
    SPEED_EDGES,
    SPEED_LABELS,
    TARGETS,
    band_seconds,
    kinematics,
    smooth,
)

SEED_BASE = 10001  # calibration seeds; the 120-seed check uses 1–120
TRUST = 1.5  # largest step, in design radii (the design spans ±1)
DAMPING = 0.05  # Levenberg–Marquardt damping, per scaled knob, in loss units
SHRINK = 0.6  # radius factor after a round whose step stayed within half the trust region
# "Dithering": a 4-s window in play in which a player's path is over 10 m and his net move under
# 2 m, counted as episodes (runs of such windows), per in-play player-hour, on smoothed tracking
# (decision 41's sweep against IDSSE: 16.1 and 18.5 in the demo matches, 10.4–15.1 in IDSSE).
DITHER_S, DITHER_PATH_M, DITHER_NET_M = 4.0, 10.0, 2.0
DITHER_TOLERANCE = 2.0  # per player-hour: about half the IDSSE range (our choice)
# The shape of high-speed running (decision 43), from runs (1-s mean speed above HI_SPEED, as the
# estimator's signals and the highlights count them) of outfield players, smoothed positions:
# the share that last at most SHORT_RUN_S, the share that start within CLOSE_RUN_S of the last
# one's end (the stuff of back-to-back runs), and the share that turn back (within TURN_BACK_S,
# heading more than 120° from the last run). Shares, not counts: the volume of running is set by
# the Premier League targets above, and IDSSE is a lower-volume league (a first fit with IDSSE's
# 33 runs per player-hour as a target could not have both). Before decision 43 (16 seeds): 72%,
# 30% and 11.5%, against IDSSE's 61%, 18% and 4.3%: short runs close together, the player
# sprinting straight back after a turnover. Tolerances are our choice.
SHORT_RUN_S, CLOSE_RUN_S, TURN_BACK_S = 2, 20, 10
RUN_SHAPE_TOLERANCE = {"short_pct": 3.0, "close_pct": 2.0, "back_pct": 0.8}


@dataclass(frozen=True)
class Knob:
    name: str  # a params name, or "POSITION_EFFORT.CB" for one entry of that dict
    lo: float
    hi: float
    radius: float  # half-width of the first round's design


# The knobs tuned by hand before decision 42 (params.py says what each does). Work rate per
# position moves high-speed running and sprint distance together; the efforts of the hardest
# runs (tracking a runner, overlaps, recovery runs, counter-attack support) move sprint distance
# more than high-speed running, which is how one position can have both on target;
# DUEL_PER_TOUCH and TRANSITION_CHANCE the two counts (DEAD_SPEED, the walk back into shape at a
# dead ball, was a knob in decision 42's first run: no effect on the running while the ball is
# dead within ±0.06, so it was left out);
# SHAPE_RUN_GAP (when a player runs back to his shape) and SHAPE_LAG_S (how fast the shape follows
# the ball) set how often a shape run chases a target that swings back (dithering).
KNOBS = [Knob(f"POSITION_EFFORT.{p.value}", 0.85, 1.35, 0.03) for p in Position]
KNOBS += [
    Knob("TRACK_EFFORT", 0.70, 1.0, 0.04),
    Knob("OVERLAP_EFFORT", 0.70, 1.0, 0.04),
    # In danger a recovery run speeds up from SHAPE_RUN_SPEED to RECOVERY_EFFORT (roles), never
    # down: decision 42's second run went to 0.808 with a bound of 0.70.
    Knob("RECOVERY_EFFORT", P.SHAPE_RUN_SPEED, 1.0, 0.04),
    Knob("COUNTER_SUPPORT_EFFORT", 0.70, 1.0, 0.04),
    Knob("DUEL_PER_TOUCH", 0.15, 0.90, 0.06),
    Knob("TRANSITION_CHANCE", 0.10, 0.60, 0.05),
    Knob("SHAPE_RUN_GAP", 5.0, 15.0, 1.0),
    Knob("SHAPE_LAG_S", 0.5, 3.5, 0.3),
    # Decision 43, the shape of the running: how hard a player brakes as he arrives (constant
    # deceleration, movement.step), how long he does not run back the way he sprinted, and the
    # speeds a shape run and a recovery run in danger start from at the smallest gap, and the
    # cover defender's speed (it had been a shape run's, and the role changes hands every touch).
    Knob("ARRIVE_DECEL", 1.5, 4.0, 0.3),
    Knob("TURN_S", 3.5, 10.0, 1.0),
    Knob("SHAPE_RUN_MIN", 0.30, 0.55, 0.04),
    Knob("RECOVERY_START", 0.40, P.SHAPE_RUN_SPEED, 0.05),
    Knob("COVER_SPEED", 0.35, P.SHAPE_RUN_SPEED, 0.05),
]


def get(name: str) -> float:
    if "." in name:
        table, key = name.split(".")
        return float(getattr(P, table)[Position(key)])
    return float(getattr(P, name))


def put(name: str, value: float) -> None:
    if "." in name:
        table, key = name.split(".")
        getattr(P, table)[Position(key)] = value
    else:
        setattr(P, name, value)


def idsse_bands() -> np.ndarray | None:
    """Outfield speed bands of the IDSSE matches, % of player time (``sim.idsse``)."""
    from runningbattery.sim.idsse import band_shares, load_derived

    derived = load_derived()
    return band_shares(derived, "speed_s", "outfield") if derived else None


def dither(xy: np.ndarray, alive: np.ndarray) -> tuple[int, float]:
    """Dithering episodes in one period of smoothed positions (frames, players, 2; NaN off the
    pitch) and the in-play player-hours they come from."""
    w = round(DITHER_S * P.FRAME_RATE_HZ)
    step = np.nan_to_num(np.hypot(*np.diff(xy, axis=0).transpose(2, 0, 1)))
    walked = np.vstack([np.zeros((1, xy.shape[1])), np.cumsum(step, axis=0)])
    path = walked[w:] - walked[:-w]
    net = np.hypot(*(xy[w:] - xy[:-w]).transpose(2, 0, 1))
    dead = np.concatenate([[0], np.cumsum(~alive)])
    in_play = (dead[w:-1] - dead[: -w - 1]) == 0
    flag = (path > DITHER_PATH_M) & (net < DITHER_NET_M) & in_play[:, None]
    starts = flag & ~np.vstack([np.zeros((1, flag.shape[1]), dtype=bool), flag[:-1]])
    on = ~np.isnan(xy[..., 0]) & alive[:, None]
    return int(starts.sum()), float(on.sum() / P.FRAME_RATE_HZ / 3600.0)


def run_shape(xy: np.ndarray, cols) -> np.ndarray:
    """Hours on the pitch, runs, short runs, close runs and turn-backs (``SHORT_RUN_S`` …) of
    columns ``cols`` in one period of smoothed positions (frames, players, 2; NaN off the
    pitch), from 1-s mean speeds."""
    hz = round(P.FRAME_RATE_HZ)
    n = len(xy) // hz
    out = np.zeros(5)
    for j in cols:
        p = xy[: n * hz, j]
        sec = (np.hypot(*np.gradient(p, axis=0).T) * hz).reshape(n, hz).mean(axis=1)
        on = np.isfinite(sec)
        if not on.any():
            continue
        out[0] += on.sum() / 3600.0
        fast = np.r_[False, on & (sec > P.HI_SPEED) & (sec <= SPEED_CAP), False].astype(int)
        edges = np.flatnonzero(np.diff(fast))
        prev = None
        for a, b in zip(edges[::2], edges[1::2] - 1, strict=True):
            out[1] += 1
            out[2] += b - a + 1 <= SHORT_RUN_S
            d = p[min(b + 1, n - 1) * hz] - p[max(a - 1, 0) * hz]
            way = d / max(float(np.hypot(*d)), 1e-6)
            if prev is not None:
                gap = a - prev[0] - 1
                out[3] += gap <= CLOSE_RUN_S
                out[4] += gap <= TURN_BACK_S and float(way @ prev[1]) < -0.5
            prev = (b, way)
    return out


def run_shape_moments(total: np.ndarray) -> dict[str, float]:
    _, runs, short, close, back = total
    runs = max(runs, 1)
    return {"short_pct": 100.0 * short / runs, "close_pct": 100.0 * close / runs,
            "back_pct": 100.0 * back / runs}  # fmt: skip


def idsse_run_shape() -> dict[str, float] | None:
    """``run_shape`` of the IDSSE matches (``sim.spacing`` cache), pooled: each player's spells
    on the pitch smoothed apart; each team's goalkeeper (the player most often within 17.5 m of
    a goal line) left out."""
    from runningbattery.sim.idsse import RAW, on_pitch_spells
    from runningbattery.sim.spacing import CACHE, idsse_periods

    if not RAW.exists():
        return None
    total = np.zeros(5)
    for folder in sorted(p for p in RAW.iterdir() if (p / CACHE).exists()):
        periods, team, _ = idsse_periods(folder)
        deep = np.nanmean(np.vstack([np.abs(pos[..., 0]) > 35.0 for pos, _ in periods]), axis=0)
        keepers = {int(np.flatnonzero(team == k)[np.argmax(deep[team == k])]) for k in (0, 1)}
        for pos, _ in periods:
            xy = np.full_like(pos, np.nan)
            for j in range(pos.shape[1]):
                for a, b in on_pitch_spells(pos[:, j]):
                    xy[a:b, j] = smooth(pos[a:b, j][:, None, :])[:, 0]
            total += run_shape(xy, [j for j in range(pos.shape[1]) if j not in keepers])
    return run_shape_moments(total) if total[0] else None


def idsse_dither() -> float | None:
    """Dithering episodes per in-play player-hour in the IDSSE matches cached at 10 Hz
    (``sim.spacing``), pooled."""
    from runningbattery.sim.idsse import RAW
    from runningbattery.sim.spacing import CACHE, idsse_periods

    if not RAW.exists():
        return None
    n = hours = 0.0
    for folder in sorted(p for p in RAW.iterdir() if (p / CACHE).exists()):
        for pos, alive in idsse_periods(folder)[0]:
            a, b = dither(pos, alive)
            n, hours = n + a, hours + b
    return n / hours if hours else None


def moment_targets(
    bands: np.ndarray | None,
    dithering: float | None = None,
    shape: dict[str, float] | None = None,
) -> list[tuple[str, float, float]]:
    """(name, target, tolerance) of every moment; a gap of one tolerance scores 1."""
    out = []
    for pos, (dist, hid, spr) in POSITION_TARGETS.items():
        out.append((f"{pos}.distance", dist, 0.05 * dist))
        # Keepers: their high-speed running is a few dozen metres, judged within ±10%; their
        # sprint distance within ±5 m (batch.GK_SPRINT_TOLERANCE_M).
        out.append((f"{pos}.hid", hid, (0.10 if pos == "GK" else 0.05) * hid))
        out.append((f"{pos}.sprint", spr, 5.0 if pos == "GK" else 0.05 * spr))
    for name, target in PHASE_TARGETS.items():
        out.append((f"phase.{name}", target, 0.10 * target))
    for name, target in PHASE_HID_TARGETS.items():
        out.append((f"phase_hid.{name}", target, 0.10 * target))
    for key, tol in (("duels", 0.10), ("transitions", 0.10), ("fouls", 0.15), ("shots", 0.15),
                     ("passes", 0.10)):  # fmt: skip
        out.append((key, TARGETS[key][0], tol * TARGETS[key][0]))
    out.append(("ball_in_play_pct", TARGETS["ball_in_play_pct"][0], 4.0))
    if bands is not None:
        for label, pct in zip(SPEED_LABELS, bands, strict=True):
            out.append((f"band.{label}", float(pct), 3.0))  # batch.BAND_TOLERANCE, points
    if dithering is not None:
        out.append(("dither", dithering, DITHER_TOLERANCE))
    for name, value in (shape or {}).items():
        out.append((f"runs.{name}", value, RUN_SHAPE_TOLERANCE[name]))
    return out


def match_moments(job: tuple[dict[str, float], int]) -> dict[str, float]:
    """The moments of one match with the knobs set to ``values`` (every knob is set, so a
    worker never keeps another point's values)."""
    from runningbattery.sim.output import simulate
    from runningbattery.sim.runs import speeds
    from runningbattery.sim.summary import event_counts, movement

    values, seed = job
    for name, value in values.items():
        put(name, value)
    m = simulate(seed, f"calib{seed}")
    starters = [p for team in m.metadata.teams for p in team.players if p.starter]
    ids = [p.id for p in starters]
    moved = movement([pf.pos for pf in m.periods], ids)
    out: dict[str, float] = {}
    for pos in POSITION_TARGETS:
        cols = [p.id for p in starters if p.position.value == pos]
        for key, name in (("distance", "distance_m"), ("hid", "hid_m"), ("sprint", "sprint_m")):
            out[f"{pos}.{key}"] = float(np.mean([moved[name][i] for i in cols]))
    team_of = np.repeat([0, 1], 11)
    metres = {k: 0.0 for k in ("in_possession", "out_of_possession", "dead")}
    hid = dict(metres)
    frames = dict(metres)
    for pf in m.periods:
        speed = speeds(pf.pos)
        step = speed / P.FRAME_RATE_HZ
        alive, holder = pf.alive[:-1, None], pf.possession[:-1, None]
        masks = {
            "in_possession": alive & (holder == team_of[None]),
            "out_of_possession": alive & (holder == 1 - team_of[None]),
            "dead": ~alive & np.ones((1, 22), dtype=bool),
        }
        for name, mask in masks.items():
            metres[name] += float(np.where(mask, step, 0.0).sum())
            hid[name] += float(np.where(mask & (speed > P.HI_SPEED), step, 0.0).sum())
            frames[name] += float(mask.sum())
    for name in PHASE_TARGETS:
        out[f"phase.{name}"] = metres[name] / (frames[name] / P.FRAME_RATE_HZ / 60.0)
    for name in PHASE_HID_TARGETS:
        out[f"phase_hid.{name}"] = hid[name] / (frames[name] / P.FRAME_RATE_HZ / 60.0)
    counts = event_counts(m.events)
    for key in ("duels", "transitions", "fouls", "shots", "passes"):
        out[key] = float(counts[key])
    alive = np.concatenate([pf.alive for pf in m.periods])
    out["ball_in_play_pct"] = 100.0 * float(alive.mean())
    is_gk = np.array([p.position == Position.GK for p in starters])
    band = np.zeros(len(SPEED_EDGES) - 1)
    episodes = hours = 0.0
    shape = np.zeros(5)
    for obs, pf in zip(m.observed, m.periods, strict=True):  # as batch.observed_kinematics
        xy = smooth(np.where(obs.seen[..., None], obs.pos, np.nan))
        band += band_seconds(kinematics(xy)[0][:, ~is_gk], SPEED_EDGES)
        a, b = dither(xy, pf.alive)
        episodes, hours = episodes + a, hours + b
        shape += run_shape(xy, np.flatnonzero(~is_gk))
    out["dither"] = episodes / hours
    out |= {f"runs.{k}": v for k, v in run_shape_moments(shape).items()}
    for label, pct in zip(SPEED_LABELS, 100.0 * band / band.sum(), strict=True):
        out[f"band.{label}"] = float(pct)
    return out


def design(n: int, dims: int, seed: int) -> np.ndarray:
    """``n`` points of a scrambled Sobol design on [-1, 1]^dims, the centre first."""
    sobol = qmc.Sobol(dims, scramble=True, seed=seed).random(n)
    return np.vstack([np.zeros(dims), 2.0 * sobol - 1.0])


def fit(x: np.ndarray, gaps: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Least squares of every scaled gap on the scaled knobs, one row per match: the gaps at the
    centre (K), the Jacobian (K × dims) and the standard error of the centre's gaps (K)."""
    a = np.hstack([np.ones((len(x), 1)), x])
    coef, *_ = np.linalg.lstsq(a, gaps, rcond=None)
    resid = gaps - a @ coef
    dof = max(len(x) - a.shape[1], 1)
    cov = np.linalg.inv(a.T @ a)
    se0 = np.sqrt(np.sum(resid**2, axis=0) / dof * cov[0, 0])
    return coef[0], coef[1:].T, se0


def step(
    g0: np.ndarray,
    jac: np.ndarray,
    centre: np.ndarray,
    radius: np.ndarray,
    knobs: list[Knob],
    trust: float = TRUST,
) -> np.ndarray:
    """The Levenberg–Marquardt step (scaled knobs) that minimises |g0 + J d|² + DAMPING |d|²
    within the trust region and the knobs' bounds."""
    lo = np.maximum(-trust, (np.array([k.lo for k in knobs]) - centre) / radius)
    hi = np.minimum(trust, (np.array([k.hi for k in knobs]) - centre) / radius)
    hi = np.maximum(hi, lo + 1e-9)  # a centre outside a (tightened) bound steps back to it
    a = np.vstack([jac, math.sqrt(DAMPING) * np.eye(len(knobs))])
    b = np.concatenate([-g0, np.zeros(len(knobs))])
    return lsq_linear(a, b, bounds=(lo, hi)).x


def evaluate(
    pool, values: dict[str, float], seeds: range, names: list[str], target, tol
) -> tuple[float, np.ndarray]:
    """The loss and the mean scaled gaps of one set of knobs, simulated on ``seeds``."""
    rows = list(pool.map(match_moments, [(values, s) for s in seeds], chunksize=1))
    gaps = ((np.array([[r[n] for n in names] for r in rows]) - target) / tol).mean(axis=0)
    return float(gaps @ gaps), gaps


def line_search(
    json_in: Path,
    fractions: tuple[float, ...],
    per_point: int,
    seed_base: int,
    jobs: int | None,
    log=print,
) -> dict:
    """Backtracking along a round's step: the round's centre and the points a ``fraction`` of
    the way along its step, each simulated on its own ``per_point`` seeds (no design, so it
    costs a fraction of a round); the best of them is the result. The surface's step is only as
    good as its linear fit, and decision 42's rounds kept landing above their prediction."""
    out = json.loads(json_in.read_text())
    last = next(h for h in reversed(out["history"]) if not h["rejected"])
    knobs = list(last["centre"])
    targets = [(m["name"], m["target"], m["tolerance"]) for m in out["moments"]]
    names = [t[0] for t in targets]
    target = np.array([t[1] for t in targets])
    tol = np.array([t[2] for t in targets])
    centre = np.array([last["centre"][k] for k in knobs])
    end = np.array([last["step"][k] for k in knobs])
    tried = []
    with ProcessPoolExecutor(max_workers=jobs or default_workers()) as pool:
        for n, f in enumerate((0.0, *fractions)):
            values = dict(zip(knobs, map(float, centre + f * (end - centre)), strict=True))
            seeds = range(seed_base + n * per_point, seed_base + (n + 1) * per_point)
            loss, gaps = evaluate(pool, values, seeds, names, target, tol)
            tried.append(dict(fraction=f, loss=loss, values=values,
                              gaps=dict(zip(names, map(float, gaps), strict=True))))  # fmt: skip
            big = ", ".join(f"{k} {g:+.1f}" for k, g in zip(names, gaps, strict=True) if abs(g) > 1)
            log(f"  {f:4.2f} of the step: loss {loss:5.1f}  ({big})", flush=True)
    best = min(tried, key=lambda x: x["loss"])
    return dict(tried=tried, result=best["values"], fraction=best["fraction"])


def report_round(
    r: int, names: list[str], g0: np.ndarray, se0: np.ndarray, pred: np.ndarray
) -> list[str]:
    lines = [f"Round {r}: loss at the centre {float(g0 @ g0):.1f}, predicted after the step "
             f"{float(pred @ pred):.1f} (gaps in tolerances; |gap| ≤ 1 is within)."]  # fmt: skip
    for name, g, s, p in zip(names, g0, se0, pred, strict=True):
        flag = " !!" if abs(g) > 1 else ""
        lines.append(f"  {name:<28}{g:+7.2f} ±{s:4.2f}  →{p:+7.2f}{flag}")
    return lines


def calibrate(
    rounds: int,
    n_design: int,
    per_point: int,
    jobs: int | None,
    start: dict[str, float] | None = None,
    radius_scale: float = 1.0,
    seed_base: int = SEED_BASE,
    log=print,
) -> dict:
    knobs = KNOBS
    for name, value in (start or {}).items():
        if any(k.name == name for k in knobs):  # a knob since left out keeps params.py's value
            put(name, value)
    targets = moment_targets(idsse_bands(), idsse_dither(), idsse_run_shape())
    names = [t[0] for t in targets]
    target = np.array([t[1] for t in targets])
    tol = np.array([t[2] for t in targets])
    centre = np.array([get(k.name) for k in knobs])
    radius = np.array([k.radius for k in knobs]) * radius_scale
    history = []
    seed = seed_base
    best = None  # (loss, (g0, jac, centre, radius)) of the best round so far
    trust = TRUST
    jobs = jobs or default_workers()
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for r in range(1, rounds + 1):
            t0 = time.time()
            x = design(n_design, len(knobs), seed=r)
            points = centre + x * radius
            work = []
            for row in points:
                values = {k.name: float(v) for k, v in zip(knobs, row, strict=True)}
                work += [(values, seed + s) for s in range(per_point)]
                seed += per_point
            results = list(pool.map(match_moments, work, chunksize=1))
            xs = np.repeat(x, per_point, axis=0)
            gaps = (np.array([[res[n] for n in names] for res in results]) - target) / tol
            g0, jac, se0 = fit(xs, gaps)
            loss = float(g0 @ g0)
            surface = (g0, jac, centre, radius)
            rejected = best is not None and loss > best[0]
            if rejected:  # back to the best round's surface, with half the trust region
                trust /= 2.0
                surface = best[1]
            else:
                best = (loss, surface)
            d = step(*surface, knobs, trust)
            pred = surface[0] + surface[1] @ d
            new = surface[2] + d * surface[3]
            for line in report_round(r, names, g0, se0, pred):
                log(line)
            if rejected:
                log(f"  Worse than the best round ({best[0]:.1f}): its step is taken again "
                    f"from the best round, trust region {trust:.2f} radii.")  # fmt: skip
            log(f"  {len(results)} matches in {time.time() - t0:.0f} s. Knobs:", flush=True)
            for k, c, v, dd in zip(knobs, centre, new, d, strict=True):
                log(f"  {k.name:<28}{c:7.3f} → {v:7.3f}  ({dd:+.2f} radii)")
            history.append(
                dict(
                    round=r,
                    centre={k.name: float(c) for k, c in zip(knobs, centre, strict=True)},
                    radius={k.name: float(c) for k, c in zip(knobs, radius, strict=True)},
                    gaps={n: float(g) for n, g in zip(names, g0, strict=True)},
                    gap_se={n: float(g) for n, g in zip(names, se0, strict=True)},
                    loss=loss,
                    rejected=rejected,
                    jacobian={
                        n: dict(zip([k.name for k in knobs], map(float, row), strict=True))
                        for n, row in zip(names, jac, strict=True)
                    },  # fmt: skip
                    step={k.name: float(v) for k, v in zip(knobs, new, strict=True)},
                    predicted_gaps={n: float(g) for n, g in zip(names, pred, strict=True)},
                    predicted_loss=float(pred @ pred),
                    matches=len(results),
                )
            )
            radius = surface[3]
            if np.max(np.abs(d)) < trust / 2:
                radius = radius * SHRINK
            centre = new
    return dict(
        knobs=[vars(k) for k in knobs],
        moments=[dict(name=n, target=float(t), tolerance=float(s)) for n, t, s in targets],
        history=history,
        result={k.name: float(v) for k, v in zip(knobs, centre, strict=True)},
        best_round={k.name: float(v) for k, v in zip(knobs, best[1][2], strict=True)},
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m runningbattery.sim.calibrate", description=__doc__
    )
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--design", type=int, default=32, help="Sobol points per round")
    parser.add_argument("--seeds-per-point", type=int, default=16)
    parser.add_argument("--jobs", type=int, help="worker processes (default: physical cores)")
    parser.add_argument("--json", type=Path, help="write the rounds and the result here")
    parser.add_argument("--start", type=Path, help="start from this earlier --json's result")
    parser.add_argument("--radius-scale", type=float, default=1.0, help="first design's radius")
    parser.add_argument("--seed-base", type=int, default=SEED_BASE, help="first seed")
    parser.add_argument(
        "--line-search",
        type=Path,
        help="instead of rounds: backtrack along the last accepted step of this earlier --json",
    )
    args = parser.parse_args(argv)
    if args.line_search:
        out = line_search(args.line_search, (0.25, 0.5, 1.0), 4 * args.seeds_per_point,
                          args.seed_base, args.jobs)  # fmt: skip
        print(f"\nResult: {out['fraction']} of the step (write into params.py):")
        for name, value in out["result"].items():
            print(f"  {name} = {value:.3f}")
        if args.json:
            args.json.write_text(json.dumps(out, indent=1))
        return
    start = json.loads(args.start.read_text())["result"] if args.start else None
    out = calibrate(args.rounds, args.design, args.seeds_per_point, args.jobs, start,
                    args.radius_scale, args.seed_base)  # fmt: skip
    print("\nResult (write into params.py):")
    for name, value in out["result"].items():
        print(f"  {name} = {value:.3f}")
    if args.json:
        args.json.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
