"""The names knob: the people and the organisations of sample 1 spelled inconsistently.

Fifteen names carry a fixed tuple of spellings each: the name in capitals, the name in small
letters, an initial for a first name, the surname first, a corporate suffix dropped, a space or
a hyphen inside a compound name, and one transposed-letter misspelling. Which spelling a
document writes is drawn once per document from seed 0, so one document spells one name one
way and the room spells it several.

Nothing but letters moves. A name is replaced only on a whole word, never inside an email
address, a web address, a file path or any run of characters carrying a figure, so identifiers,
numbers and dates read back as sample 1 wrote them. Every quote fact of the key carries the
text as it stands in the fact's first document; every other fact keeps its value.
"""

from __future__ import annotations

import random
import re
from dataclasses import replace

from rlm.widen import Source, Variant, document_markdown, identity, wrap

NAME = "names"

# The seed the draw runs from. No clock and no socket: the same room every time.
SEED = 0

# A name is listed in the README only when the room writes it in this many spellings.
MIN_SPELLINGS = 3

# The names and the spellings each one is written in. A name whose room is smaller than the
# tuple uses the first spellings the draw hands it, so every name here reaches at least three.
SPELLINGS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Elena Marquez",
        ("ELENA MARQUEZ", "elena marquez", "E. Marquez", "Marquez, Elena", "Elena Marqeuz"),
    ),
    (
        "Daniel Cho",
        ("DANIEL CHO", "daniel cho", "D. Cho", "Cho, Daniel", "Danile Cho"),
    ),
    (
        "Priya Raman",
        ("PRIYA RAMAN", "priya raman", "P. Raman", "Raman, Priya", "Priya Ramna"),
    ),
    (
        "Owen Bell",
        ("OWEN BELL", "owen bell", "O. Bell", "Bell, Owen", "Owen Blel"),
    ),
    (
        "Karl Webb",
        ("KARL WEBB", "karl webb", "K. Webb", "Webb, Karl", "Karl Wbeb"),
    ),
    (
        "Grace Okafor",
        ("GRACE OKAFOR", "grace okafor", "G. Okafor", "Okafor, Grace", "Grace Okafro"),
    ),
    (
        "Renata Castellano",
        (
            "RENATA CASTELLANO",
            "renata castellano",
            "R. Castellano",
            "Castellano, Renata",
            "Renata Casetllano",
        ),
    ),
    (
        "VistaPort Media Inc",
        (
            "VISTAPORT MEDIA INC",
            "vistaport media inc",
            "VistaPort Media, Inc.",
            "Vista Port Media Inc",
            "VistaPort Meida Inc",
        ),
    ),
    (
        "VistaPort",
        ("VISTAPORT", "vistaport", "Vista Port", "Vista-Port", "Vistaprot"),
    ),
    (
        "Northstar Mobile Holdings plc",
        (
            "NORTHSTAR MOBILE HOLDINGS PLC",
            "Northstar Mobile Holdings",
            "North Star Mobile Holdings plc",
            "North-star Mobile Holdings plc",
            "Nortshtar Mobile Holdings plc",
        ),
    ),
    (
        "Meridian Media Agency",
        (
            "MERIDIAN MEDIA AGENCY",
            "meridian media agency",
            "Meridian Media",
            "Meridian-Media Agency",
            "Meridian Meida Agency",
        ),
    ),
    (
        "Canton Street Capital",
        (
            "CANTON STREET CAPITAL",
            "canton street capital",
            "Canton Street",
            "Canton-Street Capital",
            "Cantno Street Capital",
        ),
    ),
    (
        "Brandt & Mauer LLP",
        (
            "BRANDT & MAUER LLP",
            "brandt & mauer llp",
            "Brandt & Mauer",
            "Brandt-Mauer LLP",
            "Brandt & Muaer LLP",
        ),
    ),
    (
        "Helios Retail Group",
        (
            "HELIOS RETAIL GROUP",
            "helios retail group",
            "Helios Retail",
            "Helios-Retail Group",
            "Helios Retial Group",
        ),
    ),
    (
        "Redbridge Risk Advisors",
        (
            "REDBRIDGE RISK ADVISORS",
            "redbridge risk advisors",
            "Redbridge Risk",
            "Redbridge-Risk Advisors",
            "Redbrigde Risk Advisors",
        ),
    ),
)

# The names as one pattern, longest first, so that the long form of a name is matched before
# its short form and the text is read once. A name matches on a whole word only.
FOUND = re.compile(
    r"(?<![A-Za-z])(?:"
    + "|".join(re.escape(name) for name, _ in sorted(SPELLINGS, key=lambda pair: -len(pair[0])))
    + r")(?![A-Za-z])"
)

# What a name is never respelled inside: a run of characters holding a figure, a slash, a
# backslash or an at sign, and a host or file name. Email addresses, web addresses, file paths
# and every identifier the phase 1 index reads are inside one of these.
GUARDED = re.compile(r"\S*[@/\\]\S*|\S*\d\S*|\S*\.[A-Za-z]{2,6}(?![A-Za-z])\S*")

# The whitespace a quote may be wrapped on where a document writes it over two lines.
BREAK = r"\s+"


