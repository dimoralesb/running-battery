"""Generator: determinism, valid files, the interim realism targets (summary.TARGETS), the motion
model, run purposes, position noise and the replay tool."""

import itertools
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from secondwind.io import EVENTS, METADATA, TRACKING, TRUTH, read_match, read_truth
from secondwind.schema import X_LIMIT, Y_LIMIT, EventType, MatchMetadata, Position, RunPurpose
from secondwind.sim import movement
from secondwind.sim import params as P
from secondwind.sim.batch import parse_seeds
from secondwind.sim.match import MatchEngine, PeriodFrames
from secondwind.sim.output import CLEAN_COPY, observe, read_clean_copy, simulate
from secondwind.sim.replay import load_window, write_html
from secondwind.sim.rosters import make_teams
from secondwind.sim.runs import speeds, spells
from secondwind.sim.summary import (
    BALL_IN_PLAY_BAND,
    POSSESSION_BAND,
    TARGETS,
    count_tolerance,
    summarise_match,
)

SEEDS = [1, 2, 3, 4, 5]
MAX_SPEED = 12.0  # m/s (43.2 km/h): nobody is faster between two frames


def generate(jobs: list[tuple[int, Path, list[str]]]) -> list[subprocess.Popen]:
    """Start the CLI for several matches at once, as a user would. Wait with ``finish``."""
    return [
        subprocess.Popen(
            [sys.executable, "-m", "secondwind.sim", "--seed", str(seed), "--out", str(folder)]
            + extra,
            stdout=subprocess.DEVNULL,
        )
        for seed, folder, extra in jobs
    ]


def finish(procs: list[subprocess.Popen]) -> None:
    for proc in procs:
        assert proc.wait(timeout=300) == 0


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> tuple[dict, object]:
    """The CLI matches, plus seed 1 simulated in this process while they run."""
    root = tmp_path_factory.mktemp("synthetic")
    folders = {seed: root / f"m{seed:04d}" for seed in SEEDS}
    folders["again"] = root / "again" / "m0001"
    folders["club"] = root / "club" / "m0001"
    folders["clean"] = root / "clean" / "m0001"
    jobs = [(seed, folders[seed], []) for seed in SEEDS]
    jobs += [(1, folders["again"], []), (1, folders["club"], ["--club-tests"])]
    jobs += [(1, folders["clean"], ["--clean-copy"])]
    procs = generate(jobs)
    sim1 = simulate(1, "m0001")
    finish(procs)
    return folders, sim1


@pytest.fixture(scope="module")
def folders(generated) -> dict:
    return generated[0]


@pytest.fixture(scope="module")
def sim1(generated):
    return generated[1]


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
        "dropout_share": 1 - sum(len(f.players) for f in frames) / (22 * len(frames)),
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
        assert truth.runs
        assert truth.settings["noise_sigma_m"] == P.NOISE_SIGMA
        series = truth.players[0].series
        assert set(series.fast_pool) == {1.0} and set(series.speed_mult) == {1.0}
        checks = summaries[seed][1]
        assert len(series.t) == checks["truth_seconds"]
        assert checks["frame_numbers_ok"] and checks["period_frames_ok"]
        assert checks["period_2_clock_ok"]
        # Dropouts leave a player out of a frame now and then (params.DROPOUTS_PER_MIN).
        assert max(checks["players_per_frame"]) == 22
        assert min(checks["players_per_frame"]) >= 18
        assert 0.0 < checks["dropout_share"] < 0.02
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
    tolerance = count_tolerance(target, len(SEEDS))
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
    """From the noisy tracking after the summary's 1 Hz filter."""
    fastest = max(summaries[s][0].max_step_speed for s in SEEDS)
    assert fastest < MAX_SPEED, fastest


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


# --- Motion model ---------------------------------------------------------------------------------


def _limits_hold(before: np.ndarray, after: np.ndarray, a0: np.ndarray, s0: np.ndarray) -> None:
    """Speeds one frame apart: never above S0, never gaining faster than a_max(v) [Morin2021],
    never braking harder than BRAKE_MAX."""
    tol = 1e-6
    assert np.all(after <= s0 + tol)
    gain = (after - before) / P.DT
    assert np.all(gain <= movement.a_max(before, a0, s0) + tol), gain.max()
    assert np.all(-gain <= P.BRAKE_MAX + tol), (-gain).max()


