"""Generator: determinism, valid files, the interim realism targets (summary.TARGETS), the motion
model, run purposes, position noise, the fatigue switch and truth.json, and the replay tool.
Physiology and fatigue behaviours on constructed states are in test_fatigue.py."""

import itertools
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from runningbattery.io import EVENTS, METADATA, TRACKING, TRUTH, read_match, read_truth
from runningbattery.schema import X_LIMIT, Y_LIMIT, EventType, MatchMetadata, Position, RunPurpose
from runningbattery.sim import movement, spacing
from runningbattery.sim import params as P
from runningbattery.sim.batch import parse_seeds
from runningbattery.sim.match import MatchEngine, PeriodFrames
from runningbattery.sim.output import CLEAN_COPY, observe, read_clean_copy, simulate
from runningbattery.sim.replay import load_window, write_html
from runningbattery.sim.roles import CODE as PURPOSES_CODE
from runningbattery.sim.rosters import make_teams
from runningbattery.sim.runs import speeds
from runningbattery.sim.summary import (
    BALL_IN_PLAY_BAND,
    POSSESSION_BAND,
    TARGETS,
    count_tolerance,
    summarise_match,
)

SEEDS = [1, 2, 3, 4, 5]
MAX_SPEED = 12.0  # m/s (43.2 km/h): nobody is faster between two frames


def _holds(spell, period: int, t: np.ndarray) -> np.ndarray:
    """Frames (times ``t`` of ``period``) when ``spell``'s player was in their slot."""
    on = np.full(len(t), period > spell.on[0]) | ((period == spell.on[0]) & (t >= spell.on[1]))
    if spell.off is not None:
        on &= (period < spell.off[0]) | ((period == spell.off[0]) & (t < spell.off[1]))
    return on


def _per_frame(match, pf, value) -> np.ndarray:
    """(frames, 22): ``value(spell)`` for whoever was in each slot at each frame of ``pf``."""
    t = np.arange(len(pf.alive)) / P.FRAME_RATE_HZ
    out = np.full((len(t), 22), np.nan)
    for spell in match.spells:
        on = _holds(spell, pf.period, t)
        out[on, spell.slot] = value(spell)
    return out


