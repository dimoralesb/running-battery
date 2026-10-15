"""Load IDSSE matches with floodlight and print basic facts (day-1 "IDSSE loads" check).

Usage: uv run python scripts/check_idsse.py [MATCH_ID ...]   (default: every downloaded match)
"""

import sys
from pathlib import Path

import numpy as np
from floodlight.io.dfl import read_position_data_xml

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "idsse"


def summarize(match_id: str) -> None:
    folder = RAW / match_id
    xy, possession, ballstatus, teamsheets, pitch = read_position_data_xml(
        folder / "positions.xml", folder / "info.xml"
    )
    print(f"\n{match_id}: pitch {pitch.length:.1f} x {pitch.width:.1f} m")
    alive = np.concatenate([ballstatus[seg].code for seg in ballstatus])
    print(f"  ball in play: {np.mean(alive == 1):.1%} of frames")
    speeds = []
    for segment, teams in xy.items():
        home = teams["Home"]
        minutes = len(home) / home.framerate / 60
        print(f"  {segment}: {len(home)} frames at {home.framerate} Hz ({minutes:.1f} min)")
        for team in ("Home", "Away"):
            pos = teams[team].xy  # (frames, 2 * players), NaN when a player is absent
            v = np.diff(pos, axis=0) * teams[team].framerate
            speeds.append(np.hypot(v[:, 0::2], v[:, 1::2]).ravel())
    s = np.concatenate(speeds)
    s = s[np.isfinite(s)]
    print(
        "  raw speed (no smoothing): "
        f"median {np.median(s):.2f}, 99.9th pct {np.percentile(s, 99.9):.2f} m/s; "
        f"time >5.5 m/s {np.mean(s > 5.5):.2%}, >7 m/s {np.mean(s > 7):.2%}"
    )


if __name__ == "__main__":
    ids = sys.argv[1:] or sorted(p.name for p in RAW.iterdir() if (p / "positions.xml").exists())
    for match_id in ids:
        summarize(match_id)
