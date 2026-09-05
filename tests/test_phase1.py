"""Phase 1 sections tests. Ingest reads a sample's data room and writes sections.jsonl. These
tests run ingest twice into two run directories and check that the two files are byte
identical, that every document the key names has a section, that every anchor parses and
resolves to a page, line, cell or row that exists in the file, that every planted quote and
identifier is in the text of a section of one of its own documents, and that the run prints one
coverage line. A sample whose ingest is not enabled yet is skipped."""

import csv
import email
import email.policy
import hashlib
import json
import mailbox
import re
from dataclasses import dataclass
from pathlib import Path

import openpyxl
import pdfplumber
import pytest
from pdftext.extraction import paginated_plain_text_output

from rlm.amounts import normalise_amount, normalise_date
from rlm.ingest import Coverage, ingest, main
from rlm.key import load_key
from rlm.sections import KINDS, parse_anchor

ROOT = Path(__file__).resolve().parents[1]

# The samples ingest reads today. Slice 04 empties this skip.
ENABLED = ("atlas",)
SKIP_REASON = "ingest not enabled for this sample yet"

# The document counts sample 1 carries, by extension, fixed by construction. 100 documents,
# the key's own count; data_room/README.md is the brief, not a document, and is not among them.
ATLAS_EXTENSIONS = {".pdf": 61, ".xlsx": 29, ".csv": 7, ".txt": 1, ".eml": 1, ".mbox": 1}

_WHITESPACE = re.compile(r"\s+")
_BLANK_LINE = re.compile(r"\n\s*\n")


def flatten(text):
    """Collapses runs of whitespace to one space and strips the ends."""
    return _WHITESPACE.sub(" ", text).strip()


@dataclass(frozen=True)
class Run:
    """One pair of ingest runs on a sample: the two files, the records and what was printed."""

    first: Path
    second: Path
    coverage: Coverage
    records: tuple[dict, ...]
    printed: str


_RUNS: dict[str, Run] = {}


@pytest.fixture
def ingested(sample, sample_dir, run_dir, capsys):
    """Runs ingest twice on the sample and returns both files, the records and the output.

    The pair of runs is done once per sample and reused, because ingest reads 61 PDFs twice
    with two engines and every test in this file needs the same artefact.
    """
    if sample not in ENABLED:
        pytest.skip(SKIP_REASON)
    if sample not in _RUNS:
        second_dir = run_dir.with_name(run_dir.name + "-b")
        coverage = ingest(sample_dir, run_dir)
        assert main([str(sample_dir), str(second_dir)]) == 0
        printed = capsys.readouterr().out
        first = run_dir / "sections.jsonl"
        records = tuple(
            json.loads(line) for line in first.read_text(encoding="utf-8").splitlines()
        )
        _RUNS[sample] = Run(
            first=first,
            second=second_dir / "sections.jsonl",
            coverage=coverage,
            records=records,
            printed=printed,
        )
    return _RUNS[sample]


@pytest.fixture
def key(sample_dir):
    return load_key(sample_dir)


@pytest.fixture
def indexed(ingested):
    """The index records of the sample's first run, read back from index.jsonl."""
    path = ingested.first.with_name("index.jsonl")
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())


def test_sections_anchor_round_trip():
    """Every anchor this phase writes parses back to the doc and the place it names."""
    doc = "data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf"

    page_line = parse_anchor(f"{doc}#p2l14")
    assert (page_line.doc, page_line.kind, page_line.page, page_line.line) == (doc, "page-line", 2, 14)

    table_row = parse_anchor(f"{doc}#p2t1r3")
    assert (table_row.kind, table_row.page, table_row.table, table_row.row) == ("page-table-row", 2, 1, 3)

    line = parse_anchor("data_room/a.txt#l14")
    assert (line.doc, line.kind, line.line) == ("data_room/a.txt", "line", 14)

    message = parse_anchor("data_room/a.mbox#m3l14")
    assert (message.kind, message.message, message.line) == ("message-line", 3, 14)

    cell = parse_anchor("data_room/a.xlsx#Key Rotation Exceptions!B14")
    assert (cell.kind, cell.sheet, cell.column, cell.row) == ("sheet-cell", "Key Rotation Exceptions", "B", 14)

    row = parse_anchor("data_room/a.csv#r14")
    assert (row.kind, row.row) == ("row", 14)

    for bad in ["no-hash", "data_room/a.txt#", "data_room/a.txt#l", "data_room/a.txt#page2"]:
        with pytest.raises(ValueError):
            parse_anchor(bad)


