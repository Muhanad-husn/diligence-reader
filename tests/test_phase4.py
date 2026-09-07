"""Phase 4 dossier tests. The dossier reads a sample's map, index, sections and notes and
writes dossier.md: the matter's document set, its timeline, the names the notes gave it, its
figures, the models blind to it, the comparisons the room's own words make and the lesser
matters the room holds outside the set. These tests run the dossier twice, the second time
into a temporary directory, and check that the two files are byte identical, that the first
matter's document set holds every document of the key's matter-documents fact and none of its
decoys, that every planted document is ranked above every decoy both in the map and in the
dossier's own list, that every phase 1 and phase 2 fact of the key has a row carrying its
value with an anchor that parses, belongs to one of the fact's documents and is one of the
anchors the phase 1 and 2 artefacts wrote, that the names section carries the workstream, the
programme and the ticket, that the models section carries the map's consequences, that every
comparison the key plants for phase 4 has a row naming its documents and quoting both sides of
its value, that the lesser matters section ranks every flagged document outside the set by its
largest money figure with every decoy in it, and that the run prints one readout line.

A comparison row is two or more `<doc> | <quote> | <anchor>` triples joined by ` || `. A side
of a comparison is the half of the key's value on one side of ` against `. A side is carried
when the quotes of one part of the row, its documents disjoint from the other side's, hold
every number of the side, every day of the side, and every word of the side that the fact's
documents carry at all. A day may also be carried by the phase 1 index having read that day in
one of those documents, which is how a mail header's own date reaches a row whose sections drop
it. Words are matched with one plural or tense ending dropped, so `drafted` reads `Draft` and
`retained` reads `RETAINED`. A word of the key's value that no document of the fact carries is
not asserted; it is written into the phase 4 readout instead.

A number a room writes without its unit is carried as well: the phase 1 index read the
workbook cell `22.2` under a `Revenue ($M)` header as $22.2M, so a row of that document whose
figure or quote holds `22.2` carries the fact. Whether a decoy outranks a planted document in
the map is not asked here either: the founder moved that check off the map on 2026-09-07,
because the northwind decoy shares its template with the seed, so it is the dossier's own
list, which the document set governs, that has to put every planted document above every
decoy.

All three gate samples are enabled. A sample whose dossier inputs are absent is skipped, as is
a check the sample plants nothing for: a map with no version pair has no draft against final,
and a key with no decoy has no decoy to place."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

from rlm.amounts import date_matches, normalise_amount
from rlm.dossier import main
from rlm.key import load_key
from rlm.map import read_notes
from rlm.notes import straighten
from rlm.sections import parse_anchor

ROOT = Path(__file__).resolve().parents[1]

# The three gate samples the dossier runs on.
ENABLED = ("atlas", "northwind", "northstar-dental")
SKIP_REASON = "dossier not run for this sample yet"

# What the dossier's inputs are called under runs/<sample>/.
INPUTS = ("index.jsonl", "map.json", "sections.jsonl")

# The headings the dossier writes for one matter, in the order it writes them.
SECTIONS = (
    "Documents",
    "Timeline",
    "Names",
    "Figures",
    "Models blind to it",
    "Comparisons",
    "Lesser matters",
)

# The sections whose rows are `- <date or figure> | <doc> | <quote> | <anchor>`.
ROW_SECTIONS = ("Timeline", "Names", "Figures", "Models blind to it")

# The section whose rows are triples joined by ` || `, and the one that ranks the room's rest.
COMPARISONS = "Comparisons"
LESSER = "Lesser matters"

# What splits a comparison fact's value into its two sides.
AGAINST = " against "

# What an empty field is written as, in the dossier and here.
EMPTY = "-"

# The words a value carries that say nothing about where it came from, before stemming.
STOP_SOURCE = (
    "a an and any are as at be been by for from has have in is it its no not of on or "
    "that the their there this to was were what which with"
)

_LETTERS = re.compile(r"[A-Za-z]{2,}")
_DIGITS = re.compile(r"[0-9]+")

# The endings one pass of the stemmer drops, longest first.
_ENDINGS = ("ings", "ing", "ions", "ion", "ies", "ied", "ees", "ed", "es", "ly", "s", "e", "y")


@dataclass(frozen=True)
class Row:
    """One row of the dossier: its section, its four fields and the line it was read from."""

    section: str
    first: str
    doc: str
    quote: str
    anchor: str
    line: str


@dataclass(frozen=True)
class Run:
    """One pair of dossier runs on a sample: the two files, the text and what was printed."""

    first: Path
    second: Path
    text: str
    printed: str


_RUNS: dict[str, Run] = {}


def _inputs_ready(run_dir: Path) -> bool:
    if not all((run_dir / name).exists() for name in INPUTS):
        return False
    notes_dir = run_dir / "notes"
    return notes_dir.is_dir() and any(notes_dir.glob("*.json"))


@pytest.fixture
def dossiered(sample, sample_dir, run_dir, capsys, tmp_path_factory):
    """Runs the dossier twice on the sample and returns both files, the text and the output.

    The pair of runs is done once per sample and reused. The second run reads copies of the
    same inputs from a temporary directory and writes its dossier there, which is what makes
    the byte-identical check a check on the dossier and not on the file it overwrote.
    """
    if sample not in ENABLED or not _inputs_ready(run_dir):
        pytest.skip(SKIP_REASON)
    if sample not in _RUNS:
        second_dir = tmp_path_factory.mktemp(f"dossier-{sample}")
        for name in INPUTS:
            shutil.copy(run_dir / name, second_dir / name)
        shutil.copytree(run_dir / "notes", second_dir / "notes")
        assert main([str(sample_dir), str(run_dir)]) == 0
        assert main([str(sample_dir), str(second_dir)]) == 0
        printed = capsys.readouterr().out
        first = run_dir / "dossier.md"
        _RUNS[sample] = Run(
            first=first,
            second=second_dir / "dossier.md",
            text=first.read_text(encoding="utf-8"),
            printed=printed,
        )
    return _RUNS[sample]


@pytest.fixture
def key(sample_dir):
    return load_key(sample_dir)


@pytest.fixture
def mapped(run_dir):
    """The map the dossier was written from."""
    return json.loads((run_dir / "map.json").read_text(encoding="utf-8"))


@pytest.fixture
def known_anchors(run_dir):
    """Every anchor the phase 1 and phase 2 artefacts wrote, by document path.

    An anchor the dossier writes has to be one of these: the dossier cites the artefacts it
    read and invents no place of its own.
    """
    found: dict[str, set[str]] = {}

    def keep(anchor):
        doc = anchor.rsplit("#", 1)[0]
        found.setdefault(doc, set()).add(anchor)

    for line in (run_dir / "sections.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        keep(record["anchor"])
        for cell in record.get("cells") or []:
            keep(f"{record['doc']}#{record['heading']}!{cell['ref']}")
    for line in (run_dir / "index.jsonl").read_text(encoding="utf-8").splitlines():
        for anchor in json.loads(line)["anchors"]:
            keep(anchor)
    for path in sorted((run_dir / "notes").glob("*.json")):
        note = json.loads(path.read_text(encoding="utf-8"))
        for field in ("concealed", "cross_references", "figures", "flags"):
            for item in note[field]:
                keep(item["anchor"])
    return found


# ---------------------------------------------------------------- reading the dossier back


def sections_of(text: str) -> dict[str, list[str]]:
    """The lines under each `### ` heading of the first matter, by heading."""
    found: dict[str, list[str]] = {}
    heading = None
    for line in text.splitlines():
        if line.startswith("### "):
            heading = line[4:].strip()
            found.setdefault(heading, [])
        elif heading is not None and line.startswith("- "):
            found[heading].append(line)
    return found


def rows_of(text: str) -> list[Row]:
    """Every four-field row of the dossier, with the section it sits in.

    A row is `- <date or figure> | <doc> | <quote> | <anchor>`. The quote is the only field
    that may itself hold a pipe, because a table row's cells are written that way, so the
    anchor is read off the end and the quote is what is left in the middle.
    """
    found = []
    for heading, lines in sections_of(text).items():
        if heading not in ROW_SECTIONS:
            continue
        for line in lines:
            fields = line[2:].split(" | ")
            assert len(fields) >= 4, line
            found.append(
                Row(
                    section=heading,
                    first=fields[0],
                    doc=fields[1],
                    quote=" | ".join(fields[2:-1]),
                    anchor=fields[-1],
                    line=line,
                )
            )
    return found


def document_rows(text: str) -> list[tuple[int, str]]:
    """The Documents section read back as (rank, document id) pairs, in file order."""
    found = []
    for line in sections_of(text).get("Documents", []):
        rank, _, rest = line[2:].partition(". ")
        found.append((int(rank), rest.split(" | ", 1)[0]))
    return found


def planted_documents(key) -> set[str]:
    """The documents the key's phase 3 document fact names: the matter's document set."""
    for fact in key.facts:
        if fact.id == "matter-documents":
            return set(fact.documents)
    for fact in key.facts:
        if fact.phase == 3 and fact.kind == "document":
            return set(fact.documents)
    return set(key.required_documents)


def fact_documents(key, fact_id: str) -> tuple[str, ...]:
    """The documents the key fact with that id resolves to, empty where there is no such fact."""
    for fact in key.facts:
        if fact.id == fact_id:
            return fact.documents
    return ()


def fact_value(key, fact_id: str):
    """The value of the key fact with that id, or None where the sample has no such fact."""
    for fact in key.facts:
        if fact.id == fact_id:
            return fact.value
    return None


# ---------------------------------------------------------------- the artefact


def test_dossier_is_markdown_with_one_trailing_newline(dossiered, sample):
    raw = dossiered.text
    assert raw.startswith(f"# Dossier: {sample}\n")
    assert raw.endswith("\n") and not raw.endswith("\n\n")


def test_dossier_two_runs_are_byte_identical(dossiered):
    """Two runs of the same sample write the same bytes, which is what makes it pinnable."""
    assert dossiered.first.read_bytes() == dossiered.second.read_bytes()


def test_dossier_carries_every_section_in_order(dossiered):
    """The first matter carries the seven headings of the phase, in the order the plan fixes."""
    order = [line[4:].strip() for line in dossiered.text.splitlines() if line.startswith("### ")]
    assert order[: len(SECTIONS)] == list(SECTIONS)


def test_dossier_documents_hold_the_planted_documents_and_no_decoy(dossiered, key):
    listed = [doc for _, doc in document_rows(dossiered.text)]
    assert listed, "the Documents section is empty"
    assert len(listed) == len(set(listed))
    planted = planted_documents(key)
    decoys = {decoy.document for decoy in key.decoys}
    assert planted <= set(listed), sorted(planted - set(listed))
    assert not (decoys & set(listed)), sorted(decoys & set(listed))


def test_dossier_ranks_every_planted_document_above_every_decoy(dossiered, key):
    """No decoy outranks a planted document in the dossier's own list.

    The map's ranking is not asked. On northwind the decoy is a master service agreement whose
    change-of-control clause is benign in its wording, the two agreements share their template,
    and the founder moved the decoy check off the map and onto the dossier on 2026-09-07. A
    decoy the document set leaves out is below every document the set holds.
    """
    planted = planted_documents(key)
    decoys = {decoy.document for decoy in key.decoys}
    if not decoys:
        pytest.skip("the key names no decoy")
    listed = document_rows(dossiered.text)
    assert [rank for rank, _ in listed] == sorted(rank for rank, _ in listed)
    places = {doc: rank for rank, doc in listed}
    below = max(places.values()) + 1
    assert max(places[doc] for doc in planted) < min(
        (places[doc] for doc in decoys if doc in places), default=below
    )


@pytest.fixture
def index_surfaces(run_dir, key):
    """Every surface the phase 1 index read as an amount, by document and by amount.

    The index reads a workbook cell `22.2` under a `Revenue ($M)` header as 22200000 USD. The
    room never writes `$22.2M`, so a fact of that value is carried by the surface the index
    read it from, in the document it read it in.
    """
    found: dict[str, dict[tuple, set[str]]] = {}
    ids = {path: doc for doc, path in key.documents.items()}
    for line in (run_dir / "index.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record["kind"] != "amount":
            continue
        marker = (record["value"], record["unit"])
        for anchor in record["anchors"]:
            doc = ids.get(anchor.rsplit("#", 1)[0])
            if doc is not None:
                found.setdefault(doc, {}).setdefault(marker, set()).add(str(record["surface"]))
    return found


def amount_of(value):
    """The value as an amount and its unit, or None where it names no amount."""
    try:
        return normalise_amount(str(value))
    except ValueError:
        return None


def test_dossier_carries_every_phase_1_and_2_fact(
    dossiered, key, known_anchors, index_surfaces
):
    """Every planted fact of phase 1 and phase 2 has a row that carries it.

    A row carries a fact when its date or figure field, or its quote, holds the fact's value
    after straightening, or holds a surface the phase 1 index read in that row's document as
    the fact's own amount, and its anchor parses, belongs to one of the fact's documents and is
    one of the anchors the phase 1 and 2 artefacts wrote.
    """
    rows = rows_of(dossiered.text)
    assert rows
    checked = 0
    for fact in key.facts:
        if fact.phase not in (1, 2):
            continue
        checked += 1
        wanted = straighten(fact.value)
        marker = amount_of(fact.value)

        def held(row, wanted=wanted, marker=marker):
            written = f"{straighten(row.first)} {straighten(row.quote)}"
            if wanted in written:
                return True
            if marker is None or marker[1] is None:
                return False
            surfaces = index_surfaces.get(row.doc, {}).get(marker, set())
            return any(straighten(surface) in written for surface in surfaces)

        hits = [row for row in rows if row.doc in fact.documents and held(row)]
        assert hits, f"{fact.id}: {fact.value!r} has no row in {list(fact.documents)}"
        good = []
        for row in hits:
            path = key.documents[row.doc]
            if parse_anchor(row.anchor).doc != path:
                continue
            if row.anchor in known_anchors.get(path, set()):
                good.append(row)
        assert good, f"{fact.id}: no row with an anchor of its own document"
    assert checked >= 1


def test_dossier_names_carry_the_workstream_the_programme_and_the_ticket(dossiered, key):
    """The names section gives each name the notes wrote a document and an anchor."""
    named = [row for row in rows_of(dossiered.text) if row.section == "Names"]
    assert named
    for fact_id in ("workstream", "programme", "ticket"):
        value = fact_value(key, fact_id)
        if value is None:
            continue
        wanted = straighten(value)
        hits = [row for row in named if wanted in straighten(row.first)]
        assert hits, f"{fact_id}: {value!r} is not in the Names section"
        for row in hits:
            assert row.doc in key.documents
            assert row.anchor.startswith(key.documents[row.doc] + "#")


def test_dossier_models_blind_to_it_carries_the_map_consequences(dossiered, key, mapped):
    """The section carries one row per consequence of the map's first matter, and the map
    carries a break for every series that turned and a model for every model dated after."""
    consequences = mapped["matters"][0]["consequences"]
    blind = [row for row in rows_of(dossiered.text) if row.section == "Models blind to it"]
    assert len(blind) == len(consequences)
    assert {row.anchor for row in blind} == {row["anchor"] for row in consequences}
    assert {row.doc for row in blind} == {row["doc"] for row in consequences}

    stepped = fact_documents(key, "step-down")
    waved = fact_documents(key, "reset-wave")
    modelled = fact_documents(key, "synergy-npv")
    if not (stepped and waved and modelled):
        return
    breaks = [row for row in consequences if row["kind"] == "series-break"]
    models = [row for row in consequences if row["kind"] == "model-after"]
    assert len(consequences) == 4
    assert [row["doc"] for row in breaks] == sorted({stepped[0], waved[0]})
    assert len({row["period"] for row in breaks}) == 1
    assert len(models) == 2
    assert modelled[0] in {row["doc"] for row in models}


def test_dossier_every_row_anchor_belongs_to_its_document(dossiered, key, known_anchors):
    """Every row names a document of the room and a place inside that document."""
    rows = rows_of(dossiered.text)
    assert rows
    for row in rows:
        assert row.doc in key.documents, row.line
        path = key.documents[row.doc]
        assert parse_anchor(row.anchor).doc == path, row.line
        assert row.anchor in known_anchors.get(path, set()), row.line


def test_dossier_rows_are_all_inside_the_document_set(dossiered, key, mapped):
    """No row names a document outside the matter's own set.

    The set is the map's cluster less the documents the dossier's clause rule takes out, so it
    is a part of the cluster and it holds the seed.
    """
    cluster = set(mapped["matters"][0]["cluster"])
    listed = {doc for _, doc in document_rows(dossiered.text)}
    assert listed <= cluster, sorted(listed - cluster)
    assert set(mapped["matters"][0]["seed"]) <= listed
    for row in rows_of(dossiered.text):
        assert row.doc in listed, row.line


def test_dossier_prints_one_readout_line(dossiered, sample):
    lines = [
        line for line in dossiered.printed.splitlines() if line.startswith(f"dossier {sample}:")
    ]
    assert len(lines) == 2, dossiered.printed
    for line in lines:
        for word in ("documents", "timeline", "names", "figures", "consequences", "seconds"):
            assert word in line


def test_dossier_digest_is_pinned(dossiered, sample):
    """The sha256 of the sample's dossier.md is the one tests/phase4-digests.json holds."""
    digests = json.loads((ROOT / "tests" / "phase4-digests.json").read_text(encoding="utf-8"))
    assert sample in digests, f"{sample} has no pinned dossier digest"
    assert set(digests[sample]) == {"dossier.md"}
    got = hashlib.sha256(dossiered.first.read_bytes()).hexdigest()
    assert got == digests[sample]["dossier.md"]


