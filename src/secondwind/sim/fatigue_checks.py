"""Fatigue checks: what tired players do differently, measured the way the papers measured it.

``uv run python -m secondwind.sim.fatigue_checks --seeds 1-30`` simulates the same seeds with
fatigue on and off and prints both next to the published values; ``sim.batch`` adds the same
table to its report. Picking each player's most intense window guarantees lower values after it
even with no fatigue at all, so the gap between the two columns is the part that is really
fatigue (PLAN §2.5, "No-fatigue control").

Per match (``sim_measure``), on the noise-free positions, outfield players who played the whole
match (as in the papers; substitutes have their own check), kept as sums so that matches pool by
adding (``summarise`` then gives % changes of the pooled sums):

- **Recovery after peaks** [Leifsson2024, Table 1]: each player's most intense 1-, 2- and 5-min
  window (rolling in 1 s steps, inside a half, with 5 min of the half left after it) of distance
  above 5.5 m/s (HSR), above 7 m/s (sprint) or while speeding up at 3 m/s² or more (AccD); then
  the same distance in each of the next 5 minutes against the player's match average per minute
  without the peak window.
- **Purposes after peaks** [Ju2022, p.975]: the most intense 1-, 3- and 5-min window of
  distance above 5.5 m/s; in the next window of the same length, that distance in total and run
  for covering, recovery runs and closing down (the run purpose behind each frame,
  ``roles.py``), against the match average for a window that long.
- **Effort shape after the peak** [Fang2024, Table 2, Fig. 1]: the 5 min of ball-in-play time
  with the most distance above 5.5 m/s, against the next 5 min of ball-in-play time: the length,
  duration and mean speed of the efforts above 5.5 m/s lasting 1 s or more (as ``runs.py``)
  that start with the ball in play; the carries' count, length and speed; and the receiver's
  speed at each reception.
- **End of the match** [Bradley2009, Fig. 2, p.163; Bradley2013, p.4; Chen2025;
  VighLarsen2018]: distance above 4 m/s (14.4 km/h) per minute in the last 15 min of the 90
  (75–90, added time left out) against the first 15; the mean time between efforts above
  5.5 m/s in the same windows and in each half; per minute in the second half against the
  first: total distance, distance above 5.5 and above 7 m/s, and accelerations and
  decelerations beyond 2 m/s² lasting 0.5 s or more (our definition); the first 10 min of each
  half; and the second half against the first by first-half load (players split into thirds by
  their distance above 4 m/s per minute in the first half).
- **Runs skipped while tired** (fatigue on only): of the hard-run decisions wanted above
  5.5 m/s (``Physiology.decisions``, every ask), the share skipped while the player was
  ``tired`` (a tired moment), while late-match fatigued (tank below ``LATE_TANK_BELOW``, not
  tired) and while neither, in total and for covering, recovery runs and closing down. Ju2022's
  drops after peak periods [p.975] are the reference for the size. (Distance run while tired is
  no measure of this: players get tired in the busiest spells, when everyone runs more.)
- **Substitutes** [Bradley2013, Table IV; Bradley 2014 via Hills2018; synthesis §4.7]:
  distance above 5.5 m/s per minute on the pitch against whole-match outfield players over the
  same minutes and over the whole match, and against the player each one replaced (before the
  substitution).
- **Runs** measured and skipped by purpose (truth.json: skipped runs one per situation, only
  those forecast to be high-intensity runs), the share of player-seconds with a tired moment and
  with late-match fatigue, and the tank at the final whistle.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import numpy as np

from secondwind import default_workers
from secondwind.schema import EventType, Position, RunPurpose
from secondwind.sim import params as P
from secondwind.sim.output import owner
from secondwind.sim.roles import CODE
from secondwind.sim.runs import speeds, spells

HZ = round(P.FRAME_RATE_HZ)
AFTER_S = 300  # the 5 min after a peak that Leifsson2024 follows, minute by minute
SPRINT_SPEED = 7.0  # m/s (25.2 km/h) [Leifsson2024; synthesis §4.1]
ACC_HARD = 3.0  # m/s², intense acceleration [Leifsson2024]
HIR_SPEED = 4.0  # m/s (14.4 km/h), high-intensity running [Bradley2009]
ACC_EFFORT, ACC_EFFORT_S = 2.0, 0.5  # m/s² [VighLarsen2018] and s (our definition)
LEIFSSON_WINDOWS = (60, 120, 300)
JU_WINDOWS = (60, 180, 300)
JU_PURPOSES = ("covering", "recovery_run", "close_down")
FANG_S = 300  # 5 min of ball-in-play time [Fang2024]
EARLY = (0, 900)  # first 15 min of the first half, s since its kick-off
LATE = (1800, 2700)  # 75–90 min: the second half's 30–45 min
DIP_S = 600  # first 10 min of each half [Bradley2013, p.4]
TIRED_BLOCKS = (0, 900, 1800, 2700)  # 15-min blocks of each half (the last includes added time)

# Peak distance per minute in the most intense 1-, 2- and 5-min window: HSR 62 / 38 / 22, sprint
# 53 / 30 / 15 m/min [Leifsson2024, Table 1; synthesis §4.3]; AccD not given there.
LEIFSSON_PEAK = {"hsr": (62, 38, 22), "sprint": (53, 30, 15)}
# Published values, % against the match average per minute [Leifsson2024, Table 1].
LEIFSSON = {
    "hsr_60": (-29, -6, -3, -2, -2),
    "hsr_120": (-35, -11, 0, -2, -3),
    "hsr_300": (-45, -29, -13, -8, -4),
    "sprint_60": (-20, -3, -7, -3, 4),
    "sprint_120": (-24, -12, -3, 0, -7),
    "sprint_300": (-39, -29, -18, -17, -12),
    "accd_60": (68, 89, 94, 88, 90),
    "accd_120": (47, 86, 93, 90, 88),
    "accd_300": (23, 56, 76, 85, 87),
}
# PLAN §2.5: each minute within ±10 percentage points; minute 1 after a 5-min HSR peak between
# −35 and −55%.
LEIFSSON_TOLERANCE = 10.0
LEIFSSON_HSR_300_MIN1 = (-55.0, -35.0)
# High-intensity distance in the next window against the match average, players [Ju2022,
# p.975]: in total after 1-, 3- and 5-min peaks; by purpose, the range over the three windows.
JU_TOTAL = {60: -48, 180: -30, 300: -25}
JU_PURPOSE = {"covering": (-44, -22), "recovery_run": (-43, -34), "close_down": (-45, -27)}
# Next 5 min against the peak 5 min [Fang2024]: per effort (Table 2), carries (Fig. 1: count
# −26%; length and speed only as effect sizes, −0.37 and −0.32) and the receiver's speed (Fig. 1,
# ES −0.5); distance above 5.5 m/s per minute −77.2% (Table 2).
FANG = {"length": -23, "duration": -32, "speed": -3, "carries": -26, "hsr": -77}
# End of the match: (published %, our pass range) [Bradley2009, Fig. 2, p.162–163; Chen2025;
# VighLarsen2018]; the pass ranges are PLAN §2.5.
END = {
    "hir_last15_vs_first15": (-21, (-30, -10)),
    "hsr_half2_vs_half1": (3, (-10, 10)),
    "sprint_half2_vs_half1": (7, (-10, 10)),
    "gap_last15_vs_first15": (28, (15, 40)),
    "gap_half2_vs_half1": (15, None),
    "td_half2_vs_half1": (-5, None),
    "accdec_half2_vs_half1": (-11, None),
}


def _per_second(x: np.ndarray) -> np.ndarray:
    """(frames, players) to (seconds, players) sums; a last partial second is dropped."""
    s = len(x) // HZ
    return x[: s * HZ].reshape(s, HZ, -1).sum(axis=1)


def _windows(x: np.ndarray, w: int, after: int) -> np.ndarray:
    """Rolling sums of ``w`` rows of (rows, players), for the starts that leave ``after`` rows
    after the window: (starts, players), possibly empty."""
    n = max(len(x) - w - after + 1, 0)
    c = np.concatenate([np.zeros((1, x.shape[1])), np.cumsum(x, axis=0)])
    return c[w : w + n] - c[:n]


def _peak(halves: list[np.ndarray], w: int, after: int) -> list[tuple[int, int]]:
    """Per player, (half, start row) of the largest window over both halves; (-1, -1) if none
    fits."""
    players = halves[0].shape[1]
    best = np.full(players, -np.inf)
    where = [(-1, -1)] * players
    for h, x in enumerate(halves):
        sums = _windows(x, w, after)
        if not len(sums):
            continue
        start = sums.argmax(axis=0)
        top = sums[start, np.arange(players)]
        for j in np.flatnonzero(top > best):
            best[j], where[j] = top[j], (h, int(start[j]))
    return where


def _leifsson(halves: list[np.ndarray], w: int) -> dict:
    total = sum(x.sum(axis=0) for x in halves)
    seconds = sum(len(x) for x in halves)
    base, peak, players, after = 0.0, 0.0, 0, np.zeros(5)
    for j, (h, i) in enumerate(_peak(halves, w, AFTER_S)):
        if h < 0:
            continue
        x = halves[h][:, j]
        top = x[i : i + w].sum()
        base += (total[j] - top) / ((seconds - w) / 60.0)
        peak += top / (w / 60.0)
        players += 1
        after += x[i + w : i + w + AFTER_S].reshape(5, 60).sum(axis=1)
    return {"base": float(base), "peak": float(peak), "players": players, "after": after.tolist()}


def _ju(groups: dict[str, list[np.ndarray]], w: int) -> dict:
    hsr = groups["total"]
    seconds = sum(len(x) for x in hsr)
    out = {name: {"next": 0.0, "avg": 0.0} for name in groups}
    for j, (h, i) in enumerate(_peak(hsr, w, w)):
        if h < 0:
            continue
        for name, x in groups.items():
            out[name]["next"] += float(x[h][i + w : i + 2 * w, j].sum())
            out[name]["avg"] += float(sum(y[:, j].sum() for y in x)) * w / seconds
    return out


def _efforts(v: np.ndarray) -> list[list[tuple[int, float, float]]]:
    """Per player, (start frame, length m, duration s) of each effort above 5.5 m/s lasting at
    least 1 s (``runs.hi_runs``)."""
    out = []
    for j in range(v.shape[1]):
        out.append(
            [
                (a, float(v[a:b, j].sum()) / HZ, (b - a) / HZ)
                for a, b in spells(v[:, j] > P.HI_SPEED, round(P.HI_MIN_S * HZ))
            ]
        )
    return out


def sim_measure(match) -> dict:
    """The fatigue checks for one ``SimMatch`` (module docstring)."""
    meta = match.metadata
    starters = [p for team in meta.teams for p in team.players if p.starter]
    ids = [p.id for p in starters]  # engine slots
    went_off = {s.player_out for s in meta.substitutions}
    cols = np.flatnonzero(
        [p.position != Position.GK and p.id not in went_off for p in starters]
    )  # outfield players who played the whole match
    halves: dict[str, list[np.ndarray]] = {}
    v_by_half, alive_by_half, efforts, accdec = [], [], [], []
    for pf in match.periods:
        v = speeds(pf.pos)[:, cols]  # (frames − 1, players): frame k to k + 1
        step = v / HZ
        acc = np.vstack([np.zeros((1, len(cols))), np.diff(v, axis=0) * HZ])
        purpose = pf.purpose[:-1, cols]
        frame = {
            "td": step,
            "hsr": np.where(v > P.HI_SPEED, step, 0.0),
            "sprint": np.where(v > SPRINT_SPEED, step, 0.0),
            "accd": np.where(acc >= ACC_HARD, step, 0.0),
            "hir": np.where(v > HIR_SPEED, step, 0.0),
        }
        for name in JU_PURPOSES:
            code = CODE[RunPurpose(name)]
            frame[name] = np.where((v > P.HI_SPEED) & (purpose == code), step, 0.0)
        for name, x in frame.items():
            halves.setdefault(name, []).append(_per_second(x))
        v_by_half.append(v)
        alive_by_half.append(pf.alive[:-1])
        efforts.append(_efforts(v))
        n = round(ACC_EFFORT_S * HZ)
        accdec.append(
            sum(
                len(spells(acc[:, j] > ACC_EFFORT, n)) + len(spells(acc[:, j] < -ACC_EFFORT, n))
                for j in range(len(cols))
            )
        )
    res: dict = {
        "leifsson": {
            f"{m}_{w}": _leifsson(halves[m], w)
            for m in ("hsr", "sprint", "accd")
            for w in LEIFSSON_WINDOWS
        },
        "ju": {
            str(w): _ju({"total": halves["hsr"]} | {k: halves[k] for k in JU_PURPOSES}, w)
            for w in JU_WINDOWS
        },
        "fang": _fang(match, ids, cols, v_by_half, alive_by_half, efforts),
        "end": _end(halves, efforts, accdec),
        "runs": dict(Counter(f"{r.purpose.value}:{int(r.executed)}" for r in match.truth.runs)),
    }
    res["subs"] = _subs(match, cols)
    series = {p.player_id: p.series for p in match.truth.players}
    res["skips"] = _skips(match, series)
    # Tired and late-match shares: every outfield player, substitutes included, per second on
    # the pitch.
    gk = {p.id for team in meta.teams for p in team.players if p.position == Position.GK}
    everyone = [pid for pid in series if pid not in gk]
    flags = {"tired": [np.array(series[pid].tired) for pid in everyone]}
    flags["late"] = [np.array(series[pid].tank) < P.LATE_TANK_BELOW for pid in everyone]
    for name, per_player in flags.items():
        res[name] = {
            "seconds": sum(len(f) for f in per_player),
            name: int(sum(f.sum() for f in per_player)),
        }
        blocks = np.zeros((2, len(TIRED_BLOCKS), 2))  # half, block, (flagged, seconds)
        for pid, flag in zip(everyone, per_player, strict=True):
            s = series[pid]
            period, t = np.array(s.period), np.array(s.t)
            block = np.digitize(t, TIRED_BLOCKS[1:])
            for h in (0, 1):
                on = period == h + 1
                blocks[h, :, 0] += np.bincount(block[on], flag[on], len(TIRED_BLOCKS))
                blocks[h, :, 1] += np.bincount(block[on], minlength=len(TIRED_BLOCKS))
        res[f"{name}_blocks"] = blocks.ravel().tolist()  # flat, so that matches add up
    res["tank_end"] = [series[ids[c]].tank[-1] for c in cols]
    return res


def _subs(match, cols: np.ndarray) -> dict:
    """Substitutes' distance above 5.5 m/s and minutes on the pitch, and the same for the
    whole-match outfield players (``cols``) over the same minutes and over the whole match,
    and for the players replaced before they went off: [metres, player-minutes] each."""
    v_all = [speeds(pf.pos) for pf in match.periods]
    hsr = [_per_second(np.where(v > P.HI_SPEED, v, 0.0) / HZ) for v in v_all]
    seconds = [len(x) for x in hsr]
    out = {
        "sub": [0.0, 0.0],
        "same": [0.0, 0.0],
        "replaced": [0.0, 0.0],
        "whole": [float(sum(x[:, cols].sum() for x in hsr)), sum(seconds) / 60.0 * len(cols)],
    }
    for spell in match.spells or []:
        if spell.player.starter:
            continue
        h, t0 = spell.on
        j, k = spell.slot, int(t0)
        after = hsr[h - 1][k:]
        out["sub"][0] += float(after[:, j].sum())
        out["sub"][1] += len(after) / 60.0
        out["same"][0] += float(after[:, cols].sum())
        out["same"][1] += len(after) / 60.0 * len(cols)
        before = sum(float(hsr[q][:, j].sum()) for q in range(h - 1)) + hsr[h - 1][:k, j].sum()
        out["replaced"][0] += float(before)
        out["replaced"][1] += (sum(seconds[: h - 1]) + k) / 60.0
    return out


def _skips(match, series: dict) -> dict:
    """Hard-run decisions wanted above 5.5 m/s, made and skipped, in total and by purpose, split
    by the player's state at that second: tired, late-match fatigued (not tired) or fresh."""
    states = ("tired", "late", "fresh")
    out = {name: {k: [0, 0] for k in states} for name in ("all", *JU_PURPOSES)}
    body = match.physiology
    if body is None:
        return out
    state_of = {}  # player: {period: (first second, state codes)}
    for pid, s in series.items():
        period, t = np.array(s.period), np.array(s.t)
        code = np.where(np.array(s.tired), 0, np.where(np.array(s.tank) < P.LATE_TANK_BELOW, 1, 2))
        state_of[pid] = {
            h: (int(t[period == h][0]), code[period == h]) for h in (1, 2) if (period == h).any()
        }
    for d in body.decisions:
        pid = owner(match.spells, d.player, d.period, d.t_start).player.id
        t0, codes = state_of[pid][d.period]
        state = states[codes[min(max(int(d.t_start) - t0, 0), len(codes) - 1)]]
        for name in ("all", d.purpose.value):
            if name in out:
                out[name][state][0 if d.made else 1] += 1
    return out