def test_sections_two_runs_are_byte_identical(ingested):
    """Two runs of the same sample write the same bytes, which is what makes ingest pinnable."""
    assert ingested.first.read_bytes() == ingested.second.read_bytes()


def test_sections_records_are_sorted_and_well_shaped(ingested):
    """Records are sorted by doc then ordinal, keys are sorted, and each carries the shape."""
    text_keys = {"anchor", "doc", "heading", "kind", "ordinal", "text", "warning"}
    order = [(record["doc"], record["ordinal"]) for record in ingested.records]
    assert order == sorted(order)

    lines = ingested.first.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(ingested.records)
    for line, record in zip(lines, ingested.records):
        assert line == json.dumps(record, sort_keys=True, ensure_ascii=False)
        assert line == line.rstrip()
        assert record["kind"] in KINDS
        if record["kind"] == "row":
            assert set(record) == text_keys | {"cells"}
            assert record["cells"]
            for cell in record["cells"]:
                assert set(cell) == {"ref", "value"}
        else:
            assert set(record) == text_keys
        assert record["text"]
        assert record["heading"] is None or isinstance(record["heading"], str)
        assert record["warning"] is None or isinstance(record["warning"], str)

    by_doc: dict[str, list[int]] = {}
    for record in ingested.records:
        by_doc.setdefault(record["doc"], []).append(record["ordinal"])
    for doc, ordinals in by_doc.items():
        assert ordinals == list(range(1, len(ordinals) + 1)), doc


def test_sections_cover_every_key_document(ingested, key, sample):
    """Every document the key names has at least one section, and every format is read."""
    documented = {record["doc"] for record in ingested.records}
    for doc_id, relative in key.documents.items():
        assert relative in documented, f"{doc_id} -> {relative}"
    if sample == "atlas":
        counted: dict[str, int] = {}
        for doc in documented:
            suffix = Path(doc).suffix
            counted[suffix] = counted.get(suffix, 0) + 1
        assert counted == ATLAS_EXTENSIONS


def test_sections_read_only_the_documents_the_key_names(ingested, key):
    """Every sectioned document is one the key names, so a brief, a key or a fixture is never read."""
    named = set(key.documents.values())
    assert {record["doc"] for record in ingested.records} <= named


def test_sections_anchors_resolve_in_their_files(ingested, sample_dir):
    """Every anchor parses and names a page, line, cell or row the file really has."""
    resolver = Resolver(sample_dir)
    for record in ingested.records:
        anchor = parse_anchor(record["anchor"])
        assert anchor.doc == record["doc"]
        assert resolver.resolves(anchor), record["anchor"]


def test_sections_carry_every_quote_and_identifier_fact(ingested, key):
    """Every planted quote and identifier is in the text of a section of one of its documents."""
    texts: dict[str, list[str]] = {}
    for record in ingested.records:
        texts.setdefault(record["doc"], []).append(flatten(record["text"]))
    for fact in key.facts:
        if fact.kind not in ("quote", "identifier"):
            continue
        wanted = flatten(fact.value)
        assert any(
            wanted in text
            for doc_id in fact.documents
            for text in texts.get(key.documents[doc_id], [])
        ), fact.id


