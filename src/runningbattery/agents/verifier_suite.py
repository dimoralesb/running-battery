"""The Verifier suite (BUILD_PLAN §3, run 7; v2 2026-10-17) and its report.

``python -m runningbattery.agents.verifier_suite [--llm] [--json docs/verifier_report.json]``

Five sets:
- ``VALID`` (37) and ``BLOCKED`` (40): v1 plus claims 35–39, the register's wordings and
  the blocked claims of synthesis §5.3; the rules must get all of them right
  (tests/test_verifier.py).
- ``PARAPHRASES`` (23): blocked claims in other words, written before the rules were run on
  them and never used to tune the rules. What the rules miss here is what the LLM pass is for.
- ``CONTEXT`` (64): sentences with a moment's context (rule 2, claim 13) or facts (N1): a 3–0
  lead, the start of the second half, just subbed on, a long stoppage, possession, a low
  first-half load, and numbers that are or are not in the data. Each says whether it should pass.
- ``FACT_CHECKS`` (10): F1, sentences that do or do not agree with their facts, held out like
  the paraphrases (written before prompt revision 4, never used to tune it).

The report gives caught (blocked sentences that were blocked) and false blocks (valid sentences
that were blocked) for the rules alone and for rules + LLM.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from runningbattery.agents.verifier import verify

# (sentence, mode): the register's own wordings (synthesis §5.1–5.2), the alternatives it offers
# for blocked claims (§5.3), and measured facts stated as facts.
VALID = [
    ("After a player's hardest 5 minutes, high-speed running in the next minute is typically "
     "about 40% below their match average. It comes back over about 5 minutes.", "fan"),
    ("Short bursts are shaken off in a minute or two. A five-minute spell takes about five "
     "minutes, and sprinting takes longer.", "fan"),
    ("In the Premier League, players make about a third fewer high-speed recovery runs right "
     "after their hardest minutes of the match than they normally do.", "fan"),
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
    ("A typical professional would be below half their short-term reserve after this about one "
     "time in three.", "fan"),
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
    ("His hardest minutes so far, for the second time in five minutes.", "fan"),
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
    # Added 2026-10-19 with claim 39 (decision 30): where the running happened, measured.
    ("Without the ball, with it in the opponents' third, Albion did 146 m of high-speed running "
     "per minute of that situation.", "fan"),
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
    ("Albion pressed high for the whole first half.", "fan", "39"),
    ("He closed the full-back down at 7 m/s.", "fan", "39"),
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
    # Added 2026-10-19 with claim 39 (decision 30), before its rule was written.
    ("Albion's front three hunted the ball down deep in Ravensholt's half.", "fan", "39"),
    ("They swarmed the man on the ball to win it back high up the pitch.", "fan", "39"),
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

SPLIT = {"team_moment": True, "facts": {
    "team_hsr_share_after_ball_changed_hands": {"value": 43, "unit": "% of the team's high-speed "
                                                "running in this block"},
    "time_share_after_ball_changed_hands": {"value": 29, "unit": "% of this block's ball-in-play "
                                            "time"},
    "team_hsr_per_min_after_losing": {"value": 433, "unit": "m per minute of that situation"},
    "block": "0:00–15:00"}}  # fmt: skip

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
    # Reworded with the name itself on 2026-10-18 (decision 29: "catching breath after a red-zone
    # spell" became "just after an intense spell"; prompt revision 4), and again on 2026-10-19
    # (decision 30: "just after his hardest minutes so far"; prompt revision 5).
    ("This is the third time his team have lost the ball just after his hardest minutes so far.",
     "fan",
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
    # not read as a baseline (BASELINE fixed). Reworded for decision 38 (a player's metres per
    # minute say high-speed, G5): it tests the baseline.
    ("Since coming on he has done 9.3 m/min of high-speed running, about 5% below the player he "
     "replaced (9.8 m/min).",
     "analyst", {"facts": {"sub_hsr_per_min": {"value": 9.3, "unit": "m/min"},
                           "replaced_player_hsr_per_min": {"value": 9.8, "unit": "m/min"},
                           "vs_replaced_player": {"value": -5.0, "unit": "%"}}}, None, True),
    # Found in the sixth feeds (2026-10-18): a rules false block, the LLM's non-breaking hyphen
    # ("team‑mates", U+2011) hid the baseline (the rules now read it as "-"); reworded for
    # decision 38 (G5 for players) …
    ("He has done 9.8 m/min of high-speed running, 25% below the player he replaced but 49% above "
     "his team‑mates over the same minutes.", "analyst",
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
    # Found on the deployed site (story_h04, 24:37): claim 11 followed by "may not be only
    # fatigue", which says he is partly fatigued, his own state (claim 33, G9).
    ("He has done running that would leave a typical professional at about 83% of their "
     "short-term reserve, and his team had the ball 75% of the last 5 minutes so this may not be "
     "only fatigue.", "fan",
     {"non_fatigue_reasons": [{"code": "team_in_possession",
                               "text": "his team had the ball 75% of the last 5 min"}],
      "facts": {"typical_pro_battery_now": {"value": 0.83, "unit": "share"}}}, "11", False),
    # Found in the seventh feeds (2026-10-18, decision 29): a rules false block, a baseline in
    # words ("of the last five minutes") …
    ("The ball was in play only 25% of the last five minutes.", "fan",
     {"facts": {"in_play_last_5min": {"value": 0.25, "unit": "share"}}}, None, True),
    # (and one more in the eighth feeds: "of that period")
    ("He had 0 touches in the last 5 min while the ball was in play only 25% of that period.",
     "analyst", {"facts": {"touches_last_5min": {"value": 0, "unit": "touches"},
                           "in_play_last_5min": {"value": 0.25, "unit": "share"}}}, None, True),
    # … and a field name copied into the sentence (G10; both passes let it through).
    ("This is the third time his team lost the ball just after his hardest minutes so far "
     "(times_exposed_so_far = 3).", "analyst",
     {"facts": {"times_exposed_so_far": {"value": 3, "unit": "turnovers"}}}, None, False),
    # Found in the eighth feeds (2026-10-18). Claim 3's wording ended "our estimate says he had
    # less in the tank for this one", his own state (decision 14); the LLM blocked it once and
    # passed this at 24:37 on the site's feed. The wording now stops at the finding.
    ("In the Premier League players make about a third fewer high-speed recovery runs after a "
     "peak, and our estimate says he may have had less in the tank here.", "fan",
     {"facts": {"times_exposed_so_far": {"value": 3, "unit": "turnovers"}}}, "3", False),
    # A general finding used as the reason for something it does not cover: a 197 s spell is not
    # a short burst (claim 2), and five minutes on is not "a minute or two" (F1).
    ("Five minutes after his 197 s spell his last 2 min high-speed running was 10.9 m/min, which "
     "fits the idea that short bursts are shaken off in a minute or two.", "analyst",
     {"facts": {"spell_duration": {"value": 197, "unit": "s"},
                "minutes_after_spell": {"value": 5.0, "unit": "min"},
                "last_2min_hsr_per_min": {"value": 10.9, "unit": "m/min"}}}, None, False),
    # Claims used where they do not fit (decision 25): claim 36 at 12:29, claim 7 at 45+2.
    ("Top speed hardly drops over a match: in the Premier League, players' fastest runs late on "
     "are almost as fast as their fastest early on.", "fan",
     {"facts": {}, "claims_offered": ["37", "10"]}, "36", False),
    ("In the last 15 minutes, players typically do about a fifth less hard running than at "
     "kick-off, with longer breaks between efforts.", "fan",
     {"facts": {}, "claims_offered": ["9a", "9b", "7", "30"]}, "7", True),
    # Added 2026-10-19 with the running split (decision 30), on a team moment: claim 4's "tired
    # legs" would be about the team (35); the split as a measured fact; "most" for 43% (F1, the
    # LLM pass only); and a purpose read from it (39).
    ("Losing the ball forces the hardest running of the game. This is where tired legs get "
     "exposed.", "fan", {"facts": {}, "team_moment": True, "claims_offered": ["4", "9a"]}, "4",
     False),
    ("43% of Albion's high-speed running in 0:00–15:00 came in the first 10 seconds after the "
     "ball changed hands, in 29% of the time the ball was in play.", "fan", SPLIT, None, True),
    ("Most of Albion's high-speed running in 0:00–15:00 came in the first 10 seconds after the "
     "ball changed hands.", "fan", SPLIT, None, False),
    ("Albion did 433 m of high-speed running per minute in the 10 seconds after losing the ball, "
     "pressing to win it back.", "fan", SPLIT, None, False),
    # Found in the decision 30 feeds (2026-10-19). A share of the running without the share of
    # the time (G5; the rules had blocked it as a % without a baseline) …
    ("43% of Albion's high-speed running in that block came in the first 10 s after the ball "
     "changed hands.", "fan", SPLIT, None, False),
    # … the field name typical_pro_battery_now as his battery (claim 33; both passes let it
    # through) and "spell" for his hardest minutes (G10; both passes let it through) …
    ("His typical-pro battery now is about 66% of a typical professional's short-term reserve.",
     "analyst", {"facts": {"typical_pro_battery_now": {"value": 0.66, "unit": "share"}}}, None,
     False),
    ("His hardest-minute peak was 86 m in 1 min, with that hardest spell lasting 35 s.", "analyst",
     {"facts": {"hardest_minutes_peak_1min_hsr": {"value": 86, "unit": "m in 1 min"},
                "hardest_minutes_duration": {"value": 35, "unit": "s"}}}, None, False),
    # … a non-fatigue reason pinned to the typical-pro wording (G9; both passes let it through) …
    ("He has done running that would leave a typical professional at about 56% of their "
     "short-term reserve, but the two-goal lead may explain some of it.", "fan",
     {"non_fatigue_reasons": [{"code": "big_lead", "text": "his team leads by 2 (3–1)"}],
      "facts": {"typical_pro_battery_now": {"value": 0.56, "unit": "share"}}}, "11", False),
    # … a percentage spelled out, which the numbers check cannot read (both passes let it
    # through, tagged with claim 9b; G1) …
    ("Forty-three percent of Albion's high-speed running in that block came in the first 10 s "
     "after the ball changed hands.", "fan", SPLIT, "9b", False),
    # … a rules false block in the last feeds (G5 did not read "ball-in-play time") …
    ("62% of Albion's high-speed running in this block came in the first 10 s after the ball "
     "changed hands, in 28% of the block's ball-in-play time.", "analyst",
     {"team_moment": True, "facts": {
         "team_hsr_share_after_ball_changed_hands": {"value": 62, "unit": "% of the team's "
                                                     "high-speed running in this block"},
         "time_share_after_ball_changed_hands": {"value": 28, "unit": "% of this block's "
                                                 "ball-in-play time"}}}, None, True),
    # … claim 4 pinned on the player at 24:37 on the site's feed, while his own speed in the clip
    # was about 1 m/s (both passes let it through) …
    ("Losing the ball forces the hardest running of the game, and this is one of those moments "
     "for Marco Tarvsall.", "fan",
     {"facts": {"mean_speed_next_8s": {"value": 3.1, "unit": "m/s"}},
      "claims_offered": ["4", "3", "11"]}, "4", False),
    # … and again on the decision 37 feed (14:20), as a name and a colon, while he jogged (top
    # 4.6 m/s); both passes let it through, and the G12 rule was written from it. The finding
    # on its own is fine.
    ("Marco Tarvsall: losing the ball forces the hardest running of the game.", "fan",
     {"facts": {"mean_speed_next_8s": {"value": 3.9, "unit": "m/s"}},
      "claims_offered": ["4", "3", "11"]}, "4", False),
    ("Losing the ball forces the hardest running of the game.", "fan",
     {"facts": {"mean_speed_next_8s": {"value": 3.9, "unit": "m/s"}},
      "claims_offered": ["4", "3", "11"]}, "4", True),
    # … his own "typical-pro reserve" (35:17; rule 33 read only "battery"), and a team's
    # metres per minute without saying they are high-speed running (59:59); the rules were
    # extended from them. The worded-out versions are fine.
    ("He did hardly any high-speed running in the last 5 min while his typical-pro short-term "
     "reserve estimate is about 91% (band 82–96%).", "analyst",
     {"facts": {"typical_pro_battery": {"value": 0.91, "unit": "share"}}}, None, False),
    ("He came on 10 min ago and his estimated typical-pro short-term reserve is about 85%.",
     "analyst", {"facts": {"typical_pro_battery": {"value": 0.85, "unit": "share"},
                           "minutes_on": {"value": 10, "unit": "min"}}}, None, False),
    ("In 45:00–60:00 Westerlyn Albion ran 234 m/min without the ball and 214 m/min with the "
     "ball.", "fan",
     {"team_moment": True, "team_names": ["Westerlyn Albion", "Ravensholt Albion"],
      "facts": {"team_hsr_per_min_without_ball": {"value": 234, "unit": "m/min"},
                "team_hsr_per_min_with_ball": {"value": 214, "unit": "m/min"},
                "block": "45:00–60:00"}}, None, False),
    ("In 45:00–60:00 Westerlyn Albion did 234 m of high-speed running per minute without the "
     "ball and 214 m with it.", "fan",
     {"team_moment": True, "team_names": ["Westerlyn Albion", "Ravensholt Albion"],
      "facts": {"team_hsr_per_min_without_ball": {"value": 234, "unit": "m/min"},
                "team_hsr_per_min_with_ball": {"value": 214, "unit": "m/min"},
                "block": "45:00–60:00"}}, None, True),
    # Found on the site's feed (decision 38, 86:33): claim 13's example scoreline copied word
    # for word at 2–5 (his team three up); each number was in the facts (a lead of 3, 0 touches)
    # and both passes let it through. G13 was written from it. The true scoreline is fine.
    ("His running dropped while his team sat on a 3–0 lead, so this may be tactical rather than "
     "fatigue.", "fan",
     {"context": {"score": {"home": 2, "away": 5}, "lead": {"value": 3, "unit": "goals"}},
      "non_fatigue_reasons": [{"code": "big_lead", "text": "a big lead (2–5)"}],
      "facts": {"touches_last_5min": {"value": 0, "unit": "touches"}},
      "claims_offered": ["13", "14", "9b"]}, "13", False),
    ("His running dropped while his team sat on a 5–2 lead, so this may be tactical rather than "
     "fatigue.", "fan",
     {"context": {"score": {"home": 2, "away": 5}, "lead": {"value": 3, "unit": "goals"}},
      "non_fatigue_reasons": [{"code": "big_lead", "text": "a big lead (2–5)"}],
      "facts": {"touches_last_5min": {"value": 0, "unit": "touches"}},
      "claims_offered": ["13", "14", "9b"]}, "13", True),
    # Found on the site's feed (decision 38): a player's metres per minute without saying they
    # are high-speed running (31:38; G5 read only team moments), and "level" for two teams 5%
    # apart, in an LLM rewrite that also slipped in the score (45+1:04; G10 now reads "level"
    # against the gap). Both passes let them through; the worded-out versions are fine.
    ("He averaged 23 m/min.", "fan",
     {"facts": {"last_2min_hsr_per_min": {"value": 23.4, "unit": "m/min"}}}, None, False),
    ("He averaged 23 m of high-speed running per minute in the last 2 minutes.", "fan",
     {"facts": {"last_2min_hsr_per_min": {"value": 23.4, "unit": "m/min"}}}, None, True),
    ("Westerlyn Albion and Ravensholt Albion were level at 1–1 in 30:00–45+1:05; earlier in the "
     "match Westerlyn Albion's high-speed running was 91% higher than Ravensholt Albion's.",
     "analyst",
     {"team_moment": True, "team_names": ["Westerlyn Albion", "Ravensholt Albion"],
      "context": {"score": {"home": 1, "away": 1}},
      "facts": {"vs_opponent": {"value": 5, "unit": "%"},
                "earlier_gap_vs_opponent": {"value": 91, "unit": "%"},
                "block": "30:00–45+1:05"}}, None, False),
    ("In 30:00–45+1:05 Westerlyn Albion did 5% more high-speed running per ball-in-play minute "
     "than Ravensholt Albion, down from 91% more earlier.", "analyst",
     {"team_moment": True, "team_names": ["Westerlyn Albion", "Ravensholt Albion"],
      "context": {"score": {"home": 1, "away": 1}},
      "facts": {"vs_opponent": {"value": 5, "unit": "%"},
                "earlier_gap_vs_opponent": {"value": 91, "unit": "%"},
                "block": "30:00–45+1:05"}}, None, True),
    # … and "over the same minutes" for the player he replaced, whose rate is over his own
    # minutes on the pitch (75:59; G14 was written from it). With the team-mates it is right.
    ("He is only 1% above the player he replaced over the same minutes.", "fan",
     {"facts": {"sub_hsr_per_min": {"value": 15.5, "unit": "m/min"},
                "vs_replaced_player": {"value": 1, "unit": "%"},
                "vs_teammates": {"value": 64, "unit": "%"}}}, None, False),
    ("He did 64% more high-speed running per minute than his team-mates over the same minutes "
     "and 1% more than the player he replaced.", "fan",
     {"facts": {"sub_hsr_per_min": {"value": 15.5, "unit": "m/min"},
                "vs_replaced_player": {"value": 1, "unit": "%"},
                "vs_teammates": {"value": 64, "unit": "%"}}}, None, True),
    # … the player's own state as a share, in an LLM rewrite on the site's feed (claim 33; the
    # rule read only percentages), a raw reserve decimal in natural's feed (43:44, G9), and
    # claim 2's middle clause cut off from its recovery verb …
    ("Earlier in the match he fell to about 0.64 of a typical professional's short-term reserve; "
     "right now he's at about 0.68, by our estimate.", "analyst",
     {"facts": {"typical_pro_battery_now": {"value": 0.68, "unit": "share"},
                "lowest_typical_pro_battery_so_far": {"value": 0.64, "unit": "share"}}}, "19c",
     False),
    ("By our estimate, his running has left a typical professional at about 0.59 of their "
     "short-term reserve — marginally above his lowest point this match (0.56).", "analyst",
     {"facts": {"typical_pro_battery_now": {"value": 0.59, "unit": "share"},
                "lowest_typical_pro_battery_so_far": {"value": 0.56, "unit": "share"}}}, "19c",
     False),
    ("A five-minute spell takes about five minutes.", "fan",
     {"facts": {"minutes_after_hardest_minutes": {"value": 5.0, "unit": "min"}}}, "2", False),
    # … and claim 3 used as the lead-in to his own speed after a turnover, which reads as fewer
    # recovery runs from him because of his hardest minutes (the LLM rewrote it into this).
    ("In the Premier League, players make about a third fewer high-speed recovery runs right "
     "after their hardest minutes than they normally do; here his mean speed in the next 8 s was "
     "3.7 m/s and he was 44 m from the ball 8 s later.", "analyst",
     {"facts": {"mean_speed_next_8s": {"value": 3.7, "unit": "m/s"},
                "distance_to_ball_8s_later": {"value": 44, "unit": "m"},
                "window_after_turnover": {"value": 8, "unit": "s"}}}, None, False),
    # Found on the site's feed (story_h04, 74:59, 2026-10-19): "0% more" for two teams that were
    # level (G10; the Narrator's prompt forbids it, no rule did), and "Albion's" when both teams
    # are "… Albion" (G11; both passes let them through).
    ("Westerlyn Albion and Ravensholt Albion were level in 60:00–75:00, with Albion doing 0% more "
     "high-speed running per ball-in-play minute in that block; earlier the gap was 35%.",
     "analyst", {"team_moment": True, "team_names": ["Westerlyn Albion", "Ravensholt Albion"],
                 "facts": {"vs_opponent": {"value": 0.4, "unit": "%"},
                           "earlier_gap_vs_opponent": {"value": 35, "unit": "%"},
                           "block": "60:00–75:00"}}, None, False),
    ("In 60:00–75:00, 45% of Albion's high-speed running came in the first 10 s after the ball "
     "changed hands, in 34% of the time the ball was in play.", "fan",
     {"team_moment": True, "team_names": ["Westerlyn Albion", "Ravensholt Albion"],
      "facts": {"team_hsr_share_after_ball_changed_hands": {"value": 45, "unit": "%"},
                "time_share_after_ball_changed_hands": {"value": 34, "unit": "%"},
                "block": "60:00–75:00"}}, None, False),
    ("In 60:00–75:00, 45% of Westerlyn Albion's high-speed running came in the first 10 s after "
     "the ball changed hands, in 34% of the time the ball was in play.", "fan",
     {"team_moment": True, "team_names": ["Westerlyn Albion", "Ravensholt Albion"],
      "facts": {"team_hsr_share_after_ball_changed_hands": {"value": 45, "unit": "%"},
                "time_share_after_ball_changed_hands": {"value": 34, "unit": "%"},
                "block": "60:00–75:00"}}, None, True),
    # Found in the decision 31 feed: the LLM read G11 into a team named through its player and
    # rewrote it as "Marco Tarvsall has been involved in a turnover" (24:37, a video moment); the
    # register's G11 now says such a name is clear.
    ("This is the third time Marco Tarvsall's team have lost the ball just after his hardest "
     "minutes so far.", "fan",
     {"team_names": ["Westerlyn Albion", "Ravensholt Albion"],
      "facts": {"times_exposed_so_far": {"value": 3, "unit": "turnovers"}}}, None, True),
    # Held out (2026-10-19, written before the claim 2 rule and never used to tune it): claim 2
    # is about published 1- and 5-min peaks in general; as the reason for one player's own
    # running after a stretch of a given length it is a general finding used as his (blocked),
    # while the wording alone and his own numbers alone are fine.
    ("He is 4 min after his 82 s burst of high-speed running, and short bursts like that are "
     "shaken off in a minute or two, so he should be back to his usual running.", "analyst",
     {"facts": {"hardest_minutes_duration": {"value": 82, "unit": "s"},
                "minutes_after_hardest_minutes": {"value": 4.0, "unit": "min"}}}, "2", False),
    ("A longer effort takes longer to recover from, which is why his running only picked up "
     "3.5 min after his 150 s of hardest minutes.", "fan",
     {"facts": {"hardest_minutes_duration": {"value": 150, "unit": "s"},
                "minutes_after_hardest_minutes": {"value": 3.5, "unit": "min"}}}, "2", False),
    ("Short bursts are shaken off in a minute or two. A five-minute spell takes about five "
     "minutes, and sprinting takes longer.", "fan",
     {"facts": {"hardest_minutes_duration": {"value": 82, "unit": "s"}}}, "2", True),
    ("He is 9 min after his hardest minutes so far, and his last 2 min of high-speed running "
     "was 13.4 m/min.", "analyst",
     {"facts": {"minutes_after_hardest_minutes": {"value": 9.0, "unit": "min"},
                "last_2min_hsr_per_min": {"value": 13.4, "unit": "m/min"}}}, None, True),
]  # fmt: skip


# F1, held out (2026-10-18): sentences that do or do not agree with their facts, written before
# prompt revision 4 and never used to tune the prompt or the rules. A baseline run on revision 3
# came first (see the report). The first version gave the percentages a bare "%" unit, which the
# LLM read as "12% of his average"; the units are now the ones the tools send (sentences and
# labels unchanged).
F1_UP = {
    "facts": {
        "hsr_last_5min_vs_match_average": {
            "value": 12.0,
            "unit": "% above (+) or below (−) his match average",
        }
    }
}
F1_SUB = {"facts": {"sub_hsr_per_min": {"value": 13.1, "unit": "m/min"},
                    "vs_teammates": {"value": 35.0, "unit": "% above (+) or below (−) his "
                                     "team-mates over the same minutes"}}}  # fmt: skip
F1_BALL = {"facts": {"distance_to_ball_at_turnover": {"value": 6, "unit": "m"},
                     "distance_to_ball_8s_later": {"value": 14, "unit": "m"}}}  # fmt: skip
F1_RUN = {"facts": {"peak_speed": {"value": 8.4, "unit": "m/s"},
                    "peak_speed_kmh": {"value": 30, "unit": "km/h"},
                    "share_of_top_speed": {"value": 93, "unit": "% of his top speed so far"},
                    "new_personal_best": False}}  # fmt: skip
F1_BEST = {"facts": F1_RUN["facts"] | {"share_of_top_speed": {"value": 100,
                                                              "unit": "% of his top speed so far"},
                                       "new_personal_best": True}}  # fmt: skip
F1_BACK = {"facts": {"last_2min_hsr_per_min": {"value": 14.0, "unit": "m/min"},
                     "match_average_per_min": {"value": 10.1, "unit": "m/min"},
                     "minutes_after_spell": {"value": 5.0, "unit": "min"}}}  # fmt: skip
FACT_CHECKS = [
    ("His high-speed running in the last 5 minutes is well below his match average.", "fan",
     F1_UP, None, False),
    ("His high-speed running in the last 5 minutes is 12% above his match average.", "fan",
     F1_UP, None, True),
    ("Since coming on he has done less high-speed running per minute than his team-mates.",
     "fan", F1_SUB, None, False),
    ("Since coming on he has done 35% more high-speed running per minute than his team-mates.",
     "fan", F1_SUB, None, True),
    ("He was 6 m from the ball when his team lost it, and closer still eight seconds later.",
     "fan", F1_BALL, None, False),
    ("He was 6 m from the ball when his team lost it, and 14 m eight seconds later.", "fan",
     F1_BALL, None, True),
    ("His fastest run of the match so far: 8.4 m/s (30 km/h).", "fan", F1_RUN, None, False),
    ("His fastest run of the match so far: 8.4 m/s (30 km/h).", "fan", F1_BEST, None, True),
    ("Five minutes after his spell his high-speed running is still below his match average.",
     "fan", F1_BACK, None, False),
    ("His running has dropped since the restart, likely because his team kept the ball.", "fan",
     F1_UP | {"non_fatigue_reasons": [POSS]}, "13", False),
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
    out += [dict(set="facts", sentence=s, mode=m, context=x, claim=c, should_pass=ok)
            for s, m, x, c, ok in FACT_CHECKS]  # fmt: skip
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
    from runningbattery.agents.llm_verifier import verifier_agent, verify_full

    agent = verifier_agent()
    gate = asyncio.Semaphore(concurrency)

    async def one(r: dict) -> None:
        async with gate:
            claim = r["claim"] if r["context"] else None
            v = await verify_full(r["sentence"], r["mode"], r["context"], claim, agent)
        r["llm_ok"] = v.ok
        r["llm_stage"] = v.stage
        r["llm_findings"] = v.findings
        r["llm_fact_check"] = v.fact_check

    await asyncio.gather(*(one(r) for r in rows))


def report(rows: list[dict]) -> dict:
    out: dict = {"n": len(rows), "by_set": {}}
    keys = ["rules_ok"] + (["llm_ok"] if "llm_ok" in rows[0] else [])
    for key in keys:
        out[key.removesuffix("_ok")] = rates(rows, key)
    for name in ("valid", "blocked", "paraphrase", "context", "facts"):
        sub = [r for r in rows if r["set"] == name]
        out["by_set"][name] = {k.removesuffix("_ok"): rates(sub, k) for k in keys}
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m runningbattery.agents.verifier_suite")
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
