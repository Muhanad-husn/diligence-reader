"""Phase 7 fixture tests for sample 4, the Verizon and Yahoo filings.

The splitter tests run on small in-memory inputs and always run. The fixture tests read
samples/yahoo/documents/ and skip with a reason when it is absent, because the documents are
fetched from sec.gov and are never committed. The determinism test splits the cached raw HTML
twice and compares bytes, so it opens no socket.

The run checks at the end read the artefacts one run of the unchanged chain left under
runs/yahoo/, one phase at a time in order, with the checks the phase 1 to 5 test modules
carry, the way tests/test_phase6.py reads a variant. They skip with a reason where an artefact
is absent. The readout prints one line: recall over the public record key, the dollars the
ledger booked to phase 7 for yahoo, the verifier's state, and the first phase whose check
failed, or holds.
"""

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

import test_phase1
import test_phase2
import test_phase3
import test_phase4
import test_phase5
from rlm.gateway import Ledger
from rlm.grade import COMPARISON_JOIN, measure_recall
from rlm.key import KINDS, load_key
from rlm.yahoo import (
    FILINGS,
    LIMIT,
    Part,
    fold_empty,
    heading_of,
    markdown_of,
    slug,
    split_filing,
    split_headings,
    split_long,
    write_parts,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples" / "yahoo"
DOCUMENTS = SAMPLE / "documents"
RAW = DOCUMENTS / "_raw"
ACCESSION = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")

# The sample's name in the ledger and under runs/, the phase its calls book to, and what the
# acceptance criterion lets one run of the chain cost.
YAHOO = "yahoo"
RUN_DIR = ROOT / "runs" / YAHOO
PHASE = 7
RUN_DOLLARS = 2.0

# The three files whose sha256 the digest file pins.
PINNED_FILES = ("report.md", "verify.json", "grade.json")
DIGESTS_PATH = ROOT / "tests" / "phase7-yahoo-digests.json"

# The documents a stage dropped on the run of 2026-09-09 and the facts the report does not
# carry, each with the phase that owns it and the one sentence that says why, put to the
# founder in the pull request of #125. A known miss is not asserted; it is counted in the
# readout, and a fact every one of whose documents is a known miss is excused with it. The
# fix belongs to the phase named (RULES.md gate 2), never here. The three phase 2 misses of the
# run of 2026-09-09 were fixed by #131: a document over 20,000 characters is noted in pieces.
COVER = (
    "phase 3's, noted and out of the cluster: an 8-K cover page sharing the file number and "
    "the employer number with the other cover pages and nothing with the deal"
)
CUT = "phase 4's, in the cluster and cut from the set: its values are all carried by the set"
KNOWN_MISSES: dict[str, str] = {
    "documents/8-K-2016-07-25-stock-purchase-agreement/03-current-report.md": COVER,
    "documents/8-K-2017-02-21-amendment/03-current-report.md": COVER,
    "documents/8-K-2016-07-25-stock-purchase-agreement/04-item-1-01-entry-into-a-material-definitive-agreement.md": CUT,
    "documents/DEFM14A-2017-04-24/10-summary.md": CUT,
    "documents/8-K-2017-02-21-amendment/17-witnesseth.md": (
        "phase 4's, in the cluster and cut from the set: the reorganization amendment's one "
        "value of its own, the fifty percent share, is a quote and not a number"
    ),
}
KNOWN_FACT_MISSES: dict[str, str] = {
    "commission-file-number": (
        "phase 4's, the 10-K cover page is in the set and the dossier writes no row for a "
        "file number"
    ),
    "employer-identification-number": (
        "phase 4's, the 10-K cover page is in the set and the dossier writes no row for an "
        "employer number"
    ),
    "reorganization-amendment-share": (
        "phase 4's, the note quotes the fifty percent share and the set cut the document"
    ),
}


def documents_or_skip():
    if not DOCUMENTS.is_dir():
        pytest.skip("samples/yahoo/documents/ is absent; run python -m rlm.yahoo fetch samples/yahoo")
    return DOCUMENTS


def raw_or_skip():
    if not RAW.is_dir() or not any(RAW.rglob("*.htm")):
        pytest.skip("samples/yahoo/documents/_raw/ is absent; run python -m rlm.yahoo fetch samples/yahoo")
    return RAW


# The splitter, on inputs written here.


def test_heading_of_reads_an_item_row():
    assert heading_of("**Item  1.01** | **Entry into a Material Definitive Agreement.**") == (
        "Item 1.01 Entry into a Material Definitive Agreement."
    )


def test_heading_of_reads_a_bold_item_line():
    assert heading_of("**Item 1\\. Business **") == "Item 1. Business"


def test_heading_of_reads_an_article_line():
    assert heading_of("ARTICLE I ") == "ARTICLE I"


def test_heading_of_reads_a_capital_section_line():
    assert heading_of("**BACKGROUND OF THE SALE TRANSACTION**") == "BACKGROUND OF THE SALE TRANSACTION"


def test_heading_of_refuses_a_table_row_with_a_page_number():
    assert heading_of("ARTICLE I PURCHASE AND SALE OF SHARES; CLOSING  |    |   | 1 |") is None


def test_heading_of_refuses_a_table_rule_and_ordinary_prose():
    assert heading_of("---|---|---") is None
    assert heading_of("") is None
    assert heading_of("On February 20, 2017, Yahoo and Verizon entered into an Amendment.") is None


def test_heading_of_refuses_a_table_of_contents_line():
    assert heading_of("##### Table of Contents") is None


def test_split_headings_keeps_the_text_before_the_first_heading():
    text = "cover line\n\n**ITEM 1. BUSINESS**\n\nbody one\n\n**ITEM 2. PROPERTIES**\n\nbody two\n"
    parts = split_headings(text)
    assert [part.heading for part in parts] == ["front matter", "ITEM 1. BUSINESS", "ITEM 2. PROPERTIES"]
    assert "cover line" in parts[0].text
    assert "body one" in parts[1].text
    assert parts[1].text.startswith("**ITEM 1. BUSINESS**")


def test_fold_empty_merges_a_heading_that_carries_nothing():
    parts = [
        Part(heading="UNITED STATES", text="**UNITED STATES**\n"),
        Part(heading="FORM 8-K", text="**FORM 8-K**\n\nthe cover of the report\n"),
    ]
    folded = fold_empty(parts)
    assert [part.heading for part in folded] == ["FORM 8-K"]
    assert folded[0].text.startswith("**UNITED STATES**")
    assert "the cover of the report" in folded[0].text


def test_split_long_cuts_at_paragraph_boundaries():
    body = "\n\n".join(f"paragraph {n} " + "x" * 90 for n in range(40))
    part = Part(heading="ITEM 8. FINANCIAL STATEMENTS", text=body)
    pieces = split_long(part, 500)
    assert len(pieces) > 1
    assert all(len(piece.text) <= 500 for piece in pieces)
    assert pieces[0].heading == "ITEM 8. FINANCIAL STATEMENTS"
    assert pieces[1].heading == "ITEM 8. FINANCIAL STATEMENTS (continued 2)"
    assert "".join(piece.text for piece in pieces).replace("\n", "") == body.replace("\n", "")


def test_split_long_cuts_a_paragraph_that_is_itself_too_long():
    part = Part(heading="ONE BLOCK", text="y" * 1200)
    pieces = split_long(part, 500)
    assert all(len(piece.text) <= 500 for piece in pieces)
    assert "".join(piece.text for piece in pieces) == "y" * 1200


def test_split_filing_holds_every_part_under_the_limit():
    text = "cover\n\n**ITEM 1. BUSINESS**\n\n" + "\n\n".join("z" * 300 for _ in range(20))
    parts = split_filing(text, 1000)
    assert parts
    assert all(len(part.text) <= 1000 for part in parts)


def test_slug_is_a_file_name():
    assert slug("Item 1.01 Entry into a Material Definitive Agreement.") == (
        "item-1-01-entry-into-a-material-definitive-agreement"
    )
    assert slug("***") == "section"


def test_markdown_of_drops_tags_and_keeps_the_words():
    text = markdown_of("<html><body><p><b>ITEM 1. BUSINESS</b></p><p>Yahoo is a guide.</p></body></html>")
    assert "ITEM 1. BUSINESS" in text
    assert "Yahoo is a guide." in text
    assert "<p>" not in text


def test_markdown_of_turns_non_breaking_spaces_into_spaces():
    text = markdown_of("<html><body><p>reduced by $350&#160;million.</p></body></html>")
    assert "$350 million." in text
    assert "\xa0" not in text


def test_write_parts_writes_the_same_bytes_twice(tmp_path):
    parts = [Part(heading="ITEM 1. BUSINESS", text="**ITEM 1. BUSINESS**\n\nbody\n")]
    first = write_parts(tmp_path / "a", parts)
    second = write_parts(tmp_path / "b", parts)
    assert [path.name for path in first] == [path.name for path in second]
    assert first[0].read_bytes() == second[0].read_bytes()


# The seven filings, as fetched.


def test_seven_filings_are_declared():
    assert len(FILINGS) == 7
    assert len({filing.accession for filing in FILINGS}) == 7
    assert len({filing.folder for filing in FILINGS}) == 7


def test_readme_names_the_seven_accession_numbers():
    text = (SAMPLE / "README.md").read_text(encoding="utf-8")
    named = set(ACCESSION.findall(text))
    assert {filing.accession for filing in FILINGS} <= named


def test_documents_hold_seven_folders():
    documents = documents_or_skip()
    folders = sorted(path.name for path in documents.iterdir() if path.is_dir() and not path.name.startswith("_"))
    assert folders == sorted(filing.folder for filing in FILINGS)


def test_every_folder_holds_markdown_files():
    documents = documents_or_skip()
    for filing in FILINGS:
        files = sorted((documents / filing.folder).glob("*.md"))
        assert files, filing.folder


def test_no_section_is_over_the_limit():
    documents = documents_or_skip()
    for path in sorted(documents.rglob("*.md")):
        assert len(path.read_text(encoding="utf-8")) <= LIMIT, path.name


def test_a_second_split_of_the_cached_html_writes_the_same_bytes(tmp_path):
    raw = raw_or_skip()
    for filing in FILINGS:
        for source in filing.sources:
            html = (raw / filing.accession / source.file).read_text(encoding="utf-8", errors="replace")
            parts = split_filing(markdown_of(html), LIMIT)
            first = write_parts(tmp_path / "first" / source.file, parts)
            second = write_parts(tmp_path / "second" / source.file, parts)
            assert [path.name for path in first] == [path.name for path in second]
            for one, two in zip(first, second):
                assert one.read_bytes() == two.read_bytes(), f"{filing.folder} {source.file} {one.name}"


# The key and the brief.


@pytest.fixture
def key():
    return load_key(SAMPLE)


def test_key_loads(key):
    assert key.sample == "yahoo"
    assert key.documents
    assert len(key.facts) >= 10


def test_key_has_the_five_kinds(key):
    kinds = {fact.kind for fact in key.facts}
    assert kinds <= KINDS
    assert {"number", "date", "quote", "identifier", "comparison"} <= kinds


def test_key_has_no_rubric_and_no_decoys(key):
    assert key.rubric == ()
    assert key.decoys == ()


def test_key_answer_is_a_reprice_of_350_usd_millions(key):
    assert key.answer.action.startswith("reprice")
    assert (key.answer.number, key.answer.low, key.answer.high) == (350.0, 350.0, 350.0)
    assert key.answer.unit == "USD millions"


def test_key_facts_resolve(key):
    ids = {fact.id for fact in key.facts}
    assert len(ids) == len(key.facts)
    for fact in key.facts:
        assert fact.kind in KINDS, fact.id
        assert fact.phase in range(1, 6), fact.id
        assert fact.documents, fact.id
        for doc in fact.documents:
            assert doc in key.documents, f"{fact.id} names {doc}"


def test_key_documents_are_files(key):
    documents_or_skip()
    for doc_id, rel in key.documents.items():
        assert (SAMPLE / rel).is_file(), f"{doc_id} -> {rel}"


def test_key_required_documents_are_named(key):
    assert key.required_documents
    assert set(key.required_documents) <= set(key.documents)


def test_every_fact_value_is_in_every_document_it_names(key):
    """A comparison fact is two spans joined by " against ", the join rlm.grade splits on, and
    each side has to be in every document the fact names. Every other kind is one span."""
    documents_or_skip()
    for fact in key.facts:
        sides = fact.value.split(COMPARISON_JOIN) if fact.kind == "comparison" else [fact.value]
        assert len(sides) == (2 if fact.kind == "comparison" else 1), fact.id
        for doc in fact.documents:
            text = (SAMPLE / key.documents[doc]).read_text(encoding="utf-8")
            for side in sides:
                assert side in text, f"{fact.id} side {side!r} not in {doc}"


def test_key_is_valid_json_with_sorted_shape():
    data = json.loads((SAMPLE / "key.json").read_text(encoding="utf-8"))
    assert set(data) == {
        "sample",
        "brief",
        "documents",
        "required_documents",
        "decoys",
        "facts",
        "answer",
        "rubric",
        "bar",
    }
    assert data["bar"] == {"perfect": 100, "wrong_under": 40}


def test_brief_is_in_sample_ones_shape(key):
    brief = (SAMPLE / key.brief).read_text(encoding="utf-8")
    assert (SAMPLE / key.brief).is_file()
    atlas = (ROOT / "samples" / "atlas" / "brief.md").read_text(encoding="utf-8")
    assert headings(brief)[1:] == headings(atlas)[1:]
    assert headings(brief)[0].startswith("# ")
    assert "—" not in brief


def headings(text):
    return [normalise(line.strip()) for line in text.splitlines() if line.startswith("#")]


def normalise(line):
    return line.replace("’", "'").replace("—", ",")


# ---------------------------------------------------------------- the output cap knob


def test_notes_output_cap_defaults_to_its_own_constant():
    """--max-output-tokens left off is the phase 2 cap, and 16000 is what the re-note used."""
    from rlm import notes as noter

    assert noter.parse_args(["s", "r"]).max_output_tokens == noter.MAX_OUTPUT_TOKENS == 6000
    assert noter.parse_args(["s", "r", "--max-output-tokens", "16000"]).max_output_tokens == 16000


# ---------------------------------------------------------------- one run of the chain


@pytest.fixture
def sample():
    """Shadows the conftest fixture so sample_dir and run_dir resolve to sample 4's."""
    return YAHOO


def excused(key) -> dict[str, str]:
    """The facts the run may miss, each with the one sentence that says why."""
    lost = set(KNOWN_MISSES)
    found = dict(KNOWN_FACT_MISSES)
    for fact in key.facts:
        documents = set(fact.documents)
        if documents and documents <= lost and fact.id not in found:
            named = ", ".join(sorted(documents))
            found[fact.id] = f"every document it names is a known miss: {named}"
    return found


@pytest.fixture
def records():
    path = RUN_DIR / "sections.jsonl"
    if not path.exists():
        pytest.skip("ingest not run on yahoo yet")
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())


