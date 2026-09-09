"""Phase 7 fixture tests for sample 4, the Verizon and Yahoo filings.

The splitter tests run on small in-memory inputs and always run. The fixture tests read
samples/yahoo/documents/ and skip with a reason when it is absent, because the documents are
fetched from sec.gov and are never committed. The determinism test splits the cached raw HTML
twice and compares bytes, so it opens no socket.
"""

import json
import re
from pathlib import Path

import pytest

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
    documents_or_skip()
    for fact in key.facts:
        for doc in fact.documents:
            text = (SAMPLE / key.documents[doc]).read_text(encoding="utf-8")
            assert fact.value in text, f"{fact.id} not in {doc}"


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
