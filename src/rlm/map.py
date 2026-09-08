"""Builds runs/<sample>/map.json from the index, the sections and the notes.

The map is a graph of the room. Its nodes are the documents the key names, in the key's own
order, each with its folder, its first date and the status words the index read off it. Its
edges are the values two documents share: an `identifier` the index saw, a `cross-reference` a
note wrote, a `version` pair of a draft and its final, and a `date` where two documents carry a
dated section within seven days of each other. A shared value weighs less the more documents
carry it, so AURORA in sixteen documents weighs a quarter of `vpauth-legacy-2019` in four.

An `identifier` or `cross-reference` edge is kept only where a flag of both notes says it is
about that value, or the value is inside a concealed item of both. A value only the index saw
joins two documents by coincidence about as often as by matter; a value both notes named as the
thing a worry is about is the matter itself. A flag's own words, its quote and its consequence
are not looked inside: a flag that mentions a code in passing is not a flag about that code.
Date and version edges are kept as they are, because neither is a coincidence of vocabulary.

The matter is seeded at the document whose three strongest links are the strongest in the room.
The cluster around that seed is a set, not a cut: a document is in it because a named link put
it there, and every document carries the link it came by, so the set reads backwards to the
seed. Only non-date edges are followed, and never an edge whose value is a bare count, because
a room shares `5` and `2025` the way it shares the alphabet. Each rule below runs once, on the
set the rules before it built, and is not repeated.

A document joins as `shared` where it has such an edge to the seed, which is to say where a flag
of its note and a flag of the seed's note are about the same value. It joins as `version` where
it is the draft or the final of a pair the set already touches. It joins as `consequence` where
the matter broke a series it holds, or where it is a model written after the matter that still
carries a figure the broken series left behind. It joins as `reach` where two documents of the
set each share a value of the matter with it and those are two different values, one of which
the matter owns, or where one value of the matter it shares with one document of the set is an
exact money figure the matter owns. A value of the matter is a value the room's notes write,
as a cross reference or as a figure, whole or as a word inside one they write, and that the
matter owns, every other document of the room carrying it being in the set already; an exact
money figure is a value of the matter whether the matter owns it or not, because a figure only
a few documents carry names a matter as well as a code does. It joins as `compare` where a set
document's note names it at a place that asks, in the room's own words, for the two to be read
against each other. It joins as `covenant` where one of its flags is quoted with a termination
word and writes the same run of words as a flag of the seed or of a document the seed joined by
`shared`, and either that flag is quoted with a termination word as well or the run names a
value of the matter.

Every document is also scored by what it shares with the seed, plus one round of that score
spread along the edges, each neighbour's contribution divided by its own total weight so that
the room's index and its Q&A log, which link to everything, pass on almost nothing. The score
orders the set and orders the room outside it; it does not decide either. Each document of the
set is lifted by the room's highest score, so the set is the head of the ranking and the scores
still fall.

The matter then carries two things a graph of shared values cannot see. Its `versions` are the
index's draft and final pairs where at least one of the two is in the set already, with the two
dates and the two status lists the map already read. Its `consequences` are the links the map
finds by mechanism. A `series-break` is a table of periods in the room whose numbers turn: the
step from one period to the next starts running one way and each step is bigger than the
column's usual step. A series turns once, at the earliest period any of its columns turns, and
the matter keeps every series that turns inside a week of its own date and on or after it, in a
document that is not the seed. Two tables of the same weeks turn on the same day when the
matter moved both, and both are the matter's consequence. A `model-after` is a document whose
name, folder or note says model, forecast, plan or synergy, dated after the matter, whose note
still carries a figure the broken series left behind: the same number, ignoring the currency
and the unit letter, so 615m and 615 are one figure and 4100 is not 410. The figure has to be a
figure of another set document's note as well. The matter keeps every such model, because a
number that outlived the matter in two models is two models to correct, not one.

Nothing here reads the key's facts, its required documents or its decoys, opens a socket or
calls a model. The key is read for the id and path of each document and for nothing else.
"""

from __future__ import annotations

import collections
import datetime
import itertools
import json
import re
import statistics
import sys
import time
from pathlib import Path

from rlm.index import line_cells
from rlm.key import load_key
from rlm.words import (
    COMPARE_WORDS,
    TERMINATION_WORDS,
    document_of,
    fold,
    folded_words,
    named_by,
    one_line,
    sections_by_document,
    shared_run,
)

# What each kind of shared value is worth before it is divided by the number of documents that
# carry it. A note that wrote a value down is better evidence than an index that saw it; a
# draft and its final are the same matter twice; two dates within a week are the weakest of all.
KIND_WEIGHTS = {
    "cross-reference": 4.0,
    "date": 0.2,
    "identifier": 1.0,
    "version": 4.0,
}

# The four kinds of edge the map writes.
EDGE_KINDS = tuple(sorted(KIND_WEIGHTS))

# Two dated sections this many days apart or fewer make a date edge.
DATE_WINDOW = 7

# A value more than this share of the room carries is background, not a link.
BREADTH_SHARE = 0.5

# A value more than this share of the room carries cannot reach a document into the set. A value
# that merely links two documents may be twice as common as one that pulls a third in.
REACH_SHARE = 0.25

# The kinds of link that put a document in the set, in the order the map writes them.
VIA_KINDS = ("compare", "consequence", "covenant", "reach", "seed", "shared", "version")

# How many steps in a row have to run the same way for a column of numbers to have turned.
TURN_RUN = 3

# The words that say a document is about what is to come rather than what happened.
MODEL_WORDS = frozenset({"forecast", "model", "plan", "synergy"})

# How many of a document's strongest links are read when the seed is chosen.
SEED_LINKS = 3

# The id of the key fact the phase 3 tests read the planted cluster from.
MATTER_FACT = "matter-documents"

