"""Read-only match tools for the agents: the only way the agents
see a match. ``agents.mcp_server`` serves them over MCP; the feed pipeline calls them directly.

They read ``metadata.json``, ``events.jsonl``, ``tracking.jsonl`` (ball status, possession and
positions at 1 Hz) and the estimator's ``signals.json``, never the truth file. Every number
comes back as ``{"value", "unit", "source"}``: the source names the field it was computed from,
so a sentence can be traced back to the data.

Times are ``(period, t)``, ``t`` in seconds since that period's kick-off, because the match
clock repeats (first-half added time runs past 45:00 while the second half starts at 45:00).
``clock`` is the broadcast label ("45+2:10", "67:12"); ``video_s`` counts seconds from the
first kick-off with half-time left out, for syncing to video.

Thresholds for moments and context are our assumptions unless a source is named.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

import numpy as np

from runningbattery.agents import verifier
from runningbattery.engine import params as EP
from runningbattery.io import EVENTS, METADATA, SIGNALS, TRACKING, read_signals
from runningbattery.schema import Event, MatchMetadata

PERIOD_CLOCK = {1: 0.0, 2: 45 * 60.0}
PERIOD_END = {1: 45 * 60.0, 2: 90 * 60.0}
DEFENDERS = ("CB", "FB", "DM")

# Context (moment_context) and moments (find_moments); our assumptions.
START_OF_HALF_S = 600.0  # the 2nd-half dip lasts about 10 min [Bradley2013; Mohr2005]
JUST_ON_S = 600.0  # "just substituted on"
JUST_CHANGED_S = 10.0  # "just lost / won the ball"; transitions last about 15 s (sim params)
LONG_STOPPAGE_S = 30.0
LOW_IN_PLAY = 0.5  # share of the last 5 min with the ball in play
TEAM_POSSESSION = 0.6  # share of the last 5 min with the ball: "his team had the ball"
BIG_LEAD = 2
LOW_FIRST_HALF_LOAD = 0.9  # energy at half-time vs the median starter's
DROP_SHARE = 0.6  # 5-min high-speed running below this share of his match average so far
MIN_HSR_PER_MIN = 3.0  # m/min; below this a player's "normal" is too small to compare with
MIN_ON_S = 600  # not_tired_tactical: at least 10 min on the pitch before a drop counts
SECOND_WIND_WINDOW_S = (120.0, 600.0)  # back to normal 2–10 min after a spell [Leifsson2024]
FRESH_WINDOW_S = 600.0  # a substitute's first 10 min
# Reasons that can explain a 5-min drop (not_tired_tactical), weighted for ranking.
WINDOW_REASONS = {"big_lead": 1.0, "team_in_possession": 0.5, "low_first_half_load": 0.5,
                  "low_ball_in_play": 0.3}  # fmt: skip
LOW_CHANCE_NOTE = (
    "Calibrated for a typical professional (isotonic map fitted on dev seeds 1–60). On held-out "
    "matches its expected calibration error is 0.001 (0.009 raw): seconds it puts at 0.1–0.2 "
    "and 0.3–0.4 were short-term tired 12% and 35% of the time. On players less fit than a "
    "typical professional it stays poorly calibrated (0.059). About the running, never the "
    "player's own state."
)
BATTERY_NOTE = (
    "Share of a typical professional's short-term reserve (D′) that this running would leave; "
    "the player's own CS and D′ are unknown."
)
MOMENT_KINDS = {
    "red_zone": ("His hardest minutes so far: 1-, 2- or 5-min high-speed running at ≥ 90% of his "
                 "best so far and of the published peak [Leifsson2024, Table 1]",
                 ["1", "2", "11", "19c"]),
    "exposed_on_turnover": ("His team loses the ball while he (a defender) is in or just after his "
                            "hardest minutes so far [Ju2022; Bortnik2022]", ["4", "3", "11"]),
    "second_wind": ("His high-speed running is back to his own match average 2–10 min after his "
                    "hardest minutes [Leifsson2024]", ["1", "2"]),
    "fresh_legs": ("A substitute who out-ran his team-mates: his high-speed running per minute vs "
                   "theirs over the same minutes and vs the player he replaced [Bradley2013; "
                   "Hills2018]", ["6"]),
    "not_tired_tactical": ("His running dropped while a non-fatigue reason fits (lead, stoppage, "
                           "possession, start of a half, just on) [Bradley2013; Morgans2025]",
                           ["13", "14", "9b"]),
    "tug_of_war": ("Team level: one team's high-speed running per ball-in-play minute over a "
                   "15-min block is well above the other's, or a gap that was there has closed "
                   " [Allen2026a; Allen2026b]", ["9a", "9b", "7", "30"]),
    "flat_out": ("A run at or near the player's top speed so far in the match (his fastest "
                 "second), measured [Kavanagh2024; Bradley2009]", ["36", "37", "10"]),
}  # fmt: skip
TEAM_KINDS = {"tug_of_war"}
# A caught-on-the-break moment needs the counter to come within COUNTER_NEAR_M metres of him or
# to end in a shot; the counter is the opponents' possession, followed for at most COUNTER_MAX_S
# seconds and at least COUNTER_MIN_S (the clip shows it). Our assumption.
COUNTER_NEAR_M = 15.0
COUNTER_MAX_S = 15.0
COUNTER_MIN_S = 6.0
# The overlay plays a clip on this long past its end (export.CLIP_AFTER). A caught-on-the-break
# moment's battery is read there, at the end of the clip of his counter (the line
# gave his 72% at the turnover, the clip ended on 61% after he had run 45 m above 5.5 m/s).
CLIP_AFTER_S = 2.0
BLOCK_S = 900.0  # 15-min blocks, as the published end-of-match comparisons [Bradley2009]
TEAM_GAP = 15.0  # % between the teams for a team-running moment (our assumption)
GAP_CLOSED = 7.5  # % below which a gap counts as closed (our assumption)
MIN_IN_PLAY_S = 300.0  # a block needs 5 min of ball in play to compare
# Spells of hardest minutes less than EPISODE_GAP_S apart in a half are one time when we count
# them ("for the second time"): the red-zone flag flickers as his 1-min running hovers near his
# best so far (H04 had 8 spells by 19:50, some 6 s apart, mostly one stretch, and the
# feed said "for the eighth time"). Our assumption.
EPISODE_GAP_S = 60.0
FLAT_OUT_SHARE = 0.9  # a flat-out run: ≥ 90% of his top speed so far (our assumption)
# Before the 75th minute a run that is neither his nor anyone's fastest so far needs 95%: the site's
# 11:56 "92% of his top speed so far" showed nothing worth a clip. After it, claim 36
# (top speed hardly drops) gives a 90% run its point.
FLAT_OUT_EARLY_SHARE = 0.95
FLAT_OUT_MIN_SPEED = 7.0  # m/s (25.2 km/h): about the sprint threshold [Bradley2009, p.162]
# A "so far" claim (his hardest minutes so far, his top speed so far, the lowest point of his
# match so far) needs SO_FAR_MIN_S on the pitch, as MIN_ON_S: before it, it is true of almost any
# running ("his hardest minutes so far" at 1:47 and 5:38, "his fastest of the match
# so far" from a substitute 4 min after he came on). Our assumption.
SO_FAR_MIN_S = 600
# A new best (his own, or anyone's so far) must beat the old one by this much, so that it shows at
# the 0.1 m/s we print: 7.92 against 7.88 m/s read as "7.9 and 7.9" and the LLM pass rewrote a
# true "new personal best" into "not his fastest". Our assumption.
NEW_BEST_MARGIN = 0.05  # m/s
MAX_PLAUSIBLE_SPEED = 11.0  # m/s; faster seconds are tracking errors (our assumption)
# Where each team's running happened: situations of play from possession and the
# ball's position only, ball in play. Situations, not purposes: "pressing" or "recovery runs"
# are what a player meant to do, which positions do not show (claims 35, 38; validate/purposes).
TRANSITION_S = 10.0  # the first 10 s after the ball changes hands: transitions last 9.3–10.9 s
# on average [Bortnik2022, Table 2]
THIRD_X = 105.0 / 6.0  # the pitch in thirds: lines 17.5 m either side of halfway (105 m pitch)
SITUATIONS = {
    "after_losing": "first 10 s after losing the ball",
    "after_winning": "first 10 s after winning the ball",
    "on_ball": "on the ball, after those 10 s",
    "off_ball_high": "without the ball, with it in the opponents' third",
    "off_ball_deep": "without the ball, with it in the middle or their own third",
}
CHANGED_HANDS = ("after_losing", "after_winning")
# A touch: an on-ball event of his (our definition; a carry is the run between a reception and
# the next action, so it is not counted again). Claim 14 needs these counts.
TOUCH_TYPES = ("pass", "reception", "shot", "clearance", "interception", "ball_recovery")
# Claims offered only where they fit: claim 1's figure is for a spell of about
# 5 min [Leifsson2024, Table 1], claim 36 for a run after the 75th minute, claim 7 for the
# last block of the match.
LONG_SPELL_S = 240.0
MIN_AVERAGE_S = 600  # a "match average" needs 10 min on the pitch (as MIN_ON_S)
# Published match peak speed by position, Brazil, 10 Hz GNSS [SilvaH2025, Table 1]; DM and AM
# use the central midfielders' value.
MATCH_PEAK = {"CB": 8.09, "FB": 8.79, "DM": 8.41, "CM": 8.41, "AM": 8.41, "WM": 8.52,
              "CF": 8.29}  # fmt: skip
REASONS = {
    "big_lead": "his team leads by {lead} ({score})",
    "start_of_half": "the first {minutes:.0f} min of the half",
    "just_subbed_on": "he came on {minutes:.0f} min ago",
    "ball_out_of_play": "the ball has been out of play for {seconds:.0f} s",
    "low_ball_in_play": "the ball was in play only {share:.0%} of the last 5 min",
    "team_in_possession": "his team had the ball {share:.0%} of the last 5 min",
    "just_won_ball": "his team won the ball {seconds:.0f} s ago",
    "low_first_half_load": "his first-half load was {share:.0%} of the median starter's",
}


def q(value: float | int, unit: str, source: str, digits: int = 2) -> dict[str, Any]:
    """A number with its unit and the field it came from."""
    if isinstance(value, float | np.floating):
        v = round(float(value), digits) if math.isfinite(value) else None  # JSON has no NaN
        v = int(v) if v is not None and digits == 0 else v  # "32 km/h", not "32.0"
    else:
        v = int(value)
    return {"value": v, "unit": unit, "source": source}


def clock_label(period: int, t: float) -> str:
    c = PERIOD_CLOCK[period] + t
    end = PERIOD_END[period]
    if c >= end:
        extra = c - end
        return f"{end / 60:.0f}+{int(extra // 60)}:{int(extra % 60):02d}"
    return f"{int(c // 60)}:{int(c % 60):02d}"


def parse_time(value: str | float | int, period: int | None = None) -> tuple[int, float]:
    """ "67:12", "45+2:10", "90+1" or minutes (67.2) to (period, t). Clock times up to 45:00
    are the first half unless ``period`` says otherwise."""
    if isinstance(value, int | float):
        minutes, extra = float(value), 0.0
        base = None
    else:
        m = re.fullmatch(r"\s*(\d+)(?:\+(\d+))?(?::(\d+(?:\.\d+)?))?\s*", str(value))
        if not m:
            raise ValueError(f"not a match time: {value!r}")
        base = float(m.group(1))
        extra = float(m.group(2) or 0) + float(m.group(3) or 0) / 60.0
        minutes = base if m.group(2) else base + extra
        extra = extra if m.group(2) else 0.0
    if base is not None and extra and base in (45.0, 90.0):
        p = 1 if base == 45.0 else 2
        return p, (base - PERIOD_CLOCK[p] / 60.0 + extra) * 60.0
    p = period or (1 if minutes <= 45.0 else 2)
    return p, max(minutes * 60.0 - PERIOD_CLOCK[p], 0.0)


@dataclass
class Series:
    """One player's signals as arrays, indexed by second on the pitch."""

    period: np.ndarray
    t: np.ndarray
    cols: dict[str, np.ndarray]

    def index(self, period: int, t: float) -> int | None:
        """The last second on the pitch at or before (period, t); None if not on yet."""
        key = self.period * 1e5 + self.t
        i = int(np.searchsorted(key, period * 1e5 + t, side="right")) - 1
        return i if i >= 0 else None

    def span(self, a: tuple[int, float], b: tuple[int, float]) -> slice:
        key = self.period * 1e5 + self.t
        lo = int(np.searchsorted(key, a[0] * 1e5 + a[1], side="left"))
        hi = int(np.searchsorted(key, b[0] * 1e5 + b[1], side="right"))
        return slice(lo, hi)


