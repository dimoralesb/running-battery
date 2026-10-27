"""Clip audit: every clip of the site's Highlights view checked against the match (decision 38).

    uv run python scripts/clip_audit.py data/synthetic/demo/story app/public/data/story \
        [fan|analyst] [--json out.json]

Rebuilds the clip list as the overlay does (``reel`` in Highlights.tsx, ``queue`` in data.ts,
played from 3 s before a clip's start to 2 s after its end within its half, ``clipFrom``/``clipTo``
in App.tsx; without the clips removed by hand, ``hidden.json``, decision 48)
and reports, per clip: the clip player's top speed and metres above 5.5 m/s (flagged below
5.5 m/s); players the tracking loses for longer than the overlay fills (2.4 s, drawn nowhere) and
the shorter gaps it draws faded; shots, and passes on a clear chance (inside 25 m, no outfield
defender goal-side within 8 m of the line to goal); the ball moving faster than 40 m/s between
frames while in play; team-mates within 0.7 m in play (noted while the ball is dead, when walls and
corner packs may stand closer); players off the pitch; a keeper more than 25 m off his line while
his team defends; a player above 5.5 m/s (over 1 s of tracking) more than 1.5 s after the ball
went dead; a clearance that goes out behind the clearer's own goal line from further out than
``CLEAR_CORNER_DEPTH`` (decision 40); and two clips sharing more than 2 s. Decision 41 adds: a
sprint-turn (over 1 s of tracking above 6 m/s, then within 4 s above 6 m/s the opposite way,
cos < −0.7, ball in play; real matches 0–1.04 per player-hour, IDSSE); a duel, tackle or foul
whose winner (or fouler) is more than 1.5 m from the ball (aerial duel, tackle) or the other
player (ground duel, foul); a completed pass passing within 0.35 m of an outfield opponent while
low (ball under 1 m, away from its first and last 0.3 s); a substitute who comes on away from the
halfway line, or a replaced player who leaves away from a line; and a red-zone clip that shows
under half of the metres above 5.5 m/s of his last minute. Decision 46 adds a shot after the
clip: the play on screen at its last second (its possession) ends in a shot after it (the
overlay runs a clip on to a shot within 20 s, ``toShot``), and leaves team moments out of the
clips (the Stats tab). Decision 45 adds a run into a
team-mate: above 5.5 m/s (over 1 s of tracking) for at least ``MATE_RUN_M``, then (ball in play,
within 2 s) within ``MATE_END_M`` of a team-mate who is not on the ball (a full-back's 38 m
overlap ended at his winger's shoulder, the story match's 9:58; IDSSE has 1.15 per in-play
player-hour, 20 a match, so the total matters more than one clip). Then the match totals.
Synthetic data only.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

from runningbattery.sim.params import CLEAR_CORNER_DEPTH

HALF_L, HALF_W = 52.5, 34.0
HI = 5.5  # m/s, high-speed running
CLIP_BEFORE, CLIP_AFTER = 3.0, 2.0  # App.tsx clipFrom / clipTo
MOMENT_BEFORE, MOMENT_AFTER = 8.0, 4.0  # data.ts, a moment's default window
GAP_FILL_S = 2.4  # data.ts gapFill
PRIORITY = ["longest_run", "recovery_run", "top_speed", "back_to_back", "busiest_minute"]
RESTARTS = {"corner", "free_kick", "throw_in", "goal_kick", "kick_off", "penalty"}
DEAD_GRACE_S = 1.5  # time to stop after the ball goes dead (decision 40)
SHARE_MAX = 2.0  # s two clips of different players may share (data.ts; decision 41)
RUNS_ON_S = 1.0  # a highlight running on past its player's moment gives way to it (decision 42)
OFFSIDE_FLAG_M, OFFSIDE_FLAG_S = 5.0, 2.0  # an offside spell (decision 46)
SHOT_REACH_S = 20.0  # data.ts: a clip runs on to a shot this soon after it (decision 46)
TURN_SPEED, TURN_WITHIN_S, TURN_COS = 6.0, 4.0, -0.7  # sprint-turns (decision 41)
DUEL_FLAG_M = 1.5  # a duel's winner, or a fouler, within reach (decision 41)
PASS_NEAR_M, PASS_NEAR_FLAG_M = 0.6, 0.35  # completed low passes this close to an opponent
SUB_LINE_M = 3.0  # a substitute comes on within this of halfway; the replaced player leaves
# within this of a line
MATE_RUN_M, MATE_END_M, MATE_BALL_M = 15.0, 2.5, 3.0  # a run into a team-mate (decision 45)
MATE_SETTLE = 20  # frames after the run in which he comes to rest


def top_so_far(all_: list[dict], kind: str, now: float, n: int) -> list[dict]:
    best: dict[str, dict] = {}
    for h in all_:
        if h["kind"] != kind or h["video_s"] > now:
            continue
        b = best.get(h["player"]["id"])
        if b is None or h["value"] > b["value"]:
            best[h["player"]["id"]] = h
    return sorted(best.values(), key=lambda h: -h["value"])[:n]


def reel(all_: list[dict], end: float) -> list[dict]:
    """Highlights.tsx ``reel``."""
    out: list[dict] = []
    for h in (h for k in PRIORITY for h in top_so_far(all_, k, end, 2)):
        if not any(
            h["start_video_s"] <= o["end_video_s"] + 3
            and o["start_video_s"] <= h["end_video_s"] + 3
            for o in out
        ):
            out.append(h)
    out.sort(key=lambda h: h["start_video_s"])
    return out + top_so_far(all_, "most_ground", end, 1)


def clock_label(match: dict, v: float) -> str:
    """data.ts ``clockLabel``."""
    p2 = next((p for p in match["periods"] if p["period"] == 2), None)
    second = p2 is not None and v >= p2["video_start"]
    t = v - p2["video_start"] if second else v
    c = t + (2700.0 if second else 0.0)
    end = 5400.0 if second else 2700.0
    mmss = lambda s: f"{int(s // 60)}:{int(s % 60):02d}"  # noqa: E731
    return f"{int(end // 60)}+{mmss(c - end)}" if c >= end else mmss(c)


def to_shot(match: dict, it: dict, shots: list[dict]) -> dict:
    """data.ts ``toShot`` (decision 46): a clip whose possession is still on at its last second
    runs on to the first shot it leads to, if within SHOT_REACH_S of that second, in the same
    half."""
    if it["lapse"]:
        return it
    shown = it["end"] + CLIP_AFTER
    half = next(q for q in reversed(match["periods"]) if q["video_start"] <= it["start"])
    half_end = half["video_start"] + half["duration_s"]
    # The first shot of the play on screen not landed before the clip; none if it shows it.
    on = [x for x in shots if x["possession_from"] <= shown <= x["possession_to"]
          and x["arrive_s"] > it["start"] and x["video_s"] < half_end]  # fmt: skip
    if on and on[0]["arrive_s"] > shown and on[0]["video_s"] - shown <= SHOT_REACH_S:
        return it | dict(end=on[0]["arrive_s"])
    return it


def js_num(x: float) -> str:
    """A number as JavaScript prints it in a template string (803.0 -> "803")."""
    return str(int(x)) if float(x).is_integer() else repr(x)


def queue(
    match: dict,
    feed: dict,
    clips: dict,
    hls: list[dict],
    mode: str,
    shots: list[dict],
    hidden: frozenset[str] = frozenset(),
) -> list[dict]:
    """data.ts ``queue``: one clip per action; no team moments (decision 46: the Stats tab);
    the clips removed by hand (``hidden``, decision 48) taken out last, leaving a gap."""
    items = [
        to_shot(match, dict(
            id=f"hl:{h['kind']}:{h['player']['id']}:{js_num(h['video_s'])}", kind=h["kind"],
            player=h["player"]["id"], clock=h["clock"],
            at=h["start_video_s"] if h["kind"] == "recovery_run" else h["video_s"],
            start=0.0 if h["kind"] == "most_ground" else h["start_video_s"],
            end=h["end_video_s"], lapse=h["kind"] == "most_ground", moment=None), shots)
        for h in hls
    ]  # fmt: skip
    moments = []
    for m in feed["moments"]:
        mid = m["moment_id"]
        lines = [e for e in feed["entries"] if e["moment_id"] == mid and e["mode"] == mode
                 and e["shown"]]  # fmt: skip
        if not lines or not lines[0].get("player"):
            continue  # a team moment: a statistic, in the Stats tab (decision 46)
        window = clips.get(m["moment_id"], "default")
        if window is None:
            continue
        start, end = (
            (max(m["video_s"] - MOMENT_BEFORE, 0.0), m["video_s"] + MOMENT_AFTER)
            if window == "default"
            else window
        )
        moments.append(to_shot(match, dict(
            id=m["moment_id"], kind=m["kind"], player=lines[0]["player"]["id"],
            clock=m["clock"] if window == "default" else clock_label(match, start),
            at=m["video_s"] if window == "default" else start,
            start=start, end=end, lapse=False, moment=m["moment_id"]), shots))  # fmt: skip

    def shared(a: dict, b: dict) -> bool:
        ov = min(a["end"], b["end"]) - max(a["start"], b["start"])
        half = ov > 0.5 * min(a["end"] - a["start"], b["end"] - b["start"])
        other = a["player"] != b["player"] and ov > SHARE_MAX - CLIP_BEFORE - CLIP_AFTER
        return not a["lapse"] and (half or other)  # decision 41: more than SHARE_MAX played

    ln = lambda x: x["end"] - x["start"]  # noqa: E731
    ov = lambda a, b: min(a["end"], b["end"]) - max(a["start"], b["start"])  # noqa: E731
    pad = CLIP_BEFORE + CLIP_AFTER

    out: list[dict] = []
    for m in moments:
        if any(ov(o, m) > 0.5 * min(ln(o), ln(m))  # the same action (decision 39)
               or (o["player"] != m["player"] and ov(o, m) > SHARE_MAX - pad)  # decision 41
               for o in out):  # fmt: skip
            continue
        k = next((i for i, h in enumerate(items) if shared(h, m)), None)
        if k is None and m["player"]:  # touching the same player's highlight (decision 40)
            k = next((i for i, h in enumerate(items) if not h["lapse"] and h["moment"] is None
                      and h["player"] == m["player"] and ov(h, m) > -pad), None)  # fmt: skip
        if k is None:
            out.append(m)
        elif (items[k]["player"] == m["player"] and items[k]["moment"] is None
              and items[k]["end"] <= m["end"] + RUNS_ON_S):  # fmt: skip
            h = items[k]
            items[k] = h | dict(
                moment=m["id"],
                kind=f"{h['kind']}+{m['kind']}",
                start=min(h["start"], m["start"]),
                end=max(h["end"], m["end"]),
            )
        else:
            items.pop(k)
            out.append(m)
    return [i for i in sorted(items + out, key=lambda i: i["at"])
            if i["id"] not in hidden and i["moment"] not in hidden]  # fmt: skip


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    match_dir, export_dir = args[0], args[1]
    mode = args[2] if len(args) > 2 and args[2] in ("fan", "analyst") else "fan"
    meta = json.load(open(f"{match_dir}/metadata.json"))
    events = [json.loads(x) for x in open(f"{match_dir}/events.jsonl")]
    frames = [json.loads(x) for x in open(f"{match_dir}/tracking.jsonl")]
    hl = json.load(open(f"{export_dir}/highlights.json"))
    feed = json.load(open(f"{export_dir}/feed.json"))
    match = json.load(open(f"{export_dir}/match.json"))
    sig = json.load(open(f"{export_dir}/signals.json"))

    team_of, pos_of, name = {}, {}, {}
    for tm in meta["teams"]:
        for p in tm["players"]:
            team_of[p["id"]], pos_of[p["id"]] = tm["id"], p["position"]
            name[p["id"]] = f"{p['id']} #{p['shirt']}"
    home_pos_p1 = next(t for t in meta["teams"] if t["id"] == "home")[
        "attacks_positive_x_in_period_1"
    ]
    vstart = {p["period"]: p["video_start"] for p in match["periods"]}
    ids = sorted(team_of)
    col = {pid: k for k, pid in enumerate(ids)}
    n = len(frames)
    pos = np.full((n, len(ids), 2), np.nan)
    ball = np.zeros((n, 2))
    ball_z = np.zeros(n)
    vt, alive = np.zeros(n), np.zeros(n, bool)
    period, poss = np.zeros(n, int), np.empty(n, object)
    for f, fr in enumerate(frames):
        vt[f], period[f] = vstart[fr["period"]] + fr["t"], fr["period"]
        alive[f], poss[f] = fr["ball_status"] == "alive", fr.get("possession_team")
        ball[f] = fr["ball"]["x"], fr["ball"]["y"]
        ball_z[f] = fr["ball"]["z"]
        for p in fr["players"]:
            pos[f, col[p["id"]]] = p["x"], p["y"]

    def attack_sign(team: str, per: int) -> float:
        """Sign of x of the goal ``team`` attacks."""
        s = 1.0 if (home_pos_p1 if per == 1 else not home_pos_p1) else -1.0
        return s if team == "home" else -s

    def frame_at(v: float) -> int:
        return int(np.clip(np.searchsorted(vt, v - 1e-6), 0, n - 1))

    gaps = []  # (player, from, to): absent between two frames he is in, same half
    for pid, k in col.items():
        idx = np.flatnonzero(~np.isnan(pos[:, k, 0]))
        for h in np.flatnonzero(np.diff(idx) > 1):
            a, b = idx[h], idx[h + 1]
            if period[a] == period[b]:
                gaps.append((pid, vt[a + 1], vt[b - 1] + 0.1))

    speed = np.hypot(*(ball[1:] - ball[:-1]).T) / np.maximum(np.diff(vt), 1e-6)
    ok = alive[1:] & alive[:-1] & (period[1:] == period[:-1])
    jumps = [(float(vt[f + 1]), float(speed[f])) for f in np.flatnonzero(ok & (speed > 40))]

    keeper_far = []  # (keeper, from, to, max metres off his line) while his team defends
    for pid in (p for p in ids if pos_of[p] == "GK"):
        team = team_of[pid]
        goal_x = np.array([-attack_sign(team, per) * HALF_L for per in period])
        off = np.abs(pos[:, col[pid], 0] - goal_x)
        bad = alive & (poss != team) & np.array([p is not None for p in poss]) & (off > 25)
        f = 0
        while f < n:
            if not bad[f]:
                f += 1
                continue
            g = f
            while g + 1 < n and bad[g + 1]:
                g += 1
            far = float(np.nanmax(off[f : g + 1]))
            keeper_far.append((pid, float(vt[f]), float(vt[g] + 0.1), far))
            f = g + 1

    dead_runs = []  # (player, from, to, top m/s, s after dead): above 5.5 m/s once settled
    half_w = 5  # frames: speed over 1 s of tracking, centred
    t_dead = np.full(n, np.nan)  # when the ball last went dead, for each dead frame
    for f in range(n):
        if not alive[f]:
            same = f > 0 and not alive[f - 1] and period[f - 1] == period[f]
            t_dead[f] = t_dead[f - 1] if same else vt[f]
    lo, hi = np.arange(n) - half_w, np.arange(n) + half_w
    ok = (lo >= 0) & (hi < n)
    lo, hi = np.clip(lo, 0, n - 1), np.clip(hi, 0, n - 1)
    dead_all = (
        ok & ~alive & ~alive[lo] & ~alive[hi] & (t_dead[lo] == t_dead) & (t_dead[hi] == t_dead)
    )
    settled = dead_all & (vt - t_dead >= DEAD_GRACE_S)
    v1 = (
        np.hypot(*(pos[hi] - pos[lo]).transpose(2, 0, 1))
        / np.maximum(vt[hi] - vt[lo], 1e-6)[:, None]
    )
    fast = settled[:, None] & (v1 > HI)
    for k, pid in enumerate(ids):
        f = 0
        while f < n:
            if not fast[f, k]:
                f += 1
                continue
            g = f
            while g + 1 < n and fast[g + 1, k] and t_dead[g + 1] == t_dead[f]:
                g += 1
            top = float(np.nanmax(v1[f : g + 1, k]))
            dead_runs.append((pid, float(vt[f]), float(vt[g] + 0.1), top, float(vt[f] - t_dead[f])))
            f = g + 1

    behind_far = []  # (video s, player, metres from his own goal line)
    for e in events:
        if e["type"] != "clearance":
            continue
        own_x = -attack_sign(e["team_id"], e["period"]) * HALF_L
        depth = abs(own_x - e["start"]["x"])
        behind = np.sign(e["end"]["x"]) == np.sign(own_x) and abs(e["end"]["x"]) > HALF_L
        if behind and depth > CLEAR_CORNER_DEPTH:
            behind_far.append((vstart[e["period"]] + e["t"], e["player_id"], round(depth, 1)))

    chances = []  # releases inside 25 m with no outfield defender goal-side within 8 m of the line
    for e in events:
        if e["type"] not in ("pass", "shot") or e.get("subtype") in RESTARTS:
            continue
        team, per = e["team_id"], e["period"]
        a = np.array([e["start"]["x"], e["start"]["y"]])
        goal = np.array([attack_sign(team, per) * HALF_L, 0.0])
        seg = goal - a
        dist = float(np.hypot(*seg))
        if dist > 25:
            continue
        f = frame_at(vstart[per] + e["t"])
        opp = [col[p] for p in ids if team_of[p] != team and pos_of[p] != "GK"]
        q = pos[f, opp] - a
        q = q[~np.isnan(q[:, 0])]
        along = q @ seg / dist
        across = np.abs(seg[0] * q[:, 1] - seg[1] * q[:, 0]) / dist
        if np.any((along > 0) & (along <= dist) & (across <= 8)):
            continue
        back = e["type"] == "pass" and attack_sign(team, per) * (e["end"]["x"] - a[0]) < 0
        chances.append(dict(v=vstart[per] + e["t"], type=e["type"], player=e["player_id"],
                            dist=round(dist, 1), backward=bool(back), to=e.get("related_player_id"),
                            outcome=e.get("outcome")))  # fmt: skip
    shots = [(vstart[e["period"]] + e["t"], e["player_id"], e.get("subtype"), e.get("xg"))
             for e in events if e["type"] == "shot"]  # fmt: skip
    # Each shot's possession (decision 46): its first and last event (export.shots).
    poss_from: dict[tuple[int, int], float] = {}
    poss_to: dict[tuple[int, int], float] = {}
    for e in events:
        if e.get("possession_id") is not None:
            key = (e["period"], e["possession_id"])
            poss_from.setdefault(key, e["t"])
            poss_to[key] = max(e.get("end_t") or e["t"], e["t"])
    shot_play = [dict(video_s=vstart[e["period"]] + e["t"], player=e["player_id"],
                      arrive_s=vstart[e["period"]] + (e.get("end_t") or e["t"]),
                      possession_from=vstart[e["period"]]
                      + poss_from.get((e["period"], e.get("possession_id")), e["t"]),
                      possession_to=vstart[e["period"]]
                      + poss_to.get((e["period"], e.get("possession_id")), e["t"]))
                 for e in events if e["type"] == "shot"]  # fmt: skip

    # Sprint-turns (decision 41): speed over 1 s of tracking (centred) above TURN_SPEED, then
    # within TURN_WITHIN_S above it the opposite way, ball in play; counted where they start.
    turns = []  # (video s, player)
    play_s = {1: 0.0, 2: 0.0}
    for per in (1, 2):
        rows = np.flatnonzero(period == per)
        if not len(rows):
            continue
        p = pos[rows]
        m = len(rows)
        k = np.arange(m)
        vel = p[np.clip(k + half_w, 0, m - 1)] - p[np.clip(k - half_w, 0, m - 1)]
        vel /= (2 * half_w) / 10.0
        sp = np.hypot(*vel.transpose(2, 0, 1))
        found = np.zeros(sp.shape, bool)
        lags = int(TURN_WITHIN_S * 10)
        for lag in range(2 * half_w, lags + 1, half_w):
            b, sb = vel[lag:], sp[lag:]
            cos = (vel[:-lag] * b).sum(-1) / np.maximum(sp[:-lag] * sb, 1e-6)
            found[:-lag] |= (sp[:-lag] > TURN_SPEED) & (sb > TURN_SPEED) & (cos < TURN_COS)
        found[m - lags - half_w :] = False
        found &= alive[rows][:, None]
        start = found & ~np.vstack([np.zeros((1, found.shape[1]), bool), found[:-1]])
        turns += [(float(vt[rows[f]]), ids[j]) for f, j in zip(*np.nonzero(start), strict=True)]
        play_s[per] = float((alive[rows][:, None] & ~np.isnan(p[..., 0])).sum()) / 10.0
    turns.sort()

    # Offside spells (decision 46): an outfield attacker of the team on the ball more than
    # OFFSIDE_FLAG_M beyond the offside line (the second-last opponent, the ball or halfway) for
    # OFFSIDE_FLAG_S or more, ball in play (a run in behind had gone 13 m offside for 6 s; IDSSE
    # 1.1 such spells per attacking player-hour, ours 10.9 before decision 46).
    offside = []  # (video s at the start, player, seconds, metres at most)
    for tm in ("home", "away"):
        mine = [col[q] for q in ids if team_of[q] == tm and pos_of[q] != "GK"]
        theirs = [col[q] for q in ids if team_of[q] != tm]
        sign = np.array([attack_sign(tm, per) for per in period])
        ou = np.where(np.isnan(pos[:, theirs, 0]), -np.inf, pos[:, theirs, 0] * sign[:, None])
        line = np.maximum(np.maximum(np.sort(ou, axis=1)[:, -2], ball[:, 0] * sign), 0.0)
        on = alive & (poss == tm)
        for j in mine:
            beyond = np.where(on, pos[:, j, 0] * sign - line, -np.inf)
            bad = np.nan_to_num(beyond, nan=-np.inf) > OFFSIDE_FLAG_M
            edges = np.diff(np.r_[0, bad.astype(int), 0])
            for f0, f1 in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True):
                if (f1 - f0) / 10.0 >= OFFSIDE_FLAG_S and period[f0] == period[f1 - 1]:
                    offside.append((float(vt[f0]), ids[j], (f1 - f0) / 10.0,
                                    round(float(beyond[f0:f1].max()), 1)))  # fmt: skip

    # Runs into a team-mate (decision 45): above HI over 1 s of tracking (centred) for at least
    # MATE_RUN_M, ending with the ball in play within MATE_END_M of a team-mate not on the ball.
    into_mate = []  # (video s at the end, player, team-mate, metres run)
    running = alive[:, None] & (v1 > HI)
    for k, pid in enumerate(ids):
        mates = [col[q] for q in ids if team_of[q] == team_of[pid] and q != pid]
        f = 0
        while f < n:
            if not running[f, k]:
                f += 1
                continue
            g = f
            while g + 1 < n and running[g + 1, k] and period[g + 1] == period[f]:
                g += 1
            metres = float(np.nansum(np.hypot(*np.diff(pos[f : g + 1, k], axis=0).T)))
            # where he comes to rest: the 2 s after he drops below HI, same half, in play
            h = g + 1
            while h < min(g + MATE_SETTLE, n) and period[h] == period[g] and alive[h]:
                h += 1
            d = np.hypot(*(pos[g:h, mates] - pos[g:h, k][:, None]).transpose(2, 0, 1))
            if metres >= MATE_RUN_M and np.isfinite(d).any():
                e_, m_ = np.unravel_index(int(np.nanargmin(d)), d.shape)
                j, at = mates[m_], g + e_
                if d[e_, m_] < MATE_END_M and np.hypot(*(pos[at, j] - ball[at])) > MATE_BALL_M:
                    into_mate.append((float(vt[at]), pid, ids[j], round(metres)))
            f = g + 1

    # Duels from too far (decision 41): the winner of an aerial duel or a tackle to the ball, the
    # two players of a ground duel or a foul to each other.
    far_duels = []  # (video s, kind, player, metres)
    duel_gaps = {"aerial": [], "ground": [], "tackle": [], "foul": []}
    for e in events:
        if e["type"] not in ("duel", "tackle", "foul"):
            continue
        f = frame_at(vstart[e["period"]] + e["t"])
        me, other = col.get(e["player_id"]), col.get(e.get("related_player_id"))
        if e["type"] == "duel" and e.get("subtype") == "aerial":
            kind, w = "aerial", me if e["outcome"] == "success" else other
            d = float(np.hypot(*(pos[f, w] - ball[f]))) if w is not None else np.nan
        elif e["type"] == "tackle":
            kind, d = "tackle", float(np.hypot(*(pos[f, me] - ball[f])))
        else:
            kind = "ground" if e["type"] == "duel" else "foul"
            d = float(np.hypot(*(pos[f, me] - pos[f, other]))) if other is not None else np.nan
        if np.isnan(d):
            continue
        duel_gaps[kind].append(d)
        if d > DUEL_FLAG_M:
            far_duels.append((vstart[e["period"]] + e["t"], kind, e["player_id"], round(d, 1)))

    # Completed passes through opponents (decision 41): the ball low (under 1 m), away from its
    # first and last 0.3 s, near an outfield opponent before the receiver takes it.
    recs: dict[tuple[int, str], list[float]] = {}
    for e in events:
        if e["type"] == "reception":
            recs.setdefault((e["period"], e["player_id"]), []).append(e["t"])
    completed, near_passes = 0, []  # (video s, passer, opponent, metres)
    for e in events:
        if e["type"] != "pass" or e.get("outcome") != "success" or not e.get("related_player_id"):
            continue
        rt = [t for t in recs.get((e["period"], e["related_player_id"]), [])
              if e["t"] < t < e["t"] + 6]  # fmt: skip
        if not rt:
            continue
        completed += 1
        f0 = frame_at(vstart[e["period"]] + e["t"])
        f1 = frame_at(vstart[e["period"]] + rt[0])
        seg = np.arange(f0 + 3, f1 - 2)
        if not len(seg):
            continue
        opp = [col[p] for p in ids if team_of[p] != e["team_id"] and pos_of[p] != "GK"]
        dd = np.hypot(*(pos[seg][:, opp] - ball[seg, None]).transpose(2, 0, 1))
        dd = np.where((ball_z[seg] < 1.0)[:, None] & ~np.isnan(dd), dd, np.inf)
        k = np.unravel_index(np.argmin(dd), dd.shape)
        if dd[k] < PASS_NEAR_M:
            near_passes.append(
                (float(vt[seg[k[0]]]), e["player_id"], ids[opp[k[1]]], round(float(dd[k]), 2))
            )

    # Substitutions (decision 41): on at the halfway line, off at a line.
    sub_bad = []  # (video s, text)
    for e in events:
        if e["type"] != "substitution":
            continue
        v = vstart[e["period"]] + e["t"]
        f = frame_at(v)
        on, off = col.get(e.get("related_player_id")), col.get(e["player_id"])
        if on is not None and e["t"] > 0:  # half-time substitutes line up for the kick-off
            seen = pos[f : f + 50, on]  # his first 5 s (a dropout may hide the first frames)
            seen = seen[~np.isnan(seen[:, 0])]
            if len(seen) and np.abs(seen[:, 0]).min() > SUB_LINE_M:
                x, y = seen[0]
                sub_bad.append((v, f"{name[ids[on]]} comes on at ({x:.0f}, {y:.0f})"))
        if off is not None and e["t"] > 0:
            seen = pos[max(f - 50, 0) : f, off]  # his last 5 s
            seen = seen[~np.isnan(seen[:, 0])]
            if len(seen):
                to_line = np.minimum(HALF_L - np.abs(seen[:, 0]), HALF_W - np.abs(seen[:, 1]))
                if to_line.min() > SUB_LINE_M:
                    x, y = seen[-1]
                    sub_bad.append((v, f"{name[ids[off]]} leaves at ({x:.0f}, {y:.0f})"))

    end = match["periods"][-1]["video_start"] + match["periods"][-1]["duration_s"]
    moment_at = {mo["moment_id"]: mo for mo in feed["moments"]}
    hidden_json = Path(export_dir) / "hidden.json"
    hidden = frozenset(json.loads(hidden_json.read_text())) if hidden_json.exists() else frozenset()
    items = queue(match, feed, match.get("clips", {}), reel(hl, end), mode, shot_play, hidden)
    report = []
    for it in items:
        half = next(q for q in reversed(match["periods"]) if q["video_start"] <= it["start"])
        h0, h1 = half["video_start"], half["video_start"] + half["duration_s"] - 0.1
        a = 0.0 if it["lapse"] else max(it["start"] - CLIP_BEFORE, h0)
        b = min(it["end"] if it["lapse"] else min(it["end"] + CLIP_AFTER, h1), end - 1)
        if it["lapse"]:  # the whole match at 120×: check only its last seconds
            a = b - 5
        f0, f1 = frame_at(a), frame_at(b)
        r = dict(clock=it["clock"], kind=it["kind"], player=it["player"], id=it["id"],
                 window=[round(a, 1), round(b, 1)], flags=[], notes=[])  # fmt: skip
        pid = it["player"]
        if pid:
            s = sig[pid]
            sp = np.array(s["speed"], float) / 10.0
            i0 = max(math.ceil(a - float(s["start"])), 0)
            i1 = max(math.floor(b - float(s["start"])) + 1, 0)
            seg = sp[i0:i1]
            seg = seg[seg <= 11]
            top = float(seg.max()) if len(seg) else 0.0
            d = np.hypot(*(pos[f0 : f1 + 1, col[pid]] - ball[f0 : f1 + 1]).T)
            near = round(float(np.nanmin(d)), 1) if np.isfinite(d).any() else None
            r.update(top=round(top, 1), above_55=round(float(seg[seg > HI].sum())),
                     nearest_ball=near)  # fmt: skip
            if top < HI:
                r["flags"].append(f"player top {top:.1f} m/s (below 5.5)")
            mo = moment_at.get(it["moment"]) if it["moment"] else None
            if mo is not None and mo["kind"] == "red_zone":
                k = int(float(mo["video_s"]) - float(s["start"]))
                minute = sp[max(k - 59, 0) : k + 1]
                minute = float(minute[(minute > HI) & (minute <= 11)].sum())
                r["red_zone_minute"] = round(minute)
                if float(seg[seg > HI].sum()) < 0.5 * minute:
                    r["flags"].append(
                        f"red zone: clip shows {seg[seg > HI].sum():.0f} of his last minute's "
                        f"{minute:.0f} m above 5.5"
                    )
        lost = [(p, x, y) for p, x, y in gaps if x < b and y > a and y - x >= 0.3]
        long_ = [g for g in lost if g[2] - g[1] > GAP_FILL_S]
        if long_:
            r["flags"].append(
                "vanish: " + ", ".join(f"{name[p]} {x:.1f}+{y - x:.1f}s" for p, x, y in long_)
            )
        if len(lost) > len(long_):
            r["notes"].append(f"{len(lost) - len(long_)} tracking gaps drawn faded")
        r["shots"] = [f"{name[p]} {k} xG {xg}" for v, p, k, xg in shots if a <= v <= b]
        # Its play ends in a shot after it stops (decision 46): the first shot of the possession
        # on screen at its last second that had not landed before it started.
        x = next((x for x in shot_play if x["possession_from"] <= b <= x["possession_to"]
                  and x["arrive_s"] > a and x["video_s"] < h1 + 0.1), None)  # fmt: skip
        if x is not None and x["arrive_s"] > b:  # beyond the overlay's reach: a long possession
            (r["flags"] if x["video_s"] - b <= SHOT_REACH_S else r["notes"]).append(
                f"shot after the clip: {name[x['player']]} at "
                f"{x['video_s']:.1f}s, {x['video_s'] - b:.0f} s after its end"
            )
        for c in (c for c in chances if a <= c["v"] <= b and c["type"] == "pass"):
            r["flags"].append(
                f"pass on a clear chance at {c['v']:.1f}s by {name[c['player']]}, "
                f"{c['dist']} m out, {'backward' if c['backward'] else 'forward'} to {c['to']} "
                f"({c['outcome']})"
            )
        j = [(v, s) for v, s in jumps if a <= v <= b]
        if j:
            r["flags"].append("ball jumps: " + ", ".join(f"{v:.1f}s {s:.0f} m/s" for v, s in j))
        close, close_dead, offp = set(), set(), set()
        for f in range(f0, f1 + 1):
            for tm in ("home", "away"):
                ks = [col[p] for p in ids if team_of[p] == tm and not np.isnan(pos[f, col[p], 0])]
                xy = pos[f, ks]
                dd = np.hypot(*(xy[:, None] - xy[None]).transpose(2, 0, 1))
                for u, w in zip(*np.nonzero(np.triu(dd < 0.7, 1)), strict=True):
                    (close if alive[f] else close_dead).add(
                        "-".join(sorted((ids[ks[u]], ids[ks[w]])))
                    )
            if alive[f]:
                out = (np.abs(pos[f, :, 0]) > HALF_L + 1) | (np.abs(pos[f, :, 1]) > HALF_W + 1)
                offp.update(ids[o] for o in np.flatnonzero(out))
        if close:
            r["flags"].append("team-mates within 0.7 m in play: " + ", ".join(sorted(close)))
        if close_dead:
            r["notes"].append(
                "team-mates within 0.7 m, ball dead: " + ", ".join(sorted(close_dead))
            )
        if offp:
            r["flags"].append("off the pitch in play: " + ", ".join(sorted(offp)))
        kf = [(p, x, y, m) for p, x, y, m in keeper_far if x < b and y > a]
        if kf:
            r["flags"].append("keeper over 25 m off his line while defending: " + ", ".join(
                f"{p} {x:.1f}+{y - x:.1f}s, {m:.1f} m" for p, x, y, m in kf))  # fmt: skip
        dr = [(p, x, y, m, s) for p, x, y, m, s in dead_runs if x < b and y > a]
        if dr:
            r["flags"].append("above 5.5 m/s with the ball dead: " + ", ".join(
                f"{name[p]} {x:.1f}+{y - x:.1f}s ({s:.1f} s after dead), top {m:.1f} m/s"
                for p, x, y, m, s in dr))  # fmt: skip
        tr = [(v, p) for v, p in turns if a <= v <= b]
        if tr:
            r["flags"].append("sprint-turn: " + ", ".join(f"{name[p]} {v:.1f}s" for v, p in tr))
        for v, kind, p, d in (x for x in far_duels if a <= x[0] <= b):
            r["flags"].append(f"{kind} at {v:.1f}s by {name[p]} from {d} m")
        for v, p, o, d in (x for x in near_passes if a <= x[0] <= b and x[3] < PASS_NEAR_FLAG_M):
            r["flags"].append(f"pass by {name[p]} through {name[o]} ({d} m) at {v:.1f}s")
        for v, text in (x for x in sub_bad if a <= x[0] <= b):
            r["flags"].append(f"substitution at {v:.1f}s: {text}")
        for v, p, q, m in (x for x in into_mate if a <= x[0] <= b):
            r["flags"].append(f"run into a team-mate: {name[p]} ran {m} m, ended by {name[q]} "
                              f"at {v:.1f}s")  # fmt: skip
        for v, p, secs, m in (x for x in offside if a <= x[0] <= b):
            r["flags"].append(f"offside: {name[p]} {m} m beyond the line for {secs:.1f} s "
                              f"at {v:.1f}s")  # fmt: skip
        for v, p, depth in (c for c in behind_far if a <= c[0] <= b):
            r["flags"].append(
                f"clearance behind own goal line at {v:.1f}s by {name[p]}, {depth} m out"
            )
        report.append(r)
    for i, r in enumerate(report):
        for q in report[i + 1 :]:
            ov = min(r["window"][1], q["window"][1]) - max(r["window"][0], q["window"][0])
            if ov > 2:
                r["flags"].append(f"shares {ov:.0f} s with {q['clock']} {q['kind']}")
    totals = dict(
        clips=len(report),
        clips_flagged=sum(1 for r in report if r["flags"]),
        clips_player_below_55=sum(1 for r in report if r.get("top", 99) < HI),
        clips_with_vanishing=sum(
            1 for r in report if any(f.startswith("vanish") for f in r["flags"])
        ),
        clips_shared=sum(1 for r in report if any(f.startswith("shares") for f in r["flags"])),
        shots=len(shots),
        clear_chances=len(chances),
        clear_chances_shot=sum(c["type"] == "shot" for c in chances),
        clear_chances_backward_pass=sum(c["type"] == "pass" and c["backward"] for c in chances),
        clear_chances_forward_pass=sum(c["type"] == "pass" and not c["backward"] for c in chances),
        ball_jumps=len(jumps),
        keeper_far_episodes=len(keeper_far),
        dead_ball_fast=len(dead_runs),
        clips_dead_ball_fast=sum(
            1 for r in report if any(f.startswith("above 5.5 m/s with") for f in r["flags"])
        ),
        clearances_behind_far=len(behind_far),
        clips_clearance_behind_far=sum(
            1 for r in report if any(f.startswith("clearance behind") for f in r["flags"])
        ),
        sprint_turns=len(turns),
        sprint_turns_per_player_hour={
            per: round(
                sum(1 for v, _ in turns if (v >= vstart.get(2, 1e9)) == (per == 2))
                / max(play_s[per] / 3600.0, 1e-9),
                2,
            )
            for per in (1, 2)
        },  # fmt: skip
        clips_sprint_turn=sum(
            1 for r in report if any(f.startswith("sprint-turn") for f in r["flags"])
        ),
        duels_far=len(far_duels),
        duel_metres_median={
            k: round(float(np.median(v)), 2) if v else None for k, v in duel_gaps.items()
        },  # fmt: skip
        duels_far_by_kind={k: sum(1 for x in far_duels if x[1] == k) for k in duel_gaps},
        clips_duel_far=sum(
            1
            for r in report
            if any(" from " in f and f.split()[0] in duel_gaps for f in r["flags"])
        ),
        completed_low_passes=completed,
        passes_near_opponent=len(near_passes),
        passes_through_opponent=sum(1 for x in near_passes if x[3] < PASS_NEAR_FLAG_M),
        clips_pass_through=sum(
            1 for r in report if any(f.startswith("pass by") for f in r["flags"])
        ),
        substitutions_off_line=len(sub_bad),
        runs_into_mate=len(into_mate),
        clips_run_into_mate=sum(
            1 for r in report if any(f.startswith("run into a team-mate") for f in r["flags"])
        ),
        offside_spells=len(offside),
        clips_offside=sum(1 for r in report if any(f.startswith("offside:") for f in r["flags"])),
        clips_shot_after=sum(
            1 for r in report if any(f.startswith("shot after the clip") for f in r["flags"])
        ),
        clips_red_zone_short=sum(
            1 for r in report if any(f.startswith("red zone") for f in r["flags"])
        ),
        tracking_gaps=sum(1 for _, x, y in gaps if y - x >= 0.3),
        tracking_gaps_over_fill=sum(1 for _, x, y in gaps if y - x > GAP_FILL_S),
    )
    for r in report:
        extra = (
            f"  top {r['top']} m/s, {r['above_55']} m above 5.5, ball within {r['nearest_ball']} m"
            if "top" in r
            else ""
        )
        print(f"{r['clock']:>7} {r['kind']:<34} {r['player'] or 'team':<5}{extra}")
        for s in r["shots"]:
            print(f"          shot: {s}")
        for x in r["flags"]:
            print(f"          ! {x}")
        for x in r["notes"]:
            print(f"          · {x}")
    print(json.dumps(totals, indent=1))
    if "--json" in sys.argv:
        out = dict(totals=totals, clips=report, chances=chances, keeper_far=keeper_far, jumps=jumps,
                   dead_runs=dead_runs, behind_far=behind_far, turns=turns, far_duels=far_duels,
                   near_passes=near_passes, sub_bad=sub_bad, into_mate=into_mate)  # fmt: skip
        json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)


if __name__ == "__main__":
    main()