# How many values a ranked row gives as its reason.
WHY_LIMIT = 3

_WORD = re.compile(r"[A-Za-z][A-Za-z\-]+")
_COUNT = re.compile(r"[0-9][0-9,]*")
_LETTERS = re.compile(r"[A-Za-z]+")
_FIGURE = re.compile(r"([0-9]+(?:\.[0-9]+)?)(?:[a-z%]{0,2})")
_MONEY = re.compile(r"[,$\s]")
_DAY_MONTH_YEAR = re.compile(r"([0-9]{1,2}) ([A-Za-z]+) ([0-9]{4})")
_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


def is_count(value) -> bool:
    """Whether a value is a bare count: digits and commas, once its ends are trimmed.

    `5`, `2025` and `1,840` are counts, and a count is not a value of the matter: a room shares
    them the way it shares the alphabet. `912.8m`, `$12m` and `NQ-17` name something.
    """
    return bool(_COUNT.fullmatch(str(value).strip()))


def value_weight(kind: str, carriers: int) -> float:
    """What one shared value is worth to the pair of documents that share it.

    The weight falls with the number of documents carrying the value, so a value four documents
    carry weighs four times a value sixteen carry.
    """
    if kind not in KIND_WEIGHTS:
        raise ValueError(f"not an edge kind: {kind!r}")
    if carriers < 2:
        raise ValueError(f"a shared value needs two documents, not {carriers}")
    return KIND_WEIGHTS[kind] / carriers


def read_jsonl(path: Path) -> list[dict]:
    """Every record of a JSON lines file, in file order."""
    text = path.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def read_notes(run_dir: Path, ids_by_path: dict[str, str]) -> dict[str, dict]:
    """Every note under runs/<sample>/notes/, keyed by the document id the note is about."""
    notes = {}
    notes_dir = run_dir / "notes"
    if not notes_dir.is_dir():
        return notes
    for path in sorted(notes_dir.glob("*.json")):
        note = json.loads(path.read_text(encoding="utf-8"))
        doc_id = ids_by_path.get(note["doc"])
        if doc_id:
            notes[doc_id] = note
    return notes


def named_values(note: dict) -> tuple[set[str], str]:
    """The folded values a note's flags are about, and its concealed items as one folded string.

    This is where a value has to appear for the map to count it as a link: what a flag names as
    the thing it is about, whole, or what the note wrote down as concealed. A flag's own words,
    its quote and its consequence are not looked inside, because a flag that mentions a code in
    passing is not a flag about that code, and a value is not read inside another value, because
    legacy_uap is not legacy_uap_backup_2021.tar.gz. A note written before flags carried about
    reads as its concealed items alone.
    """
    values = {
        fold(value)
        for flag in note["flags"]
        for value in flag.get("about", [])
        if isinstance(value, str) and fold(value)
    }
    concealed = fold(" ".join(part for item in note["concealed"] for part in (item["claim"], item["quote"])))
    return values, concealed


def is_about(named: tuple[set[str], str] | None, folded: str) -> bool:
    """Whether a folded value is one a note's flags are about, or sits in its concealed items.

    A value with a digit in it also counts when it sits whole, on word boundaries, inside one
    element: 24 months is inside twenty-four (24) months and vpauth-legacy-2019 is inside
    kid=vpauth-legacy-2019. A value without a digit has to be the element: legacy_uap is not
    legacy_uap_backup_2021.tar.gz.
    """
    if not named or not folded:
        return False
    values, concealed = named
    if folded in values or folded in concealed:
        return True
    if not any(char.isdigit() for char in folded):
        return False
    inside = re.compile(r"(?<!\S)" + re.escape(folded) + r"(?!\S)")
    return any(inside.search(value) for value in values)


def person_values(notes: dict[str, dict]) -> set[str]:
    """The cross-reference values the notes call people more often than anything else.

    A person's name is not evidence that two documents are about the same matter: a general
    counsel signs the tax memo and the forensic memo alike.
    """
    kinds: dict[str, collections.Counter] = {}
    for note in notes.values():
        for reference in note["cross_references"]:
            kinds.setdefault(reference["value"], collections.Counter())[reference["kind"]] += 1
    people = set()
    for value, counted in kinds.items():
        top = max(counted.items(), key=lambda pair: (pair[1], pair[0] == "person"))
        if top[0] == "person":
            people.add(value)
    return people


def written_values(notes: dict[str, dict]) -> tuple[set[str], set[str]]:
    """The values the room's notes write in their own right, whole and in every run of words.

    A note writes a value where it names it as a cross reference or reads it as a figure. A
    cross reference the note calls a person is left out, because a person's name is not evidence
    that two documents are about the same matter, and a title written beside a person is not
    one either. The second set holds every run of words of those values, so `DPA` is found
    inside `Tidewater DPA` and `45 days` inside `Net 45 days` without looking for either there.
    """
    whole: set[str] = set()
    for note in notes.values():
        for reference in note["cross_references"]:
            if reference["kind"] != "person":
                whole.add(fold(reference["value"]))
        for figure in note["figures"]:
            whole.add(fold(figure["surface"]))
    whole.discard("")
    return whole, {run for value in whole for run in word_runs(value)}


def word_runs(folded: str) -> set[str]:
    """Every run of one or more words of a folded value, in no particular order."""
    words = folded.split()
    return {
        " ".join(words[start:end])
        for start in range(len(words))
        for end in range(start + 1, len(words) + 1)
    }


def is_written(value, written: tuple[set[str], set[str]]) -> bool:
    """Whether the notes write a value, whole or as a word inside a value they write.

    `DPA` is written inside `Tidewater DPA` and `45 days` inside `Net 45 days`, so the room
    writes both down. `EBITDA`, `MAU`, `CEO` and `Day-1` are in no cross reference and no
    figure, whole or in part: they are the words the room writes in front of a number, beside a
    person or on a milestone, and the index cut them out of its prose.
    """
    return fold(value) in written[1]


