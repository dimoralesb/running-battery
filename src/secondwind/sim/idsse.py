"""Speed and acceleration distributions of the IDSSE matches [Bassek2025], for calibration.

``uv run python -m secondwind.sim.idsse`` reads the 7 downloaded matches (``scripts/
fetch_idsse.py``; needs the ``calib`` extra for floodlight) and writes, for each match, a small
file of derived numbers next to the raw data: seconds in each speed and acceleration band,
effort counts, and per-player totals. ``sim.batch --idsse`` compares our matches with them
(PLAN §2.5: time in each speed band within ±3 percentage points).

IDSSE is CC BY 4.0 and for calibration only (PLAN §2.2): the raw files and the derived files
both stay in the git-ignored ``data/raw/idsse/``, and nothing from them goes into the demo.

The pipeline is the one our own tracking gets in ``sim.batch``:

1. TRACAB positions at 25 Hz [Bassek2025, p.2], resampled to 10 Hz by linear interpolation.
2. Each player's spell on the pitch is smoothed with ``summary.smooth`` (zero-lag 4th-order
   Butterworth, 1 Hz [Deutsch2025, Methods]). A gap (NaN) in IDSSE means the player is off the
   pitch, not a dropout, so spells are smoothed separately.
3. Speed and tangential acceleration by central differences, without the frames Deutsch2025
   removes as tracking errors (``summary.kinematics``).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from secondwind.sim import params as P
from secondwind.sim.runs import spells
from secondwind.sim.summary import (
    ACCEL_EDGES,
    EFFORT_MINUTES,
    SPEED_EDGES,
    SPRINT_SPEED,
    band_seconds,
    effort_count,
    kinematics,
    smooth,
)

RAW = Path(__file__).resolve().parents[3] / "data" / "raw" / "idsse"
DERIVED = "calib_10hz.json"
SOURCE_HZ = 25.0  # TRACAB [Bassek2025, p.2]
# DFL position codes [Bassek2025, Fig. 2] mapped to our positions. Our mapping: HL/HR are the
# half-space central midfielders, OLM/ORM and LA/RA the wide attacking players.
DFL_POSITIONS = {
    "TW": "GK",
    "IVL": "CB", "IVR": "CB", "IVZ": "CB",
    "LV": "FB", "RV": "FB",
    "DML": "DM", "DMR": "DM", "DMZ": "DM", "DLM": "DM", "DRM": "DM",
    "HL": "CM", "HR": "CM",
    "ZO": "AM",
    "LM": "WM", "RM": "WM", "OLM": "WM", "ORM": "WM", "LA": "WM", "RA": "WM",
    "STL": "CF", "STR": "CF", "STZ": "CF",
}  # fmt: skip
MIN_SPELL_FRAMES = 60  # 6 s at 10 Hz: shorter spells on the pitch are dropped (our choice)


def resample(xy: np.ndarray, source_hz: float = SOURCE_HZ) -> np.ndarray:
    """(frames, ...) positions at ``source_hz`` to the 10 Hz grid by linear interpolation.
    A NaN next to a new frame stays NaN."""
    n = len(xy)
    t_new = np.arange(0.0, (n - 1) / source_hz + 1e-9, 1.0 / P.FRAME_RATE_HZ)
    idx = t_new * source_hz
    i0 = np.minimum(np.floor(idx).astype(int), n - 2)
    w = (idx - i0).reshape(-1, *([1] * (xy.ndim - 1)))
    return (1.0 - w) * xy[i0] + w * xy[i0 + 1]


def on_pitch_spells(col: np.ndarray) -> list[tuple[int, int]]:
    """(start, stop) of the stretches where a player has a position (x and y not NaN)."""
    return spells(np.isfinite(col).all(axis=1), MIN_SPELL_FRAMES)


def player_kinematics(xy: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    """Speed and acceleration of each spell on the pitch of one player, (frames, 2) at 10 Hz."""
    out = []
    for a, b in on_pitch_spells(xy):
        sm = smooth(xy[a:b, None, :])
        speed, acc = kinematics(sm)
        out.append((speed[:, 0], acc[:, 0]))
    return out


def derive_match(folder: Path) -> dict:
    """Read one IDSSE match and reduce it to band seconds and per-player totals."""
    from floodlight.io.dfl import read_position_data_xml

    xy, _, _, teamsheets, _ = read_position_data_xml(folder / "positions.xml", folder / "info.xml")
    groups = ("outfield", "GK")
    speed_s = {g: np.zeros(len(SPEED_EDGES) - 1) for g in groups}
    accel_s = {g: np.zeros(len(ACCEL_EDGES) - 1) for g in groups}
    players: dict[str, dict] = {}
    for teams in xy.values():
        for team in ("Home", "Away"):
            sheet = teamsheets[team].teamsheet
            frames = teams[team].xy
            assert abs(teams[team].framerate - SOURCE_HZ) < 1e-6, teams[team].framerate
            at10 = resample(frames)
            for _, row in sheet.iterrows():
                if "xID" not in row or row["xID"] != row["xID"]:
                    continue
                x = int(row["xID"])
                pos = DFL_POSITIONS.get(row["position"] or "", "?")
                group = "GK" if pos == "GK" else "outfield"
                rec = players.setdefault(
                    str(row["pID"]),
                    dict(team=team, position=pos, minutes=0.0, distance=0.0, hid=0.0, sprint=0.0,
                         top_speed=0.0, sprints=0, high_decels=0),
                )  # fmt: skip
                for speed, acc in player_kinematics(at10[:, 2 * x : 2 * x + 2]):
                    speed_s[group] += band_seconds(speed, SPEED_EDGES)
                    accel_s[group] += band_seconds(acc, ACCEL_EDGES)
                    step = np.nan_to_num(speed) / P.FRAME_RATE_HZ
                    rec["minutes"] += len(speed) / P.FRAME_RATE_HZ / 60.0
                    rec["distance"] += float(step.sum())
                    rec["hid"] += float(step[speed > P.HI_SPEED].sum())
                    rec["sprint"] += float(step[speed > SPRINT_SPEED].sum())
                    rec["top_speed"] = max(rec["top_speed"], float(np.nanmax(speed)))
                    rec["sprints"] += effort_count(speed, "sprint")
                    rec["high_decels"] += effort_count(-acc, "high_decel")
    return {
        "match_id": folder.name,
        "speed_s": {g: v.tolist() for g, v in speed_s.items()},
        "accel_s": {g: v.tolist() for g, v in accel_s.items()},
        "players": players,
    }


def load_derived(root: Path = RAW) -> list[dict]:
    """The derived files already written (empty if IDSSE was never processed here)."""
    if not root.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(root.glob(f"*/{DERIVED}"))]


def band_shares(matches: list[dict], key: str, group: str) -> np.ndarray:
    """Percent of player time in each band, pooled over matches."""
    total = np.sum([m[key][group] for m in matches], axis=0)
    return 100.0 * total / total.sum()


def position_means(matches: list[dict], min_minutes: float = 85.0) -> dict[str, dict]:
    """Per-position means of the players who played at least ``min_minutes`` (our choice):
    totals per match and efforts per 98 min, as in ``sim.batch``."""
    rows: dict[str, list[dict]] = {}
    for m in matches:
        for r in m["players"].values():
            if r["minutes"] >= min_minutes and r["position"] != "?":
                rows.setdefault(r["position"], []).append(r)
    out = {}
    for pos, rs in rows.items():
        out[pos] = {"n": len(rs)}
        for key in ("distance", "hid", "sprint", "top_speed"):
            out[pos][key] = float(np.mean([r[key] for r in rs]))
        for key, name in (("sprints", "sprints_per_98"), ("high_decels", "hdec_per_98")):
            out[pos][name] = float(np.mean([r[key] * EFFORT_MINUTES / r["minutes"] for r in rs]))
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m secondwind.sim.idsse", description=__doc__)
    parser.add_argument("matches", nargs="*", help="IDSSE match ids (default: all downloaded)")
    parser.add_argument("--force", action="store_true", help="redo matches already derived")
    args = parser.parse_args(argv)
    ids = args.matches or sorted(p.name for p in RAW.iterdir() if (p / "positions.xml").exists())
    for match_id in ids:
        out = RAW / match_id / DERIVED
        if out.exists() and not args.force:
            print(f"{match_id}: already derived")
            continue
        out.write_text(json.dumps(derive_match(RAW / match_id), indent=1))
        print(f"{match_id}: wrote {out}")


if __name__ == "__main__":
    main()
