"""Phase 4 dossier tests. The dossier reads a sample's map, index, sections and notes and
writes dossier.md: the matter's document set, its timeline, the names the notes gave it, its
figures and the models blind to it. These tests run the dossier twice, the second time into a
temporary directory, and check that the two files are byte identical, that the first matter's
document set holds every document of the key's matter-documents fact and none of its decoys,
that every planted document is ranked above every decoy both in the map and in the dossier's
own list, that every phase 1 and phase 2 fact of the key has a row carrying its value with an
anchor that parses, belongs to one of the fact's documents and is one of the anchors the phase
1 and 2 artefacts wrote, that the names section carries the workstream, the programme and the
ticket, that the models section carries the map's consequences, and that the run prints one
readout line.

Only sample 1 is enabled in this slice. Samples 2 and 3 are widened in slice 03, and a sample
whose dossier inputs are absent is skipped."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

from rlm.dossier import main
from rlm.key import load_key
from rlm.notes import straighten
from rlm.sections import parse_anchor

ROOT = Path(__file__).resolve().parents[1]

# The samples this slice runs the dossier on. Slice 03 widens this to the three gate samples.
ENABLED = ("atlas",)
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


def test_dossier_ranks_every_planted_document_above_every_decoy(dossiered, key, mapped):
    """No decoy outranks a planted document, in the map's ranking or in the dossier's list."""
    planted = planted_documents(key)
    decoys = {decoy.document for decoy in key.decoys}
    ranked = {row["doc"]: at for at, row in enumerate(mapped["matters"][0]["ranked"])}
    worst = max(ranked[doc] for doc in planted)
    best = min((ranked[doc] for doc in decoys), default=len(ranked))
    assert worst < best, sorted(doc for doc in decoys if ranked[doc] < worst)

    listed = document_rows(dossiered.text)
    assert [rank for rank, _ in listed] == sorted(rank for rank, _ in listed)
    places = {doc: rank for rank, doc in listed}
    assert max(places[doc] for doc in planted) < min(
        (places[doc] for doc in decoys if doc in places), default=len(listed) + 1
    )


def test_dossier_carries_every_phase_1_and_2_fact(dossiered, key, known_anchors):
    """Every planted fact of phase 1 and phase 2 has a row that carries it.

    A row carries a fact when its date or figure field, or its quote, holds the fact's value
    after straightening, and its anchor parses, belongs to one of the fact's documents and is
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
        hits = [
            row
            for row in rows
            if row.doc in fact.documents
            and (wanted in straighten(row.first) or wanted in straighten(row.quote))
        ]
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
    """No row names a document outside the matter's own set."""
    listed = {doc for _, doc in document_rows(dossiered.text)}
    assert listed == set(mapped["matters"][0]["cluster"])
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
            f"consequences {counted['Models blind to it']}, seconds {seconds:.1f}"
        )
        terminalreporter.write_line(
            f"phase 4 {sample}: planted recall {recall:.1f}% "
            f"({len(found)} of {len(planted)}), decoys in the set {len(decoys & listed)}"
        )
        for doc in sorted(planted - listed):
            terminalreporter.write_line(f"phase 4 {sample}: not in the set {doc}")
        for doc in sorted(decoys & listed):
            terminalreporter.write_line(f"phase 4 {sample}: decoy in the set {doc}")
