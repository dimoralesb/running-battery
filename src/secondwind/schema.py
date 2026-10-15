"""Data contract for one Second Wind match (PLAN §2.3; RESEARCH_SYNTHESIS §7).

A match is four files in one folder:

- ``tracking.jsonl``: one :class:`TrackingFrame` per line, 10 Hz.
- ``events.jsonl``: one :class:`Event` per line.
- ``metadata.json``: :class:`MatchMetadata`.
- ``truth.json``: :class:`MatchTruth`. Validation only; the estimator never reads it.

Units: metres, seconds, m/s, m/s². Coordinates have their origin at the centre spot, x along the
length (±52.5 m) and y along the width (±34 m). Which team attacks +x is in the metadata.

Run ``python -m secondwind.schema`` to export the JSON Schemas to ``schemas/``.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# 0.1.3: truth.json gets ``settings`` (the generator assumptions used for each match, PLAN §2.6
# point 3); tracking frames document dropouts (a player left out of ``players``).
SCHEMA_VERSION = "0.1.3"

# A little beyond the 52.5 x 34 m half-pitch, for players and the ball just outside the lines.
X_LIMIT = 60.0
Y_LIMIT = 40.0

X = Annotated[float, Field(ge=-X_LIMIT, le=X_LIMIT)]
Y = Annotated[float, Field(ge=-Y_LIMIT, le=Y_LIMIT)]
Seconds = Annotated[float, Field(ge=0)]
Fraction = Annotated[float, Field(ge=0, le=1)]
Period = Literal[1, 2]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- Shared enums -------------------------------------------------------------------------------


class Position(StrEnum):
    """Position codes as in Allen2024 (synthesis §4.2)."""

    GK = "GK"
    CB = "CB"
    FB = "FB"
    DM = "DM"
    CM = "CM"
    AM = "AM"
    WM = "WM"
    CF = "CF"


class BallStatus(StrEnum):
    ALIVE = "alive"
    DEAD = "dead"


class Phase(StrEnum):
    """Phase of play, from the viewpoint of the event's team (synthesis §7.2).

    ``positive_transition`` / ``negative_transition`` are the first seconds after winning / losing
    the ball [Bortnik2022]. ``high_press`` and ``defensive_block`` are out-of-possession phases.
    """

    BUILD_UP = "build_up"
    PROGRESSION = "progression"
    FINAL_THIRD = "final_third"
    POSITIVE_TRANSITION = "positive_transition"
    NEGATIVE_TRANSITION = "negative_transition"
    HIGH_PRESS = "high_press"
    DEFENSIVE_BLOCK = "defensive_block"
    SET_PIECE = "set_piece"


class EventType(StrEnum):
    PASS = "pass"  # restarts (throw-in, corner, free kick, goal kick, kick-off) are pass subtypes
    CARRY = "carry"
    RECEPTION = "reception"
    SHOT = "shot"
    DUEL = "duel"
    TACKLE = "tackle"
    INTERCEPTION = "interception"
    PRESSURE = "pressure"
    BALL_RECOVERY = "ball_recovery"
    BALL_LOSS = "ball_loss"
    CLEARANCE = "clearance"
    FOUL = "foul"
    OFFSIDE = "offside"  # player_id is the offside player; an indirect free kick follows
    BALL_OUT = "ball_out"
    GOAL = "goal"
    CARD = "card"
    SUBSTITUTION = "substitution"
    PERIOD_START = "period_start"
    PERIOD_END = "period_end"


class Outcome(StrEnum):
    SUCCESS = "success"
    FAIL = "fail"


class BodyPart(StrEnum):
    FOOT = "foot"
    HEAD = "head"
    OTHER = "other"


class PassHeight(StrEnum):
    GROUND = "ground"
    LOW = "low"
    HIGH = "high"


class RunPurpose(StrEnum):
    """Intended purpose of a high-intensity run: the 12 categories in Ju2022."""

    PUSH_UP_PITCH = "push_up_pitch"
    BREAK_INTO_BOX = "break_into_box"
    RUN_IN_BEHIND = "run_in_behind"
    OVER_UNDERLAP = "over_underlap"
    RUN_WITH_BALL = "run_with_ball"
    MOVE_TO_RECEIVE = "move_to_receive"
    SUPPORT_PLAY = "support_play"
    INTERCEPTION = "interception"
    RECOVERY_RUN = "recovery_run"
    COVERING = "covering"
    CLOSE_DOWN = "close_down"
    OTHER = "other"


# --- tracking.jsonl -----------------------------------------------------------------------------


class Point(_Model):
    x: X
    y: Y


class Ball(_Model):
    x: X
    y: Y
    z: Annotated[float, Field(ge=0, le=50)]


class PlayerPosition(_Model):
    id: str
    x: X
    y: Y


class TrackingFrame(_Model):
    """One 10 Hz frame. Speeds are not stored: the estimator derives them from positions."""

    frame: Annotated[int, Field(ge=0)]
    period: Period
    t: Seconds = Field(description="Seconds since this period's kick-off")
    clock: Seconds = Field(description="Match clock in seconds; period 2 starts at 2700")
    ball_status: BallStatus
    possession_team: str | None = Field(
        default=None, description="Team in possession; null (or left out) when contested"
    )
    ball: Ball
    players: list[PlayerPosition] = Field(
        max_length=22,
        description="Players seen in this frame; a player left out is a tracking dropout",
    )

    @model_validator(mode="after")
    def _unique_players(self) -> TrackingFrame:
        ids = [p.id for p in self.players]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate player id in frame {self.frame}")
        return self


# --- events.jsonl -------------------------------------------------------------------------------


class Score(_Model):
    home: Annotated[int, Field(ge=0)]
    away: Annotated[int, Field(ge=0)]


class Event(_Model):
    """One on-ball or match event, SPADL / StatsBomb-like (synthesis §7.2)."""

    id: Annotated[int, Field(ge=0)]
    period: Period
    t: Seconds = Field(description="Seconds since this period's kick-off")
    clock: Seconds
    type: EventType
    subtype: str | None = Field(
        default=None, description="e.g. throw_in, corner, free_kick, goal_kick, cross, yellow"
    )
    player_id: str | None = None
    team_id: str | None = None
    related_player_id: str | None = Field(
        default=None, description="Pass receiver, duel opponent, or player coming on"
    )
    start: Point | None = None
    end: Point | None = None
    end_t: Seconds | None = Field(
        default=None, description="End time of a carry, or arrival time of a pass"
    )
    outcome: Outcome | None = None
    body_part: BodyPart | None = None
    height: PassHeight | None = None
    xg: Fraction | None = None
    possession_id: Annotated[int, Field(ge=0)] | None = None
    phase: Phase | None = None
    score: Score = Field(description="Score before this event")

    @model_validator(mode="after")
    def _consistent(self) -> Event:
        if self.xg is not None and self.type != EventType.SHOT:
            raise ValueError("xg is only allowed on shots")
        if self.height is not None and self.type != EventType.PASS:
            raise ValueError("height is only allowed on passes")
        if self.end_t is not None and self.end_t < self.t:
            raise ValueError("end_t must not be before t")
        if self.type == EventType.CARRY and (self.start is None or self.end is None):
            raise ValueError("a carry needs start and end, to compute carry speed [Fang2024]")
        return self


# --- metadata.json ------------------------------------------------------------------------------


class ClubTestValues(_Model):
    """Club fitness-test values: the truth plus measurement error (PLAN §3.2).

    Broadcasters never have these, so the generator leaves them out unless asked
    (``--club-tests``). They exist for one validation experiment: how much club data would help.
    """

    cs: Annotated[float, Field(gt=1.5, lt=6.0, description="Critical speed, m/s")]
    d_prime: Annotated[float, Field(gt=20, lt=600, description="D′, m")]
    a0: Annotated[float, Field(gt=3, lt=12, description="Max acceleration at 0 m/s, m/s²")]
    s0: Annotated[float, Field(gt=6, lt=12, description="Theoretical top speed, m/s")]


class PlayerInfo(_Model):
    id: str
    name: str
    shirt: Annotated[int, Field(ge=1, le=99)]
    position: Position
    starter: bool
    test_values: ClubTestValues | None = Field(default=None, description="null for goalkeepers")


class TeamInfo(_Model):
    id: str
    name: str
    side: Literal["home", "away"]
    formation: str
    attacks_positive_x_in_period_1: bool
    players: list[PlayerInfo] = Field(min_length=11)


class PeriodInfo(_Model):
    period: Period
    start_frame: Annotated[int, Field(ge=0)]
    end_frame: Annotated[int, Field(ge=0)]
    duration_s: Annotated[float, Field(gt=0)]


class Substitution(_Model):
    period: Period
    t: Seconds
    team_id: str
    player_out: str
    player_in: str


class Pitch(_Model):
    length: float = 105.0
    width: float = 68.0


class Generator(_Model):
    name: str = "secondwind.sim"
    version: str
    seed: int


class MatchMetadata(_Model):
    schema_version: str = SCHEMA_VERSION
    match_id: str
    generator: Generator
    pitch: Pitch = Pitch()
    frame_rate_hz: float = 10.0
    periods: list[PeriodInfo] = Field(min_length=1, max_length=2)
    teams: list[TeamInfo] = Field(min_length=2, max_length=2)
    substitutions: list[Substitution] = []

    @model_validator(mode="after")
    def _unique_ids(self) -> MatchMetadata:
        ids = [p.id for team in self.teams for p in team.players]
        if len(ids) != len(set(ids)):
            raise ValueError("player ids must be unique across both teams")
        if {team.side for team in self.teams} != {"home", "away"}:
            raise ValueError("need one home team and one away team")
        return self


# --- truth.json ---------------------------------------------------------------------------------


class TrueParams(_Model):
    """Hidden physiology of one player (synthesis §3.2.3–3.2.4)."""

    cs: Annotated[float, Field(gt=0)]
    d_prime: Annotated[float, Field(gt=0)]
    a0: Annotated[float, Field(gt=0)]
    s0: Annotated[float, Field(gt=0)]
    fast_fraction: Fraction = Field(description="Share of D′ in the fast pool")
    tau_fast: Annotated[float, Field(gt=0, description="Fast-pool recharge time at rest, s")]
    tau_slow: Annotated[float, Field(gt=0, description="Slow-pool recharge time at rest, s")]


class TruthSeries(_Model):
    """1 Hz series. All lists have the same length. Pools and tank are fractions of full."""

    period: list[Period]
    t: list[Seconds]
    fast_pool: list[Fraction]
    slow_pool: list[Fraction]
    tank: list[Fraction]
    speed_mult: list[Fraction] = Field(description="Multiplier on top speed (loss capped ~5%)")
    accel_mult: list[Fraction]
    run_choice_mult: list[Fraction] = Field(description="Multiplier on choosing a hard run")
    tired: list[bool]

    @model_validator(mode="after")
    def _same_length(self) -> TruthSeries:
        lengths = {name: len(getattr(self, name)) for name in type(self).model_fields}
        if len(set(lengths.values())) != 1:
            raise ValueError(f"truth series lengths differ: {lengths}")
        return self


class PlayerTruth(_Model):
    player_id: str
    params: TrueParams
    series: TruthSeries


class RunTruth(_Model):
    """A high-intensity run the player intended. ``executed=False`` marks a skipped run."""

    run_id: Annotated[int, Field(ge=0)]
    player_id: str
    period: Period
    t_start: Seconds
    t_end: Seconds
    purpose: RunPurpose
    executed: bool

    @model_validator(mode="after")
    def _ordered(self) -> RunTruth:
        if self.t_end < self.t_start:
            raise ValueError("t_end must not be before t_start")
        return self


class MatchTruth(_Model):
    schema_version: str = SCHEMA_VERSION
    match_id: str
    fatigue_enabled: bool = Field(description="False for no-fatigue control matches")
    story: dict[str, str | float | int | bool] = {}
    settings: dict[str, str | float | int | bool] = Field(
        default={},
        description="Generator assumptions used for this match (position noise now; fatigue "
        "effect sizes later), so validation can report results across them (PLAN §2.6)",
    )
    players: list[PlayerTruth]
    runs: list[RunTruth] = []


# --- JSON Schema export -------------------------------------------------------------------------

EXPORTS: dict[str, type[BaseModel]] = {
    "tracking_frame": TrackingFrame,
    "event": Event,
    "metadata": MatchMetadata,
    "truth": MatchTruth,
}


def json_schemas() -> dict[str, dict]:
    return {name: model.model_json_schema() for name, model in EXPORTS.items()}


def export_json_schemas(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, schema in json_schemas().items():
        path = out_dir / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
        paths.append(path)
    return paths


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    for p in export_json_schemas(root / "schemas"):
        print(p.relative_to(root))