def names_a_value(words: str, written: tuple[set[str], set[str]]) -> bool:
    """Whether a folded run of words holds a value the notes write in its own right."""
    return bool(word_runs(words) & written[0])


def value_holders(
    shared: dict[tuple[str, str], dict[str, tuple[float, int]]]
) -> dict[str, set[str]]:
    """Every document that carries each value the set is built along."""
    holders: dict[str, set[str]] = {}
    for pair, held in shared.items():
        for value in held:
            holders.setdefault(value, set()).update(pair)
    return holders


def ordinary_words(sections: list[dict]) -> set[str]:
    """The capitalised tokens the room writes in lower case at least as often as in capitals.

    `THE`, `COUNSEL` and `DRAFT` are ordinary English the room also writes as `the`, `counsel`
    and `draft`; `AURORA` and `CISO` it never writes in lower case. Only the second kind is a
    code two documents can share.
    """
    upper: collections.Counter = collections.Counter()
    lower: collections.Counter = collections.Counter()
    for section in sections:
        for word in set(_WORD.findall(section["text"])):
            if word.isupper():
                upper[word] += 1
            elif word.islower():
                lower[word] += 1
    return {word for word in upper if lower[word.lower()] >= upper[word]}


def as_iso(value) -> datetime.date | None:
    """The day a date record's value names, or None where it is not a plain ISO day."""
    try:
        return datetime.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def as_day(value) -> datetime.date | None:
    """The day a period cell names, written either 2025-10-20 or 20 October 2025.

    A month or a quarter is coarser than a day and reads as None.
    """
    day = as_iso(value)
    if day is not None:
        return day
    match = _DAY_MONTH_YEAR.fullmatch(str(value).strip())
    if not match or match.group(2).casefold() not in _MONTHS:
        return None
    month = _MONTHS.index(match.group(2).casefold()) + 1
    try:
        return datetime.date(int(match.group(3)), month, int(match.group(1)))
    except ValueError:
        return None


