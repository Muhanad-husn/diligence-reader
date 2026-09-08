"""Phase 6 widen tests. The generator writes a variant of sample 1 as a markdown data room
with a key by construction, and the chain of phases 1 to 5 runs on that variant unchanged.

These tests have two halves. The first half is the generator: it regenerates the committed
variant into a temporary directory and compares every file byte for byte, it reads the
markdown back through ingest's own block rule and asks for one block per source section, and
it checks the key it wrote. The second half is the harness: one test per phase in order,
parametrised over every samples/atlas-*/key.json on disk, reading the artefacts the chain left
under runs/<variant>/ and skipping with a reason where an artefact is absent. The checks come
from rlm.grade and from the phase 1 to 5 test modules; nothing here restates a rule those
modules already carry.

The readout prints one line per variant: recall, the dollars the ledger booked to phase 6 for
that sample, the spread of the two writes, and the first phase whose test failed, or holds.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import test_phase1
import test_phase2
import test_phase3
import test_phase4
import test_phase5
from rlm import ingest as ingester
from rlm import notes as noter
from rlm import pin
from rlm import widen
from rlm import write as writer
from rlm.gateway import PHASE_CAPS, Gateway, Ledger
from rlm.grade import measure_recall
from rlm.key import load_key

ROOT = Path(__file__).resolve().parents[1]

# The sample every variant is generated from, and the pinned artefact the generator reads.
SOURCE = "atlas"
SOURCE_SECTIONS = ROOT / "runs" / SOURCE / "sections.jsonl"

# The phase this slice books its calls to, and the cap PLAN.md section 4 gives it.
PHASE = 6
PHASE_CAP = 15.0

# Every variant on disk, in name order. A slice that has not generated its variant yet leaves
# this list shorter, and the harness tests are collected against what is there.
VARIANTS = tuple(
    sorted(
        path.parent.name
        for path in (ROOT / "samples").glob("atlas-*/key.json")
    )
)

# The variant this slice generates and the knob that writes it.
CONTROL = "atlas-control"
CONTROL_DIR = ROOT / "samples" / CONTROL

# What sample 1 carries, by construction, and what a variant of it therefore carries.
DOCUMENTS = 100
FACTS = 53

# The bar the rubric is read against, phase 5's own.
RUBRIC_BAR = test_phase5.RUBRIC_BAR

SKIP_NO_PIN = "runs/atlas/sections.jsonl absent; run phase 1 ingest first"
SKIP_NO_CONTROL = "samples/atlas-control has not been generated yet"


# ---------------------------------------------------------------- the variant under test


@pytest.fixture(params=VARIANTS)
def sample(request):
    """Every variant on disk. This shadows the conftest fixture, so sample_dir and run_dir of
    the conftest resolve to samples/<variant> and runs/<variant> inside this module."""
    return request.param


@pytest.fixture
def key(sample_dir):
    return load_key(sample_dir)


@pytest.fixture
def records(run_dir):
    """The sections of the variant's run, or a skip when ingest has not run on it."""
    path = run_dir / "sections.jsonl"
    if not path.exists():
        pytest.skip("ingest not run for this variant yet")
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())


@pytest.fixture
def indexed(run_dir, records):
    path = run_dir / "index.jsonl"
    if not path.exists():
        pytest.skip("ingest not run for this variant yet")
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())


@pytest.fixture
def notes(run_dir):
    """Every note of the variant's run, keyed by file name, or a skip when there are none."""
    notes_dir = run_dir / "notes"
    if not notes_dir.is_dir():
        pytest.skip("notes not run for this variant yet")
    found = {}
    for path in sorted(notes_dir.glob("*.json")):
        raw = path.read_text(encoding="utf-8")
        found[path.name] = (raw, json.loads(raw))
    if not found:
        pytest.skip("notes not run for this variant yet")
    return found