def _fang(match, ids, cols, v_by_half, alive_by_half, efforts) -> dict:
    """The 5 min of ball-in-play time with the most distance above 5.5 m/s against the next."""
    col_of = {ids[c]: k for k, c in enumerate(cols)}
    w = FANG_S * HZ
    pairs = zip(v_by_half, alive_by_half, strict=True)
    in_play = [np.where(v[a] > P.HI_SPEED, v[a], 0.0) / HZ for v, a in pairs]
    played = [np.cumsum(a) - 1 for a in alive_by_half]  # ball-in-play frames before each frame
    peaks = _peak(in_play, w, w)
    keys = ("efforts", "length", "duration", "hsr", "carries", "carry_m", "carry_s")
    out = {k: [0.0, 0.0] for k in (*keys, "receptions", "receive_speed")}  # [peak, next]

    def window(h: int, j: int, frame: int) -> int | None:
        """0 in the player's peak window, 1 in the next, else None (ball dead: None)."""
        ph, start = peaks[j]
        frame = min(frame, len(played[h]) - 1)
        if ph != h or not alive_by_half[h][frame]:
            return None
        k = (played[h][frame] - start) // w
        return int(k) if k in (0, 1) else None

    for j, (h, start) in enumerate(peaks):
        if h < 0:
            continue
        for k in (0, 1):
            out["hsr"][k] += float(in_play[h][start + k * w : start + (k + 1) * w, j].sum())
        for a, length, duration in efforts[h][j]:
            k = window(h, j, a)
            if k is not None:
                out["efforts"][k] += 1
                out["length"][k] += length
                out["duration"][k] += duration
    for e in match.events:
        if e.player_id not in col_of or e.type not in (EventType.CARRY, EventType.RECEPTION):
            continue
        j, h, frame = col_of[e.player_id], e.period - 1, round(e.t * HZ)
        k = window(h, j, frame)
        if k is None:
            continue
        if e.type == EventType.CARRY:
            out["carries"][k] += 1
            out["carry_m"][k] += float(np.hypot(e.end.x - e.start.x, e.end.y - e.start.y))
            out["carry_s"][k] += (e.end_t or e.t) - e.t
        else:
            v = v_by_half[h]
            out["receptions"][k] += 1
            out["receive_speed"][k] += float(v[min(frame, len(v) - 1), j])
    return out


