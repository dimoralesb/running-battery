"""The IDSSE matches [Bassek2025] as match folders, events included, for the moment realism
check (``validate.moments``): do the moments the feed shows happen in real football?

``python -m runningbattery.validate.real_events [match ids] [--out data/real/idsse]``

writes ``<out>/<match id>/`` (``metadata.json``, ``tracking.jsonl``, ``events.jsonl``; no truth)
from ``sim.idsse.to_match`` and the DFL event file. The output folder is git-ignored: IDSSE is
CC BY 4.0 and, until PLAN says otherwise, used offline only.

Anonymised as it is written: teams are "home" and "away", players H01–H11 and A01–A11 (starters,
goalkeeper first, then by position) and H12… for substitutes in the order they came on, with
fictional team and player names from ``sim.rosters`` (a fixed draw per match id) and shirt
numbers given by position as the generator does. Positions, times and events are the match's.

Events are not synchronised with the tracking in the release (offset −0.37 ± 1.82 s, max 27 s
[Bassek2025, p.8]), so (our method):

1. **Possession** comes from the tracking's possession flag, which is synchronised. The flag
   changes about 500 times a match (every touch in a duel); a team has the ball once it has kept
   the flag ``HOLD_S`` (shorter spells go to the team before). ``possession_id`` goes up with
   each change and at each kick-off, as in the generator (``sim.match``).
2. **Turnovers**: a change of possession with the ball in play from ``OPEN_PLAY_S`` before to
   ``OPEN_PLAY_S`` after it. Each gets a ``ball_recovery`` event at the change, by the winning
   player nearest the ball (DFL's own ``BallClaiming`` events are dropped, so a gain is not
   counted twice).
3. **Transitions**: the generator starts one after a share of open-play turnovers
   (``params.TRANSITION_CHANCE``, a draw: the team chose to counter). Real tracking shows the
   choice instead: a turnover starts a positive transition when the winning team takes the ball
   ``COUNTER_ADVANCE_M`` towards the opponents' goal within ``COUNTER_WITHIN_S`` while it keeps
   it (a quick attack after the regain [Bortnik2022]). It lasts as in the generator: at most
   ``TRANSITION_MAX_S``, ended by the next change of possession or a dead ball. The winning
   team's events in it are ``positive_transition``, the other team's ``negative_transition``.
   ``--all-turnovers`` makes every open-play turnover a transition (the sensitivity run).
4. **Event times**: shots carry DFL's own tracking frame (``CalculatedFrame``) and are placed
   there. Each half's offset between the event clock and the tracking is the median over those
   shots; every other event is shifted by it and then snapped, within ``SNAP_S``, to the frame
   where its player is nearest the ball, if he comes within ``SNAP_M`` of it.
5. **Positions**: an event's ``start`` is its player's tracked position at that frame (the ball's
   for events without a player), in our coordinates.

DFL event → ours: passes, crosses and restarts (throw-in, free kick, goal kick, corner, kick-off)
→ ``pass`` with the restart as subtype; shots → ``shot`` (DFL's xG; penalties and direct free
kicks too) and ``goal``; ``TacklingGame`` → ``tackle`` + ``ball_loss`` (tackled) when the ball
changed hands from the player on it, else ``duel`` (ground or aerial); ``OtherBallAction`` →
``clearance`` when DFL marks it a defensive clearance, else ``reception`` (a touch); fouls,
cautions (``card``), offsides, substitutions. Not mapped (no counterpart, or not an action on
the pitch): deletions, VAR checks, "penalty not awarded", "chance without shot", "spectacular
play", "nutmeg", runs, fair play, referee balls, team-official cautions and the rest; DFL has no
carries, pressures or ball-out events, so those types stay empty (reported per match).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

from runningbattery.io import Match, write_match
from runningbattery.schema import (
    BodyPart,
    Event,
    EventType,
    MatchMetadata,
    Outcome,
    PassHeight,
    Phase,
    PlayerInfo,
    Point,
    Score,
    Substitution,
    TeamInfo,
    TrackingFrame,
)
from runningbattery.sim import params as SP
from runningbattery.sim import rosters
from runningbattery.sim.idsse import RAW, SOURCE_HZ, to_match

OUT = Path(__file__).resolve().parents[3] / "data" / "real" / "idsse"
HZ = 10
HOLD_S = 2.0  # a team has the ball once it has kept the possession flag 2 s (our assumption)
OPEN_PLAY_S = 0.5  # a turnover in open play: ball alive 0.5 s either side (our assumption)
COUNTER_ADVANCE_M = 20.0  # a positive transition: the ball 20 m nearer goal ...
COUNTER_WITHIN_S = 10.0  # ... within 10 s of the regain [Bortnik2022: transitions last ~10 s]
TRANSITION_MAX_S = SP.TRANSITION_S[0]  # the generator's mean transition (15 s)
SNAP_S = 3.0  # an event snaps to its player's nearest approach to the ball within 3 s ...
SNAP_M = 2.0  # ... if he comes within 2 m of it (our assumptions)
BALL_FRAME_N = {"firstHalf": 10000, "secondHalf": 100000}  # checked in all 7 position files
POSITION_ORDER = ["GK", "CB", "FB", "DM", "CM", "AM", "WM", "CF"]
RESTARTS = {"ThrowIn": "throw_in", "FreeKick": "free_kick", "GoalKick": "goal_kick",
            "CornerKick": "corner", "KickOff": "kick_off", "Penalty": "penalty"}  # fmt: skip
SHOT_RESULT = {"ShotWide": "wide", "SavedShot": "saved", "BlockedShot": "blocked",
               "SuccessfulShot": "goal", "ShotWoodWork": "woodwork",
               "OtherShot": "other"}  # fmt: skip
HEIGHT = {"flat": PassHeight.GROUND, "high": PassHeight.HIGH}


def _time(s: str) -> datetime:
    return datetime.fromisoformat(s)


def read_dfl(path: Path) -> list[dict]:
    """The DFL event file as flat records: ``kind`` is the tag path ("ThrowIn/Play",
    "ShotAtGoal/SavedShot"), ``attrs`` the attributes of every element merged (inner wins)."""
    out = []
    for ev in ET.parse(path).getroot():
        if not len(ev):
            continue
        tags, attrs, node = [], dict(ev.attrib), ev[0]
        while node is not None:
            tags.append(node.tag)
            attrs |= node.attrib
            node = node[0] if len(node) else None
        out.append({"kind": "/".join(tags), "time": _time(ev.attrib["EventTime"]),
                    "attrs": attrs})  # fmt: skip
    return out


def _possession_runs(code: list[str | None]) -> list[list]:
    """[team, first frame, end frame) of each spell with the ball after ``HOLD_S`` smoothing."""
    raw: list[list] = []
    for k, c in enumerate(code):
        if raw and raw[-1][0] == c:
            raw[-1][2] = k + 1
        else:
            raw.append([c, k, k + 1])
    kept: list[list] = []
    for c, a, b in raw:
        if kept and (c is None or (b - a) / HZ < HOLD_S or c == kept[-1][0]):
            kept[-1][2] = b
        else:
            kept.append([c, a, b])
    return kept


class _Half:
    """One period's tracking as arrays, for snapping and positions."""

    def __init__(self, frames: list[TrackingFrame], ids: list[str]):
        self.t = np.array([f.t for f in frames])
        self.alive = np.array([f.ball_status == "alive" for f in frames])
        self.code = [f.possession_team for f in frames]
        self.ball = np.array([(f.ball.x, f.ball.y) for f in frames])
        self.col = {pid: j for j, pid in enumerate(ids)}
        self.xy = np.full((len(frames), len(ids), 2), np.nan)
        for k, f in enumerate(frames):
            for p in f.players:
                self.xy[k, self.col[p.id]] = (p.x, p.y)

    def frame(self, t: float) -> int:
        return int(np.clip(round(t * HZ), 0, len(self.t) - 1))

    def where(self, pid: str | None, k: int) -> Point:
        xy = self.xy[k, self.col[pid]] if pid in self.col else self.ball[k]
        if np.isnan(xy).any():
            xy = self.ball[k]
        return Point(x=float(np.clip(xy[0], -60, 60)), y=float(np.clip(xy[1], -40, 40)))

    def snap(self, pid: str | None, k0: int) -> tuple[int, bool]:
        if pid not in self.col:
            return k0, False
        a, b = max(k0 - round(SNAP_S * HZ), 0), min(k0 + round(SNAP_S * HZ) + 1, len(self.t))
        d = np.hypot(*(self.xy[a:b, self.col[pid]] - self.ball[a:b]).T)
        if not np.isfinite(d).any() or np.nanmin(d) > SNAP_M:
            return k0, False
        return a + int(np.nanargmin(d)), True