def as_number(value) -> float | None:
    """The number a cell holds, whether the file wrote it as a number or as digits."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(_MONEY.sub("", str(value)))
    except ValueError:
        return None


def figure_number(surface) -> str | None:
    """The number a figure's surface names, without its currency, its commas or its unit.

    615, 615m and $410m read as 615, 615 and 410, so a model that writes 615m and a table that
    writes 615 carry one figure. 4100 reads as 4100 and is not 410. A surface that is not one
    number reads as None.
    """
    match = _FIGURE.fullmatch(_MONEY.sub("", str(surface).casefold()))
    if not match:
        return None
    return format(float(match.group(1)), "g")


def turn_index(values: list[float]) -> int | None:
    """Where a column of numbers turns, or None where it never does.

    The steps are the differences from one period to the next and the usual step is the median
    of their sizes. A turn is the start of a run of TURN_RUN steps that all go the same way and
    are all bigger than the usual step: the period where a column stops wobbling and moves. The
    index returned is the period the first of those steps arrives at, and the earliest run wins.
    """
    if len(values) < TURN_RUN + 2:
        return None
    steps = [values[at] - values[at - 1] for at in range(1, len(values))]
    usual = statistics.median(abs(step) for step in steps)
    for start in range(len(steps) - TURN_RUN + 1):
        run = steps[start : start + TURN_RUN]
        if all(step > usual for step in run) or all(-step > usual for step in run):
            return start + 1
    return None


def shared_values(
    records: list[dict],
    notes: dict[str, dict],
    ids_by_path: dict[str, str],
    first_anchors: dict[str, str],
    skipped: set[str],
) -> list[tuple[str, str, dict[str, str]]]:
    """Every value two or more documents share, as (kind, value, {document: anchor}).

    An identifier is an index `identifier` record, a one-word capitalised `name` record, or an
    `amount` record: an exact figure only a few documents carry names a matter as well as a code
    does. A cross reference is a value a note wrote, carried also by another note, by another
    document's index or by being the id of that document. A version is an index version pair.
    """
    found: list[tuple[str, str, dict[str, str]]] = []

    def anchors_of(record) -> dict[str, str]:
        carriers: dict[str, str] = {}
        for anchor in record["anchors"]:
            doc_id = document_of(anchor, ids_by_path)
            if doc_id:
                carriers.setdefault(doc_id, anchor)
        return carriers

    by_surface: dict[str, dict[str, str]] = {}
    by_amount: dict[tuple, tuple[str, dict[str, str]]] = {}
    versions: dict[str, dict[str, str]] = {}
    for record in records:
        kind = record["kind"]
        surface = str(record["surface"])
        if kind == "identifier" or (kind == "name" and " " not in surface and surface.isupper()):
            for doc_id, anchor in anchors_of(record).items():
                by_surface.setdefault(surface, {}).setdefault(doc_id, anchor)
        elif kind == "amount":
            marker = (record["value"], record["unit"])
            shown, carriers = by_amount.setdefault(marker, (surface, {}))
            if surface < shown:
                shown = surface
            for doc_id, anchor in anchors_of(record).items():
                carriers.setdefault(doc_id, anchor)
            by_amount[marker] = (shown, carriers)
        elif kind == "version-pair":
            for doc_id, anchor in anchors_of(record).items():
                versions.setdefault(surface, {}).setdefault(doc_id, anchor)

    # The surfaces the index saw, folded, so a note's value can be looked up in another
    # document's index.
    index_carriers: dict[str, dict[str, str]] = {}
    for record in records:
        if record["kind"] not in ("identifier", "name"):
            continue
        folded = fold(record["surface"])
        if not folded:
            continue
        for anchor in record["anchors"]:
            doc_id = document_of(anchor, ids_by_path)
            if doc_id:
                index_carriers.setdefault(folded, {}).setdefault(doc_id, anchor)

    for surface, carriers in sorted(by_surface.items()):
        if surface not in skipped:
            found.append(("identifier", surface, carriers))
    for _, (surface, carriers) in sorted(by_amount.items(), key=lambda item: str(item[0])):
        found.append(("identifier", surface, carriers))
    for surface, carriers in sorted(versions.items()):
        found.append(("version", surface, carriers))

    references: dict[str, dict[str, str]] = {}
    for doc_id in sorted(notes):
        for reference in notes[doc_id]["cross_references"]:
            references.setdefault(reference["value"], {}).setdefault(doc_id, reference["anchor"])
    for value, carriers in sorted(references.items()):
        if value in skipped:
            continue
        carried = dict(carriers)
        for doc_id, anchor in sorted(index_carriers.get(fold(value), {}).items()):
            carried.setdefault(doc_id, anchor)
        named = str(value).strip().upper()
        if named in first_anchors:
            carried.setdefault(named, first_anchors[named])
        found.append(("cross-reference", value, carried))
    return found


def date_edges(
    records: list[dict], ids_by_path: dict[str, str], breadth: int
) -> dict[tuple[str, str], dict]:
    """One edge per pair of documents with a dated section within seven days of each other.

    A pair keeps its strongest window: the fewer documents dated in a window, the more two
    documents dated inside it have in common. The anchors are the two dated sections.
    """
    dated: dict[str, dict[str, str]] = {}
    for record in records:
        if record["kind"] != "date" or as_iso(record["value"]) is None:
            continue
        for anchor in record["anchors"]:
            doc_id = document_of(anchor, ids_by_path)
            if doc_id:
                dated.setdefault(str(record["value"]), {}).setdefault(doc_id, anchor)

    days = sorted(dated)
    as_days = {day: datetime.date.fromisoformat(day) for day in days}
    best: dict[tuple[str, str], dict] = {}
    for first in days:
        near = [day for day in days if abs((as_days[day] - as_days[first]).days) <= DATE_WINDOW]
        population: set[str] = set()
        for day in near:
            population |= set(dated[day])
        if len(population) < 2 or len(population) > breadth:
            continue
        weight = value_weight("date", len(population))
        for second in near:
            if second < first:
                continue
            value = first if first == second else f"{first} to {second}"
            both = sorted(set(dated[first]) | set(dated[second]))
            for a, b in itertools.combinations(both, 2):
                anchor_a = dated[first].get(a) or dated[second].get(a)
                anchor_b = dated[second].get(b) or dated[first].get(b)
                if anchor_a is None or anchor_b is None:
                    continue
                pair = (a, b)
                if pair in best and best[pair]["weight"] >= weight:
                    continue
                best[pair] = {
                    "a": a,
                    "b": b,
                    "kind": "date",
                    "value": value,
                    "anchors": {"a": anchor_a, "b": anchor_b},
                    "weight": weight,
                }
    return best


def build_edges(
    records: list[dict],
    sections: list[dict],
    notes: dict[str, dict],
    ids_by_path: dict[str, str],
    first_anchors: dict[str, str],
    order: list[str],
) -> list[dict]:
    """Every edge of the map, sorted by its two documents, its kind and its value."""
    breadth = max(2, int(len(order) * BREADTH_SHARE))
    skipped = person_values(notes) | ordinary_words(sections)
    named = {doc_id: named_values(note) for doc_id, note in notes.items()}

    edges: dict[tuple, dict] = {}
    for kind, value, carriers in shared_values(
        records, notes, ids_by_path, first_anchors, skipped
    ):
        if len(carriers) < 2 or len(carriers) > breadth:
            continue
        weight = value_weight(kind, len(carriers))
        folded = fold(value)
        for a, b in itertools.combinations(sorted(carriers), 2):
            if kind != "version":
                if not (is_about(named.get(a), folded) and is_about(named.get(b), folded)):
                    continue
            marker = (a, b, kind, str(value))
            if marker in edges and edges[marker]["weight"] >= weight:
                continue
            edges[marker] = {
                "a": a,
                "b": b,
                "kind": kind,
                "value": str(value),
                "anchors": {"a": carriers[a], "b": carriers[b]},
                "weight": weight,
            }

    for pair, edge in date_edges(records, ids_by_path, breadth).items():
        marker = (pair[0], pair[1], "date", edge["value"])
        edges.setdefault(marker, edge)

    return [edges[marker] for marker in sorted(edges)]


def adjacency(edges: list[dict]) -> dict[str, dict[str, float]]:
    """The total weight between every pair of documents an edge joins."""
    linked: dict[str, dict[str, float]] = {}
    for edge in edges:
        a, b, weight = edge["a"], edge["b"], edge["weight"]
        for one, other in ((a, b), (b, a)):
            side = linked.setdefault(one, {})
            side[other] = side.get(other, 0.0) + weight
    return linked


def choose_seed(edges: list[dict], order: list[str]) -> list[str]:
    """The document the matter is seeded at: the one whose strongest links are the strongest.

    A document is measured by the sum of its three heaviest links that are not mere date
    proximity, so a document sharing several rare values with several documents wins over one
    the room mentions often.
    """
    strongest: dict[str, list[float]] = {}
    for edge in edges:
        if edge["kind"] == "date":
            continue
        strongest.setdefault(edge["a"], []).append(edge["weight"])
        strongest.setdefault(edge["b"], []).append(edge["weight"])
    pull = {
        doc: sum(sorted(strongest.get(doc, []), reverse=True)[:SEED_LINKS]) for doc in order
    }
    head = min(order, key=lambda doc: (-pull[doc], doc))
    return [head]


def score_documents(
    linked: dict[str, dict[str, float]], seed: list[str], order: list[str]
) -> dict[str, float]:
    """Every document's score against the seed.

    The first term is what the document shares with the seed. The second is one round of that
    score spread along the edges, each neighbour's contribution divided by the neighbour's own
    total weight, so a document the whole room links to passes on almost nothing and a document
    with two links passes on most of what it has. The seed itself is scored above the room.
    """
    direct = {doc: sum(linked.get(doc, {}).get(head, 0.0) for head in seed) for doc in order}
    others = [direct[doc] for doc in order if doc not in seed]
    highest = max(others) if others else 0.0
    for head in seed:
        direct[head] = highest * 1.5 if highest else 1.0
    top = max(direct.values()) or 1.0
    near = {doc: value / top for doc, value in direct.items()}

    degree = {doc: sum(linked.get(doc, {}).values()) for doc in order}
    spread = {}
    for doc in order:
        total = 0.0
        for other, weight in linked.get(doc, {}).items():
            if other == doc or near.get(other, 0.0) <= 0 or degree.get(other, 0.0) <= 0:
                continue
            total += weight * near[other] / degree[other]
        spread[doc] = total
    furthest = max(spread.values()) or 1.0
    return {doc: round(near[doc] + spread[doc] / furthest, 6) for doc in order}


def reasons(edges: list[dict], scores: dict[str, float]) -> dict[str, list[str]]:
    """The values that carry each document's score, heaviest first.

    A link counts for as much as its weight times the score of the document at its other end,
    which is what the score itself is built from.
    """
    pull: dict[str, dict[str, float]] = {}
    for edge in edges:
        for side, other in (("a", "b"), ("b", "a")):
            doc = edge[side]
            gain = edge["weight"] * scores.get(edge[other], 0.0)
            current = pull.setdefault(doc, {})
            current[edge["value"]] = max(current.get(edge["value"], 0.0), gain)
    ranked = {}
    for doc, values in pull.items():
        best = sorted(values.items(), key=lambda pair: (-pair[1], pair[0]))
        ranked[doc] = [value for value, _ in best[:WHY_LIMIT]]
    return ranked


def matter_date(seed: list[str], core: list[str], dated: dict[str, list[str]]) -> str | None:
    """The day the matter starts: the earliest day the seed shares with a document of the core.

    The core is the seed and the documents that share a value with it, which is the set before
    any consequence is read, because the consequences are found by that day. Where the seed
    shares no day, its own earliest day stands; where it carries no day at all, the matter has
    no date.
    """
    others = [doc for doc in core if doc not in seed]
    for head in seed:
        shared = [
            day
            for day in dated.get(head, [])
            if any(day in dated.get(other, []) for other in others)
        ]
        if shared:
            return min(shared)
    for head in seed:
        if dated.get(head):
            return min(dated[head])
    return None


def value_edges(edges: list[dict]) -> dict[tuple[str, str], dict[str, tuple[float, int]]]:
    """The values the set is built along, by pair of documents, each with its weight and its
    number of carriers.

    Date edges are left out, because two documents dated in the same week are not linked by a
    value, and so is any value that is a bare count. The number of carriers is read back off the
    weight the edge was given, which is the kind's weight divided by that number. Where a pair
    shares one value twice over, by an index the room saw and by a note that wrote it down, the
    heavier of the two stands.
    """
    shared: dict[tuple[str, str], dict[str, tuple[float, int]]] = {}
    for edge in edges:
        value = edge["value"]
        if edge["kind"] == "date" or is_count(value):
            continue
        held = (edge["weight"], max(2, round(KIND_WEIGHTS[edge["kind"]] / edge["weight"])))
        for one, other in ((edge["a"], edge["b"]), (edge["b"], edge["a"])):
            side = shared.setdefault((one, other), {})
            if held[0] > side.get(value, (0.0, 0))[0]:
                side[value] = held
    return shared


def shared_links(
    seed: list[str], shared: dict[tuple[str, str], dict[str, tuple[float, int]]], order: list[str]
) -> dict[str, dict]:
    """Every document with a value in common with the seed, and the values it came by.

    A row lists the heaviest WHY_LIMIT of those values, which are the rarest of them, so a
    reader sees what the document and the seed share and not how much of the room they share.
    """
    found: dict[str, dict] = {}
    for doc in order:
        if doc in seed:
            continue
        heads: list[str] = []
        values: dict[str, float] = {}
        for head in seed:
            held = shared.get((doc, head), {})
            if not held:
                continue
            heads.append(head)
            for value, (weight, _) in held.items():
                values[value] = max(values.get(value, 0.0), weight)
        if not values:
            continue
        best = sorted(values, key=lambda value: (-values[value], value))[:WHY_LIMIT]
        found[doc] = {"from": sorted(heads), "kind": "shared", "values": sorted(best)}
    return found


def version_links(versions: list[dict], inside: set[str]) -> dict[str, dict]:
    """The other half of every version pair the set already holds one half of.

    A draft and its final are one document written twice, so the set takes both or neither.
    """
    found: dict[str, dict] = {}
    for pair in versions:
        for doc, other in (tuple(pair["docs"]), tuple(reversed(pair["docs"]))):
            if doc in inside or other not in inside:
                continue
            found[doc] = {
                "from": [other],
                "kind": "version",
                "values": sorted(pair["docs"]),
            }
    return found


def break_links(broken: list[dict], seed: list[str]) -> dict[str, dict]:
    """Every document whose series turned in the matter's own week, linked to the seed."""
    return {
        row["doc"]: {"from": sorted(seed), "kind": "consequence", "values": [row["period"]]}
        for row in broken
    }


