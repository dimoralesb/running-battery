import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from secondwind.io import read_match, read_truth, write_match
from secondwind.schema import (
    Ball,
    ClubTestValues,
    Event,
    Generator,
    MatchMetadata,
    MatchTruth,
    PeriodInfo,
    PlayerInfo,
    PlayerPosition,
    PlayerTruth,
    Point,
    RunTruth,
    Score,
    TeamInfo,
    TrackingFrame,
    TrueParams,
    TruthSeries,
    json_schemas,
)

ROOT = Path(__file__).resolve().parents[1]
POSITIONS = ["GK", "CB", "CB", "FB", "FB", "DM", "CM", "AM", "WM", "WM", "CF"]
TEST_VALUES = ClubTestValues(cs=3.7, d_prime=180, a0=7.4, s0=9.3)


def team(side: str) -> TeamInfo:
    players = [
        PlayerInfo(
            id=f"{side[0].upper()}{i:02d}",
            name=f"Player {side} {i}",
            shirt=i,
            position=pos,
            starter=True,
            test_values=None if pos == "GK" else TEST_VALUES,
        )
        for i, pos in enumerate(POSITIONS, start=1)
    ]
    return TeamInfo(
        id=side,
        name=f"FC {side.title()}",
        side=side,
        formation="4-2-3-1",
        attacks_positive_x_in_period_1=side == "home",
        players=players,
    )


def metadata() -> MatchMetadata:
    return MatchMetadata(
        match_id="m0001",
        generator=Generator(version="0.1.0", seed=1),
        periods=[PeriodInfo(period=1, start_frame=0, end_frame=1, duration_s=0.2)],
        teams=[team("home"), team("away")],
    )


def frame(n: int) -> TrackingFrame:
    return TrackingFrame(
        frame=n,
        period=1,
        t=n / 10,
        clock=n / 10,
        ball_status="alive",
        possession_team="home",
        ball=Ball(x=0, y=0, z=0),
        players=[PlayerPosition(id="H01", x=-50, y=0), PlayerPosition(id="A01", x=50, y=0)],
    )


def event(**overrides) -> Event:
    fields = dict(
        id=0,
        period=1,
        t=0.0,
        clock=0.0,
        type="pass",
        subtype="kick_off",
        player_id="H07",
        team_id="home",
        start=Point(x=0, y=0),
        end=Point(x=-10, y=5),
        outcome="success",
        height="ground",
        phase="build_up",
        score=Score(home=0, away=0),
    )
    return Event(**(fields | overrides))


def truth() -> MatchTruth:
    series = TruthSeries(
        period=[1, 1],
        t=[0.0, 1.0],
        fast_pool=[1.0, 0.9],
        slow_pool=[1.0, 1.0],
        tank=[1.0, 1.0],
        speed_mult=[1.0, 1.0],
        accel_mult=[1.0, 1.0],
        run_choice_mult=[1.0, 0.95],
        tired=[False, False],
    )
    params = TrueParams(
        cs=3.7, d_prime=180, a0=7.4, s0=9.3, fast_fraction=0.45, tau_fast=25, tau_slow=450
    )
    run = RunTruth(
        run_id=0,
        player_id="H04",
        period=1,
        t_start=0.0,
        t_end=0.0,
        purpose="recovery_run",
        executed=False,
    )
    return MatchTruth(
        match_id="m0001",
        fatigue_enabled=True,
        players=[PlayerTruth(player_id="H04", params=params, series=series)],
        runs=[run],
    )


def test_match_round_trip(tmp_path):
    events = [event(), event(id=1, type="carry", subtype=None, height=None, end_t=1.5)]
    write_match(tmp_path, metadata(), [frame(0), frame(1)], events, truth())

    match = read_match(tmp_path)
    assert match.metadata == metadata()
    assert [f.frame for f in match.frames] == [0, 1]
    assert match.events == events
    assert read_truth(tmp_path) == truth()


@pytest.mark.parametrize(
    "overrides",
    [
        {"xg": 0.1},  # xg on a pass
        {"type": "shot", "height": "ground"},  # height on a shot
        {"end_t": -1.0},
        {"type": "carry", "end": None, "height": None},  # carry without an end point
        {"start": {"x": 70, "y": 0}},  # off the pitch
        {"phase": "counter_attack"},  # unknown phase
        {"speed": 7.0},  # unknown field
    ],
)
def test_invalid_events_rejected(overrides):
    with pytest.raises(ValidationError):
        event(**overrides)


def test_contested_frame_round_trip(tmp_path):
    """possession_team=None is left out on write (exclude_none) and must read back as None."""
    contested = frame(0).model_copy(update={"possession_team": None})
    write_match(tmp_path, metadata(), [contested], [event()])
    assert read_match(tmp_path).frames == [contested]


def test_duplicate_player_in_frame_rejected():
    players = [{"id": "H01", "x": 0, "y": 0}, {"id": "H01", "x": 1, "y": 0}]
    with pytest.raises(ValidationError, match="duplicate player id"):
        TrackingFrame.model_validate(frame(0).model_dump() | {"players": players})


def test_truth_series_lengths_must_match():
    with pytest.raises(ValidationError, match="lengths differ"):
        TruthSeries(
            period=[1],
            t=[0.0, 1.0],
            fast_pool=[1.0],
            slow_pool=[1.0],
            tank=[1.0],
            speed_mult=[1.0],
            accel_mult=[1.0],
            run_choice_mult=[1.0],
            tired=[False],
        )


def test_duplicate_player_ids_across_teams_rejected():
    home = team("home")
    away = team("away").model_copy(update={"players": home.players})
    with pytest.raises(ValidationError, match="unique"):
        MatchMetadata.model_validate(
            metadata().model_dump() | {"teams": [home.model_dump(), away.model_dump()]}
        )


def test_exported_json_schemas_are_up_to_date():
    for name, schema in json_schemas().items():
        path = ROOT / "schemas" / f"{name}.schema.json"
        assert json.loads(path.read_text()) == schema, (
            f"{path.name} is stale: run `uv run python -m secondwind.schema`"
        )