def _names(match_id: str, teams: list[list[tuple[str, str, int]]]) -> tuple[list[str], dict]:
    """Fictional team names and player names (``sim.rosters``), fixed per match id."""
    rng = np.random.default_rng(int(hashlib.sha256(match_id.encode()).hexdigest()[:8], 16))
    places = rng.choice(len(rosters.PLACES), size=2, replace=False)
    team_names = [f"{rosters.PLACES[p]} {rng.choice(rosters.SUFFIXES)}" for p in places]
    used: set[str] = set()
    sim_teams, plans = [], []
    for k, players in enumerate(teams):
        starters, subs = [], []
        for pid, pos, shirt in players:
            p = rosters.SimPlayer(pid, rosters._player_name(rng, used), shirt, pos, (0.0, 0.0),
                                  None, None)  # type: ignore[arg-type]  # fmt: skip
            (subs if int(pid[1:]) > 11 else starters).append(p)
        sim_teams.append(rosters.SimTeam("", "", "", "", True, starters, 0.0, 0.0))
        plans += [rosters.SubPlan(k, 0, 0.0, p) for p in subs]
    sim_teams, plans = rosters.distinct_names(sim_teams, plans)
    names = {p.id: p.name for t in sim_teams for p in t.players}
    names |= {s.player.id: s.player.name for s in plans}
    return team_names, names