def model_links(
    modelled: list[dict], notes: dict[str, dict], inside: set[str]
) -> dict[str, dict]:
    """Every model written after the matter, linked to the set documents that hold its figure.

    The figure is the number the model still assumes and the broken series left behind, and the
    documents behind the model are the ones whose notes carry that same number. The number is
    the one model_after wrote on the row, not the first figure at the row's anchor: thirteen
    figures of DR-021 share one anchor of its finance pack and the first of them is carried by
    no other document of the set.
    """
    carried: dict[str, list[str]] = {}
    for doc in sorted(inside):
        for figure in notes.get(doc, {}).get("figures", []):
            number = figure_number(figure["surface"])
            if number:
                carried.setdefault(number, []).append(doc)
    found: dict[str, dict] = {}
    for row in modelled:
        number = row["figure"]
        holders = sorted(set(carried.get(number, [])) - {row["doc"]})
        if not holders:
            continue
        found[row["doc"]] = {
            "from": holders,
            "kind": "consequence",
            "values": [number],
        }
    return found


def reach_links(
    shared: dict[tuple[str, str], dict[str, tuple[float, int]]],
    inside: set[str],
    order: list[str],
    written: tuple[set[str], set[str]],
) -> dict[str, dict]:
    """Every document the set reaches by values of the matter, from two places or by one figure.

    A value of the matter is a value the room's notes write and the matter owns. The notes write
    it where a cross reference or a figure carries it, whole or as a word inside one they carry.
    The matter owns it where every other document of the room that carries it is in the set
    already, so the value reaches this one document and no other.

    Both halves are needed. `EBITDA`, `MAU`, `CEO` and `Day-1` are in no cross reference and no
    figure: the room writes them in front of a number, beside a person and on a milestone, and
    the index cut them out of its prose. `LLP` is written after three firms and `SOC` in front
    of a certificate, so the notes do write both, but eleven documents carry either and the set
    holds three of them, so neither is the matter's.

    An exact money figure is a value of the matter whether the matter owns it or not, because a
    figure only a few documents carry names a matter as well as a code does. A value more than
    REACH_SHARE of the room carries is not a value of the matter at all.

    A document joins where two documents of the set each share a value of the matter with it,
    those are two different values, and the matter owns at least one of the two. It joins on one
    value alone where that value is an exact money figure the matter owns; the row then carries
    that one document and that one figure, the heaviest of them where the document has several,
    and the earliest by value and by id where two weigh the same.
    """
    breadth = REACH_SHARE * len(order)
    holders = value_holders(shared)
    found: dict[str, dict] = {}
    for doc in order:
        if doc in inside:
            continue
        carried: dict[str, set[str]] = {}
        owned: set[str] = set()
        money: tuple[float, str, str] | None = None
        for other in sorted(inside):
            for value, (weight, carriers) in shared.get((doc, other), {}).items():
                if carriers > breadth or not is_written(value, written):
                    continue
                owns = not (holders[value] - inside - {doc})
                if not (owns or value.startswith("$")):
                    continue
                carried.setdefault(value, set()).add(other)
                if not owns:
                    continue
                owned.add(value)
                if value.startswith("$"):
                    mark = (-weight, value, other)
                    if money is None or mark < money:
                        money = mark
        heads = {other for held in carried.values() for other in held}
        if len(carried) >= 2 and len(heads) >= 2 and owned:
            found[doc] = {"from": sorted(heads), "kind": "reach", "values": sorted(carried)}
        elif money is not None:
            found[doc] = {"from": [money[2]], "kind": "reach", "values": [money[1]]}
    return found