@pytest.fixture
def sections_by_doc(records):
    by_doc: dict[str, list[dict]] = {}
    for record in records:
        by_doc.setdefault(record["doc"], []).append(record)
    return by_doc


@pytest.fixture
def mapped(run_dir):
    path = run_dir / "map.json"
    if not path.exists():
        pytest.skip("map not run for this variant yet")
    return test_phase3.Run(
        first=path,
        second=path,
        document=json.loads(path.read_text(encoding="utf-8")),
        printed="",
    )


@pytest.fixture
def dossiered(run_dir):
    path = run_dir / "dossier.md"
    if not path.exists():
        pytest.skip("dossier not run for this variant yet")
    return test_phase4.Run(
        first=path, second=path, text=path.read_text(encoding="utf-8"), printed=""
    )


@pytest.fixture
def report(run_dir):
    path = run_dir / "report.md"
    dossier = run_dir / "dossier.md"
    digest = run_dir / "digest.md"
    if not (path.exists() and dossier.exists() and digest.exists()):
        pytest.skip("report not written for this variant yet")
    return test_phase5.Report(
        path=path,
        text=path.read_text(encoding="utf-8"),
        dossier=dossier.read_text(encoding="utf-8"),
        digest=digest.read_text(encoding="utf-8"),
    )


@pytest.fixture
def verified(run_dir, report):
    path = run_dir / "verify.json"
    if not path.exists():
        pytest.skip("verify.json not written for this variant yet")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def graded(run_dir, report):
    path = run_dir / "grade.json"
    if not path.exists():
        pytest.skip("grade.json not written for this variant yet")
    return json.loads(path.read_text(encoding="utf-8"))


# The two fixtures the phase 4 checks take, reused as the phase 4 test module wrote them.
known_anchors = test_phase4.known_anchors
index_surfaces = test_phase4.index_surfaces


# ---------------------------------------------------------------- what the readout remembers


_RAN: set[tuple[str, int]] = set()
_HELD: set[tuple[str, int]] = set()


def ran(sample: str, phase: int) -> None:
    """Records that this variant's test for this phase started."""
    _RAN.add((sample, phase))


def holds(sample: str, phase: int) -> None:
    """Records that this variant's test for this phase reached its end."""
    _HELD.add((sample, phase))


def first_failure(sample: str) -> int | None:
    """The lowest phase whose test ran on this variant and did not reach its end."""
    for phase in range(1, 6):
        if (sample, phase) in _RAN and (sample, phase) not in _HELD:
            return phase
    return None


# ---------------------------------------------------------------- the generator


def tree(directory: Path) -> dict[str, bytes]:
    """Every file under a directory, by its path relative to it, with its bytes."""
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def generate(target: Path) -> int:
    """Runs the control knob from sample 1's pinned sections into target."""
    return widen.main(
        [
            "control",
            str(ROOT / "samples" / SOURCE),
            str(target),
            "--runs",
            str(ROOT / "runs"),
        ]
    )


def source_texts() -> dict[str, list[str]]:
    """The rendered text of every section of sample 1's pinned run, by document path."""
    found: dict[str, list[str]] = {}
    for line in SOURCE_SECTIONS.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        rendered = widen.render(record["text"])
        if rendered:
            found.setdefault(record["doc"], []).append(rendered)
    return found


def test_generator_writes_the_committed_control_byte_for_byte(tmp_path):
    """Regenerating the control into a temporary directory gives the committed sample back."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)
    if not CONTROL_DIR.exists():
        pytest.skip(SKIP_NO_CONTROL)

    assert generate(tmp_path / CONTROL) == 0

    assert tree(tmp_path / CONTROL) == tree(CONTROL_DIR)


def test_generator_writes_the_same_bytes_twice(tmp_path):
    """Two runs of the knob write the same files: seed 0, no model, no clock, no socket."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)

    assert generate(tmp_path / "one" / CONTROL) == 0
    assert generate(tmp_path / "two" / CONTROL) == 0

    assert tree(tmp_path / "one" / CONTROL) == tree(tmp_path / "two" / CONTROL)


