"""The explanation feed (BUILD_PLAN "Thu 22"): a match folder in, a verified, timestamped
``feed.json`` out, so the overlay and a video can sync to it (PLAN §4).

``python -m runningbattery.agents.feed <match folder> [--offline] [--favourite H04]``

Four agents, each with a plain-code fallback so the feed never has a gap:
1. **Tactical** picks the moments: an Agent Framework agent on Foundry with the MCP server
   (``agents.mcp_server``) as its only tool; offline, the best-ranked moments of each kind,
   spread over the match.
2. **Narrator** writes one sentence per moment from the claims register's wordings and the
   moment's facts; offline (or as the fallback for a blocked sentence), fixed templates.
3. **Personalization** (a thin step, decision 6): fan or analyst wording, and a favourite
   player's moments first (his and those of the player who replaced him, in code).
4. **Verifier** checks every sentence: the rules, then the LLM pass (``agents.llm_verifier``).
   A blocked sentence is replaced by the Verifier's rewrite if that passes both checks, else by
   the template, else left out. Blocked sentences stay in the feed with ``shown: false``.

Then plain code makes sure of two things the prompts ask for (decision 25): a team moment says
how the two teams compare (``MUST_SAY``; else the verified template line is added; decision 31
adds a substitute against his team-mates and, for the favourite caught on the break, what his
running would leave a typical professional), and each
general register sentence is shown at most ``MAX_GENERAL`` times per mode (later ones stay in
the feed with ``verdict: "repeat"``, ``shown: false``); a moment left with no line gets its
verified template line.

Each entry: ``t`` and ``period`` (seconds since that period's kick-off), ``clock``, ``video_s``,
``player``, ``kind``, ``sentence``, ``claim`` (register id, or ``fact`` for a measured fact),
``sources`` (citation keys and data fields), ``mode``, ``verdict`` (pass, rewritten, fallback,
template, repeat, blocked) and what the Verifier found.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from runningbattery.agents import verifier
from runningbattery.agents.llm_verifier import FullVerdict, verify_full
from runningbattery.agents.tools import MOMENT_KINDS, TEAM_KINDS, MatchTools

FEED = "feed.json"
MODES = ("fan", "analyst")
PER_KIND = {"tug_of_war": 2, "red_zone": 3, "exposed_on_turnover": 3, "flat_out": 2,
            "second_wind": 2, "fresh_legs": 2, "not_tired_tactical": 2}  # fmt: skip
MIN_GAP_S = 180.0  # moments at least 3 min apart (our assumption, for a readable feed)
MAX_PER_PLAYER = 3
MAX_GENERAL = 2  # each general register sentence at most twice per mode (decision 25)
# Register claims about this player or moment; every other claim is a general finding.
SPECIFIC = {"5", "8", "10", "11", "12", "13", "14", "17", "19", "19c"}
# A favourite's moments the feed should hold, by kind, in this order (decision 25): the first
# FAVOURITE_ARC kinds always (exposed on the turnover, the substitute who came on for him), the
# rest until he has FAVOURITE_MIN.
FAVOURITE_KINDS = ("exposed_on_turnover", "fresh_legs", "red_zone", "second_wind", "flat_out",
                   "not_tired_tactical")  # fmt: skip
FAVOURITE_ARC = 2
FAVOURITE_MIN = 4
# What a team moment's lines must say (decision 25): the comparison between the two teams.
MUST_SAY = {
    "ran harder": r"\d+\s*%\s*more\b[^.]*\bthan\b",
    "gap closed": r"\bgap\b[^.]*\b(closed|gone)\b|\blevel\b|\bthe same\b",
}
# Decision 31: the point of a fresh-legs moment is the comparison with his team-mates, and the
# favourite's caught-on-the-break moment says what his running would cost (claim 11); the
# Narrator left both out of a regenerated feed.
FRESH_LEGS_SAYS = r"\bteam-?mates\b"
FAVOURITE_EXPOSED_SAYS = r"\btypical professional\b"
ORDINAL = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
           7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth"}  # fmt: skip


# --- Tactical --------------------------------------------------------------------------------


def candidates(tools: MatchTools, limit: int = 8, players: set[str] = frozenset()) -> dict:
    """Every ranked moment the Tactical agent may pick, by id; a favourite's own moments too."""
    out = {}
    for kind in MOMENT_KINDS:
        for mo in tools.find_moments(kind, limit)["moments"]:
            out[mo["id"]] = mo
        for pid in sorted(players):
            if kind not in TEAM_KINDS:
                for mo in tools.find_moments(kind, 3, player=pid)["moments"]:
                    out.setdefault(mo["id"], mo)
    return out


def related(tools: MatchTools, favourite: str | None) -> set[str]:
    """The favourite and the player who came on for him, if any."""
    if not favourite:
        return set()
    off = tools.m.sub_off.get(favourite)
    return {favourite} | ({off[2]} if off else set())


