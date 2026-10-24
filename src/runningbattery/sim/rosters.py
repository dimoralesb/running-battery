"""Two fictional teams: names, line-ups, hidden true values and club test values.

Club and player names are built from invented place names and syllables. They are meant to
sound plausible, not to match any real club or player (none were checked against real squads).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

import numpy as np

from runningbattery.schema import ClubTestValues, PlayerInfo, Position, TeamInfo, TrueParams
from runningbattery.sim import params as P

PLACES = [
    "Fellhaven",
    "Brackenmoor",
    "Corrowdale",
    "Westerlyn",
    "Saltmere",
    "Ravensholt",
    "Kelderby",
    "Aldermoor",
    "Thistlewick",
    "Glenmarsh",
]
SUFFIXES = ["Athletic", "Rovers", "Wanderers", "Town", "Albion", "Harriers"]
FIRST_NAMES = [
    "Adam", "Ben", "Callum", "Dario", "Eli", "Felix", "Gabriel", "Hugo", "Ivan", "Jonah",
    "Kofi", "Luca", "Marco", "Nico", "Oscar", "Pablo", "Rafael", "Sami", "Theo", "Yusuf",
]  # fmt: skip
SURNAME_START = [
    "Ash", "Brem", "Cad", "Dorr", "Elm", "Fenn", "Gald", "Hask", "Ivel", "Jorr", "Kest",
    "Lanv", "Morr", "Orv", "Pell", "Rask", "Sorr", "Tarv", "Varr", "Wend", "Yarr",
]  # fmt: skip
SURNAME_END = [
    "away", "bury", "cott", "dane", "enby", "holm", "ick", "lowe", "mere", "nell", "ock",
    "rigg", "sall", "ver", "wick",
]  # fmt: skip


@dataclass(frozen=True)
class SimPlayer:
    id: str
    name: str
    shirt: int
    position: Position
    slot: tuple[float, float]  # (u, v) in the team's attacking frame, see params.FORMATION_4231
    params: TrueParams
    test_values: ClubTestValues | None
    starter: bool = True

    def info(self, club_tests: bool) -> PlayerInfo:
        return PlayerInfo(
            id=self.id,
            name=self.name,
            shirt=self.shirt,
            position=self.position,
            starter=self.starter,
            test_values=self.test_values if club_tests else None,
        )


@dataclass(frozen=True)
class SimTeam:
    id: str
    name: str
    side: str
    formation: str
    attacks_positive_x_in_period_1: bool
    players: list[SimPlayer]
    pass_success: float  # base pass completion before distance and pressure
    press_chance: float  # chance of a high press when the opponent builds up

    def info(self, club_tests: bool, bench: tuple[SimPlayer, ...] = ()) -> TeamInfo:
        """The starters, then ``bench``: the substitutes who came on."""
        return TeamInfo(
            id=self.id,
            name=self.name,
            side=self.side,
            formation=self.formation,
            attacks_positive_x_in_period_1=self.attacks_positive_x_in_period_1,
            players=[p.info(club_tests) for p in [*self.players, *bench]],
        )


@dataclass(frozen=True)
class SubPlan:
    """A planned substitution: from ``clock_s`` on the match clock (45:00 or earlier: at
    half-time), at the next stoppage, ``player`` replaces the one in engine slot ``slot``."""

    team: int
    slot: int  # engine index 0–21
    clock_s: float
    player: SimPlayer


def _clipped_normal(rng: np.random.Generator, mean: float, sd: float, lo_hi) -> float:
    return float(np.clip(rng.normal(mean, sd), *lo_hi))


def true_params(rng: np.random.Generator, prior: dict | None = None) -> TrueParams:
    """Hidden physiology of one player (synthesis §3.2.3, §3.2.4, §3.6). ``prior`` overrides
    the CS, D′ and pool settings (``params.VARY_PLAYERS``); the draws are the same either way."""
    q = prior or {}
    cs_sd, cs_range = q.get("cs_sd", P.CS_SD), q.get("cs_range", P.CS_RANGE)
    dp_sd, dp_range = q.get("d_prime_sd", P.D_PRIME_SD), q.get("d_prime_range", P.D_PRIME_RANGE)
    return TrueParams(
        cs=round(_clipped_normal(rng, P.CS_MEAN, cs_sd, cs_range), 3),
        d_prime=round(_clipped_normal(rng, P.D_PRIME_MEAN, dp_sd, dp_range), 1),
        a0=round(_clipped_normal(rng, P.A0_MEAN, P.A0_SD, P.A0_RANGE), 3),
        s0=round(_clipped_normal(rng, P.S0_MEAN, P.S0_SD, P.S0_RANGE), 3),
        fast_fraction=round(
            float(rng.uniform(*q.get("fast_fraction_range", P.FAST_FRACTION_RANGE))), 3
        ),
        tau_fast=round(float(rng.uniform(*q.get("tau_fast_range", P.TAU_FAST_RANGE))), 1),
        tau_slow=round(float(rng.uniform(*q.get("tau_slow_range", P.TAU_SLOW_RANGE))), 1),
    )


def club_test_values(rng: np.random.Generator, truth: TrueParams) -> ClubTestValues:
    """Truth plus a normal measurement error on each value (params.TEST_ERROR_SD)."""

    def measured(name: str, ndigits: int) -> float:
        sd = P.TEST_ERROR_SD[name]
        error = float(np.clip(rng.normal(0.0, sd), -3 * sd, 3 * sd))
        return round(getattr(truth, name) * (1 + error), ndigits)

    return ClubTestValues(
        cs=measured("cs", 2),
        d_prime=measured("d_prime", 0),
        a0=measured("a0", 2),
        s0=measured("s0", 2),
    )


def _player_name(rng: np.random.Generator, used: set[str]) -> str:
    while True:
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAME_START)}{rng.choice(SURNAME_END)}"
        name = _collapse(name)
        if name not in used:
            used.add(name)
            return name


def _collapse(name: str) -> str:
    return re.sub(r"(.)\1\1+", r"\1\1", name)  # "Yarr" + "rigg" is Yarrigg, not Yarrrigg


def distinct_names(
    teams: list[SimTeam], plans: list[SubPlan]
) -> tuple[list[SimTeam], list[SubPlan]]:
    """No two players of a team share a first name or a surname's start (decision 42: "Sami
    Yarrigg" and "Sami Yarrick" were the away team's two centre-backs). The later one (starters
    first, then substitutes, by id) takes the next unused first name or start in the lists. No
    random draws: names are labels only, so the match is the same frame for frame."""
    names = {p.name for t in teams for p in t.players} | {s.player.name for s in plans}
    renamed: dict[str, str] = {}
    for k, team in enumerate(teams):
        firsts: set[str] = set()
        starts: set[str] = set()
        mine = [p for p in team.players] + sorted(
            (s.player for s in plans if s.team == k), key=lambda p: p.id
        )
        for p in mine:
            first, surname = p.name.split(" ", 1)
            start = max((s for s in SURNAME_START if surname.startswith(s)), key=len)
            end = surname[len(start) :]
            if first in firsts or start in starts:
                names.discard(p.name)
                i, j = FIRST_NAMES.index(first), SURNAME_START.index(start)
                while first in firsts:
                    i = (i + 1) % len(FIRST_NAMES)
                    first = FIRST_NAMES[i]
                name = _collapse(f"{first} {start}{end}")
                while start in starts or name in names:
                    j = (j + 1) % len(SURNAME_START)
                    start = SURNAME_START[j]
                    name = _collapse(f"{first} {start}{end}")
                renamed[p.id] = name
                names.add(name)
            firsts.add(first)
            starts.add(start)

    def new(p: SimPlayer) -> SimPlayer:
        return replace(p, name=renamed[p.id]) if p.id in renamed else p

    teams = [replace(t, players=[new(p) for p in t.players]) for t in teams]
    plans = [replace(s, player=new(s.player)) for s in plans]
    return teams, plans


def make_teams(rng: np.random.Generator, prior: dict | None = None) -> list[SimTeam]:
    """Home and away teams, both 4-2-3-1. Ids are H01–H11 and A01–A11 in formation order."""
    places = rng.choice(len(PLACES), size=2, replace=False)
    home_attacks_positive_x = bool(rng.random() < 0.5)
    used: set[str] = set()
    teams = []
    for side, place in zip(["home", "away"], places, strict=True):
        shirts = {pos: list(numbers) for pos, numbers in P.SHIRTS.items()}
        players = []
        for i, (pos, u, v) in enumerate(P.FORMATION_4231, start=1):
            truth = true_params(rng, prior)
            players.append(
                SimPlayer(
                    id=f"{side[0].upper()}{i:02d}",
                    name=_player_name(rng, used),
                    shirt=shirts[pos].pop(0),
                    position=pos,
                    slot=(u, v),
                    params=truth,
                    test_values=None if pos == Position.GK else club_test_values(rng, truth),
                )
            )
        teams.append(
            SimTeam(
                id=side,
                name=f"{PLACES[place]} {rng.choice(SUFFIXES)}",
                side=side,
                formation="4-2-3-1",
                attacks_positive_x_in_period_1=home_attacks_positive_x == (side == "home"),
                players=players,
                pass_success=float(rng.normal(P.PASS_BASE_SUCCESS, P.PASS_SUCCESS_TEAM_SD)),
                press_chance=float(rng.uniform(*P.PRESS_CHANCE)),
            )
        )
    return teams


def plan_substitutions(
    rng: np.random.Generator, teams: list[SimTeam], prior: dict | None = None
) -> list[SubPlan]:
    """Each team's substitutes (params, "Substitutions"): how many, the windows, and who goes
    off, like for like. A substitute gets their own hidden values and club test values. Ids
    H12–H16 and A12–A16, shirts 12–16, in the order they are planned."""
    used = {p.name for team in teams for p in team.players}
    plans = []
    for k, team in enumerate(teams):
        n = int(rng.choice(P.SUBS_CHOICES, p=P.SUBS_WEIGHTS))
        windows = sorted(
            float(np.clip(rng.normal(mean, sd), *P.SUB_WINDOW_CLIP))
            for mean, sd in zip(P.SUB_WINDOWS_MIN, P.SUB_WINDOW_SD, strict=True)
        )
        weight = np.array([P.SUB_WEIGHT[p.position] for p in team.players])
        number = 12
        for minute, count in zip(windows, P.SUBS_PER_WINDOW[n], strict=True):
            clock = 45.0 * 60.0 if minute < P.HALF_TIME_SUB_BEFORE else minute * 60.0
            for _ in range(count):
                j = int(rng.choice(11, p=weight / weight.sum()))
                weight[j] = 0.0  # a slot is substituted once
                off = team.players[j]
                truth = true_params(rng, prior)
                player = SimPlayer(
                    id=f"{team.side[0].upper()}{number:02d}",
                    name=_player_name(rng, used),
                    shirt=number,
                    position=off.position,
                    slot=off.slot,
                    params=truth,
                    test_values=club_test_values(rng, truth),
                    starter=False,
                )
                plans.append(SubPlan(k, 11 * k + j, clock, player))
                number += 1
    return sorted(plans, key=lambda s: (s.clock_s, s.slot))
