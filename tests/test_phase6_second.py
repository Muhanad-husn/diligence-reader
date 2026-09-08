"""Phase 6, the second knob. `python -m rlm.widen second samples/atlas samples/atlas-second`
writes a variant of sample 1 that carries a second matter: sample 2's eleven contract documents
added as a ninth folder, `data_room/08_Northwind_Contracts/`, with the ids DR-101 to DR-111.

Sample 1's room is untouched, document for document and byte for byte. The eleven added
documents carry sample 2's own text. The key is sample 1's key with sample 2's key merged into
it: 53 facts then 16, 14 required documents then 10, five decoys then one, each of sample 2's
documents lists remapped to the new ids. The answer, the rubric and the bar stay sample 1's,
because a 400m repricing outranks a 12.4m cliff.

The eleven ids, the counts and the two orderings the chain has to hold are written out below,
so this module is the specification and the knob is read against it. The harness of phases 1 to
5 on the variant is tests/test_phase6.py, which picks the variant up from
samples/atlas-second/key.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import test_phase6
from rlm import ingest as ingester
from rlm import verify
from rlm import widen
from rlm.key import load_key

ROOT = Path(__file__).resolve().parents[1]

SOURCE = "atlas"
SOURCE_DIR = ROOT / "samples" / SOURCE
SOURCE_SECTIONS = ROOT / "runs" / SOURCE / "sections.jsonl"

KNOB = "second"
SECOND = "atlas-second"
SECOND_DIR = ROOT / "samples" / SECOND
DIGESTS_PATH = ROOT / "tests" / "phase6-second-digests.json"

CONTROL_DIR = ROOT / "samples" / "atlas-control"

# The sample the second matter comes from, and the folder of it the knob reads.
SAMPLE_TWO = "northwind"
SAMPLE_TWO_DIR = ROOT / "samples" / SAMPLE_TWO
SAMPLE_TWO_ROOM = "sample_data_room/Northwind_Logistics"

# The folder the second matter is written under, and the id the first added document takes.
FOLDER = "08_Northwind_Contracts"
FIRST_ID = "DR-101"

# The eleven added documents in file name order, with the id each one takes.
ADDED: tuple[tuple[str, str], ...] = (
    ("DR-101", "arr_schedule.xlsx.md"),
    ("DR-102", "board_deck_excerpt.pdf.md"),
    ("DR-103", "cap_table_summary.pdf.md"),
    ("DR-104", "contractor_agreement_route_engine.pdf.md"),
    ("DR-105", "dpa_tidewater.pdf.md"),
    ("DR-106", "employment_ip_agreement.pdf.md"),
    ("DR-107", "msa_granite_manufacturing.pdf.md"),
    ("DR-108", "msa_harbor_foods.pdf.md"),
    ("DR-109", "msa_meridian_freight.pdf.md"),
    ("DR-110", "order_form_cobalt_retail.pdf.md"),
    ("DR-111", "subprocessor_register.pdf.md"),
)

# The one document of sample 2 that is not added: it is the buyer's own overview, not a
# contract of the target.
NOT_ADDED = "sample_data_room/_reference/buyer_overview.pdf.md"

# The Meridian MSA, which carries the second matter's own finding, and the Granite MSA, which
# is sample 2's decoy.
MERIDIAN = "DR-109"
GRANITE = "DR-107"

# What sample 1 carries, what sample 2 brings, and what the variant therefore carries.
SOURCE_DOCUMENTS = 100
SOURCE_FACTS = 53
SOURCE_REQUIRED = 14
SOURCE_DECOYS = 5
SECOND_FACTS = 16
SECOND_REQUIRED = 10
SECOND_DECOYS = 1
DOCUMENTS = SOURCE_DOCUMENTS + len(ADDED)
FACTS = SOURCE_FACTS + SECOND_FACTS
REQUIRED = SOURCE_REQUIRED + SECOND_REQUIRED
DECOYS = SOURCE_DECOYS + SECOND_DECOYS

# The earlier slices' variants, which this slice leaves as they are committed.
EARLIER = (("control", "atlas-control"), ("names", "atlas-names"), ("unnamed", "atlas-unnamed"))

SKIP_NO_PIN = "runs/atlas/sections.jsonl absent; run phase 1 ingest first"
SKIP_NO_SECOND = "samples/atlas-second has not been generated yet"


def generate(target: Path) -> int:
    """Runs the second knob from sample 1's pinned sections into target."""
    return widen.main([KNOB, str(SOURCE_DIR), str(target), "--runs", str(ROOT / "runs")])