def ensure_favourite(picked: list[str], found: dict[str, dict], ids: set[str]) -> list[str]:
    """Add the favourite's (and his replacement's) best moment of each kind in FAVOURITE_KINDS
    that the pick left out (the first FAVOURITE_ARC kinds always, the rest until they have
    FAVOURITE_MIN), at least a minute from the other player moments. For the first
    FAVOURITE_ARC kinds his best-ranked moment is added even when another of that kind was
    picked: the Tactical agent once picked his second turnover and left out the third, the
    story's (decision 30)."""
    chosen = [found[i] for i in picked]
    mine = [m for m in chosen if who(m) in ids]
    for n, kind in enumerate(FAVOURITE_KINDS):
        if n >= FAVOURITE_ARC and len(mine) >= FAVOURITE_MIN:
            break
        have = [m for m in mine if m["kind"] == kind]
        best = max((m for m in found.values() if m["kind"] == kind and who(m) in ids),
                   key=lambda m: m["score"], default=None)  # fmt: skip
        if have and (n >= FAVOURITE_ARC or best is None or best in have):
            continue
        for mo in sorted(found.values(), key=lambda m: -m["score"]):
            if (
                mo["kind"] == kind
                and who(mo) in ids
                # A minute from the other player moments; a team moment at a block's end may be
                # nearer (its clip is a different picture; decision 37: all of the favourite's
                # best turnovers fell within 60 s of one and his story dropped out).
                and all(
                    abs(mo["video_s"] - c["video_s"]) >= 60.0 for c in chosen if c.get("player")
                )
            ):
                chosen.append(mo)
                mine.append(mo)
                break
    return [m["id"] for m in sorted(chosen, key=lambda m: m["video_s"])]


def who(mo: dict) -> str:
    """A moment's subject: the player's id, or "team:<id>" for a team moment."""
    return mo["player"]["id"] if mo.get("player") else f"team:{mo['team']['id']}"


def pick_offline(found: dict[str, dict], favourite: set[str] = frozenset()) -> list[str]:
    """The best-ranked moments of each kind, at least MIN_GAP_S apart and at most
    MAX_PER_PLAYER per player; a favourite player's moments (and his replacement's) first."""
    chosen: list[dict] = []
    per_player: dict[str, int] = {}

    def fits(mo: dict) -> bool:
        if per_player.get(who(mo), 0) >= MAX_PER_PLAYER:
            return False
        return all(abs(mo["video_s"] - c["video_s"]) >= MIN_GAP_S for c in chosen)

    order = sorted(found.values(), key=lambda m: (who(m) not in favourite, m["rank"]))
    for kind, n in PER_KIND.items():
        taken = 0
        for mo in order:
            if mo["kind"] == kind and taken < n and fits(mo):
                chosen.append(mo)
                per_player[who(mo)] = per_player.get(who(mo), 0) + 1
                taken += 1
    return [m["id"] for m in sorted(chosen, key=lambda m: m["video_s"])]


class Pick(BaseModel):
    moment_id: str
    why: str


class Picks(BaseModel):
    picks: list[Pick]


TACTICAL = """You are the Tactical analyst of Running Battery. Using only the tools, pick the 10 to
14 moments of this synthetic match that best tell the story of who did the most hard running and
when it cost them. Call match_summary once, then find_moments for each kind (red_zone,
exposed_on_turnover, second_wind, fresh_legs, not_tired_tactical, tug_of_war, flat_out) with
limit 6; team_running shows how the two teams' running compares. Prefer variety (every kind if
it exists, several players and both teams), moments at least 3 minutes apart, and the story arc:
- a team that ran much harder than the other (tug_of_war "ran harder") and, if found, the moment
  the gap closed (tug_of_war "gap closed"): pick both;
- a defender exposed on turnovers again and again: prefer his second or third exposure
  (times_exposed_so_far), and the substitute who came on for him (fresh_legs) if there is one;
- a drop that is tactical rather than fatigue, a second wind, the fastest runs.
{favourite}Return the moment ids exactly as the tools gave them, in match order, each with a
one-line reason."""


async def pick_llm(folder: Path, found: dict[str, dict], favourite: str | None) -> list[str]:
    from agent_framework import MCPStdioTool

    from runningbattery.agents import foundry

    fav = (
        f"The viewer's favourite player is {favourite}: include his moments, and those of the "
        "player who came on for him (find_moments with player). "
        if favourite
        else ""
    )
    server = MCPStdioTool(
        name="running-battery", command=sys.executable,
        args=["-m", "runningbattery.agents.mcp_server", str(folder)],
    )  # fmt: skip
    async with server:
        agent = foundry.agent("Tactical", TACTICAL.format(favourite=fav), "main", tools=server)
        r = await agent.run("Pick the moments.", options={"response_format": Picks})
    ids = [p.moment_id for p in (r.value.picks if r.value else []) if p.moment_id in found]
    return sorted(dict.fromkeys(ids), key=lambda i: found[i]["video_s"])


# --- Facts and context -----------------------------------------------------------------------


