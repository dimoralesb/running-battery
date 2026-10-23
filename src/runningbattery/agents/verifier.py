"""The rule-based Verifier (PLAN §3.4; BUILD_PLAN "Wed 21"): fixed checks that run before any
LLM check, so unsupported claims are blocked even if the LLM Verifier slips.

``python -m runningbattery.agents.verifier "He is tired." [--mode analyst]``

Each rule is tied to a row of the claims register (``claims.json``, from synthesis §5): a
blocked claim (20–34), a qualified claim used without its qualifier (10, 11, 17, 19c, 19d), an
analyst-only claim in fan mode (9c, 16, 18, 19, 19d), or a global rule (G1 baseline for every
percentage, G2 estimate language, G9 typical-professional wording). A sentence passes only if no
rule fires.

With a ``context`` (from the ``moment_context`` tool, plus the facts the sentence was written
from) two more checks run (v2, 2026-10-17):
- **Context check** (rule 2, G3, claim 13): "tired", "fatigue", "in the red" and the like while
  a non-fatigue reason is present (a big lead, a long stoppage, the start of a half, just
  subbed on, his team on the ball…) must name that reason; otherwise use neutral words.
- **Numbers** (N1): every number in the sentence must be one of the facts (or a rounding, a
  percentage or km/h of one), the cited claim's own wording (except the examples in claims 11,
  12 and 13), or a window length ("5 min").
- **Touches** (claim 14, decision 25): "fewer touches" needs the measured touch counts in the
  facts, and they must show fewer touches than his match so far.
- **Claims offered** (decision 25): with ``claims_offered`` (the register ids the moment offers,
  ``find_moments``), a sentence citing any other claim is blocked: claim 1 only after a spell of
  about 5 min, claim 36 only after the 75th minute, claim 7 only in the last block.
- **Team names** (G11): with ``team_names``, a word both names share ("Albion") must not stand
  for one team.
- **Claim 2 as his own** (2026-10-19): claim 2's finding in a sentence that gives his own
  stretch's length in digits.
The rules can only block. The LLM pass (``agents.llm_verifier``) runs after them.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

Mode = Literal["fan", "analyst"]
REGISTER = Path(__file__).with_name("claims.json")
FLAGS = re.IGNORECASE

# Words that make a sentence a statement about fatigue or the battery.
FATIGUE = (
    r"\b(tired|tiring|fatigu\w*|exhaust\w*|knackered|shattered|leggy|in the tank|in the red|"
    r"battery|reserve|running on empty|out of gas|heavy legs|tired legs|dead legs|"
    r"legs (?:had|have) gone)\b"
)
# Estimate language (G2) or the typical-professional wording (claim 11).
HEDGE = (
    r"\b(likely|probably|our estimate|we estimate|estimated?|the data suggest|suggests?|"
    r"typical professional|typical pro|model|may|might|could|in general|typically)\b"
)
# A reference to one player (G2 applies to statements about a player, not general ones).
PERSON = r"\b(he|she|him|his|her|he's|she's)\b"
# A capitalised name as the subject (not a sentence-opening function word).
NAME = r"\b(?!(?:This|That|It|There|Here|What|Which|Who|The|A|An|In|After|When)\b)[A-Z][a-z]+"
STATE = r"(tired|exhausted|fatigued|knackered|spent|shattered|out on his feet|done in)"
# Baselines that make a percentage meaningful (G1, claim 24).
BASELINE = (
    r"\b(than|vs\.?|versus|compared (?:with|to)|match average|average|normal|usual|peak|"
    r"first 15|kick-off|first half|reserve|typical (?:professional|pro)|of the time|chance|earlier|"
    r"of the (last|first|next) (\d+|one|two|three|five|ten|fifteen) min\w*|team-?mates|"
    r"of (that|the|this) (period|time|spell|block|window)|"
    r"top speed|opponents?|of (his|their|the team's|[A-Z]\w+'s) high-speed running|"
    r"(the )?player he replaced)\b"
)
NEGATED_LACTIC = r"\b(isn'?t|is not|not|no|nothing to do with)\b[^.]{0,25}\blactic"
# Wording that blames fatigue, for the context check (rule 2).
TIRED = (
    r"\b(tired|tiring|tire[sd]? out|fatigu\w*|exhaust\w*|in the red|leggy|heavy legs|dead legs|"
    r"legs (?:had|have) gone|out of steam|out of gas|running on empty|fad(?:e|es|ed|ing))\b"
)
# How a sentence names each non-fatigue reason (codes from tools.REASONS).
STOPPAGE = (
    r"stoppage|out of play|ball (was|is|has been|went) (out|dead)|break in play|delay|restart"
)
NAMES_REASON = {
    "big_lead": r"\blead\b|leading|ahead|\bup\b|\d\s*[–-]\s*\d|sitting (deep|back)|"
    r"sat (deep|back|on)|game state|comfortable",
    "start_of_half": r"(start|beginning|opening|first (few )?minutes) of the (second |2nd |first )?"
    r"half|after the (break|restart|interval)|since the restart|half-?time|kick-?off",
    "just_subbed_on": r"came on|coming on|just on\b|substitute|off the bench|fresh legs|settling",
    "ball_out_of_play": STOPPAGE + r"|injury|treatment",
    "low_ball_in_play": STOPPAGE + r"|ball in play",
    "team_in_possession": r"possession|had the ball|has the ball|on the ball|with the ball|"
    r"(kept|keeping|keep) the ball",
    "just_won_ball": r"possession|won (the ball|it) back|won the ball|on the ball|with the ball",
    "low_first_half_load": r"first half|first-half|before the break",
}  # fmt: skip
# Fatigue named only to rule it out ("tactical rather than fatigue", "not fatigue").
NOT_FATIGUE = (
    r"(rather than|not|isn'?t|is not|instead of|no sign of|nothing to do with)\s+"
    r"(a sign of |just |simply )?(fatigue|tiredness|being tired)"
)
# A scoreline in a sentence ("a 3–0 lead", "leading 2-1"): G13 checks it against the score.
SCORELINE = (
    r"\b(\d{1,2})\s*[–-]\s*(\d{1,2})\s+(?:lead|win|victory|defeat|deficit|scoreline|advantage|"
    r"up|down)\b|\b(?:at|leading|led|trailing|behind|ahead|up|down|lead of)\s+(\d{1,2})\s*[–-]\s*"
    r"(\d{1,2})\b(?![:%.\d])"
)
# Claims whose wording holds an example, not a finding ("about 40%", "13 km", "a 3–0 lead"):
# its numbers must come from the facts.
EXAMPLE_WORDING = {"11", "12", "13"}
NUMBER = r"(?<![\w.])\d+(?:[.,]\d+)?"
# Claim 14's finding ("fewer touches"), however it is worded.
FEWER_TOUCHES = (
    r"\b(fewer|less|reduced|drop in|fall in)\s+(\w+\s+)?(touch(es)?|on the ball)\b|"
    r"\btouch(es)?\b[^.]*\b(dropped|fell|down)\b"
)
SPELLED = (
    r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
    r"sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
    r"hundred"
)
WINDOW = r"(?<![\w.])(1|2|5|10|15|30|45|60|90)\s*(-|\s)?(min\w*|second\w*|s\b|metres?)"
# Claim 2's finding, in its own words, and a length of time in digits ("82 s", "4 min").
CLAIM_2 = (
    r"short bursts?|shaken off|(?:five-minute spell|five hard minutes) takes?|"
    r"sprinting takes longer"
)
DURATION = r"(?<![\w.])\d+(?:\.\d+)?\s*(s|secs?|seconds?|mins?|minutes?)\b"


@dataclass(frozen=True)
class Rule:
    claim: str  # claims register id ("33", "G1", …)
    message: str
    pattern: str  # fires when found…
    needs: str | None = None  # …and this is found too
    unless: str | None = None  # …and this is not found
    fan_only: bool = False  # only blocks in fan mode (analyst-only claims)
    sourced_ok: bool = False  # passes when every number in it is one of the facts (N1)


RULES: tuple[Rule, ...] = (
    # 11 (decision 41, 15:55 and 66:00 of the site's feed): "would leave a typical professional
    # at about 76% of their short-term reserve, though that may reflect the ball being in play
    # only 48%": claim 11 takes no reason after it (running already done is not explained by
    # the ball being out; the Narrator's prompt says so).
    Rule("11", "Claim 11 takes no reason after it: say what the running would leave a typical "
         "professional, and give a reason for the running in its own sentence",
         r"short-term reserve\b[^.]*\b((may|might|could) (reflect|be (down to|due to)))\b"
         r"|short-term reserve\b[^.]*\b(because|due to|partly|given)\b[^.]*\b(ball|possession|"
         r"lead|score|stoppage|came on|substitut)"),
    # 33: the player's own state.
    Rule("33", "About the player's own state; say what the running would cost a typical "
         "professional (claim 11)",
         rf"(\b(he|she|they)\s*(is|'s|’s|are|was|were|looks?|seems?|appears?)|{NAME}\s+"
         rf"(is|was|looks|seems))\s+(\w+\s+)?{STATE}\b"),
    Rule("33", "A percentage of the player himself; say what it would leave a typical "
         "professional", r"\b(he|she|he's|she's)\s*(is|'s|’s|was)?\s*(at|down to|on)\s+"
         r"(about\s+)?\d+\s*(%|percent)"),
    # The same as a share (the decision 30 feeds: "he fell to about 0.64 of a typical
    # professional's short-term reserve; right now he's at about 0.68").
    Rule("33", "A share of the player himself; say what the running would leave a typical "
         "professional", r"\b(he|she|he's|she's)\s*(is|'s|’s|was)?\s*(at|down to|on|fell to|"
         r"dropped to)\s+(about\s+)?(0?\.\d+|\d+\s*(%|percent))"),
    Rule("33", "The player's battery; say what the running would leave a typical professional",
         r"\b(his|her|their)\s+battery\b", unless=r"typical professional"),
    # Found on the deployed site (2026-10-18): "so this may not be only fatigue" says he is partly
    # fatigued; the LLM pass read it as a hedge in every run (decision 29).
    Rule("33", "Fatigue as part of the reason is a statement about the player's own state",
         r"\b(not|isn'?t|is not|wasn'?t)\s+(be\s+)?(only|just|entirely|purely|all|simply)\s+"
         r"(down to\s+)?(fatigue|tiredness|being tired)\b|\bpartly\s+(fatigue|tiredness|tired)\b|"
         r"\b(some|a bit of|an element of)\s+(fatigue|tiredness)\b"),
    # G10 (decision 29): field names the LLM copied from the facts ("times_exposed_so_far = 3").
    Rule("G10", "A field name on screen; write plain English", r"\b[a-z]+(?:_[a-z0-9]+)+\b"),
    # Found in the decision 30 feeds: the field name typical_pro_battery_now as "his typical-pro
    # battery", the old names as "that hardest spell", and a reason pinned to the battery wording.
    Rule("33", "The player's battery, even \"typical-pro\"; say what the running would leave a "
         "typical professional", r"\b(his|her)\s+([\w-]+\s+){0,2}typical[- ]pro(fessional)?('s)?\s+"
         r"(short-term\s+)?(battery|reserve)\b"),  # "reserve", "estimated": decision 37 feeds
    Rule("G10", "Our name for the window is \"his hardest minutes\", never a spell (decision 30)",
         r"\b(hardest|intense|red-zone)\s+spell\b|\bhardest minutes\b[^.]*\bspell\b"),
    Rule("G9", "The typical-professional wording describes the running done; nothing explains "
         "it away", r"\breserve\b[^.]*\b(explains?|explained|because of|due to|down to)\b"),
    # Found in the decision 30 feeds: "Forty-three percent of Albion's high-speed running…", a
    # number spelled out, which the numbers check (N1) and the baseline rules (G1) cannot read.
    Rule("G1", "Write percentages in digits, so their baseline and number can be checked",
         r"\b(" + SPELLED + r")([- ](" + SPELLED + r"))?\s+(percent|per cent)\b"),
    # Found on the site's feed (decision 30, 24:37): claim 4 pinned on a player who ran at
    # 1 m/s ("…and this is one of those moments for Marco Tarvsall").
    Rule("4", "Claim 4 is about transitions in general; it says nothing about this player's "
         "running (give his measured speed instead)",
         r"hardest running of the game\b[^.]*\b(for|by|from)\s+(him|[A-Z]\w+)\b|"
         r"\b(he|[A-Z]\w+)\s+(is|was)\s+(doing|making)\s+the hardest running\b"),
    # G5 (decision 30): a share of the running in a situation needs the share of the time.
    Rule("G5", "A share of the running in a situation needs how much of the time it took (G5)",
         r"\d+\s*%[^.]*\bhigh-speed running\b[^.]*\b(came|happened|was done)\b[^.]*\bafter\b",
         unless=r"\bof the time\b|\btime the ball was in play\b|\bball-in-play time\b|"
         r"\bper minute\b"),
    # Found on the site's feed (story_h04, 74:59): "Albion doing 0% more high-speed running" for
    # two teams that were level.
    Rule("G10", "A 0% difference is \"level\"; say so in words",
         r"(?<![\d.,])0\s*(%|percent|per cent)\s*(more|less|fewer|above|below|higher|lower|"
         r"ahead|behind|up|down|difference)\b"),
    Rule("33", "\"Running on empty\" is about the player's own state",
         r"running on empty|out of gas|on fumes|nothing left in the tank"),
    Rule("19c", "Never \"empty\" or \"exhausted\" from the battery (claim 19c)",
         r"\b(battery|tank|reserve)\b[^.]*\b(empty|drained|flat|dead)\b"),
    Rule("G9", "A share of the player's own reserve; use the typical-professional wording",
         r"\d+\s*(%|percent)\s+of\s+(his|her|their own)\s+(reserve|battery|D′|D')"),
    Rule("G9", "Give the short-term reserve as a percentage (e.g. 59%), not a raw decimal",
         r"\b0\.\d+\s+of\s+(a\s+|their\s+|the\s+)?(typical\s+professional'?s\s+)?(short-term\s+)?"
         r"reserve\b|\breserve\b[^.]*\(\s*(?:about\s+)?0\.\d+\s*\)"),
    Rule("2", "Claim 2 is about recovery time; keep 'shaken off' or 'recover'",
         r"\b(five-minute spell|five hard minutes)\s+takes?\b", unless=r"shaken off|recover"),
    # 20–22: errors blamed on fatigue.
    Rule("20", "Pass accuracy holds up under fatigue in matches (claim 20)",
         r"(misplac\w*|wayward|sloppy|errant|stray|poor|bad|loose)\s+(pass|touch)|"
         r"gave (the ball|it|possession) away|misplaced", needs=FATIGUE),
    Rule("21", "Decisions and concentration are not shown to fail with fatigue (claim 21)",
         r"(bad|poor|wrong|rash)\s+decision|lost (his |her )?concentration|switched off|"
         r"mental lapse", needs=FATIGUE),
    Rule("22", "Shooting success is unchanged with fatigue (claim 22)",
         r"missed (the|a|his|her|that) (shot|chance|sitter|header)|shot (wide|over)|skied",
         needs=FATIGUE),
    Rule("23", "Intense accelerations are not suppressed after peaks (claim 23)",
         r"can(no|'|’)?t accelerate|unable to accelerate|lost (his|her) acceleration|"
         r"no acceleration left"),
    # 24 / G1: percentages.
    Rule("24", "A percentage without its baseline (vs his match average, vs his peak, vs the "
         "first 15 min)", r"\d+\s*(%|percent)", unless=BASELINE),
    Rule("24", "A drop this large is vs the peak, not \"below normal\" (claim 24)",
         r"\b([6-9]\d|100)\s*(%|percent)[^.]*\b(less than|below|under)\s+(his |her |their )?"
         r"(normal|usual|match average|average)", sourced_ok=True),
    # 25–29.
    Rule("25", "Lactate does not track temporary fatigue (claim 25)", r"\blact(ic|ate)\b",
         unless=NEGATED_LACTIC),
    Rule("26", "Carry-over from earlier matches is not modelled (claim 26)",
         r"(from|after) (wednesday|tuesday|thursday|midweek|last week|the last|the previous)"
         r"('s)?\s*(match|game|fixture)|fixture congestion|midweek (match|game)",
         needs=FATIGUE),
    Rule("27", "No heart-rate data (claim 27)", r"\b(heart rate|pulse)\b|\b\d+\s*bpm\b"),
    Rule("28", "Not supported: role effects on space are small and similar (claim 28)",
         r"tired (forwards|strikers|attackers|wingers)[^.]*space|"
         r"(forwards|strikers) lose the most space"),
    Rule("29", "A player's physiology is assumed, never measured from tracking (claim 29)",
         r"\b(his|her|their)\s+(critical speed|CS|D′|D'|VO2 ?max|VO₂max|lactate threshold|"
         r"anaerobic threshold)\b[^.]*\d|critical speed (from|in) (this|the) (match|game)",
         unless=r"assumed|model parameter"),
    # 30–32, 34.
    Rule("30", "Winners outrun losers only slightly; no causal claim (claim 30)",
         r"\b(won|win|wins|beat)\b[^.]*\bbecause\b[^.]*\b(ran|run|running|outran|covered|"
         r"work rate)\b|\boutran\b[^.]*\b(so|and|which is why)\b[^.]*\b(won|win)\b|"
         r"\bran (more|further)\b[^.]*\bso\b[^.]*\b(won|win)\b"),
    Rule("31", "In-possession running goes with fewer points, not better play (claim 31)",
         r"ran (more|further) (with|in possession of) the ball[^.]*\b(better|won)\b"),
    Rule("32", "Acceleration counts differ ~10-fold between tracking systems (claim 32)",
         r"\baccelerations?\b[^.]*\b(than|above|below|compared (with|to))\b[^.]*"
         r"\b(league|published|premier league|norm|typical player|other players|average)\b"),
    Rule("34", "Running in a match does not show fitness (claim 34)",
         r"\b(ran|covered|running|distance)\b[^.]*(\b(so|which means|shows?|proves?)\b|:)[^.]*"
         r"\b(fitter|fittest|unfit|fitness)\b|\b(fitter|fittest|unfit)\b[^.]*"
         r"(\b(because|as)\b|:)[^.]*\b(ran|covered|running|distance)\b"),
    # 35, 38: team-level fatigue, and effort or intent read from speed.
    Rule("35", "Which team is more tired is not measurable from positions (claim 35); compare "
         "the running per ball-in-play minute instead",
         r"\b(fresher|more tired|tireder|less tired|wearier|fitter|more exhausted)\s+(team|side|"
         r"of the two|XI)\b|\b(team|side|XI)s?\b[^.]{0,40}\b(is|are|look|looks|seem|seems)\s+"
         r"(\w+\s+)?(tired|tiring|fresher|exhausted|fatigued|fitter|leggy|spent)\b|"
         r"\b(tired|tiring|exhausted|fatigued|leggy)\s+(team|side|XI)\b|"
         r"\b(look|looks|are|is|seem|seems)\s+(\w+\s+)?(tired|tiring|exhausted|fatigued|leggy|"
         r"spent)\s+as an? (team|side|unit)\b"),
    Rule("38", "Speed shows what a player did, not whether he tried (claim 38); give the speed "
         "and the gap",
         r"\b(didn'?t|did not|never|couldn'?t be bothered to|not)\s+(try|trying|bother|bothered|"
         r"track back|run back|chase|interested)\b|\bgave up\b|\bgiving up\b|\blazy\b|"
         r"\blaziness\b|\bjogg(ed|ing) back\b|\bwalk(ed|ing) back\b|\bshould have (sprinted|"
         r"run|chased|tracked|gone)\b|\bwork-?shy\b|\bno effort\b|\bhalf-?hearted\w*\b|"
         r"\black of (effort|commitment|intensity)\b"),
    # 39 (decision 30): pressing is a purpose. A positions-only rule for it scored precision 0.21
    # against the generator's hidden purposes (validate/purposes.py), so say where the ball was.
    Rule("39", "Pressing is what a run meant to do, which positions do not show (claim 39); say "
         "where the ball was and who had it",
         r"\b(press|presses|pressed|pressing|presser|high press|counter-?press\w*)\b|"
         r"\bclos(e|es|ed|ing)\s+([\w'-]+\s+){0,2}down\b", unless=r"\bgenerated with\b"),
    # Qualified claims used without their qualifier.
    Rule("10", "Top speed barely changes in matches; only \"a bit slower than earlier\" "
         "(claim 10)", r"lost (his|her) (pace|speed|legs)|no pace left|no legs left"),
    Rule("19d", "Never about one player's choices (claim 19d)",
         r"saving (himself|herself|his legs|her legs)|pacing (himself|herself)|conserving "
         r"(his|her) energy"),
    Rule("17", "Pitch control with fatigue is a model view (claim 17)", r"\bspace\b",
         needs=FATIGUE, unless=r"model|we estimate|estimate"),
    # G2: estimate language for statements about a player.
    Rule("G2", "Fatigue statements about a player need estimate language or the "
         "typical-professional wording", FATIGUE, needs=PERSON, unless=HEDGE),
    # Analyst-only claims in fan mode.
    Rule("16", "Lab-only finding: analyst mode only (claims 9c, 16, 19d)",
         r"\bin lab (tests|simulations)\b|\blab simulations\b", fan_only=True),
    Rule("18", "A weak association in one league: analyst mode only (claim 18)",
         r"\bin one league\b", fan_only=True),
    Rule("19", "Acceleration–speed profiles: analyst mode only, low confidence (claim 19)",
         r"acceleration(-|–| )?(speed )?profile", fan_only=True),
)  # fmt: skip


@dataclass(frozen=True)
class Finding:
    claim: str
    message: str


@dataclass(frozen=True)
class Verdict:
    sentence: str
    ok: bool
    findings: tuple[Finding, ...]


@cache
def register() -> dict:
    """The claims register (synthesis §5) as data."""
    return json.loads(REGISTER.read_text())


def register_row(claim_id: str) -> dict | None:
    """One row of the register (a claim or a global rule), or None."""
    reg = register()
    return next((r for r in reg["claims"] + reg["global_rules"] if r["id"] == str(claim_id)), None)


def _found(pattern: str, text: str) -> bool:
    return re.search(pattern, text, FLAGS) is not None


def numbers_in(obj) -> list[float]:
    """Every number in a context or facts structure (values, scores, clock labels)."""
    if isinstance(obj, bool) or obj is None:
        return []
    if isinstance(obj, int | float):
        return [float(obj)] if obj == obj else []
    if isinstance(obj, str):
        return [float(x.replace(",", ".")) for x in re.findall(NUMBER, obj)]
    if isinstance(obj, dict):
        return [x for v in obj.values() for x in numbers_in(v)]
    if isinstance(obj, list | tuple):
        return [x for v in obj for x in numbers_in(v)]
    return []


def _traced(x: float, known: list[float]) -> bool:
    """x is one of the known numbers, rounded (fan mode says "about 40%"), as a percentage of a
    share, as km/h of a speed in m/s, or as the size of a change ("30% below" for −30)."""
    for a in known:
        for b in (a, 100.0 * a, 3.6 * a, abs(a)):
            if abs(x - b) <= max(0.6, 0.08 * abs(b)):
                return True
    return False


def _all_traced(text: str, context: dict) -> bool:
    known = numbers_in(context)
    bare = re.sub(WINDOW, " ", text, flags=FLAGS)
    return all(_traced(float(x.replace(",", ".")), known) for x in re.findall(NUMBER, bare))


def from_facts(text: str, facts: dict, wording: str = "") -> bool:
    """The sentence gives numbers, every one of them from the facts and not all of them in the
    claim's ``wording``: a measured fact, whatever claim it was tagged with (decision 29)."""
    bare = re.sub(WINDOW, " ", text, flags=FLAGS)
    found = [float(x.replace(",", ".")) for x in re.findall(NUMBER, bare)]
    own = numbers_in(wording)
    return (bool(found) and _all_traced(text, {"facts": facts})
            and not all(_traced(x, own) for x in found))  # fmt: skip


