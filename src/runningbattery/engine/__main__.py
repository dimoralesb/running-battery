"""Estimate fatigue signals for one match: ``python -m runningbattery.engine data/synthetic/m0001``.

Reads ``tracking.jsonl``, ``events.jsonl`` and ``metadata.json`` (never ``truth.json``) and
writes ``signals.json`` into the match folder, or to ``--out``. Broadcast mode is the default and
the product; ``--mode club`` uses club test values (the validation experiment only; the match
must have been generated with ``--club-tests``).
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from runningbattery.engine import params as P
from runningbattery.engine.estimate import estimate
from runningbattery.io import SIGNALS, read_match, write_signals


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m runningbattery.engine", description=__doc__)
    parser.add_argument("folder", type=Path, help="match folder")
    parser.add_argument("--out", type=Path, help=f"default: <folder>/{SIGNALS}")
    parser.add_argument("--mode", choices=["broadcast", "club"], default="broadcast")
    parser.add_argument(
        "--update",
        choices=["draws", "correction"],
        default="draws",
        help="broadcast mode: per-player update from prior draws (default), or the one-way "
        "D′ correction only (fallback)",
    )
    parser.add_argument("--k", type=float, default=P.K, help=f"battery recharge factor ({P.K:g})")
    parser.add_argument(
        "--prior",
        choices=sorted(P.PRIORS),
        default=P.DEFAULT_PRIOR,
        help="typical player: 'pro' (professional players, the generator's population; for "
        "synthetic matches and real tracking) or 'university' (sensitivity, older matches); "
        "engine/params.py",
    )
    args = parser.parse_args(argv)
    start = time.perf_counter()
    match = read_match(args.folder)
    if args.mode == "club" and not any(
        p.test_values for team in match.metadata.teams for p in team.players
    ):
        parser.error("club mode needs club test values (generate the match with --club-tests)")
    signals = estimate(match, mode=args.mode, update=args.update, k=args.k, prior=args.prior)
    out = args.out or args.folder / SIGNALS
    write_signals(out, signals)
    spells = len(signals.tired_spells)
    print(
        f"{out}: {len(signals.players)} players, {spells} tired spells "
        f"({time.perf_counter() - start:.1f} s)"
    )


if __name__ == "__main__":
    main()