# ------------------------------------------------- comparisons and lesser matters


@dataclass(frozen=True)
class Triple:
    """One `<doc> | <quote> | <anchor>` part of a comparison row."""

    doc: str
    quote: str
    anchor: str


def stem(word: str) -> str:
    """The word lower cased with one plural or tense ending dropped.

    The ending is dropped only where at least three letters are left, so `days` reads `day`,
    `drafted` reads `draft`, `creation` reads `creat` and `was` is left alone.
    """
    word = word.lower()
    for ending in _ENDINGS:
        if word.endswith(ending) and len(word) - len(ending) >= 3:
            return word[: -len(ending)]
    return word


STOP_WORDS = frozenset(stem(word) for word in STOP_SOURCE.split())


def cut_days(text) -> str:
    """The text with every day it names cut out, so a day is not read as a number or a word."""
    text = straighten(str(text))
    for start, end, _ in reversed(date_matches(text)):
        text = text[:start] + " " + text[end:]
    return text


def words_of(text) -> set[str]:
    """Every word of the text that says something, stemmed, with the days cut out first."""
    return {stem(word) for word in _LETTERS.findall(cut_days(text))} - STOP_WORDS


def numbers_of(text) -> set[str]:
    """Every run of digits the text names, with the days cut out and the thousands marks gone."""
    return set(_DIGITS.findall(cut_days(text).replace(",", "")))