def context_findings(text: str, context: dict, claim_id: str | None) -> list[Finding]:
    """The checks that need the match: rule 2 (claim 13) and N1."""
    out = []
    reasons = [r["code"] for r in context.get("non_fatigue_reasons", [])]
    if reasons and _found(TIRED, text) and not _found(NOT_FATIGUE, text):
        if not any(_found(NAMES_REASON.get(code, r"$^"), text) for code in reasons):
            listed = ", ".join(r["text"] for r in context["non_fatigue_reasons"])
            out.append(
                Finding(
                    "13",
                    f"Context check: {listed}; name it or use neutral words "
                    "such as 'ran less' (rule 2, claim 13)",
                )
            )
    # A team moment (decision 30): fatigue words there read as the team's own state, even in a
    # general wording such as claim 4's "tired legs get exposed".
    if context.get("team_moment") and _found(FATIGUE, text) and not _found(NOT_FATIGUE, text):
        out.append(Finding("35", "A team moment: fatigue words read as the team's own state "
                           "(claim 35); give the measured running instead"))  # fmt: skip
    # G11 (found on the site's feed, story_h04): "45% of Albion's high-speed running" when both
    # teams are "… Albion"; a word the two names share does not say which team.
    names = context.get("team_names") or []
    if len(names) == 2:
        shared = set(names[0].split()) & set(names[1].split())
        bare = re.sub("|".join(map(re.escape, names)), " ", text)
        if any(re.search(rf"\b{re.escape(w)}\b", bare) for w in shared):
            out.append(Finding("G11", f"Name the team in full: {' and '.join(names)} share a "
                               "word, so it alone does not say which team (G11)"))  # fmt: skip
    # Claim 2 is about published 1- and 5-min peaks in general; given as the reason for one
    # player's running after a stretch of his own (a 76 s and a 197 s one in the feeds), it is
    # a general finding used as his, which only the LLM pass caught, sometimes.
    if (
        (str(claim_id) == "2" or _found(CLAIM_2, text))
        and _found(PERSON, text)
        and _found(DURATION, text)
    ):
        out.append(Finding("2", "Claim 2 is a general finding about 1- and 5-minute peaks; give "
                           "his own numbers on their own, not as its example"))  # fmt: skip
    if str(claim_id) == "2" and not _found(r"shaken off|recover", text):
        out.append(Finding("2", "Claim 2 is about recovery time; keep 'shaken off' or "
                           "'recover'"))  # fmt: skip
    # G12 (decision 37, found on the site's feed): "Marco Tarvsall: losing the ball forces the
    # hardest running of the game." A published finding opened with a player's name reads as
    # being about him (he had jogged). Measured templates ("fact") may open with his name.
    named = re.match(r"\s*[A-Z][\w'-]+(?: [A-Z][\w'-]+)+:\s", text)
    if named and claim_id is not None and str(claim_id) != "fact":
        out.append(Finding("G12", "A published finding opened with a player's name reads as "
                           "being about him; give it as a general finding, his own numbers "
                           "apart"))  # fmt: skip
    # G5 (decision 37 feed, 59:59): "Westerlyn Albion ran 234 m/min without the ball" is the
    # team's high-speed running; without the word it reads as all running. Decision 38's feed
    # (31:38): "He averaged 23 m/min." for one player, so it holds for players too.
    if (
        "facts" in context
        and re.search(r"\d\s*m\s*(/\s*min|per\s+minute|a\s+minute)", text)
        and not re.search(r"high-speed|above 5\.5|sprint", text)
    ):
        out.append(Finding("G5", "Say which running the metres per minute are: high-speed "
                           "running (above 5.5 m/s)"))  # fmt: skip
    # G5 (decision 39 feed, 52:00): "did 96% less running than his match average" was his
    # high-speed running; his running in all fell nowhere near 96%.
    elif (
        "facts" in context
        and re.search(r"\d\s*%\s*(less|more|lower|higher|below|above|fewer)\s+running\b", text,
                      FLAGS)
        and not re.search(r"high-speed|high-intensity|above 5\.5|sprint", text, FLAGS)
    ):  # fmt: skip
        out.append(Finding("G5", "Say which running the percentage is about: high-speed "
                           "running (above 5.5 m/s)"))  # fmt: skip
    # G10 (decision 38 feed, 45+1:04): "were level at 1–1" in a block where one team did 5% more;
    # "level" is a difference of 0% (decision 31).
    gap = (context.get("facts") or {}).get("vs_opponent")
    gap = gap.get("value") if isinstance(gap, dict) else gap
    if isinstance(gap, int | float) and abs(gap) >= 0.5 and re.search(r"\blevel\b", text):
        out.append(Finding("G10", f"\"Level\" means no difference; the teams were {abs(gap):.0f}% "
                           "apart in this block"))  # fmt: skip
    # G13 (decision 38, found on the site's feed, 86:33): "while his team sat on a 3–0 lead" at
    # 5–2, claim 13's example scoreline copied; each number was in the facts (lead 3, 0 touches).
    score = context.get("score") or (context.get("context") or {}).get("score")
    if isinstance(score, dict) and {"home", "away"} <= score.keys():
        actual = sorted((int(score["home"]), int(score["away"])))
        for m in re.finditer(SCORELINE, text, FLAGS):
            a, b = (int(x) for x in m.groups() if x is not None)
            if sorted((a, b)) != actual:
                was = f"{score['home']}–{score['away']}"
                out.append(Finding("G13", f"The score was {was} (home–away); a scoreline is "
                                   "the score at that moment"))  # fmt: skip
                break
    # G14 (decision 38 feed, 75:59): "only 1% above the player he replaced over the same
    # minutes"; the replaced player's rate is over his own minutes on the pitch.
    if re.search(r"\bhe replaced\b[^.;]*\bsame minutes\b", text) and not re.search(
        r"team-?mates", text
    ):
        out.append(Finding("G14", "The player he replaced is compared over that player's own "
                           "minutes, not the same minutes; only the team-mates are"))  # fmt: skip
    offered = context.get("claims_offered")
    if offered is not None and claim_id and str(claim_id) not in offered:
        out.append(Finding(str(claim_id), f"Claim {claim_id} is not offered for this moment "
                           f"(offered: {', '.join(offered) or 'none'}; decision 25)"))  # fmt: skip
    facts = context.get("facts") or {}
    if "facts" in context and (str(claim_id) == "14" or _found(FEWER_TOUCHES, text)):
        if "touches_last_5min" not in facts:
            out.append(Finding("14", "Fewer touches needs the measured touch counts in the facts "
                               "(claim 14, decision 25)"))  # fmt: skip
        elif not facts.get("fewer_touches_than_usual"):
            out.append(Finding("14", "The touch counts do not show fewer touches than his match "
                               "so far (claim 14)"))  # fmt: skip
    # 19c (decision 41, 38:26 of the site's feed): "the lowest point of his match so far" with
    # the battery at 0.620 and an earlier low of 0.618, both shown as 0.62.
    if (
        "facts" in context
        and re.search(r"\blowest point\b", text, FLAGS)
        and not facts.get("at_lowest_point_so_far")
    ):
        out.append(Finding("19c", "\"The lowest point of his match so far\" needs the running to "
                           "leave a typical professional lower now than at any earlier second "
                           "(at_lowest_point_so_far)"))  # fmt: skip
    if "facts" in context:
        known = numbers_in(context)
        if claim_id and str(claim_id) not in EXAMPLE_WORDING:
            row = next((c for c in register()["claims"] if c["id"] == str(claim_id)), None)
            known += numbers_in(row.get("wording", "")) if row else []
        bare = re.sub(WINDOW, " ", text, flags=FLAGS)
        loose = [x for x in re.findall(NUMBER, bare)
                 if not _traced(float(x.replace(",", ".")), known)]  # fmt: skip
        if loose:
            out.append(
                Finding("N1", f"Number(s) {', '.join(loose)} not in the data or the cited claim")
            )
    return out