def brief(tools: MatchTools, mo: dict) -> dict[str, Any]:
    """What the Narrator and the Verifier get for one moment: its facts, the player's signals
    over the 5 min before it, the context and the claims it may use."""
    per, t = mo["period"], mo["t"]
    pid = mo["player"]["id"] if mo.get("player") else None
    ctx = tools.context_at(per, t, pid, None if pid else mo["team"]["id"])
    end = ctx["clock"]
    start = max(t - 300.0, 0.0)
    sig = tools.player_signals(pid, _clock(tools, per, start), _clock(tools, per, t)) if pid else {}
    facts = dict(mo["facts"])
    if sig.get("on_pitch"):
        b, h = sig["battery"], sig["hsr"]
        facts |= {
            "typical_pro_battery_now": b["typical_pro_at_end"],
            "typical_pro_battery_band": b["band_10_90_at_end"],
            "lowest_typical_pro_battery_so_far": b["lowest_in_match_so_far"],
            "low_chance_now": sig["low_chance"]["at_end"] if sig["low_chance"] else None,
            "energy_since_kickoff": sig["energy"]["since_kickoff"],
            "hsr_last_5min_vs_match_average": h["window_vs_match_average"],
            "hsr_threshold": h["threshold"],
        }
    claims = []
    for cid in mo["claims"]:
        row = tools.claim(cid)
        claims.append({k: row.get(k) for k in ("id", "status", "mode", "pattern", "qualifier",
                                                  "wording", "sources")})  # fmt: skip
    return {
        "moment_id": mo["id"], "kind": mo["kind"], "what": MOMENT_KINDS[mo["kind"]][0],
        "clock": end, "player": mo.get("player"), "team": mo.get("team"),
        "opponent": mo.get("opponent"), "team_names": [t.name for t in tools.m.teams.values()],
        "facts": facts,
        "non_fatigue_reasons": ctx["non_fatigue_reasons"],
        "context": {k: ctx[k] for k in ("score", "ball_in_play", "possession", "lead",
                                        "team_just_lost_ball", "team_just_won_ball",
                                        "came_on") if k in ctx},
        "claims": claims,
        "low_chance_calibration": "calibrated for a typical professional; when it says 0.1–0.2 "
        "a typical professional was short-term tired about 12% of the time (PLAN §3.3)",
    }  # fmt: skip


def _clock(tools: MatchTools, period: int, t: float) -> str:
    return tools.m.when(period, t)["clock"]


def verifier_context(b: dict) -> dict[str, Any]:
    return {"non_fatigue_reasons": b["non_fatigue_reasons"], "facts": b["facts"],
            "context": b["context"], "subject": _name(b), "team_names": b.get("team_names"),
            "claims_offered": [c["id"] for c in b["claims"]],
            "team_moment": b["kind"] in TEAM_KINDS}  # fmt: skip


def _name(b: dict) -> str:
    return b["player"]["name"] if b.get("player") else b["team"]["name"]


# --- Narrator (templates) --------------------------------------------------------------------


def _v(b: dict, key: str, scale: float = 1.0, digits: int = 0):
    x = b["facts"].get(key)
    x = x["value"] if isinstance(x, dict) else x
    if x is None or not math.isfinite(x):
        return None
    x = x * scale
    return int(round(x)) if digits == 0 else round(x, digits)


def _pro(b: dict) -> tuple[str, str] | None:
    """Claim 11's line for the moment, from typical_pro_battery_now."""
    bat = _v(b, "typical_pro_battery_now", 100)
    if bat is None:
        return None
    return ("11", f"That running would leave a typical professional at about {bat}% of their "
                  "short-term reserve, by our estimate.")  # fmt: skip