def _gaps(efforts: list[tuple[int, float, float]], lo: float, hi: float) -> list[float]:
    """Seconds from the end of each effort to the start of the next, both starting in
    [lo, hi) s."""
    inside = [(a / HZ, a / HZ + d) for a, _, d in efforts if lo <= a / HZ < hi]
    return [b[0] - a[1] for a, b in zip(inside, inside[1:], strict=False)]


def _end(halves: dict[str, list[np.ndarray]], efforts, accdec: list[int]) -> dict:
    first, second = halves["hir"]
    late = second[LATE[0] : LATE[1]]
    out: dict = {
        "minutes": [len(x) / 60.0 for x in halves["td"]],
        "accdec": accdec,
        "hir_early": [float(first[EARLY[0] : EARLY[1]].sum()), (EARLY[1] - EARLY[0]) / 60.0],
        "hir_late": [float(late.sum()), len(late) / 60.0],
        "hir_start": [float(x[:DIP_S].sum()) for x in halves["hir"]],
    }
    for name in ("td", "hsr", "sprint", "hir"):
        out[name] = [float(x.sum()) for x in halves[name]]
    out["gaps"] = {}
    for key, h, lo, hi in (
        ("early", 0, *EARLY),
        ("late", 1, *LATE),
        ("half1", 0, 0, np.inf),
        ("half2", 1, 0, np.inf),
    ):
        gaps = [g for player in efforts[h] for g in _gaps(player, lo, hi)]
        out["gaps"][key] = [float(sum(gaps)), len(gaps)]
    # Per player: distance above 4 m/s per minute in each half (for the load groups).
    out["load"] = [
        [
            float(first[:, j].sum() / out["minutes"][0]),
            float(second[:, j].sum() / out["minutes"][1]),
        ]
        for j in range(first.shape[1])
    ]
    return out