def test_sections_run_prints_one_coverage_line(ingested, key):
    """The run prints one line carrying documents read, sections written, disagreements, empty."""
    lines = [line for line in ingested.printed.splitlines() if line.strip()]
    assert len(lines) == 1, lines
    assert lines[0] == (
        f"documents read: {ingested.coverage.documents}, "
        f"sections written: {ingested.coverage.sections}, "
        f"engine disagreements: {ingested.coverage.disagreements}, "
        f"empty extractions: {ingested.coverage.empty}"
    )
    assert ingested.coverage.sections == len(ingested.records)
    assert ingested.coverage.documents >= len(key.documents)


def test_index_normalise_amount_reads_the_surface():
    """The normaliser maps a surface to a number and, where the surface says one, a unit."""
    assert normalise_amount("$12,400,000") == (12400000.0, "USD")
    assert normalise_amount("$12.4m") == (12400000.0, "USD")
    assert normalise_amount("$240m") == (240000000.0, "USD")
    assert normalise_amount("$12m") == (12000000.0, "USD")
    assert normalise_amount("912.8m") == (912800000.0, None)
    assert normalise_amount("912,800,000 records") == (912800000.0, "records")
    assert normalise_amount("1.1bn") == (1100000000.0, None)
    assert normalise_amount("30.1%") == (30.1, "percent")
    assert normalise_amount("45-day") == (45.0, "days")
    assert normalise_amount("45 days") == (45.0, "days")
    assert normalise_amount("36 months") == (36.0, "months")
    assert normalise_amount("36-month") == (36.0, "months")
    assert normalise_amount("615") == (615.0, None)
    assert normalise_amount("24.8") == (24.8, None)
    # Read from the parenthesised digits, not from an English number table.
    assert normalise_amount("twenty-four (24) months") == (24.0, "months")
    for bad in ["", "TB", "no digits here"]:
        with pytest.raises(ValueError):
            normalise_amount(bad)


def test_index_normalise_date_reads_the_surface():
    """The normaliser maps every date surface this phase meets to one ISO string."""
    assert normalise_date("2025-10-18") == "2025-10-18"
    assert normalise_date("18 October 2025") == "2025-10-18"
    assert normalise_date("11 Dec 2025") == "2025-12-11"
    assert normalise_date("31 July 2021") == "2021-07-31"
    assert normalise_date("2025-10-18T02:14:07Z") == "2025-10-18"
    assert normalise_date("[2025-10-23 09:10 UTC]") == "2025-10-23"
    assert normalise_date("October 18, 2025") == "2025-10-18"
    for bad in ["", "October", "2025", "2025-13-40", "18 Octember 2025"]:
        with pytest.raises(ValueError):
            normalise_date(bad)


def test_index_two_runs_are_byte_identical(ingested):
    """Two runs of the same sample write the same index bytes."""
    first = ingested.first.with_name("index.jsonl")
    second = ingested.second.with_name("index.jsonl")
    assert first.read_bytes() == second.read_bytes()


def test_index_records_are_sorted_and_well_shaped(ingested, indexed):
    """Every record carries the seven keys, a kind, a unit from the vocabulary, and its lists."""
    kinds = {"date", "amount", "name", "identifier", "status", "version-pair", "series"}
    units = {"USD", "percent", "records", "months", "days", "count"}
    lines = ingested.first.with_name("index.jsonl").read_text(encoding="utf-8").splitlines()
    assert indexed
    assert len(lines) == len(indexed)
    for line, record in zip(lines, indexed):
        assert line == json.dumps(record, sort_keys=True, ensure_ascii=False)
        assert line == line.rstrip()
        assert set(record) == {"anchors", "context", "docs", "kind", "surface", "unit", "value"}
        assert record["kind"] in kinds
        assert record["unit"] is None or record["unit"] in units
        assert record["surface"] and isinstance(record["surface"], str)
        assert isinstance(record["context"], str)
        assert record["docs"] == sorted(set(record["docs"])) != []
        assert record["anchors"] == sorted(set(record["anchors"])) != []
    order = [
        (record["kind"], json.dumps(record["value"], sort_keys=True), record["anchors"][0])
        for record in indexed
    ]
    assert order == sorted(order)


