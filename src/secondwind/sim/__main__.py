"""Generate one match: ``python -m secondwind.sim --seed 1 --out data/synthetic/m0001``.

Fatigue is on and the match tempo drawn by default. ``--no-fatigue`` gives the no-fatigue
control of the same seed (PLAN §2.5); adding ``--no-tempo`` gives the match as the generator
made it before fatigue and tempo existed (81f023d), file for file.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from secondwind.sim import params as P
from secondwind.sim.output import CLEAN_COPY, generate


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m secondwind.sim", description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True, help="match folder to write")
    parser.add_argument("--match-id", help="default: the folder name")
    parser.add_argument(
        "--club-tests",
        action="store_true",
        help="also write club test values (validation experiment only; broadcasters lack them)",
    )
    parser.add_argument(
        "--noise-sigma",
        type=float,
        default=P.NOISE_SIGMA,
        help=f"position noise per axis, m (default {P.NOISE_SIGMA})",
    )
    parser.add_argument(
        "--no-fatigue",
        action="store_true",
        help="no-fatigue control: every player fresh all match (same seed, same tempo)",
    )
    tempo = parser.add_mutually_exclusive_group()
    tempo.add_argument(
        "--tempo", type=float, help="fix the shared match tempo (default: drawn, 1 ± 0.03)"
    )
    tempo.add_argument("--no-tempo", action="store_true", help="no shared match tempo")
    parser.add_argument(
        "--no-subs",
        action="store_true",
        help="no substitutions (with --no-fatigue --no-tempo there are none anyway)",
    )
    parser.add_argument(
        "--clean-copy",
        action="store_true",
        help=f"also save the noise-free positions to <out>/{CLEAN_COPY} (debugging only)",
    )
    args = parser.parse_args(argv)

    started = time.perf_counter()
    tempo = False if args.no_tempo else (True if args.tempo is None else args.tempo)
    match = generate(
        args.seed,
        args.out,
        args.match_id,
        args.club_tests,
        args.noise_sigma,
        args.clean_copy,
        fatigue=not args.no_fatigue,
        tempo=tempo,
        subs=not args.no_subs,
    )
    frames = sum(len(p.alive) for p in match.periods)
    print(
        f"wrote {args.out}: {frames} frames, {len(match.events)} events "
        f"in {time.perf_counter() - started:.1f} s"
    )


if __name__ == "__main__":
    main()