# --- Pooling and report --------------------------------------------------------------------------


def _pct(a: float, b: float) -> float:
    return 100.0 * (a / b - 1.0) if b else float("nan")


def _add(a, b):
    """Add two per-match results: numbers and lists of numbers add up; ``load`` rows (lists of
    lists) and the tanks join."""
    if isinstance(a, dict):
        return {k: _add(a[k], b[k]) for k in a}
    if isinstance(a, list) and a and isinstance(a[0], list):
        return a + b
    if isinstance(a, list):
        return [x + y for x, y in zip(a, b, strict=True)]
    return a + b


def summarise(per_match: list[dict]) -> dict:
    """Pool the sums over matches; each figure is a % change of pooled values."""
    runs: Counter = Counter()
    tanks: list[float] = []
    pooled = None
    for m in per_match:
        runs.update(m["runs"])
        tanks += m["tank_end"]
        rest = {k: v for k, v in m.items() if k not in ("runs", "tank_end")}
        pooled = rest if pooled is None else _add(pooled, rest)
    assert pooled is not None
    out: dict = {"n": len(per_match)}
    out["leifsson"] = {
        key: [_pct(a, d["base"]) for a in d["after"]] for key, d in pooled["leifsson"].items()
    }
    out["leifsson_peak"] = {
        key: d["peak"] / max(d["players"], 1) for key, d in pooled["leifsson"].items()
    }
    out["skips"] = {
        name: {
            state: -100.0 * skipped / max(made + skipped, 1) for state, (made, skipped) in d.items()
        }
        for name, d in pooled["skips"].items()
    }
    out["ju"] = {
        int(w): {name: _pct(d["next"], d["avg"]) for name, d in groups.items()}
        for w, groups in pooled["ju"].items()
    }
    f = pooled["fang"]
    pair = {
        "length": [f["length"][k] / max(f["efforts"][k], 1) for k in (0, 1)],
        "duration": [f["duration"][k] / max(f["efforts"][k], 1) for k in (0, 1)],
        "speed": [f["length"][k] / max(f["duration"][k], 1e-9) for k in (0, 1)],
        "efforts": f["efforts"],
        "hsr": f["hsr"],
        "carries": f["carries"],
        "carry_m": [f["carry_m"][k] / max(f["carries"][k], 1) for k in (0, 1)],
        "carry_speed": [f["carry_m"][k] / max(f["carry_s"][k], 1e-9) for k in (0, 1)],
        "receive_speed": [f["receive_speed"][k] / max(f["receptions"][k], 1) for k in (0, 1)],
    }
    out["fang"] = {
        k: {"peak": v[0], "next": v[1], "pct": _pct(v[1], v[0])} for k, v in pair.items()
    }
    e = pooled["end"]
    m1, m2 = e["minutes"]
    gap = {k: s / max(n, 1) for k, (s, n) in e["gaps"].items()}
    out["end"] = {
        "hir_last15_vs_first15": _pct(
            e["hir_late"][0] / e["hir_late"][1], e["hir_early"][0] / e["hir_early"][1]
        ),
        "hsr_half2_vs_half1": _pct(e["hsr"][1] / m2, e["hsr"][0] / m1),
        "sprint_half2_vs_half1": _pct(e["sprint"][1] / m2, e["sprint"][0] / m1),
        "gap_last15_vs_first15": _pct(gap["late"], gap["early"]),
        "gap_half2_vs_half1": _pct(gap["half2"], gap["half1"]),
        "td_half2_vs_half1": _pct(e["td"][1] / m2, e["td"][0] / m1),
        "accdec_half2_vs_half1": _pct(e["accdec"][1] / m2, e["accdec"][0] / m1),
        "hir_first10_half2_vs_half1": _pct(e["hir_start"][1], e["hir_start"][0]),
        "gap_first15_s": gap["early"],
    }
    load = np.array(e["load"])
    group = np.digitize(load[:, 0], np.quantile(load[:, 0], [1 / 3, 2 / 3]))
    out["end"]["half2_by_load"] = {
        name: _pct(load[group == g, 1].mean(), load[group == g, 0].mean())
        for name, g in (("high", 2), ("moderate", 1), ("low", 0))
    }
    out["runs"] = {
        p.value: {
            "made": runs[f"{p.value}:1"] / len(per_match),
            "skipped": runs[f"{p.value}:0"] / len(per_match),
        }
        for p in RunPurpose
    }
    rate = {k: m / max(minutes, 1e-9) for k, (m, minutes) in pooled["subs"].items()}
    out["subs"] = {
        "rate": rate,
        "minutes": pooled["subs"]["sub"][1] / len(per_match),
        "vs_same": _pct(rate["sub"], rate["same"]),
        "vs_whole": _pct(rate["sub"], rate["whole"]),
        "vs_replaced": _pct(rate["sub"], rate["replaced"]),
    }
    for name in ("tired", "late"):
        out[f"{name}_pct"] = 100.0 * pooled[name][name] / max(pooled[name]["seconds"], 1)
        b = np.array(pooled[f"{name}_blocks"]).reshape(2, len(TIRED_BLOCKS), 2)
        out[f"{name}_blocks_pct"] = (100.0 * b[..., 0] / np.maximum(b[..., 1], 1)).tolist()
    t = np.array(tanks)
    out["tank_end"] = {
        q: float(np.quantile(t, x)) for q, x in (("p10", 0.1), ("p50", 0.5), ("p90", 0.9))
    }
    return out