def test_generator_refuses_a_sections_file_that_is_not_the_pinned_one(tmp_path, capsys):
    """A sections.jsonl whose sha256 is not the pinned one stops the run before it writes."""
    runs = tmp_path / "runs" / SOURCE
    runs.mkdir(parents=True)
    (runs / "sections.jsonl").write_text("{}\n", encoding="utf-8")
    target = tmp_path / CONTROL

    code = widen.main(
        [
            "control",
            str(ROOT / "samples" / SOURCE),
            str(target),
            "--runs",
            str(tmp_path / "runs"),
        ]
    )

    assert code == 2
    assert "sections.jsonl" in capsys.readouterr().out
    assert not target.exists()


def test_generator_refuses_a_knob_it_has_no_module_for(tmp_path, capsys):
    """A knob with no module under rlm.widen is a refusal that names the knob."""
    code = widen.main(
        [
            "nosuchknob",
            str(ROOT / "samples" / SOURCE),
            str(tmp_path / "out"),
            "--runs",
            str(ROOT / "runs"),
        ]
    )

    assert code == 2
    assert "nosuchknob" in capsys.readouterr().out


def test_generator_renders_a_section_holding_a_blank_line_as_one_block(tmp_path):
    """A section text with a blank line inside it reads back as one section, not two."""
    document = widen.document_markdown([widen.render("first line\n\nsecond line"), "after"])
    path = tmp_path / "a.md"
    path.write_text(document, encoding="utf-8", newline="\n")

    sections = ingester.read_document(path, "a.md")[0]

    assert [section.text for section in sections] == ["first line\nsecond line", "after"]


def test_generator_renders_a_carriage_return_as_one_block(tmp_path):
    """A section text ending in a carriage return reads back as one section, not two."""
    document = widen.document_markdown([widen.render("Marc,\r"), widen.render("a\r\nb\r")])
    path = tmp_path / "a.md"
    path.write_text(document, encoding="utf-8", newline="\n")

    sections = ingester.read_document(path, "a.md")[0]

    assert [section.text for section in sections] == ["Marc,", "a\nb"]


def test_generator_leaves_markdown_emphasis_marks_where_they_are(tmp_path):
    """Emphasis marks in a section text are text, and ingest reads them back unchanged."""
    text = "The reserve is **$12m** and the range is _$240m to $465m_."
    document = widen.document_markdown([widen.render(text)])
    path = tmp_path / "a.md"
    path.write_text(document, encoding="utf-8", newline="\n")

    sections = ingester.read_document(path, "a.md")[0]

    assert [section.text for section in sections] == [text]


def test_control_holds_a_hundred_documents_and_fifty_three_facts():
    """The variant's key loads and carries sample 1's own counts."""
    if not CONTROL_DIR.exists():
        pytest.skip(SKIP_NO_CONTROL)

    key = load_key(CONTROL_DIR)

    assert len(key.documents) == DOCUMENTS
    assert len(key.facts) == FACTS
    for path in key.documents.values():
        assert path.startswith("data_room/") and path.endswith(".md"), path
        assert (CONTROL_DIR / path).is_file(), path


def test_control_keeps_the_ids_the_decoys_the_answer_and_the_rubric():
    """Only the document paths and the sample's name change; the rest of the key is sample 1's."""
    if not CONTROL_DIR.exists():
        pytest.skip(SKIP_NO_CONTROL)
    source = load_key(ROOT / "samples" / SOURCE)
    key = load_key(CONTROL_DIR)

    assert key.sample == CONTROL
    assert set(key.documents) == set(source.documents)
    assert key.required_documents == source.required_documents
    assert key.decoys == source.decoys
    assert key.answer == source.answer
    assert key.rubric == source.rubric
    assert key.bar == source.bar
    assert key.facts == source.facts


