"""The text helpers the map and the dossier both read documents with.

Both modules compare what a room wrote: the map to decide which documents the matter reaches,
the dossier to write the rows a person checks. The dossier imports the map, so anything they
share lives here instead, where neither imports the other.

What is here is the folding of a value into a comparable form, the words of a text that say
something, the longest run of words two texts both write, the words a room uses when it ends an
agreement or asks for two documents to be read against each other, and the section lookups that
turn an anchor into the text at that place.

Nothing here reads a key, opens a socket or calls a model.
"""

from __future__ import annotations

import re
from pathlib import Path

# The words too common in this prose for two statements that share them to be about one thing.
COMMON_WORDS = frozenset(
    "the a an and or of to in on at for from by with as is are was were be been not no any "
    "that this it its their there which what has have had will would may can could should "
    "we our us they them he she his her".split()
)

# How many words that say something a shared run has to hold to be a subject.
SUBJECT_WORDS = 2

# What ends an agreement.
TERMINATION_WORDS = re.compile(r"\b(terminate|terminates|termination)\b", re.IGNORECASE)

# What a document writes where it asks to be read against another document.
COMPARE_WORDS = re.compile(
    r"\b(compare|compared|compares|comparison|reconcile|reconciled|reconciles|"
    r"reconciliation|versus)\b",
    re.IGNORECASE,
)

_LOOSE = re.compile(r"[^a-z0-9]+")
_WHITESPACE = re.compile(r"\s+")


def fold(value) -> str:
    """The comparable form of a value: lower case, with every run of punctuation a single space.

    `kid=vpauth-legacy-2019` and `kid vpauth legacy 2019` fold to the same thing, so a value can
    be looked for inside the words of a flag whatever punctuation either side used.
    """
    return _LOOSE.sub(" ", str(value).casefold()).strip()


def one_line(text) -> str:
    """The text with every run of whitespace collapsed to one space and the ends trimmed.

    Nothing else is changed, so a quote stays the note's own words and a markdown mark the note
    wrote is still there for a reader to see.
    """
    return _WHITESPACE.sub(" ", str(text)).strip()


def content_words(text) -> set[str]:
    """The words of a text that say something: folded, longer than two letters, not common."""
    return {word for word in fold(text).split() if len(word) > 2} - COMMON_WORDS


def folded_words(text) -> list[str]:
    """The words of a text, folded, in the order it wrote them."""
    return fold(one_line(text)).split()


def shared_run(first: list[str], second: list[str]) -> tuple[str, ...] | None:
    """The longest run of words the two texts both write, holding SUBJECT_WORDS that say
    something, or None where they share no such run.

    A run of common English is not a subject: `in the event of a` is how every clause opens, and
    `of this agreement` says only that both are agreements.
    """
    lengths = [0] * (len(second) + 1)
    best: tuple[str, ...] | None = None
    for a in range(len(first)):
        carried = [0] * (len(second) + 1)
        for b in range(len(second)):
            if first[a] == second[b]:
                carried[b + 1] = lengths[b] + 1
                run = tuple(first[a + 1 - carried[b + 1] : a + 1])
                if len(content_words(" ".join(run))) >= SUBJECT_WORDS and (
                    best is None or len(run) > len(best)
                ):
                    best = run
        lengths = carried
    return best


def document_of(anchor: str, ids_by_path: dict[str, str]) -> str | None:
    """The document id an anchor belongs to, or None where the anchor names no key document."""
    return ids_by_path.get(anchor.rsplit("#", 1)[0])


def sections_by_document(
    sections: list[dict], ids_by_path: dict[str, str]
) -> dict[str, list[tuple[str, str]]]:
    """Every section of the run as (anchor, one line of text), by the document it sits in."""
    found: dict[str, list[tuple[str, str]]] = {}
    for section in sections:
        doc = document_of(section["anchor"], ids_by_path)
        if doc is not None:
            found.setdefault(doc, []).append((section["anchor"], one_line(section["text"])))
    return found


def closest_section(
    held: list[tuple[str, str]], text, without: set[str] = frozenset()
) -> tuple[str, str] | None:
    """The section of a document that shares the most words with a text, earliest anchor first.

    The words in `without` are not counted. None where the document shares no other word with
    the text at all.
    """
    wanted = content_words(text) - set(without)
    best = None
    for anchor, written in held:
        shared = len(wanted & content_words(written))
        if not shared:
            continue
        mark = (-shared, anchor)
        if best is None or mark < best[0]:
            best = (mark, (anchor, written))
    return None if best is None else best[1]


def named_by(nodes: dict[str, dict]) -> dict[str, str]:
    """Every document by a name a cross reference can call it: its id and its file name.

    A file name two documents of the room share names neither of them, because a reference to
    it says nothing about which one is meant.
    """
    carriers: dict[str, set[str]] = {}
    for doc, node in nodes.items():
        for name in (doc, Path(node["path"]).name):
            carriers.setdefault(name.upper(), set()).add(doc)
    return {name: held.pop() for name, held in carriers.items() if len(held) == 1}
