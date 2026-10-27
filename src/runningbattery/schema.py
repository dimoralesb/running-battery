"""Data contract for one Running Battery match.

A match is four files in one folder:

- ``tracking.jsonl``: one :class:`TrackingFrame` per line, 10 Hz.
- ``events.jsonl``: one :class:`Event` per line.
- ``metadata.json``: :class:`MatchMetadata`.
- ``truth.json``: :class:`MatchTruth`. Validation only; the estimator never reads it.

The estimator (``runningbattery.engine``) writes a fifth file, ``signals.json``
(:class:`MatchSignals`), for the agents and the app.

Units: metres, seconds, m/s, m/s². Coordinates have their origin at the centre spot, x along the
length (±52.5 m) and y along the width (±34 m). Which team attacks +x is in the metadata.

Run ``python -m runningbattery.schema`` to export the JSON Schemas to ``schemas/``.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# 0.1.3: truth.json gets ``settings`` (the generator assumptions used for each match); tracking
# frames document dropouts (a player left out of ``players``).
# 0.1.4: ``tired`` is short-term tiredness only (late-match fatigue is the ``tank`` below
# ``settings["late_tank_below"]``); skipped runs are one per situation and only those forecast to
# have been high-intensity runs.
# 0.1.5: substitutions: substitutes in ``players`` (``starter`` false) and in ``substitutions``;
# a player's truth series covers only their time on the pitch.
# 0.1.6: ``signals.json``, the estimator's output (per player, per second on the pitch).
# 0.1.7: ``signals.json`` records the typical-player prior (``engine.prior``).
# 0.1.8: ``signals.json`` gets ``low_chance``, the typical-pro chance of a low battery (decision
# 14); the default prior is ``pro``, the generator's population.
# 0.1.9: ``low_chance`` is calibrated (a monotone map fitted on the dev seeds,
# ``engine/params.py`` LOW_CHANCE_MAP); the raw share of the draws is kept as ``low_chance_raw``,
# and ``engine.low_chance_map`` names the map (null: no map, the two are the same).
SCHEMA_VERSION = "0.1.9"

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
    """Position codes as in Allen2024."""

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
    """Phase of play, from the viewpoint of the event's team.

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
    """One on-ball or match event, SPADL / StatsBomb-like."""

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
    """Club fitness-test values: the truth plus measurement error.

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
    name: str = "runningbattery.sim"
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

    def slot_of(self) -> dict[str, int]:
        """Each player's slot 0–21 (home starters in order, then away): a substitute takes the
        slot of the player replaced."""
        starters = [p for team in self.teams for p in team.players if p.starter]
        slot = {p.id: k for k, p in enumerate(starters)}
        for sub in sorted(self.substitutions, key=lambda s: (s.period, s.t)):
            slot[sub.player_in] = slot[sub.player_out]
        return slot

    @model_validator(mode="after")
    def _unique_ids(self) -> MatchMetadata:
        ids = [p.id for team in self.teams for p in team.players]
        if len(ids) != len(set(ids)):
            raise ValueError("player ids must be unique across both teams")
        if {team.side for team in self.teams} != {"home", "away"}:
            raise ValueError("need one home team and one away team")
        team_of = {p.id: team.id for team in self.teams for p in team.players}
        starter = {p.id: p.starter for team in self.teams for p in team.players}
        if any(sum(p.starter for p in team.players) != 11 for team in self.teams):
            raise ValueError("each team needs 11 starters")
        for sub in self.substitutions:
            out_team, in_team = team_of.get(sub.player_out), team_of.get(sub.player_in)
            if not out_team == in_team == sub.team_id or starter[sub.player_in]:
                raise ValueError(f"bad substitution {sub.player_out} -> {sub.player_in}")
        return self


# --- truth.json ---------------------------------------------------------------------------------


class TrueParams(_Model):
    """Hidden physiology of one player."""

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
    tired: list[bool] = Field(
        description="Tired moment: the two pools alone cut the chance of a hard run by at least "
        "a quarter (settings tired_below). Late-match fatigue is tank below "
        "settings late_tank_below"
    )

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
    """A high-intensity run with its intended purpose. ``executed=True``: measured in the
    tracking (above 5.5 m/s for at least 1 s). ``executed=False``: a run a tired player skipped,
    one per situation, forecast to have been a high-intensity run had it been made."""

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
        description="Generator assumptions used for this match (position noise, tempo, fatigue "
        "effect sizes), so validation can report results across them",
    )
    players: list[PlayerTruth]
    runs: list[RunTruth] = []


# --- signals.json (the estimator's output) ------------------------------------------------------

Share = Annotated[float, Field(ge=0, le=1)]


class EngineSettings(_Model):
    """How the signals were made (values and sources in ``engine/params.py``)."""

    mode: Literal["broadcast", "club"] = Field(
        description="broadcast: shared prior only; club: club test values (validation only)"
    )
    prior: str = Field(
        description="Typical player: pro (professional players, the generator's population) or "
        "university (sensitivity); engine/params.py PRIORS"
    )
    update: Literal["draws", "correction"] = Field(
        description="draws: per-player update of CS and D′ from prior draws; "
        "correction: one value with the one-way D′ correction only (club mode, fallback)"
    )
    k: Annotated[float, Field(gt=0, description="Battery recharge factor, τ = k·D′/(CS − v)")]
    n_draws: Annotated[int, Field(ge=1)]
    penalty_width: Annotated[float, Field(gt=0)]
    low_battery: Share = Field(description="Tired: median battery below this share of D′")
    peak_share: Share
    peak_floor: Annotated[float, Field(ge=0)]
    hi_speed: Annotated[float, Field(gt=0, description="High-speed running threshold, m/s")]
    low_chance_map: str | None = Field(
        default=None,
        description="The calibration map applied to low_chance (where and when it was fitted); "
        "null when none fits these settings and low_chance is the raw share of the draws",
    )


class Range(_Model):
    """An estimate with its 10–90% band (lo = hi = value when there is no band)."""

    value: float
    lo: float
    hi: float


class Capacity(_Model):
    """Estimated CS (m/s) and D′ (m) at the end of the player's match: weighted over the draws
    in broadcast mode, after the one-way correction."""

    cs: Range
    d_prime: Range


class SignalSeries(_Model):
    """1 Hz series over the player's time on the pitch; all lists have the same length.

    Battery: share of the player's estimated D′ left, a relative gauge only (never "empty").
    Load: metabolic power, W/kg; energy since kick-off, kJ/kg. Recent intensity: metres above
    ``hi_speed`` in the last 1, 2 and 5 min, and the same as a share of the player's reference
    peak; windows stay inside a period. ``in_play_*``: share of that window with the ball in play.
    """

    period: list[Period]
    t: list[Seconds]
    speed: list[Annotated[float, Field(ge=0)]] = Field(description="Mean over the last second")
    battery: list[Share]
    battery_lo: list[Share] | None = Field(default=None, description="10% band; broadcast mode")
    battery_hi: list[Share] | None = None
    low_chance: list[Share] | None = Field(
        default=None,
        description="Chance that a typical player of the prior's population (a typical "
        "professional by default) would be short-term tired after this running (broadcast "
        "mode): low_chance_raw through the calibration map named in engine.low_chance_map. "
        "About the running, not this player's own state",
    )
    low_chance_raw: list[Share] | None = Field(
        default=None,
        description="The weighted share of the prior draws with a battery below low_battery, "
        "before calibration",
    )
    power: list[Annotated[float, Field(ge=0)]] = Field(description="Mean over the last second")
    power_1min: list[Annotated[float, Field(ge=0)]]
    power_5min: list[Annotated[float, Field(ge=0)]]
    energy: list[Annotated[float, Field(ge=0)]]
    hsr_1min: list[Annotated[float, Field(ge=0)]]
    hsr_2min: list[Annotated[float, Field(ge=0)]]
    hsr_5min: list[Annotated[float, Field(ge=0)]]
    hsr_1min_vs_peak: list[Annotated[float, Field(ge=0)]]
    hsr_2min_vs_peak: list[Annotated[float, Field(ge=0)]]
    hsr_5min_vs_peak: list[Annotated[float, Field(ge=0)]]
    in_play_1min: list[Share]
    in_play_5min: list[Share]
    red_zone: list[bool] = Field(description="In a 1-, 2- or 5-min red-zone (peak) spell")
    post_peak: list[bool] = Field(
        description="In a red-zone spell or the minutes after one; neutral wording only "
        '("catching breath"), never "tired"'
    )
    tired: list[bool] = Field(description="Tired moment: battery below low_battery")

    @model_validator(mode="after")
    def _same_length(self) -> SignalSeries:
        lengths = {
            name: len(v)
            for name in type(self).model_fields
            if (v := getattr(self, name)) is not None
        }
        if len(set(lengths.values())) > 1:
            raise ValueError(f"signal series lengths differ: {lengths}")
        return self


class PlayerSignals(_Model):
    player_id: str
    team_id: str
    position: Position
    starter: bool
    capacity: Capacity
    series: SignalSeries


class TiredSpell(_Model):
    """A run of tired seconds for one player, with the events that fall inside it: the
    player's defensive actions and ball losses."""

    player_id: str
    period: Period
    t_start: Seconds
    t_end: Seconds
    post_peak: bool = Field(description="The spell overlaps a post-peak window (context only)")
    battery_min: Share
    event_ids: list[int] = []


class MatchSignals(_Model):
    schema_version: str = SCHEMA_VERSION
    match_id: str
    engine: EngineSettings
    players: list[PlayerSignals]
    tired_spells: list[TiredSpell] = []


# --- JSON Schema export -------------------------------------------------------------------------

EXPORTS: dict[str, type[BaseModel]] = {
    "tracking_frame": TrackingFrame,
    "event": Event,
    "metadata": MatchMetadata,
    "truth": MatchTruth,
    "signals": MatchSignals,
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
