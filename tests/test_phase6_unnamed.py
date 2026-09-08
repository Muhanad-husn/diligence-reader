"""Phase 6, the unnamed knob. `python -m rlm.widen unnamed samples/atlas samples/atlas-unnamed`
writes a variant of sample 1 in which the matter is named nowhere: the five names the matter is
known by across functions and the two file-name identifiers that link its documents are each
replaced by a plain phrase, the same phrase in every document. Dates, record counts, amounts,
people and organisations are untouched.

The seven identifiers, the seven phrases and the five key facts the knob drops are written out
below, so this module is the specification and the knob is read against it. The knob's README
carries one table of the seven phrases and the documents each was written into, and these tests
read that table against the files. The harness of phases 1 to 5 on the variant is
tests/test_phase6.py, which picks the variant up from samples/atlas-unnamed/key.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import test_phase6
from rlm import widen
from rlm.key import load_key

ROOT = Path(__file__).resolve().parents[1]

SOURCE = "atlas"
SOURCE_DIR = ROOT / "samples" / SOURCE
SOURCE_SECTIONS = ROOT / "runs" / SOURCE / "sections.jsonl"

KNOB = "unnamed"
UNNAMED = "atlas-unnamed"
UNNAMED_DIR = ROOT / "samples" / UNNAMED
DIGESTS_PATH = ROOT / "tests" / "phase6-unnamed-digests.json"

# What sample 1 carries, and what the variant therefore carries once the knob has dropped the
# five identifier facts whose value is a name the knob removes.
DOCUMENTS = 100
SOURCE_FACTS = 53
DROPPED = ("backup-object", "signing-key", "ticket", "workstream", "programme")
FACTS = SOURCE_FACTS - len(DROPPED)

# The three identifier facts that stay: two organisations and a system, not names of the matter.
KEPT_IDENTIFIERS = ("forensics-firm", "outside-counsel", "object-store")

# The phrase each identifier is written as, by the identifier's id.
PHRASES = {
    "workstream": "workstream",
    "ticket": "ticket",
    "programme": "programme",
    "sign-in-difficulty": "sign-in difficulty",
    "account-security": "account-security",
    "archive": "archive",
    "signing-key": "signing key",
}

# The names the knob removes, by the identifier's id. A name is matched on a whole token, and
# every name but the first is matched whatever its case.
REMOVED = {
    "workstream": ("AURORA",),
    "ticket": ("NQ-17", "NQ17"),
    "programme": ("Trust Reset",),
    "sign-in-difficulty": ("login friction",),
    "account-security": ("credential-hygiene", "credential hygiene"),
    "archive": ("legacy_uap_backup_2021.tar.gz",),
    "signing-key": ("vpauth-legacy-2019",),
}

# The one organisation whose name reads like the workstream's and is not it. Sample 1's
# publisher schedule writes it and the knob leaves it alone, so the case-insensitive check for
# the workstream's name skips it.
OTHER_ORGANISATION = "Aurora Streaming Network"
OTHER_ORGANISATION_DOCUMENT = "DR-041"

# The four documents whose file name carried a name, and the name the variant gives each.
RENAMED = {
    "DR-059": "data_room/04_Product_Data_and_Technology/Programme_Project_Brief.pdf.md",
    "DR-068": (
        "data_room/05_Security_IT_and_Infrastructure/Network_Quality_Ticket_Redacted.txt.md"
    ),
    "DR-069": (
        "data_room/05_Security_IT_and_Infrastructure/"
        "Workstream_Phase1_Technical_Findings_Draft.pdf.md"
    ),
    "DR-070": (
        "data_room/05_Security_IT_and_Infrastructure/Workstream_Executive_Summary_Final.pdf.md"
    ),
}

SKIP_NO_PIN = "runs/atlas/sections.jsonl absent; run phase 1 ingest first"
SKIP_NO_UNNAMED = "samples/atlas-unnamed has not been generated yet"

# One row of the README's table: | phrase | DR-001, DR-002 |
ROW = re.compile(r"^\|\s*(?P<phrase>[^|]+?)\s*\|\s*(?P<docs>[^|]*?)\s*\|$")
DOC_ID = re.compile(r"DR-\d{3}")
DIGITS = re.compile(r"\d+")

# Every removed name as one pattern, so a document can be read with its names taken out. A name
# is a whole token: neither a letter, a figure nor an underscore stands on either side of it.
GONE = re.compile(
    "|".join(
        (
            r"(?<![A-Za-z0-9_])AURORA(?![A-Za-z0-9_])",
            r"(?<![A-Za-z0-9_])NQ-?17(?![A-Za-z0-9_])",
            r"(?i:(?<![A-Za-z0-9_])Trust Reset(?![A-Za-z0-9_]))",
            r"(?i:(?<![A-Za-z0-9_])login friction(?![A-Za-z0-9_]))",
            r"(?i:(?<![A-Za-z0-9_])credential[- ]hygiene(?![A-Za-z0-9_]))",
            r"(?<![A-Za-z0-9_])legacy_uap_backup_2021\.tar\.gz",
            r"(?<![A-Za-z0-9_])vpauth-legacy-2019(?![A-Za-z0-9_])",
        )
    )
)

# What no text of the variant may read: an article twice, an article on an article, or one
# phrase written twice in a row.
DOUBLED = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bthe\s+the\b",
        r"\b(?:a|an)\s+the\b",
        *(rf"\b{re.escape(phrase)}\s+{re.escape(phrase)}\b" for phrase in PHRASES.values()),
    )
)


def generate(target: Path) -> int:
    """Runs the unnamed knob from sample 1's pinned sections into target."""
    return widen.main([KNOB, str(SOURCE_DIR), str(target), "--runs", str(ROOT / "runs")])