def needs_second() -> None:
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)
    if not SECOND_DIR.exists():
        pytest.skip(SKIP_NO_SECOND)


def new_id() -> dict[str, str]:
    """Sample 2's document paths mapped to the ids the variant gives them."""
    return {f"{SAMPLE_TWO_ROOM}/{name}": doc_id for doc_id, name in ADDED}


def sample_two_key() -> dict:
    """Sample 2's key, read as it stands."""
    return json.loads((SAMPLE_TWO_DIR / "key.json").read_text(encoding="utf-8"))


def source_bytes(name: str) -> str:
    """One northwind source file, read as utf-8 with its line endings folded to newlines."""
    path = SAMPLE_TWO_DIR / SAMPLE_TWO_ROOM / name
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def source_blocks(name: str) -> list[str]:
    """The blocks of one northwind source file, as the knob writes them: the file split on a
    blank line, each block rendered, the empty ones dropped."""
    rendered = (widen.render(block) for block in source_bytes(name).split("\n\n"))
    return [block for block in rendered if block]


def added_path(name: str) -> str:
    """The path one added document takes in the variant."""
    return f"{widen.ROOM}/{FOLDER}/{name}"


def variant_bytes(path: str) -> str:
    """One file of the variant, read as utf-8 with its line endings folded to newlines."""
    return (SECOND_DIR / path).read_bytes().decode("utf-8").replace("\r\n", "\n")


def report_findings() -> list[tuple[str, set[str]]]:
    """The findings of the variant's report, in rank order, or a skip when it has none."""
    path = ROOT / "runs" / SECOND / "report.md"
    if not path.exists():
        pytest.skip("the chain has not written a report for the second variant yet")
    found = verify.findings(path.read_text(encoding="utf-8"))
    if not found:
        pytest.skip("the report carries no findings section")
    return found


def first_rank(found: list[tuple[str, set[str]]], documents: set[str]) -> int | None:
    """The rank of the first finding citing any of these documents, counting from zero."""
    for rank, (_, cited) in enumerate(found):
        if cited & documents:
            return rank
    return None


# ---------------------------------------------------------------- the knob


def test_the_knob_names_the_folder_the_sample_and_the_first_id():
    """The knob writes the second matter under the folder this module names, reads it out of the
    sample this module names, and gives the first added document the id this module names."""
    from rlm.widen import second

    assert second.NAME == KNOB
    assert second.FOLDER == FOLDER
    assert second.SECOND == SAMPLE_TWO
    assert second.FIRST_ID == FIRST_ID


# ---------------------------------------------------------------- the generator


def test_generator_writes_the_committed_second_variant_byte_for_byte(tmp_path):
    """Regenerating the variant into a temporary directory gives the committed sample back."""
    needs_second()

    assert generate(tmp_path / SECOND) == 0

    assert test_phase6.tree(tmp_path / SECOND) == test_phase6.tree(SECOND_DIR)


def test_generator_writes_the_same_bytes_twice(tmp_path):
    """Two runs of the knob write the same files: no draw, no model, no clock, no socket."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)

    assert generate(tmp_path / "one" / SECOND) == 0
    assert generate(tmp_path / "two" / SECOND) == 0

    assert test_phase6.tree(tmp_path / "one" / SECOND) == test_phase6.tree(
        tmp_path / "two" / SECOND
    )


def test_the_earlier_variants_are_unchanged(tmp_path):
    """The generator's addition leaves the variants of the earlier slices byte for byte as they
    are committed."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)

    for knob, name in EARLIER:
        directory = ROOT / "samples" / name
        if not directory.exists():
            continue
        assert (
            widen.main([knob, str(SOURCE_DIR), str(tmp_path / name), "--runs", str(ROOT / "runs")])
            == 0
        ), name
        assert test_phase6.tree(tmp_path / name) == test_phase6.tree(directory), name


