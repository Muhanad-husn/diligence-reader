"""Phase 6, the names knob. `python -m rlm.widen names samples/atlas samples/atlas-names`
respells the names of people and organisations with a seeded choice per document among fixed
variants, and leaves identifiers, numbers and dates alone.

The knob's README carries one table of every respelled name: the name as sample 1 writes it,
one variant per row, and the documents that variant was written into. These tests read that
table against the files, so nothing is respelled unless the README says so and the file shows
it. The harness of phases 1 to 5 on the variant is tests/test_phase6.py, which picks the
variant up from samples/atlas-names/key.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import test_phase6
from rlm import pin
from rlm import widen
from rlm.key import load_key

ROOT = Path(__file__).resolve().parents[1]

SOURCE = "atlas"
SOURCE_DIR = ROOT / "samples" / SOURCE
SOURCE_SECTIONS = ROOT / "runs" / SOURCE / "sections.jsonl"

KNOB = "names"
NAMES = "atlas-names"
NAMES_DIR = ROOT / "samples" / NAMES
DIGESTS_PATH = ROOT / "tests" / "phase6-names-digests.json"

# What the issue asks of the knob.
MIN_NAMES = 10
MIN_SPELLINGS = 3

# What sample 1 carries, and what the variant therefore carries.
DOCUMENTS = 100
FACTS = 53

SKIP_NO_PIN = "runs/atlas/sections.jsonl absent; run phase 1 ingest first"
SKIP_NO_NAMES = "samples/atlas-names has not been generated yet"

# One row of the README's table: | name | variant | DR-001, DR-002 |
ROW = re.compile(r"^\|\s*(?P<name>[^|]+?)\s*\|\s*(?P<variant>[^|]+?)\s*\|\s*(?P<docs>[^|]*?)\s*\|$")
DOC_ID = re.compile(r"DR-\d{3}")
DIGITS = re.compile(r"\d+")


def generate(target: Path) -> int:
    """Runs the names knob from sample 1's pinned sections into target."""
    return widen.main(
        [KNOB, str(SOURCE_DIR), str(target), "--runs", str(ROOT / "runs")]
    )


def needs_names() -> None:
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)
    if not NAMES_DIR.exists():
        pytest.skip(SKIP_NO_NAMES)


def unbackticked(cell: str) -> str:
    """A table cell with the backticks the README writes around a spelling taken off."""
    cell = cell.strip()
    if len(cell) >= 2 and cell[0] == "`" and cell[-1] == "`":
        return cell[1:-1]
    return cell


def readme_rows() -> list[tuple[str, str, tuple[str, ...]]]:
    """Every (name, variant, document ids) row of the README's names table."""
    rows = []
    for line in (NAMES_DIR / "README.md").read_text(encoding="utf-8").splitlines():
        match = ROW.match(line.strip())
        if not match:
            continue
        name = unbackticked(match["name"])
        variant = unbackticked(match["variant"])
        docs = tuple(DOC_ID.findall(match["docs"]))
        if name.lower() in ("name", "") or set(name) <= {"-", ":", " "}:
            continue
        rows.append((name, variant, docs))
    return rows


def document_text(key, doc_id: str) -> str:
    return (NAMES_DIR / key.documents[doc_id]).read_text(encoding="utf-8")


# ---------------------------------------------------------------- the generator


def test_generator_writes_the_committed_names_variant_byte_for_byte(tmp_path):
    """Regenerating the variant into a temporary directory gives the committed sample back."""
    needs_names()

    assert generate(tmp_path / NAMES) == 0

    assert test_phase6.tree(tmp_path / NAMES) == test_phase6.tree(NAMES_DIR)


def test_generator_writes_the_same_bytes_twice(tmp_path):
    """Two runs of the knob write the same files: seed 0, no model, no clock, no socket."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)

    assert generate(tmp_path / "one" / NAMES) == 0
    assert generate(tmp_path / "two" / NAMES) == 0

    assert test_phase6.tree(tmp_path / "one" / NAMES) == test_phase6.tree(tmp_path / "two" / NAMES)


# ---------------------------------------------------------------- the names


def test_readme_lists_at_least_ten_names_each_in_at_least_three_spellings():
    """The README's table names at least ten distinct names, and every one of them is written
    in at least three distinct spellings across the room."""
    needs_names()
    rows = readme_rows()
    spellings: dict[str, set[str]] = {}
    for name, variant, docs in rows:
        if docs:
            spellings.setdefault(name, set()).add(variant)

    assert len(spellings) >= MIN_NAMES, sorted(spellings)
    thin = {name: sorted(seen) for name, seen in spellings.items() if len(seen) < MIN_SPELLINGS}
    assert not thin, thin


def test_every_listed_spelling_is_in_every_document_the_readme_lists_for_it():
    """Each row's variant is written, as the row spells it, in each document the row names."""
    needs_names()
    key = load_key(NAMES_DIR)
    rows = readme_rows()
    assert rows, "the README carries no names table"

    missing = []
    for name, variant, docs in rows:
        for doc in docs:
            assert doc in key.documents, doc
            if variant not in document_text(key, doc):
                missing.append((name, variant, doc))
    assert not missing, missing