def days_of(text) -> set[str]:
    """Every day the text names, as ISO days."""
    return {day for _, _, day in date_matches(straighten(str(text)))}


def comparison_rows(text: str) -> list[tuple[Triple, ...]]:
    """The Comparisons section read back as rows of triples.

    A row is `- <doc> | <quote> | <anchor>` repeated and joined by ` || `. The quote is the
    only field that may hold a pipe, so the anchor is read off the end of each triple and the
    quote is what is left in the middle.
    """
    rows = []
    for line in sections_of(text).get(COMPARISONS, []):
        triples = []
        for part in line[2:].split(" || "):
            fields = part.split(" | ")
            assert len(fields) >= 3, line
            triples.append(
                Triple(doc=fields[0], quote=" | ".join(fields[1:-1]), anchor=fields[-1])
            )
        assert len(triples) >= 2, line
        rows.append(tuple(triples))
    return rows


def lesser_rows(text: str) -> list[Row]:
    """The Lesser matters section read back as four-field rows, in the order it wrote them."""
    found = []
    for line in sections_of(text).get(LESSER, []):
        fields = line[2:].split(" | ")
        assert len(fields) >= 4, line
        found.append(
            Row(
                section=LESSER,
                first=fields[0],
                doc=fields[1],
                quote=" | ".join(fields[2:-1]),
                anchor=fields[-1],
                line=line,
            )
        )
    return found