def template(b: dict, mode: str) -> list[tuple[str, str]]:
    """(claim id, sentence) for a moment, from the register's wordings and the facts."""
    name, kind = _name(b), b["kind"]
    pro = _pro(b)
    out: list[tuple[str, str] | None] = []
    if kind == "red_zone":
        n = _v(b, "hardest_minutes_count")
        peak = _v(b, "peak_1min_hsr")
        nth = ORDINAL.get(n, f"number {n}")
        if mode == "fan":
            lead = (
                f"{name}'s hardest minutes so far"
                if n == 1
                else f"For the {nth} time, {name} runs as hard as in his hardest minutes so far"
            )
            out.append(
                (
                    "fact",
                    f"{lead}: {peak} m of high-speed running in one minute, against a "
                    "published average best minute of 62 m.",
                )
            )
        else:
            out.append(
                (
                    "fact",
                    f"{name}: his hardest minutes so far ({nth} time), a 1-min peak of {peak} m "
                    "above 5.5 m/s (19.8 km/h), against a published mean peak of 62 m "
                    "[Leifsson2024].",
                )
            )
        out.append(pro)
    elif kind == "exposed_on_turnover":
        d0, d8 = _v(b, "distance_to_ball_at_turnover"), _v(b, "distance_to_ball_8s_later")
        team = b["player"]["team_name"]
        out.append(
            (
                "fact",
                f"{team} lose the ball just after {name}'s hardest minutes so far: {d0} m "
                f"from the ball, then {d8} m eight seconds "
                "later.",
            )
        )
        out.append(
            (
                "4",
                "Losing the ball forces the hardest running of the game. This is where "
                "tired legs get exposed.",
            )
            if mode == "fan" and not b["non_fatigue_reasons"]  # claim 4 blames tired legs
            else pro
        )
    elif kind == "second_wind":
        mins = _v(b, "minutes_after_hardest_minutes", digits=1)
        rate, avg = (
            _v(b, "last_2min_hsr_per_min", digits=1),
            _v(b, "match_average_per_min", digits=1),
        )
        out.append(
            (
                "fact",
                f"Second wind for {name}: {mins} minutes after his hardest minutes, "
                f"his high-speed running is back to his match average ({rate} m per "
                f"minute vs {avg}).",
            )
        )
        if mode == "analyst" and any(c["id"] == "1" for c in b["claims"]):
            out.append(
                (
                    "1",
                    "After a player's hardest 5 minutes, high-speed running in the next "
                    "minute is typically about 40% below their match average. It comes back "
                    "over about 5 minutes.",
                )
            )
    elif kind == "fresh_legs":
        rate, pct = _v(b, "sub_hsr_per_min", digits=1), _v(b, "vs_teammates")
        more = None if pct is None else f"{pct}% more" if pct >= 0 else f"{-pct}% less"
        out.append(
            (
                "fact",
                f"Fresh legs: since coming on, {name} has done {rate} m of "
                f"high-speed running per minute, {more} than his team-mates over the "
                "same minutes.",
            )
        )
        out.append(
            (
                "6",
                "Fresh legs: substitutes typically do 15–25% more high-intensity "
                "running per minute than players who started.",
            )
        )
    elif kind == "not_tired_tactical":
        pct = _v(b, "vs_match_average")
        reason = b["facts"]["reasons"][0]["text"] if b["facts"].get("reasons") else None
        drop = (
            "has hardly run at high speed in the last 5 minutes"
            if pct is None or pct <= -90
            else f"is doing {-pct}% less high-speed running than his match average"
        )
        out.append(("13", f"{name} {drop}, but {reason}, so this is likely not fatigue."))
        if any(c["id"] == "14" for c in b["claims"]):
            n, usual = _v(b, "touches_last_5min"), _v(b, "touches_per_5min_so_far")
            out.append(("14", f"Fewer touches too: {n} in the last 5 minutes against about "
                              f"{usual} per 5 minutes in his match so far, partly because the "
                              "ball was out of play more."))  # fmt: skip
    elif kind == "tug_of_war":
        f = b["facts"]
        opp = b["opponent"]["name"] if b.get("opponent") else "their opponents"
        block, vs = f["block"], _v(b, "vs_opponent")
        mine, theirs = _v(b, "team_hsr_per_in_play_min"), _v(b, "opponent_hsr_per_in_play_min")
        if f.get("pattern") == "gap closed":
            earlier, own = _v(b, "earlier_gap_vs_opponent"), _v(b, "team_vs_own_first_15")
            out.append(
                (
                    "fact",
                    f"The gap has closed: in {block} {name} and {opp} were level on "
                    "high-speed running per ball-in-play minute, after "
                    f"{name} had done up to {earlier}% more than them earlier.",
                )
                if mode == "fan"
                else (
                    "fact",
                    f"The gap has closed: {name} had done up to {earlier}% more "
                    f"high-speed running per ball-in-play minute than {opp}, and in "
                    f"{block} it was level ({mine} m vs {theirs} m).",
                )
            )
            if own is not None and own < 0:
                out.append(
                    (
                        "fact",
                        f"{name}'s high-speed running per ball-in-play minute in "
                        f"{block} is {-own}% below their first 15 minutes.",
                    )
                )
        else:
            out.append(
                (
                    "fact",
                    f"{name} did {vs}% more high-speed running per ball-in-play "
                    f"minute than {opp} in {block}"
                    + ("." if mode == "fan" else f" ({mine} m vs {theirs} m)."),
                )
            )
        share, time = (
            _v(b, "team_hsr_share_after_ball_changed_hands"),
            _v(b, "time_share_after_ball_changed_hands"),
        )
        lost, rest = _v(b, "team_hsr_per_min_after_losing"), _v(b, "team_hsr_per_min_rest")
        out.append(
            (
                "fact",
                f"In {block}, {share}% of {name}'s high-speed running came in the first 10 "
                f"seconds after the ball changed hands, in {time}% of the time the ball was in "
                "play.",
            )
            if mode == "fan"
            else (
                "fact",
                f"In {block}, {name} did {lost} m of high-speed running per minute in the first "
                f"10 s after losing the ball, against {rest} m per minute the rest of the time "
                "the ball was in play.",
            )
        )
        if mode == "fan":
            out.append(
                (
                    "9a",
                    "When one side raises the tempo, the other has to match it: in the "
                    "Premier League the two teams' running totals move closely "
                    "together.",
                )
            )
    elif kind == "flat_out":
        f = b["facts"]
        v, kmh, share = (
            _v(b, "peak_speed", digits=1),
            _v(b, "peak_speed_kmh"),
            _v(b, "share_of_top_speed"),
        )
        run = f", {f['running']}" if f.get("running") else ""
        if f.get("fastest_in_match_so_far"):
            out.append(
                (
                    "fact",
                    f"{name} reaches {v} m/s ({kmh} km/h){run}: the fastest second "
                    "of anyone in the match so far.",
                )
            )
        elif f.get("new_personal_best"):
            out.append(
                ("fact", f"{name}'s fastest run of the match so far: {v} m/s ({kmh} km/h){run}.")
            )
        else:
            out.append(
                (
                    "fact",
                    f"{name} reaches {v} m/s ({kmh} km/h){run}, {share}% of his top speed so far.",
                )
            )
        if f.get("share_of_top_before_75"):
            out.append(
                (
                    "36",
                    "Top speed hardly drops over a match: in the Premier League, "
                    "players' fastest runs late on are almost as fast as their fastest "
                    "early on.",
                )
            )
        elif mode == "analyst":
            out.append(
                (
                    "37",
                    "Flat-out running is rare: Premier League players cover only "
                    "about 20–30 m a match above 85% of their season top speed.",
                )
            )
    return [x for x in out if x and not re.search(r"\bNone\b", x[1])]  # a fact was missing