def compare_links(
    inside: set[str],
    nodes: dict[str, dict],
    notes: dict[str, dict],
    sections: list[dict],
    ids_by_path: dict[str, str],
) -> dict[str, dict]:
    """Every document a document of the set asks, in the room's own words, to be read against.

    A note names another document by its id or its file name, and the section it names it in
    carries a compare word. That is the room asking for the two to be put side by side, which is
    a reason to hold the second document whatever else it shares.
    """
    held = sections_by_document(sections, ids_by_path)
    named = named_by(nodes)
    found: dict[str, dict] = {}
    for doc in sorted(inside):
        note = notes.get(doc)
        if not note:
            continue
        texts = dict(held.get(doc, []))
        for reference in sorted(
            note["cross_references"], key=lambda item: (item["anchor"], str(item["value"]))
        ):
            other = named.get(str(reference["value"]).strip().upper())
            if other is None or other == doc or other in inside or other in found:
                continue
            text = texts.get(reference["anchor"])
            if not text or not COMPARE_WORDS.search(text):
                continue
            found[other] = {
                "from": [doc],
                "kind": "compare",
                "values": [str(reference["value"])],
            }
    return found


def covenant_links(
    core: list[str],
    notes: dict[str, dict],
    inside: set[str],
    order: list[str],
    written: tuple[set[str], set[str]],
) -> dict[str, dict]:
    """Every document outside the set whose termination clause writes a set document's own words.

    A flag quoted with a termination word that writes the same run of words as a flag of the
    seed, or of a document the seed joined by `shared`, is a right to end an agreement over what
    the set already holds. The run has to be more than the words every agreement writes: either
    the set document's flag is quoted with a termination word as well, so the run is one right
    written twice, or the run names a value of the matter, so it is one subject written twice.
    `written notice if the other party materially breaches this agreement` is the first, `as the
    Trust Reset` is the second, and `change of control` and `without undue delay` are neither.
    Whether the clause gives the right or takes it away is not read here: the dossier reads the
    clause out of the note.
    """
    said = [(head, flag) for head in core if head in notes for flag in notes[head]["flags"]]
    found: dict[str, dict] = {}
    for doc in order:
        note = notes.get(doc)
        if doc in inside or not note:
            continue
        for flag in note["flags"]:
            if not TERMINATION_WORDS.search(one_line(flag["quote"])):
                continue
            mine = folded_words(flag["quote"])
            for head, other in said:
                run = shared_run(mine, folded_words(other["quote"]))
                if run is None:
                    continue
                words = " ".join(run)
                ends = bool(TERMINATION_WORDS.search(one_line(other["quote"])))
                if not (ends or names_a_value(words, written)):
                    continue
                found[doc] = {"from": [head], "kind": "covenant", "values": [words]}
                break
            if doc in found:
                break
    return found


