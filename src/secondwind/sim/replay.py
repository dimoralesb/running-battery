"""Replay a generated match, to judge the movement by eye.

    python -m secondwind.sim.replay data/synthetic/m0001 --start 12:00 --seconds 120

writes ``replay.html`` into the match folder: a self-contained page (no libraries) with the pitch,
22 players, the ball (drawn larger when it is in the air), ball status, possession, score and
the latest event, with play, pause, speed and a time slider. ``--purposes`` also labels each
high-intensity run with its purpose from ``truth.json`` (validation data: for debugging only).

``--gif`` and ``--stills`` draw with matplotlib instead (``uv sync --extra replay``): an animated
GIF of the window, or one PNG of evenly spaced frames.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

from secondwind.io import EVENTS, METADATA, TRACKING, TRUTH

PURPOSE_SHORT = {
    "push_up_pitch": "PUSH",
    "break_into_box": "BOX",
    "run_in_behind": "BEHIND",
    "over_underlap": "OVERLAP",
    "run_with_ball": "CARRY",
    "move_to_receive": "SHOW",
    "support_play": "SUPPORT",
    "interception": "INTERCEPT",
    "recovery_run": "RECOVER",
    "covering": "COVER",
    "close_down": "PRESS",
    "other": "OTHER",
}
COLOURS = ("#d62728", "#1f77b4")  # home, away


def parse_clock(text: str) -> float:
    """``12:30`` or ``750`` (seconds) on the match clock."""
    if ":" in text:
        minutes, seconds = text.split(":")
        return 60.0 * int(minutes) + float(seconds)
    return float(text)


def load_window(folder: Path, start: float, seconds: float, purposes: bool = False) -> dict:
    """Frames, events and (optionally) run labels for ``seconds`` from match clock ``start``."""
    meta = json.loads((folder / METADATA).read_text())
    rate = meta["frame_rate_hz"]
    ids = [p["id"] for team in meta["teams"] for p in team["players"]]
    shirts = [p["shirt"] for team in meta["teams"] for p in team["players"]]
    team_ids = [team["id"] for team in meta["teams"]]

    # Frames are in order at a fixed rate; find the first frame at or after ``start``.
    first = 0
    for period in meta["periods"]:
        clock0 = 0.0 if period["period"] == 1 else 2700.0
        if start < clock0 + period["duration_s"]:
            first = period["start_frame"] + max(0, round((start - clock0) * rate))
            break
        first = period["end_frame"]
    count = round(seconds * rate)
    frames = []
    with (folder / TRACKING).open() as f:
        for line in itertools.islice(f, first, first + count):
            fr = json.loads(line)
            seen = {p["id"]: (p["x"], p["y"]) for p in fr["players"]}
            holder = fr.get("possession_team")
            ball = fr["ball"]
            frames.append(
                {
                    "clock": fr["clock"],
                    "period": fr["period"],
                    "t": fr["t"],
                    "alive": fr["ball_status"] == "alive",
                    "poss": team_ids.index(holder) if holder in team_ids else -1,
                    "ball": [ball["x"], ball["y"], ball["z"]],
                    "xy": [seen.get(pid) for pid in ids],
                }
            )
    if not frames:
        raise SystemExit(f"no frames at {start} s")
    lo, hi = frames[0]["clock"], frames[-1]["clock"]
    events = []
    with (folder / EVENTS).open() as f:
        for line in f:
            e = json.loads(line)
            if lo - 30 <= e["clock"] <= hi:
                who = ids.index(e["player_id"]) if e.get("player_id") in ids else -1
                label = e["type"] + (f" ({e['subtype']})" if e.get("subtype") else "")
                events.append(
                    {"clock": e["clock"], "label": label, "who": who, "score": e["score"]}
                )
    runs = []
    if purposes and (folder / TRUTH).exists():
        truth = json.loads((folder / TRUTH).read_text())
        for r in truth.get("runs", []):
            clock0 = 0.0 if r["period"] == 1 else 2700.0
            a, b = clock0 + r["t_start"], clock0 + r["t_end"]
            if b >= lo and a <= hi:
                runs.append(
                    {"a": a, "b": b, "who": ids.index(r["player_id"]), "what": r["purpose"]}
                )
    return {
        "match_id": meta["match_id"],
        "teams": [team["name"] for team in meta["teams"]],
        "shirts": shirts,
        "positions": [p["position"] for team in meta["teams"] for p in team["players"]],
        "rate": rate,
        "frames": frames,
        "events": events,
        "runs": runs,
    }


def write_html(window: dict, out: Path) -> None:
    payload = dict(window, colours=COLOURS, short=PURPOSE_SHORT)
    data = json.dumps(payload, separators=(",", ":"))
    out.write_text(
        HTML.replace("__TITLE__", f"Replay {window['match_id']}").replace("__DATA__", data)
    )


def clock_text(clock: float) -> str:
    return f"{int(clock // 60):02d}:{int(clock % 60):02d}"


def draw_pitch(ax) -> None:
    from matplotlib.patches import Arc, Circle, Rectangle

    ax.set_facecolor("#3a7d44")
    line = dict(color="white", lw=1.2, fill=False)
    ax.add_patch(Rectangle((-52.5, -34), 105, 68, **line))
    ax.plot([0, 0], [-34, 34], color="white", lw=1.2)
    ax.add_patch(Circle((0, 0), 9.15, **line))
    for s in (-1, 1):
        ax.add_patch(Rectangle((s * 52.5 - (16.5 if s > 0 else 0), -20.16), 16.5, 40.32, **line))
        ax.add_patch(Rectangle((s * 52.5 - (5.5 if s > 0 else 0), -9.16), 5.5, 18.32, **line))
        ax.add_patch(
            Arc(
                (s * 41.5, 0),
                18.3,
                18.3,
                theta1=127 if s > 0 else -53,
                theta2=233 if s > 0 else 53,
                color="white",
                lw=1.2,
            )
        )
        ax.plot([s * 52.5, s * 54.5, s * 54.5, s * 52.5], [-3.66, -3.66, 3.66, 3.66], color="white")
    ax.set_xlim(-56, 56)
    ax.set_ylim(-37, 37)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])


def draw_frame(ax, window: dict, k: int, trail_s: float = 0.0) -> None:
    """One frame; ``trail_s`` also draws each player's path over the last seconds."""
    fr = window["frames"][k]
    ax.clear()
    draw_pitch(ax)
    back = window["frames"][max(0, k - round(trail_s * window["rate"])) : k + 1]
    for j in range(len(fr["xy"])):
        path = [f["xy"][j] for f in back if f["xy"][j] is not None]
        if len(path) > 1:
            ax.plot(*zip(*path, strict=True), color=COLOURS[0 if j < 11 else 1], lw=1, alpha=0.6)
    for j, xy in enumerate(fr["xy"]):
        if xy is None:
            continue
        team = 0 if j < 11 else 1
        gk = window["positions"][j] == "GK"
        ax.scatter(*xy, s=120, c="#f5d000" if gk else COLOURS[team], edgecolors="white", zorder=3)
        ax.text(
            *xy,
            str(window["shirts"][j]),
            color="white",
            fontsize=6,
            ha="center",
            va="center",
            zorder=4,
        )
        for r in window["runs"]:
            if r["who"] == j and r["a"] <= fr["clock"] <= r["b"]:
                ax.text(
                    xy[0],
                    xy[1] + 2.2,
                    PURPOSE_SHORT[r["what"]],
                    color="black",
                    fontsize=5,
                    ha="center",
                    zorder=5,
                    bbox=dict(fc="white", ec="none", pad=0.5),
                )
    bx, by, bz = fr["ball"]
    ax.scatter(bx, by, s=25 + 6 * bz, c="white", edgecolors="black", zorder=6)
    holder = window["teams"][fr["poss"]] if fr["poss"] >= 0 else "contested"
    status = "in play" if fr["alive"] else "dead ball"
    last = [e for e in window["events"] if e["clock"] <= fr["clock"]]
    score = last[-1]["score"] if last else {"home": 0, "away": 0}
    title = (
        f"{window['teams'][0]} {score['home']}–{score['away']} {window['teams'][1]}   "
        f"{clock_text(fr['clock'])}   {status}   possession: {holder}"
    )
    ax.set_title(title, fontsize=8)
    if last:
        ax.text(-55, -36.2, last[-1]["label"], fontsize=7, color="white")