def guarded(text: str) -> set[int]:
    """The character positions of one text that no name is respelled inside."""
    positions: set[int] = set()
    for match in GUARDED.finditer(text):
        positions.update(range(match.start(), match.end()))
    return positions


def rewrite(text: str, spelling: dict[str, str], seen: set[tuple[str, str]] | None = None) -> str:
    """One text with every name in `spelling` written the way that document writes it.

    `spelling` maps a name to the spelling drawn for the document the text belongs to. A name
    with no entry is left alone, and so is a match that falls inside a guarded run. Every
    (name, spelling) pair actually written is added to `seen`.
    """
    inside = guarded(text)

    def swap(match: re.Match) -> str:
        if any(position in inside for position in range(match.start(), match.end())):
            return match.group(0)
        name = match.group(0)
        chosen = spelling.get(name)
        if chosen is None:
            return name
        if seen is not None:
            seen.add((name, chosen))
        return chosen

    return FOUND.sub(swap, text)


def carried(sections: dict[str, tuple[str, ...]]) -> dict[str, list[str]]:
    """The documents each name is written in, outside the guarded runs, in path order."""
    found: dict[str, list[str]] = {name: [] for name, _ in SPELLINGS}
    for doc in sorted(sections):
        text = "\n".join(sections[doc])
        inside = guarded(text)
        for match in FOUND.finditer(text):
            if any(position in inside for position in range(match.start(), match.end())):
                continue
            name = match.group(0)
            if name in found and doc not in found[name]:
                found[name].append(doc)
    return found


def draw(sections: dict[str, tuple[str, ...]]) -> dict[str, dict[str, str]]:
    """The spelling drawn for every name in every document that writes it.

    The documents of one name are shuffled from seed 0 and the spellings are dealt round the
    shuffled order, so the draw is seeded, the same every run, and a name in three documents
    or more is written in at least three spellings.
    """
    rooms = carried(sections)
    generator = random.Random(SEED)
    drawn: dict[str, dict[str, str]] = {}
    for name, spellings in SPELLINGS:
        documents = list(rooms[name])
        generator.shuffle(documents)
        for number, doc in enumerate(documents):
            drawn.setdefault(doc, {})[name] = spellings[number % len(spellings)]
    return drawn


def as_written(value: str, document: str) -> str:
    """A quote as the document writes it, taking the line break a document wraps it on.

    Returns the value unchanged when the document does not carry it.
    """
    pattern = re.compile(BREAK.join(re.escape(word) for word in value.split()))
    match = pattern.search(document)
    return match.group(0) if match else value


def table(seen: dict[str, set[tuple[str, str]]], ids: dict[str, str]) -> str:
    """The README's table: one row per name and spelling, with the documents that wrote it."""
    documents: dict[tuple[str, str], list[str]] = {}
    for doc in sorted(seen, key=lambda path: ids[path]):
        for pair in seen[doc]:
            documents.setdefault(pair, []).append(ids[doc])

    rows = ["| name | spelling | documents |", "|---|---|---|"]
    for name, spellings in SPELLINGS:
        written = [one for one in spellings if (name, one) in documents]
        if len(written) < MIN_SPELLINGS:
            continue
        for one in written:
            rows.append(f"| `{name}` | `{one}` | {', '.join(documents[(name, one)])} |")
    return "\n".join(rows)


def notes(seen: dict[str, set[tuple[str, str]]], ids: dict[str, str]) -> str:
    """The section the knob adds to the variant's README."""
    listed = table(seen, ids)
    names = len({row.split("`")[1] for row in listed.splitlines()[2:]})
    said = wrap(
        f"The knob respells {names} names of people and organisations. A name carries a fixed "
        f"tuple of spellings and the spelling one document writes is drawn from seed 0, so the "
        f"room spells every name below in at least {MIN_SPELLINGS} ways. A name is replaced on "
        f"a whole word only, never inside an email address, a web address, a file path or any "
        f"run of characters carrying a figure, so identifiers, numbers and dates are untouched."
    )
    return f"## Names\n\n{said}\n\n{listed}\n"


def build(source: Source) -> Variant:
    """The variant of sample 1 with its names spelled inconsistently."""
    drawn = draw(source.sections)
    seen: dict[str, set[tuple[str, str]]] = {}

    rewritten = {}
    for doc in sorted(source.sections):
        spelling = drawn.get(doc, {})
        written: set[tuple[str, str]] = set()
        texts = tuple(rewrite(text, spelling, written) for text in source.sections[doc])
        rewritten[doc] = document_markdown(texts)
        if written:
            seen[doc] = written

    def text(doc: str, one: str) -> str:
        return rewrite(one, drawn.get(doc, {}))

    def fact(one: dict) -> dict:
        if one["kind"] != "quote":
            return one
        doc = source.key["documents"][one["documents"][0]]
        value = rewrite(one["value"], drawn.get(doc, {}))
        return {**one, "value": as_written(value, rewritten[doc])}

    variant = identity(source, NAME, text=text, fact=fact)
    ids = {path: doc_id for doc_id, path in source.key["documents"].items()}
    return replace(variant, notes=notes(seen, ids))