def needs_unnamed() -> None:
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)
    if not UNNAMED_DIR.exists():
        pytest.skip(SKIP_NO_UNNAMED)


def hits(text: str) -> list[str]:
    """Every removed name the text writes, read case insensitively.

    The publisher schedule's streaming organisation is taken out of the text before it is read,
    because its name is the workstream's codename in ordinary case and it is not the matter.
    """
    lowered = text.lower().replace(OTHER_ORGANISATION.lower(), " ")
    return [name for names in REMOVED.values() for name in names if name.lower() in lowered]


def variant_files() -> list[Path]:
    """Every file of the variant, of any kind, in path order."""
    return sorted(path for path in UNNAMED_DIR.rglob("*") if path.is_file())


def readme_rows() -> list[tuple[str, tuple[str, ...]]]:
    """Every (phrase, document ids) row of the README's phrases table."""
    rows = []
    for line in (UNNAMED_DIR / "README.md").read_text(encoding="utf-8").splitlines():
        match = ROW.match(line.strip())
        if not match:
            continue
        phrase = match["phrase"].strip("` ")
        if phrase.lower() in ("phrase", "") or set(phrase) <= {"-", ":", " "}:
            continue
        rows.append((phrase, tuple(DOC_ID.findall(match["docs"]))))
    return rows


def document_text(key, doc_id: str) -> str:
    return (UNNAMED_DIR / key.documents[doc_id]).read_text(encoding="utf-8")


def carried() -> dict[str, list[str]]:
    """The document ids sample 1 writes each identifier's names in, by the identifier's id."""
    source = load_key(SOURCE_DIR)
    texts = test_phase6.source_texts()
    found: dict[str, list[str]] = {name: [] for name in REMOVED}
    for doc_id, path in sorted(source.documents.items()):
        text = "\n".join(texts.get(path, ()))
        for name, names in REMOVED.items():
            for one in names:
                pattern = re.compile(
                    rf"(?<![A-Za-z0-9_]){re.escape(one)}(?![A-Za-z0-9_])",
                    0 if one == "AURORA" else re.IGNORECASE,
                )
                if pattern.search(text):
                    found[name].append(doc_id)
                    break
    return found