def version_pairs(
    records: list[dict],
    ids_by_path: dict[str, str],
    nodes: dict[str, dict],
    inside: set[str],
) -> list[dict]:
    """The index's draft and final pairs that touch the set, the draft first.

    A pair carries its two documents, the two dates the index read off them and the two status
    lists the map's own nodes carry.
    """
    pairs = []
    for record in records:
        if record["kind"] != "version-pair":
            continue
        value = record["value"]
        draft = ids_by_path.get(value.get("draft"))
        final = ids_by_path.get(value.get("final"))
        if not draft or not final or not ({draft, final} & inside):
            continue
        if not value.get("draft_date") or not value.get("final_date"):
            continue
        pairs.append(
            {
                "dates": [str(value["draft_date"]), str(value["final_date"])],
                "docs": [draft, final],
                "status": [nodes[draft]["status"], nodes[final]["status"]],
            }
        )
    return sorted(pairs, key=lambda pair: pair["docs"])


def row_series(
    records: list[dict], sections: dict[str, dict], ids_by_path: dict[str, str]
) -> list[dict]:
    """Every index series whose members are the rows of one table, read back as numbers.

    A series is kept where every member row is a section of the run, every row's leading cell is
    a day, and at least one column holds a number in every row. A series of documents, five
    quarters of board minutes, has no rows and is not one of these.
    """
    found = []
    for record in records:
        value = record["value"]
        if record["kind"] != "series" or value.get("form") != "rows":
            continue
        doc = ids_by_path.get(record["docs"][0]) if record["docs"] else None
        members = list(value.get("members", []))
        rows = [sections.get(anchor) for anchor in members]
        if doc is None or not rows or any(row is None for row in rows):
            continue
        # A row of a markdown rendition carries its fields as one line and no cells, and the
        # index's own line-cell rule reads them back the way the sheet gave them.
        cells = [row.get("cells") or line_cells(row["text"]) for row in rows]
        if not all(cells):
            continue
        days = [as_day(row[0]["value"]) for row in cells]
        if any(day is None for day in days):
            continue
        columns = []
        for at in range(1, min(len(row) for row in cells)):
            numbers = [as_number(row[at]["value"]) for row in cells]
            if all(number is not None for number in numbers):
                columns.append(numbers)
        if columns:
            found.append(
                {
                    "anchors": members,
                    "columns": columns,
                    "days": days,
                    "doc": doc,
                    "series": str(record["surface"]),
                }
            )
    return found


def series_break(
    series: list[dict], date: str | None, seed: list[str]
) -> tuple[list[dict], set[str]]:
    """Every series break of the matter, and the numbers those series carried before turning.

    A series turns at the earliest period any of its columns turns. The matter keeps every
    series that turns on or after its own date and no more than DATE_WINDOW days later, in a
    document that is not the seed. Two tables of the same weeks turn on the same day when the
    matter moved both, and both are kept. The breaks come back sorted by document and period,
    and the numbers are the union of what the turning columns carried before their turn.
    """
    began = as_iso(date) if date else None
    if began is None:
        return [], set()
    found = []
    before: set[str] = set()
    for table in series:
        if table["doc"] in seed:
            continue
        turns = [turn_index(column) for column in table["columns"]]
        places = [turn for turn in turns if turn is not None]
        if not places:
            continue
        at = min(places)
        day = table["days"][at]
        if day < began or (day - began).days > DATE_WINDOW:
            continue
        for column, turn in zip(table["columns"], turns):
            if turn == at:
                before.update(format(value, "g") for value in column[:at])
        found.append(
            {
                "anchor": table["anchors"][at],
                "doc": table["doc"],
                "kind": "series-break",
                "period": day.isoformat(),
                "series": table["series"],
            }
        )
    return sorted(found, key=lambda row: (row["doc"], row["period"])), before


def model_after(
    notes: dict[str, dict],
    nodes: dict[str, dict],
    inside: set[str],
    date: str | None,
    before: set[str],
) -> list[dict]:
    """Every model written after the matter that still carries one of its old numbers.

    A model is a document whose file name, whose folder or whose note's own words say model,
    forecast, plan or synergy. It is a consequence of the matter where its first date is after
    the matter, where one of its note's figures is a number the broken series carried before it
    turned, and where another document of the set carries that figure as well. The anchor is the
    figure's place in the model and figure is its number, since one anchor can carry many
    figures; the first such figure of the note stands for the model.
    A number that outlived the matter in two models is two models to correct, so every model is
    kept and not only the earliest. The models come back sorted by document.
    """
    if not date or not before:
        return []
    carried: dict[str, set[str]] = {}
    for doc in inside:
        for figure in notes.get(doc, {}).get("figures", []):
            number = figure_number(figure["surface"])
            if number:
                carried.setdefault(number, set()).add(doc)
    found = []
    for doc in sorted(notes):
        node = nodes[doc]
        if not node["date"] or node["date"] <= date:
            continue
        words = _LETTERS.findall(notes[doc].get("what") or "")
        words += _LETTERS.findall(node["folder"])
        words += _LETTERS.findall(Path(node["path"]).stem)
        if not MODEL_WORDS & {word.casefold() for word in words}:
            continue
        for figure in notes[doc]["figures"]:
            number = figure_number(figure["surface"])
            if number is None or number not in before:
                continue
            if not carried.get(number, set()) - {doc}:
                continue
            found.append(
                {
                    "anchor": figure["anchor"],
                    "date": node["date"],
                    "doc": doc,
                    "figure": number,
                    "kind": "model-after",
                }
            )
            break
    return found