@pytest.fixture
def indexed(records):
    path = RUN_DIR / "index.jsonl"
    if not path.exists():
        pytest.skip("ingest not run on yahoo yet")
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())


@pytest.fixture
def notes():
    notes_dir = RUN_DIR / "notes"
    found = {}
    if notes_dir.is_dir():
        for path in sorted(notes_dir.glob("*.json")):
            raw = path.read_text(encoding="utf-8")
            found[path.name] = (raw, json.loads(raw))
    if not found:
        pytest.skip("notes not run on yahoo yet")
    return found


@pytest.fixture
def sections_by_doc(records):
    by_doc: dict[str, list[dict]] = {}
    for record in records:
        by_doc.setdefault(record["doc"], []).append(record)
    return by_doc


@pytest.fixture
def mapped():
    path = RUN_DIR / "map.json"
    if not path.exists():
        pytest.skip("map not run on yahoo yet")
    return test_phase3.Run(
        first=path, second=path, document=json.loads(path.read_text(encoding="utf-8")), printed=""
    )


@pytest.fixture
def dossiered():
    path = RUN_DIR / "dossier.md"
    if not path.exists():
        pytest.skip("dossier not run on yahoo yet")
    return test_phase4.Run(
        first=path, second=path, text=path.read_text(encoding="utf-8"), printed=""
    )