def test_control_brief_is_sample_ones_brief():
    """The control adds no document, so it adds no paragraph to the brief."""
    if not CONTROL_DIR.exists():
        pytest.skip(SKIP_NO_CONTROL)

    assert (CONTROL_DIR / "brief.md").read_text(encoding="utf-8") == (
        ROOT / "samples" / SOURCE / "brief.md"
    ).read_text(encoding="utf-8")


def test_control_readme_lists_the_knob_and_the_facts_it_drops():
    """The variant's README names the knob and says which facts the knob dropped."""
    if not CONTROL_DIR.exists():
        pytest.skip(SKIP_NO_CONTROL)

    text = (CONTROL_DIR / "README.md").read_text(encoding="utf-8")

    assert "control" in text
    assert "none" in text.lower()


def test_control_documents_carry_every_source_section_text_in_order():
    """Each markdown file holds the text of every section of its source document, in order."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)
    if not CONTROL_DIR.exists():
        pytest.skip(SKIP_NO_CONTROL)
    source = load_key(ROOT / "samples" / SOURCE)
    key = load_key(CONTROL_DIR)
    texts = source_texts()

    for doc_id, path in source.documents.items():
        written = (CONTROL_DIR / key.documents[doc_id]).read_text(encoding="utf-8")
        at = 0
        for text in texts[path]:
            found = written.find(text, at)
            assert found >= 0, (doc_id, text[:80])
            at = found + len(text)


def test_control_documents_read_back_as_one_section_per_source_section():
    """Ingest's own block rule reads each markdown file back as the sections it was written
    from, one for one and in order."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)
    if not CONTROL_DIR.exists():
        pytest.skip(SKIP_NO_CONTROL)
    source = load_key(ROOT / "samples" / SOURCE)
    key = load_key(CONTROL_DIR)
    texts = source_texts()

    for doc_id, path in source.documents.items():
        target = CONTROL_DIR / key.documents[doc_id]
        sections = ingester.read_document(target, key.documents[doc_id])[0]
        assert [section.text for section in sections] == texts[path], doc_id


# ---------------------------------------------------------------- the phase flag


def test_notes_phase_defaults_to_its_own_constant():
    """--phase left off books to phase 2, and --phase 6 books to phase 6."""
    assert noter.parse_args(["s", "r"]).phase == noter.PHASE == 2
    assert noter.parse_args(["s", "r", "--phase", "6"]).phase == PHASE


def test_write_phase_defaults_to_its_own_constant():
    """--phase left off books to phase 5, and --phase 6 books to phase 6."""
    assert writer.parse_args(["s", "r"]).phase == writer.PHASE == 5
    assert writer.parse_args(["s", "r", "--phase", "6"]).phase == PHASE


def test_the_phase_6_cap_is_fifteen_dollars():
    """PLAN.md section 4 gives phase 6 a $15 cap, and the gateway is what enforces it."""
    assert PHASE_CAPS[PHASE] == PHASE_CAP