def verify(
    sentence: str, mode: Mode = "fan", context: dict | None = None, claim_id: str | None = None
) -> Verdict:
    """Check one sentence against the fixed rules; ``ok`` only if none fires. ``context``: the
    moment's context and facts (adds the context check and the numbers check); ``claim_id``:
    the register row the sentence was written from."""
    # The LLM writes non-breaking hyphens ("team‑mates", U+2011): the patterns expect "-".
    text = sentence.replace("’", "'").replace("‑", "-").replace("‐", "-")
    findings = []
    for rule in RULES:
        if rule.fan_only and mode != "fan":
            continue
        if not _found(rule.pattern, text):
            continue
        if rule.needs and not _found(rule.needs, text):
            continue
        if rule.unless and _found(rule.unless, text):
            continue
        if rule.sourced_ok and context and "facts" in context and _all_traced(text, context):
            continue
        findings.append(Finding(rule.claim, rule.message))
    if context:
        findings += context_findings(text, context, claim_id)
    return Verdict(sentence, not findings, tuple(dict.fromkeys(findings)))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m runningbattery.agents.verifier", description=__doc__
    )
    parser.add_argument("sentences", nargs="+")
    parser.add_argument("--mode", choices=["fan", "analyst"], default="fan")
    args = parser.parse_args(argv)
    for s in args.sentences:
        v = verify(s, args.mode)
        print(("PASS  " if v.ok else "BLOCK ") + s)
        for f in v.findings:
            print(f"      claim {f.claim}: {f.message}")


if __name__ == "__main__":
    main()
