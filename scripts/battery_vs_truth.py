"""README figure: one held-out player's battery against his true reserve (docs/figures/).

    uv run python scripts/battery_vs_truth.py data/synthetic/heldout/h0062 \
        docs/figures/battery_vs_truth.png 0.059

Runs the estimator on a match from the simulator's held-out seeds and draws the outfield player
(on for 80 minutes or more) whose mean gap to the hidden reserve is closest to the third argument,
the held-out average (README), or to the match's median when it is left out.
"""

import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from runningbattery.engine.estimate import compute
from runningbattery.io import read_match, read_truth
from runningbattery.validate.estimator import align, goalkeepers

match = Path(sys.argv[1])
out = Path(sys.argv[2])
m = read_match(match)
est = compute(m)
truth = align(est, read_truth(match), goalkeepers(m))
s = est.seconds
# The player whose mean error is closest to the median player's (no cherry-picking).
errs = {}
for j, pid in enumerate(est.tracks.ids):
    on = s.on[:, j] & np.isfinite(truth.pools[:, j])
    if truth.outfield[j] and on.sum() > 80 * 60:
        errs[pid] = float(np.nanmean(np.abs(s.battery[on, j] - truth.pools[on, j])))
med = float(np.median(list(errs.values())))
target = float(sys.argv[3]) if len(sys.argv) > 3 else med
pid = min(errs, key=lambda p: abs(errs[p] - target))
j = est.tracks.ids.index(pid)
print(
    "match",
    match.name,
    "players",
    len(errs),
    "median error",
    round(med, 3),
    "player",
    pid,
    round(errs[pid], 3),
    "all",
    sorted(round(v, 3) for v in errs.values()),
)
first = (s.period == 1).sum() / 60.0
minute = s.t / 60.0 + np.where(s.period == 2, first, 0.0)
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#8c959f",
        "axes.labelcolor": "#1f2328",
        "xtick.color": "#57606a",
        "ytick.color": "#57606a",
    }
)
fig, ax = plt.subplots(figsize=(10, 3.6), facecolor="white")
BLUE, ORANGE = "#2563eb", "#e8590c"
for half in (1, 2):
    rows = np.flatnonzero(s.on[:, j] & (s.period == half))
    x = minute[rows]
    lab = half == 1
    ax.fill_between(
        x,
        100 * s.battery_lo[rows, j],
        100 * s.battery_hi[rows, j],
        color=BLUE,
        alpha=0.15,
        lw=0,
        label="range of our battery (middle 80% of 200 typical pros)" if lab else None,
    )
    ax.plot(
        x,
        100 * s.battery[rows, j],
        color=BLUE,
        lw=1.8,
        label="our battery, from positions only" if lab else None,
    )
    ax.plot(
        x,
        100 * truth.pools[rows, j],
        color=ORANGE,
        lw=1.4,
        label="the player's true reserve (hidden from the battery)" if lab else None,
    )
ax.axvline(first, color="#8c959f", lw=1, ls=(0, (4, 3)))
ax.text(first + 0.6, 4, "half-time", color="#57606a", fontsize=9)
ax.set_ylim(0, 105)
ax.set_yticks([0, 50, 100])
ax.set_yticklabels(["0%", "50%", "100%"])
ax.set_xlabel("minute of play")
ax.set_ylabel("reserve left")
ax.grid(axis="y", color="#d0d7de", lw=0.8)
ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=False, fontsize=9.5, ncol=1)
ax.set_title(
    "One simulated player in a match the battery was not tuned on "
    f"(average gap {100 * errs[pid]:.0f} points)",
    loc="left",
    fontsize=11.5,
    color="#1f2328",
)
fig.tight_layout()
fig.savefig(out, dpi=150, facecolor="white")
print("wrote", out)