def written_beside_another_name() -> dict[str, set[str]]:
    """The documents in which every occurrence of an identifier's names stands beside another
    removed name, with nothing but whitespace, a bracket, a quote mark or a slash between them.

    Two names beside each other name one thing, so the room writes one phrase for the pair.
    """
    source = load_key(SOURCE_DIR)
    texts = test_phase6.source_texts()
    beside: dict[str, set[str]] = {name: set() for name in REMOVED}
    for doc_id, path in source.documents.items():
        text = "\n".join(texts.get(path, ()))
        spans = [match.span() for match in GONE.finditer(text)]
        touching: set[str] = set()
        alone: set[str] = set()
        for number, (start, end) in enumerate(spans):
            name = identifier_written(text[start:end])
            gaps = []
            if number:
                gaps.append(text[spans[number - 1][1] : start])
            if number + 1 < len(spans):
                gaps.append(text[end : spans[number + 1][0]])
            side = touching if any(not re.search(r"[A-Za-z0-9]", gap) for gap in gaps) else alone
            side.add(name)
        for name in touching - alone:
            beside[name].add(doc_id)
    return beside


def identifier_written(name: str) -> str:
    """The identifier id one written name belongs to."""
    for key, names in REMOVED.items():
        if any(one.lower() == name.lower() for one in names):
            return key
    raise AssertionError(name)


# ---------------------------------------------------------------- the knob


def test_the_knob_removes_seven_identifiers_and_writes_seven_phrases():
    """The knob names the seven identifiers this module names, with the same phrase for each and
    the same names removed for each."""
    from rlm.widen import unnamed

    assert {one.id: one.phrase for one in unnamed.IDENTIFIERS} == PHRASES
    assert {one.id: tuple(one.names) for one in unnamed.IDENTIFIERS} == REMOVED


# ---------------------------------------------------------------- the generator


def test_generator_writes_the_committed_unnamed_variant_byte_for_byte(tmp_path):
    """Regenerating the variant into a temporary directory gives the committed sample back."""
    needs_unnamed()

    assert generate(tmp_path / UNNAMED) == 0

    assert test_phase6.tree(tmp_path / UNNAMED) == test_phase6.tree(UNNAMED_DIR)


def test_generator_writes_the_same_bytes_twice(tmp_path):
    """Two runs of the knob write the same files: no draw, no model, no clock, no socket."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)

    assert generate(tmp_path / "one" / UNNAMED) == 0
    assert generate(tmp_path / "two" / UNNAMED) == 0

    assert test_phase6.tree(tmp_path / "one" / UNNAMED) == test_phase6.tree(
        tmp_path / "two" / UNNAMED
    )


def test_the_control_and_the_names_variants_are_unchanged(tmp_path):
    """The generator's two additions leave the variants of the earlier slices byte for byte as
    they are committed."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)
    for knob, name in (("control", "atlas-control"), ("names", "atlas-names")):
        directory = ROOT / "samples" / name
        if not directory.exists():
            continue
        assert widen.main([knob, str(SOURCE_DIR), str(tmp_path / name), "--runs",
                           str(ROOT / "runs")]) == 0
        assert test_phase6.tree(tmp_path / name) == test_phase6.tree(directory), name


# ---------------------------------------------------------------- the matter is named nowhere


def test_no_file_of_the_variant_holds_a_removed_name():
    """No file of the variant, of any kind, its path included, writes any of the seven names,
    read case insensitively."""
    needs_unnamed()
    files = variant_files()
    assert len(files) >= DOCUMENTS

    found = {}
    for path in files:
        relative = path.relative_to(UNNAMED_DIR).as_posix()
        written = hits(relative) + hits(path.read_text(encoding="utf-8"))
        if written:
            found[relative] = sorted(set(written))
    assert not found, found