def counter_end_t(t: float, chain_t: list[float]) -> float:
    """When a counter that starts at ``t`` ends for the clip: its possession's last event, kept
    between ``COUNTER_MIN_S`` and ``COUNTER_MAX_S`` seconds after ``t``."""
    last = max((x for x in chain_t if x >= t), default=t)
    return min(max(last, t + COUNTER_MIN_S), t + COUNTER_MAX_S)


class MatchData:
    """A match folder as the agents may see it (no truth)."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.metadata = MatchMetadata.model_validate_json((self.folder / METADATA).read_text())
        with (self.folder / EVENTS).open() as f:
            self.events = [Event.model_validate_json(line) for line in f if line.strip()]
        self.signals = read_signals(self.folder / SIGNALS)
        self.players = {
            p.id: {"id": p.id, "name": p.name, "shirt": p.shirt, "team": team.id,
                   "team_name": team.name, "position": p.position.value, "starter": p.starter}
            for team in self.metadata.teams for p in team.players
        }  # fmt: skip
        self.teams = {team.id: team for team in self.metadata.teams}
        self.durations = {p.period: p.duration_s for p in self.metadata.periods}
        self.series = {}
        for ps in self.signals.players:
            s = ps.series
            cols = {
                k: np.asarray(v, dtype=float)
                for k, v in s.model_dump().items()
                if v is not None and k not in ("period", "t")
            }
            self.series[ps.player_id] = Series(np.asarray(s.period), np.asarray(s.t), cols)
        self._read_tracking()
        self._full: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] | None = None

    def _read_tracking(self) -> None:
        """Ball status, possession and positions once per second (the frames on whole seconds
        of each period)."""
        hz = round(self.metadata.frame_rate_hz)
        starts = {p.period: p.start_frame for p in self.metadata.periods}
        ids = list(self.players)
        col = {pid: j for j, pid in enumerate(ids)}
        rows: dict[int, list] = {1: [], 2: []}
        with (self.folder / TRACKING).open() as f:
            for n, line in enumerate(f):
                period = 1 if n < starts.get(2, 1 << 60) else 2
                if (n - starts[period]) % hz:
                    continue
                fr = json.loads(line)
                xy = np.full((len(ids), 2), np.nan)
                for p in fr["players"]:
                    xy[col[p["id"]]] = (p["x"], p["y"])
                ball = fr["ball"]
                rows[period].append(
                    (fr["ball_status"] == "alive", fr.get("possession_team"), xy,
                     (ball["x"], ball["y"]))
                )  # fmt: skip
        self.col = col
        self.alive = {p: np.array([r[0] for r in rs]) for p, rs in rows.items() if rs}
        self.possession = {p: [r[1] for r in rs] for p, rs in rows.items() if rs}
        self.xy = {p: np.stack([r[2] for r in rs]) for p, rs in rows.items() if rs}
        self.ball = {p: np.array([r[3] for r in rs]) for p, rs in rows.items() if rs}

    # --- Time ------------------------------------------------------------------------------

    def video_s(self, period: int, t: float) -> float:
        return round(t + (self.durations[1] if period == 2 else 0.0), 1)

    def when(self, period: int, t: float) -> dict[str, Any]:
        return {"period": period, "t": round(float(t), 1), "clock": clock_label(period, t),
                "video_s": self.video_s(period, t)}  # fmt: skip

    def second(self, period: int, t: float) -> int:
        n = len(self.alive[period])
        return int(min(max(math.floor(t), 0), n - 1))

    def gap_at(self, period: int, t: float, j: int) -> float:
        """Player column ``j``'s distance to the ball at ``t``, between the 1-Hz samples
        (read at the whole second before, "8 s later" said 4 m for 6.6 m)."""
        n = len(self.alive[period])
        k = int(min(max(math.floor(t), 0), max(n - 2, 0)))
        f = min(max(t - k, 0.0), 1.0) if n > 1 else 0.0
        xy, ball = self.xy[period], self.ball[period]
        k1 = min(k + 1, n - 1)
        a = xy[k, j] + f * (xy[k1, j] - xy[k, j])
        b = ball[k] + f * (ball[k1] - ball[k])
        return float(np.hypot(*(a - b)))

    def nearest_ball(self, period: int, t0: float, t1: float, j: int) -> float:
        """Player column ``j``'s smallest distance to the ball from ``t0`` to ``t1``, at the full
        frame rate (the 1-Hz samples said "as close as 2 m" for 1.2 m). NaN if he
        is not seen."""
        if self._full is None:
            self._read_full_tracking()
        times, xy, ball = self._full[period]
        k = (times >= t0 - 1e-6) & (times <= t1 + 1e-6)
        d = np.hypot(*(xy[k, j] - ball[k]).T)
        return float(np.nanmin(d)) if np.isfinite(d).any() else float("nan")

    def _read_full_tracking(self) -> None:
        """Every frame's positions and ball, per period (read once, when first needed)."""
        ids = list(self.players)
        rows: dict[int, list] = {1: [], 2: []}
        with (self.folder / TRACKING).open() as f:
            for line in f:
                fr = json.loads(line)
                xy = np.full((len(ids), 2), np.nan)
                for p in fr["players"]:
                    xy[self.col[p["id"]]] = (p["x"], p["y"])
                rows[fr["period"]].append((fr["t"], xy, (fr["ball"]["x"], fr["ball"]["y"])))
        self._full = {
            p: (np.array([r[0] for r in rs]), np.stack([r[1] for r in rs]),
                np.array([r[2] for r in rs]))
            for p, rs in rows.items() if rs
        }  # fmt: skip

    # --- Lookups ---------------------------------------------------------------------------

    def player(self, ref: str) -> dict[str, Any]:
        """By id ("H04"), name, or "home 3" / "away 9" (team and shirt)."""
        ref = str(ref).strip()
        if ref.upper() in self.players:
            return self.players[ref.upper()]
        for p in self.players.values():
            if p["name"].lower() == ref.lower():
                return p
        m = re.fullmatch(r"(home|away)\s*#?(\d+)", ref.lower())
        if m:
            for p in self.players.values():
                if p["team"] == m.group(1) and p["shirt"] == int(m.group(2)):
                    return p
        raise KeyError(f"no player {ref!r}")

    @cached_property
    def goals(self) -> list[Event]:
        return sorted((e for e in self.events if e.type.value == "goal"),
                      key=lambda e: (e.period, e.t))  # fmt: skip

    def score(self, period: int, t: float) -> dict[str, int]:
        done = [g for g in self.goals if (g.period, g.t) <= (period, t)]
        return {side: sum(g.team_id == side for g in done) for side in ("home", "away")}

    @cached_property
    def sub_times(self) -> dict[str, tuple[int, float, str]]:
        """Player id -> (period, t, the other player) for players who came on."""
        return {s.player_in: (s.period, s.t, s.player_out) for s in self.metadata.substitutions}

    @cached_property
    def sub_off(self) -> dict[str, tuple[int, float, str]]:
        return {s.player_out: (s.period, s.t, s.player_in) for s in self.metadata.substitutions}

    @cached_property
    def team_seconds(self) -> dict[int, dict[str, np.ndarray]]:
        """Per period, per second: each team's high-speed metres and metres (outfield players on
        the pitch), with ball status and possession from the tracking."""
        out = {}
        for per, alive in self.alive.items():
            n = len(alive)
            d = {f"{k}_{team}": np.zeros(n) for team in self.teams for k in ("hsr", "dist")}
            for pid, s in self.series.items():
                info = self.players[pid]
                if info["position"] == "GK":
                    continue
                rows = np.flatnonzero(s.period == per)
                k = np.clip(np.floor(s.t[rows]).astype(int), 0, n - 1)
                speed = s.cols["speed"][rows]
                np.add.at(d[f"dist_{info['team']}"], k, speed)
                np.add.at(d[f"hsr_{info['team']}"], k, np.where(speed > EP.HI_SPEED, speed, 0.0))
            d["alive"] = alive
            d["poss"] = np.array([x or "" for x in self.possession[per]])
            out[per] = d
        return out

    def team_rates(self, period: int, a: float, b: float) -> dict[str, dict[str, float]]:
        """Each team's running per ball-in-play minute between a and b seconds of a period."""
        d = self.team_seconds[period]
        w = slice(int(a), int(min(b, len(d["alive"]))))
        alive, poss = d["alive"][w], d["poss"][w]
        out = {}
        for team in self.teams:
            other = next(t for t in self.teams if t != team)
            hsr, dist = d[f"hsr_{team}"][w], d[f"dist_{team}"][w]
            mine, theirs = alive & (poss == team), alive & (poss == other)

            def rate(x, mask):
                return float(x[mask].sum() / mask.sum() * 60.0) if mask.sum() else float("nan")

            out[team] = {"hsr": rate(hsr, alive), "hsr_with_ball": rate(hsr, mine),
                         "hsr_without_ball": rate(hsr, theirs), "dist": rate(dist, alive),
                         "possession": float(mine.sum() / max(alive.sum(), 1)),
                         "in_play_s": float(alive.sum())}  # fmt: skip
        return out

    @cached_property
    def situations(self) -> dict[int, dict[str, np.ndarray]]:
        """Per period, per team, per second: its situation of play (``SITUATIONS``), "" with the
        ball out of play. The team on the ball is the last one seen with it (a loose ball stays
        with them); a change of possession starts the first ``TRANSITION_S`` s for both teams,
        as for a recovery run (``highlights.losses``)."""
        out = {}
        for per, alive in self.alive.items():
            holder, since = [], []
            last, change = "", -1e9
            for k, x in enumerate(self.possession[per]):
                if x and x != last:
                    change = k if last else change  # the first holder of the half is no change
                    last = x
                holder.append(last)
                since.append(k - change)
            holder_, fresh = np.array(holder), np.array(since) < TRANSITION_S
            out[per] = {}
            for team, info in self.teams.items():
                forward = info.attacks_positive_x_in_period_1 == (per == 1)
                x = self.ball[per][:, 0] * (1.0 if forward else -1.0)  # towards their goal
                mine = holder_ == team
                s = np.where(
                    mine,
                    np.where(fresh, "after_winning", "on_ball"),
                    np.where(fresh, "after_losing",
                             np.where(x >= THIRD_X, "off_ball_high", "off_ball_deep")),
                )  # fmt: skip
                out[per][team] = np.where(alive & (holder_ != ""), s, "")
        return out

    def team_situations(self, period: int, a: float, b: float) -> dict[str, dict[str, dict]]:
        """Each team's metres above 5.5 m/s (outfield team total) and ball-in-play seconds per
        situation between a and b seconds of a period."""
        d, sit = self.team_seconds[period], self.situations[period]
        w = slice(int(a), int(min(b, len(d["alive"]))))
        out = {}
        for team in self.teams:
            hsr, s = d[f"hsr_{team}"][w], sit[team][w]
            out[team] = {k: {"hsr": float(hsr[s == k].sum()), "in_play_s": float((s == k).sum())}
                         for k in SITUATIONS}  # fmt: skip
        return out

    def blocks(self) -> list[tuple[int, float, float]]:
        """15-min blocks per period (added time in the last one): (period, start, end) s."""
        out = []
        for per, dur in self.durations.items():
            a = 0.0
            while a < dur:
                b = a + BLOCK_S if a + 2 * BLOCK_S <= dur + BLOCK_S / 2 else dur
                out.append((per, a, min(b, dur)))
                a = b
        return out

    @cached_property
    def touches(self) -> dict[str, list[tuple[int, float]]]:
        """Player id -> (period, t) of each touch (``TOUCH_TYPES``)."""
        out: dict[str, list[tuple[int, float]]] = {}
        for e in self.events:
            if e.player_id and e.type.value in TOUCH_TYPES:
                out.setdefault(e.player_id, []).append((e.period, e.t))
        return out

    def in_play(self, pid: str) -> np.ndarray:
        """For each of his seconds on the pitch: was the ball in play?"""
        s = self.series[pid]
        return np.array([bool(self.alive[int(p)][self.second(int(p), float(t))])
                         for p, t in zip(s.period, s.t, strict=True)])  # fmt: skip

    def hsr_per_s(self, pid: str) -> np.ndarray:
        """Metres above HI_SPEED in each second (the per-second mean speed)."""
        speed = self.series[pid].cols["speed"]
        return np.where(speed > EP.HI_SPEED, speed, 0.0)

    def hsr_avg_so_far(self, pid: str) -> np.ndarray:
        """His match average so far, m/min of high-speed running per minute on the pitch."""
        h = self.hsr_per_s(pid)
        return np.cumsum(h) / np.maximum(np.arange(1, len(h) + 1), 60) * 60.0