# --- Narrator and Personalization (LLM) ------------------------------------------------------


class Line(BaseModel):
    moment_id: str
    claim_id: str
    sentence: str


class Lines(BaseModel):
    lines: list[Line]


NARRATOR = """You are the Narrator of Running Battery, live commentary on a synthetic football match
for {audience}. For each moment write one or two sentences, each a separate line with the
claim id it uses: a register claim id from the moment's "claims", or "fact" for a measured fact
from its "facts" (distances, high-speed running, his hardest minutes, energy, speeds).

Rules (a Verifier blocks anything else):
- Never say a player is tired, exhausted, empty, unfit or fitter, or blame an error, a miss, a
  decision or a result on fatigue. The battery and low_chance describe the RUNNING relative to a
  typical professional: "running that would leave a typical professional at about X% of their
  short-term reserve", never "he is at X%" or "his battery".
- Use the register's wordings, adapted to the moment; keep their qualifiers. Use a wording only
  for what it says, never as a lead-in to a different fact ("the other has to match it: they
  ran more without the ball" mixes two findings). Use only the claim
  ids in the moment's "claims"; a sentence that gives the moment's own numbers (its facts) is
  "fact", even next to a general finding.
- Every number must be one of the moment's facts (you may round it) or in the claim's wording.
  Every percentage says what it is compared with (his match average, his peak, his team-mates).
- If the moment lists non_fatigue_reasons, a sentence that mentions fatigue must name the reason
  and hedge ("likely", "may be").
- A red_zone moment is "his hardest minutes so far" (the few minutes when he has run hardest so
  far); the post-peak window is neutral: "just after his hardest minutes so far" (it says when,
  nothing about his body). Find a natural sentence for them; never call them a "spell".
- The battery is never his: not "his battery", not "his typical-pro battery". Claim 11's wording
  takes no reason after it (a lead or possession does not "explain" running already done).
- The numbers in the wordings of claims 11, 12 and 13 are examples: for claim 11 use the
  moment's typical_pro_battery_now (0.62 is "about 62%"). What you say must agree with the facts.
- Say something specific to each moment; use a general register sentence at most twice in the
  whole feed. For not_tired_tactical moments, say what fits instead of fatigue (the reason).
- Write "hardly any" rather than "0.0 m/min". Never start a sentence with a label such as
  "fact:".
- fastest_in_match_so_far means so far: "the fastest of anyone in the match so far".
- Never say or imply that a team is more tired, fresher or fitter than the other (claim 35):
  compare their measured running per ball-in-play minute instead. Never read effort or intent
  from speed ("didn't try", "gave up", "jogged back", "should have sprinted"; claim 38): give the
  speed, the share of his top speed so far and what happened.
- Team numbers are high-speed running (> 5.5 m/s), team totals: say "high-speed running", never
  "covered", which reads as total distance. vs_opponent is how much more (+) or less (−) the
  team ran than the opponent: say "X% more than their opponents", never turn it round.
- Claims 3 and 4 are general findings: never apply them to this player ("one of those moments
  for him", "the hardest running of the game for him"); his own running is in the facts.
- Never write field names such as vs_opponent or top_speed_so_far; write plain English.
- Team moments (tug_of_war) also say where the running happened, from possession and the ball's
  position only (team_hsr_share_after_ball_changed_hands with time_share_after_ball_changed_hands,
  or metres per minute of a situation, never raw totals): "In 0:00–15:00, 43% of Westerlyn
  Albion's high-speed running came in the first 10 seconds after the ball changed hands, in 29%
  of the time the ball was in play". Name the block once. Situations say where, never why: no
  "pressing", "pressed", "closing down" or other purposes (claim 39), no tiredness. From claim 4
  use only its first sentence ("Losing the ball forces the hardest running of the game"); "tired
  legs" would be about the team (claim 35).
- Team moments (tug_of_war): the first sentence compares the two teams by name, as the
  comparison is the point: "Westerlyn Albion did 30% more high-speed running per ball-in-play
  minute than Ravensholt Albion in 0:00–15:00" (vs_opponent). For pattern "gap closed" say "the
  gap has closed", that the two sides were level in that block, and how big the gap was earlier
  (earlier_gap_vs_opponent). In fan mode that comparison is the one number.
- Name every team in full ("team_names"), every time: when the two names share a word (Westerlyn
  Albion, Ravensholt Albion), that word alone does not say which team.
- Claim 14 ("fewer touches") only if the moment's claims include it; then give the touch
  counts from the facts (touches_last_5min against touches_per_5min_so_far).
- An exposed_on_turnover moment with times_exposed_so_far above 1: say it is the second (third…)
  time his team lost the ball just after his hardest minutes so far, in those words ("This is
  the third time his team have lost the ball just after his hardest minutes so far"; for the
  favourite: "This is the third time <his name>'s team have lost the ball…"), not "exposed"
  and not "he is facing".
- A flat_out run with new_personal_best: say it is his fastest of the match so far, never a
  share of his top speed above 100%.
- A gap that closed: say the two sides were level, never "0% more".
- Claims 1 (after his hardest 5 minutes), 7 (the last 15 minutes) and 36 (top speed late on) are
  offered only where they fit; the Verifier blocks them elsewhere.
- m/s first, km/h in brackets. Plain English.
{style}"""
STYLE = {
    "fan": "Fan mode: short, vivid sentences, numbers rounded, one number per sentence, no "
    "jargon, no citation keys. Analyst-only claims are not allowed.",
    "analyst": "Analyst mode: precise, with units and the battery band where useful; you may "
    "add citation keys in brackets such as [Leifsson2024]; CS and D′ are model parameters "
    "(assumed), never measured.",
}