def test_notes_books_its_row_to_the_phase_it_was_given(tmp_path):
    """One note run with --phase 6 leaves one phase 6 row and makes one call."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)
    ledger_path = tmp_path / "LEDGER.md"
    test_phase2.write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    transport = test_phase2.FakeTransport(
        [test_phase2.reply(json.dumps(test_phase2.MINIMAL_NOTE), tokens_in=2500, tokens_out=400)]
    )
    gateway = Gateway(api_key="k", transport=transport)

    code = noter.main(
        [
            str(ROOT / "samples" / SOURCE),
            str(ROOT / "runs" / SOURCE),
            "--only",
            "DR-069",
            "--out",
            str(tmp_path / "out"),
            "--phase",
            "6",
        ],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )

    assert code == 0
    rows = test_phase2.ledger_rows(ledger_path)
    assert rows[-1]["phase"] == "6"
    assert rows[-1]["sample"] == SOURCE


def _fake_write_sample(tmp_path):
    """A sample directory, a run directory holding the fake room, and an empty ledger.

    This is the phase 5 fake_sample fixture's own room, built here so that the phase flag can
    be tested without a network and without the phase 5 fixture's parametrisation.
    """
    sample_dir = tmp_path / "atlas"
    run_dir = tmp_path / "run"
    sample_dir.mkdir()
    run_dir.mkdir()
    (sample_dir / "brief.md").write_text("# Brief\n\nFind the matter.\n", encoding="utf-8")
    (run_dir / "dossier.md").write_text(test_phase5.FAKE_DOSSIER, encoding="utf-8")
    test_phase5.write_jsonl(run_dir / "sections.jsonl", test_phase5.FAKE_SECTIONS)
    test_phase5.write_jsonl(run_dir / "index.jsonl", test_phase5.FAKE_INDEX)
    (run_dir / "map.json").write_text(
        json.dumps(test_phase5.FAKE_MAP, indent=1) + "\n", encoding="utf-8"
    )
    ledger_path = tmp_path / "LEDGER.md"
    ledger_path.write_text(test_phase5.LEDGER_HEADER, encoding="utf-8")
    return sample_dir, run_dir, Ledger(ledger_path)


def test_write_books_its_row_to_the_phase_it_was_given(tmp_path):
    """One write run with --phase 6 leaves one phase 6 row."""
    sample_dir, run_dir, ledger = _fake_write_sample(tmp_path)
    transport = test_phase5.FakeTransport([test_phase5.reply(test_phase5.FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)

    code = writer.main(
        [str(sample_dir), str(run_dir), "--phase", "6"], gateway=gateway, ledger=ledger
    )

    assert code == 0
    rows = ledger.rows()
    assert len(rows) == 1
    assert rows[0]["phase"] == "6"


# ---------------------------------------------------------------- phases 1 to 5 on a variant


def test_phase_1_holds_on_the_variant(sample, sample_dir, key, records, indexed):
    """Every anchor resolves in its own file and every planted fact is in the room."""
    ran(sample, 1)
    ingested = test_phase1.Run(
        first=ROOT / "runs" / sample / "sections.jsonl",
        second=ROOT / "runs" / sample / "sections.jsonl",
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
    # Phase 1 owns the facts the key marks phase 1: a date, an amount or an identifier the
    # room writes. A phase 3, 4 or 5 fact is a statement about the map, the dossier or the
    # report and the phase that owns it is what resolves it.
    missed = [
        fact.id
        for fact in key.facts
        if fact.phase == 1
        and not test_phase1._fact_resolved(fact, key, sectioned, texts, indexed)
    ]
    assert not missed, f"{sample}: phase 1 does not resolve {missed}"
    holds(sample, 1)


def test_phase_2_holds_on_the_variant(sample, key, notes, sections_by_doc):
    """Every note is well shaped, every quote verifies, and every phase 2 fact is quoted."""
    ran(sample, 2)
    test_phase2.assert_notes_well_shaped(notes, key)
    test_phase2.assert_notes_quotes_verified(notes, sections_by_doc)
    test_phase2.test_one_document_carries_its_planted_quotes(notes, key)
    holds(sample, 2)


def test_phase_3_holds_on_the_variant(sample, key, mapped):
    """The first matter's cluster holds every planted document and every required document."""
    ran(sample, 3)
    test_phase3.test_map_first_matter_cluster_holds_the_planted_documents(mapped, key)
    cluster = set(mapped.document["matters"][0]["cluster"])
    required = set(key.required_documents)
    assert required <= cluster, sorted(required - cluster)
    holds(sample, 3)


def test_phase_4_holds_on_the_variant(sample, key, dossiered, known_anchors, index_surfaces):
    """The document set holds the planted documents and no decoy, and every phase 1 and 2 fact
    has a row with an anchor of its own document."""
    ran(sample, 4)
    test_phase4.test_dossier_documents_hold_the_planted_documents_and_no_decoy(dossiered, key)
    test_phase4.test_dossier_carries_every_phase_1_and_2_fact(
        dossiered, key, known_anchors, index_surfaces
    )
    test_phase4.test_dossier_every_row_anchor_belongs_to_its_document(
        dossiered, key, known_anchors
    )
    holds(sample, 4)