HSR_SRC = "signals.players[].series.speed > 5.5 m/s (19.8 km/h), per minute on the pitch"
VS_AVG = "% above (+) or below (−) his match average"
HSR_TEAM = "m of high-speed running (> 5.5 m/s) per ball-in-play minute, team total"
HSR_WITH = "m of high-speed running per minute with the ball, team total"
HSR_WITHOUT = "m of high-speed running per minute without the ball, team total"
DIST_TEAM = "m of total distance per ball-in-play minute, team total"


class MatchTools:
    """The six tools. Each returns plain JSON-able data."""

    def __init__(self, folder: Path | str):
        self.m = MatchData(Path(folder))

    # --- match_summary -----------------------------------------------------------------------

    def match_summary(self) -> dict[str, Any]:
        m = self.m
        score = {"home": 0, "away": 0}
        timeline = []
        for g in m.goals:
            score[g.team_id] += 1
            who = m.players.get(g.player_id or "", {})
            timeline.append(m.when(g.period, g.t) | {
                "team": g.team_id, "scorer": who.get("name"), "scorer_id": g.player_id,
                "score": dict(score), "source": "events.jsonl type=goal",
            })  # fmt: skip
        subs = []
        for s in m.metadata.substitutions:
            subs.append(m.when(s.period, s.t) | {
                "team": s.team_id, "off": m.players[s.player_out]["name"], "off_id": s.player_out,
                "on": m.players[s.player_in]["name"], "on_id": s.player_in,
                "source": "metadata.substitutions",
            })  # fmt: skip
        teams = [
            {"id": t.id, "name": t.name, "side": t.side, "formation": t.formation,
             "players": [m.players[p.id] for p in t.players]}
            for t in m.metadata.teams
        ]  # fmt: skip
        return {
            "match_id": m.metadata.match_id,
            "synthetic": True,
            "teams": teams,
            "final_score": score,
            "goals": timeline,
            "substitutions": subs,
            "periods": [
                {"period": p.period,
                 "minutes": q(p.duration_s / 60.0, "min", "metadata.periods[].duration_s", 1)}
                for p in m.metadata.periods
            ],  # fmt: skip
            "engine": {"prior": m.signals.engine.prior, "mode": m.signals.engine.mode,
                       "k": m.signals.engine.k, "low_chance_map": m.signals.engine.low_chance_map},
        }  # fmt: skip

    # --- player_signals ----------------------------------------------------------------------

    def player_signals(
        self, player: str, start: str | float | None = None, end: str | float | None = None
    ) -> dict[str, Any]:
        m = self.m
        info = m.player(player)
        s = m.series.get(info["id"])
        if s is None or not len(s.t):
            return {"player": info, "on_pitch": False}
        a = parse_time(start) if start is not None else (int(s.period[0]), float(s.t[0]))
        b = parse_time(end) if end is not None else (int(s.period[-1]), float(s.t[-1]))
        w = s.span(a, b)
        if w.stop <= w.start:
            return {"player": info, "on_pitch": False, "window": [m.when(*a), m.when(*b)]}
        i, c = w.stop - 1, s.cols
        hsr, avg = m.hsr_per_s(info["id"]), m.hsr_avg_so_far(info["id"])
        n = w.stop - w.start
        win_rate = float(hsr[w].sum()) / max(n, 60) * 60.0
        red, post = c["red_zone"][w].astype(bool), c["post_peak"][w].astype(bool)
        sig = "signals.players[].series."
        out = {
            "player": info,
            "on_pitch": True,
            "window": {
                "from": m.when(int(s.period[w.start]), float(s.t[w.start])),
                "to": m.when(int(s.period[i]), float(s.t[i])),
                "seconds_on_pitch": q(n, "s", sig + "t"),
            },  # fmt: skip
            "battery": {
                "typical_pro_at_end": q(
                    c["battery"][i],
                    "share of a typical professional's short-term reserve",
                    sig + "battery",
                ),
                "band_10_90_at_end": [
                    q(c["battery_lo"][i], "share", sig + "battery_lo"),
                    q(c["battery_hi"][i], "share", sig + "battery_hi"),
                ]
                if "battery_lo" in c
                else None,
                "lowest_in_window": q(c["battery"][w].min(), "share", sig + "battery"),
                "lowest_in_match_so_far": q(c["battery"][: i + 1].min(), "share", sig + "battery"),
                "note": BATTERY_NOTE,
            },
            "low_chance": {
                "at_end": q(c["low_chance"][i], "chance", sig + "low_chance"),
                "max_in_window": q(c["low_chance"][w].max(), "chance", sig + "low_chance"),
                "calibration": LOW_CHANCE_NOTE,
            }
            if "low_chance" in c
            else None,
            "energy": {
                "since_kickoff": q(c["energy"][i], "kJ/kg", sig + "energy", 1),
                "in_window": q(
                    c["energy"][i] - (c["energy"][w.start - 1] if w.start else 0.0),
                    "kJ/kg",
                    sig + "energy",
                    1,
                ),
            },
            "hsr": {
                "last_1min": q(c["hsr_1min"][i], "m", sig + "hsr_1min", 0),
                "last_2min": q(c["hsr_2min"][i], "m", sig + "hsr_2min", 0),
                "last_5min": q(c["hsr_5min"][i], "m", sig + "hsr_5min", 0),
                "last_1min_vs_own_peak": q(
                    c["hsr_1min_vs_peak"][i], "share of his best so far", sig + "hsr_1min_vs_peak"
                ),
                "last_5min_vs_own_peak": q(
                    c["hsr_5min_vs_peak"][i], "share of his best so far", sig + "hsr_5min_vs_peak"
                ),
                "window_per_min": q(win_rate, "m/min", HSR_SRC, 1),
                "match_average_per_min": q(avg[i], "m/min", HSR_SRC, 1),
                "window_vs_match_average": q(pct(win_rate, avg[i]), VS_AVG, HSR_SRC, 0),
                "threshold": q(EP.HI_SPEED, "m/s (19.8 km/h)", "engine.hi_speed"),
            },
            "flags": {
                "in_hardest_minutes_now": bool(red[-1]),
                "just_after_hardest_minutes_now": bool(post[-1]),
                "hardest_minutes_s": q(int(red.sum()), "s", sig + "red_zone"),
                "hardest_minutes_count": q(
                    (episodes([(a + w.start, b + w.start) for a, b in runs(red)], s) or [0])[-1],
                    "times at his hardest minutes so far",
                    sig + "red_zone",
                ),
                "just_after_hardest_minutes_s": q(int(post.sum()), "s", sig + "post_peak"),
                "post_peak_wording": "neutral only: just after his hardest minutes so far",
            },
            "in_play": {
                "last_1min": q(c["in_play_1min"][i], "share", sig + "in_play_1min"),
                "last_5min": q(c["in_play_5min"][i], "share", sig + "in_play_5min"),
            },
            "capacity_assumed": {
                "cs": q(
                    signals_capacity(m, info["id"], "cs"),
                    "m/s",
                    "signals.players[].capacity.cs (model parameter, assumed; never measured)",
                ),
                "d_prime": q(
                    signals_capacity(m, info["id"], "d_prime"),
                    "m",
                    "signals.players[].capacity.d_prime (model parameter, assumed)",
                    0,
                ),
            },
        }
        return out

    # --- moment_context ----------------------------------------------------------------------

    def moment_context(
        self, t: str | float, period: int | None = None, player: str | None = None,
        team: str | None = None,
    ) -> dict[str, Any]:  # fmt: skip
        """What else could explain the running at match time ``t`` (a clock label, or minutes on
        the match clock) (claim 13)."""
        p, sec = parse_time(t, period)
        return self.context_at(p, sec, player, team)

    def context_at(
        self, p: int, sec: float, player: str | None = None, team: str | None = None
    ) -> dict[str, Any]:
        """``moment_context`` at ``sec`` seconds after period ``p``'s kick-off."""
        m = self.m
        info = m.player(player) if player else None
        team = team or (info["team"] if info else None)
        k = m.second(p, sec)
        alive = m.alive[p]
        last5 = slice(max(k - 299, 0), k + 1)
        dead_for = 0
        while k - dead_for >= 0 and not alive[k - dead_for]:
            dead_for += 1
        poss = m.possession[p]
        holder = next((x for x in reversed(poss[: k + 1]) if x), None)
        changed = k
        while changed > 0 and (poss[changed - 1] or holder) == holder:
            changed -= 1
        since_change = float(k - changed)
        score = m.score(p, sec)
        ctx: dict[str, Any] = m.when(p, sec) | {
            "ball_in_play": bool(alive[k]),
            "ball_out_for": q(dead_for, "s", "tracking.ball_status"),
            "in_play_last_5min": q(alive[last5].mean(), "share", "tracking.ball_status"),
            "score": score,
            "minutes_into_half": q(sec / 60.0, "min", "tracking.t", 1),
            "possession": holder,
            "possession_for": q(since_change, "s", "tracking.possession_team"),
        }
        reasons = []
        if not alive[k] and dead_for >= LONG_STOPPAGE_S:
            reasons.append(("ball_out_of_play", {"seconds": dead_for}))
        if alive[last5].mean() < LOW_IN_PLAY:
            reasons.append(("low_ball_in_play", {"share": alive[last5].mean()}))
        if sec < START_OF_HALF_S:
            reasons.append(("start_of_half", {"minutes": START_OF_HALF_S / 60.0}))
        if team:
            other = "away" if team == "home" else "home"
            lead = score[team] - score[other]
            ctx["team"] = team
            ctx["lead"] = q(lead, "goals", "events.jsonl type=goal")
            share = float(np.mean([x == team for x in poss[last5]]))
            ctx["team_possession_last_5min"] = q(share, "share", "tracking.possession_team")
            ctx["team_just_lost_ball"] = holder != team and since_change <= JUST_CHANGED_S
            ctx["team_just_won_ball"] = holder == team and since_change <= JUST_CHANGED_S
            if lead >= BIG_LEAD:
                reasons.append(
                    ("big_lead", {"lead": lead, "score": f"{score['home']}–{score['away']}"})
                )
            if share >= TEAM_POSSESSION:
                reasons.append(("team_in_possession", {"share": share}))
            if ctx["team_just_won_ball"]:
                reasons.append(("just_won_ball", {"seconds": since_change}))
        if info:
            ctx["player"] = info
            ctx["defensive_role"] = info["position"] in DEFENDERS
            on = m.sub_times.get(info["id"])
            if on and (on[0], on[1]) <= (p, sec):
                ago = (sec - on[1]) if on[0] == p else sec + m.durations[on[0]] - on[1]
                ctx["came_on"] = m.when(on[0], on[1]) | {"for": m.players[on[2]]["name"]}
                if ago <= JUST_ON_S:
                    reasons.append(("just_subbed_on", {"minutes": ago / 60.0}))
            if p == 2 and info["id"] in m.series:
                share = first_half_load(m, info["id"])
                if share is not None:
                    ctx["first_half_load_vs_median_starter"] = q(
                        share, "share", "signals.players[].series.energy at half-time"
                    )
                    if share < LOW_FIRST_HALF_LOAD:
                        reasons.append(("low_first_half_load", {"share": share}))
        ctx["non_fatigue_reasons"] = [
            {"code": code, "text": REASONS[code].format(**kw)} for code, kw in reasons
        ]
        ctx["rule"] = ("Before 'tired', 'fatigue' or 'in the red': if a non-fatigue reason is "
                       "listed, name it or use neutral words such as 'ran less' ("
                       "claim 13).")  # fmt: skip
        return ctx

    # --- team_running ------------------------------------------------------------------------

    def team_running(self, start: str | float | None = None, end: str | float | None = None
                     ) -> dict[str, Any]:  # fmt: skip
        """Both teams' running per ball-in-play minute, with and without the ball (G5), over a
        window (default the whole match) and in 15-min blocks, and where it happened: per
        situation of play (``SITUATIONS``), metres above 5.5 m/s, ball-in-play minutes, metres
        per minute of that situation (G5) and shares. Measured, never "who is more tired"
        (claim 35)."""
        m = self.m
        a = parse_time(start) if start is not None else (1, 0.0)
        b = (
            parse_time(end)
            if end is not None
            else (max(m.durations), m.durations[max(m.durations)])
        )
        src = "signals.players[].series.speed (outfield) and tracking ball_status, possession_team"

        def pack(r: dict) -> dict:
            return {team: {
                "hsr_per_in_play_min": q(x["hsr"], HSR_TEAM, src, 0),
                "hsr_per_min_with_ball": q(x["hsr_with_ball"], HSR_WITH, src,
                                           0),
                "hsr_per_min_without_ball": q(x["hsr_without_ball"], HSR_WITHOUT, src, 0),
                "distance_per_in_play_min": q(x["dist"], DIST_TEAM, src, 0),
                "possession": q(x["possession"], "share of ball-in-play time", src),
            } for team, x in r.items()}  # fmt: skip

        blocks = []
        for per, lo, hi in m.blocks():
            if (per, hi) <= a or (per, lo) >= b:
                continue
            r = m.team_rates(per, lo, hi)
            split = situation_split([m.team_situations(per, lo, hi)])
            blocks.append({"from": m.when(per, lo)["clock"], "to": m.when(per, hi)["clock"],
                           "period": per, "teams": pack(r), "situations": split})  # fmt: skip
        totals = {team: {"hsr": 0.0, "hsr_with_ball": 0.0, "hsr_without_ball": 0.0, "dist": 0.0}
                  for team in m.teams}  # fmt: skip
        window, spans = {}, []
        for per in m.durations:
            lo = a[1] if per == a[0] else (0.0 if per > a[0] else None)
            hi = b[1] if per == b[0] else (m.durations[per] if per < b[0] else None)
            if lo is None or hi is None or hi <= lo:
                continue
            window[per] = m.team_rates(per, lo, hi)
            spans.append(m.team_situations(per, lo, hi))
        for team in totals:  # weighted by ball-in-play time
            w = sum(r[team]["in_play_s"] for r in window.values()) or 1.0
            for k in totals[team]:
                vals = [(r[team][k], r[team]["in_play_s"]) for r in window.values()
                        if r[team][k] == r[team][k]]  # fmt: skip
                totals[team][k] = sum(v * n for v, n in vals) / max(sum(n for _, n in vals), 1)
            totals[team]["possession"] = sum(r[team]["possession"] * r[team]["in_play_s"]
                                             for r in window.values()) / w  # fmt: skip
        return {"window": [m.when(*a)["clock"], m.when(*b)["clock"]], "teams": pack(totals),
                "situations": situation_split(spans), "blocks": blocks,
                "note": "Team totals of the outfield players per minute of that phase (G5). Both "
                        "teams' running rises and falls together (claim 9a); who is more tired is "
                        "not measurable from positions (claim 35). Situations come from "
                        "possession and the ball's position only: where the running happened, "
                        "never why (claim 38)."}  # fmt: skip

    # --- find_moments ------------------------------------------------------------------------

    def find_moments(self, kind: str, limit: int = 10, player: str | None = None) -> dict:
        """Story moments, ranked (best first)."""
        if kind not in MOMENT_KINDS:
            return {"error": f"unknown kind {kind!r}", "kinds": list(MOMENT_KINDS)}
        found = getattr(self, f"_moments_{kind}")()
        if player:
            pid = self.m.player(player)["id"]
            found = [x for x in found if x["player"] and x["player"]["id"] == pid]
        found.sort(key=lambda x: -x["score"])
        for r, x in enumerate(found, start=1):
            x["rank"] = r
        what, claims = MOMENT_KINDS[kind]
        return {"kind": kind, "what": what, "claims": claims, "count": len(found),
                "moments": found[:limit]}  # fmt: skip

    def _moment(self, kind, pid, period, t, score, facts, why, claims=None) -> dict[str, Any]:
        return {
            "id": f"{kind}:{pid}:{period}:{int(t)}", "kind": kind,
            **self.m.when(period, t),
            "player": self.m.players[pid], "score": round(float(score), 3),
            "facts": facts, "claims": MOMENT_KINDS[kind][1] if claims is None else claims,
            "why": why,
        }  # fmt: skip

    def _team_moment(self, team, period, t, score, facts, why, claims=None) -> dict[str, Any]:
        info = self.m.teams[team]
        other = next(t for k, t in self.m.teams.items() if k != team)
        return {
            "id": f"tug_of_war:{team}:{period}:{int(t)}", "kind": "tug_of_war",
            **self.m.when(period, t),
            "player": None, "team": {"id": team, "name": info.name},
            "opponent": {"id": other.id, "name": other.name},
            "score": round(float(score), 3), "facts": facts,
            "claims": MOMENT_KINDS["tug_of_war"][1] if claims is None else claims, "why": why,
        }  # fmt: skip

    def _moments_tug_of_war(self) -> list[dict]:
        m, out = self.m, []
        src = "signals.players[].series.speed (outfield) and tracking ball_status, possession_team"
        first: dict[str, float] = {}
        widest = 0.0  # the widest gap so far (signed, home minus away), until it closes
        for per, lo, hi in m.blocks():
            r = m.team_rates(per, lo, hi)
            if min(x["in_play_s"] for x in r.values()) < MIN_IN_PLAY_S:
                continue
            home, away = r["home"]["hsr"], r["away"]["hsr"]
            for team in r:
                first.setdefault(team, r[team]["hsr"])
            gap = pct(home, away)
            if not gap == gap:
                continue
            before = widest
            closed = abs(before) >= TEAM_GAP and abs(gap) < GAP_CLOSED
            widest = 0.0 if closed else (gap if abs(gap) > abs(widest) else widest)
            if abs(gap) < TEAM_GAP and not closed:
                continue
            lead = ("home" if before > 0 else "away") if closed else ("home" if gap > 0 else "away")
            other = "away" if lead == "home" else "home"
            t = hi - 1.0
            facts = {
                "block": f"{m.when(per, lo)['clock']}–{m.when(per, hi)['clock']}",
                "team_hsr_per_in_play_min": q(r[lead]["hsr"], HSR_TEAM, src, 0),
                "opponent_hsr_per_in_play_min": q(r[other]["hsr"], HSR_TEAM, src, 0),
                "vs_opponent": q(
                    pct(r[lead]["hsr"], r[other]["hsr"]),
                    "% above (+) or below (−) the opponent in this block",
                    src,
                    0,
                ),
                "team_vs_own_first_15": q(
                    pct(r[lead]["hsr"], first[lead]),
                    "% above (+) or below (−) his team's first 15 min",
                    src,
                    0,
                ),
                "opponent_vs_own_first_15": q(
                    pct(r[other]["hsr"], first[other]),
                    "% above (+) or below (−) their first 15 min",
                    src,
                    0,
                ),
                "team_possession": q(r[lead]["possession"], "share of ball-in-play time", src),
                "team_hsr_per_min_without_ball": q(
                    r[lead]["hsr_without_ball"], HSR_WITHOUT, src, 0
                ),
                "team_hsr_per_min_with_ball": q(r[lead]["hsr_with_ball"], HSR_WITH, src, 0),
                "score": m.score(per, t),
                "pattern": "gap closed" if closed else "ran harder",
            }
            facts |= self._split_facts(m.team_situations(per, lo, hi), lead, other)
            if closed:
                facts["earlier_gap_vs_opponent"] = q(
                    abs(before), "% (the widest gap earlier, before it closed)", src, 0
                )
            score = abs(gap) / 100.0 + (1.0 if closed else 0.0)
            why = (
                "the gap in running between the teams has closed"
                if closed
                else "one team ran much harder per ball-in-play minute"
            )
            last = per == max(m.durations) and hi >= m.durations[per]
            claims = [c for c in MOMENT_KINDS["tug_of_war"][1] if c != "7" or last]
            claims.insert(0, "4")  # where the running came; claim 4's first sentence
            out.append(self._team_moment(lead, per, t, score, facts, why, claims))
        return out

    @staticmethod
    def _split_facts(sit: dict, lead: str, other: str) -> dict[str, Any]:
        """Where a team moment's running happened: the share that came in the first
        10 s after the ball changed hands (either way), in what share of the time, and metres per
        minute of each situation (G5). Measured: situations, never purposes (claims 38, 39)."""

        def rate(x: dict, keys) -> float:
            n = sum(x[k]["in_play_s"] for k in keys)
            return sum(x[k]["hsr"] for k in keys) / n * 60.0 if n else float("nan")

        def share(x: dict, field: str) -> float:
            tot = sum(v[field] for v in x.values())
            return 100.0 * sum(x[k][field] for k in CHANGED_HANDS) / tot if tot else float("nan")

        rest = [k for k in SITUATIONS if k != "after_losing"]
        per_min = "m of high-speed running per minute of that situation, team total"
        return {
            "team_hsr_share_after_ball_changed_hands": q(
                share(sit[lead], "hsr"), "% of the team's high-speed running in this block that "
                "came in the first 10 s after the ball changed hands (either way)", SIT_SRC, 0),
            "opponent_hsr_share_after_ball_changed_hands": q(
                share(sit[other], "hsr"), "% of the opponents' high-speed running in this block "
                "that came in the first 10 s after the ball changed hands", SIT_SRC, 0),
            "time_share_after_ball_changed_hands": q(
                share(sit[lead], "in_play_s"), "% of this block's ball-in-play time that was in "
                "the first 10 s after the ball changed hands", SIT_SRC, 0),
            "team_hsr_per_min_after_losing": q(rate(sit[lead], ["after_losing"]),
                                               per_min + " (first 10 s after losing the ball)",
                                               SIT_SRC, 0),
            "team_hsr_per_min_after_winning": q(rate(sit[lead], ["after_winning"]),
                                                per_min + " (first 10 s after winning the ball)",
                                                SIT_SRC, 0),
            "team_hsr_per_min_rest": q(rate(sit[lead], rest), per_min + " (the rest of the time "
                                       "the ball was in play, after winning it included)",
                                       SIT_SRC, 0),
        }  # fmt: skip

    def _moments_flat_out(self) -> list[dict]:
        m, out = self.m, []
        sig = "signals.players[].series.speed (fastest second)"
        found = []
        speeds = []  # every outfield player's (video time, speed), for "fastest of anyone"
        for pid, s in m.series.items():
            info = m.players[pid]
            if info["position"] == "GK":
                continue
            v = np.where(s.cols["speed"] <= MAX_PLAUSIBLE_SPEED, s.cols["speed"], 0.0)
            top_before = np.maximum.accumulate(np.r_[0.0, v[:-1]])
            video = s.t + np.where(s.period == 2, m.durations[1], 0.0)
            speeds.append((video, v))
            hot = (
                (v >= FLAT_OUT_SHARE * top_before)
                & (top_before >= FLAT_OUT_MIN_SPEED)
                & (np.arange(len(v)) >= SO_FAR_MIN_S)  # seconds on the pitch
            )
            late_top = v[video < 75 * 60].max() if (video < 75 * 60).any() else 0.0
            for a, b in runs(hot):
                i = a + int(np.argmax(v[a : b + 1]))
                found.append((float(video[i]), pid, i, float(v[i]), float(top_before[a]), late_top))
        found.sort()
        for vid, pid, i, peak, top, late_top in found:
            s, info = m.series[pid], m.players[pid]
            per, t = int(s.period[i]), float(s.t[i])
            # Fastest of anyone so far: against every outfield player's every second before this
            # one, not only the earlier flat-out moments (a run at 10:48 was called
            # the fastest when another player had been faster outside any flat-out moment).
            before = [float(sp[tv < vid].max()) for tv, sp in speeds if (tv < vid).any()]
            fastest = peak >= max(before, default=0.0) + NEW_BEST_MARGIN
            facts = {
                "peak_speed": q(peak, "m/s", sig, 1),
                "peak_speed_kmh": q(peak * 3.6, "km/h", sig, 0),
                "top_speed_so_far": q(top, "m/s (his fastest second before this run)", sig, 1),
                "his_fastest_so_far": peak >= top + NEW_BEST_MARGIN,
                "fastest_of_any_player_so_far": fastest,
                "published_match_peak_for_position": q(MATCH_PEAK[info["position"]], "m/s, "
                                                       "mean match peak for his position",
                                                       "SilvaH2025, Table 1 (Brazil, GNSS)", 2),
            }  # fmt: skip
            if (peak < top + NEW_BEST_MARGIN and not fastest and vid < 75 * 60
                    and peak < FLAT_OUT_EARLY_SHARE * top):  # fmt: skip
                continue
            if peak < top + NEW_BEST_MARGIN:  # a new best is his fastest so far, not "108%"
                facts["share_of_top_speed"] = q(100.0 * peak / top, "% of his top speed so far",
                                                sig, 0)  # fmt: skip
            if vid >= 75 * 60 and late_top > 0:
                facts["share_of_top_before_75"] = q(
                    100.0 * peak / late_top,
                    "% of his fastest second before the 75th minute",
                    sig,
                    0,
                )
            direction = self._direction(pid, per, t)
            if direction:
                facts["running"] = direction
            score = (
                peak / 10.0
                + 0.5 * (peak >= top + NEW_BEST_MARGIN)
                + 1.0 * fastest
                + 0.3 * (vid >= 75 * 60)
            )
            late = "share_of_top_before_75" in facts
            claims = [c for c in MOMENT_KINDS["flat_out"][1] if c != "36" or late]
            out.append(
                self._moment(
                    "flat_out",
                    pid,
                    per,
                    t,
                    score,
                    facts,
                    "a run at or near his top speed so far",
                    claims,
                )
            )
        return out

    def _direction(self, pid: str, period: int, t: float) -> str | None:
        """What the run looked like (measured): towards which goal, and who had the ball."""
        m = self.m
        k = m.second(period, t)
        xy = m.xy[period][:, m.col[pid]]
        a, b = max(k - 2, 0), min(k + 1, len(xy) - 1)
        if np.isnan(xy[a, 0]) or np.isnan(xy[b, 0]):
            return None
        team = m.players[pid]["team"]
        forward = m.teams[team].attacks_positive_x_in_period_1 == (period == 1)
        dx = (xy[b, 0] - xy[a, 0]) * (1 if forward else -1)
        holder = m.possession[period][k]
        if dx < 0 and holder and holder != team:
            return "towards his own goal while the opponents had the ball"
        if dx > 0 and holder == team:
            return "towards the opponents' goal with his team on the ball"
        return None

    def _spells(self, pid: str) -> list[tuple[int, int]]:
        s = self.m.series[pid]
        out = []
        for per in (1, 2):
            rows = np.flatnonzero(s.period == per)
            for a, b in runs(s.cols["red_zone"][rows].astype(bool)):
                out.append((int(rows[a]), int(rows[b])))
        return out

    def _moments_red_zone(self) -> list[dict]:
        m, out = self.m, []
        sig = "signals.players[].series."
        for pid, s in m.series.items():
            if m.players[pid]["position"] == "GK":
                continue
            spells = self._spells(pid)
            times = episodes(spells, s)
            for n, (a, b) in enumerate(spells, start=1):
                peak = float(s.cols["hsr_1min"][a : b + 1].max())
                i = a + int(np.argmax(s.cols["hsr_1min"][a : b + 1]))
                if i < SO_FAR_MIN_S:  # seconds on the pitch
                    continue
                low = float(s.cols["battery"][a : b + 1].min())
                facts = {
                    "hardest_minutes_count": q(
                        times[n - 1],
                        "times at his hardest minutes so far, this one included",
                        sig + "red_zone",
                    ),
                    "duration": q(float(s.t[b] - s.t[a] + 1), "s", sig + "red_zone", 0),
                    "peak_1min_hsr": q(peak, "m in 1 min", sig + "hsr_1min", 0),
                    "published_mean_peak_1min": q(
                        62.0,
                        "m/min, mean 1-min peak of outfield players (all positions)",
                        "Leifsson2024, Table 1",
                        0,
                    ),  # fmt: skip
                    "typical_pro_battery_low": q(
                        low, "share of a typical professional's short-term reserve", sig + "battery"
                    ),
                    "low_chance_max": q(
                        float(s.cols["low_chance"][a : b + 1].max()), "chance", sig + "low_chance"
                    ),
                }
                if i >= MIN_AVERAGE_S:
                    avg = m.hsr_avg_so_far(pid)[i]
                    facts["match_average_per_min"] = q(avg, "m/min", HSR_SRC, 1)
                recent = [
                    x
                    for x in self._spells(pid)[: n - 1]
                    if s.period[x[1]] == s.period[a] and s.t[a] - s.t[x[1]] <= 300
                ]
                facts["hardest_minutes_in_last_5min"] = q(
                    len({times[spells.index(x)] for x in recent} | {times[n - 1]}),
                    "times at his hardest minutes in the last 5 min",
                    sig + "red_zone",
                )
                score = peak / 62.0 + (1.0 - low) + 0.3 * len(recent)
                long = s.t[b] - s.t[a] + 1 >= LONG_SPELL_S
                claims = [c for c in MOMENT_KINDS["red_zone"][1] if c != "1" or long]
                out.append(
                    self._moment(
                        "red_zone",
                        pid,
                        int(s.period[i]),
                        float(s.t[i]),
                        score,
                        facts,
                        "high-speed running at his peak",
                        claims,
                    )
                )
        return out

    def _moments_exposed_on_turnover(self) -> list[dict]:
        m, out = self.m, []
        seen: set[int] = set()
        by_poss: dict[int, list[Event]] = {}
        for e in m.events:
            if e.possession_id is not None:
                by_poss.setdefault(e.possession_id, []).append(e)
        sig = "signals.players[].series."
        exposed: dict[str, int] = {}
        for e in m.events:
            pid_ = e.possession_id
            if e.phase is None or e.phase.value != "positive_transition" or pid_ in seen:
                continue
            seen.add(pid_)
            lost = "away" if e.team_id == "home" else "home"
            chain = by_poss.get(pid_, [])
            shot = max((x.xg or 0.0 for x in chain if x.type.value == "shot"), default=0.0)
            goal = any(x.type.value == "goal" for x in chain)
            counter_end = counter_end_t(e.t, [x.t for x in chain if x.period == e.period])
            for pid, s in m.series.items():
                info = m.players[pid]
                if info["team"] != lost or info["position"] not in DEFENDERS:
                    continue
                i = s.index(e.period, e.t)
                if i is None or s.period[i] != e.period or e.t - s.t[i] > 1.5:
                    continue
                if not (s.cols["post_peak"][i] or s.cols["red_zone"][i]):
                    continue
                # "just after his hardest minutes so far" is a "so far" claim (the
                # favourite's 9:14 turnover came 554 s into his match; no exception without one)
                if i < SO_FAR_MIN_S:  # seconds on the pitch
                    continue
                spells = self._spells(pid)
                j = m.col[pid]
                d0 = m.gap_at(e.period, e.t, j)
                read_t = min(counter_end + CLIP_AFTER_S, m.durations[e.period] - 0.1)
                d8 = m.gap_at(e.period, min(e.t + 8.0, len(m.alive[e.period]) - 1.0), j)
                spd = s.cols["speed"][i + 1 : i + 9]
                nearest = m.nearest_ball(e.period, e.t, max(counter_end, e.t + 1.0), j)
                nearest = d0 if nearest != nearest else nearest
                # A turnover the clip can show: the counter came his way or ended in a shot
                # (one clip showed him 34 m from a counter that went elsewhere).
                if nearest > COUNTER_NEAR_M and shot == 0.0 and not goal:
                    continue
                facts = {
                    "distance_to_ball_at_turnover": q(
                        d0, "m", "tracking players[].x,y and ball", 0
                    ),
                    "distance_to_ball_8s_later": q(d8, "m", "tracking players[].x,y and ball", 0),
                    "mean_speed_next_8s": q(
                        float(spd.mean()) if len(spd) else 0.0, "m/s", sig + "speed", 1
                    ),
                    "hardest_minutes_so_far": q(
                        max(
                            (
                                n
                                for x, n in zip(spells, episodes(spells, s), strict=True)
                                if x[0] <= i
                            ),
                            default=0,
                        ),  # fmt: skip
                        "times at his hardest minutes so far",
                        sig + "red_zone",
                    ),
                    "last_5min_hsr": q(s.cols["hsr_5min"][i], "m", sig + "hsr_5min", 0),
                    "typical_pro_battery": q(
                        s.cols["battery"][s.index(e.period, read_t) or i],
                        "share of a typical professional's short-term reserve, at the end of "
                        "the counter",
                        sig + "battery",
                    ),
                    "low_chance": q(s.cols["low_chance"][i], "chance", sig + "low_chance"),
                    "counter_xg": q(shot, "xG", "events.jsonl shot xg in this possession"),
                    "counter_goal": goal,
                    "counter_seconds": q(
                        counter_end - e.t, "s", "events.jsonl this possession, at most 15 s", 0
                    ),
                    "ball_nearest_him_in_counter": q(
                        nearest, "m", "tracking players[].x,y and ball, every frame", 0
                    ),
                    "window_after_turnover": q(8, "s", "tracking, 8 s after the turnover"),
                    "losing_team": lost,
                }
                exposed[pid] = exposed.get(pid, 0) + 1
                facts["times_exposed_so_far"] = q(
                    exposed[pid], "turnovers so far while he was in or just after his hardest "
                    "minutes so far, this one included", "events.jsonl positive_transition and "
                    "signals.players[].series.red_zone, post_peak",
                )  # fmt: skip
                # Claim 4 ("losing the ball forces the hardest running of the game") is offered
                # only if he did run hard after it: next to a player who jogged it read as being
                # about him, and the clip showed otherwise.
                ran_hard = len(spd) > 0 and float(spd.max()) >= EP.HI_SPEED
                claims = MOMENT_KINDS["exposed_on_turnover"][1]
                claims = claims if ran_hard else [c for c in claims if c != "4"]
                score = (
                    0.5 * (exposed[pid] - 1)  # the same defender exposed again: the story
                    + 2.0 * goal
                    + 2.0 * shot
                    + float(s.cols["low_chance"][i]) * 3
                    + (0.5 if s.cols["red_zone"][i] else 0.0)
                    + max(d8 - d0, 0.0) / 10.0
                    + (1.0 if nearest <= COUNTER_NEAR_M else 0.0)
                )
                mo = self._moment(
                    "exposed_on_turnover",
                    pid,
                    e.period,
                    e.t,
                    score,
                    facts,
                    "his team lost the ball just after his hardest minutes so far",
                    claims,
                )
                out.append(mo | {"read_t": read_t})  # where brief reads his battery
        return out

    def _moments_second_wind(self) -> list[dict]:
        m, out = self.m, []
        lo, hi = SECOND_WIND_WINDOW_S
        for pid, s in m.series.items():
            if m.players[pid]["position"] == "GK":
                continue
            avg = m.hsr_avg_so_far(pid)
            rate2 = s.cols["hsr_2min"] / 2.0
            for a, b in self._spells(pid):
                per, end = s.period[b], s.t[b]
                after = np.flatnonzero((s.period == per) & (s.t >= end + lo) & (s.t <= end + hi))
                calm = after[~s.cols["post_peak"][after].astype(bool)]  # post-peak window over
                back = [i for i in calm if rate2[i] >= avg[b] >= MIN_HSR_PER_MIN]
                if not back:
                    continue
                i = back[0]
                facts = {
                    "minutes_after_hardest_minutes": q(
                        (s.t[i] - end) / 60.0, "min", "signals.players[].series.red_zone", 1
                    ),
                    "last_2min_hsr_per_min": q(
                        rate2[i], "m/min", "signals.players[].series.hsr_2min / 2", 1
                    ),
                    "match_average_per_min": q(avg[b], "m/min", HSR_SRC, 1),
                    "vs_match_average": q(pct(rate2[i], avg[b]), VS_AVG, HSR_SRC, 0),
                }
                peak = float(s.cols["hsr_1min"][a : b + 1].max())
                facts["hardest_minutes_peak_1min_hsr"] = q(
                    peak, "m in 1 min", "signals.players[].series.hsr_1min", 0
                )
                dur = float(s.t[b] - s.t[a] + 1)
                facts["hardest_minutes_duration"] = q(
                    dur, "s", "signals.players[].series.red_zone", 0
                )
                score = peak / 62.0 + 0.5 * (hi - (s.t[i] - end)) / hi
                claims = [c for c in MOMENT_KINDS["second_wind"][1]
                          if c != "1" or dur >= LONG_SPELL_S]  # fmt: skip
                out.append(
                    self._moment(
                        "second_wind",
                        pid,
                        int(per),
                        float(s.t[i]),
                        score,
                        facts,
                        "back to his normal high-speed running",
                        claims,
                    )
                )
        return out

    def _moments_fresh_legs(self) -> list[dict]:
        m, out = self.m, []
        for s_ in m.metadata.substitutions:
            on, off = s_.player_in, s_.player_out
            if on not in m.series or off not in m.series:
                continue
            so = m.series[on]
            hsr_on = m.hsr_per_s(on)
            n = min(len(so.t), int(FRESH_WINDOW_S))
            if n < 120:
                continue
            end = (int(so.period[n - 1]), float(so.t[n - 1]))
            start = (int(so.period[0]), float(so.t[0]))
            rate_on = float(hsr_on[:n].sum()) / n * 60.0
            hsr_off = m.hsr_per_s(off)
            rate_off = float(hsr_off.sum()) / max(len(hsr_off), 60) * 60.0
            mates = []
            for pid, s in m.series.items():
                info = m.players[pid]
                if pid in (on, off) or info["team"] != s_.team_id or info["position"] == "GK":
                    continue
                w = s.span(start, end)
                if w.stop - w.start >= 0.9 * n:
                    mates.append(float(m.hsr_per_s(pid)[w].sum()) / (w.stop - w.start) * 60.0)
            team_rate = float(np.mean(mates)) if mates else float("nan")
            if team_rate > 0 and rate_on <= team_rate:
                continue  # no fresh legs: he did not out-run his team-mates
            facts = {
                "minutes_on": q(n / 60.0, "min", "signals.players[].series.t", 0),
                "sub_hsr_per_min": q(rate_on, "m/min", HSR_SRC, 1),
                "replaced_player_hsr_per_min": q(
                    rate_off, "m/min", HSR_SRC + " (his whole match)", 1
                ),
                "teammates_hsr_per_min_same_minutes": q(team_rate, "m/min", HSR_SRC, 1),
                "vs_replaced_player": q(
                    pct(rate_on, rate_off),
                    "% above (+) or below (−) the player he replaced, against that player's "
                    "own minutes on the pitch (not the same minutes)",
                    HSR_SRC,
                    0,
                ),
                "vs_teammates": q(
                    pct(rate_on, team_rate),
                    "% above (+) or below (−) his team-mates over the same minutes",
                    HSR_SRC,
                    0,
                ),
                "replaced": m.players[off]["name"],
            }
            score = rate_on / max(team_rate, 1.0) if mates else 0.0
            out.append(
                self._moment("fresh_legs", on, *end, score, facts, "a substitute's first minutes")
            )
        return out

    def _moments_not_tired_tactical(self) -> list[dict]:
        m, out = self.m, []
        for pid, s in m.series.items():
            if m.players[pid]["position"] == "GK":
                continue
            avg = m.hsr_avg_so_far(pid)
            rate5 = s.cols["hsr_5min"] / 5.0
            low = (
                (rate5 < DROP_SHARE * avg)
                & (avg >= MIN_HSR_PER_MIN)
                & (s.cols["low_chance"] < 0.05)
            )
            best = None
            for per in (1, 2):
                rows = np.flatnonzero((s.period == per) & low & (s.t >= 300))
                rows = rows[rows >= MIN_ON_S]  # his "normal" needs time on the pitch
                for i in rows[::60]:
                    ctx = self.context_at(int(per), float(s.t[i]), pid)
                    reasons = [r for r in ctx["non_fatigue_reasons"] if r["code"] in WINDOW_REASONS]
                    if not reasons:
                        continue
                    drop = 1.0 - rate5[i] / avg[i]
                    if best is None or drop > best[0]:
                        best = (drop, int(per), float(s.t[i]), i, reasons)
            if best is None:
                continue
            drop, per, t, i, reasons = best
            facts = {
                "last_5min_hsr_per_min": q(
                    rate5[i], "m/min", "signals.players[].series.hsr_5min / 5", 1
                ),
                "match_average_per_min": q(avg[i], "m/min", HSR_SRC, 1),
                "vs_match_average": q(pct(rate5[i], avg[i]), VS_AVG, HSR_SRC, 0),
                "low_chance": q(
                    s.cols["low_chance"][i], "chance", "signals.players[].series.low_chance"
                ),
                "reasons": reasons,
            }
            facts |= self._touch_facts(pid, i)
            fewer = facts["fewer_touches_than_usual"] and facts["less_ball_in_play_than_usual"]
            claims = [c for c in MOMENT_KINDS["not_tired_tactical"][1] if c != "14" or fewer]
            out.append(
                self._moment(
                    "not_tired_tactical",
                    pid,
                    per,
                    t,
                    drop + sum(WINDOW_REASONS[r["code"]] for r in reasons) + avg[i] / 20.0,
                    facts,
                    "running dropped, and something other than fatigue fits",
                    claims,
                )
            )
        return out

    def _touch_facts(self, pid: str, i: int) -> dict[str, Any]:
        """His touches in the 5 min up to his i-th second on the pitch against his match so
        far, as counts and per ball-in-play minute (claim 14 needs them)."""
        m, s = self.m, self.m.series[pid]
        per, t = int(s.period[i]), float(s.t[i])
        alive = m.in_play(pid)[: i + 1]
        window = (s.period[: i + 1] == per) & (s.t[: i + 1] > t - 300.0)
        times = [x for x in m.touches.get(pid, []) if x <= (per, t)]
        recent = sum(1 for p, x in times if p == per and x > t - 300.0)
        usual = len(times) / (i + 1) * 300.0  # per 5 min on the pitch, his match so far
        play_now, play_usual = alive[window].mean(), alive.mean()
        src = "events.jsonl (" + ", ".join(TOUCH_TYPES) + ") by player_id"
        bip = "tracking.ball_status"

        def rate(n: float, sec: float) -> float:
            return n / sec * 60.0 if sec > 0 else float("nan")

        return {
            "touches_last_5min": q(recent, "touches (his on-ball events)", src),
            "touches_per_5min_so_far": q(usual, "touches per 5 min on the pitch, his match so "
                                         "far", src, 1),
            "touches_per_in_play_min_last_5min": q(
                rate(recent, alive[window].sum()), "touches per ball-in-play minute", src, 1),
            "touches_per_in_play_min_so_far": q(
                rate(len(times), alive.sum()), "touches per ball-in-play minute, his match so far",
                src, 1),
            "in_play_last_5min": q(play_now, "share of the last 5 min with the ball in play", bip),
            "in_play_so_far": q(play_usual, "share of his minutes so far with the ball in play",
                                bip),
            "fewer_touches_than_usual": bool(recent < usual),
            "less_ball_in_play_than_usual": bool(play_now < play_usual),
        }  # fmt: skip

    # --- claim, verify -----------------------------------------------------------------------

    def claim(self, claim_id: str) -> dict[str, Any]:
        reg = verifier.register()
        for row in reg["claims"] + reg["global_rules"]:
            if row["id"] == str(claim_id):
                return row | {"source": "agents/claims.json"}
        return {"error": f"no claim {claim_id!r}"}

    def verify(
        self, sentence: str, mode: str = "fan", context: dict | None = None,
        claim_id: str | None = None,
    ) -> dict[str, Any]:  # fmt: skip
        v = verifier.verify(sentence, mode, context, claim_id)  # type: ignore[arg-type]
        return {
            "sentence": sentence,
            "ok": v.ok,
            "stage": "rules",
            "findings": [{"claim": f.claim, "message": f.message} for f in v.findings],
        }