@pytest.fixture
def notes_by_doc(run_dir, key):
    """Every note of the run, by document id."""
    return read_notes(run_dir, {path: doc for doc, path in key.documents.items()})


@pytest.fixture
def document_words(run_dir, key):
    """Every word each document holds, stemmed, read from the sections the phase 1 pass wrote."""
    found: dict[str, set[str]] = {}
    ids = {path: doc for doc, path in key.documents.items()}
    for line in (run_dir / "sections.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        doc = ids.get(record["doc"])
        if doc is None:
            continue
        found.setdefault(doc, set()).update(words_of(record["text"]))
    return found


@pytest.fixture
def index_days(run_dir, key):
    """Every day the phase 1 index read, by the document it read it in."""
    found: dict[str, set[str]] = {}
    ids = {path: doc for doc, path in key.documents.items()}
    for line in (run_dir / "index.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record["kind"] != "date":
            continue
        for anchor in record["anchors"]:
            doc = ids.get(anchor.rsplit("#", 1)[0])
            if doc is not None:
                found.setdefault(doc, set()).add(str(record["value"]))
    return found


def comparison_facts(key) -> list:
    """The key's phase 4 comparison facts, in the order the key wrote them."""
    return [fact for fact in key.facts if fact.phase == 4 and fact.kind == "comparison"]


def side_missing(side: str, triples, wanted_words: set[str], index_days) -> set[str]:
    """What of the side the triples fail to carry, empty where they carry all of it.

    The triples are the part of a row that stands for one side. A number and a day have to be
    in the quotes themselves, except that a day the phase 1 index read in one of the triples'
    documents counts as carried, which is how a document whose sections drop its own header
    date still carries it. A word has to be in the quotes, stemmed.
    """
    quoted = " ".join(triple.quote for triple in triples)
    carried_days = days_of(quoted)
    for triple in triples:
        carried_days |= index_days.get(triple.doc, set())
    missing = {f"number {number}" for number in numbers_of(side) - numbers_of(quoted)}
    missing |= {f"day {day}" for day in days_of(side) - carried_days}
    missing |= {f"word {word}" for word in wanted_words - words_of(quoted)}
    return missing


def split_by_content(row, fact, document_words):
    """The row's documents split into the fact's two sides by their words and numbers alone.

    Days are left out on purpose: cut_days takes them out of both the side and the quotes before
    words_of and numbers_of ever see them, so the split is the one a reader would make from the
    room's own words, before a day is asked of either side at all. None where no split of the
    row's documents carries both sides this way.
    """
    first, second = fact.value.split(AGAINST, 1)
    held = set().union(*(document_words.get(doc, set()) for doc in fact.documents))
    wanted = [words_of(side) & held for side in (first, second)]
    docs = sorted({triple.doc for triple in row})
    for mask in range(1, 2 ** len(docs) - 1):
        left = {doc for at, doc in enumerate(docs) if mask >> at & 1}
        parts = (left, set(docs) - left)
        carries = True
        for at, (side, part) in enumerate(zip((first, second), parts)):
            quoted = " ".join(triple.quote for triple in row if triple.doc in part)
            if numbers_of(side) - numbers_of(quoted) or wanted[at] - words_of(quoted):
                carries = False
                break
        if carries:
            return parts
    return None


def split_row(row, fact, document_words, index_days):
    """Reads a row as the two sides of a fact, or returns what each side fails to carry.

    Each side is given the triples of one part of the row, and the two parts name no document
    in common. Every way of splitting the row's documents in two is tried and the first that
    carries both sides wins, so the row is read the way a person reads it: this document says
    one thing, that one says the other.
    """
    first, second = fact.value.split(AGAINST, 1)
    held = set().union(*(document_words.get(doc, set()) for doc in fact.documents))
    wanted = [words_of(side) & held for side in (first, second)]
    docs = sorted({triple.doc for triple in row})
    best = None
    for mask in range(1, 2 ** len(docs) - 1):
        left = {doc for at, doc in enumerate(docs) if mask >> at & 1}
        parts = (left, set(docs) - left)
        found = [
            side_missing(
                side,
                [triple for triple in row if triple.doc in part],
                wanted[at],
                index_days,
            )
            for at, (side, part) in enumerate(zip((first, second), parts))
        ]
        if not found[0] and not found[1]:
            return None
        if best is None or sum(len(one) for one in found) < sum(len(one) for one in best):
            best = found
    return best


# What of a comparison's value no document of the fact holds, gathered for the readout.
_UNREACHED: dict[str, list[str]] = {}


def test_dossier_comparisons_carry_every_planted_comparison(
    dossiered, sample, key, document_words, index_days
):
    """Every comparison the key plants for phase 4 has a row that quotes both of its sides.

    The row names the fact's documents and no others, and its quotes carry both sides of the
    fact's value: each side's numbers, its days and the words its own documents hold.
    """
    facts = comparison_facts(key)
    assert facts, "the key plants no phase 4 comparison"
    rows = comparison_rows(dossiered.text)
    assert rows, "the Comparisons section is empty"
    for fact in facts:
        wanted = set(fact.documents)
        held = set().union(*(document_words.get(doc, set()) for doc in fact.documents))
        for side in fact.value.split(AGAINST, 1):
            for word in sorted(words_of(side) - held):
                _UNREACHED.setdefault(sample, []).append(f"{fact.id}: {word}")
        hits = [row for row in rows if {triple.doc for triple in row} == wanted]
        assert hits, f"{fact.id}: no row naming {sorted(wanted)}"
        reasons = [split_row(row, fact, document_words, index_days) for row in hits]
        assert any(found is None for found in reasons), (
            f"{fact.id}: {fact.value!r} is not carried by its row: "
            f"{[sorted(one) for found in reasons if found for one in found]}"
        )


def test_dossier_deadline_comparison_quotes_its_own_day(dossiered, key, document_words):
    """A comparison that names three or more documents is a deadline against the action taken
    after it, the room's own words split three ways: the window, the day it counts from and the
    action. Where a side of such a fact names a day, the row's own part for that side has to
    quote the day itself, straightened, and not rely on a day the phase 1 index happened to read
    somewhere else in the same document.
    """
    facts = [fact for fact in comparison_facts(key) if len(fact.documents) > 2]
    if not facts:
        pytest.skip("the key plants no comparison of three or more documents")
    rows = comparison_rows(dossiered.text)
    checked = 0
    for fact in facts:
        first, second = fact.value.split(AGAINST, 1)
        wanted_docs = set(fact.documents)
        hits = [row for row in rows if {triple.doc for triple in row} == wanted_docs]
        assert hits, f"{fact.id}: no row naming {sorted(wanted_docs)}"
        for side in (first, second):
            day = days_of(side)
            if not day:
                continue
            checked += 1
            at = 0 if side == first else 1
            carried = False
            for row in hits:
                split = split_by_content(row, fact, document_words)
                if split is None:
                    continue
                quoted = " ".join(triple.quote for triple in row if triple.doc in split[at])
                if day <= days_of(quoted):
                    carried = True
                    break
            assert carried, f"{fact.id}: {side!r} does not quote its own day"
    assert checked >= 1


def test_dossier_comparison_anchors_belong_to_their_documents(dossiered, key, known_anchors):
    """Every comparison row cites a place the phase 1 and 2 artefacts wrote in its own document."""
    rows = comparison_rows(dossiered.text)
    assert rows
    for row in rows:
        for triple in row:
            assert triple.doc in key.documents, triple
            path = key.documents[triple.doc]
            assert parse_anchor(triple.anchor).doc == path, triple
            assert triple.anchor in known_anchors.get(path, set()), triple
            assert triple.quote and triple.quote != EMPTY, triple


def test_dossier_comparisons_are_sorted_and_written_once(dossiered):
    """The rows are sorted by the documents they name and no run of documents is written twice."""
    rows = comparison_rows(dossiered.text)
    keys = [tuple(triple.doc for triple in row) for row in rows]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys))