def test_every_respelled_name_is_respelled_in_at_least_one_document_it_was_in():
    """A name in the table is one sample 1 writes: its source spelling is in the source room,
    and at least one variant that is not the source spelling is in the variant room."""
    needs_names()
    source = load_key(SOURCE_DIR)
    texts = test_phase6.source_texts()
    source_room = "\n".join("\n".join(texts[path]) for path in source.documents.values())
    rows = readme_rows()

    respelled: dict[str, bool] = {}
    for name, variant, docs in rows:
        assert name in source_room, name
        if docs and variant != name:
            respelled[name] = True
        respelled.setdefault(name, False)
    unchanged = sorted(name for name, seen in respelled.items() if not seen)
    assert not unchanged, unchanged


def test_identifiers_numbers_and_dates_are_untouched():
    """Every run of digits in every document is the source's, in the source's order. A name
    knob changes letters, never a figure, an identifier or a date."""
    needs_names()
    source = load_key(SOURCE_DIR)
    key = load_key(NAMES_DIR)
    texts = test_phase6.source_texts()

    for doc_id, path in source.documents.items():
        wanted = DIGITS.findall("\n".join(texts[path]))
        got = DIGITS.findall(document_text(key, doc_id))
        assert got == wanted, doc_id


def test_every_document_reads_back_with_the_source_section_count():
    """The knob rewrites text inside a section and never adds or drops one."""
    needs_names()
    source = load_key(SOURCE_DIR)
    key = load_key(NAMES_DIR)
    texts = test_phase6.source_texts()

    for doc_id, path in source.documents.items():
        written = document_text(key, doc_id)
        blocks = [block for block in written.replace("\r\n", "\n").split("\n\n") if block.strip()]
        assert len(blocks) == len(texts[path]), doc_id


# ---------------------------------------------------------------- the key


def test_names_key_keeps_the_counts_the_ids_the_decoys_the_answer_and_the_rubric():
    """The key is sample 1's, with the new paths and the fact texts the knob rewrote."""
    needs_names()
    source = load_key(SOURCE_DIR)
    key = load_key(NAMES_DIR)

    assert key.sample == NAMES
    assert len(key.documents) == DOCUMENTS
    assert len(key.facts) == FACTS
    assert set(key.documents) == set(source.documents)
    assert key.required_documents == source.required_documents
    assert key.decoys == source.decoys
    assert key.answer == source.answer
    assert key.rubric == source.rubric
    assert key.bar == source.bar
    for path in key.documents.values():
        assert path.startswith("data_room/") and path.endswith(".md"), path
        assert (NAMES_DIR / path).is_file(), path


def test_names_key_facts_are_the_source_facts_except_quote_text():
    """Every fact keeps its id, kind, documents and phase; a fact that is not a quote keeps its
    value; a quote fact's value stands in the fact's first document as written."""
    needs_names()
    source = {fact.id: fact for fact in load_key(SOURCE_DIR).facts}
    key = load_key(NAMES_DIR)

    assert [fact.id for fact in key.facts] == list(source)
    for fact in key.facts:
        was = source[fact.id]
        assert fact.kind == was.kind, fact.id
        assert fact.documents == was.documents, fact.id
        assert fact.phase == was.phase, fact.id
        if fact.kind == "quote":
            assert fact.value in document_text(key, fact.documents[0]), fact.id
        else:
            assert fact.value == was.value, fact.id


def test_names_brief_is_sample_ones_brief():
    """The knob adds no document, so it adds no paragraph to the brief."""
    needs_names()

    assert (NAMES_DIR / "brief.md").read_text(encoding="utf-8") == (
        SOURCE_DIR / "brief.md"
    ).read_text(encoding="utf-8")


# ---------------------------------------------------------------- the pinned digests


def test_names_digests_are_pinned(tmp_path, capsys):
    """tests/phase6-names-digests.json holds what phases 1 to 5 pin for the variant."""
    if not (ROOT / "runs" / NAMES / "grade.json").exists():
        pytest.skip("the chain has not run on the names variant yet")
    if not DIGESTS_PATH.exists():
        pytest.skip("no names digests pinned yet")

    wanted = test_phase6.pinned_digests(ROOT / "runs", NAMES, tmp_path)
    capsys.readouterr()

    assert json.loads(DIGESTS_PATH.read_text(encoding="utf-8")) == {NAMES: wanted}