def write_stills(window: dict, out: Path, n: int) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cols = 2
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 6, rows * 4))
    frames = len(window["frames"])
    for i, ax in enumerate(axes.flat):
        if i < n:
            draw_frame(ax, window, min(frames - 1, (i + 1) * frames // n), trail_s=3.0)
        else:
            ax.axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def write_gif(window: dict, out: Path, fps: int) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter

    fig, ax = plt.subplots(figsize=(7.5, 5))
    every = max(1, round(window["rate"] / fps))
    ks = range(0, len(window["frames"]), every)
    anim = FuncAnimation(fig, lambda k: draw_frame(ax, window, k), frames=ks)
    anim.save(out, writer=PillowWriter(fps=fps))
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m secondwind.sim.replay", description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--start", default="10:00", help="match clock, MM:SS or seconds")
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--purposes", action="store_true", help="label runs from truth.json")
    parser.add_argument("--out", type=Path, help="default: replay.html (or .gif/.png) in folder")
    parser.add_argument("--gif", action="store_true", help="animated GIF (needs matplotlib)")
    parser.add_argument("--fps", type=int, default=5, help="GIF frames per second")
    parser.add_argument("--stills", type=int, help="PNG of this many frames (needs matplotlib)")
    args = parser.parse_args(argv)

    window = load_window(args.folder, parse_clock(args.start), args.seconds, args.purposes)
    if args.stills:
        out = args.out or args.folder / "replay.png"
        write_stills(window, out, args.stills)
    elif args.gif:
        out = args.out or args.folder / "replay.gif"
        write_gif(window, out, args.fps)
    else:
        out = args.out or args.folder / "replay.html"
        write_html(window, out)
    print(f"wrote {out}")


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root { --bg: #f4f4f2; --fg: #1d1d1b; --muted: #6b6b66; --grass: #3a7d44; }
@media (prefers-color-scheme: dark) { :root { --bg: #171717; --fg: #ececea; --muted: #a3a39e; } }
body { margin: 0; padding: 16px; background: var(--bg); color: var(--fg);
       font: 14px/1.4 system-ui, sans-serif; }
main { max-width: 1100px; margin: 0 auto; }
canvas { width: 100%; height: auto; background: var(--grass); border-radius: 6px; display: block; }
.bar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 10px 0; }
.bar input[type=range] { flex: 1; min-width: 160px; }
#status { font-variant-numeric: tabular-nums; }
#event { color: var(--muted); min-height: 1.4em; }
button, select { font: inherit; }
</style></head><body><main>
<div class="bar"><strong id="score"></strong><span id="status"></span></div>
<canvas id="pitch" width="1120" height="760"></canvas>
<div class="bar">
  <button id="play">Pause</button>
  <select id="speed"><option>0.5</option><option selected>1</option><option>2</option>
    <option>4</option></select>
  <input id="seek" type="range" min="0" value="0">
</div>
<div id="event"></div>
</main><script>
const D = __DATA__;
const cv = document.getElementById("pitch"), g = cv.getContext("2d");
const W = cv.width, H = cv.height, S = W / 112, X = x => (x + 56) * S, Y = y => (37 - y) * S;
const seek = document.getElementById("seek"); seek.max = D.frames.length - 1;
let k = 0, playing = true, last = null, acc = 0;
const mmss = c => String(Math.floor(c / 60)).padStart(2, "0") + ":" +
  String(Math.floor(c % 60)).padStart(2, "0");
function line(pts) { g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(X(x), Y(y)) :
  g.moveTo(X(x), Y(y))); g.stroke(); }
function pitch() {
  g.fillStyle = "#3a7d44"; g.fillRect(0, 0, W, H);
  g.strokeStyle = "rgba(255,255,255,0.85)"; g.lineWidth = 2;
  g.strokeRect(X(-52.5), Y(34), 105 * S, 68 * S); line([[0, -34], [0, 34]]);
  g.beginPath(); g.arc(X(0), Y(0), 9.15 * S, 0, 2 * Math.PI); g.stroke();
  for (const s of [-1, 1]) {
    line([[s * 52.5, -20.16], [s * 36, -20.16], [s * 36, 20.16], [s * 52.5, 20.16]]);
    line([[s * 52.5, -9.16], [s * 47, -9.16], [s * 47, 9.16], [s * 52.5, 9.16]]);
    line([[s * 52.5, -3.66], [s * 54.5, -3.66], [s * 54.5, 3.66], [s * 52.5, 3.66]]);
  }
}
function draw() {
  const f = D.frames[k];
  pitch();
  g.font = "bold 13px system-ui"; g.textAlign = "center"; g.textBaseline = "middle";
  f.xy.forEach((p, j) => {
    if (!p) return;
    const gk = D.positions[j] === "GK";
    g.fillStyle = gk ? "#f5d000" : D.colours[j < 11 ? 0 : 1];
    g.beginPath(); g.arc(X(p[0]), Y(p[1]), 11, 0, 2 * Math.PI); g.fill();
    g.strokeStyle = "white"; g.lineWidth = 1.5; g.stroke();
    g.fillStyle = gk ? "black" : "white"; g.fillText(D.shirts[j], X(p[0]), Y(p[1]) + 1);
    const r = D.runs.find(r => r.who === j && r.a <= f.clock && f.clock <= r.b);
    if (r) {
      const s = D.short[r.what]; g.font = "11px system-ui";
      const w = g.measureText(s).width + 6;
      g.fillStyle = "rgba(255,255,255,0.9)"; g.fillRect(X(p[0]) - w / 2, Y(p[1]) - 30, w, 15);
      g.fillStyle = "black"; g.fillText(s, X(p[0]), Y(p[1]) - 22); g.font = "bold 13px system-ui";
    }
  });
  const [bx, by, bz] = f.ball;
  g.fillStyle = "rgba(0,0,0,0.3)";
  g.beginPath(); g.arc(X(bx) + bz, Y(by) + bz, 5, 0, 2 * Math.PI); g.fill();
  g.fillStyle = "white"; g.strokeStyle = "black"; g.lineWidth = 1.5;
  g.beginPath(); g.arc(X(bx), Y(by), 5 + bz * 0.6, 0, 2 * Math.PI); g.fill(); g.stroke();
  const ev = D.events.filter(e => e.clock <= f.clock), e = ev[ev.length - 1];
  const sc = e ? e.score : {home: 0, away: 0};
  document.getElementById("score").textContent =
    `${D.teams[0]} ${sc.home}–${sc.away} ${D.teams[1]}`;
  const holder = f.poss >= 0 ? D.teams[f.poss] : "contested";
  document.getElementById("status").textContent =
    `${mmss(f.clock)} (half ${f.period}) · ${f.alive ? "in play" : "dead ball"} · ` +
    `possession: ${holder}`;
  document.getElementById("event").textContent = e ? `${mmss(e.clock)} ${e.label}` +
    (e.who >= 0 ? ` – ${D.teams[e.who < 11 ? 0 : 1]} #${D.shirts[e.who]}` : "") : "";
  seek.value = k;
}
function tick(now) {
  if (last !== null && playing) {
    acc += (now - last) / 1000 * D.rate * Number(document.getElementById("speed").value);
    const step = Math.floor(acc); acc -= step;
    if (step) { k = Math.min(D.frames.length - 1, k + step); draw(); }
    if (k === D.frames.length - 1) playing = false;
  }
  last = now; requestAnimationFrame(tick);
}
document.getElementById("play").onclick = e => {
  playing = !playing; if (playing && k === D.frames.length - 1) k = 0;
  e.target.textContent = playing ? "Pause" : "Play"; };
seek.oninput = () => { k = Number(seek.value); draw(); };
draw(); requestAnimationFrame(tick);
</script></body></html>
"""

if __name__ == "__main__":
    main()
