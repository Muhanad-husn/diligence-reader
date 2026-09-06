"""Builds runs/<sample>/map.json from the index, the sections and the notes.

The map is a graph of the room. Its nodes are the documents the key names, in the key's own
order, each with its folder, its first date and the status words the index read off it. Its
edges are the values two documents share: an `identifier` the index saw, a `cross-reference` a
note wrote, a `version` pair of a draft and its final, and a `date` where two documents carry a
dated section within seven days of each other. A shared value weighs less the more documents
carry it, so AURORA in sixteen documents weighs a quarter of `vpauth-legacy-2019` in four.

An `identifier` or `cross-reference` edge is kept only where the value is inside a flag or a
concealed item of both documents. A value only the index saw joins two documents by coincidence
about as often as by matter; a value both notes wrote down as a worry is the matter itself.
Date and version edges are kept as they are, because neither is a coincidence of vocabulary.

The matter is seeded at the document whose three strongest links are the strongest in the room.
Every document is then scored by what it shares with the seed, plus one round of that score
spread along the edges, each neighbour's contribution divided by its own total weight so that
the room's index and its Q&A log, which link to everything, pass on almost nothing. The cluster
is the prefix of the ranked list still scoring at least a hundredth of the highest score.

The matter then carries two things a graph of shared values cannot see. Its `versions` are the
index's draft and final pairs where at least one of the two is in the cluster, with the two
dates and the two status lists the map already read. Its `consequences` are two links the map
finds by mechanism. A `series-break` is a table of periods in the room whose numbers turn: the
step from one period to the next starts running one way and each step is bigger than the
column's usual step. A series turns once, at the earliest period any of its columns turns, and
the matter keeps the turn nearest its own date, inside a week of it and on or after it, in a
document that is not the seed. Where two series turn on the same day the map keeps the one in
the document scoring highest against the seed. A `model-after` is a document whose name, folder
or note says model, forecast, plan or synergy, dated after the matter, whose note still carries
a figure the broken series left behind: the same number, ignoring the currency and the unit
letter, so 615m and 615 are one figure and 4100 is not 410. The figure has to be a figure of
another cluster document's note as well. The matter keeps the earliest such model.

Each consequence adds a twentieth of the highest score to its document before the ranking is
taken, which is five times the cluster cut. A document the room barely mentions is lifted inside
the cluster by a consequence alone, and a document that shares the matter's own codes still
outranks it.

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

from rlm.key import load_key

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

# A document stays in the cluster while it scores at least this share of the highest score.
CLUSTER_SHARE = 0.01

# What one consequence adds to a document's score, as a share of the highest score. Five times
# the cluster cut: a consequence alone puts a document inside the cluster and no further.
CONSEQUENCE_SHARE = 5 * CLUSTER_SHARE

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
_LOOSE = re.compile(r"[^a-z0-9]+")
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


def fold(value) -> str:
    """The comparable form of a value: lower case, with every run of punctuation a single space.

    `kid=vpauth-legacy-2019` and `kid vpauth legacy 2019` fold to the same thing, so a value can
    be looked for inside the words of a flag whatever punctuation either side used.
    """
    return _LOOSE.sub(" ", str(value).casefold()).strip()


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


def cluster_size(scores: list[float]) -> int:
    """How many of the ranked documents are in the cluster.

    Scores come in descending order. The cut is a share of the highest score, so it moves with
    the room and is not a count fitted to any one sample: a document is in the cluster while it
    scores at least a hundredth of what the strongest document scores.
    """
    if not scores or scores[0] <= 0:
        return 0
    cut = scores[0] * CLUSTER_SHARE
    size = 0
    for score in scores:
        if score < cut:
            break
        size += 1
    return size


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


def worry_text(note: dict) -> str:
    """The folded words of a note's flags and concealed items, joined into one string.

    This is where a value has to appear for the map to count it as a link: what the note wrote
    down as a worry, not what the document happens to mention.
    """
    parts = []
    for flag in note["flags"]:
        parts += [flag["flag"], flag["quote"], flag["consequence"]]
    for item in note["concealed"]:
        parts += [item["claim"], item["quote"]]
    return fold(" ".join(parts))


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


def document_of(anchor: str, ids_by_path: dict[str, str]) -> str | None:
    """The document id an anchor belongs to, or None where the anchor names no key document."""
    return ids_by_path.get(anchor.rsplit("#", 1)[0])


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
    worries = {doc_id: worry_text(note) for doc_id, note in notes.items()}

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
                worried = folded and folded in worries.get(a, "") and folded in worries.get(b, "")
                if not worried:
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


def matter_date(
    seed: list[str], cluster: list[str], dated: dict[str, list[str]]
) -> str | None:
    """The day the matter starts: the earliest day the seed shares with another cluster document.

    Where the seed shares no day, its own earliest day stands; where it carries no day at all,
    the matter has no date.
    """
    others = [doc for doc in cluster if doc not in seed]
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


def clustered(order: list[str], scores: dict[str, float]) -> list[str]:
    """The documents above the cut, by id."""
    ordered = sorted(order, key=lambda doc: (-scores[doc], doc))
    return sorted(ordered[: cluster_size([scores[doc] for doc in ordered])])


def version_pairs(
    records: list[dict],
    ids_by_path: dict[str, str],
    nodes: dict[str, dict],
    cluster: set[str],
) -> list[dict]:
    """The index's draft and final pairs that touch the cluster, the draft first.

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
        if not draft or not final or not ({draft, final} & cluster):
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
        cells = [row.get("cells") or [] for row in rows]
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
    series: list[dict], date: str | None, seed: list[str], scores: dict[str, float]
) -> tuple[dict | None, set[str]]:
    """The matter's one series break, and the numbers that series carried before it turned.

    A series turns at the earliest period any of its columns turns. The matter keeps the turn
    nearest its own date, on or after it and no more than DATE_WINDOW days later, in a document
    that is not the seed. Where two series turn on the same day the map keeps the one in the
    document scoring highest against the seed.
    """
    began = as_iso(date) if date else None
    if began is None:
        return None, set()
    best = None
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
        marker = ((day - began).days, -scores.get(table["doc"], 0.0), table["doc"])
        if best is None or marker < best[0]:
            best = (marker, table, turns, at, day)
    if best is None:
        return None, set()
    _, table, turns, at, day = best
    before = set()
    for column, turn in zip(table["columns"], turns):
        if turn == at:
            before.update(format(value, "g") for value in column[:at])
    found = {
        "anchor": table["anchors"][at],
        "doc": table["doc"],
        "kind": "series-break",
        "period": day.isoformat(),
        "series": table["series"],
    }
    return found, before