@pytest.fixture
def report():
    path = RUN_DIR / "report.md"
    dossier = RUN_DIR / "dossier.md"
    digest = RUN_DIR / "digest.md"
    if not (path.exists() and dossier.exists() and digest.exists()):
        pytest.skip("report not written on yahoo yet")
    return test_phase5.Report(
        path=path,
        text=path.read_text(encoding="utf-8"),
        dossier=dossier.read_text(encoding="utf-8"),
        digest=digest.read_text(encoding="utf-8"),
    )


@pytest.fixture
def verified(report):
    path = RUN_DIR / "verify.json"
    if not path.exists():
        pytest.skip("verify.json not written on yahoo yet")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def graded(report):
    path = RUN_DIR / "grade.json"
    if not path.exists():
        pytest.skip("grade.json not written on yahoo yet")
    return json.loads(path.read_text(encoding="utf-8"))


known_anchors = test_phase4.known_anchors
index_surfaces = test_phase4.index_surfaces

_RAN: set[int] = set()
_HELD: set[int] = set()
_MISSED: list[str] = []


def first_failure() -> int | None:
    """The lowest phase whose check ran and did not reach its end."""
    for phase in range(1, 6):
        if phase in _RAN and phase not in _HELD:
            return phase
    return None


def test_phase_1_holds_on_yahoo(sample_dir, key, records, indexed):
    """Every anchor resolves in its own file and every phase 1 fact is in the room."""
    _RAN.add(1)
    ingested = test_phase1.Run(
        first=RUN_DIR / "sections.jsonl",
        second=RUN_DIR / "sections.jsonl",
        coverage=None,
        records=tuple(records),
        printed="",
    )
    test_phase1.test_sections_anchors_resolve_in_their_files(ingested, sample_dir)
    test_phase1.test_sections_carry_every_quote_and_identifier_fact(ingested, key)
    sectioned = {record["doc"] for record in records}
    texts: dict[str, list[str]] = {}
    for record in records:
        texts.setdefault(record["doc"], []).append(test_phase1.flatten(record["text"]))
    missed = [
        fact.id
        for fact in key.facts
        if fact.phase == 1
        and not test_phase1._fact_resolved(fact, key, sectioned, texts, indexed)
    ]
    assert not missed, f"phase 1 does not resolve {missed}"
    _HELD.add(1)