def test_motion_model_limits_random_states():
    """Random positions, velocities, targets and wanted speeds, stepped many times."""
    rng = np.random.default_rng(0)
    n = 500
    a0 = rng.uniform(*P.A0_RANGE, n)
    s0 = rng.uniform(*P.S0_RANGE, n)
    pos = rng.uniform(-50, 50, (n, 2))
    direction = rng.normal(size=(n, 2))
    vel = direction / np.hypot(*direction.T)[:, None] * rng.uniform(0, 1, n)[:, None] * s0[:, None]
    for _ in range(200):
        target = (
            rng.uniform(-60, 60, (n, 2)) if rng.random() < 0.2 else pos + rng.normal(0, 20, (n, 2))
        )
        cap = rng.uniform(0.0, 1.2, n) * s0
        before = np.hypot(*vel.T)
        pos, vel = movement.step(pos, vel, target, cap, a0, s0)
        _limits_hold(before, np.hypot(*vel.T), a0, s0)


def test_motion_model_limits_with_push():
    """The push-apart velocity never breaks the limits, and never makes a player faster."""
    rng = np.random.default_rng(1)
    n = 500
    a0 = rng.uniform(*P.A0_RANGE, n)
    s0 = rng.uniform(*P.S0_RANGE, n)
    pos = rng.uniform(-50, 50, (n, 2))
    vel = rng.normal(0, 3, (n, 2))
    for _ in range(200):
        target = pos + rng.normal(0, 10, (n, 2))
        cap = rng.uniform(0.0, 1.2, n) * s0
        push = rng.normal(0, 1, (n, 2)) * rng.uniform(0, P.SEPARATION_MAX, n)[:, None]
        before = np.hypot(*vel.T)
        pos, vel = movement.step(pos, vel, target, cap, a0, s0, push=push)
        _limits_hold(before, np.hypot(*vel.T), a0, s0)
    # A sprinter pushed from behind wants no more speed than before.
    s0 = np.array([9.3])
    args = (np.zeros((1, 2)), np.array([[8.0, 0.0]]), np.array([[100.0, 0.0]]), s0, s0 - 1.9, s0)
    _, plain = movement.step(*args)
    _, pushed = movement.step(*args, push=np.array([[P.SEPARATION_MAX, 0.0]]))
    assert pushed[0, 0] <= plain[0, 0] + 1e-9


def test_push_apart_and_spread_targets():
    team_of = np.array([0, 0, 1, 0])
    # 0 and 1: team-mates on one spot; 2: an opponent 1 m away; 3: far off.
    pos = np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 0.0], [30.0, 0.0]])
    push = movement.push_apart(pos, team_of)
    assert push[0, 0] < 0 < push[1, 0]  # split along x
    assert np.allclose(np.hypot(*push[:2].T), P.SEPARATION_MAX)  # 1.8 m short, capped
    assert np.allclose(push[2:], 0.0)  # 1 m from an opponent is close enough
    # Team-mates 1 m apart: (1.8 − 1) / τ each, straight away from the other.
    near = movement.push_apart(np.array([[0.0, 0.0], [0.0, 1.0]]), np.array([0, 0]))
    gap = P.SEPARATION_TEAM - 1.0
    assert np.allclose(near, [[0.0, -gap / P.SEPARATION_TAU], [0.0, gap / P.SEPARATION_TAU]])
    anchored = np.array([True, False, False, False])
    assert np.allclose(movement.push_apart(pos, team_of, anchored)[0], 0.0)

    spread = movement.spread_targets(pos, team_of)
    assert np.hypot(*(spread[0] - spread[1])) == pytest.approx(P.SEPARATION_TEAM)
    assert np.allclose(spread[2:], pos[2:])  # opponents' targets are left alone
    spread = movement.spread_targets(pos, team_of, anchored)
    assert np.allclose(spread[0], pos[0])  # the anchored player keeps their target
    assert np.hypot(*(spread[1] - pos[0])) == pytest.approx(P.SEPARATION_TEAM)