def personalize(mode: str, favourite: str | None) -> str:
    """The Personalization step: the audience, the style, and the favourite player."""
    style = STYLE[mode]
    if favourite:
        style += (
            f" The viewer follows {favourite}: in his moments, name him in the first sentence "
            '(as its subject, or as in "<his name>\'s team"; never as a label before a colon).'
        )
    return NARRATOR.format(audience="casual fans" if mode == "fan" else "analysts", style=style)


def unlabel(sentence: str) -> str:
    """Drop a label the Narrator put before a sentence ("fact: he had 0 touches…", or a bare
    claim id, "11: He has done running…", in the decision 31 feed; "60:00–75:00" stays)."""
    s = re.sub(r"^\s*(fact|claim\s*[\w.]+)\s*:\s*|^\s*(\d{1,2}[a-d]?|G\d{1,2})\s*:\s+", "",
               sentence, flags=re.I)  # fmt: skip
    return s[:1].upper() + s[1:]


def narrator_view(b: dict) -> dict:
    """A moment as the Narrator gets it: no "what", and the facts without their source fields,
    whose code names ("series.red_zone") it copied into sentences (decision 29)."""
    facts = {k: {x: y for x, y in v.items() if x != "source"} if isinstance(v, dict) else v
             for k, v in b["facts"].items()}  # fmt: skip
    return {k: v for k, v in b.items() if k != "what"} | {"facts": facts}


async def narrate_llm(briefs: list[dict], mode: str, favourite: str | None) -> list[Line]:
    from runningbattery.agents import foundry

    agent = foundry.agent("Narrator", personalize(mode, favourite), "main")
    payload = json.dumps([narrator_view(b) for b in briefs], ensure_ascii=False)
    r = await agent.run(f"Moments (JSON):\n{payload}", options={"response_format": Lines})
    return r.value.lines if r.value else []


# --- Verifier and the feed -------------------------------------------------------------------


def sources(b: dict, claim: str) -> list[str]:
    out = []
    if claim not in ("fact", None):
        row = next((c for c in b["claims"] if c["id"] == claim), None)
        row = row or verifier.register_row(claim)
        out += (row or {}).get("sources") or []
    out += sorted({f["source"] for f in b["facts"].values()
                   if isinstance(f, dict) and "source" in f})  # fmt: skip
    return out


async def check(
    b: dict, mode: str, claim: str, sentence: str, agent
) -> tuple[FullVerdict, str | None]:
    ctx = verifier_context(b)
    cid = None if claim == "fact" else claim
    v = await verify_full(sentence, mode, ctx, cid, agent)
    return v, cid


