"""Run one seeded match and turn the engine's arrays and event log into the four files."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from secondwind import __version__
from secondwind.io import write_match
from secondwind.schema import (
    Ball,
    BallStatus,
    Event,
    Generator,
    MatchMetadata,
    MatchTruth,
    PeriodInfo,
    PlayerPosition,
    PlayerTruth,
    Point,
    Score,
    TrackingFrame,
    TruthSeries,
)
from secondwind.sim import params as P
from secondwind.sim.match import MatchEngine, PeriodFrames
from secondwind.sim.rosters import SimTeam, make_teams

PERIOD_2_CLOCK = 2700.0  # schema: period 2 starts at 45:00 on the match clock


@dataclass(frozen=True)
class SimMatch:
    metadata: MatchMetadata
    periods: list[PeriodFrames]
    events: list[Event]
    truth: MatchTruth


def period_lengths(rng: np.random.Generator) -> list[int]:
    """Frames in each half. Total 99.5 ± 2.9 min [Allen2025, Table 2]; split is our assumption."""
    lo = P.MATCH_MINUTES_MEAN - P.MATCH_MINUTES_CLIP_SD * P.MATCH_MINUTES_SD
    hi = P.MATCH_MINUTES_MEAN + P.MATCH_MINUTES_CLIP_SD * P.MATCH_MINUTES_SD
    total_s = 60.0 * float(np.clip(rng.normal(P.MATCH_MINUTES_MEAN, P.MATCH_MINUTES_SD), lo, hi))
    added_s = total_s - 2 * PERIOD_2_CLOCK
    first_s = PERIOD_2_CLOCK + rng.uniform(*P.FIRST_HALF_ADDED_SHARE) * added_s
    return [round(first_s * P.FRAME_RATE_HZ), round((total_s - first_s) * P.FRAME_RATE_HZ)]


def simulate(seed: int, match_id: str, club_tests: bool = False) -> SimMatch:
    """One match. Club test values go into the metadata only if ``club_tests`` is set; the
    match itself is the same either way."""
    rng = np.random.default_rng(seed)
    teams = make_teams(rng)
    lengths = period_lengths(rng)
    first_kick = int(rng.integers(2))
    engine = MatchEngine(rng, teams)
    periods = [
        engine.run_period(1, lengths[0], first_kick),
        engine.run_period(2, lengths[1], 1 - first_kick),
    ]
    infos, start = [], 0
    for pf in periods:
        n = len(pf.alive)
        infos.append(
            PeriodInfo(
                period=pf.period,
                start_frame=start,
                end_frame=start + n - 1,
                duration_s=n / P.FRAME_RATE_HZ,
            )
        )
        start += n
    metadata = MatchMetadata(
        match_id=match_id,
        generator=Generator(version=__version__, seed=seed),
        frame_rate_hz=P.FRAME_RATE_HZ,
        periods=infos,
        teams=[team.info(club_tests) for team in teams],
    )
    return SimMatch(metadata, periods, to_events(engine), neutral_truth(match_id, teams, periods))


def to_events(engine: MatchEngine) -> list[Event]:
    ids, team_ids = engine.ids, [team.id for team in engine.teams]
    rows = sorted(engine.events, key=lambda e: (e["period"], e["t"], e["seq"]))
    events = []
    for n, e in enumerate(rows):
        clock = e["t"] + (PERIOD_2_CLOCK if e["period"] == 2 else 0.0)
        related = e.get("related_player_id")
        events.append(
            Event(
                id=n,
                period=e["period"],
                t=e["t"],
                clock=round(clock, 1),
                type=e["type"],
                subtype=None if e.get("subtype") is None else str(e["subtype"]),
                player_id=ids[e["player"]] if e["player"] >= 0 else None,
                team_id=None if e["team"] is None else team_ids[e["team"]],
                related_player_id=None if related is None else ids[related],
                start=Point(x=e["start"][0], y=e["start"][1]) if "start" in e else None,
                end=Point(x=e["end"][0], y=e["end"][1]) if "end" in e else None,
                end_t=e.get("end_t"),
                outcome=e.get("outcome"),
                body_part=e.get("body_part"),
                height=e.get("height"),
                xg=e.get("xg"),
                possession_id=e.get("possession_id"),
                phase=e.get("phase"),
                score=Score(home=e["score"][0], away=e["score"][1]),
            )
        )
    return events


def neutral_truth(match_id: str, teams: list[SimTeam], periods: list[PeriodFrames]) -> MatchTruth:
    """Valid but flat truth: fatigue off, full pools and tank, all multipliers 1 (Saturday)."""
    period, t = [], []
    for pf in periods:
        seconds = (len(pf.alive) - 1) // round(P.FRAME_RATE_HZ) + 1
        period += [pf.period] * seconds
        t += [float(s) for s in range(seconds)]
    n = len(t)
    series = TruthSeries(
        period=period,
        t=t,
        fast_pool=[1.0] * n,
        slow_pool=[1.0] * n,
        tank=[1.0] * n,
        speed_mult=[1.0] * n,
        accel_mult=[1.0] * n,
        run_choice_mult=[1.0] * n,
        tired=[False] * n,
    )
    players = [
        PlayerTruth(player_id=p.id, params=p.params, series=series)
        for team in teams
        for p in team.players
    ]
    return MatchTruth(match_id=match_id, fatigue_enabled=False, players=players)


def tracking_frames(match: SimMatch) -> Iterator[TrackingFrame]:
    """Frames built without per-row validation (fast); tests validate them on read."""
    ids = [p.id for team in match.metadata.teams for p in team.players]
    team_ids = [team.id for team in match.metadata.teams]
    frame = 0
    for pf in match.periods:
        clock0 = PERIOD_2_CLOCK if pf.period == 2 else 0.0
        pos = (np.round(pf.pos, 2) + 0.0).tolist()
        ball = (np.round(pf.ball, 2) + 0.0).tolist()
        for k in range(len(pf.alive)):
            t = round(k / P.FRAME_RATE_HZ, 1)
            holder = int(pf.possession[k])
            yield TrackingFrame.model_construct(
                frame=frame,
                period=pf.period,
                t=t,
                clock=round(clock0 + t, 1),
                ball_status=BallStatus.ALIVE if pf.alive[k] else BallStatus.DEAD,
                possession_team=None if holder < 0 else team_ids[holder],
                ball=Ball.model_construct(x=ball[k][0], y=ball[k][1], z=ball[k][2]),
                players=[
                    PlayerPosition.model_construct(id=pid, x=xy[0], y=xy[1])
                    for pid, xy in zip(ids, pos[k], strict=True)
                ],
            )
            frame += 1


def write(match: SimMatch, folder: Path) -> None:
    write_match(folder, match.metadata, tracking_frames(match), match.events, match.truth)


def generate(
    seed: int, folder: Path, match_id: str | None = None, club_tests: bool = False
) -> SimMatch:
    """Simulate one match and write its four files to ``folder`` (match id: folder name)."""
    match = simulate(seed, match_id or folder.name, club_tests)
    write(match, folder)
    return match