def test_push_apart_looks_ahead_for_team_mates():
    """Two players 3 m apart running at each other: team-mates move apart before they meet;
    opponents are judged where they are now (pressing and duels are left alone)."""
    pos = np.array([[-1.5, 0.0], [1.5, 0.0]])
    vel = np.array([[1.5, 0.0], [-1.5, 0.0]])
    mates = movement.push_apart(pos, np.array([0, 0]), vel=vel)
    assert mates[0, 0] < 0 < mates[1, 0]
    assert np.allclose(movement.push_apart(pos, np.array([0, 0])), 0.0)
    assert np.allclose(movement.push_apart(pos, np.array([0, 1]), vel=vel), 0.0)


def _held_restart(kind: str, spot_uv: tuple[float, float], seconds: float = 30.0):
    """An engine a few seconds into a match, then a restart for team 0 at ``spot_uv`` (team 0's
    attacking frame), held for ``seconds`` while everyone moves into place."""
    rng = np.random.default_rng(0)
    engine = MatchEngine(rng, make_teams(rng))
    engine.run_period(1, 50, 0)
    spot = engine.to_uv(0, np.array(spot_uv))
    engine.schedule_restart(kind, 0, spot, 5.0, spot.copy())
    engine.restart.t = np.inf  # never taken
    for k in range(round(seconds * P.FRAME_RATE_HZ)):
        t = 5.0 + k / P.FRAME_RATE_HZ
        engine.follow_ball(t)
        engine.move(t)
    return engine, spot


@pytest.mark.parametrize(
    "kind, spot_uv, keep",
    [
        ("free_kick", (P.HALF_LENGTH - 22.0, 6.0), P.RESTART_DISTANCE),  # in wall range
        ("free_kick", (-10.0, -20.0), P.RESTART_DISTANCE),
        ("corner", (P.HALF_LENGTH, P.HALF_WIDTH), P.RESTART_DISTANCE + P.CORNER_ARC),
        ("throw_in", (5.0, -P.HALF_WIDTH), P.THROW_IN_DISTANCE),
    ],
)
def test_restart_distance_and_taker(kind, spot_uv, keep):
    """Once settled, opponents stand at least 9.15 m from a free kick (Law 13), 9.15 m from the
    corner arc (Laws 1, 17) and 2 m from a throw-in (Law 15) [IFAB2025], give or take the
    approach (0.5 m); the taker about 1 m behind the ball."""
    engine, spot = _held_restart(kind, spot_uv)
    opponents = engine.pos[11:]
    assert np.hypot(*(opponents - spot).T).min() > keep - 0.5
    taker = engine.restart.taker
    assert abs(np.hypot(*(engine.pos[taker] - spot)) - P.TAKER_BEHIND) < 0.3


def test_free_kick_in_range_gets_a_wall():
    """WALL_SIZE[0] defenders side by side, WALL_GAP apart, at the edge of the 9.15 m circle."""
    engine, spot = _held_restart("free_kick", (P.HALF_LENGTH - 24.0, 4.0))
    edge = P.RESTART_DISTANCE + P.RESTART_MARGIN
    d = np.hypot(*(engine.pos[11:] - spot).T)
    wall = engine.pos[11:][np.abs(d - edge) < 0.3]
    assert len(wall) >= P.WALL_SIZE[0], d.round(1)
    gaps = np.hypot(*(wall[:, None] - wall[None]).T)
    np.fill_diagonal(gaps, np.inf)
    assert np.allclose(gaps.min(axis=1), P.WALL_GAP, atol=0.15), gaps.min(axis=1)


def test_free_kicks_keep_distance_over_a_match(sim1):
    """A whole match: the median nearest opponent at a free kick is outside 9.15 m (5.8 m before
    the rule), and nobody is inside the corner circle. Quick free kicks may be taken with
    opponents closer [IFAB2025, Law 13], so single kicks are not judged here."""
    ids = [p.id for team in sim1.metadata.teams for p in team.players]
    nearest = {"free_kick": [], "corner": []}
    for e in sim1.events:
        if e.type == EventType.PASS and e.subtype in nearest:
            taker = ids.index(e.player_id)
            pos = sim1.periods[e.period - 1].pos[round(e.t * P.FRAME_RATE_HZ)]
            opponents = pos[11:] if taker < 11 else pos[:11]
            spot = np.array([e.start.x, e.start.y])
            nearest[e.subtype].append(np.hypot(*(opponents - spot).T).min())
    assert np.median(nearest["free_kick"]) > P.RESTART_DISTANCE
    assert min(nearest["corner"]) > P.RESTART_DISTANCE + P.CORNER_ARC