def test_dossier_draft_against_final_comes_from_the_map_version_pair(dossiered, mapped):
    """The map's version pair has a comparison row of its own."""
    pairs = {tuple(sorted(pair["docs"])) for pair in mapped["matters"][0]["versions"]}
    if not pairs:
        pytest.skip("the map found no version pair in this matter")
    named = {
        tuple(sorted({triple.doc for triple in row}))
        for row in comparison_rows(dossiered.text)
    }
    assert pairs <= named, sorted(pairs - named)


def test_dossier_comparisons_reach_outside_the_seed(dossiered, key, mapped):
    """The comparisons name more documents than the seed, and every one is a room document."""
    named = {triple.doc for row in comparison_rows(dossiered.text) for triple in row}
    assert named <= set(key.documents)
    assert len(named) > len(mapped["matters"][0]["seed"])


def expected_lesser(key, listed, notes_by_doc) -> list[tuple[float, str]]:
    """The documents Lesser matters has to list, in the order it has to list them.

    Every document outside the matter's set whose note carries a flag, ranked by the largest
    money figure its note holds, largest first, and then by id. A document with a flag and no
    money figure follows the ones with money. The set is what the Documents section lists, so a
    document the clause rule took out of the set is a lesser matter and is listed here.
    """
    inside = set(listed)
    found = []
    for doc in sorted(set(key.documents) - inside):
        note = notes_by_doc.get(doc)
        if not note or not note["flags"]:
            continue
        largest = 0.0
        for figure in note["figures"]:
            if "$" not in figure["surface"]:
                continue
            try:
                value, _ = normalise_amount(figure["surface"])
            except ValueError:
                continue
            largest = max(largest, value)
        found.append((largest, doc))
    found.sort(key=lambda pair: (-pair[0], pair[1]))
    return found


