"""Read and write a match folder (the four files described in ``secondwind.schema``)."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from secondwind.schema import Event, MatchMetadata, MatchTruth, TrackingFrame

TRACKING = "tracking.jsonl"
EVENTS = "events.jsonl"
METADATA = "metadata.json"
TRUTH = "truth.json"


@dataclass(frozen=True)
class Match:
    """What the estimator may see: everything except the truth."""

    metadata: MatchMetadata
    frames: list[TrackingFrame]
    events: list[Event]


def _write_jsonl(path: Path, rows: Iterable[BaseModel]) -> None:
    with path.open("w") as f:
        for row in rows:
            f.write(row.model_dump_json(exclude_none=True))
            f.write("\n")


def _read_jsonl[M: BaseModel](path: Path, model: type[M]) -> Iterator[M]:
    with path.open() as f:
        for line in f:
            if line.strip():
                yield model.model_validate_json(line)


def write_match(
    folder: Path,
    metadata: MatchMetadata,
    frames: Iterable[TrackingFrame],
    events: Iterable[Event],
    truth: MatchTruth | None = None,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / METADATA).write_text(metadata.model_dump_json(indent=2, exclude_none=True))
    _write_jsonl(folder / TRACKING, frames)
    _write_jsonl(folder / EVENTS, events)
    if truth is not None:
        (folder / TRUTH).write_text(truth.model_dump_json(exclude_none=True))


def read_match(folder: Path) -> Match:
    """Load the files the estimator is allowed to see. Validates every row."""
    return Match(
        metadata=MatchMetadata.model_validate_json((folder / METADATA).read_text()),
        frames=list(_read_jsonl(folder / TRACKING, TrackingFrame)),
        events=list(_read_jsonl(folder / EVENTS, Event)),
    )


def read_truth(folder: Path) -> MatchTruth:
    """Validation only. Never call this from ``secondwind.engine``."""
    return MatchTruth.model_validate_json((folder / TRUTH).read_text())