def test_teammates_do_not_stack(sim1):
    """Push-apart on a whole match (noise-free positions). Before it (commit 145bf90), seed 1 had a
    team-mate within 0.5 m in 0.24% of player-frames and within 1 m in 0.93%."""
    frames = within_half = within_one = 0
    longest = 0
    for pf in sim1.periods:
        nearest = np.full(pf.pos.shape[:2], np.inf)
        for team in (range(11), range(11, 22)):
            for i, j in itertools.combinations(team, 2):
                d = np.hypot(*(pf.pos[:, i] - pf.pos[:, j]).T)
                nearest[:, i] = np.minimum(nearest[:, i], d)
                nearest[:, j] = np.minimum(nearest[:, j], d)
                close = (d < 1.0) & pf.alive  # walls stand close on purpose at dead balls
                longest = max([longest] + [b - a for a, b in spells(close, 1)])
        frames += nearest.size
        within_half += int((nearest < 0.5).sum())
        within_one += int((nearest < 1.0).sum())
    assert within_half / frames < 0.003, within_half / frames  # 0.04–0.20% on seeds 1–30
    assert within_one / frames < 0.0075, within_one / frames  # 0.26–0.61% on seeds 1–30
    assert longest / P.FRAME_RATE_HZ < 8.0  # in play, nobody stands on a team-mate's spot


def test_motion_model_matches_narizuka_at_full_effort():
    """Straight ahead from rest at full effort the model gives v(t) = S0(1 − e^(−αt)),
    α = A0/S0 [Narizuka2023, Eq. 3–4], up to the explicit-Euler step."""
    a0, s0 = np.array([7.4]), np.array([9.3])
    pos, vel = np.zeros((1, 2)), np.zeros((1, 2))
    target = np.array([[1000.0, 0.0]])
    for _ in range(30):  # 3 s
        pos, vel = movement.step(pos, vel, target, s0, a0, s0)
    expected = s0[0] * (1 - np.exp(-a0[0] / s0[0] * 3.0))
    assert abs(vel[0, 0] - expected) < 0.15, (vel[0, 0], expected)
    assert abs(vel[0, 1]) < 1e-9


def test_match_motion_within_limits(sim1):
    """Every player, every frame of a whole match (noise-free positions)."""
    params = {p.player_id: p.params for p in sim1.truth.players}
    ids = [p.id for team in sim1.metadata.teams for p in team.players]
    a0 = np.array([params[i].a0 for i in ids])
    s0 = np.array([params[i].s0 for i in ids])
    for pf in sim1.periods:
        v = speeds(pf.pos)
        _limits_hold(v[:-1], v[1:], a0[None], s0[None])


# --- Run purposes ---------------------------------------------------------------------------------


def test_runs_have_valid_purposes_and_times(folders, sim1):
    seen: set[RunPurpose] = set()
    for seed in SEEDS:
        truth = read_truth(folders[seed])
        meta = MatchMetadata.model_validate_json((folders[seed] / METADATA).read_text())
        length = {
            p.period: (p.end_frame - p.start_frame) / meta.frame_rate_hz for p in meta.periods
        }
        ids = {p.id for team in meta.teams for p in team.players}
        assert [r.run_id for r in truth.runs] == list(range(len(truth.runs)))
        for r in truth.runs:
            assert r.purpose in RunPurpose and r.executed and r.player_id in ids
            assert 0.0 <= r.t_start and r.t_end <= length[r.period]
            assert r.t_end - r.t_start >= P.HI_MIN_S - 1e-9
            seen.add(r.purpose)
    # Both phases of play show up: most of Ju2022's classes appear in five matches.
    assert len(seen) >= 9, seen
    assert {RunPurpose.RECOVERY_RUN, RunPurpose.COVERING, RunPurpose.RUN_IN_BEHIND} <= seen


def test_runs_are_high_intensity(sim1):
    """Each run is above 5.5 m/s for its whole span [Ju2022, p.974], and only those spells."""
    ids = [p.id for team in sim1.metadata.teams for p in team.players]
    v = {pf.period: speeds(pf.pos) for pf in sim1.periods}
    rate = P.FRAME_RATE_HZ
    for r in sim1.truth.runs:
        a, b = round(r.t_start * rate), round(r.t_end * rate)
        j = ids.index(r.player_id)
        assert np.all(v[r.period][a:b, j] > P.HI_SPEED)
        assert a == 0 or v[r.period][a - 1, j] <= P.HI_SPEED
        assert b == len(v[r.period]) or v[r.period][b, j] <= P.HI_SPEED


