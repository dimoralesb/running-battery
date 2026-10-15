"""Generator v0: determinism, valid files, and the interim realism targets (summary.TARGETS)."""

import itertools
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from secondwind.io import EVENTS, METADATA, TRACKING, TRUTH, read_match, read_truth
from secondwind.schema import X_LIMIT, Y_LIMIT, EventType, MatchMetadata, Position
from secondwind.sim import params as P
from secondwind.sim.summary import (
    BALL_IN_PLAY_BAND,
    COUNT_TOLERANCE,
    POSSESSION_BAND,
    RARE_COUNT_TOLERANCE,
    TARGETS,
    summarise_match,
)

SEEDS = [1, 2, 3, 4, 5]
MAX_SPEED = 12.0  # m/s (43.2 km/h): nobody is faster between two frames


def generate(jobs: list[tuple[int, Path, list[str]]]) -> None:
    """Run the CLI for several matches at once, as a user would."""
    procs = [
        subprocess.Popen(
            [sys.executable, "-m", "secondwind.sim", "--seed", str(seed), "--out", str(folder)]
            + extra,
            stdout=subprocess.DEVNULL,
        )
        for seed, folder, extra in jobs
    ]
    for proc in procs:
        assert proc.wait(timeout=300) == 0


@pytest.fixture(scope="module")
def folders(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("synthetic")
    folders = {seed: root / f"m{seed:04d}" for seed in SEEDS}
    folders["again"] = root / "again" / "m0001"
    folders["club"] = root / "club" / "m0001"
    jobs = [(seed, folders[seed], []) for seed in SEEDS]
    jobs += [(1, folders["again"], []), (1, folders["club"], ["--club-tests"])]
    generate(jobs)
    return folders


@pytest.fixture(scope="module")
def summaries(folders) -> dict:
    """Read every match with full pydantic validation, keep only the summary."""
    out = {}
    for seed in SEEDS:
        match = read_match(folders[seed])
        out[seed] = (summarise_match(match), _check_match(match))
    return out


def _check_match(match) -> dict:
    """Structural facts gathered while the frames are in memory."""
    meta = match.metadata
    frames = match.frames
    starts = [p.start_frame for p in meta.periods]
    return {
        "frame_numbers_ok": [f.frame for f in frames] == list(range(len(frames))),
        "period_frames_ok": all(
            frames[p.start_frame].period == p.period
            and frames[p.end_frame].period == p.period
            and round((p.end_frame - p.start_frame + 1) / meta.frame_rate_hz, 1) == p.duration_s
            for p in meta.periods
        ),
        "period_2_clock_ok": frames[starts[1]].clock == 2700.0 and frames[starts[1]].t == 0.0,
        "players_per_frame": {len(f.players) for f in frames},
        "events_sorted": all(
            (a.period, a.t) <= (b.period, b.t) for a, b in itertools.pairwise(match.events)
        ),
        "event_ids_ok": [e.id for e in match.events] == list(range(len(match.events))),
        "carries_ok": all(e.end_t is not None for e in match.events if e.type == EventType.CARRY),
        "goals": sum(e.type == EventType.GOAL for e in match.events),
        "truth_seconds": sum((p.end_frame - p.start_frame) // 10 + 1 for p in meta.periods),
        "final_score": match.events[-1].score,
        "no_test_values": all(p.test_values is None for team in meta.teams for p in team.players),
    }


def test_same_seed_gives_identical_files(folders):
    for name in (TRACKING, EVENTS, METADATA, TRUTH):
        assert (folders[1] / name).read_bytes() == (folders["again"] / name).read_bytes(), name


def test_different_seeds_differ(folders):
    assert (folders[1] / EVENTS).read_bytes() != (folders[2] / EVENTS).read_bytes()


def test_files_validate(folders, summaries):
    for seed in SEEDS:
        truth = read_truth(folders[seed])
        assert truth.fatigue_enabled is False
        assert len(truth.players) == 22
        assert truth.runs == []
        series = truth.players[0].series
        assert set(series.fast_pool) == {1.0} and set(series.speed_mult) == {1.0}
        checks = summaries[seed][1]
        assert len(series.t) == checks["truth_seconds"]
        assert checks["frame_numbers_ok"] and checks["period_frames_ok"]
        assert checks["period_2_clock_ok"]
        assert checks["players_per_frame"] == {22}
        assert checks["events_sorted"] and checks["event_ids_ok"] and checks["carries_ok"]
        assert checks["no_test_values"]  # broadcast data by default
        score = checks["final_score"]
        assert score.home + score.away == checks["goals"]


def test_match_length(summaries):
    lo = P.MATCH_MINUTES_MEAN - 3 * P.MATCH_MINUTES_SD
    hi = P.MATCH_MINUTES_MEAN + 3 * P.MATCH_MINUTES_SD
    minutes = [summaries[s][0].match_minutes for s in SEEDS]
    assert all(lo <= m <= hi for m in minutes), minutes
    assert abs(np.mean(minutes) - P.MATCH_MINUTES_MEAN) <= P.MATCH_MINUTES_SD


def test_ball_in_play_and_possession(summaries):
    bip = np.mean([summaries[s][0].ball_in_play_pct for s in SEEDS])
    assert BALL_IN_PLAY_BAND[0] <= bip <= BALL_IN_PLAY_BAND[1], bip
    lo, hi = POSSESSION_BAND
    for team in ("home", "away"):
        share = np.mean([summaries[s][0].possession_pct[team] for s in SEEDS])
        assert lo <= share <= hi, (team, share)
    for s in SEEDS:  # also every single match
        assert all(lo <= v <= hi for v in summaries[s][0].possession_pct.values())


@pytest.mark.parametrize(
    "key", ["passes", "shots", "duels", "fouls", "throw_ins", "corners", "transitions", "offsides"]
)
def test_event_counts_near_targets(summaries, key):
    mean = np.mean([summaries[s][0].counts[key] for s in SEEDS])
    target = TARGETS[key][0]
    tolerance = RARE_COUNT_TOLERANCE if target < 5 else COUNT_TOLERANCE
    assert abs(mean - target) <= tolerance * target, (key, mean, target)


def test_club_tests_change_only_the_metadata(folders):
    for name in (TRACKING, EVENTS, TRUTH):
        assert (folders[1] / name).read_bytes() == (folders["club"] / name).read_bytes(), name
    meta = MatchMetadata.model_validate_json((folders["club"] / METADATA).read_text())
    truth = {p.player_id: p.params for p in read_truth(folders["club"]).players}
    for team in meta.teams:
        for p in team.players:
            if p.position == Position.GK:
                assert p.test_values is None
                continue
            for name, sd in P.TEST_ERROR_SD.items():
                ratio = getattr(p.test_values, name) / getattr(truth[p.id], name)
                assert abs(ratio - 1) <= 3 * sd + 0.01, (p.id, name, ratio)


def test_nobody_faster_than_12_m_per_s(summaries):
    fastest = max(summaries[s][0].max_step_speed for s in SEEDS)
    assert fastest < MAX_SPEED, fastest
    # And nobody beyond their own top speed S0 (at most 10.3 m/s [Morin2021, Table 1]).
    assert fastest <= P.S0_RANGE[1] + 0.01


def test_positions_inside_schema_limits(summaries):
    for s in SEEDS:
        e = summaries[s][0].extent
        assert e["player_x"] <= X_LIMIT and e["ball_x"] <= X_LIMIT
        assert e["player_y"] <= Y_LIMIT and e["ball_y"] <= Y_LIMIT
        assert 0.0 <= e["ball_z_min"] and e["ball_z_max"] <= 50.0


def test_summary_cli_runs(folders):
    out = subprocess.run(
        [sys.executable, "-m", "secondwind.sim.summary", str(folders[1])],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "ball in play" in out and "H01" in out and "A11" in out
