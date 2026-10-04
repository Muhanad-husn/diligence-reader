"""Loads a sample's answer key from its key.json file.

The key names the sample's documents, the required documents and decoys, the planted facts,
the expected answer, the grading rubric and the pass bar.

A room handed to the command may have no key. room_documents gives the documents every stage
reads, from the key where there is one and from the room's own files where there is none, and
room_name gives the name the map writes.
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


# The suffixes ingest.read_document has a reader for, lower case. A file of any other suffix is
# not a document of a room with no key.
READABLE_SUFFIXES = (".pdf", ".xlsx", ".csv", ".txt", ".md", ".eml", ".mbox")

# The files at a room's root that describe the room rather than belong to it.
ROOM_FILES = ("brief.md", "key.json")


def room_documents(sample_dir: Path) -> dict[str, str]:
    """The room's documents as document id to path relative to the room, in posix form.

    A room with key.json gives the key's documents, in the key's order, so a sample reads
    exactly as it always has. A room with no key gives every file under it whose suffix ingest
    can read, leaving out brief.md and key.json at the room's root, any path with a part that
    starts with a dot, and Office's ~$ lock files, sorted by relative posix path.

    A document of a room with no key is its own relative path, the id northwind's and
    northstar-dental's keys already use. That id survives every place an id goes: notes.note_name
    turns its slashes into a file name, the map and the dossier key on it, and the writer and the
    verifier read a citation `[<doc> | <anchor>]` whose doc is any run of characters but a
    bracket or a bar, and every anchor ingest writes begins with the same path. A path holding a
    bracket or a bar would not read back out of a citation.
    """
    sample_dir = Path(sample_dir)
    if has_key(sample_dir):
        return load_key(sample_dir).documents
    found = []
    for path in sample_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in READABLE_SUFFIXES:
            continue
        relative = path.relative_to(sample_dir)
        if relative.as_posix() in ROOM_FILES:
            continue
        if any(part.startswith(".") for part in relative.parts) or path.name.startswith("~$"):
            continue
        found.append(relative.as_posix())
    return {relative: relative for relative in sorted(found)}


def room_name(sample_dir: Path) -> str:
    """The room's name: the key's sample where there is a key, the folder's name where not."""
    sample_dir = Path(sample_dir)
    return load_key(sample_dir).sample if has_key(sample_dir) else sample_dir.name
