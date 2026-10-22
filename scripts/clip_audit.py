"""Clip audit: every clip of the site's Highlights view checked against the match (decision 38).

    uv run python scripts/clip_audit.py data/synthetic/demo/story app/public/data/story \
        [fan|analyst] [--json out.json]

Rebuilds the clip list as the overlay does (``reel`` in Highlights.tsx, ``queue`` in data.ts,
played from 3 s before a clip's start to 2 s after its end within its half, ``clipFrom``/``clipTo``
in App.tsx)
and reports, per clip: the clip player's top speed and metres above 5.5 m/s (flagged below
5.5 m/s); players the tracking loses for longer than the overlay fills (2.4 s, drawn nowhere) and
the shorter gaps it draws faded; shots, and passes on a clear chance (inside 25 m, no outfield
defender goal-side within 8 m of the line to goal); the ball moving faster than 40 m/s between
frames while in play; team-mates within 0.7 m in play (noted while the ball is dead, when walls and
corner packs may stand closer); players off the pitch; a keeper more than 25 m off his line while
his team defends; a player above 5.5 m/s (over 1 s of tracking) more than 1.5 s after the ball
went dead; a clearance that goes out behind the clearer's own goal line from further out than
``CLEAR_CORNER_DEPTH`` (decision 40); and two clips sharing more than 2 s. Then the match totals.
Synthetic data only.
"""

from __future__ import annotations

import json
import math
import sys

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


def queue(match: dict, feed: dict, clips: dict, hls: list[dict], mode: str) -> list[dict]:
    """data.ts ``queue``: one clip per action."""
    items = [
        dict(id=f"hl:{h['kind']}:{h['player']['id']}:{h['video_s']}", kind=h["kind"],
             player=h["player"]["id"], clock=h["clock"],
             at=h["start_video_s"] if h["kind"] == "recovery_run" else h["video_s"],
             start=0.0 if h["kind"] == "most_ground" else h["start_video_s"], end=h["end_video_s"],
             lapse=h["kind"] == "most_ground", moment=None)
        for h in hls
    ]  # fmt: skip
    moments = []
    for m in feed["moments"]:
        mid = m["moment_id"]
        lines = [e for e in feed["entries"] if e["moment_id"] == mid and e["mode"] == mode
                 and e["shown"]]  # fmt: skip
        if not lines:
            continue
        window = clips.get(m["moment_id"], "default")
        if window is None:
            continue
        start, end = (
            (max(m["video_s"] - MOMENT_BEFORE, 0.0), m["video_s"] + MOMENT_AFTER)
            if window == "default"
            else window
        )
        moments.append(dict(id=m["moment_id"], kind=m["kind"],
                            player=(lines[0].get("player") or {}).get("id"),
                            clock=m["clock"] if window == "default" else clock_label(match, start),
                            at=m["video_s"] if window == "default" else start,
                            start=start, end=end, lapse=False, moment=m["moment_id"]))  # fmt: skip

    def shared(a: dict, b: dict) -> bool:
        ov = min(a["end"], b["end"]) - max(a["start"], b["start"])
        return not a["lapse"] and ov > 0.5 * min(a["end"] - a["start"], b["end"] - b["start"])

    out: list[dict] = []
    for m in moments:
        ln = lambda x: x["end"] - x["start"]  # noqa: E731
        ov = lambda a, b: min(a["end"], b["end"]) - max(a["start"], b["start"])  # noqa: E731
        if any(ov(o, m) > 0.5 * min(ln(o), ln(m)) for o in out):  # the same action (decision 39)
            continue
        k = next((i for i, h in enumerate(items) if shared(h, m)), None)
        if k is None and m["player"]:  # touching the same player's highlight (decision 40)
            pad = CLIP_BEFORE + CLIP_AFTER
            k = next((i for i, h in enumerate(items) if not h["lapse"] and h["moment"] is None
                      and h["player"] == m["player"] and ov(h, m) > -pad), None)  # fmt: skip
        if k is None:
            out.append(m)
        elif items[k]["player"] == m["player"] and items[k]["moment"] is None:
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
    return sorted(items + out, key=lambda i: i["at"])


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
    vt, alive = np.zeros(n), np.zeros(n, bool)
    period, poss = np.zeros(n, int), np.empty(n, object)
    for f, fr in enumerate(frames):
        vt[f], period[f] = vstart[fr["period"]] + fr["t"], fr["period"]
        alive[f], poss[f] = fr["ball_status"] == "alive", fr.get("possession_team")
        ball[f] = fr["ball"]["x"], fr["ball"]["y"]
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

    end = match["periods"][-1]["video_start"] + match["periods"][-1]["duration_s"]
    items = queue(match, feed, match.get("clips", {}), reel(hl, end), mode)
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
        lost = [(p, x, y) for p, x, y in gaps if x < b and y > a and y - x >= 0.3]
        long_ = [g for g in lost if g[2] - g[1] > GAP_FILL_S]
        if long_:
            r["flags"].append(
                "vanish: " + ", ".join(f"{name[p]} {x:.1f}+{y - x:.1f}s" for p, x, y in long_)
            )
        if len(lost) > len(long_):
            r["notes"].append(f"{len(lost) - len(long_)} tracking gaps drawn faded")
        r["shots"] = [f"{name[p]} {k} xG {xg}" for v, p, k, xg in shots if a <= v <= b]
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
                   dead_runs=dead_runs, behind_far=behind_far)  # fmt: skip
        json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)


if __name__ == "__main__":
    main()