def build_map(sample_dir: Path, run_dir: Path) -> dict:
    """Reads a sample's index, sections and notes and returns the map."""
    key = load_key(sample_dir)
    order = list(key.documents)
    ids_by_path = {path: doc_id for doc_id, path in key.documents.items()}

    sections = read_jsonl(run_dir / "sections.jsonl")
    records = read_jsonl(run_dir / "index.jsonl")
    notes = read_notes(run_dir, ids_by_path)

    first_anchors: dict[str, str] = {}
    for section in sections:
        doc_id = ids_by_path.get(section["doc"])
        if doc_id and doc_id not in first_anchors:
            first_anchors[doc_id] = section["anchor"]

    dated: dict[str, list[str]] = {}
    statuses: dict[str, set[str]] = {}
    for record in records:
        if record["kind"] == "date" and as_iso(record["value"]) is not None:
            for anchor in record["anchors"]:
                doc_id = document_of(anchor, ids_by_path)
                if doc_id:
                    dated.setdefault(doc_id, []).append(str(record["value"]))
        elif record["kind"] == "status":
            for anchor in record["anchors"]:
                doc_id = document_of(anchor, ids_by_path)
                if doc_id:
                    statuses.setdefault(doc_id, set()).add(str(record["value"]))
    dated = {doc: sorted(set(days)) for doc, days in dated.items()}

    documents = []
    for doc_id in order:
        path = key.documents[doc_id]
        days = dated.get(doc_id, [])
        documents.append(
            {
                "date": days[0] if days else None,
                "doc": doc_id,
                "folder": Path(path).parent.name,
                "path": path,
                "status": sorted(statuses.get(doc_id, ())),
            }
        )

    edges = build_edges(records, sections, notes, ids_by_path, first_anchors, order)
    linked = adjacency(edges)
    seed = choose_seed(edges, order)
    scores = score_documents(linked, seed, order)

    nodes = {node["doc"]: node for node in documents}
    shared = value_edges(edges)
    written = written_values(notes)
    why = reasons(edges, scores)

    via: dict[str, dict] = {head: {"from": [], "kind": "seed", "values": []} for head in seed}
    inside = set(seed)

    def hold(links: dict[str, dict]) -> None:
        """Puts every document a rule found into the set, leaving the links already there."""
        for doc, link in links.items():
            if doc not in via:
                via[doc] = link
                inside.add(doc)

    hold(shared_links(seed, shared, order))
    core = sorted(inside)

    date = matter_date(seed, core, dated)
    versions = version_pairs(records, ids_by_path, nodes, set(inside))
    hold(version_links(versions, set(inside)))

    by_anchor = {section["anchor"]: section for section in sections}
    broken, before = series_break(row_series(records, by_anchor, ids_by_path), date, seed)
    hold(break_links(broken, seed))
    modelled = model_after(notes, nodes, set(inside), date, before)
    hold(model_links(modelled, notes, set(inside)))
    consequences = sorted(broken + modelled, key=lambda row: (row["kind"], row["doc"]))

    hold(reach_links(shared, set(inside), order, written))
    hold(compare_links(set(inside), nodes, notes, sections, ids_by_path))
    hold(covenant_links(core, notes, set(inside), order, written))

    lift = max(scores.values(), default=0.0)
    for doc in inside:
        scores[doc] = round(scores[doc] + lift, 6)
    ordered = sorted(order, key=lambda doc: (doc not in inside, -scores[doc], doc))
    ranked = [
        {"doc": doc, "score": scores[doc], "via": via.get(doc), "why": why.get(doc, [])}
        for doc in ordered
    ]

    matter = {
        "cluster": sorted(inside),
        "consequences": consequences,
        "date": date,
        "id": 1,
        "ranked": ranked,
        "seed": seed,
        "versions": versions,
    }
    return {
        "documents": documents,
        "edges": [
            {
                "a": edge["a"],
                "anchors": edge["anchors"],
                "b": edge["b"],
                "kind": edge["kind"],
                "value": edge["value"],
                "weight": round(edge["weight"], 6),
            }
            for edge in edges
        ],
        "matters": [matter],
        "sample": key.sample,
    }


def write_map(document: dict, run_dir: Path) -> Path:
    """Writes the map to runs/<sample>/map.json with sorted keys and one trailing newline."""
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "map.json"
    path.write_text(
        json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def readout_line(document: dict, seconds: float) -> str:
    """The one line a map run prints: the counts, the cluster and the time it took."""
    by_kind: dict[str, int] = {}
    for edge in document["edges"]:
        by_kind[edge["kind"]] = by_kind.get(edge["kind"], 0) + 1
    counted = ", ".join(f"{kind} {by_kind[kind]}" for kind in sorted(by_kind))
    empty: dict = {"cluster": [], "consequences": [], "versions": []}
    matter = document["matters"][0] if document["matters"] else empty
    return (
        f"map {document['sample']}: nodes {len(document['documents'])}, "
        f"edges {len(document['edges'])} ({counted}), "
        f"matters {len(document['matters'])}, "
        f"cluster {len(matter['cluster'])}, "
        f"versions {len(matter['versions'])}, "
        f"consequences {len(matter['consequences'])}, "
        f"seconds {seconds:.1f}"
    )


def main(argv: list[str]) -> int:
    """Maps one sample from the command line and prints the readout line."""
    if len(argv) != 2:
        print("usage: python -m rlm.map <sample_dir> <run_dir>")
        return 2
    sample_dir, run_dir = Path(argv[0]), Path(argv[1])
    started = time.monotonic()
    document = build_map(sample_dir, run_dir)
    write_map(document, run_dir)
    print(readout_line(document, time.monotonic() - started))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