def test_index_anchors_resolve_to_sections(ingested, indexed):
    """Every anchor and every doc of the index is one slice 01 wrote."""
    anchors = {record["anchor"] for record in ingested.records}
    docs = {record["doc"] for record in ingested.records}
    for record in indexed:
        for anchor in record["anchors"]:
            assert anchor in anchors, anchor
        for doc in record["docs"]:
            assert doc in docs, doc
        assert {anchor.rpartition("#")[0] for anchor in record["anchors"]} == set(record["docs"])


def test_index_carries_every_phase_1_fact(indexed, key, sample):
    """Every phase 1 fact is in the index on a normalised value against one of its documents.

    The key's value goes through the same normaliser as the document surface, so no rule is
    written against a key string. An identifier fact is satisfied by a name as well.
    """
    kinds = {"date": ("date",), "number": ("amount",), "identifier": ("identifier", "name")}
    facts = [fact for fact in key.facts if fact.phase == 1]
    if sample == "atlas":
        assert len(facts) == 29
    assert facts
    for fact in facts:
        assert fact.kind in kinds, fact.id
        wanted_docs = {key.documents[doc_id] for doc_id in fact.documents}
        unit = None
        if fact.kind == "date":
            value = normalise_date(fact.value)
        elif fact.kind == "number":
            value, unit = normalise_amount(fact.value)
        else:
            value = fact.value
        assert any(
            record["kind"] in kinds[fact.kind]
            and record["value"] == value
            and (unit is None or record["unit"] == unit)
            and wanted_docs.intersection(record["docs"])
            for record in indexed
        ), fact.id


def test_index_credits_an_established_name_where_it_opens_a_line(indexed, sample):
    """A word that is a name elsewhere is a name at the start of a line or after a label too."""
    if sample != "atlas":
        pytest.skip("the name places of this sample are not pinned here")
    opening = {
        "data_room/00_Index_and_Process/Data_Room_Index.xlsx",
        "data_room/02_Financials_and_Tax/Contingency_Reserve_Memo.pdf",
    }
    names = [record for record in indexed if record["kind"] == "name" and record["value"] == "VistaPort"]
    assert len(names) == 1
    assert opening <= set(names[0]["docs"])


def test_index_amount_in_a_workbook_cell_takes_its_unit_from_the_header(indexed, sample):
    """A bare number in a workbook cell carries the unit its sheet's own header names."""
    headed = {
        "atlas": (
            912800000.0,
            "records",
            "data_room/05_Security_IT_and_Infrastructure/Backup_Retention_Inventory.xlsx",
        ),
    }
    if sample not in headed:
        pytest.skip("no workbook header case recorded for this sample yet")
    value, unit, doc = headed[sample]
    assert any(
        record["kind"] == "amount"
        and record["value"] == value
        and record["unit"] == unit
        and doc in record["docs"]
        and any(
            anchor.startswith(doc + "#") and "!" in anchor.rpartition("#")[2]
            for anchor in record["anchors"]
        )
        for record in indexed
    )


# The status words sample 1's own documents carry, from the key's account of the room. A
# document may carry more than the ones named here; these are the ones that must be there.
ATLAS_STATUS = {
    "data_room/05_Security_IT_and_Infrastructure/Network_Quality_Ticket_NQ17_Redacted.txt": {"redacted"},
    "data_room/06_Legal_Regulatory_and_Compliance/Outside_Counsel_Privacy_Risk_Memo_Redacted.pdf": {
        "redacted",
        "privileged",
    },
    "data_room/02_Financials_and_Tax/Draft_Financials_FY2025.pdf": {"draft"},
    "data_room/02_Financials_and_Tax/Audited_Financials_FY2023.pdf": {"final"},
    "data_room/02_Financials_and_Tax/Audited_Financials_FY2024.pdf": {"final"},
}