def generate(jobs: list[tuple[int, Path, list[str]]]) -> list[subprocess.Popen]:
    """Start the CLI for several matches at once, as a user would. Wait with ``finish``."""
    return [
        subprocess.Popen(
            [sys.executable, "-m", "runningbattery.sim", "--seed", str(seed), "--out", str(folder)]
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
    folders["off"] = root / "off" / "m0001"
    folders["legacy"] = root / "legacy" / "m0001"
    folders["vary"] = root / "vary" / "m0001"
    jobs = [(seed, folders[seed], []) for seed in SEEDS]
    jobs += [(1, folders["again"], []), (1, folders["club"], ["--club-tests"])]
    jobs += [(1, folders["clean"], ["--clean-copy"]), (1, folders["off"], ["--no-fatigue"])]
    jobs += [(1, folders["legacy"], ["--no-fatigue", "--no-tempo"])]
    jobs += [(1, folders["vary"], ["--vary"])]
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
        "subs": len(meta.substitutions),
        "on_pitch": [{p.id for p in f.players} for f in frames[:: 10 * 60]],  # once a minute
        "slot_of": meta.slot_of(),
    }


def test_same_seed_gives_identical_files(folders):
    for name in (TRACKING, EVENTS, METADATA, TRUTH):
        assert (folders[1] / name).read_bytes() == (folders["again"] / name).read_bytes(), name


def test_different_seeds_differ(folders):
    assert (folders[1] / EVENTS).read_bytes() != (folders[2] / EVENTS).read_bytes()


def test_files_validate(folders, summaries):
    for seed in SEEDS:
        truth = read_truth(folders[seed])
        checks = summaries[seed][1]
        assert truth.fatigue_enabled is True
        # 3–5 substitutes per team; a late one may not happen if no stoppage comes in time.
        assert 4 <= checks["subs"] <= 10 and len(truth.players) == 22 + checks["subs"]
        seconds = {}  # a slot's players together cover the whole match, second by second
        for p in truth.players:
            slot = checks["slot_of"][p.player_id]
            seconds[slot] = seconds.get(slot, 0) + len(p.series.t)
        assert set(seconds.values()) == {checks["truth_seconds"]}
        assert all(len(ids) <= 22 for ids in checks["on_pitch"])
        assert truth.runs
        assert truth.settings["noise_sigma_m"] == P.NOISE_SIGMA
        assert truth.settings["tired_below"] == P.TIRED_BELOW
        assert abs(truth.settings["tempo"] - 1) <= P.TEMPO_CLIP_SD * P.TEMPO_SD + 1e-9
        series = truth.players[0].series  # the home goalkeeper plays the whole match
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


# Shots: an accepted gap since decision 46 (README "Accepted gaps"): the onside runs and runs in
# behind make more chances, and the fit (SHOT_RATE, SHOT_RATE_CLEAR) left 29 a match on 120 seeds
# against 24.4 [Bassek2025] and Wyscout's Premier League 23.4 (10th-90th percentile of matches
# 17-30). It reports XPASS once the gap closes.
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
        [sys.executable, "-m", "runningbattery.sim.summary", str(folders[1])],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "ball in play" in out and "H01" in out and "A11" in out


# --- Fatigue switch and truth.json ---------------------------------------------------------------


def test_no_fatigue_control(folders):
    """``--no-fatigue``: the same seed, teams, physiology settings, tempo and planned
    substitutions, every player fresh (neutral series, no skipped runs), and the match plays out
    differently (so a substitution may wait for a different stoppage). ``--no-tempo`` as well
    leaves the tempo and the substitutions out (the generator as it was before fatigue and
    tempo, 81f023d; checked file for file on one machine apart from schema_version, since
    matches differ between machines)."""
    on, off, legacy = (read_truth(folders[k]) for k in (1, "off", "legacy"))
    assert off.fatigue_enabled is False and legacy.fatigue_enabled is False
    assert off.settings["tempo"] == on.settings["tempo"] and "tempo" not in legacy.settings
    assert "tank_m" not in off.settings
    for truth in (off, legacy):
        assert all(r.executed for r in truth.runs)
        for p in truth.players:
            assert set(p.series.fast_pool) == {1.0} and set(p.series.run_choice_mult) == {1.0}
            assert not any(p.series.tired)
    meta = {
        k: MatchMetadata.model_validate_json((folders[k] / METADATA).read_text())
        for k in (1, "off", "legacy")
    }
    starters = {k: [p for t in m.teams for p in t.players if p.starter] for k, m in meta.items()}
    assert starters[1] == starters["off"] == starters["legacy"]
    pairs = {k: {s.player_out: s.player_in for s in meta[k].substitutions} for k in (1, "off")}
    shared = pairs[1].keys() & pairs["off"].keys()
    assert len(shared) >= 4 and all(pairs[1][k] == pairs["off"][k] for k in shared)
    assert not meta["legacy"].substitutions and len(legacy.players) == 22
    params = {k: {p.player_id: p.params for p in t.players} for k, t in (("on", on), ("off", off))}
    assert all(params["off"][k] == v for k, v in params["on"].items() if k in params["off"])
    assert (folders[1] / TRACKING).read_bytes() != (folders["off"] / TRACKING).read_bytes()


def test_varied_match_records_its_settings(folders):
    """``--vary``: the match's effect sizes and noise are drawn in their ``params.VARY`` ranges
    and written to ``settings`` with the wider player prior; the label thresholds stay fixed;
    the starters are the same players (same names), with values from the wider prior."""
    plain, varied = read_truth(folders[1]), read_truth(folders["vary"])
    s = varied.settings
    assert s["varied"] is True and "varied" not in plain.settings
    for key, (lo, hi) in P.VARY.items():
        assert lo <= s[key] <= hi, key
    assert s["tired_below"] == P.TIRED_BELOW and s["late_tank_below"] == P.LATE_TANK_BELOW
    assert s["prior_cs_sd"] == P.VARY_PLAYERS["cs_sd"]
    assert (s["prior_d_prime_lo"], s["prior_d_prime_hi"]) == P.VARY_PLAYERS["d_prime_range"]
    meta = {
        k: MatchMetadata.model_validate_json((folders[k] / METADATA).read_text())
        for k in (1, "vary")
    }
    names = {k: [p.name for t in m.teams for p in t.players if p.starter] for k, m in meta.items()}
    assert names[1] == names["vary"]
    assert [p.params for p in plain.players[:22]] != [p.params for p in varied.players[:22]]


def test_truth_series_with_fatigue(sim1):
    """Pools and tank stay fractions; the tank never rises within a half and gets some back at
    half-time; capacity falls by at most CAPACITY_MAX_LOSS; ``tired`` is the pool term below
    TIRED_BELOW (values rounded to 0.001); some players get tired and skip runs."""
    from runningbattery.sim.physiology import below

    tired_any = False
    for p in sim1.truth.players:
        s = p.series
        period = np.array(s.period)
        tank = np.array(s.tank)
        for h in (1, 2):
            assert np.all(np.diff(tank[period == h]) <= 0)
        if (period == 1).any():
            assert tank[period == 2][0] >= tank[period == 1][-1]
        else:  # a substitute comes on fresh; his first record is up to 0.9 s later
            assert tank[0] >= 0.99 and s.fast_pool[0] >= 0.99
        assert min(s.speed_mult) >= 1 - P.CAPACITY_MAX_LOSS - 1e-9
        ff = p.params.fast_fraction
        left = ff * np.array(s.fast_pool) + (1 - ff) * np.array(s.slow_pool)
        pools, tired = below(left, P.POOL_FREE, P.POOL_GAIN), np.array(s.tired)
        assert np.all(pools[tired] <= P.TIRED_BELOW + 3e-3)
        assert np.all(pools[~tired] >= P.TIRED_BELOW - 3e-3)
        assert np.all(np.array(s.run_choice_mult)[tired] <= P.TIRED_BELOW + 1e-3)
        tired_any |= tired.any()
    assert tired_any
    skipped = [r for r in sim1.truth.runs if not r.executed]
    assert skipped and all(r.t_end >= r.t_start for r in skipped)
    assert {RunPurpose.RECOVERY_RUN, RunPurpose.COVERING} <= {r.purpose for r in skipped}


def test_capacity_holds_every_frame(sim1):
    """Nobody runs faster than S0 × speed_mult, frame by frame (noise-free positions), whoever
    is in the slot. The multiplier only falls within a half, so the value recorded a second
    earlier bounds it."""
    truth = {p.player_id: p.series for p in sim1.truth.players}
    for pf in sim1.periods:
        v = speeds(pf.pos)
        t = np.arange(len(v)) / P.FRAME_RATE_HZ
        for spell in sim1.spells:
            s = truth[spell.player.id]
            here = np.array(s.period) == pf.period
            if not here.any():
                continue
            seconds, mult = np.array(s.t)[here], np.array(s.speed_mult)[here]
            on = _holds(spell, pf.period, t)
            k = np.clip(np.searchsorted(seconds, t[on], side="right") - 2, 0, len(mult) - 1)
            cap = spell.player.params.s0 * mult[k] + 0.01  # rounding
            assert np.all(v[on, spell.slot] <= cap), spell.player.id


def test_fatigue_checks_on_a_match(sim1):
    """``sim.fatigue_checks`` on a whole match: every pipeline gives numbers, tired players
    skip a larger share of hard runs than fresh ones, and the table prints."""
    from runningbattery.sim import fatigue_checks

    out = fatigue_checks.summarise([fatigue_checks.sim_measure(sim1)])
    assert len(out["leifsson"]) == 9 and all(len(v) == 5 for v in out["leifsson"].values())
    assert np.isfinite(out["end"]["hir_last15_vs_first15"])
    assert out["fang"]["efforts"]["peak"] > 0
    skips = out["skips"]["all"]
    assert skips["tired"] < skips["fresh"] <= 0  # % skipped, as a negative change
    assert 0 < out["tired_pct"] < 100 and 0 < out["late_pct"] < 100
    assert out["subs"]["minutes"] > 0 and np.isfinite(out["subs"]["vs_whole"])
    assert "Leifsson2024" in fatigue_checks.format_table(out, out)


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
    """Two players 3 m apart running at each other: team-mates step aside, each to their own
    right, before they meet; opponents are judged where they are now (pressing and duels are
    left alone)."""
    pos = np.array([[-1.5, 0.0], [1.5, 0.0]])
    vel = np.array([[1.5, 0.0], [-1.5, 0.0]])
    mates = movement.push_apart(pos, np.array([0, 0]), vel=vel)
    assert mates[0, 1] < 0 < mates[1, 1]
    assert np.allclose(mates[:, 0], 0.0)
    assert np.allclose(movement.push_apart(pos, np.array([0, 0])), 0.0)
    assert np.allclose(movement.push_apart(pos, np.array([0, 1]), vel=vel), 0.0)


def test_push_apart_judges_team_mates_at_closest_approach():
    """Paths that cross half a second from now, 3.06 m apart now and again in 1 s: team-mates
    step aside now (judged at their positions 1 s on, they would not be); opponents are left
    alone."""
    pos = np.array([[-1.5, 0.3], [1.5, -0.3]])
    vel = np.array([[3.0, 0.0], [-3.0, 0.0]])
    mates = movement.push_apart(pos, np.array([0, 0]), vel=vel)
    assert mates[0, 1] > 0 > mates[1, 1]  # sideways, away from where the other will pass
    assert np.allclose(mates[:, 0], 0.0)
    assert np.allclose(movement.push_apart(pos + vel, np.array([0, 0])), 0.0)
    assert np.allclose(movement.push_apart(pos, np.array([0, 1]), vel=vel), 0.0)


def test_ball_moves_to_its_player(sim1):
    """The ball never jumps to a player's feet: in play it moves at most 40 m/s between frames (a
    hard shot or pass is about 30), at receptions, interceptions and won tackles too (decision 38:
    it moved 4-7 m in 0.1 s)."""
    for pf in sim1.periods:
        speed = np.hypot(*np.diff(pf.ball[:, :2], axis=0).T) * P.FRAME_RATE_HZ
        alive = pf.alive[1:] & pf.alive[:-1]
        assert speed[alive].max() <= 40.0, (pf.period, speed[alive].max())


def test_clear_chances_end_in_shots(sim1):
    """Inside 25 m with no outfield defender goal-side within 8 m of the line to goal, players
    shoot (some after carrying on at goal) rather than pass back (decision 38: 13 of 23 such
    chances in the story match were backward passes)."""
    home_up = sim1.metadata.teams[0].attacks_positive_x_in_period_1
    clear, shots = 0, 0
    for e in sim1.events:
        if e.type not in (EventType.PASS, EventType.SHOT) or e.subtype in (
            "corner", "free_kick", "throw_in", "goal_kick", "kick_off",
        ):  # fmt: skip
            continue
        home = e.team_id == "home"
        up = home_up if e.period == 1 else not home_up
        goal = np.array([(1.0 if up == home else -1.0) * P.HALF_LENGTH, 0.0])
        a = np.array([e.start.x, e.start.y])
        seg = goal - a
        dist = float(np.hypot(*seg))
        if dist > 25.0:
            continue
        pf = sim1.periods[e.period - 1]
        k = min(round(e.t * P.FRAME_RATE_HZ), len(pf.alive) - 1)
        q = (pf.pos[k, 12:22] if home else pf.pos[k, 1:11]) - a
        along = q @ seg / dist
        across = np.abs(seg[0] * q[:, 1] - seg[1] * q[:, 0]) / dist
        if np.any((along > 0) & (along <= dist) & (across <= 8.0)):
            continue
        clear += 1
        shots += e.type == EventType.SHOT
    assert clear >= 3 and shots >= 0.8 * clear, (shots, clear)


def test_dead_ball_separation():
    """While the ball is dead team-mates may stand SEPARATION_DEAD apart, never on one spot."""
    pos = np.array([[0.0, 0.0], [0.0, 1.0]])
    team_of = np.array([0, 0])
    assert np.allclose(movement.push_apart(pos, team_of, team_keep=P.SEPARATION_DEAD), 0.0)
    assert np.allclose(movement.spread_targets(pos, team_of, keep=P.SEPARATION_DEAD), pos)
    same = np.zeros((2, 2))
    spread = movement.spread_targets(same, team_of, keep=P.SEPARATION_DEAD)
    assert np.hypot(*(spread[0] - spread[1])) == pytest.approx(P.SEPARATION_DEAD)
    push = movement.push_apart(same, team_of, team_keep=P.SEPARATION_DEAD)
    assert push[0, 0] < 0 < push[1, 0]


def _engine():
    """An engine a few seconds into a match."""
    rng = np.random.default_rng(0)
    engine = MatchEngine(rng, make_teams(rng))
    engine.run_period(1, 50, 0)
    return engine


def _hold(engine, seconds: float, t0: float = 5.0) -> np.ndarray:
    """Hold the current dead ball for ``seconds``, due at their end but never taken (set-piece
    jobs pace themselves to it, ``Roles.dead_pace``); positions of every frame."""
    engine.restart.t = t0 + seconds
    frames = []
    for k in range(round(seconds * P.FRAME_RATE_HZ)):
        t = t0 + k / P.FRAME_RATE_HZ
        engine.follow_ball(t)
        engine.move(t)
        frames.append(engine.pos.copy())
    return np.array(frames)


def _held_restart(kind: str, spot_uv: tuple[float, float], seconds: float = 30.0):
    """An engine a few seconds into a match, then a restart for team 0 at ``spot_uv`` (team 0's
    attacking frame), held for ``seconds`` while everyone moves into place."""
    engine = _engine()
    spot = engine.to_uv(0, np.array(spot_uv))
    engine.schedule_restart(kind, 0, spot, 5.0, spot.copy())
    engine.history = _hold(engine, seconds)
    return engine, spot


def _team_mate_gaps(pos: np.ndarray) -> list[np.ndarray]:
    """Distance from each player to their nearest team-mate, per team."""
    out = []
    for team in (pos[:11], pos[11:]):
        d = np.hypot(*(team[:, None] - team[None]).transpose(2, 0, 1))
        np.fill_diagonal(d, np.inf)
        out.append(d.min(axis=1))
    return out


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
    """WALL_SIZE[0] defenders side by side, WALL_GAP apart, at the edge of the 9.15 m circle.
    Held 45 s: at a set piece the wall comes from the front players, who may start 40 m away
    and walk round the circle."""
    engine, spot = _held_restart("free_kick", (P.HALF_LENGTH - 24.0, 4.0), 45.0)
    edge = P.RESTART_DISTANCE + P.RESTART_MARGIN
    wall = engine.pos[engine.roles.wall_members]
    d = np.hypot(*(wall - spot).T)
    assert len(wall) == P.WALL_SIZE[0] and np.all(np.abs(d - edge) < 0.3), d.round(2)
    gaps = np.hypot(*(wall[:, None] - wall[None]).T)
    np.fill_diagonal(gaps, np.inf)
    assert np.allclose(gaps.min(axis=1), P.WALL_GAP, atol=0.15), gaps.min(axis=1)


def test_corner_crowds_the_box():
    """A held corner: the pack (CORNER_PACK) stands side by side, each with a team-mate within
    1 m but never on one spot (SEPARATION_DEAD), and each has a marker within 1.5 m; two
    defenders stand at their zonal spots (CORNER_ZONAL)."""
    engine, _ = _held_restart("corner", (P.HALF_LENGTH, -P.HALF_WIDTH))
    attack, defend = _team_mate_gaps(engine.pos)
    plan = engine.roles.plan
    # The pack: the attackers holding a spot that is not a CORNER_SPOTS one (a pack player who
    # takes the corner hands his spot to the nearest free attacker, ``set_piece_plan``).
    spots = {slot for slot, _, _ in P.CORNER_SPOTS}
    pack = [i for i, _, holds in plan if holds and i % 11 not in spots]
    assert len(pack) == len(P.CORNER_PACK)
    assert np.all(attack[pack] < 1.0), attack.round(2)
    assert min(attack.min(), defend.min()) > P.SEPARATION_DEAD - 0.15
    marked = np.hypot(*(engine.pos[pack][:, None] - engine.pos[None, 11:]).transpose(2, 0, 1))
    assert np.all(marked.min(axis=1) < 1.5), marked.min(axis=1)
    zonal = [(i, spot) for i, spot, _ in plan if i - 11 in [s for s, _, _ in P.CORNER_ZONAL]]
    assert len(zonal) == len(P.CORNER_ZONAL)
    assert all(np.hypot(*(engine.pos[i] - spot)) < 1.0 for i, spot in zonal)


def test_free_kick_near_goal_drops_the_defence():
    """A free kick 28 m out (in wall range, not SET_PIECE_U upfield): besides the wall, the
    markers hold a line FREE_KICK_LINE_GAP goal-side of the ball and the attackers stand level
    with it, onside [IFAB2025, Law 11], give or take FREE_KICK_LINE_JITTER (not ruler-straight).
    """
    depth = 28.0
    engine, _ = _held_restart("free_kick", (P.HALF_LENGTH - depth, 3.0))
    line = np.clip(depth - P.FREE_KICK_LINE_GAP, *P.FREE_KICK_LINE)
    u = engine.to_uv(0, engine.pos)[:, 0]  # team 0 attacks towards u = +52.5
    near = P.FREE_KICK_LINE_JITTER + 0.5
    markers = [11 + s for s in P.BOX_MARKERS]
    assert np.all(np.abs(P.HALF_LENGTH - u[markers] - line) < near), (P.HALF_LENGTH - u).round(1)
    forward = [i for i, _, holds in engine.roles.plan if holds]
    assert len(forward) == len(P.BOX_MARKERS)
    assert np.all(np.abs(P.HALF_LENGTH - u[forward] - line - 1.0) < near)
    assert np.std(u[forward]) > 0.2  # staggered
    second_last = np.sort(u[11:])[-2]
    assert u[forward].max() < second_last  # onside


def test_attackers_keep_clear_of_the_wall():
    """Attackers stay at least 1 m from a wall of three or more [IFAB2025, Law 13]: from every
    wall member standing in place (within 0.3 m of its spot), in every frame."""
    # 45 s: a wall member may come from 38 m away at the set-piece walk (decision 46's match
    # state: the striker, about 35 s; the check is every frame he is in place).
    engine, _ = _held_restart("free_kick", (P.HALF_LENGTH - 23.0, 1.0), 45.0)
    wall = engine.roles.wall(True)
    assert len(wall) >= P.WALL_SIZE[0]
    h = engine.history
    in_place = np.stack([np.hypot(*(h[:, i] - spot).T) < 0.3 for i, spot in wall], axis=1)
    assert in_place[-1].all()
    members = [i for i, _ in wall]
    gaps = np.hypot(*(h[:, :11, None] - h[:, None, members]).transpose(3, 0, 1, 2))
    gaps[:, engine.restart.taker] = np.inf
    gaps = np.where(in_place[:, None, :], gaps, np.inf)
    assert gaps.min() >= 1.0, gaps.min()


def test_goal_huddle():
    """After a goal the HUDDLE_N nearest team-mates gather round the scorer (within 1 m, never
    on one spot) and hold for HUDDLE_HOLD_S; then everyone walks back for the kick-off."""
    engine = _engine()
    scorer = 10  # team 0's centre-forward
    engine.goal(5.0, scorer, engine.pos[scorer].copy())
    huddle = engine.restart.huddle
    mates = huddle.mates
    assert len(mates) == P.HUDDLE_N
    frames = _hold(engine, 60.0)
    assert huddle.formed
    close = np.all(
        np.hypot(*(frames[:, mates] - frames[:, None, scorer]).transpose(2, 0, 1)) < 1.0, 1
    )
    held = close[round((huddle.t_end - P.HUDDLE_HOLD_S - 5.0) * P.FRAME_RATE_HZ) :][
        : round(P.HUDDLE_HOLD_S * P.FRAME_RATE_HZ)
    ]
    # together for most of the hold (decision 46's refit: 0.75, the last to arrive settling
    # from 1.11 m into the 0.85-m ring; 0.8 before)
    assert held.mean() > 0.7, held.mean()
    at = frames[round((huddle.t_end - 5.0 - 1.0) * P.FRAME_RATE_HZ)]
    assert _team_mate_gaps(at)[0].min() > P.SEPARATION_DEAD - 0.15
    u = engine.to_uv(0, frames[-1][:11])[:, 0]
    assert np.all(u < 0.0)  # back in their own half, the opponents kick off


def test_dead_ball_jobs_pace_to_the_restart_and_brake():
    """When the ball goes dead, a sprinting player brakes at once (below HI_SPEED within 0.5 s,
    ``DEAD_BRAKE_ABOVE``), and nobody is above HI_SPEED after 1.5 s. Set-piece jobs pace
    themselves to the restart (``Roles.dead_pace``): a walk with time to spare, the jog when
    there is none; with a corner 30 s away they go up slower than with it 8 s away, and still
    reach their spots in time. The jog cap stays clearly below HI_SPEED for every player
    (decision 40)."""
    cap = P.WALL_SPEED * P.S0_RANGE[1]  # after the work rate (decision 42)
    assert cap < P.HI_SPEED - 0.4, cap
    engine = _engine()
    engine.roles.effort[:] = 1.3  # whatever the work rate
    engine.schedule_restart("throw_in", 0, np.array([0.0, P.HALF_WIDTH]), 5.0, np.zeros(2))
    engine.restart.t = 6.0  # past due: everyone with a job jogs
    _, want, _, calm, _ = engine.roles.targets(5.0)
    assert np.all(want[~calm] <= P.WALL_SPEED * engine.s0[~calm] + 1e-9)
    engine = _engine()
    engine.schedule_restart("throw_in", 0, np.array([0.0, P.HALF_WIDTH]), 5.0, np.zeros(2))
    engine.restart.t = 65.0
    i = engine.restart.taker
    near, far = engine.pos[i] + [2.0, 0.0], engine.pos[i] + [80.0, 0.0]
    assert engine.roles.dead_pace(i, near, 5.0) == P.SET_PIECE_WALK
    assert engine.roles.dead_pace(i, far, 30.0) == P.WALL_SPEED  # past due (29 s)
    pace = engine.roles.dead_pace(i, engine.pos[i] + [60.0, 0.0], 5.0)
    assert pace == pytest.approx(
        60.0 / (P.SET_PIECE_DUE * 60.0) / (engine.s0[i] * engine.roles.effort[i])
    )
    mean = {}
    for seconds in (30.0, 8.0):
        engine = _engine()
        spot = engine.to_uv(0, np.array([P.HALF_LENGTH, -P.HALF_WIDTH]))
        engine.schedule_restart("corner", 0, spot, 5.0, spot.copy())
        sprinters = [3, 8, 14]
        engine.vel[sprinters] = [8.0, 0.0]
        frames = _hold(engine, seconds)
        speed = np.hypot(*np.diff(frames, axis=0).transpose(2, 0, 1)) * P.FRAME_RATE_HZ
        assert np.all(speed[4, sprinters] < P.HI_SPEED), speed[4, sprinters]
        assert speed[round(1.5 * P.FRAME_RATE_HZ) :].max() < P.HI_SPEED
        jobs = [i for i, _, _ in engine.roles.plan] + [engine.restart.taker]
        mean[seconds] = np.median(speed[15:60, jobs].mean(axis=0))  # 1.5–6 s after dead
        if seconds == 30.0:
            gaps = [np.hypot(*(frames[-1, i] - at)) for i, at, holds in engine.roles.plan if holds]
            assert max(gaps) < 1.0, np.round(gaps, 2)
    assert mean[30.0] < mean[8.0] - 0.5, mean


def test_clearances_go_behind_only_close_to_goal():
    """An out clearance goes behind for a corner only from within CLEAR_CORNER_DEPTH of the
    goal line, as a short deflection (CLEAR_DEFLECT wider, off the posts); from further out
    it goes over the touchline ahead of the clearer. About CLEAR_OUT of them go out either way
    (decision 40: a keeper's clearance from 15 m went over his own line)."""
    engine = _engine()
    d = 3  # team 0's left-back
    for depth in (2.0, 12.0):
        ends = []
        for k in range(400):
            where = engine.to_uv(0, np.array([-P.HALF_LENGTH + depth, -8.0]))
            engine.clearance(5.0 + k, d, where)
            ends.append((engine.to_uv(0, engine.flight.end), engine.flight.result))
        uv = np.array([e for e, _ in ends])
        out = np.array([r == "out" for _, r in ends])
        behind = uv[:, 0] < -P.HALF_LENGTH
        assert abs(out.mean() - P.CLEAR_OUT) < 0.07, out.mean()
        if depth > P.CLEAR_CORNER_DEPTH:
            assert not behind.any()
            assert np.all(np.abs(uv[out, 1]) > P.HALF_WIDTH) and np.all(uv[out, 0] > -40.0)
        else:
            share = behind.sum() / out.sum()
            assert abs(share - P.CLEAR_OUT_CORNER) < 0.1, share
            wide = np.abs(uv[behind, 1]) - 8.0
            assert np.all((wide >= P.CLEAR_DEFLECT[0] - 1e-9) & (wide <= P.CLEAR_DEFLECT[1]))


def test_carries_in_the_box_head_for_goal():
    """Inside the opponents' penalty area a carry aims at the goal, not straight upfield, so a
    player who receives near the goal line does not run to the byline (decision 40: a cross
    taken 3 m out ended 6 m wide, passed back)."""
    engine = _engine()
    c = 10  # team 0's centre-forward
    u, v = P.HALF_LENGTH - 12.0, 8.0  # far enough from the lines that no carry is clipped
    angles = []
    for k in range(300):
        engine.pos[c] = engine.to_uv(0, np.array([u, v]))
        engine.vel[c] = 0.0
        engine.start_touch(c, 5.0 + k)
        step = engine.to_uv(0, engine.touch.carry_to) - np.array([u, v])
        angles.append(np.arctan2(step[1], step[0]))
    aim = np.arctan2(-v, P.HALF_LENGTH - u)
    assert abs(np.median(angles) - aim) < 0.15, (np.median(angles), aim)  # straight on: -0.08


def test_free_kicks_keep_distance_over_a_match(sim1):
    """A whole match: the median nearest opponent at a free kick is outside 9.15 m (5.8 m before
    the rule), and nobody is inside the corner circle. Quick free kicks may be taken with
    opponents closer [IFAB2025, Law 13], so single kicks are not judged here."""
    slot = sim1.metadata.slot_of()
    nearest = {"free_kick": [], "corner": []}
    for e in sim1.events:
        if e.type == EventType.PASS and e.subtype in nearest:
            taker = slot[e.player_id]
            pos = sim1.periods[e.period - 1].pos[round(e.t * P.FRAME_RATE_HZ)]
            opponents = pos[11:] if taker < 11 else pos[:11]
            spot = np.array([e.start.x, e.start.y])
            nearest[e.subtype].append(np.hypot(*(opponents - spot).T).min())
    assert np.median(nearest["free_kick"]) > P.RESTART_DISTANCE
    assert min(nearest["corner"]) > P.RESTART_DISTANCE + P.CORNER_ARC


def test_teammates_do_not_stack(sim1):
    """Push-apart on a whole match (noise-free positions, ``sim.spacing``). Bounds: the spread
    over seeds 1–30 plus margin (fatigue on, 2026-10-16; with fatigue off, 2026-10-15, the
    spread was about the same). In play, a team-mate within 1 m in 0.15–0.22% of player-frames
    (0.45% judged 1 s ahead instead of at closest approach, about 0.9% before the push-apart;
    IDSSE 0.20%) and within 0.5 m in 0.01–0.03%. Dead balls crowd on purpose (corner pack,
    walls, goal huddle; SEPARATION_DEAD): within 1 m 1.4–3.4%, but within 0.5 m only
    0.01–0.21%, so nobody stands on a team-mate's spot."""
    s = spacing.sim_measure(sim1)
    assert s["mate_1m_play"] < 0.35, s["mate_1m_play"]
    assert s["mate_0.5m_play"] < 0.06, s["mate_0.5m_play"]
    assert s["ep_mate_max_play"] < 8.0  # in play, nobody stays on a team-mate's spot
    assert 0.8 < s["mate_1m_dead"] < 5.0, s["mate_1m_dead"]
    assert s["mate_0.5m_dead"] < 0.3, s["mate_0.5m_dead"]


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
    """Every player, every frame of a whole match (noise-free positions), with the values of
    whoever is in the slot."""
    for pf in sim1.periods:
        v = speeds(pf.pos)
        a0 = _per_frame(sim1, pf, lambda s: s.player.params.a0)[1:-1]
        s0 = _per_frame(sim1, pf, lambda s: s.player.params.s0)[1:-1]
        _limits_hold(v[:-1], v[1:], a0, s0)


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
            assert r.purpose in RunPurpose and r.player_id in ids
            assert 0.0 <= r.t_start and r.t_end <= length[r.period]
            if r.executed:  # a skipped run keeps its planned end (test_truth_series_with_fatigue)
                assert r.t_end - r.t_start >= P.HI_MIN_S - 1e-9
                seen.add(r.purpose)
    # Both phases of play show up: most of Ju2022's classes appear in five matches.
    assert len(seen) >= 9, seen
    assert {RunPurpose.RECOVERY_RUN, RunPurpose.COVERING, RunPurpose.RUN_IN_BEHIND} <= seen


def test_runs_are_high_intensity(sim1):
    """Each run made is above 5.5 m/s for its whole span [Ju2022, p.974], and only those
    spells."""
    slot = sim1.metadata.slot_of()
    v = {pf.period: speeds(pf.pos) for pf in sim1.periods}
    rate = P.FRAME_RATE_HZ
    for r in sim1.truth.runs:
        if not r.executed:
            continue
        a, b = round(r.t_start * rate), round(r.t_end * rate)
        j = slot[r.player_id]
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
    slot = match.metadata.slot_of()
    clean = np.concatenate([pf.pos for pf in sim1.periods])
    errors, missing = [], 0
    for k, frame in enumerate(match.frames):
        got = {p.id: (p.x, p.y) for p in frame.players}
        missing += 22 - len(got)
        errors += [np.subtract(xy, clean[k, slot[pid]]) for pid, xy in got.items()]
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
    from runningbattery.sim.replay import write_stills

    out = tmp_path / "stills.png"
    write_stills(load_window(folders[1], start=600.0, seconds=4.0), out, 2)
    assert out.stat().st_size > 10_000


def test_story_controls_press_until_the_hour_and_sub_the_exposed_full_back():
    """Story controls (PLAN §2.3; sim.story): the press is on for the pressing team only, until
    press_until_min; the story substitution takes the exposed full-back's slot, like for like,
    and keeps the number of substitutions."""
    from runningbattery.sim.rosters import make_teams, plan_substitutions
    from runningbattery.sim.story import STORIES, story_subs

    story = STORIES["press-fade"]
    assert story.pressing(0, 59 * 60.0) and not story.pressing(0, 60 * 60.0)
    assert not story.pressing(1, 10 * 60.0)
    rng = np.random.default_rng(3)
    teams = make_teams(rng)
    plans = plan_substitutions(rng, teams)
    new = story_subs(plans, teams, story)
    assert len(new) == len(plans)
    mine = [p for p in new if p.slot == story.exposed_slot]
    assert len(mine) == 1 and mine[0].clock_s == story.sub_minute * 60.0
    off = teams[0].players[story.exposed_slot]
    assert mine[0].player.position == off.position == "FB" and mine[0].player.slot == off.slot
    assert len({p.slot for p in new}) == len(new)  # a slot is substituted once
    assert story.settings()["name"] == "press-fade"


def _play(engine, t0: float, seconds: float) -> tuple[np.ndarray, list]:
    """Step ``engine`` as ``run_period`` does from ``t0``; positions of every frame, and the
    substitutions made."""
    frames, subs = [], []
    for k in range(round(seconds * P.FRAME_RATE_HZ)):
        t = round(t0 + k / P.FRAME_RATE_HZ, 1)
        engine.update(t)
        if engine.pending and engine.mode == "dead":
            subs += engine.substitute_due(t, k)
        if engine.leaving:
            subs += engine.walk_off(t, k)
        engine.follow_ball(t)
        frames.append(engine.pos.copy())
        engine.move(t)
    return np.array(frames), subs


def test_trackers_follow_the_runner_and_stop_with_the_pass():
    """Decision 41: a defender tracking a runner in behind aims goal-side of where the runner is
    now, not of where he was heading, and stops once the pass reaches someone else."""
    from runningbattery.sim.match import Flight
    from runningbattery.sim.roles import Run

    engine = _engine()
    roles = engine.roles
    roles.clear()
    runner, receiver = 10, 9  # team 0's centre-forward and a winger
    engine.pos[runner] = engine.to_uv(0, np.array([20.0, 5.0]))
    goal = engine.to_uv(0, np.array([45.0, 4.0]))
    roles.runs[runner] = Run(RunPurpose.RUN_IN_BEHIND, 20.0, P.BEHIND_EFFORT, target=goal)
    roles.track(5.0, runner)
    tracker = next(i for i, r in roles.runs.items() if r.follow == runner)
    assert engine.positions[tracker] in (Position.CB, Position.FB)
    far = engine.to_uv(0, np.array([-45.0, -30.0]))  # the pass goes to the winger, far away
    engine.flight = Flight(far, far.copy(), 5.0, 8.0, 0.0, "complete", by=7, to=receiver,
                           event=roles.runs[tracker].follow_pass)  # fmt: skip
    engine.mode = "flight"
    for spot in ([20.0, 5.0], [28.0, 2.0]):
        engine.pos[runner] = engine.to_uv(0, np.array(spot))
        tgt, _, purpose, _, _ = roles.targets(5.5)
        want = roles.goal_side(1, engine.pos[runner], P.TRACK_GOAL_SIDE)
        assert np.hypot(*(tgt[tracker] - want)) < 0.5
        assert purpose[tracker] == PURPOSES_CODE[RunPurpose.RECOVERY_RUN]
    engine.start_touch(receiver, 6.0)  # it reached someone else
    roles.targets(6.1)
    assert tracker not in roles.runs


def test_no_sprint_straight_back():
    """Decision 41: within TURN_S of being above HI_SPEED one way, a run the other way goes no
    faster than SHAPE_RUN_MIN; after it, at its planned speed."""
    from runningbattery.sim.roles import Run

    engine = _engine()
    roles = engine.roles
    roles.clear()
    engine.mode, engine.loose_point, engine.loose_since = "loose", np.array([40.0, 30.0]), 5.0
    i = 3
    engine.pos[i] = (-20.0, -20.0)  # far from the loose ball: not a chaser
    back = engine.pos[i] - [20.0, 0.0]
    for t, capped in ((6.0, True), (5.0 + P.TURN_S + 0.5, False)):
        roles.runs[i] = Run(RunPurpose.RECOVERY_RUN, t + 5.0, 1.0, target=back)
        roles.fast_t[i], roles.fast_dir[i] = 5.0, (1.0, 0.0)
        engine.vel[i] = 0.0
        _, cap, _, _, _ = roles.targets(t)
        share = P.SHAPE_RUN_MIN if capped else 1.0
        assert cap[i] == pytest.approx(min(share * roles.effort[i], 1.0) * engine.s0[i])


def test_duels_need_the_players_within_reach():
    """Decision 41: a ground duel (or foul) needs the challenger within DUEL_REACH of the carrier
    and the ball; from DUEL_ENGAGE he goes in for it and holds the carrier up. An aerial
    challenger not under the ball at arrival does not contest it."""
    from runningbattery.sim.match import Flight

    engine = _engine()
    c, opp = 8, 13
    engine.pos[c], engine.vel[c] = engine.to_uv(0, np.array([0.0, 0.0])), 0.0
    engine.start_touch(c, 5.0)
    engine.touch.duel_at, engine.touch.t_release = 5.0, 5.5
    others = [j for j in engine.members(1) if j != opp]
    engine.pos[others] = engine.pos[c] + [0.0, 30.0]
    engine.pos[opp] = engine.pos[c] + engine.to_uv(0, np.array([3.0, 0.0]))
    n = len(engine.events)
    engine.update_touch(5.0)
    assert engine.touch.challenger == opp and engine.touch.t_release >= 5.0 + P.DUEL_HOLD_S
    assert not any(e["type"] == EventType.DUEL for e in engine.events[n:])
    engine.pos[opp] = engine.pos[c] + engine.to_uv(0, np.array([1.0, 0.0]))
    engine.update_touch(5.1)
    duel = [e for e in engine.events[n:] if e["type"] == EventType.DUEL]
    assert len(duel) == 1 and duel[0]["player"] == opp

    for gap, contested in ((3.0, False), (0.6, True)):
        engine = _engine()
        r, ch = 9, 14
        end = engine.to_uv(0, np.array([10.0, 10.0]))
        engine.pos[r], engine.pos[ch] = end, end + [gap, 0.0]
        engine.flight = Flight(end - [20.0, 0.0], end, 4.0, 5.0, 8.0, "aerial", by=7, to=r,
                               challenger=ch, receiver_wins=False)  # fmt: skip
        engine.mode = "flight"
        n = len(engine.events)
        engine.arrive(5.0)
        aerial = [e for e in engine.events[n:] if e["type"] == EventType.DUEL]
        assert bool(aerial) == contested
        if not contested:
            got = engine.events[n]
            assert got["type"] == EventType.RECEPTION and got["player"] == r


def test_low_passes_are_cut_out_on_the_way():
    """Decision 41: a low pass that rolls within CUT_OUT_CONTROL of an outfield opponent is
    intercepted there; within CUT_OUT_REACH, deflected loose; further off, it arrives."""
    from runningbattery.sim.match import Flight

    for off, result in ((0.1, "intercepted"), (0.5, "loose"), (2.0, "complete")):
        engine = _engine()
        engine.roles.clear()
        passer, to, opp = 6, 9, 15
        a = engine.to_uv(0, np.array([-10.0, 0.0]))
        b = engine.to_uv(0, np.array([10.0, 0.0]))
        engine.pos[passer], engine.pos[to] = a, b
        others = [j for j in engine.members(1)[1:] if j != opp]
        engine.pos[others] = [0.0, 30.0]
        engine.pos[opp] = engine.to_uv(0, np.array([0.0, off]))
        engine.log(EventType.PASS, 5.0, passer, start=a, end=b, outcome="success")
        engine.flight = Flight(a, b, 5.0, 7.0, 0.0, "complete", by=passer, to=to,
                               event=len(engine.events) - 1)  # fmt: skip
        engine.mode = "flight"
        n = len(engine.events)
        for k in range(1, 25):
            engine.update(round(5.0 + k / P.FRAME_RATE_HZ, 1))
        new = [e["type"] for e in engine.events[n:]]
        if result == "intercepted":
            assert EventType.INTERCEPTION in new and engine.events[n - 1]["outcome"] == "fail"
        elif result == "loose":
            assert EventType.INTERCEPTION not in new and engine.events[n - 1]["outcome"] == "fail"
            assert engine.flight.by == opp and engine.flight.result in ("loose", "out")
        else:
            assert engine.events[n - 1]["outcome"] == "success"
            assert EventType.RECEPTION in new


def test_substitutes_come_on_at_the_halfway_line():
    """Decision 41: at a stoppage the replaced player walks to the halfway line by the benches'
    touchline and leaves there, and the restart waits for him; the substitute comes on at that
    spot and jogs to his place. The slot they share never jumps."""
    from dataclasses import replace

    from runningbattery.sim.rosters import plan_substitutions

    rng = np.random.default_rng(0)
    teams = make_teams(rng)
    plan = plan_substitutions(np.random.default_rng(1), teams)[0]
    engine = MatchEngine(rng, teams, subs=[replace(plan, clock_s=1.0)])
    engine.run_period(1, 50, 0)
    i = plan.slot
    engine.pos[i] = engine.to_uv(int(engine.team_of[i]), np.array([-30.0, 20.0]))
    engine.schedule_restart("throw_in", 0, np.array([10.0, P.HALF_WIDTH]), 5.0, np.zeros(2))
    engine.restart.t = 8.0  # due long before he is off
    n = len(engine.events)
    frames, subs = _play(engine, 5.0, 70.0)
    assert len(subs) == 1 and subs[0][1] == i
    k = subs[0][0]
    assert np.hypot(*(frames[k, i] - engine.sub_point(i))) < 0.6
    assert abs(frames[k, i, 0]) <= P.SUB_ENTRY_X + 0.6 and frames[k, i, 1] < -P.HALF_WIDTH + 1.6
    step = np.hypot(*np.diff(frames[: k + 50, i], axis=0).T) * P.FRAME_RATE_HZ
    assert step.max() < P.HI_SPEED, step.max()  # no jump; walks off, jogs on
    sub = next(e for e in engine.events[n:] if e["type"] == EventType.SUBSTITUTION)
    taken = [e for e in engine.events[n:] if e["type"] == EventType.PASS and e["t"] > 5.0]
    assert taken and taken[0]["t"] > sub["t"]  # the throw-in waited


def test_team_mates_have_distinct_names():
    """Decision 42: no two players of a team (substitutes included) share a first name or a
    surname's start ("Sami Yarrigg" and "Sami Yarrick" were one team's centre-backs); names are
    labels only, drawn as before, so the match does not change."""
    from runningbattery.sim.rosters import FIRST_NAMES, SURNAME_START

    for seed in (2028, 2031, 7):
        m = simulate(seed, f"names{seed}", subs=True)
        for team in m.metadata.teams:
            names = [p.name for p in team.players]
            firsts = [n.split(" ")[0] for n in names]
            starts = [
                max((s for s in SURNAME_START if n.split(" ", 1)[1].startswith(s)), key=len)
                for n in names
            ]
            assert len(set(firsts)) == len(firsts), names
            assert len(set(starts)) == len(starts), names
            assert all(f in FIRST_NAMES for f in firsts)


def test_overlaps_need_room_and_end_with_the_carriers_pass():
    """Decision 45: with the winger on the touchline the overlap aimed 1 m inside him, his own
    spot, and the full-back kept running after the winger passed. Now it goes outside the carrier
    with a lane along the touchline and UNDERLAP_IN inside him without one (also with the defence
    level with him), and a run about the carrier ends when he plays the ball."""
    from runningbattery.sim.roles import Run

    engine = _engine()
    roles = engine.roles
    roles.overlap_chance = 1.0
    carrier, back, other = 9, 4, 3  # team 0: a winger, the full-back on his side, the other one
    cases = ((6.0, 20.0, 1.0), (1.0, 20.0, -P.UNDERLAP_IN), (1.0, 0.0, -P.UNDERLAP_IN))
    for lane, room, out in cases:
        roles.clear()
        c_uv = np.array([10.0, P.HALF_WIDTH - lane])
        engine.pos[carrier] = engine.to_uv(0, c_uv)
        engine.pos[back] = engine.to_uv(0, np.array([-5.0, 25.0]))
        engine.pos[other] = engine.to_uv(0, np.array([-5.0, -25.0]))
        roles.onside_u = lambda team, u=c_uv[0] + room: u
        roles.on_touch(carrier, 5.0)
        run = roles.runs.get(back)
        assert run is not None and run.purpose == RunPurpose.OVER_UNDERLAP
        assert run.carrier == carrier
        assert run.offset_uv[1] == pytest.approx(min(lane - 1.0, 5.0) if out > 0 else out)
    stays = Run(RunPurpose.RUN_IN_BEHIND, 20.0, P.BEHIND_EFFORT, target=np.zeros(2))
    roles.runs[10] = stays
    roles.on_pass(5.5, carrier, 7, False, False, True, engine.pos[7])
    assert back not in roles.runs and roles.runs.get(10) is stays


def test_a_run_does_not_aim_at_a_team_mates_spot():
    """Decision 45: a runner's target stays RUN_SPACE from his team-mates' targets (6.5% of our
    high-speed runs ended within 2.5 m of a team-mate, IDSSE's 3.8%); a presser keeps his."""
    from runningbattery.sim.roles import Run

    engine = _engine()
    roles = engine.roles
    roles.clear()
    runner, mate = 8, 7
    tgt = engine.pos.copy()
    spot = np.array([5.0, 5.0])
    tgt[mate], tgt[runner] = spot, spot + [1.0, 0.0]
    roles.runs[runner] = Run(RunPurpose.MOVE_TO_RECEIVE, 20.0, P.RUN_SPEED, target=tgt[runner])
    engine.pos[mate], engine.vel[:] = spot, 0.0  # where the team-mate stands, too (decision 46)
    purpose = np.full(22, -1, dtype=np.int8)
    purpose[runner] = PURPOSES_CODE[RunPurpose.MOVE_TO_RECEIVE]
    out = roles.space_runs(tgt, np.zeros(22, dtype=bool), purpose)
    assert np.hypot(*(out[runner] - spot)) == pytest.approx(P.RUN_SPACE)
    assert out[runner][0] > spot[0]  # straight away from the team-mate's spot
    others = [i for i in range(22) if i != runner]
    assert np.array_equal(out[others], tgt[others])
    roles.runs[runner].purpose = RunPurpose.CLOSE_DOWN
    purpose[runner] = PURPOSES_CODE[RunPurpose.CLOSE_DOWN]
    assert np.array_equal(roles.space_runs(tgt, np.zeros(22, dtype=bool), purpose), tgt)


def test_a_run_in_behind_holds_the_line_until_the_pass():
    """Decision 46: a run in behind aims no further than the offside line (plus where a dropping
    line will be) while a team-mate carries the ball, and goes BEHIND_TIMING_S before he passes
    (a forward had run 13 m offside while the carrier ran with the ball for 6 s)."""
    from runningbattery.sim.roles import Run

    engine = _engine()
    roles = engine.roles
    carrier, runner = 7, 10
    engine.pos[carrier] = engine.to_uv(0, np.array([0.0, 0.0]))
    engine.start_touch(carrier, 5.0)
    roles.clear()
    engine.touch.t_release = 9.0
    run = Run(RunPurpose.RUN_IN_BEHIND, 20.0, P.BEHIND_EFFORT)
    run.target = engine.to_uv(0, np.array([48.0, 0.0]))
    run.onside = run.next_pass = True
    roles.runs[runner] = run
    engine.follow_ball(5.1)
    tgt, _, purpose, _, _ = roles.targets(5.1)
    assert purpose[runner] == PURPOSES_CODE[RunPurpose.RUN_IN_BEHIND]
    assert engine.to_uv(0, tgt[runner])[0] <= roles.onside_aim(0) + 1e-9
    tgt, _, _, _, _ = roles.targets(9.0 - P.BEHIND_TIMING_S + 0.1)
    assert engine.to_uv(0, tgt[runner])[0] > roles.onside_aim(0) + 5.0  # on his way


def test_a_run_for_the_next_pass_ends_when_it_goes_elsewhere():
    """Decision 46: runs in behind, into space, in support and into the box are for the next
    pass; they end when it goes to someone else square or back (a fifth ran on for 2 s), go on
    with a forward pass (the attack goes on), and runners into the box go on to attack a cross."""
    from runningbattery.sim.roles import Run

    engine = _engine()
    roles = engine.roles
    roles.clear()
    passer, space, box, receiver = 7, 9, 10, 8
    for i, why in ((space, RunPurpose.MOVE_TO_RECEIVE), (box, RunPurpose.BREAK_INTO_BOX)):
        roles.runs[i] = Run(why, 20.0, P.RUN_SPEED, target=engine.pos[i].copy(), next_pass=True)
    ahead = engine.pos[passer] + engine.to_uv(0, np.array([P.BEHIND_PASS_FORWARD + 5.0, 0.0]))
    back = engine.pos[passer] + engine.to_uv(0, np.array([-5.0, 0.0]))
    roles.on_pass(5.0, passer, receiver, through=False, cross=False, open_play=False, end=ahead)
    assert space in roles.runs and box in roles.runs  # forward: the attack goes on
    roles.on_pass(5.5, passer, receiver, through=False, cross=True, open_play=False, end=back)
    assert space not in roles.runs and box in roles.runs
    roles.on_pass(6.0, passer, receiver, through=False, cross=False, open_play=False, end=back)
    assert box not in roles.runs


def test_a_run_up_into_shape_ends_when_the_shape_goes_back():
    """Decision 46: with the ball, a push-up ends once the shape spot it runs to is behind him
    (40% of push-ups ran on for 2 s after a pass back)."""
    from runningbattery.sim.roles import Run

    engine = _engine()
    roles = engine.roles
    roles.clear()
    engine.poss_team = engine.last_team = 0
    back = 2  # a centre-back
    shape, holder = roles.shape()
    assert holder == 0
    roles.runs[back] = Run(RunPurpose.PUSH_UP_PITCH, 20.0, P.SHAPE_RUN_SPEED, shape=True)
    engine.pos[back] = shape[back] + engine.to_uv(0, np.array([-15.0, 0.0]))  # below his spot
    roles.targets(5.0)
    assert back in roles.runs
    engine.pos[back] = shape[back] + engine.to_uv(0, np.array([15.0, 0.0]))  # the spot went back
    roles.targets(5.1)
    assert back not in roles.runs


def test_the_cover_stands_diagonally_and_the_jobs_stick():
    """Decision 46: the cover defender stands COVER_SIDE across from the carrier's line to goal,
    towards the middle, not in the presser's lane; the presser keeps his job until another
    defender is ROLE_KEEP_M nearer the carrier (they swapped every frame and ran side by side)."""
    engine = _engine()
    roles = engine.roles
    carrier = 9
    engine.pos[carrier] = engine.to_uv(0, np.array([10.0, 20.0]))
    engine.start_touch(carrier, 5.0)
    roles.clear()
    engine.follow_ball(5.0)
    tgt, _, purpose, _, _ = roles.targets(5.0)
    cover = roles.cover
    assert purpose[cover] == PURPOSES_CODE[RunPurpose.COVERING]
    line = roles.goal_side(1, engine.pos[carrier], P.COVER_DEPTH)
    spot = roles.cover_spot(1, carrier, cover)  # before team-mates' spacing moves it
    gap = engine.to_uv(1, spot) - engine.to_uv(1, line)
    assert abs(gap[1]) == pytest.approx(P.COVER_SIDE)
    assert abs(engine.to_uv(1, spot)[1]) < abs(engine.to_uv(1, line)[1])  # towards the middle
    presser = roles.pressers[0]
    other = cover
    d = np.hypot(*(engine.pos[presser] - engine.pos[carrier]))
    away = engine.pos[carrier] - engine.pos[other]
    away /= np.hypot(*away)
    engine.pos[other] = engine.pos[carrier] - away * max(d - 0.5 * P.ROLE_KEEP_M, 0.5)
    roles.targets(5.1)
    assert roles.pressers[0] == presser  # nearer, but not ROLE_KEEP_M nearer
    engine.pos[other] = engine.pos[carrier] - away * max(d - 1.5 * P.ROLE_KEEP_M, 0.2)
    roles.targets(5.2)
    assert roles.pressers[0] == other


def test_runners_keep_out_of_a_team_mates_lane():
    """Decision 46: a runner alongside a team-mate running the same way moves his target across,
    to RUN_SPACE from that lane (two defenders going back ran side by side 2 m apart)."""
    from runningbattery.sim.roles import Run

    engine = _engine()
    roles = engine.roles
    roles.clear()
    runner, mate = 2, 3
    engine.pos[:11] = np.array([-45.0, 30.0])  # the rest of his team well away
    engine.pos[:11, 1] -= np.arange(11) * 3.0
    engine.pos[runner], engine.pos[mate] = np.array([0.0, 0.0]), np.array([1.0, 2.0])
    engine.vel[:] = 0.0
    engine.vel[runner] = engine.vel[mate] = np.array([6.0, 0.0])
    tgt = engine.pos.copy()
    tgt[runner], tgt[mate] = np.array([25.0, 0.0]), np.array([30.0, 9.0])
    roles.runs[runner] = Run(RunPurpose.RECOVERY_RUN, 20.0, P.RECOVERY_EFFORT, target=tgt[runner])
    purpose = np.full(22, -1, dtype=np.int8)
    purpose[runner] = PURPOSES_CODE[RunPurpose.RECOVERY_RUN]
    out = roles.space_runs(tgt, np.zeros(22, dtype=bool), purpose)
    assert out[runner][1] == pytest.approx(2.0 - P.RUN_SPACE)  # out of his lane, away from him
    engine.vel[mate] = 0.0  # a team-mate standing aside is no lane to keep out of
    assert np.array_equal(roles.space_runs(tgt, np.zeros(22, dtype=bool), purpose), tgt)


def test_dead_balls_wait_only_for_a_cause():
    """Decision 46: no long stoppage without a cause (a goal kick had waited 94 s); a booking adds
    CARD_DELAY_S."""
    engine = _engine()
    spot = engine.pos[5].copy()
    waits = []
    for _ in range(400):
        engine.schedule_restart("goal_kick", 0, spot, 5.0, spot)
        waits.append(engine.restart.t - 5.0)
    median, sigma = P.DEAD_TIME["goal_kick"]
    assert max(waits) < median * P.DEAD_TIME_SCALE * np.exp(4.0 * sigma)  # 4 SD of the lognormal
    engine.free_kick(5.0, 0, spot, booked=True)
    assert engine.restart.t - 5.0 >= P.CARD_DELAY_S


def test_the_cover_runs_only_when_far_from_his_spot():
    """Decision 46: the cover defender's pace rises with his gap like a shape run's (at
    COVER_SPEED whatever the gap, he sprinted 1–2 s at every new carrier)."""
    engine = _engine()
    roles = engine.roles
    i = 13
    near = engine.pos[i] + [P.SHAPE_RUN_GAP - 5.0, 0.0]
    far = engine.pos[i] + [P.SHAPE_RUN_FULL + 5.0, 0.0]
    assert roles.cover_pace(i, near) == pytest.approx(P.SHAPE_RUN_MIN)
    assert roles.cover_pace(i, far) == pytest.approx(P.COVER_SPEED)


def test_the_team_that_lost_the_ball_counter_presses():
    """Decision 46: after a turnover in open play the nearest players of the team that lost it
    (COUNTERPRESS_N, within COUNTERPRESS_REACH) hunt the ball, whoever has it; not after a
    restart."""
    engine = _engine()
    roles = engine.roles
    P_old = P.COUNTERPRESS_CHANCE
    try:
        P.COUNTERPRESS_CHANCE = 1.0
        engine.ball_xy[:2] = engine.pos[13]  # an opponent of team 0 next to the ball
        roles.on_possession_change(0, 5.0, turnover=False)
        assert not any(r.hunt for r in roles.runs.values())
        roles.on_possession_change(0, 5.0, turnover=True)
        hunters = [i for i, r in roles.runs.items() if r.hunt]
        assert 1 <= len(hunters) <= P.COUNTERPRESS_N
        assert all(engine.team_of[i] == 1 for i in hunters)
        assert all(roles.runs[i].purpose == RunPurpose.CLOSE_DOWN for i in hunters)
        engine.start_touch(7, 5.2)  # the winners' next touch: the hunt goes on
        assert all(i in roles.runs for i in hunters)
    finally:
        P.COUNTERPRESS_CHANCE = P_old


def test_the_keeper_claims_a_high_ball_into_his_six_yard_box():
    """Decision 46: a high ball dropping into the six-yard box is the keeper's with
    GK_CLAIM_CHANCE (nobody claimed one: 14% of our shots came from inside 6 m, Wyscout's Premier
    League 3.7%)."""
    engine = _engine()
    old = P.GK_CLAIM_CHANCE
    try:
        P.GK_CLAIM_CHANCE = 1.0
        taker, target = 9, 10
        engine.pos[taker] = engine.to_uv(0, np.array([P.HALF_LENGTH - 1.0, P.HALF_WIDTH - 1.0]))
        engine.pos[target] = engine.to_uv(0, np.array([P.HALF_LENGTH - 2.0, 0.0]))
        engine.play_pass(5.0, taker, engine.pos[taker].copy(), restart="corner")
        f = engine.flight
        end_u = engine.to_uv(0, f.end)[0]
        if end_u > P.HALF_LENGTH - P.SIX_YARD_DEPTH and f.peak_z > 2.0:
            assert f.result == "intercepted" and f.to == int(engine.members(1)[0])
    finally:
        P.GK_CLAIM_CHANCE = old


def test_the_keeper_comes_out_to_a_carrier_through_on_goal():
    """Decision 46: a carrier within GK_RUSH_RANGE with a clear lane has the keeper come out to
    meet him (he stayed on his line and the carrier walked in)."""
    engine = _engine()
    roles = engine.roles
    carrier = 10
    for i in engine.members(1)[1:]:  # the defence far away: his lane is clear
        engine.pos[i] = engine.to_uv(0, np.array([-30.0, float(i) - 16.0]))
    engine.pos[carrier] = engine.to_uv(0, np.array([P.HALF_LENGTH - 14.0, 2.0]))
    engine.start_touch(carrier, 5.0)
    roles.clear()
    engine.follow_ball(5.0)
    tgt, _, _, _, _ = roles.targets(5.0)
    gk = int(engine.members(1)[0])
    assert np.hypot(*(tgt[gk] - engine.pos[carrier])) < P.GK_RUSH_GAP + 0.5


def test_opponents_do_not_press_or_crowd_a_keeper_on_the_ball():
    """Decision 47: when the goalkeeper holds the ball, opponents neither press nor cover him, and
    their shape spots stay outside his penalty area and at least 10 m in front of him (while
    shape_w decayed after a save, attackers' shape targets stayed inside the six-yard box)."""
    engine = _engine()
    roles = engine.roles
    gk = int(engine.members(0)[0])
    engine.pos[gk] = engine.to_uv(0, np.array([-P.HALF_LENGTH + 4.0, 0.0]))
    engine.shape_w[:] = [0.0, 1.0]  # team 1 still in full attacking shape after a shot
    engine.start_touch(gk, 5.0)
    roles.clear()
    engine.follow_ball(5.0)
    shape, _ = roles.shape()
    opp = engine.members(1)[1:]
    opp_u = engine.to_uv(1, shape[opp])[:, 0]
    gk_u = float(engine.to_uv(1, engine.pos[gk])[0])
    assert np.all(opp_u <= min(P.HALF_LENGTH - P.BOX_DEPTH, gk_u - 10.0) + 1e-6)
    _, _, purpose, _, _ = roles.targets(5.0)
    assert roles.pressers == [] and roles.cover == -1
    assert not np.any(purpose[opp] == PURPOSES_CODE[RunPurpose.CLOSE_DOWN])


def test_out_of_possession_upfield_shape_runs_do_not_sprint():
    """Decision 47: out of possession and not pressing, midfielders and forwards whose shape spot
    is upfield move into shape at no more than SHAPE_RUN_MIN (not sprinting away from the goal they
    defend)."""
    engine = _engine()
    roles = engine.roles
    roles.clear()
    engine.press = None
    shape, _ = roles.shape()
    cm = 16  # team 1 central midfielder, out of possession (holder == 0)
    engine.pos[cm] = shape[cm] - engine.to_uv(1, np.array([22.0, 0.0]))
    roles.start_shape_runs(5.0, shape, 0)
    assert cm in roles.runs and roles.runs[cm].speed == pytest.approx(P.SHAPE_RUN_MIN)


def test_cover_does_not_overwrite_a_second_presser_and_pressers_space_out():
    """Decision 47: when a second player closes the carrier down (counter-press or build-up press),
    the cover role goes to another team-mate instead of overwriting his CLOSE_DOWN run, and the
    two pressers' targets stand 3 m apart."""
    from runningbattery.sim.roles import Run

    engine = _engine()
    roles = engine.roles
    carrier = 7
    p1, p2, p3 = 16, 17, 15
    c_xy = engine.to_uv(0, np.array([0.0, 0.0]))
    engine.pos[carrier], engine.vel[carrier] = c_xy, 0.0
    for j in engine.members(1)[1:]:
        engine.pos[j] = engine.to_uv(1, np.array([-35.0, float(j) - 16.0]))
    engine.pos[p1] = c_xy + engine.to_uv(1, np.array([-4.0, -2.0]))
    engine.pos[p2] = c_xy + engine.to_uv(1, np.array([-6.0, 2.0]))
    engine.pos[p3] = c_xy + engine.to_uv(1, np.array([-9.0, 0.0]))
    engine.start_touch(carrier, 5.0)
    roles.clear()
    run = Run(RunPurpose.CLOSE_DOWN, 9.0, P.CHASE_SPEED)
    run.offset_uv = np.array([-P.PRESS_GAP, 0.0])
    run.hunt = True
    roles.runs[p2] = run
    tgt, _, purpose, _, _ = roles.targets(5.0)
    assert purpose[p1] == PURPOSES_CODE[RunPurpose.CLOSE_DOWN]
    assert purpose[p2] == PURPOSES_CODE[RunPurpose.CLOSE_DOWN]
    assert roles.cover == p3 and purpose[p3] == PURPOSES_CODE[RunPurpose.COVERING]
    assert np.hypot(*(tgt[p1] - tgt[p2])) == pytest.approx(3.0, abs=0.2)