def _row(label: str, published, values: list[float]) -> str:
    pub = f"{published:>10}" if isinstance(published, str) else f"{published:>+10.0f}"
    cells = "".join(f"{v:>+10.1f}" for v in values)
    return f"  {label:<44}{pub}{cells}"


def format_table(on: dict, off: dict | None = None) -> str:
    """The checks side by side: published, ours (fatigue on), and the no-fatigue control."""
    runs = [on] + ([off] if off else [])
    head = f"  {'%, fatigue on' + (' | off' if off else ''):<44}{'published':>10}"
    head += f"{'on':>10}" + (f"{'off':>10}" if off else "")
    lines = [head]
    lines.append("  Recovery after peaks, minutes 1–5 vs match average [Leifsson2024, Table 1]")
    for key, pub in LEIFSSON.items():
        for k in range(5):
            label = f"{key.replace('_', ' after ')} s peak, min {k + 1}"
            lines.append(_row(label, pub[k], [r["leifsson"][key][k] for r in runs]))
    peaks = []
    for metric, pub in LEIFSSON_PEAK.items():
        for w, value in zip(LEIFSSON_WINDOWS, pub, strict=True):
            ours = " / ".join(f"{r['leifsson_peak'][f'{metric}_{w}']:.0f}" for r in runs)
            peaks.append(f"{metric} {w // 60} min {ours} ({value})")
    lines.append("  Peak m/min, ours (published): " + "; ".join(peaks))
    lines.append("  High-intensity distance after peaks vs match average [Ju2022, p.975]")
    for w, total in JU_TOTAL.items():
        lines.append(_row(f"next {w // 60} min, total", total, [r["ju"][w]["total"] for r in runs]))
        for name, (lo, hi) in JU_PURPOSE.items():
            values = [r["ju"][w][name] for r in runs]
            lines.append(_row(f"next {w // 60} min, {name}", f"{lo} to {hi}", values))
    lines.append(
        "  Hard runs skipped, % of asks, while tired | late-match | neither; Ju2022 after peaks"
    )
    k = on["skips"]
    states = ("tired", "late", "fresh")
    lines.append(_row("all purposes", "–", [k["all"][x] for x in states]))
    for name, (lo, hi) in JU_PURPOSE.items():
        lines.append(_row(name, f"{lo} to {hi}", [k[name][x] for x in states]))
    lines.append("  Next 5 min vs peak 5 min of ball-in-play time [Fang2024, Table 2, Fig. 1]")
    for key in ("hsr", "efforts", "length", "duration", "speed", "carries", "carry_m"):
        pub = FANG.get(key, "–")
        lines.append(_row(key, pub if pub != "–" else "–", [r["fang"][key]["pct"] for r in runs]))
    for key in ("carry_speed", "receive_speed"):
        lines.append(_row(key, "ES <0", [r["fang"][key]["pct"] for r in runs]))
    lines.append(
        "  Effort mean, peak → next (on): "
        f"{on['fang']['length']['peak']:.1f} → {on['fang']['length']['next']:.1f} m, "
        f"{on['fang']['duration']['peak']:.2f} → {on['fang']['duration']['next']:.2f} s, "
        f"{on['fang']['speed']['peak']:.2f} → {on['fang']['speed']['next']:.2f} m/s "
        "(published 19.2 → 14.8 m, 6.3 → 4.3 s, 6.33 → 6.14 m/s)"
    )
    lines.append("  End of the match [Bradley2009; Bradley2013; Chen2025; VighLarsen2018]")
    for key, (pub, ok) in END.items():
        band = "" if ok is None else f"  pass {ok[0]:+d} to {ok[1]:+d}"
        lines.append(_row(key, pub, [r["end"][key] for r in runs]) + band)
    lines.append(
        _row(
            "hir_first10_half2_vs_half1",
            "<0",
            [r["end"]["hir_first10_half2_vs_half1"] for r in runs],
        )
    )
    for name, pub in (("high", -12), ("moderate", 0), ("low", 0)):
        values = [r["end"]["half2_by_load"][name] for r in runs]
        lines.append(_row(f">4 m/s, half 2 vs 1, {name} first-half load", pub, values))
    lines.append(
        f"  Mean time between efforts >5.5 m/s, first 15 min: {on['end']['gap_first15_s']:.0f} s "
        "(published 65 s [Bradley2009, p.163])"
    )
    lines.append(
        "  Substitutes, >5.5 m/s per minute on the pitch [Bradley2013, T IV; Bradley 2014 via "
        "Hills2018]"
    )
    for key, pub, label in (
        ("vs_same", 15, "vs whole-match players, same minutes"),
        ("vs_whole", 27, "vs whole-match players, whole match"),
        ("vs_replaced", 10, "vs the player replaced, before"),
    ):
        lines.append(_row(label, pub, [r["subs"][key] for r in runs]))
    sub = on["subs"]
    lines.append(
        f"  Substitute minutes per match {sub['minutes']:.0f}; m/min sub {sub['rate']['sub']:.1f}, "
        f"whole-match same minutes {sub['rate']['same']:.1f}, whole match "
        f"{sub['rate']['whole']:.1f}, replaced {sub['rate']['replaced']:.1f} "
        "(published 12.4 vs 9.8 whole match)"
    )
    lines.append("  Runs per match (truth.json): measured / skipped")
    for p, d in on["runs"].items():
        if d["made"] or d["skipped"]:
            ref = f"   off {off['runs'][p]['made']:.1f}" if off else ""
            lines.append(f"  {p:<20}{d['made']:>8.1f} / {d['skipped']:<8.1f}{ref}")
    for name, label in (("tired", "Tired moments"), ("late", "Late-match fatigue")):
        blocks = " | ".join(" ".join(f"{v:.0f}" for v in half) for half in on[f"{name}_blocks_pct"])
        lines.append(
            f"  {label}: {on[f'{name}_pct']:.1f}% of outfield player-seconds; % by 15-min block "
            f"(first half | second half, last with added time): {blocks}"
        )
    lines.append(
        f"  Tank at the final whistle: p10 {on['tank_end']['p10']:.3f}, "
        f"median {on['tank_end']['p50']:.3f}, p90 {on['tank_end']['p90']:.3f}"
    )
    return "\n".join(lines)


def _sim_one(seed: int, fatigue: bool) -> dict:
    from secondwind.sim.output import simulate

    return sim_measure(simulate(seed, f"fatigue{seed:04d}", fatigue=fatigue))


def main(argv: list[str] | None = None) -> None:
    from secondwind.sim.batch import parse_seeds

    parser = argparse.ArgumentParser(
        prog="python -m secondwind.sim.fatigue_checks", description=__doc__
    )
    parser.add_argument("--seeds", default="1-30", help="e.g. 1-90 (default 1-30)")
    parser.add_argument(
        "--jobs", type=int, help="worker processes (default: one per physical core)"
    )
    args = parser.parse_args(argv)
    seeds = parse_seeds(args.seeds)
    with ProcessPoolExecutor(max_workers=args.jobs or default_workers()) as ex:
        on = summarise(list(ex.map(partial(_sim_one, fatigue=True), seeds)))
        off = summarise(list(ex.map(partial(_sim_one, fatigue=False), seeds)))
    print(f"{len(seeds)} matches, fatigue on and off (same seeds)")
    print(format_table(on, off))


if __name__ == "__main__":
    main()