def test_dossier_lesser_matters_ranks_the_rest_of_the_room(
    dossiered, key, mapped, notes_by_doc, known_anchors
):
    """Lesser matters lists every flagged document outside the set, ranked by its largest money
    figure and then by id, each with the figure, a quote and an anchor of its own."""
    listed_in_set = {doc for _, doc in document_rows(dossiered.text)}
    wanted = expected_lesser(key, listed_in_set, notes_by_doc)
    assert wanted, "the room holds no flagged document outside the set"
    listed = lesser_rows(dossiered.text)
    assert [doc for _, doc in wanted] == [row.doc for row in listed]
    for (largest, doc), row in zip(wanted, listed):
        path = key.documents[doc]
        assert parse_anchor(row.anchor).doc == path, row.line
        assert row.anchor in known_anchors.get(path, set()), row.line
        assert row.quote and row.quote != EMPTY, row.line
        if largest:
            assert normalise_amount(row.first)[0] == largest, row.line
        else:
            assert row.first == EMPTY, row.line


def test_dossier_every_decoy_sits_in_lesser_matters_and_in_no_comparison(dossiered, key):
    """No decoy is in the first matter's set or in a comparison, and each is a lesser matter."""
    decoys = {decoy.document for decoy in key.decoys}
    if not decoys:
        pytest.skip("the key names no decoy")
    listed = {row.doc for row in lesser_rows(dossiered.text)}
    assert decoys <= listed, sorted(decoys - listed)
    inside = {doc for _, doc in document_rows(dossiered.text)}
    assert not (decoys & inside), sorted(decoys & inside)
    compared = {triple.doc for row in comparison_rows(dossiered.text) for triple in row}
    assert not (decoys & compared), sorted(decoys & compared)


