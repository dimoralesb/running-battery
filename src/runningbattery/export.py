"""Files for the web overlay (BUILD_PLAN "Fri 23"): one match folder in, compact files out.

``python -m runningbattery.export data/synthetic/demo/story --out app/public/data/story``

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
- ``feed.json``: the agents' feed, copied as it is. ``match.json`` ``clips`` gives each feed
  moment the part of the match its clip shows (decision 38, ``moment_clips``).
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

from runningbattery.agents.feed import FEED
from runningbattery.agents.highlights import highlights
from runningbattery.agents.tools import (
    MAX_PLAUSIBLE_SPEED,
    SITUATIONS,
    MatchData,
    counter_end_t,
)
from runningbattery.engine import params as EP
from runningbattery.io import TRACKING

POS_HZ = 5
TEAM_BLOCK_S = 300.0  # 5-min blocks for the team-running chart
MISSING = -32768
# A feed moment's clip (decision 38): the overlay plays from CLIP_BEFORE seconds before the
# window's start to CLIP_AFTER after its end (``clipFrom``, ``clipTo`` in App.tsx); a moment with
# no window here keeps the overlay's default (DEFAULT_BEFORE / DEFAULT_AFTER around its second).
CLIP_BEFORE, CLIP_AFTER = 3.0, 2.0
DEFAULT_BEFORE, DEFAULT_AFTER = 8.0, 4.0
SECOND_WIND_LOOKBACK_S = 120.0  # second wind: his runs in the 2 min that brought him back
# His hardest minutes: the clip shows the running of the minute up to the moment, the runs above
# 5.5 m/s within RED_ZONE_CLIP_MAX_S of each other that hold most of its metres (decision 41: the
# default window, 8 s before the moment, showed 12 of the 63 m that made it).
RED_ZONE_MINUTE_S = 60.0
# The whole minute since decision 42 (25 s before: A13's minute at 67:20 had its 91 m in five runs
# over 58 s, and the clip showed 45); the overlay fast-forwards between his runs (App.tsx).
RED_ZONE_CLIP_MAX_S = 60.0
RED_ZONE_TO_MOMENT_S = 10.0  # ...and runs on to the moment's second if it is this near, so that
# the battery at the clip's end is the one its line gives (80% on screen against a line's 71%)
# Kept even when the moment's player has no high-speed second: quiet by design, or a counter.
QUIET_KINDS = {"not_tired_tactical", "exposed_on_turnover"}


def team_running(m: MatchData) -> list[dict]:
    """Both teams' high-speed running per ball-in-play minute in ``TEAM_BLOCK_S`` blocks (team
    totals of the outfield players; the "who's doing the running" chart)."""
    out = []
    for per, dur in m.durations.items():
        a = 0.0
        while a < dur - 30.0:
            b = min(a + TEAM_BLOCK_S, dur)
            if dur - b < 30.0:  # a short tail joins the last block (decision 42: the last 25 s
                b = dur  # of a half were in none, and a team clip's numbers missed them)
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


def player_runs(m: MatchData, pid: str) -> list[tuple[float, float, float]]:
    """His runs above 5.5 m/s as (start, end, metres), video_s, from the 1-s speed."""
    s = m.series[pid]
    v = np.array([m.video_s(int(p), float(t)) for p, t in zip(s.period, s.t, strict=True)])
    fast = (s.cols["speed"] > EP.HI_SPEED) & (s.cols["speed"] <= MAX_PLAUSIBLE_SPEED)
    runs: list[tuple[float, float, float]] = []
    i = 0
    while i < len(fast):
        if not fast[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(fast) and fast[j + 1] and v[j + 1] - v[j] < 1.5:
            j += 1
        runs.append((float(v[i]), float(v[j] + 1.0), float(s.cols["speed"][i : j + 1].sum())))
        i = j + 1
    return runs


def red_zone_window(runs: list[tuple[float, float, float]], at: float) -> list[float] | None:
    """[start, end] of the runs above 5.5 m/s in the minute up to ``at`` that hold most of its
    metres within RED_ZONE_CLIP_MAX_S, on to ``at`` if it is within RED_ZONE_TO_MOMENT_S
    (``RED_ZONE_*``); None if he had no such run."""
    lo = at - RED_ZONE_MINUTE_S

    def inside(r: tuple[float, float, float]) -> float:  # his metres of the run in the minute
        a, b, metres = r
        return metres * max(min(b, at + 1.0) - max(a, lo), 0.0) / max(b - a, 1e-6)

    mine = sorted((r for r in runs if inside(r) > 0.0), key=lambda r: r[0])
    best, window = 0.0, None
    for k, first in enumerate(mine):
        metres = 0.0
        for r in mine[k:]:
            if r[1] - first[0] > RED_ZONE_CLIP_MAX_S:
                break
            metres += inside(r)
            if metres >= best:  # the later of two equal: nearer the moment
                best, window = metres, [first[0], r[1]]
    if window and at - window[1] <= RED_ZONE_TO_MOMENT_S:
        # played (CLIP_AFTER on) to the moment's second, whose battery its line gives (decision
        # 42: the clip had played 2 s past it, 62% on screen under a line's 61%)
        window[1] = max(at - CLIP_AFTER, window[0])
    return window


def moment_clips(m: MatchData, feed: dict) -> dict[str, list[float] | None]:
    """What each feed moment's clip shows (decision 38), as [start, end] in video_s, or None for
    a moment with no clip (its player does nothing above 5.5 m/s in it; the line stays in the
    full match's commentary). Moments measured over minutes get the part that shows them:
    caught on the break, the turnover to the end of the counter (``tools.counter_end_t``);
    second wind, his longest run in the 2 min before it; fresh legs, the substitute's longest run
    in his minutes on; his hardest minutes, the running of the minute that made them
    (``RED_ZONE_*``). Moments missing here keep the overlay's default."""
    out: dict[str, list[float] | None] = {}
    runs = {pid: player_runs(m, pid) for pid in m.series}
    for mo in feed.get("moments", []):
        mid, kind, at = mo["moment_id"], mo["kind"], float(mo["video_s"])
        pid = mid.split(":")[1]
        if pid not in m.series:
            continue  # a team moment
        window = None
        if kind == "exposed_on_turnover":
            per, t = int(mo["period"]), float(mo["t"])
            start = next(
                (e for e in m.events if e.period == per and abs(e.t - t) < 0.15
                 and e.phase is not None and e.phase.value == "positive_transition"),
                None,
            )  # fmt: skip
            chain = [e.t for e in m.events if start is not None and e.period == per
                     and e.possession_id == start.possession_id]  # fmt: skip
            window = [at, at + counter_end_t(t, chain) - t]
        elif kind == "red_zone":
            window = red_zone_window(runs[pid], at)
        elif kind in ("second_wind", "fresh_legs"):
            lo = at - SECOND_WIND_LOOKBACK_S if kind == "second_wind" else -1.0
            mine = [r for r in runs[pid] if lo <= r[0] <= at]
            if not mine:
                out[mid] = None
                continue
            a, b, _ = max(mine, key=lambda r: r[2])
            window = [a, b]
        played = (
            (window[0] - CLIP_BEFORE, window[1] + CLIP_AFTER)
            if window
            else (at - DEFAULT_BEFORE - CLIP_BEFORE, at + DEFAULT_AFTER + CLIP_AFTER)
        )
        shows = any(a < played[1] and b > played[0] for a, b, _ in runs[pid])
        if not shows and kind not in QUIET_KINDS:
            out[mid] = None
        elif window:
            out[mid] = [round(window[0], 1), round(window[1], 1)]
    return out


def export(folder: Path, out: Path, feed_path: Path | None = None) -> dict:
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
        # as the facts round (tools.q, 2 digits), so the screen says the line's number (decision
        # 42: 0.885 was "about 89%" in the line and 88% on screen, NumPy's half to even)
        pct = lambda a: [round(round(float(x), 2) * 100) for x in a]  # noqa: E731
        # Each half's first second (video_s) and its index: the first half ends mid-second
        # (2765.7 s in the story match), so one count from ``start`` read the second half a
        # second late (decision 44: 55% on screen, "about 54%" in the line).
        firsts = [int(np.flatnonzero(s.period == per)[0]) for per in np.unique(s.period)]
        signals[pid] = {
            "start": m.video_s(int(s.period[0]), float(s.t[0])),
            "halves": [[m.video_s(int(s.period[k]), float(s.t[k])), k] for k in firsts],
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
    feed_path = feed_path or folder / FEED
    if feed_path.exists():
        meta["clips"] = moment_clips(m, json.loads(feed_path.read_text()))
    (out / "match.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    (out / "highlights.json").write_text(json.dumps(highlights(m), indent=1, ensure_ascii=False))
    if feed_path.exists():
        shutil.copyfile(feed_path, out / FEED)
    return meta


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m runningbattery.export", description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--feed", type=Path, help="use this feed.json instead of the folder's")
    args = parser.parse_args(argv)
    meta = export(args.folder, args.out, args.feed)
    size = sum(f.stat().st_size for f in args.out.iterdir()) / 1e6
    print(f"wrote {args.out}: {meta['frames']} frames, {len(meta['ids'])} players, {size:.1f} MB")


if __name__ == "__main__":
    main()
