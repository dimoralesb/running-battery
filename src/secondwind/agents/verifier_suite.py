"""The Verifier suite (BUILD_PLAN §3, run 7; v2 2026-10-17) and its report.

``python -m secondwind.agents.verifier_suite [--llm] [--json docs/verifier_report.json]``

Four sets:
- ``VALID`` (35) and ``BLOCKED`` (38): v1 plus claims 35–38, the register's wordings and
  the blocked claims of synthesis §5.3; the rules must get all of them right
  (tests/test_verifier.py).
- ``PARAPHRASES`` (21): blocked claims in other words, written before the rules were run on
  them and never used to tune the rules. What the rules miss here is what the LLM pass is for.
- ``CONTEXT`` (37): sentences with a moment's context (rule 2, claim 13) or facts (N1): a 3–0
  lead, the start of the second half, just subbed on, a long stoppage, possession, a low
  first-half load, and numbers that are or are not in the data. Each says whether it should pass.

The report gives caught (blocked sentences that were blocked) and false blocks (valid sentences
that were blocked) for the rules alone and for rules + LLM.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from secondwind.agents.verifier import verify

# (sentence, mode): the register's own wordings (synthesis §5.1–5.2), the alternatives it offers
# for blocked claims (§5.3), and measured facts stated as facts.
VALID = [
    ("After that 5-minute spell, players typically cover about 40% less high-speed distance in "
     "the next minute than their match average. It comes back over about 5 minutes.", "fan"),
    ("Short bursts are shaken off in a minute or two. A five-minute spell takes about five "
     "minutes, and sprinting takes longer.", "fan"),
    ("In the Premier League, players make about a third fewer high-speed recovery runs right "
     "after their most intense spell than they normally do. Our estimate says he had less in "
     "the tank for this one.", "fan"),
    ("Losing the ball forces the hardest running of the game. This is where tired legs get "
     "exposed.", "fan"),
    ("His runs after that spell are shorter, and he's receiving the ball at lower speed.", "fan"),
    ("Fresh legs: substitutes typically do 15–25% more high-intensity running per minute than "
     "players who started.", "fan"),
    ("In the last 15 minutes, players typically do about a fifth less hard running than at "
     "kick-off, with longer breaks between efforts.", "fan"),
    ("He's still moving, but the high-speed runs aren't there yet.", "fan"),
    ("It isn't 'lactic acid'. Scientists think it's a short-lived disturbance in the muscle's "
     "salt balance, which clears in minutes.", "fan"),
    ("Without the ball, Premier League players typically cover about 10% more ground per minute "
     "than when they have it.", "fan"),
    ("In lab tests, about a fifth of the short-term reserve returns in the first 30 seconds of "
     "easy recovery.", "analyst"),
    ("His last few sprints were a bit slower than earlier ones.", "fan"),
    ("He has done running that would leave a typical professional at about 40% of their "
     "short-term reserve.", "fan"),
    ("A typical professional would be in the red after this about one time in three.", "fan"),
    ("About 11 km, an effort roughly like 13 km of steady running (model estimate).", "fan"),
    ("His running dropped while his team sat on a 3–0 lead, so this may be tactical rather than "
     "fatigue.", "fan"),
    ("Fewer touches, partly because the ball was out of play more.", "fan"),
    ("Players who ran hardest before the break usually do a bit less after it.", "fan"),
    ("In lab tests, tired players strike the ball a little slower and less precisely.",
     "analyst"),
    ("Model view: if he were fresh, we estimate he'd control a bit more of this area.", "fan"),
    ("Higher-placed teams tend to sprint a little more; it's a weak link, not a recipe.", "fan"),
    ("This is the lowest point of his match so far, by our estimate.", "fan"),
    ("Post-match, low confidence: his acceleration profile in the second half sits a little "
     "below the first.", "analyst"),
    ("He'd just finished a hard spell. In general, passing accuracy holds up under fatigue.",
     "fan"),
    ("He's still making short bursts, but fewer long high-speed runs.", "fan"),
    ("Both teams ran a similar amount; the difference was in what they did with it.", "fan"),
    ("His high-speed running is 30% below his match average.", "fan"),
    ("His second red-zone spell in five minutes.", "fan"),
    ("He covered 11.4 km, the most on his team.", "fan"),
    # Added 2026-10-17 with claims 35–38: team running and top speed as measured facts.
    ("Albion have done 26% more high-speed running per ball-in-play minute than Ravensholt in "
     "the first hour.", "fan"),
    ("Without the ball, Ravensholt are covering more ground per minute than with it.", "fan"),
    ("Top speed hardly drops over a match: in the Premier League, players' fastest runs late on "
     "are almost as fast as their fastest early on.", "fan"),
    ("Flat-out running is rare: Premier League players cover only about 20–30 m a match above 85% "
     "of their season top speed.", "fan"),
    ("His fastest second of the match: 8.6 m/s (31 km/h), 97% of his top speed so far.", "fan"),
    ("He ran back at 5.8 m/s (21 km/h), 70% of his top speed today, and the gap grew from 4 to "
     "9 m.", "fan"),
]  # fmt: skip

# (sentence, mode, the claim it must be blocked under): synthesis §5.3 and the unbaselined %.
BLOCKED = [
    ("He misplaced that pass because he was tired.", "fan", "20"),
    ("Fatigue caused that wayward pass.", "fan", "20"),
    ("He lost concentration because of fatigue.", "fan", "21"),
    ("He made the wrong decision there because his legs had gone.", "fan", "21"),
    ("He missed the shot because he was tired.", "fan", "22"),
    ("He can't accelerate any more after that spell.", "fan", "23"),
    ("His sprint distance is down 45%.", "fan", "24"),
    ("He covered 30% more ground.", "analyst", "24"),
    ("He ran 93% less than normal after his peak minute.", "fan", "24"),
    ("His lactic acid is building up.", "fan", "25"),
    ("Lactate is high in his legs.", "analyst", "25"),
    ("He's still tired from Wednesday's match.", "fan", "26"),
    ("His heart rate is 180 right now.", "fan", "27"),
    ("Tired forwards lose the most space.", "analyst", "28"),
    ("His critical speed is 3.8 m/s.", "analyst", "29"),
    ("His critical speed from this match is 4.2 m/s.", "fan", "29"),
    ("They won because they ran more.", "fan", "30"),
    ("City outran them, so they won.", "fan", "30"),
    ("They ran more with the ball, so they played better.", "fan", "31"),
    ("He made 95 accelerations, more than the Premier League average.", "analyst", "32"),
    ("He is tired.", "fan", "33"),
    ("He’s at 40%.", "fan", "33"),
    ("His battery is at 40%.", "fan", "33"),
    ("He is running on empty.", "fan", "33"),
    ("Saka is exhausted.", "analyst", "33"),
    ("He ran more, so he's fitter than the others.", "fan", "34"),
    ("He's the fittest player on the pitch: he covered 12 km.", "fan", "34"),
    ("His battery is empty.", "fan", "19c"),
    ("He's lost his pace.", "fan", "10"),
    ("He's saving himself for the last 15 minutes.", "analyst", "19d"),
    ("In lab tests, tired players strike the ball a little slower and less precisely.", "fan",
     "16"),
    ("He has little left in the tank.", "fan", "G2"),
    ("He's in the red.", "fan", "G2"),
    ("He has used 60% of his reserve.", "fan", "G9"),
    ("Albion are the fresher team now.", "fan", "35"),
    ("Ravensholt look tired as a side.", "fan", "35"),
    ("He didn't bother chasing his man.", "fan", "38"),
    ("He jogged back when he should have sprinted.", "fan", "38"),
]  # fmt: skip

# Blocked claims in other words (held out from the rules).
PARAPHRASES = [
    ("You can see his legs have gone, and that's why the pass went astray.", "fan", "20"),
    ("He couldn't find a team-mate because his legs were heavy.", "fan", "20"),
    ("His concentration slipped as his energy ran low.", "fan", "21"),
    ("Running out of juice, he scuffed his finish wide of the post.", "fan", "22"),
    ("There's nothing left in his legs now.", "fan", "33"),
    ("Tarvsall has hit the wall.", "fan", "33"),
    ("His reserve is down to 30%.", "fan", "33"),
    ("Albion won this because they simply outworked their opponents.", "fan", "30"),
    ("They outlasted them physically, and that's what won it.", "fan", "30"),
    ("All that extra running shows he's in better shape than the rest.", "fan", "34"),
    ("He's a yard slower than he was at kick-off.", "fan", "10"),
    ("After that spell his top speed has gone.", "fan", "10"),
    ("His VO2max is clearly higher than his team-mates'.", "analyst", "29"),
    ("The burn in his thighs tells you the acid is building.", "fan", "25"),
    ("After that sprint he has no burst left at all.", "fan", "23"),
    ("He's clearly feeling Wednesday's trip in his legs.", "fan", "26"),
    # Added 2026-10-17 with claims 35 and 38, before their rules were written.
    ("Ravensholt have run out of legs as a side.", "fan", "35"),
    ("You can see which XI has more left in the tank: it's Albion.", "fan", "35"),
    ("He didn't fancy chasing that one.", "fan", "38"),
    ("He's not putting the yards in to get back.", "fan", "38"),
    ("A lack of desire to track his runner cost them there.", "fan", "38"),
]  # fmt: skip

LEAD = {"code": "big_lead", "text": "his team leads by 3 (3–0)"}
START = {"code": "start_of_half", "text": "the first 10 min of the half"}
JUST_ON = {"code": "just_subbed_on", "text": "he came on 4 min ago"}
STOPPED = {"code": "ball_out_of_play", "text": "the ball has been out of play for 52 s"}
POSS = {"code": "team_in_possession", "text": "his team had the ball 71% of the last 5 min"}
LOW_FH = {"code": "low_first_half_load", "text": "his first-half load was 84% of the median"}
FACTS = {"facts": {"hsr_vs_match_average": {"value": -30.0, "unit": "%"},
                   "typical_pro_battery": {"value": 0.41, "unit": "share"},
                   "speed": {"value": 6.1, "unit": "m/s"}}}  # fmt: skip

TOUCHES = {"facts": {"touches_last_5min": {"value": 2, "unit": "touches"},
                     "touches_per_5min_so_far": {"value": 6.4, "unit": "touches per 5 min"},
                     "in_play_last_5min": {"value": 0.31, "unit": "share"},
                     "fewer_touches_than_usual": True}}  # fmt: skip
MORE_TOUCHES = {"facts": {"touches_last_5min": {"value": 7, "unit": "touches"},
                          "touches_per_5min_so_far": {"value": 6.4, "unit": "touches per 5 min"},
                          "fewer_touches_than_usual": False}}  # fmt: skip

HIGH = {
    "facts": {
        "typical_pro_battery_now": {"value": 0.8, "unit": "share"},
        "lowest_typical_pro_battery_so_far": {"value": 0.62, "unit": "share"},
    }
}

# (sentence, mode, context, claim id or None, should it pass?)
CONTEXT = [
    ("A typical professional would likely be in the red after running like this.", "fan",
     {"non_fatigue_reasons": [LEAD]}, "11", False),
    ("A typical professional would likely be in the red after running like this.", "fan",
     {"non_fatigue_reasons": []}, "11", True),
    ("His running dropped while his team sat on a 3–0 lead, so this may be tactical rather than "
     "fatigue.", "fan", {"non_fatigue_reasons": [LEAD]}, "13", True),
    ("His running has dropped, likely from fatigue.", "fan", {"non_fatigue_reasons": [START]},
     "13", False),
    # Ruling fatigue out needs estimate language too (G2; claim 13 says "may be tactical"). These
    # three were labelled valid in the first LLM run and relabelled after it (see the report).
    ("Just after the restart his running dropped, which is normal at the start of the second "
     "half rather than a sign of fatigue.", "fan", {"non_fatigue_reasons": [START]}, "13", False),
    ("Just after the restart his running dropped, which is normal at the start of the second "
     "half and likely not a sign of fatigue.", "fan", {"non_fatigue_reasons": [START]}, "13",
     True),
    ("He is likely tiring already.", "fan", {"non_fatigue_reasons": [JUST_ON]}, "13", False),
    ("He came on four minutes ago, so a quiet spell is him settling in, not fatigue.", "fan",
     {"non_fatigue_reasons": [JUST_ON]}, "13", False),
    ("He came on four minutes ago, so a quiet spell is probably him settling in rather than "
     "fatigue.", "fan", {"non_fatigue_reasons": [JUST_ON]}, "13", True),
    ("The data suggest fatigue is setting in.", "fan", {"non_fatigue_reasons": [STOPPED]}, "13",
     False),
    ("With the ball out of play for almost a minute, his running dropped; that is the stoppage, "
     "not fatigue.", "fan", {"non_fatigue_reasons": [STOPPED]}, "13", False),
    ("With the ball out of play for almost a minute, his running dropped; that is likely the "
     "stoppage, not fatigue.", "fan", {"non_fatigue_reasons": [STOPPED]}, "13", True),
    ("His team kept the ball for most of the last five minutes, so he ran less; likely not "
     "fatigue.", "fan", {"non_fatigue_reasons": [POSS]}, "13", True),
    ("He likely faded after the break.", "fan", {"non_fatigue_reasons": [START, LOW_FH]}, "15",
     False),
    ("He ran less after the break than before it.", "fan", {"non_fatigue_reasons": [LOW_FH]},
     "15", True),
    ("His high-speed running is 30% below his match average.", "fan", FACTS, None, True),
    ("His high-speed running is 45% below his match average.", "fan", FACTS, None, False),
    ("He has done running that would leave a typical professional at about 40% of their "
     "short-term reserve.", "fan", FACTS, "11", True),
    ("He has done running that would leave a typical professional at about 60% of their "
     "short-term reserve.", "fan", FACTS, "11", False),
    ("He reached 6.1 m/s (22 km/h) on that recovery run.", "analyst", FACTS, None, True),
    ("He reached 7.4 m/s (27 km/h) on that recovery run.", "analyst", FACTS, None, False),
    # Found in the second agent feed (2026-10-17): a percentage turned round (196 vs 160 m is
    # 22% more, but 160 is 18% less, not 22%; F1, LLM pass only).
    ("Westerlyn cover 196 m of high-speed running per ball-in-play minute while their opponents "
     "cover 160 m, roughly 22% less.", "analyst",
     {"facts": {"team_hsr_per_in_play_min": {"value": 196.0, "unit": "m"},
                "opponent_hsr_per_in_play_min": {"value": 160.0, "unit": "m"},
                "vs_opponent": {"value": 22.0, "unit": "% above (+) or below (−) the opponent"}}},
     None, False),
    # A large drop vs his match average is fine when it is the measured figure (claim 24 is
    # about unsourced ones, usually vs the peak).
    ("His high-speed running in the last 5 minutes was 86% below his match average.", "fan",
     {"facts": {"vs_match_average": {"value": -86.0, "unit": "%"}}}, None, True),
    ("His high-speed running in the last 5 minutes was 86% below his match average.", "fan",
     None, None, False),
    # Found in the first agent feed (2026-10-17): claim 11's example number copied, and a
    # "lowest point" the facts contradict (F1, LLM pass only).
    ("He has done running that would leave a typical professional at about 40% of their "
     "short-term reserve.", "fan", HIGH, "11", False),
    ("This is the lowest point of his match so far, by our estimate.", "analyst", HIGH, "19c",
     False),
    # Found in the third feeds (2026-10-17): claim 14 used with no touch counts in the facts.
    # Decision 25 adds them to not_tired_tactical moments; "fewer touches" needs them.
    ("Fewer touches, partly because the ball was out of play more.", "fan", FACTS, "14", False),
    ("Fewer touches, partly because the ball was out of play more.", "fan", TOUCHES, "14", True),
    ("He had 2 touches in the last 5 minutes against about 6 per 5 minutes in his match so far, "
     "partly because the ball was in play only 31% of the time.", "analyst", TOUCHES, "14", True),
    ("Fewer touches, partly because the ball was out of play more.", "fan", MORE_TOUCHES, "14",
     False),
    # Found in the fourth feeds (2026-10-18). The LLM blocked the post-peak window's neutral
    # name (decision 12) as physiology, 7 times in three feeds (prompt revision 3 after this).
    ("This is the third time his team have lost the ball while he was catching breath after a "
     "red-zone spell.", "fan",
     {"facts": {"times_exposed_so_far": {"value": 3, "unit": "turnovers"}}}, None, True),
    # A rewrite both passes let through: a second wind (running back above his average) put down
    # to "less opportunity to run" (F1, LLM pass only).
    ("Five minutes after his red-zone spell his high-speed running over the last two minutes was "
     "10.9 m/min, about 5% above his match average of 10.4 m/min; with the ball in play only 42% "
     "of the last five minutes this could reflect less opportunity to run rather than the "
     "player's own fatigue.", "analyst",
     {"facts": {"last_2min_hsr_per_min": {"value": 10.9, "unit": "m/min"},
                "match_average_per_min": {"value": 10.4, "unit": "m/min"},
                "vs_match_average": {"value": 5.0, "unit": "%"}},
      "context": {"in_play_last_5min": 0.42}}, None, False),
    # Found in the fifth feeds (2026-10-18): a rules false block, "the player he replaced" was
    # not read as a baseline (BASELINE fixed).
    ("Since coming on he has done 9.3 m/min, about 5% below the player he replaced (9.8 m/min).",
     "analyst", {"facts": {"sub_hsr_per_min": {"value": 9.3, "unit": "m/min"},
                           "replaced_player_hsr_per_min": {"value": 9.8, "unit": "m/min"},
                           "vs_replaced_player": {"value": -5.0, "unit": "%"}}}, None, True),
    # Found in the sixth feeds (2026-10-18): a rules false block, the LLM's non-breaking hyphen
    # ("team‑mates", U+2011) hid the baseline (the rules now read it as "-") …
    ("He has done 9.8 m/min, 25% below the player he replaced but 49% above his team‑mates "
     "over the same minutes.", "analyst",
     {"facts": {"sub_hsr_per_min": {"value": 9.8, "unit": "m/min"},
                "vs_replaced_player": {"value": -25.0, "unit": "%"},
                "vs_teammates": {"value": 49.0, "unit": "%"}}}, None, True),
    # … and a line both passes let through that reasons backwards: a 76 s spell is a short burst
    # (claim 2), not "the longer recovery" (F1, LLM pass only).
    ("Short bursts are shaken off in a minute or two, while a five-minute spell takes about five "
     "minutes to recover from; he is 6.5 min out from his 76 s spell, so this fits the longer "
     "recovery for intense work.", "analyst",
     {"facts": {"minutes_after_spell": {"value": 6.5, "unit": "min"},
                "spell_duration": {"value": 76, "unit": "s"}}}, "2", False),
    # Claims used where they do not fit (decision 25): claim 36 at 12:29, claim 7 at 45+2.
    ("Top speed hardly drops over a match: in the Premier League, players' fastest runs late on "
     "are almost as fast as their fastest early on.", "fan",
     {"facts": {}, "claims_offered": ["37", "10"]}, "36", False),
    ("In the last 15 minutes, players typically do about a fifth less hard running than at "
     "kick-off, with longer breaks between efforts.", "fan",
     {"facts": {}, "claims_offered": ["9a", "9b", "7", "30"]}, "7", True),
]  # fmt: skip


def cases() -> list[dict]:
    """Every sentence as {set, sentence, mode, context, claim, should_pass}."""
    out = [dict(set="valid", sentence=s, mode=m, context=None, claim=None, should_pass=True)
           for s, m in VALID]  # fmt: skip
    out += [dict(set="blocked", sentence=s, mode=m, context=None, claim=c, should_pass=False)
            for s, m, c in BLOCKED]  # fmt: skip
    out += [dict(set="paraphrase", sentence=s, mode=m, context=None, claim=c, should_pass=False)
            for s, m, c in PARAPHRASES]  # fmt: skip
    out += [dict(set="context", sentence=s, mode=m, context=x, claim=c, should_pass=ok)
            for s, m, x, c, ok in CONTEXT]  # fmt: skip
    return out


def rates(rows: list[dict], key: str) -> dict:
    bad = [r for r in rows if not r["should_pass"]]
    good = [r for r in rows if r["should_pass"]]
    caught = sum(not r[key] for r in bad)
    false = sum(not r[key] for r in good)
    return {"caught": f"{caught}/{len(bad)}", "false_blocks": f"{false}/{len(good)}",
            "caught_rate": round(caught / max(len(bad), 1), 3),
            "false_block_rate": round(false / max(len(good), 1), 3)}  # fmt: skip


def run_rules() -> list[dict]:
    rows = []
    for c in cases():
        # The register's own claim id is passed only with a context, as the feed does.
        v = verify(c["sentence"], c["mode"], c["context"], c["claim"] if c["context"] else None)
        rows.append(c | {"rules_ok": v.ok, "rules_findings": [f.claim for f in v.findings]})
    return rows


async def run_llm(rows: list[dict], concurrency: int = 8) -> None:
    from secondwind.agents.llm_verifier import verifier_agent, verify_full

    agent = verifier_agent()
    gate = asyncio.Semaphore(concurrency)

    async def one(r: dict) -> None:
        async with gate:
            claim = r["claim"] if r["context"] else None
            v = await verify_full(r["sentence"], r["mode"], r["context"], claim, agent)
        r["llm_ok"] = v.ok
        r["llm_stage"] = v.stage
        r["llm_findings"] = v.findings

    await asyncio.gather(*(one(r) for r in rows))


def report(rows: list[dict]) -> dict:
    out: dict = {"n": len(rows), "by_set": {}}
    keys = ["rules_ok"] + (["llm_ok"] if "llm_ok" in rows[0] else [])
    for key in keys:
        out[key.removesuffix("_ok")] = rates(rows, key)
    for name in ("valid", "blocked", "paraphrase", "context"):
        sub = [r for r in rows if r["set"] == name]
        out["by_set"][name] = {k.removesuffix("_ok"): rates(sub, k) for k in keys}
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m secondwind.agents.verifier_suite")
    parser.add_argument("--llm", action="store_true", help="also run the LLM pass (Foundry)")
    parser.add_argument("--json", type=Path, help="write the report and every verdict here")
    args = parser.parse_args(argv)
    rows = run_rules()
    if args.llm:
        asyncio.run(run_llm(rows))
    rep = report(rows)
    print(json.dumps(rep, indent=2))
    for r in rows:
        wrong = [k for k in ("rules_ok", "llm_ok") if k in r and r[k] != r["should_pass"]]
        if wrong:
            print(f"  {'/'.join(w.removesuffix('_ok') for w in wrong)} wrong [{r['set']}] "
                  f"{r['sentence']}")  # fmt: skip
    if args.json:
        args.json.write_text(json.dumps({"report": rep, "rows": rows}, indent=1,
                                        ensure_ascii=False))  # fmt: skip


if __name__ == "__main__":
    main()