def test_phase_2_holds_on_yahoo(key, notes, sections_by_doc):
    """Every note is well shaped, every quote verifies, and every phase 2 fact is quoted."""
    _RAN.add(2)
    known = excused(key)
    kept = replace(key, facts=tuple(fact for fact in key.facts if fact.id not in known))
    test_phase2.assert_notes_well_shaped(notes, key)
    test_phase2.assert_notes_quotes_verified(notes, sections_by_doc)
    test_phase2.test_one_document_carries_its_planted_quotes(notes, kept)
    test_phase2.test_seed_document_flags_name_every_planted_identifier(
        notes, key, RUN_DIR, YAHOO
    )
    _HELD.add(2)


def test_phase_3_holds_on_yahoo(key, mapped):
    """The first matter's cluster holds every planted document but for a known miss, and the
    required documents are held across the matters the map returns."""
    _RAN.add(3)
    matters = mapped.document["matters"]
    assert matters
    first = set(matters[0]["cluster"])
    for doc in sorted(test_phase3.planted_documents(key) - first):
        assert doc in KNOWN_MISSES, f"{doc} is out of the first matter and is no known miss"
        _MISSED.append(f"{doc}: known miss, {KNOWN_MISSES[doc]}")
    across: set[str] = set()
    for matter in matters:
        across |= set(matter["cluster"])
    required = set(key.required_documents) - set(KNOWN_MISSES)
    assert required <= across, sorted(required - across)
    _HELD.add(3)


