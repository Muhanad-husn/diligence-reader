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

Nothing here reads the key's facts, its required documents or its decoys, opens a socket or
calls a model. The key is read for the id and path of each document and for nothing else.
"""

from __future__ import annotations

import collections
import datetime
import itertools
import json
import re
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

# How many of a document's strongest links are read when the seed is chosen.
SEED_LINKS = 3

# The id of the key fact the phase 3 tests read the planted cluster from.
MATTER_FACT = "matter-documents"

# How many values a ranked row gives as its reason.
WHY_LIMIT = 3

_WORD = re.compile(r"[A-Za-z][A-Za-z\-]+")
_LOOSE = re.compile(r"[^a-z0-9]+")


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
    why = reasons(edges, scores)

    ordered = sorted(order, key=lambda doc: (-scores[doc], doc))
    ranked = [
        {"doc": doc, "score": scores[doc], "why": why.get(doc, [])} for doc in ordered
    ]
    size = cluster_size([row["score"] for row in ranked])
    cluster = sorted(row["doc"] for row in ranked[:size])

    matter = {
        "cluster": cluster,
        "consequences": [],
        "date": matter_date(seed, cluster, dated),
        "id": 1,
        "ranked": ranked,
        "seed": seed,
        "versions": [],
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
    matter = document["matters"][0] if document["matters"] else {"cluster": []}
    return (
        f"map {document['sample']}: nodes {len(document['documents'])}, "
        f"edges {len(document['edges'])} ({counted}), "
        f"matters {len(document['matters'])}, "
        f"cluster {len(matter['cluster'])}, "
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
