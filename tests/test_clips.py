"""The Highlights view's clips as the overlay builds them (scripts/clip_audit.py ``queue``, the
mirror of data.ts ``queue``), from the committed site data."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("clip_audit", ROOT / "scripts" / "clip_audit.py")
clip_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clip_audit)


def clips(match: str, hidden: frozenset[str]) -> list[dict]:
    d = ROOT / "app" / "public" / "data" / match
    m = json.loads((d / "match.json").read_text())
    feed = json.loads((d / "feed.json").read_text())
    hls = json.loads((d / "highlights.json").read_text())
    end = m["periods"][-1]["video_start"] + m["periods"][-1]["duration_s"]
    best = clip_audit.reel(hls, end)
    return clip_audit.queue(m, feed, m.get("clips", {}), best, "fan", m["shots"], hidden)


@pytest.mark.parametrize("match", ["story", "natural"])
def test_clips_removed_by_hand_leave_a_gap(match):
    """Decision 48: every id in hidden.json names a clip of the list, and taking them out removes
    exactly those clips (also a moment that became a highlight's line); no other clip takes their
    place."""
    hidden = frozenset(json.loads((ROOT / "app/public/data" / match / "hidden.json").read_text()))
    full = clips(match, frozenset())
    shown = clips(match, hidden)
    named = {c["id"] for c in full} | {c["moment"] for c in full if c["moment"]}
    assert hidden <= named, sorted(hidden - named)
    assert [c for c in full if c["id"] not in hidden and c["moment"] not in hidden] == shown
    assert not {c["id"] for c in shown} & hidden