def test_phase_4_holds_on_yahoo(key, dossiered, known_anchors, index_surfaces):
    """The first matter's document set holds the planted documents but for a known miss, and
    every phase 1 and 2 fact has a row with an anchor of its own document."""
    _RAN.add(4)
    listed = {doc for _, doc in test_phase4.document_rows(dossiered.text)}
    planted = test_phase3.planted_documents(key) - set(KNOWN_MISSES)
    assert planted <= listed, sorted(planted - listed)
    known = excused(key)
    kept = replace(key, facts=tuple(fact for fact in key.facts if fact.id not in known))
    test_phase4.test_dossier_carries_every_phase_1_and_2_fact(
        dossiered, kept, known_anchors, index_surfaces
    )
    test_phase4.test_dossier_every_row_anchor_belongs_to_its_document(
        dossiered, key, known_anchors
    )
    _HELD.add(4)


def test_phase_5_holds_on_yahoo(key, report, verified, graded):
    """Recall is 100 but for a known miss, the verifier passes, and the grade holds recall over
    the key and no rubric, because the key has none. Every known miss is counted in the
    readout, and a miss that comes right is taken off the list."""
    _RAN.add(5)
    recall, _, missed = measure_recall(key, report.text)
    known = excused(key)
    for fact_id in sorted(missed):
        assert fact_id in known, f"{fact_id} is missed and is no known miss, recall {recall}"
        _MISSED.append(f"{fact_id}: known miss, {known[fact_id]}")
    assert verified["passes"] is True, f"last round: {verified['rounds'][-1][:5]}"
    assert graded["recall"] == recall
    assert graded["rubric"] == []
    assert graded["score"] == recall
    _HELD.add(5)