def as_fact(b: dict, claim: str, sentence: str) -> str:
    """A team moment's comparison (MUST_SAY) is a measured fact, whatever claim the Narrator
    tagged it with (it tagged them 9a and 9b, which then counted as general sentences). So is a
    line tagged with a general claim whose numbers all come from the moment's facts, not from
    the claim's wording ("Theo Galdcott has done 12.2 m/min since coming on", tagged 6;
    decision 29)."""
    need = MUST_SAY.get(b["facts"].get("pattern")) if b["kind"] in TEAM_KINDS else None
    if need and re.search(need, sentence, re.I):
        return "fact"
    if claim in ("fact", None):
        # A register wording tagged "fact" is that claim, not a measurement (the Narrator tagged
        # claim 9b's "Without the ball, Premier League players typically cover…" as a fact).
        return next((c["id"] for c in b["claims"] if _wording_of(sentence, c.get("wording"))),
                    claim)  # fmt: skip
    if claim in SPECIFIC:
        return claim
    # The register's wording even for a claim the moment does not offer: else a number of the
    # wording that matches a fact by chance ("40%") made claim 1 a "fact" (decision 30).
    row = next((c for c in b["claims"] if c["id"] == claim), None) or verifier.register_row(claim)
    wording = (row or {}).get("wording") or ""
    return "fact" if verifier.from_facts(sentence, b["facts"], wording) else claim


def _wording_of(sentence: str, wording: str | None) -> bool:
    """The sentence is mostly the claim's wording: 60% or more of its longer words."""
    words = lambda t: set(re.findall(r"[a-z]{4,}", t.lower()))  # noqa: E731
    own = words(wording or "")
    return bool(own) and len(own & words(sentence)) >= 0.6 * len(own)


async def entries_for(b: dict, mode: str, lines: list[tuple[str, str]], agent) -> list[dict]:
    """Verify each line; replace a blocked one by the rewrite or the template (not a claim the
    moment already shows)."""
    out = []
    fallback = template(b, mode)
    lines = [(as_fact(b, c, x), x) for c, x in lines]
    for k, (claim, sentence) in enumerate(lines):
        v, _ = await check(b, mode, claim, sentence, agent)
        entry = _entry(b, mode, claim, sentence, v)
        if v.ok:
            out.append(entry)
            continue
        out.append(entry | {"shown": False})
        if v.rewrite:
            rv, _ = await check(b, mode, claim, v.rewrite, agent)
            if rv.ok:
                out.append(_entry(b, mode, claim, v.rewrite, rv, "rewritten", sentence))
                continue
        used = {e["claim"] for e in out if e["shown"]} - {"fact"}
        if k < len(fallback) and fallback[k][1] != sentence and fallback[k][0] not in used:
            fc, fs = fallback[k]
            fv, _ = await check(b, mode, fc, fs, agent)
            if fv.ok:
                out.append(_entry(b, mode, fc, fs, fv, "fallback", sentence))
    return out


def needs(b: dict, favourite: str | None = None) -> str | None:
    """What a moment's lines must say, as a pattern: a team moment's comparison (MUST_SAY), a
    substitute's against his team-mates, the favourite's typical-pro line when caught on the
    break (decision 31)."""
    if b["kind"] in TEAM_KINDS:
        return MUST_SAY.get(b["facts"].get("pattern"))
    if b["kind"] == "fresh_legs" and b["facts"].get("vs_teammates") is not None:
        return FRESH_LEGS_SAYS
    if (b["kind"] == "exposed_on_turnover" and favourite and b.get("player")
            and b["player"]["id"] == favourite and _pro(b)):  # fmt: skip
        return FAVOURITE_EXPOSED_SAYS
    return None


async def must_say(
    b: dict, mode: str, chunk: list[dict], agent, favourite: str | None = None
) -> list[dict]:
    """What the moment must say (``needs``): if no shown line says it, the verified template
    line that does, first."""
    need = needs(b, favourite)
    if not need or any(e["shown"] and re.search(need, e["sentence"], re.I) for e in chunk):
        return chunk
    for claim, sentence in [x for x in template(b, mode) + [_pro(b)] if x]:
        if re.search(need, sentence, re.I):
            v, _ = await check(b, mode, claim, sentence, agent)
            if v.ok:
                return [_entry(b, mode, claim, sentence, v, "template")] + chunk
    return chunk


def cap_general(entries: list[dict]) -> None:
    """Each general register sentence shown at most MAX_GENERAL times per mode, in match order;
    later ones stay in the feed as ``repeat``, not shown."""
    seen: dict[tuple[str, str], int] = {}
    for e in sorted(entries, key=lambda e: e["video_s"]):
        if not e["shown"] or e["claim"] in SPECIFIC or e["claim"] == "fact":
            continue
        key = (e["mode"], e["claim"])
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > MAX_GENERAL:
            e["shown"], e["verdict"] = False, "repeat"


async def refill(briefs: list[dict], entries: list[dict], agent) -> list[dict]:
    """A moment left with no line in a mode gets its first verified template line that is not
    a general sentence."""
    added = []
    for b in briefs:
        for mode in MODES:
            if any(e["shown"] and e["moment_id"] == b["moment_id"] and e["mode"] == mode
                   for e in entries):  # fmt: skip
                continue
            for claim, sentence in template(b, mode):
                if claim == "fact" or claim in SPECIFIC:
                    v, _ = await check(b, mode, claim, sentence, agent)
                    if v.ok:
                        added.append(_entry(b, mode, claim, sentence, v, "template"))
                        break
    return added


