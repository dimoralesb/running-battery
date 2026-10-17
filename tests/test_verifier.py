"""The rule-based Verifier suite (BUILD_PLAN §3, run 7): every blocked sentence and every
unbaselined % must be caught, and no valid sentence may be blocked (false-block rate 0)."""

import pytest

from secondwind.agents.verifier import RULES, register, verify

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
]  # fmt: skip


@pytest.mark.parametrize(("sentence", "mode"), VALID)
def test_valid_sentences_pass(sentence, mode):
    v = verify(sentence, mode)
    assert v.ok, [f.claim for f in v.findings]


@pytest.mark.parametrize(("sentence", "mode", "claim"), BLOCKED)
def test_blocked_sentences_are_caught_for_the_right_reason(sentence, mode, claim):
    v = verify(sentence, mode)
    assert not v.ok and claim in {f.claim for f in v.findings}


def test_suite_size_and_rates():
    """About 50 sentences, about half blocked; every blocked one caught, none falsely blocked."""
    assert len(VALID) + len(BLOCKED) >= 50 and len(BLOCKED) >= 25
    caught = sum(not verify(s, m).ok for s, m, _ in BLOCKED) / len(BLOCKED)
    false_block = sum(not verify(s, m).ok for s, m in VALID) / len(VALID)
    assert caught == 1.0 and false_block == 0.0


def test_every_blocked_claim_has_a_rule_and_a_case():
    reg = register()
    ids = {c["id"] for c in reg["claims"]} | {g["id"] for g in reg["global_rules"]}
    assert {r.claim for r in RULES} <= ids
    blocked = {c["id"] for c in reg["claims"] if c["status"] == "blocked"}
    assert blocked <= {r.claim for r in RULES}
    assert blocked <= {c for _, _, c in BLOCKED}


def test_register_wordings_pass_in_their_mode():
    """The example wording of every supported or qualified claim passes the rules."""
    for c in register()["claims"]:
        if c["status"] != "blocked":
            v = verify(c["wording"], c["mode"])
            assert v.ok, (c["id"], [f.claim for f in v.findings])