def test_dossier_readout_counts_comparisons_and_lesser_matters(dossiered, sample):
    """The readout line carries the number of comparison rows and of lesser matters it wrote."""
    comparisons = len(comparison_rows(dossiered.text))
    lesser = len(lesser_rows(dossiered.text))
    assert comparisons and lesser
    lines = [
        line for line in dossiered.printed.splitlines() if line.startswith(f"dossier {sample}:")
    ]
    assert lines
    for line in lines:
        assert f"comparisons {comparisons}" in line, line
        assert f"lesser matters {lesser}" in line, line


# ---------------------------------------------------------------- the gate


def test_gate_pin_dossiers_digests_what_is_on_disk(tmp_path, capsys):
    """pin.main --dossiers digests each sample's dossier.md as it sits on disk, copies nothing
    and writes one digest per sample keyed dossier.md."""
    from rlm import pin

    runs_root = tmp_path / "runs"
    wanted = {}
    for sample in ("atlas", "northwind"):
        sample_dir = runs_root / sample
        sample_dir.mkdir(parents=True)
        dossier_bytes = f"# {sample}\n".encode()
        (sample_dir / "dossier.md").write_bytes(dossier_bytes)
        wanted[sample] = {"dossier.md": hashlib.sha256(dossier_bytes).hexdigest()}

    digests_path = tmp_path / "phase4-digests.json"
    code = pin.main(
        [
            str(runs_root),
            "--dossiers",
            "--samples",
            "atlas",
            "northwind",
            "--digests",
            str(digests_path),
        ]
    )
    out = capsys.readouterr().out

    assert code == 0
    assert json.loads(digests_path.read_text(encoding="utf-8")) == wanted
    raw = digests_path.read_text(encoding="utf-8")
    assert raw == json.dumps(wanted, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert "atlas" in out and "northwind" in out
    for sample in wanted:
        assert (runs_root / sample / "dossier.md").exists()


def test_gate_pin_dossiers_refuses_a_sample_with_no_dossier(tmp_path, capsys):
    """pin.main --dossiers refuses, names the sample and writes no digest when a dossier is
    missing."""
    from rlm import pin

    runs_root = tmp_path / "runs"
    (runs_root / "atlas").mkdir(parents=True)
    (runs_root / "atlas" / "dossier.md").write_bytes(b"# atlas\n")
    (runs_root / "northwind").mkdir(parents=True)

    digests_path = tmp_path / "phase4-digests.json"
    code = pin.main(
        [
            str(runs_root),
            "--dossiers",
            "--samples",
            "atlas",
            "northwind",
            "--digests",
            str(digests_path),
        ]
    )
    out = capsys.readouterr().out

    assert code == 1
    assert not digests_path.exists()
    assert "northwind" in out


def test_gate_default_digests_path_follows_the_dossiers_mode():
    """The default digest file is tests/phase4-digests.json for dossiers."""
    from rlm import pin

    assert pin.default_digests_path(dossiers=True).name == "phase4-digests.json"
    assert pin.default_digests_path(dossiers=True).parent == ROOT / "tests"


# ---------------------------------------------------------------- the readout


def readout(terminalreporter):
    """Writes, per sample with a dossier, one line of counts and one line of recall."""
    if not _RUNS:
        return
    terminalreporter.section("phase 4 readout")
    for sample in ENABLED:
        if sample not in _RUNS:
            continue
        run = _RUNS[sample]
        key = load_key(ROOT / "samples" / sample)
        listed = {doc for _, doc in document_rows(run.text)}
        planted = planted_documents(key)
        decoys = {decoy.document for decoy in key.decoys}
        found = planted & listed
        recall = (len(found) / len(planted) * 100) if planted else 0.0
        rows = rows_of(run.text)
        counted = {name: 0 for name in ROW_SECTIONS}
        for row in rows:
            counted[row.section] += 1
        seconds = 0.0
        for line in run.printed.splitlines():
            if line.startswith(f"dossier {sample}:") and "seconds" in line:
                seconds = float(line.rsplit("seconds ", 1)[1])
                break
        terminalreporter.write_line(
            f"phase 4 {sample}: documents {len(listed)}, rows {len(rows)}, "
            f"timeline {counted['Timeline']}, names {counted['Names']}, "
            f"figures {counted['Figures']}, "
            f"consequences {counted['Models blind to it']}, "
            f"comparisons {len(comparison_rows(run.text))}, "
            f"lesser matters {len(lesser_rows(run.text))}, seconds {seconds:.1f}"
        )
        terminalreporter.write_line(
            f"phase 4 {sample}: planted recall {recall:.1f}% "
            f"({len(found)} of {len(planted)}), decoys in the set {len(decoys & listed)}"
        )
        for doc in sorted(planted - listed):
            terminalreporter.write_line(f"phase 4 {sample}: not in the set {doc}")
        for doc in sorted(decoys & listed):
            terminalreporter.write_line(f"phase 4 {sample}: decoy in the set {doc}")
        for note in _UNREACHED.get(sample, []):
            terminalreporter.write_line(
                f"phase 4 {sample}: no document of the fact holds this word, {note}"
            )