def _entry(b, mode, claim, sentence, v: FullVerdict, verdict=None, original=None) -> dict:
    when = {k: b["_when"][k] for k in ("t", "period", "clock", "video_s")}
    e = when | {
        "player": {k: b["player"][k] for k in ("id", "name", "shirt", "team")}
        if b.get("player") else None,
        "team": b["player"]["team"] if b.get("player") else b["team"]["id"],
        "team_name": b["player"]["team_name"] if b.get("player") else b["team"]["name"],
        "kind": b["kind"], "moment_id": b["moment_id"], "sentence": sentence, "claim": claim,
        "sources": sources(b, claim), "mode": mode,
        "verdict": verdict or ("pass" if v.ok else "blocked"), "shown": True,
        "verifier": {"stage": v.stage, "findings": v.findings},
    }  # fmt: skip
    if original:
        e["original"] = original
    return e


async def build(
    folder: Path, offline: bool = False, favourite: str | None = None
) -> dict[str, Any]:
    tools = MatchTools(folder)
    fav = tools.m.player(favourite)["id"] if favourite else None
    ids = related(tools, fav)
    found = candidates(tools, players=ids)
    picked, how = None, "offline"
    if not offline:
        try:
            picked = await pick_llm(folder, found, fav)
            how = "llm"
        except Exception as e:  # the plain-code pick stands in
            how = f"offline (tactical agent failed: {type(e).__name__})"
    if not picked:
        picked = pick_offline(found, ids)
    if ids:
        picked = ensure_favourite(picked, found, ids)
    briefs = []
    for mid in picked:
        b = brief(tools, found[mid])
        b["_when"] = {k: found[mid][k] for k in ("t", "period", "clock", "video_s")}
        briefs.append(b)
    agent = None
    if not offline:
        from runningbattery.agents.llm_verifier import verifier_agent

        agent = verifier_agent()
    entries: list[dict] = []
    narration = {}
    for mode in MODES:
        lines: dict[str, list[tuple[str, str]]] = {}
        narration[mode] = "offline"
        if not offline:
            try:
                for ln in await narrate_llm([_public(b) for b in briefs], mode, fav and
                                            tools.m.players[fav]["name"]):  # fmt: skip
                    lines.setdefault(ln.moment_id, []).append((ln.claim_id, unlabel(ln.sentence)))
                narration[mode] = "llm"
            except Exception as e:
                narration[mode] = f"offline (narrator failed: {type(e).__name__})"
        jobs = [entries_for(b, mode, lines.get(b["moment_id"]) or template(b, mode), agent)
                for b in briefs]  # fmt: skip
        for chunk in await asyncio.gather(*jobs):
            entries += chunk
    cap_general(entries)
    for b in briefs:  # after the cap, so a comparison is never held back as a repeat
        for mode in MODES:
            mine = [e for e in entries if e["moment_id"] == b["moment_id"] and e["mode"] == mode]
            entries += [e for e in await must_say(b, mode, mine, agent, fav) if e not in mine]
    entries += await refill(briefs, entries, agent)
    entries.sort(key=lambda e: (e["video_s"], e["mode"]))
    return {
        "match_id": tools.m.metadata.match_id,
        "synthetic": True,
        "created": date.today().isoformat(),
        "agents": {"tactical": how, "narrator": narration, "personalization": "plain code",
                   "verifier": "rules + llm" if agent else "rules",
                   "models": _models(offline)},
        "favourite": fav,
        "moments": [{k: b[k] for k in ("moment_id", "kind", "clock")} | b["_when"]
                    for b in briefs],
        "entries": entries,
    }  # fmt: skip


def _public(b: dict) -> dict:
    return {k: v for k, v in b.items() if not k.startswith("_")}


def _models(offline: bool) -> dict | None:
    if offline:
        return None
    from runningbattery.agents import foundry

    return {"main": foundry.model("main")}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m runningbattery.agents.feed", description=__doc__
    )
    parser.add_argument("folder", type=Path)
    parser.add_argument("--offline", action="store_true", help="no LLM: templates and rules")
    parser.add_argument("--favourite", help="player id, name or 'home 3'")
    parser.add_argument("--out", type=Path, help=f"default <folder>/{FEED}")
    args = parser.parse_args(argv)
    feed = asyncio.run(build(args.folder, args.offline, args.favourite))
    out = args.out or args.folder / FEED
    out.write_text(json.dumps(feed, indent=1, ensure_ascii=False))
    shown = [e for e in feed["entries"] if e["shown"]]
    blocked = [e for e in feed["entries"] if e["verdict"] == "blocked"]
    repeats = [e for e in feed["entries"] if e["verdict"] == "repeat"]
    print(
        f"wrote {out}: {len(feed['moments'])} moments, {len(shown)} sentences shown, "
        f"{len(blocked)} blocked, {len(repeats)} repeats held back; agents {feed['agents']}"
    )


if __name__ == "__main__":
    main()