STATUS_VALUES = {"draft", "final", "redacted", "privileged", "confidential"}

AURORA_DRAFT = "data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf"
AURORA_FINAL = "data_room/05_Security_IT_and_Infrastructure/Aurora_Executive_Summary_Final.pdf"
DRAFT_FINANCIALS = "data_room/02_Financials_and_Tax/Draft_Financials_FY2025.pdf"
FINANCE_PACKS = [
    f"data_room/02_Financials_and_Tax/Monthly_Finance_Pack_2025_{month}.pdf"
    for month in ("09", "10", "11", "12")
]
VISTAMAIL = "data_room/04_Product_Data_and_Technology/VistaMail_KPI_Weekly_Q4_2025.csv"
USER_METRICS = "data_room/04_Product_Data_and_Technology/User_Metrics_Dashboard_Q3_Q4_2025.xlsx"

RECORD_KEYS = {"anchors", "context", "docs", "kind", "surface", "unit", "value"}


def records_of(indexed, kind):
    """The index records of one kind, in the order the file holds them."""
    return [record for record in indexed if record["kind"] == kind]


def test_status_records_are_well_shaped(indexed, ingested):
    """Every record carries the seven keys, and every anchor is a section this run wrote."""
    anchors = {record["anchor"] for record in ingested.records}
    for record in indexed:
        assert set(record) == RECORD_KEYS, record
        assert isinstance(record["docs"], list) and record["docs"]
        assert isinstance(record["anchors"], list) and record["anchors"]
        for anchor in record["anchors"]:
            assert anchor in anchors, anchor
        for doc in record["docs"]:
            assert any(anchor.startswith(doc + "#") for anchor in anchors), doc

    for record in records_of(indexed, "status"):
        assert record["value"] in STATUS_VALUES
        assert record["unit"] is None
        assert len(record["docs"]) == 1
        assert len(record["anchors"]) == 1
        assert record["anchors"][0].startswith(record["docs"][0] + "#")
        assert record["surface"]
        assert record["surface"].lower() in record["context"].lower()


def test_status_words_name_the_documents_that_carry_them(indexed, sample):
    """The redacted ticket, the counsel memo, the draft year and the two audited years."""
    if sample != "atlas":
        pytest.skip("the status words of this sample are not pinned here")
    carried = {}
    for record in records_of(indexed, "status"):
        carried.setdefault(record["docs"][0], set()).add(record["value"])
    for doc, wanted in ATLAS_STATUS.items():
        assert wanted <= carried.get(doc, set()), doc


def test_versions_pair_the_aurora_draft_with_its_final(indexed, sample):
    """The one version pair in the room is AURORA, ordered draft 2025-11-12 then final 2025-11-20."""
    if sample != "atlas":
        pytest.skip("the version pairs of this sample are not pinned here")
    pairs = records_of(indexed, "version-pair")
    assert len(pairs) == 1, [pair["value"] for pair in pairs]
    pair = pairs[0]
    assert pair["surface"] == "AURORA"
    assert pair["unit"] is None
    assert pair["value"] == {
        "draft": AURORA_DRAFT,
        "draft_date": "2025-11-12",
        "final": AURORA_FINAL,
        "final_date": "2025-11-20",
    }
    assert pair["docs"] == sorted([AURORA_DRAFT, AURORA_FINAL])
    assert sorted(anchor.split("#")[0] for anchor in pair["anchors"]) == sorted([AURORA_DRAFT, AURORA_FINAL])


def test_versions_leave_a_draft_with_no_final_unpaired(indexed, sample):
    """Draft_Financials_FY2025 has no final in the room, so it is in no pair."""
    if sample != "atlas":
        pytest.skip("the version pairs of this sample are not pinned here")
    for pair in records_of(indexed, "version-pair"):
        assert DRAFT_FINANCIALS not in pair["docs"]