def _shirts(players: list[tuple[str, str, bool]]) -> dict[str, int]:
    """Shirt numbers by position as the generator gives them (``params.SHIRTS``), the rest from
    the next free number; substitutes from 12."""
    free = {pos.value: list(n) for pos, n in SP.SHIRTS.items()}
    taken: set[int] = set()
    out = {}
    for pid, pos, starter in players:
        if starter and free.get(pos):
            out[pid] = free[pos].pop(0)
            taken.add(out[pid])
    nxt = 12
    for pid, _, _ in players:
        if pid not in out:
            while nxt in taken or nxt in {n for ns in SP.SHIRTS.values() for n in ns}:
                nxt += 1
            out[pid] = nxt
            taken.add(nxt)
    return out


def convert(folder: Path, all_turnovers: bool = False) -> tuple[Match, dict]:
    """One IDSSE match as an anonymised ``io.Match`` with events, and a report of what the
    conversion did."""
    conv = to_match(folder)
    src = conv.match
    meta = src.metadata
    side_of = {t.id: t.side for t in meta.teams}
    report: dict = {"match": folder.name, "sent_off": conv.sent_off,
                    "no_position": conv.no_position}  # fmt: skip
    dfl = read_dfl(folder / "events.xml")

    # Substitutions: pair as DFL's own events say (the tracking only gives the times).
    pairs = {}
    for e in dfl:
        if e["kind"] == "Substitution":
            pairs[e["attrs"]["PlayerIn"]] = e["attrs"]["PlayerOut"]
    subs, fixed = [], 0
    for s in meta.substitutions:
        out = pairs.get(s.player_in, s.player_out)
        fixed += out != s.player_out
        subs.append(s.model_copy(update={"player_out": out}))
    report["substitutions"] = len(subs)
    report["substitution_pairs_fixed_from_events"] = fixed

    # Ids: starters goalkeeper first then by position, substitutes in the order they came on.
    sub_order = [s.player_in for s in sorted(subs, key=lambda s: (s.period, s.t))]
    new_id, teams_out, plist = {}, [], []
    for team in meta.teams:
        letter = "H" if team.side == "home" else "A"
        starters = sorted(
            (p for p in team.players if p.starter),
            key=lambda p: (POSITION_ORDER.index(p.position.value), p.shirt),
        )
        bench = sorted(
            (p for p in team.players if not p.starter),
            key=lambda p: sub_order.index(p.id) if p.id in sub_order else 99,
        )
        for n, p in enumerate(starters + bench, start=1):
            new_id[p.id] = f"{letter}{n:02d}"
        plist.append([(new_id[p.id], p.position.value, p.starter) for p in starters + bench])
    team_names, names = _names(folder.name, [[(i, pos, 0) for i, pos, _ in ps] for ps in plist])
    for team, ps, tname in zip(meta.teams, plist, team_names, strict=True):
        shirts = _shirts(ps)
        players = [
            PlayerInfo(id=i, name=names[i], shirt=shirts[i], position=pos, starter=st)
            for i, pos, st in ps
        ]
        teams_out.append(
            TeamInfo(id=team.side, name=tname, side=team.side, formation=team.formation,
                     attacks_positive_x_in_period_1=team.attacks_positive_x_in_period_1,
                     players=players)
        )  # fmt: skip
    subs = [
        Substitution(period=s.period, t=s.t, team_id=side_of[s.team_id],
                     player_out=new_id[s.player_out], player_in=new_id[s.player_in])
        for s in subs
    ]  # fmt: skip
    meta_out = MatchMetadata(
        match_id=folder.name, generator=meta.generator, periods=meta.periods, teams=teams_out,
        substitutions=subs,
    )  # fmt: skip
    frames = [
        f.model_copy(update={
            "possession_team": side_of.get(f.possession_team) if f.possession_team else None,
            "players": [p.model_copy(update={"id": new_id[p.id]}) for p in f.players],
        })
        for f in src.frames
    ]  # fmt: skip
    ids = [p.id for t in teams_out for p in t.players]
    halves = {h: _Half([f for f in frames if f.period == h], ids) for h in (1, 2)}
    attacks_plus = {t.id: t.attacks_positive_x_in_period_1 for t in teams_out}

    def toward_goal(team: str, period: int, x: np.ndarray | float):
        return x * (1.0 if attacks_plus[team] == (period == 1) else -1.0)

    # --- Possession, turnovers, transitions (from the tracking) ------------------------------
    events: list[dict] = []
    spans: dict[int, list] = {}  # period -> [team, a, b, possession id, transition end frame]
    poss_id = 0
    counts = Counter()
    for h, half in halves.items():
        spans[h] = []
        runs_ = _possession_runs(half.code)
        for n, (team, a, b) in enumerate(runs_):
            if team is None:
                continue
            poss_id += 1
            prev = runs_[n - 1][0] if n else None
            w = round(OPEN_PLAY_S * HZ)
            open_play = prev not in (None, team) and bool(half.alive[max(a - w, 0) : a + w].all())
            trans_end = None
            if open_play:
                counts["open_play_turnovers"] += 1
                end = min(b, a + round(COUNTER_WITHIN_S * HZ))
                x = toward_goal(team, h, half.ball[a:end, 0])
                if all_turnovers or (x.max() - x[0] >= COUNTER_ADVANCE_M):
                    dead = np.flatnonzero(~half.alive[a:b])
                    stop = a + int(dead[0]) if len(dead) else b
                    trans_end = min(stop, b, a + round(TRANSITION_MAX_S * HZ))
                    counts["positive_transitions"] += 1
                players = [p for p in teams_out if p.id == team][0].players
                on = [p.id for p in players if np.isfinite(half.xy[a, half.col[p.id], 0])]
                d = [np.hypot(*(half.xy[a, half.col[p]] - half.ball[a])) for p in on]
                who = on[int(np.argmin(d))] if on else None
                events.append({"period": h, "k": a, "type": EventType.BALL_RECOVERY,
                               "player_id": who, "team_id": team, "outcome": Outcome.SUCCESS,
                               "subtype": "from_tracking"})  # fmt: skip
            spans[h].append([team, a, b, poss_id, trans_end])
        counts["possessions"] += len(spans[h])

    # --- DFL events ----------------------------------------------------------------------------
    pid_new = {old: new for old, new in new_id.items()}
    kickoff = {}
    for e in dfl:
        sec = e["attrs"].get("GameSection")
        if e["kind"].startswith("KickOff") and sec:
            kickoff[sec] = e["time"]
    offsets: dict[int, list[float]] = {1: [], 2: []}

    def period_of(e: dict) -> tuple[int, float]:
        g2 = (e["time"] - kickoff["secondHalf"]).total_seconds()
        if g2 >= -60.0:
            return 2, g2
        return 1, (e["time"] - kickoff["firstHalf"]).total_seconds()

    shots_framed = []
    for e in dfl:
        cf = e["attrs"].get("CalculatedFrame")
        if e["kind"].startswith(("ShotAtGoal", "FreeKick/ShotAtGoal", "Penalty/ShotAtGoal")) and cf:
            h, g = period_of(e)
            n0 = BALL_FRAME_N["firstHalf" if h == 1 else "secondHalf"]
            t = (int(cf) - n0) / SOURCE_HZ
            offsets[h].append(t - g)
            shots_framed.append(id(e))
    offset = {h: float(np.median(v)) if v else 0.0 for h, v in offsets.items()}
    report["event_clock_offset_s"] = {h: round(v, 2) for h, v in offset.items()}
    report["offset_spread_s"] = {
        h: round(float(np.ptp(v)), 2) if v else None for h, v in offsets.items()
    }
    dropped, snapped, unsnapped = Counter(), 0, 0

    def add(e: dict, h: int, k: int, **fields) -> None:
        events.append({"period": h, "k": k} | fields)

    for e in dfl:
        kind, at = e["kind"], e["attrs"]
        top = kind.split("/")[0]
        if kind in ("Delete",) or top in ("FinalWhistle",):
            continue
        h, g = period_of(e)
        half = halves[h]
        team = side_of.get(at.get("Team") or at.get("WinnerTeam") or at.get("TeamFouler"))
        player = pid_new.get(at.get("Player") or at.get("Winner") or at.get("Fouler"))
        if id(e) in shots_framed:
            k = half.frame((int(at["CalculatedFrame"]) - BALL_FRAME_N[
                "firstHalf" if h == 1 else "secondHalf"]) / SOURCE_HZ)  # fmt: skip
        else:
            k, ok = half.snap(player, half.frame(g + offset[h]))
            snapped += ok
            unsnapped += not ok
        if "Play" in kind.split("/") and top in (*RESTARTS, "Play"):
            sub = RESTARTS.get(top) or ("cross" if kind.endswith("Cross") else None)
            if kind.endswith("Cross") and top in RESTARTS:
                sub = RESTARTS[top]
            ev = at.get("Evaluation", "")
            add(e, h, k, type=EventType.PASS, subtype=sub, player_id=player, team_id=team,
                related_player_id=pid_new.get(at.get("Recipient")),
                outcome=Outcome.SUCCESS if ev.startswith("successful") else Outcome.FAIL,
                height=HEIGHT.get(at.get("Height"), PassHeight.LOW),
                restart=top in RESTARTS)  # fmt: skip
        elif "ShotAtGoal" in kind:
            res = SHOT_RESULT.get(kind.split("/")[-1], "other")
            body = BodyPart.HEAD if at.get("TypeOfShot") == "head" else BodyPart.FOOT
            xg = float(at["xG"]) if "xG" in at else None
            add(e, h, k, type=EventType.SHOT, subtype=res if top not in RESTARTS else
                f"{RESTARTS[top]}_{res}", player_id=player, team_id=team, xg=xg, body_part=body,
                outcome=Outcome.SUCCESS if res == "goal" else Outcome.FAIL,
                restart=top in RESTARTS)  # fmt: skip
            if res == "goal" or kind.endswith("SuccessfulShot"):
                add(e, h, k, type=EventType.GOAL, player_id=player, team_id=team, after=True)
        elif kind == "TacklingGame":
            loser = pid_new.get(at.get("Loser"))
            lteam = side_of.get(at.get("LoserTeam"))
            if at.get("PossessionChange") == "true" and at.get("LoserRole") == "withBallControl":
                add(e, h, k, type=EventType.TACKLE, player_id=player, team_id=team,
                    related_player_id=loser, outcome=Outcome.SUCCESS)  # fmt: skip
                add(e, h, k, type=EventType.BALL_LOSS, subtype="tackled", player_id=loser,
                    team_id=lteam, related_player_id=player, outcome=Outcome.FAIL)  # fmt: skip
            else:
                add(e, h, k, type=EventType.DUEL,
                    subtype="aerial" if at.get("Type") == "air" else "ground", player_id=player,
                    team_id=team, related_player_id=loser, outcome=Outcome.SUCCESS)  # fmt: skip
        elif kind == "OtherBallAction":
            clear = at.get("DefensiveClearance") == "true"
            add(e, h, k, type=EventType.CLEARANCE if clear else EventType.RECEPTION,
                player_id=player, team_id=team)  # fmt: skip
        elif kind == "Foul":
            add(e, h, k, type=EventType.FOUL, player_id=player, team_id=team,
                related_player_id=pid_new.get(at.get("Fouled")))  # fmt: skip
        elif kind == "Caution":
            add(e, h, k, type=EventType.CARD, subtype=at.get("CardColor", "yellow"),
                player_id=player, team_id=team)  # fmt: skip
        elif kind == "Offside":
            add(e, h, k, type=EventType.OFFSIDE, player_id=player, team_id=team)
        elif kind == "Substitution":
            continue  # written from the metadata below (tracking times)
        else:
            dropped[kind] += 1
    report["dfl_events_not_mapped"] = dict(dropped.most_common())
    report["dfl_ball_claiming_dropped"] = dropped.get("BallClaiming", 0)
    report["events_snapped"] = snapped
    report["events_not_snapped"] = unsnapped

    for s in subs:
        half = halves[s.period]
        add({}, s.period, half.frame(s.t), type=EventType.SUBSTITUTION, player_id=s.player_out,
            team_id=s.team_id, related_player_id=s.player_in)  # fmt: skip
    for h, half in halves.items():
        add({}, h, 0, type=EventType.PERIOD_START, first=True)
        add({}, h, len(half.t) - 1, type=EventType.PERIOD_END, after=True)

    # --- Order, possession ids, phases, score ----------------------------------------------------
    events.sort(key=lambda e: (e["period"], e["k"], 0 if e.get("first") else 2 if
                               e.get("after") else 1))  # fmt: skip
    out: list[Event] = []
    score = {"home": 0, "away": 0}
    for n, e in enumerate(events):
        h, k = e["period"], e["k"]
        half = halves[h]
        span = next((s for s in spans[h] if s[1] <= k < s[2]), None)
        team = e.get("team_id")
        phase = poss = None
        if span is not None and team is not None:
            owner, a, _, poss, trans_end = span
            if e.get("restart"):
                phase = Phase.SET_PIECE
            elif trans_end is not None and k < trans_end:
                phase = Phase.POSITIVE_TRANSITION if team == owner else Phase.NEGATIVE_TRANSITION
            elif team == owner:
                x = toward_goal(team, h, half.ball[k, 0])
                third = SP.THIRD
                phase = (Phase.BUILD_UP if x < -third else
                         Phase.PROGRESSION if x < third else Phase.FINAL_THIRD)  # fmt: skip
            else:
                phase = Phase.DEFENSIVE_BLOCK
        t = round(float(half.t[k]), 1)
        fields = {key: e[key] for key in ("type", "subtype", "player_id", "team_id",
                                          "related_player_id", "outcome", "body_part",
                                          "height", "xg") if e.get(key) is not None}  # fmt: skip
        if e["type"] not in (EventType.PERIOD_START, EventType.PERIOD_END,
                             EventType.SUBSTITUTION, EventType.CARD):  # fmt: skip
            fields["start"] = half.where(e.get("player_id"), k)
        out.append(
            Event(id=n, period=h, t=t, clock=t + (2700.0 if h == 2 else 0.0),
                  possession_id=poss, phase=phase, score=Score(**score), **fields)
        )  # fmt: skip
        if e["type"] == EventType.GOAL:
            score[team] += 1
    report["score"] = dict(score)
    report |= dict(counts)
    final = [e["attrs"].get("FinalResult") for e in dfl if e["kind"] == "FinalWhistle"]
    report["dfl_final_result"] = final[-1] if final else None
    report["event_counts"] = dict(Counter(e.type.value for e in out).most_common())
    report["phase_counts"] = dict(Counter(e.phase.value for e in out if e.phase).most_common())
    return Match(metadata=meta_out, frames=frames, events=out), report


def write(match_id: str, out: Path = OUT, all_turnovers: bool = False) -> dict:
    match, report = convert(RAW / match_id, all_turnovers)
    folder = out / match_id
    write_match(folder, match.metadata, match.frames, match.events)
    (folder / "conversion.json").write_text(json.dumps(report, indent=1, default=str))
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m runningbattery.validate.real_events",
                                     description=__doc__)  # fmt: skip
    parser.add_argument("matches", nargs="*", help="IDSSE match ids (default: all downloaded)")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument(
        "--all-turnovers",
        action="store_true",
        help="every open-play turnover starts a transition (sensitivity)",
    )
    args = parser.parse_args(argv)
    ids = args.matches or sorted(p.name for p in RAW.iterdir() if (p / "events.xml").exists())
    for match_id in ids:
        report = write(match_id, args.out, args.all_turnovers)
        print(json.dumps(report, default=str))


if __name__ == "__main__":
    main()
