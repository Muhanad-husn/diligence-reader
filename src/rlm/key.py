"""Loads a sample's answer key from its key.json file.

The key names the sample's documents, the required documents and decoys, the planted facts,
the expected answer, the grading rubric and the pass bar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

KINDS = frozenset({"number", "date", "identifier", "quote", "document", "comparison"})


@dataclass(frozen=True)
class Fact:
    """A single planted fact: its kind, value, the documents it resolves to and its phase."""

    id: str
    kind: str
    value: str
    documents: tuple[str, ...]
    phase: int


@dataclass(frozen=True)
class Decoy:
    """A document that looks relevant but is not, and why."""

    document: str
    why: str


@dataclass(frozen=True)
class Answer:
    """The expected final answer: an action, a number and its range, and a unit."""

    action: str
    number: float
    low: float
    high: float
    unit: str


@dataclass(frozen=True)
class RubricRow:
    """One row of the grading rubric: a criterion, its points and what earns them."""

    id: int
    criterion: str
    points: int
    earns: str


@dataclass(frozen=True)
class Bar:
    """The pass bar: the perfect score and the score below which the answer is wrong."""

    perfect: int
    wrong_under: int


@dataclass(frozen=True)
class Key:
    """A sample's full answer key, as read from its key.json."""

    sample: str
    brief: str
    documents: dict[str, str]
    required_documents: tuple[str, ...]
    decoys: tuple[Decoy, ...]
    facts: tuple[Fact, ...]
    answer: Answer
    rubric: tuple[RubricRow, ...]
    bar: Bar


def has_key(sample_dir: Path) -> bool:
    """Says whether this sample carries an answer key, without reading a word of it."""
    return (sample_dir / "key.json").exists()


def load_key(sample_dir: Path) -> Key:
    """Reads sample_dir / "key.json" and builds the sample's Key."""
    data = json.loads((sample_dir / "key.json").read_text(encoding="utf-8"))
    facts = tuple(
        Fact(id=f["id"], kind=f["kind"], value=f["value"], documents=tuple(f["documents"]), phase=f["phase"])
        for f in data["facts"]
    )
    return Key(
        sample=data["sample"],
        brief=data["brief"],
        documents=data["documents"],
        required_documents=tuple(data["required_documents"]),
        decoys=tuple(Decoy(**d) for d in data["decoys"]),
        facts=facts,
        answer=Answer(**data["answer"]),
        rubric=tuple(RubricRow(**r) for r in data.get("rubric", [])),
        bar=Bar(**data["bar"]),
    )