def model_after(
    notes: dict[str, dict],
    nodes: dict[str, dict],
    cluster: set[str],
    date: str | None,
    before: set[str],
) -> dict | None:
    """The earliest model written after the matter that still carries one of its old numbers.

    A model is a document whose file name, whose folder or whose note's own words say model,
    forecast, plan or synergy. It is a consequence of the matter where its first date is after
    the matter, where one of its note's figures is a number the broken series carried before it
    turned, and where another cluster document's note carries that figure as well. The anchor is
    the figure's place in the model.
    """
    if not date or not before:
        return None
    carried: dict[str, set[str]] = {}
    for doc in cluster:
        for figure in notes.get(doc, {}).get("figures", []):
            number = figure_number(figure["surface"])
            if number:
                carried.setdefault(number, set()).add(doc)
    best = None
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
            marker = (node["date"], doc)
            if best is None or marker < best[0]:
                best = (
                    marker,
                    {
                        "anchor": figure["anchor"],
                        "date": node["date"],
                        "doc": doc,
                        "kind": "model-after",
                    },
                )
            break
    return best[1] if best else None


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
    cluster = clustered(order, scores)
    date = matter_date(seed, cluster, dated)
    versions = version_pairs(records, ids_by_path, nodes, set(cluster))

    by_anchor = {section["anchor"]: section for section in sections}
    broken, before = series_break(
        row_series(records, by_anchor, ids_by_path), date, seed, scores
    )
    modelled = model_after(notes, nodes, set(cluster), date, before)
    consequences = sorted(
        (row for row in (broken, modelled) if row), key=lambda row: (row["kind"], row["doc"])
    )

    bonus = max(scores.values(), default=0.0) * CONSEQUENCE_SHARE
    for row in consequences:
        scores[row["doc"]] = round(scores[row["doc"]] + bonus, 6)

    why = reasons(edges, scores)
    ordered = sorted(order, key=lambda doc: (-scores[doc], doc))
    ranked = [{"doc": doc, "score": scores[doc], "why": why.get(doc, [])} for doc in ordered]

    matter = {
        "cluster": clustered(order, scores),
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