def test_the_organisation_that_is_not_the_matter_is_untouched():
    """The publisher schedule's streaming organisation reads as sample 1 writes it: the knob
    removes the matter's names, not an organisation whose name resembles one."""
    needs_unnamed()
    key = load_key(UNNAMED_DIR)

    assert OTHER_ORGANISATION in document_text(key, OTHER_ORGANISATION_DOCUMENT)


def test_every_phrase_is_written_in_every_document_that_carried_its_identifier():
    """Each identifier's phrase stands in every document sample 1 wrote that identifier in, and
    the README's table lists those documents.

    One document is not asked for a phrase: where the room wrote a name beside another name,
    the two name one thing and one phrase is written for both, so the document reads the other
    identifier's phrase there and never the name.
    """
    needs_unnamed()
    key = load_key(UNNAMED_DIR)
    rooms = carried()
    beside = written_beside_another_name()
    rows = dict(readme_rows())
    assert set(rows) == set(PHRASES.values()), sorted(rows)

    for name, phrase in PHRASES.items():
        documents = rooms[name]
        assert documents, name
        assert list(rows[phrase]) == documents, name
        missing = [
            doc
            for doc in documents
            if phrase not in document_text(key, doc).lower() and doc not in beside[name]
        ]
        assert not missing, (name, missing)


def test_the_four_documents_whose_file_name_carried_a_name_are_renamed():
    """The four paths that carried a name are rewritten and every other path is the control's."""
    needs_unnamed()
    source = load_key(SOURCE_DIR)
    key = load_key(UNNAMED_DIR)

    assert set(key.documents) == set(source.documents)
    for doc_id, path in key.documents.items():
        wanted = RENAMED.get(doc_id, widen.markdown_path(source.documents[doc_id]))
        assert path == wanted, doc_id
        assert (UNNAMED_DIR / path).is_file(), doc_id


def test_dates_record_counts_and_amounts_are_untouched():
    """Every run of digits of every document is the source's, in the source's order, with the
    digits inside a removed name taken out. Two of the names carry a figure and nothing else
    the knob writes moves a date, a record count or an amount."""
    needs_unnamed()
    source = load_key(SOURCE_DIR)
    key = load_key(UNNAMED_DIR)
    texts = test_phase6.source_texts()

    for doc_id, path in source.documents.items():
        wanted = DIGITS.findall(GONE.sub(" ", "\n".join(texts[path])))
        got = DIGITS.findall(document_text(key, doc_id))
        assert got == wanted, doc_id


def test_the_identifier_facts_that_stay_are_written_in_their_own_documents():
    """The two organisations and the system the key names are untouched: each stands in every
    document its fact names."""
    needs_unnamed()
    key = load_key(UNNAMED_DIR)
    facts = {fact.id: fact for fact in key.facts}

    for name in KEPT_IDENTIFIERS:
        fact = facts[name]
        for doc in fact.documents:
            written = " ".join(document_text(key, doc).split())
            assert " ".join(fact.value.split()) in written, (name, doc)


def test_every_document_reads_back_with_the_source_section_count():
    """The knob rewrites text inside a section and never adds or drops one."""
    needs_unnamed()
    source = load_key(SOURCE_DIR)
    key = load_key(UNNAMED_DIR)
    texts = test_phase6.source_texts()

    for doc_id, path in source.documents.items():
        written = document_text(key, doc_id)
        blocks = [block for block in written.replace("\r\n", "\n").split("\n\n") if block.strip()]
        assert len(blocks) == len(texts[path]), doc_id


def test_no_text_of_the_variant_writes_an_article_twice_or_a_phrase_twice():
    """No file of the variant reads `the the`, `a the` or one phrase written twice in a row."""
    needs_unnamed()

    found = []
    for path in variant_files():
        text = " ".join(path.read_text(encoding="utf-8").split())
        for pattern in DOUBLED:
            for match in pattern.finditer(text):
                found.append((path.relative_to(UNNAMED_DIR).as_posix(), match.group(0)))
    assert not found, found


