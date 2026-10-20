"""The two "never cut" charts (BUILD_PLAN §3–4): ``docs/figures/*.png`` for the README.

``python -m runningbattery.validate.figures``

Validation code. The numbers come from runs cached in ``data/figures_cache/`` (git-ignored),
made with:

- ``python -m runningbattery.validate.batch <batch> --json data/figures_cache/batch_<name>.json``
  for ``dev`` (seeds 1–60, where the calibration map was fitted), ``heldout`` (default seeds
  61–120, not used for the fit) and ``validation`` (varied seeds 1001–1050);
- ``validate.ceiling`` summaries as ``ceiling_dev60.json`` and ``ceiling_validation50.json``
  (``{"summary": ceiling.summary(...)}``, recall keys as strings);
- ``sim.fatigue_checks`` on seeds 1–240 with fatigue on and off as
  ``fatigue_checks_240.json`` (``{"on": summarise(...), "off": summarise(...)}``).

The player panel is computed here, from one validation match (``--match``, ``--player``).

1. **Estimator vs truth** (``estimator_vs_truth.png``): one player's battery with its 10–90%
   band against the hidden pools; the calibration of the typical-pro chance, raw and calibrated;
   and the best precision any positions-only detector could reach (the ceiling) next to ours.
2. **No-fatigue control** (``no_fatigue_control.png``): high-speed running in the 5 minutes
   after each player's most intense 1-, 2- and 5-min spell, published [Leifsson2024, Table 1],
   with fatigue and without (same seeds), and the end-of-match decline [Bradley2009, Fig. 2].
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "figures_cache"
OUT = ROOT / "docs" / "figures"

# Dataviz reference palette, light surface (validated: scripts/validate_palette.js).
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"

# Published HSR (> 5.5 m/s) after the most intense 1-, 2- and 5-min spell, minutes 1–5, % vs the
# match average without the peak [Leifsson2024, Table 1; synthesis §3.4.1].
LEIFSSON = {
    "60": (-29, -6, -3, -2, -2),
    "120": (-35, -11, 0, -2, -3),
    "300": (-45, -29, -13, -8, -4),
}
BRADLEY_LAST15 = -21  # > 4 m/s, last 15 min vs first 15 [Bradley2009, Fig. 2]
MIN_SECONDS = 500  # reliability bins with fewer player-seconds are not drawn (too noisy)


def _style(plt) -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": MUTED,
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 8,
            "legend.frameon": False,
        }
    )


def _load(name: str) -> dict:
    path = CACHE / name
    if not path.exists():
        raise SystemExit(f"missing {path}: see the module docstring for how to make it")
    return json.loads(path.read_text())


def _reliability(ax, batches: dict[str, dict]) -> None:
    ax.plot([0, 0.7], [0, 0.7], color=MUTED, lw=0.8, ls=":", label="perfect calibration")
    ece = {b: (d["low_chance_raw_ece"], d["low_chance_ece"]) for b, d in batches.items()}
    series = (
        (
            "dev",
            "calibration_low_chance_raw",
            f"raw, dev 1–60 (ECE {ece['dev'][0]:.3f})",
            MUTED,
            "s",
            "--",
        ),
        (
            "dev",
            "calibration_low_chance",
            f"calibrated, dev 1–60, fitted ({ece['dev'][1]:.3f})",
            BLUE,
            "o",
            "-",
        ),
        (
            "heldout",
            "calibration_low_chance",
            f"calibrated, held out 61–120 ({ece['heldout'][0]:.3f} → {ece['heldout'][1]:.3f})",
            AQUA,
            "D",
            "-",
        ),
        (
            "validation",
            "calibration_low_chance",
            f"calibrated, varied 1001–1050 ({ece['validation'][0]:.3f} → "
            f"{ece['validation'][1]:.3f})",
            ORANGE,
            "^",
            "-",
        ),
    )
    for batch, key, label, color, marker, ls in series:
        rows = [r for r in batches[batch][key] if r["n"] >= MIN_SECONDS]
        x = [r["chance"] for r in rows]
        y = [r["tired"] for r in rows]
        ax.plot(x, y, color=color, marker=marker, ms=5, lw=1.5, ls=ls, label=label)
    ax.set_xlim(0, 0.7)
    ax.set_ylim(0, 0.7)
    ax.set_xlabel("typical-pro chance (mean in each 0.1 bin)")
    ax.set_ylabel("share of those seconds truly tired")
    ax.set_title(
        "Calibration of the typical-pro chance\n(ECE: expected calibration error)",
        fontsize=8,
        loc="left",
    )
    ax.legend(loc="upper left", fontsize=6.5)


def _ceiling(ax, summary: dict, title: str) -> None:
    recalls = list(summary["ceiling"])
    x = np.arange(len(recalls))
    bars = (
        ("ceiling", "best possible from positions", MUTED, None),
        ("battery", "our battery", BLUE, None),
        ("low_chance", "our typical-pro chance", ORANGE, None),
    )
    width = 0.26
    for k, (key, label, color, _) in enumerate(bars):
        vals = [summary[key][r] for r in recalls]
        pos = x + (k - 1) * width
        ax.bar(pos, vals, width * 0.92, color=color, label=label)
        for p, v in zip(pos, vals, strict=True):
            ax.text(p, v + 0.006, f"{v:.2f}", ha="center", va="bottom", fontsize=6.5, color=INK)
    ax.set_xticks(x, [f"recall {r}" for r in recalls])
    ax.set_ylim(0, 0.3)
    ax.set_ylabel("best precision")
    exact = summary["exact"][0]
    ax.set_title(f"{title}\nwith true values: precision {exact:.2f}", fontsize=8, loc="left")
    ax.grid(axis="x", visible=False)


def estimator_figure(match: Path, player: str | None, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from runningbattery.engine.estimate import compute
    from runningbattery.io import read_match, read_truth
    from runningbattery.validate.estimator import align, goalkeepers, plot_player

    batches = {b: _load(f"batch_{b}.json") for b in ("dev", "heldout", "validation")}
    ceilings = {b: _load(f"ceiling_{b}.json")["summary"] for b in ("dev60", "validation50")}
    m = read_match(match)
    est = compute(m)
    truth = align(est, read_truth(match), goalkeepers(m))
    if player is None:
        share = np.where(truth.outfield, truth.tired.mean(axis=0), -1)
        player = est.tracks.ids[int(np.argmax(share))]
    _style(plt)
    fig = plt.figure(figsize=(11, 7.4))
    grid = fig.add_gridspec(2, 3, height_ratios=(1, 1.15), hspace=0.45, wspace=0.3)
    ax = fig.add_subplot(grid[0, :])
    plot_player(est, truth, player, ax=ax)
    ax.set_title("")
    ax.set_title(
        f"Estimator vs hidden truth, validation match {m.metadata.match_id}, player {player} "
        "(typical-pro battery; the generator's two pools are hidden from the estimator)",
        fontsize=8,
        loc="left",
    )
    _reliability(fig.add_subplot(grid[1, 0]), batches)
    _ceiling(fig.add_subplot(grid[1, 1]), ceilings["dev60"], "Who is tired? Dev seeds 1–60")
    ax = fig.add_subplot(grid[1, 2])
    _ceiling(ax, ceilings["validation50"], "Who is tired? Varied 1001–1050")
    ax.legend(loc="upper right", fontsize=7)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def control_figure(path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    checks = _load("fatigue_checks_240.json")
    on, off = checks["on"], checks["off"]
    _style(plt)
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.4), width_ratios=(1, 1, 1, 0.8))
    minutes = np.arange(1, 6)
    for ax, (w, label) in zip(
        axes, (("60", "1-min"), ("120", "2-min"), ("300", "5-min")), strict=False
    ):
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.plot(
            minutes,
            LEIFSSON[w],
            color=MUTED,
            marker="s",
            ms=5,
            lw=1.5,
            ls="--",
            label="published [Leifsson2024]",
        )
        ax.plot(
            minutes,
            on["leifsson"][f"hsr_{w}"],
            color=BLUE,
            marker="o",
            ms=5,
            lw=1.5,
            label="synthetic, fatigue on",
        )
        ax.plot(
            minutes,
            off["leifsson"][f"hsr_{w}"],
            color=ORANGE,
            marker="^",
            ms=5,
            lw=1.5,
            label="synthetic, fatigue off (control)",
        )
        ax.set_xticks(minutes)
        ax.set_ylim(-75, 10)
        ax.set_xlabel(f"minute after the {label} peak")
        ax.set_title(f"After the most intense {label} spell", fontsize=8, loc="left")
    axes[0].set_ylabel("high-speed running (> 5.5 m/s)\n% vs the player's match average")
    axes[0].legend(loc="lower right", fontsize=7)
    ax = axes[3]
    vals = (BRADLEY_LAST15, on["end"]["hir_last15_vs_first15"], off["end"]["hir_last15_vs_first15"])
    names = ("published", "fatigue\non", "fatigue\noff")
    ax.bar(range(3), vals, 0.6, color=(MUTED, BLUE, ORANGE))
    for k, v in enumerate(vals):
        ax.text(
            k,
            v - 1 if v < 0 else v + 1,
            f"{v:+.1f}%",
            ha="center",
            va="top" if v < 0 else "bottom",
            fontsize=7,
        )
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_xticks(range(3), names)
    ax.set_ylim(-28, 6)
    ax.set_ylabel("> 4 m/s, last 15 min vs first 15, %")
    ax.set_title("End of the match [Bradley2009]", fontsize=8, loc="left")
    ax.grid(axis="x", visible=False)
    fig.suptitle(
        f"No-fatigue control: the same {on['n']} synthetic matches with fatigue on and off. "
        "After a peak most of the drop is there without fatigue (picking the peak, play "
        "stopping); the end-of-match decline is all fatigue.",
        fontsize=8,
        x=0.01,
        ha="left",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m runningbattery.validate.figures", description=__doc__
    )
    parser.add_argument("--match", type=Path, default=ROOT / "data/synthetic/validation/v1001")
    parser.add_argument("--player", help="default: the match's most tired outfield player")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    estimator_figure(args.match, args.player, args.out / "estimator_vs_truth.png")
    control_figure(args.out / "no_fatigue_control.png")
    for p in sorted(args.out.glob("*.png")):
        print(f"{p.relative_to(ROOT)}: {p.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