# ---------------------------------------------------------------- the room


def test_the_room_holds_a_hundred_and_eleven_documents():
    """Every path of the key is a markdown file of the room and stands on disk."""
    needs_second()

    key = load_key(SECOND_DIR)

    assert key.sample == SECOND
    assert len(key.documents) == DOCUMENTS
    for path in key.documents.values():
        assert path.startswith(f"{widen.ROOM}/") and path.endswith(".md"), path
        assert (SECOND_DIR / path).is_file(), path


def test_the_first_hundred_documents_are_the_controls():
    """Sample 1's hundred keep their ids and their paths, and each file is the control's own."""
    needs_second()
    source = load_key(SOURCE_DIR)
    key = load_key(SECOND_DIR)

    ids = list(key.documents)
    assert ids[:SOURCE_DOCUMENTS] == list(source.documents)
    for doc_id, doc in source.documents.items():
        path = widen.markdown_path(doc)
        assert key.documents[doc_id] == path, doc_id
        if CONTROL_DIR.exists():
            assert (SECOND_DIR / path).read_bytes() == (CONTROL_DIR / path).read_bytes(), doc_id


def test_the_eleven_added_documents_carry_sample_twos_own_text():
    """Each added document is sample 2's file, with the trailing newline the source may lack."""
    needs_second()
    key = load_key(SECOND_DIR)

    assert [doc_id for doc_id, _ in ADDED] == list(key.documents)[SOURCE_DOCUMENTS:]
    for doc_id, name in ADDED:
        assert key.documents[doc_id] == added_path(name), doc_id
        written = variant_bytes(key.documents[doc_id])
        wanted = source_bytes(name)
        assert written in (wanted, wanted + "\n"), doc_id
    assert NOT_ADDED.rpartition("/")[2] not in {name for _, name in ADDED}


def test_each_added_document_reads_back_as_one_section_per_source_block():
    """Ingest's own block rule reads each added file back as the blocks of sample 2's file, one
    for one and in order."""
    needs_second()
    key = load_key(SECOND_DIR)

    for doc_id, name in ADDED:
        path = key.documents[doc_id]
        sections = ingester.read_document(SECOND_DIR / path, path)[0]
        assert [section.text for section in sections] == source_blocks(name), doc_id


# ---------------------------------------------------------------- the key


def test_the_key_holds_sixty_nine_facts_in_the_two_samples_own_orders():
    """Sample 1's 53 fact ids in sample 1's order, then sample 2's 16 in sample 2's order."""
    needs_second()
    source = load_key(SOURCE_DIR)
    key = load_key(SECOND_DIR)

    assert len(key.facts) == FACTS
    assert [fact.id for fact in key.facts] == [fact.id for fact in source.facts] + [
        fact["id"] for fact in sample_two_key()["facts"]
    ]


def test_sample_ones_facts_are_unchanged():
    """The first 53 facts are sample 1's, one for one, in every field."""
    needs_second()
    source = load_key(SOURCE_DIR)
    key = load_key(SECOND_DIR)

    assert key.facts[:SOURCE_FACTS] == source.facts


def test_sample_twos_facts_keep_their_shape_with_their_documents_remapped():
    """Each added fact keeps sample 2's kind, value and phase, and its documents are sample 2's
    documents written as the ids the variant gives them."""
    needs_second()
    key = load_key(SECOND_DIR)
    remap = new_id()

    for fact, was in zip(key.facts[SOURCE_FACTS:], sample_two_key()["facts"], strict=True):
        assert fact.kind == was["kind"], fact.id
        assert fact.value == was["value"], fact.id
        assert fact.phase == was["phase"], fact.id
        assert fact.documents == tuple(remap[doc] for doc in was["documents"]), fact.id


def test_the_key_holds_twenty_four_required_documents():
    """Sample 1's 14 in order, then sample 2's 10 remapped, in sample 2's order."""
    needs_second()
    source = load_key(SOURCE_DIR)
    key = load_key(SECOND_DIR)
    remap = new_id()

    assert len(key.required_documents) == REQUIRED
    assert key.required_documents == source.required_documents + tuple(
        remap[doc] for doc in sample_two_key()["required_documents"]
    )