# ---------------------------------------------------------------- the key


def test_unnamed_key_holds_forty_eight_facts_and_the_readme_names_each_drop():
    """The five identifier facts whose value is a removed name are dropped, and the README names
    each drop with its id and why."""
    needs_unnamed()
    source = load_key(SOURCE_DIR)
    key = load_key(UNNAMED_DIR)
    readme = (UNNAMED_DIR / "README.md").read_text(encoding="utf-8")

    assert key.sample == UNNAMED
    assert len(key.facts) == FACTS
    assert [fact.id for fact in key.facts] == [
        fact.id for fact in source.facts if fact.id not in DROPPED
    ]
    for name in DROPPED:
        assert name in readme, name
    assert f"Facts: {FACTS}." in readme


def test_unnamed_key_facts_keep_their_shape():
    """Every kept fact keeps its id, kind, documents and phase. A quote fact's value stands in
    its first document, read with the whitespace a line wrap adds collapsed, as phase 1 and the
    grader read it. A fact whose value held no removed name keeps its value byte for byte."""
    needs_unnamed()
    source = {fact.id: fact for fact in load_key(SOURCE_DIR).facts}
    key = load_key(UNNAMED_DIR)

    for fact in key.facts:
        was = source[fact.id]
        assert fact.kind == was.kind, fact.id
        assert fact.documents == was.documents, fact.id
        assert fact.phase == was.phase, fact.id
        if not hits(was.value):
            assert fact.value == was.value, fact.id
        if fact.kind == "quote":
            written = " ".join(document_text(key, fact.documents[0]).split())
            assert " ".join(fact.value.split()) in written, fact.id


def test_unnamed_key_keeps_the_documents_the_decoys_the_answer_and_the_bar():
    """Only the paths, the facts and the first rubric row move; the rest of the key is
    sample 1's."""
    needs_unnamed()
    source = load_key(SOURCE_DIR)
    key = load_key(UNNAMED_DIR)

    assert len(key.documents) == DOCUMENTS
    assert key.required_documents == source.required_documents
    assert key.decoys == source.decoys
    assert key.answer == source.answer
    assert key.bar == source.bar


def test_rubric_row_one_names_the_incident_the_way_the_room_now_names_it():
    """Rubric row 1's earns text no longer writes a removed name, and every other row is
    sample 1's, unchanged."""
    needs_unnamed()
    source = load_key(SOURCE_DIR)
    key = load_key(UNNAMED_DIR)

    assert len(key.rubric) == len(source.rubric)
    first, was = key.rubric[0], source.rubric[0]
    assert (first.id, first.criterion, first.points) == (was.id, was.criterion, was.points)
    assert not hits(first.earns)
    assert first.earns != was.earns
    for phrase in ("workstream", "ticket", "programme", "archive"):
        assert phrase in first.earns, phrase
    assert key.rubric[1:] == source.rubric[1:]


def test_unnamed_brief_is_sample_ones_brief():
    """The knob adds no document and the brief names none of the seven, so the brief stands."""
    needs_unnamed()

    assert (UNNAMED_DIR / "brief.md").read_text(encoding="utf-8") == (
        SOURCE_DIR / "brief.md"
    ).read_text(encoding="utf-8")


# ---------------------------------------------------------------- the pinned digests


def test_unnamed_digests_are_pinned(tmp_path, capsys):
    """tests/phase6-unnamed-digests.json holds what phases 1 to 5 pin for the variant."""
    if not (ROOT / "runs" / UNNAMED / "grade.json").exists():
        pytest.skip("the chain has not run on the unnamed variant yet")
    if not DIGESTS_PATH.exists():
        pytest.skip("no unnamed digests pinned yet")

    wanted = test_phase6.pinned_digests(ROOT / "runs", UNNAMED, tmp_path)
    capsys.readouterr()

    assert json.loads(DIGESTS_PATH.read_text(encoding="utf-8")) == {UNNAMED: wanted}