def test_the_run_books_under_two_dollars_to_phase_7():
    """The ledger's phase 7 rows for yahoo sum under the acceptance criterion's $2."""
    if not (RUN_DIR / "grade.json").exists():
        pytest.skip("the chain has not run on yahoo yet")
    rows = Ledger(ROOT / "LEDGER.md").rows()
    booked = [row for row in rows if row["phase"] == str(PHASE) and row["sample"] == YAHOO]
    assert booked, "no phase 7 row for yahoo"
    assert sum(row["dollars"] for row in booked) < RUN_DOLLARS


def test_the_three_files_carry_the_pinned_digests():
    """tests/phase7-yahoo-digests.json holds the sha256 of report.md, verify.json and grade.json."""
    if not (RUN_DIR / "grade.json").exists():
        pytest.skip("the chain has not run on yahoo yet")
    assert DIGESTS_PATH.exists(), "no yahoo digests pinned yet"
    digests = json.loads(DIGESTS_PATH.read_text(encoding="utf-8"))
    assert set(digests) == {YAHOO}
    assert set(digests[YAHOO]) == set(PINNED_FILES)
    for name in PINNED_FILES:
        got = hashlib.sha256((RUN_DIR / name).read_bytes()).hexdigest()
        assert got == digests[YAHOO][name], name


# ---------------------------------------------------------------- the readout


def readout(terminalreporter):
    """Writes one line: recall, the phase 7 dollars, the verifier's state, and where it stands."""
    if not _RAN:
        return
    terminalreporter.section("phase 7 yahoo readout")
    recall = "not written"
    report_path = RUN_DIR / "report.md"
    if report_path.exists():
        score, _, _ = measure_recall(load_key(SAMPLE), report_path.read_text(encoding="utf-8"))
        recall = f"{score:.1f}"
    verify = "not written"
    verify_path = RUN_DIR / "verify.json"
    if verify_path.exists():
        record = json.loads(verify_path.read_text(encoding="utf-8"))
        verify = "passes" if record["passes"] else f"fails, {len(record['rounds'][-1])} failures"
    rows = Ledger(ROOT / "LEDGER.md").rows()
    dollars = sum(
        row["dollars"] for row in rows if row["phase"] == str(PHASE) and row["sample"] == YAHOO
    )
    failed = first_failure()
    state = f"phase {failed} fails" if failed else "holds"
    terminalreporter.write_line(
        f"phase 7 {YAHOO}: recall {recall}, ${dollars:.4f}, verify {verify}, {state}"
    )
    for line in _MISSED:
        terminalreporter.write_line(f"phase 7 {YAHOO}: {line}")