def test_the_key_holds_six_decoys():
    """Sample 1's five unchanged, then the Granite MSA as DR-107 with sample 2's own why."""
    needs_second()
    source = load_key(SOURCE_DIR)
    key = load_key(SECOND_DIR)
    was = sample_two_key()["decoys"]

    assert len(key.decoys) == DECOYS
    assert key.decoys[:SOURCE_DECOYS] == source.decoys
    assert len(was) == SECOND_DECOYS
    assert key.decoys[SOURCE_DECOYS].document == GRANITE
    assert key.decoys[SOURCE_DECOYS].why == was[0]["why"]


def test_the_answer_the_rubric_and_the_bar_are_sample_ones():
    """A 400m repricing outranks a 12.4m cliff, so the answer the key asks for is sample 1's."""
    needs_second()
    source = load_key(SOURCE_DIR)
    key = load_key(SECOND_DIR)

    assert key.answer == source.answer
    assert key.rubric == source.rubric
    assert key.bar == source.bar


# ---------------------------------------------------------------- the brief and the README


def test_the_brief_is_sample_ones_brief_with_one_paragraph_added():
    """Sample 1's brief stands as a prefix, and one paragraph is added at the end naming the
    folder, the id range and the ARR schedule."""
    needs_second()
    was = (SOURCE_DIR / "brief.md").read_text(encoding="utf-8")
    brief = (SECOND_DIR / "brief.md").read_text(encoding="utf-8")

    assert brief.startswith(was)
    added = brief[len(was) :]
    paragraphs = [block for block in added.split("\n\n") if block.strip()]
    assert len(paragraphs) == 1, paragraphs
    for said in (FOLDER, FIRST_ID, ADDED[-1][0], "ARR schedule"):
        assert said in added, said


def test_the_readme_names_the_knob_and_tables_the_eleven_documents():
    """The README names the knob, drops no fact, counts the facts, and carries one row per
    added document."""
    needs_second()

    text = (SECOND_DIR / "README.md").read_text(encoding="utf-8")

    assert KNOB in text
    assert "Facts dropped: none" in text
    assert f"Facts: {FACTS}." in text
    for doc_id, name in ADDED:
        rows = [line for line in text.splitlines() if line.startswith("|") and doc_id in line]
        assert len(rows) == 1, doc_id
        assert name in rows[0], doc_id


# ---------------------------------------------------------------- the chain


def test_the_first_finding_cites_sample_ones_matter():
    """The report leads with sample 1's matter: the first finding cites only documents of
    sample 1's hundred, and at least one of sample 1's fourteen required documents."""
    needs_second()
    source = load_key(SOURCE_DIR)
    found = report_findings()

    _, cited = found[0]
    assert cited, found[0][0]
    assert cited <= set(source.documents), sorted(cited - set(source.documents))
    assert cited & set(source.required_documents), sorted(cited)


def test_the_meridian_msa_stands_before_every_decoy():
    """A finding citing the Meridian MSA ranks before any finding citing one of the six
    decoys."""
    needs_second()
    key = load_key(SECOND_DIR)
    found = report_findings()

    meridian = first_rank(found, {MERIDIAN})
    assert meridian is not None, "no finding cites the Meridian MSA"
    decoy = first_rank(found, {one.document for one in key.decoys})
    assert decoy is None or meridian < decoy, (meridian, decoy)


# ---------------------------------------------------------------- the pinned digests


def test_second_digests_are_pinned(tmp_path, capsys):
    """tests/phase6-second-digests.json holds what phases 1 to 5 pin for the variant."""
    if not (ROOT / "runs" / SECOND / "grade.json").exists():
        pytest.skip("the chain has not run on the second variant yet")
    if not DIGESTS_PATH.exists():
        pytest.skip("no second digests pinned yet")

    wanted = test_phase6.pinned_digests(ROOT / "runs", SECOND, tmp_path)
    capsys.readouterr()

    assert json.loads(DIGESTS_PATH.read_text(encoding="utf-8")) == {SECOND: wanted}
