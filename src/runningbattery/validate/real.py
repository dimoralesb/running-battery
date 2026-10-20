"""Real-data conclusion check (BUILD_PLAN §3, run 4; PLAN §2.6, point 1).

``python -m runningbattery.validate.real data/synthetic/dev [--json out.json]``

Runs the estimator with the product's settings (broadcast mode, professional prior, k = 4) on
the 7 IDSSE matches [Bassek2025] (``sim.idsse.to_match``; CC BY 4.0, calibration only, never in
the demo or the repo) and on a synthetic batch, and measures the same things on both, from the
same smoothed speed the estimator reads. There is no fatigue truth in real matches, so this
compares conclusions, not accuracy: where the two disagree, the synthetic results may not carry
over to real play.

Whole-match outfield players only (on the pitch for every second, not sent off), as in
``sim.fatigue_checks``:

- **Post-peak drop** [Leifsson2024, Table 1]: each player's most intense 1- and 5-min window of
  distance above 5.5 m/s (with 5 min of the half left after it), then the same distance in each
  of the next 5 minutes against the player's match average per minute without the peak.
- **Second half** [Bradley2009, Fig. 2, p.162]: distance above 4 m/s per minute in min 75–90
  against min 0–15; distance above 5.5 m/s and total distance per minute, second half against
  first.
- **Battery dip**: each player's lowest battery (median), and the share of players who went
  below ``LOW_BATTERY`` at all; the tired flag's share of player-seconds.
- **Typical-pro chance** (``low_chance``, calibrated): each player's highest value and the share
  of player-seconds at 0.1 or more (the raw chance too).
- **Red-zone spells**: runs of red-zone seconds per player and match; the post-peak share of
  player-seconds.
- **Load**: energy since kick-off at the final whistle, kJ/kg (published 61.1 ± 6.6
  [Osgnach2010, p.174]), and total distance.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from runningbattery import default_workers
from runningbattery.engine import params as EP
from runningbattery.engine.estimate import Estimate, compute
from runningbattery.engine.signals import red_zone, spells, tired
from runningbattery.io import Match, read_match
from runningbattery.sim.fatigue_checks import EARLY, HIR_SPEED, LATE, _leifsson, _per_second
from runningbattery.sim.idsse import RAW, to_match

WINDOWS = (60, 300)  # the 1- and 5-min peaks [Leifsson2024]
CHANCE_AT = 0.1
PUBLISHED_ENERGY = (61.1, 6.6)  # kJ/kg, mean ± SD [Osgnach2010, p.174]


def whole_match(match: Match, est: Estimate, left_out: list[str] = ()) -> np.ndarray:
    """(players,) outfield players on the pitch for every second, not in ``left_out``."""
    gk = {p.id for team in match.metadata.teams for p in team.players if p.position == "GK"}
    ids = est.tracks.ids
    return est.seconds.on.all(axis=0) & np.array([i not in gk and i not in left_out for i in ids])


def measure(match: Match, left_out: list[str] = ()) -> dict:
    """Sums (which pool by adding) and per-player values for one match (module docstring)."""
    est = compute(match)
    whole = whole_match(match, est, left_out)
    tr, s = est.tracks, est.seconds
    halves: dict[str, list[np.ndarray]] = {"hsr": [], "td": [], "hir": []}
    for h in (1, 2):
        v = np.nan_to_num(tr.speed[tr.period == h][:, whole])
        step = v * EP.DT
        halves["td"].append(_per_second(step))
        halves["hsr"].append(_per_second(np.where(v > EP.HI_SPEED, step, 0.0)))
        halves["hir"].append(_per_second(np.where(v > HIR_SPEED, step, 0.0)))
    hot, post = red_zone(s)
    red = np.logical_or.reduce(list(hot.values()))
    flag = tired(s)
    cols = np.flatnonzero(whole)
    keep = s.on[:, whole]

    def count(x: np.ndarray) -> int:
        return int(x[:, whole][keep].sum())

    first, second = halves["hir"]
    return {
        "match_id": match.metadata.match_id,
        "players": int(whole.sum()),
        "leifsson": {str(w): _leifsson(halves["hsr"], w) for w in WINDOWS},
        "minutes": [len(x) / 60.0 for x in halves["td"]],
        "td": [float(x.sum()) for x in halves["td"]],
        "hsr": [float(x.sum()) for x in halves["hsr"]],
        "hir_early": [float(first[EARLY[0] : EARLY[1]].sum()), (EARLY[1] - EARLY[0]) / 60.0],
        "hir_late": [float(second[LATE[0] : LATE[1]].sum()), len(second[LATE[0] : LATE[1]]) / 60],
        "seconds": int(keep.sum()),
        "tired_s": count(flag),
        "post_peak_s": count(post),
        "red_s": count(red),
        "chance_s": count(s.low_chance >= CHANCE_AT),
        "chance_raw_s": count(s.low_chance_raw >= CHANCE_AT),
        "battery_min": s.battery[:, cols].min(axis=0).tolist(),
        "chance_max": s.low_chance[:, cols].max(axis=0).tolist(),
        "chance_raw_max": s.low_chance_raw[:, cols].max(axis=0).tolist(),
        "red_spells": [
            sum(len(spells(red[s.period == h, j])) for h in (1, 2)) for j in cols.tolist()
        ],
        "energy": s.energy[-1, cols].tolist(),
        "distance_km": [
            float(sum(x[:, k].sum() for x in halves["td"]) / 1000) for k in range(len(cols))
        ],
    }


def synthetic_measure(folder: Path) -> dict:
    return measure(read_match(folder))


def idsse_measure(folder: Path) -> dict:
    c = to_match(folder)
    out = measure(c.match, c.sent_off)
    out["sent_off"], out["no_position"] = c.sent_off, c.no_position
    return out


def _pct(a: float, b: float) -> float:
    return 100.0 * (a / b - 1.0) if b else float("nan")


def _q(values: list[float]) -> list[float]:
    return [float(x) for x in np.quantile(values, (0.1, 0.5, 0.9))]


def summarise(parts: list[dict]) -> dict:
    """Pooled figures for one data set."""
    out: dict = {"matches": len(parts), "players": sum(p["players"] for p in parts)}
    for w in map(str, WINDOWS):
        base = sum(p["leifsson"][w]["base"] for p in parts)
        after = np.sum([p["leifsson"][w]["after"] for p in parts], axis=0)
        peak = sum(p["leifsson"][w]["peak"] for p in parts)
        n = sum(p["leifsson"][w]["players"] for p in parts)
        out[f"post_peak_{w}"] = [_pct(a, base) for a in after]
        out[f"peak_{w}_m_per_min"] = peak / max(n, 1)
    m = np.sum([p["minutes"] for p in parts], axis=0)
    for name in ("td", "hsr"):
        x = np.sum([p[name] for p in parts], axis=0)
        out[f"{name}_half2_vs_half1"] = _pct(x[1] / m[1], x[0] / m[0])
    early, late = (np.sum([p[k] for p in parts], axis=0) for k in ("hir_early", "hir_late"))
    out["hir_last15_vs_first15"] = (
        _pct(late[0] / late[1], early[0] / early[1]) if late[1] and early[1] else float("nan")
    )
    seconds = sum(p["seconds"] for p in parts)
    for name in ("tired_s", "post_peak_s", "red_s", "chance_s", "chance_raw_s"):
        out[name.removesuffix("_s") + "_share"] = sum(p[name] for p in parts) / seconds
    per = {
        k: [x for p in parts for x in p[k]]
        for k in (
            "battery_min",
            "chance_max",
            "chance_raw_max",
            "red_spells",
            "energy",
            "distance_km",
        )
    }
    for k, v in per.items():
        out[k] = _q(v)
    out["below_low_battery"] = float(np.mean(np.array(per["battery_min"]) < EP.LOW_BATTERY))
    out["energy_mean_sd"] = [float(np.mean(per["energy"])), float(np.std(per["energy"]))]
    out["red_spells_mean"] = float(np.mean(per["red_spells"]))
    return out


ROWS = (
    (
        "post_peak_300",
        "HSR after a 5-min peak, min 1–5, % vs match avg",
        "−45 −29 −13 −8 −4 [Leifsson2024, T1]",
    ),
    (
        "post_peak_60",
        "HSR after a 1-min peak, min 1–5, % vs match avg",
        "−29 −6 −3 −2 −2 [Leifsson2024, T1]",
    ),
    ("peak_300_m_per_min", "5-min HSR peak, m/min", "22 [Leifsson2024, T1]"),
    ("peak_60_m_per_min", "1-min HSR peak, m/min", "62 [Leifsson2024, T1]"),
    ("hir_last15_vs_first15", ">4 m/s, min 75–90 vs 0–15, %", "−21 [Bradley2009, F2]"),
    (
        "hsr_half2_vs_half1",
        ">5.5 m/s per min, 2nd half vs 1st, %",
        "no change [Bradley2009, p.162]",
    ),
    ("td_half2_vs_half1", "total distance per min, 2nd half vs 1st, %", "lower [Chen2025]"),
    (
        "battery_min",
        "lowest battery per player, 10 / 50 / 90%",
        "0.79 ± 0.06, university players [Sutcliffe2025, F3]",
    ),
    ("below_low_battery", "players whose battery went below 0.50", ""),
    ("tired_share", "tired flag, share of player-seconds", ""),
    ("chance_max", "highest typical-pro chance per player, 10 / 50 / 90%", ""),
    ("chance_share", "player-seconds with chance ≥ 0.1", ""),
    ("chance_raw_share", "player-seconds with raw chance ≥ 0.1", ""),
    ("red_spells", "red-zone spells per player, 10 / 50 / 90%", ""),
    ("red_share", "red-zone share of player-seconds", ""),
    ("post_peak_share", "post-peak share of player-seconds", ""),
    (
        "energy_mean_sd",
        "energy at the final whistle, kJ/kg, mean ± SD",
        "61.1 ± 6.6 [Osgnach2010, p.174]",
    ),
    ("distance_km", "total distance per player, km, 10 / 50 / 90%", ""),
)


def _cell(v) -> str:
    if isinstance(v, list) and len(v) == 2:
        return f"{v[0]:.1f} ± {v[1]:.1f}"
    if isinstance(v, list) and len(v) == 3:
        return " / ".join(f"{x:.2f}" for x in v)
    if isinstance(v, list):
        return " ".join(f"{x:+.0f}" for x in v)
    return f"{v:.3f}" if abs(v) < 1 else f"{v:+.1f}" if v < 0 else f"{v:.1f}"


def format_table(real: dict, synth: dict) -> str:
    """Markdown table: published, IDSSE and synthetic side by side."""
    lines = [
        f"| Measure | IDSSE ({real['matches']} matches, {real['players']} players) | "
        f"Synthetic ({synth['matches']} matches, {synth['players']} players) | Published |",
        "|---|---|---|---|",
    ]
    for key, label, pub in ROWS:
        lines.append(f"| {label} | {_cell(real[key])} | {_cell(synth[key])} | {pub} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m runningbattery.validate.real", description=__doc__
    )
    parser.add_argument("synthetic", type=Path, help="a folder of synthetic match folders")
    parser.add_argument("--matches", type=int, help="only the first N synthetic matches")
    parser.add_argument("--json", type=Path, help="also write both summaries here")
    parser.add_argument("--jobs", type=int)
    args = parser.parse_args(argv)
    real_folders = sorted(p for p in RAW.iterdir() if (p / "positions.xml").exists())
    synth_folders = sorted(p for p in args.synthetic.iterdir() if p.is_dir())[: args.matches]
    with ProcessPoolExecutor(max_workers=args.jobs or default_workers()) as ex:
        real_parts = list(ex.map(idsse_measure, real_folders))
        synth_parts = list(ex.map(synthetic_measure, synth_folders))
    for p in real_parts:
        if p["sent_off"] or p["no_position"]:
            print(f"{p['match_id']}: sent off {p['sent_off']}, no position {p['no_position']}")
    real, synth = summarise(real_parts), summarise(synth_parts)
    print(format_table(real, synth))
    if args.json:
        args.json.write_text(json.dumps({"idsse": real, "synthetic": synth}, indent=1))


if __name__ == "__main__":
    main()