# --- helpers ---------------------------------------------------------------------------------


def episodes(spells: list[tuple[int, int]], s) -> list[int]:
    """Which time each spell (first and last index into series ``s``) is, counting spells less
    than EPISODE_GAP_S apart in a half as one."""
    out, n, prev = [], 0, None
    for a, b in spells:
        if prev is None or s.period[a] != s.period[prev] or s.t[a] - s.t[prev] > EPISODE_GAP_S:
            n += 1
        out.append(n)
        prev = b
    return out


def runs(flag: np.ndarray) -> list[tuple[int, int]]:
    """(first, last) index of each run of True."""
    if not len(flag):
        return []
    d = np.diff(np.r_[0, flag.astype(int), 0])
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1, strict=True))


SIT_SRC = (
    "signals.players[].series.speed (outfield) and tracking ball_status, possession_team, ball x"
)


def situation_split(spans: list[dict[str, dict[str, dict]]]) -> dict[str, dict[str, dict]]:
    """``MatchData.team_situations`` of one or more spans added up, per team and situation:
    metres, ball-in-play minutes, metres per minute of that situation and the shares."""
    out = {}
    for team in spans[0] if spans else {}:
        tot = {k: [sum(s[team][k][x] for s in spans) for x in ("hsr", "in_play_s")]
               for k in SITUATIONS}  # fmt: skip
        hsr, sec = sum(v[0] for v in tot.values()), sum(v[1] for v in tot.values())
        out[team] = {k: {
            "what": SITUATIONS[k],
            "hsr": q(h, "m above 5.5 m/s, team total", SIT_SRC, 0),
            "in_play_min": q(n / 60.0, "min of ball in play", SIT_SRC, 1),
            "hsr_per_min": q(h / n * 60.0 if n else float("nan"),
                             "m of high-speed running per minute of this situation, team total",
                             SIT_SRC, 0),
            "share_of_hsr": q(100.0 * h / hsr if hsr else float("nan"),
                              "% of the team's high-speed running in this window", SIT_SRC, 0),
            "share_of_time": q(100.0 * n / sec if sec else float("nan"),
                               "% of the ball-in-play time in this window", SIT_SRC, 0),
        } for k, (h, n) in tot.items()}  # fmt: skip
    return out


def pct(x: float, base: float) -> float:
    return 100.0 * (x / base - 1.0) if base > 0 else float("nan")


def signals_capacity(m: MatchData, pid: str, name: str) -> float:
    for ps in m.signals.players:
        if ps.player_id == pid:
            return getattr(ps.capacity, name).value
    return float("nan")


def first_half_load(m: MatchData, pid: str) -> float | None:
    """His energy at half-time vs the median outfield starter's (starters only)."""

    def at_half(p: str) -> float | None:
        s = m.series[p]
        rows = np.flatnonzero(s.period == 1)
        return float(s.cols["energy"][rows[-1]]) if len(rows) else None

    if not m.players[pid]["starter"]:
        return None
    mine = at_half(pid)
    others = [
        x for p, info in m.players.items()
        if info["starter"] and info["position"] != "GK" and p in m.series
        and (x := at_half(p)) is not None
    ]  # fmt: skip
    if mine is None or not others or float(np.median(others)) <= 0.0:
        return None
    return mine / float(np.median(others))