def test_phase_5_holds_on_the_variant(sample, key, report, verified, graded):
    """Recall is 100, the verifier passes, and the rubric is at or above the bar."""
    ran(sample, 5)
    recall, _, missed = measure_recall(key, report.text)
    assert recall == 100.0, f"recall {recall}, missed {missed}"
    assert verified["passes"] is True, f"last round: {verified['rounds'][-1][:5]}"
    assert graded["score"] >= RUBRIC_BAR, f"score {graded['score']}"
    assert "spread" in graded, "the second pass has not been graded"
    holds(sample, 5)


# ---------------------------------------------------------------- the pinned digests


DIGESTS_PATH = ROOT / "tests" / "phase6-control-digests.json"

# The four pin modes that read nothing but the artefacts on disk, in phase order.
PIN_MODES = ("--sections", "--from-notes", "--maps", "--dossiers")


def pinned_digests(runs_root: Path, name: str, tmp_path: Path) -> dict[str, str]:
    """Every digest the phase 1 to 5 digest files hold for one sample, in one dict.

    pin writes one file per mode, so the four modes above are run into temporary files and
    merged. The three files phase 5 pins are digested by pin's own report_digests: pin's
    --reports mode copies a write bake-off winner into place, and a variant has no bake-off.
    """
    found: dict[str, str] = {}
    for number, mode in enumerate(PIN_MODES):
        out = tmp_path / f"{number}.json"
        code = pin.main([str(runs_root), mode, "--samples", name, "--digests", str(out)])
        assert code == 0, mode
        found.update(json.loads(out.read_text(encoding="utf-8"))[name])
    found.update(pin.report_digests(runs_root / name))
    return found


def test_control_digests_are_pinned(tmp_path, capsys):
    """tests/phase6-control-digests.json holds what phases 1 to 5 pin for the control."""
    if not (ROOT / "runs" / CONTROL / "grade.json").exists():
        pytest.skip("the chain has not run on the control yet")
    if not DIGESTS_PATH.exists():
        pytest.skip("no control digests pinned yet")

    wanted = pinned_digests(ROOT / "runs", CONTROL, tmp_path)
    capsys.readouterr()

    assert json.loads(DIGESTS_PATH.read_text(encoding="utf-8")) == {CONTROL: wanted}


# ---------------------------------------------------------------- the readout


def readout(terminalreporter):
    """Writes one line per variant: recall, the phase 6 dollars, the spread, and where it stands."""
    if not _RAN:
        return
    terminalreporter.section("phase 6 readout")
    rows = Ledger(ROOT / "LEDGER.md").rows()
    for sample in VARIANTS:
        if not any(name == sample for name, _ in _RAN):
            continue
        run_dir = ROOT / "runs" / sample
        recall = "not written"
        report_path = run_dir / "report.md"
        if report_path.exists() and (ROOT / "samples" / sample / "key.json").exists():
            score, _, missed = measure_recall(
                load_key(ROOT / "samples" / sample), report_path.read_text(encoding="utf-8")
            )
            recall = f"{score:.1f}"
        spread = "not written"
        grade_path = run_dir / "grade.json"
        if grade_path.exists():
            grade = json.loads(grade_path.read_text(encoding="utf-8"))
            if "spread" in grade:
                spread = f"{grade['spread']:g}"
        dollars = sum(
            row["dollars"] for row in rows if row["phase"] == str(PHASE) and row["sample"] == sample
        )
        failed = first_failure(sample)
        state = f"phase {failed} fails" if failed else "holds"
        terminalreporter.write_line(
            f"phase 6 {sample}: recall {recall}, ${dollars:.4f}, spread {spread}, {state}"
        )