# --- Position noise -------------------------------------------------------------------------------


def test_clean_copy_matches_simulation_and_changes_no_file(folders, sim1):
    for name in (TRACKING, EVENTS, METADATA, TRUTH):
        assert (folders[1] / name).read_bytes() == (folders["clean"] / name).read_bytes(), name
    assert not (folders[1] / CLEAN_COPY).exists()
    clean = read_clean_copy(folders["clean"])
    for pf in sim1.periods:
        for name in ("pos", "ball", "alive", "possession", "purpose"):
            assert np.array_equal(clean[f"{name}_{pf.period}"], getattr(pf, name)), name
    read_match(folders["clean"])  # the extra folder does not get in the way


def test_noise_size_and_dropouts(folders, sim1):
    """tracking.jsonl = noise-free positions + N(0, σ) per axis, rounded to 1 cm."""
    match = read_match(folders[1])
    ids = [p.id for team in match.metadata.teams for p in team.players]
    clean = np.concatenate([pf.pos for pf in sim1.periods])
    errors, missing = [], 0
    for k, frame in enumerate(match.frames):
        got = {p.id: (p.x, p.y) for p in frame.players}
        missing += 22 - len(got)
        errors += [np.subtract(got[pid], clean[k, j]) for j, pid in enumerate(ids) if pid in got]
    errors = np.array(errors)
    assert abs(errors.mean()) < 0.005
    assert abs(errors.std() - P.NOISE_SIGMA) < 0.01, errors.std()
    expected = P.DROPOUTS_PER_MIN * np.mean(P.DROPOUT_S) / 60.0  # share of player-frames
    assert 0.5 * expected < missing / clean[..., 0].size < 1.5 * expected


def _period(pos: np.ndarray) -> PeriodFrames:
    """A stand-in period with these noise-free positions (n, 22, 2)."""
    n = len(pos)
    no_purpose = np.full((n, 22), -1, np.int8)
    return PeriodFrames(
        1, pos, np.zeros((n, 3)), np.ones(n, bool), np.zeros(n, np.int8), no_purpose
    )


def test_noise_is_deterministic_and_scales_with_sigma():
    """Same generator state → same noise; sigma only rescales it; dropouts do not change."""
    pos = np.zeros((600, 22, 2))
    pf = _period(pos)
    a = observe(np.random.default_rng(7), [pf], 0.1)[0]
    b = observe(np.random.default_rng(7), [pf], 0.1)[0]
    c = observe(np.random.default_rng(7), [pf], 0.3)[0]
    zero = observe(np.random.default_rng(7), [pf], 0.0)[0]
    assert np.array_equal(a.pos, b.pos) and np.array_equal(a.seen, b.seen)
    assert np.allclose(c.pos, 3 * a.pos) and np.array_equal(a.seen, c.seen)
    assert np.array_equal(zero.pos, pos)


def test_noise_keeps_positions_inside_schema_limits():
    pos = np.tile([[X_LIMIT - 0.01, -Y_LIMIT + 0.01]], (100, 22, 1))
    noisy = observe(np.random.default_rng(1), [_period(pos)], 1.0)[0].pos
    assert np.all(np.abs(noisy[..., 0]) <= X_LIMIT) and np.all(np.abs(noisy[..., 1]) <= Y_LIMIT)


# --- Tools ----------------------------------------------------------------------------------------


def test_batch_seed_parsing():
    assert parse_seeds("1-3,7") == [1, 2, 3, 7]
    assert parse_seeds("5") == [5]


def test_replay_html(folders, tmp_path):
    window = load_window(folders[1], start=600.0, seconds=5.0, purposes=True)
    assert len(window["frames"]) == 50 and window["frames"][0]["clock"] == 600.0
    out = tmp_path / "replay.html"
    write_html(window, out)
    html = out.read_text()
    assert "<canvas" in html and window["teams"][0] in html


def test_replay_stills(folders, tmp_path):
    pytest.importorskip("matplotlib")
    from secondwind.sim.replay import write_stills

    out = tmp_path / "stills.png"
    write_stills(load_window(folders[1], start=600.0, seconds=4.0), out, 2)
    assert out.stat().st_size > 10_000
