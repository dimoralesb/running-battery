"""Files for the web overlay (BUILD_PLAN "Fri 23"): one match folder in, compact files out.

``python -m secondwind.export data/synthetic/demo/story --out app/public/data/story``

- ``match.json``: teams, players, periods, goals and substitutions on the replay timeline
  (``video_s``: seconds from kick-off with half-time left out, as in ``feed.json``).
- ``positions.bin``: little-endian int16, frames at ``POS_HZ`` × (players + ball) × (x, y) in
  decimetres; ``MISSING`` when a player is off the pitch or not seen.
- ``signals.json``: per player, per second on the pitch from ``start`` (video_s): the battery
  for a typical professional and its 10–90% band, the typical-pro chance, high-speed running
  in the last minute, speed (decimetres per second), red-zone and post-peak flags (shares as
  whole percentages). ``match.json`` also has both teams' running per ball-in-play minute in
  5-min blocks, and where it happened (decision 30): per 15-min block, metres above 5.5 m/s
  and ball-in-play seconds per situation of play (``tools.SITUATIONS``).
- ``feed.json``: the agents' feed, copied as it is.
- ``highlights.json``: the physical highlights (``agents.highlights``, decision 28), with their
  captions (checked by the Verifier's rules) and the run's times for the trail on the pitch.

Reads what the agents read (``agents.tools.MatchData``), never the truth file.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np

from secondwind.agents.feed import FEED
from secondwind.agents.highlights import highlights
from secondwind.agents.tools import SITUATIONS, MatchData
from secondwind.io import TRACKING

POS_HZ = 5
TEAM_BLOCK_S = 300.0  # 5-min blocks for the team-running chart
MISSING = -32768


def team_running(m: MatchData) -> list[dict]:
    """Both teams' high-speed running per ball-in-play minute in ``TEAM_BLOCK_S`` blocks (team
    totals of the outfield players; the "who's doing the running" chart)."""
    out = []
    for per, dur in m.durations.items():
        a = 0.0
        while a < dur - 30.0:
            b = min(a + TEAM_BLOCK_S, dur)
            r = m.team_rates(per, a, b)
            out.append({"video_start": m.video_s(per, a), "video_end": m.video_s(per, b),
                        "clock": m.when(per, a)["clock"], **{
                            team: {"hsr": None if x["hsr"] != x["hsr"] else round(x["hsr"]),
                                   "possession": round(x["possession"], 2),
                                   "in_play_s": x["in_play_s"]}
                            for team, x in r.items()}})  # fmt: skip
            a = b
    return out


def team_situations(m: MatchData) -> list[dict]:
    """Where each team's high-speed running happened (decision 30), per 15-min block
    (``MatchData.blocks``): [metres above 5.5 m/s, ball-in-play seconds] per situation, team
    totals of the outfield players. Additive, so the overlay sums the blocks it needs."""
    out = []
    for per, a, b in m.blocks():
        r = m.team_situations(per, a, b)
        out.append({"video_start": m.video_s(per, a), "video_end": m.video_s(per, b),
                    "from": m.when(per, a)["clock"], "to": m.when(per, b)["clock"],
                    **{team: {k: [round(x[k]["hsr"]), round(x[k]["in_play_s"])] for k in SITUATIONS}
                       for team, x in r.items()}})  # fmt: skip
    return out


def export(folder: Path, out: Path) -> dict:
    m = MatchData(folder)
    out.mkdir(parents=True, exist_ok=True)
    ids = list(m.players)
    col = {pid: j for j, pid in enumerate(ids)}
    hz = round(m.metadata.frame_rate_hz)
    step = hz // POS_HZ
    starts = {p.period: p.start_frame for p in m.metadata.periods}
    rows = []
    with (folder / TRACKING).open() as f:
        for n, line in enumerate(f):
            period = 1 if n < starts.get(2, 1 << 60) else 2
            if (n - starts[period]) % step:
                continue
            fr = json.loads(line)
            row = np.full((len(ids) + 1, 2), MISSING, dtype=np.int16)
            for p in fr["players"]:
                row[col[p["id"]]] = (round(p["x"] * 10), round(p["y"] * 10))
            row[-1] = (round(fr["ball"]["x"] * 10), round(fr["ball"]["y"] * 10))
            rows.append(row)
    pos = np.stack(rows)
    pos.astype("<i2").tofile(out / "positions.bin")

    signals = {}
    for pid, s in m.series.items():
        c = s.cols
        pct = lambda a: np.round(100 * a).astype(int).tolist()  # noqa: E731
        signals[pid] = {
            "start": m.video_s(int(s.period[0]), float(s.t[0])),
            "battery": pct(c["battery"]),
            "lo": pct(c["battery_lo"]) if "battery_lo" in c else None,
            "hi": pct(c["battery_hi"]) if "battery_hi" in c else None,
            "low_chance": pct(c["low_chance"]) if "low_chance" in c else None,
            "hsr_1min": np.round(c["hsr_1min"]).astype(int).tolist(),
            "speed": np.round(10 * c["speed"]).astype(int).tolist(),  # decimetres per second
            "red_zone": c["red_zone"].astype(int).tolist(),
            "post_peak": c["post_peak"].astype(int).tolist(),
        }
    (out / "signals.json").write_text(json.dumps(signals, separators=(",", ":")))

    meta = {
        "match_id": m.metadata.match_id,
        "synthetic": True,
        "pos_hz": POS_HZ,
        "frames": int(pos.shape[0]),
        "ids": ids,
        "missing": MISSING,
        "periods": [
            {
                "period": p.period,
                "video_start": m.video_s(p.period, 0.0),
                "duration_s": p.duration_s,
            }
            for p in m.metadata.periods
        ],  # fmt: skip
        "teams": [
            {"id": t.id, "name": t.name, "side": t.side, "formation": t.formation}
            for t in m.metadata.teams
        ],  # fmt: skip
        "players": [m.players[pid] for pid in ids],
        "team_running": team_running(m),
        "situations": list(SITUATIONS),
        "team_situations": team_situations(m),
        "goals": [
            m.when(g.period, g.t) | {"team": g.team_id, "scorer": g.player_id} for g in m.goals
        ],  # fmt: skip
        "substitutions": [
            m.when(s.period, s.t) | {"team": s.team_id, "off": s.player_out, "on": s.player_in}
            for s in m.metadata.substitutions
        ],  # fmt: skip
    }
    (out / "match.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    (out / "highlights.json").write_text(json.dumps(highlights(m), indent=1, ensure_ascii=False))
    if (folder / FEED).exists():
        shutil.copyfile(folder / FEED, out / FEED)
    return meta


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m secondwind.export", description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--feed", type=Path, help="use this feed.json instead of the folder's")
    args = parser.parse_args(argv)
    meta = export(args.folder, args.out)
    if args.feed:
        shutil.copyfile(args.feed, args.out / FEED)
    size = sum(f.stat().st_size for f in args.out.iterdir()) / 1e6
    print(f"wrote {args.out}: {meta['frames']} frames, {len(meta['ids'])} players, {size:.1f} MB")


if __name__ == "__main__":
    main()