def test_versions_put_no_document_in_two_pairs(indexed):
    """A document is in at most one version pair, whatever the sample."""
    seen = []
    for pair in records_of(indexed, "version-pair"):
        assert len(pair["docs"]) == 2
        seen.extend(pair["docs"])
    assert len(seen) == len(set(seen)), seen


def test_series_hold_the_four_monthly_finance_packs(indexed, sample):
    """The four monthly finance packs are one document series with step month, in order."""
    if sample != "atlas":
        pytest.skip("the series of this sample are not pinned here")
    packs = [
        record
        for record in records_of(indexed, "series")
        if record["value"]["form"] == "documents" and record["docs"] == FINANCE_PACKS
    ]
    assert len(packs) == 1
    packs = packs[0]
    assert packs["value"]["step"] == "month"
    assert packs["value"]["members"] == FINANCE_PACKS
    assert [anchor.split("#")[0] for anchor in packs["anchors"]] == FINANCE_PACKS


def test_series_hold_the_weekly_rows_of_the_csv_and_the_workbook(indexed, sample):
    """The VistaMail CSV and the user metrics workbook are row series with step week."""
    if sample != "atlas":
        pytest.skip("the series of this sample are not pinned here")
    rows = {}
    for record in records_of(indexed, "series"):
        if record["value"]["form"] == "rows":
            rows.setdefault(record["docs"][0], []).append(record)

    assert len(rows[VISTAMAIL]) == 1
    vistamail = rows[VISTAMAIL][0]
    assert vistamail["surface"] == "week_start"
    assert vistamail["value"]["step"] == "week"
    assert vistamail["anchors"] == [f"{VISTAMAIL}#r1"]
    assert vistamail["value"]["members"][:3] == [
        f"{VISTAMAIL}#r2",
        f"{VISTAMAIL}#r3",
        f"{VISTAMAIL}#r4",
    ]

    assert len(rows[USER_METRICS]) == 1
    metrics = rows[USER_METRICS][0]
    assert metrics["surface"] == "Week commencing"
    assert metrics["value"]["step"] == "week"
    assert metrics["anchors"] == [f"{USER_METRICS}#Weekly MAU!A1"]
    assert metrics["value"]["members"][:3] == [
        f"{USER_METRICS}#Weekly MAU!A2",
        f"{USER_METRICS}#Weekly MAU!A3",
        f"{USER_METRICS}#Weekly MAU!A4",
    ]


def test_series_members_are_ordered_and_resolve(indexed, ingested):
    """A series has two or more members, in order, and every member is a real place."""
    anchors = {record["anchor"] for record in ingested.records}
    docs = {record["doc"] for record in ingested.records}
    for record in records_of(indexed, "series"):
        value = record["value"]
        assert value["form"] in ("documents", "rows")
        assert value["step"] in ("week", "month", "quarter")
        assert len(value["members"]) >= 2
        assert len(set(value["members"])) == len(value["members"])
        for member in value["members"]:
            assert member in (docs if value["form"] == "documents" else anchors), member


def test_series_and_sections_digests_are_pinned(ingested, sample):
    """The sha256 of the sample's two artefacts is the one tests/phase1-digests.json holds."""
    digests = json.loads((ROOT / "tests" / "phase1-digests.json").read_text(encoding="utf-8"))
    if sample not in digests:
        pytest.skip("no digest pinned for this sample yet")
    for name, wanted in sorted(digests[sample].items()):
        got = hashlib.sha256(ingested.first.with_name(name).read_bytes()).hexdigest()
        assert got == wanted, name


class Resolver:
    """Reads a sample's files with the parsing libraries and says whether an anchor exists.

    This is the independent side of the anchor test. It reads the files itself rather than
    asking ingest where a section came from.
    """

    def __init__(self, sample_dir: Path):
        self.sample_dir = sample_dir
        self._pdf_lines: dict[str, list[list[str]]] = {}
        self._pdf_tables: dict[str, list[list[int]]] = {}
        self._sheets: dict[str, dict[str, set[str]]] = {}
        self._rows: dict[str, int] = {}
        self._lines: dict[str, int] = {}
        self._messages: dict[str, list[int]] = {}

    def path(self, doc: str) -> Path:
        return self.sample_dir / doc

    def resolves(self, anchor) -> bool:
        if anchor.kind == "page-line":
            pages = self._pdf_page_lines(anchor.doc)
            return 1 <= anchor.page <= len(pages) and 1 <= anchor.line <= len(pages[anchor.page - 1])
        if anchor.kind == "page-table-row":
            pages = self._pdf_page_tables(anchor.doc)
            if not 1 <= anchor.page <= len(pages):
                return False
            tables = pages[anchor.page - 1]
            return 1 <= anchor.table <= len(tables) and 1 <= anchor.row <= tables[anchor.table - 1]
        if anchor.kind == "sheet-cell":
            sheets = self._workbook(anchor.doc)
            cells = sheets.get(anchor.sheet)
            return cells is not None and f"{anchor.column}{anchor.row}" in cells
        if anchor.kind == "row":
            return 1 <= anchor.row <= self._csv_rows(anchor.doc)
        if anchor.kind == "line":
            return 1 <= anchor.line <= self._text_lines(anchor.doc)
        if anchor.kind == "message-line":
            messages = self._mbox_lines(anchor.doc)
            return 1 <= anchor.message <= len(messages) and 1 <= anchor.line <= messages[anchor.message - 1]
        raise AssertionError(f"unknown anchor kind {anchor.kind}")

    def _pdf_page_lines(self, doc: str) -> list[list[str]]:
        if doc not in self._pdf_lines:
            pages = paginated_plain_text_output(str(self.path(doc)))
            self._pdf_lines[doc] = [page.split("\n") for page in pages]
        return self._pdf_lines[doc]

    def _pdf_page_tables(self, doc: str) -> list[list[int]]:
        if doc not in self._pdf_tables:
            with pdfplumber.open(self.path(doc)) as pdf:
                self._pdf_tables[doc] = [
                    [len(table) for table in page.extract_tables()] for page in pdf.pages
                ]
        return self._pdf_tables[doc]

    def _workbook(self, doc: str) -> dict[str, set[str]]:
        if doc not in self._sheets:
            workbook = openpyxl.load_workbook(self.path(doc), data_only=True, read_only=True)
            sheets = {}
            for sheet in workbook.worksheets:
                sheets[sheet.title] = {
                    cell.coordinate for row in sheet.iter_rows() for cell in row if cell.value is not None
                }
            workbook.close()
            self._sheets[doc] = sheets
        return self._sheets[doc]

    def _csv_rows(self, doc: str) -> int:
        if doc not in self._rows:
            with self.path(doc).open(newline="", encoding="utf-8") as handle:
                self._rows[doc] = sum(1 for _ in csv.reader(handle))
        return self._rows[doc]

    def _text_lines(self, doc: str) -> int:
        if doc not in self._lines:
            path = self.path(doc)
            if path.suffix == ".eml":
                message = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
                body = message.get_body(preferencelist=("plain",))
                text = body.get_content() if body is not None else ""
            else:
                text = path.read_text(encoding="utf-8")
            self._lines[doc] = len(text.split("\n"))
        return self._lines[doc]

    def _mbox_lines(self, doc: str) -> list[int]:
        if doc not in self._messages:
            box = mailbox.mbox(
                str(self.path(doc)),
                factory=lambda handle: email.message_from_binary_file(handle, policy=email.policy.default),
            )
            counts = []
            for message in box:
                body = message.get_body(preferencelist=("plain",))
                counts.append(len((body.get_content() if body is not None else "").split("\n")))
            box.close()
            self._messages[doc] = counts
        return self._messages[doc]
