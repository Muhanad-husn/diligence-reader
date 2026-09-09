"""Phase 6, the twice knob. `python -m rlm.widen twice samples/atlas samples/atlas-twice`
writes a variant of sample 1 whose room holds 200 documents: sample 1's hundred exactly as the
control writes them, and a hundred clones of a sister entity under
`data_room/09_Sister_Entity/` with the ids DR-201 to DR-300.

The clones carry none of the planted truth. Pass A clones the 81 documents that are neither
required nor decoys, with the names of column A, dates two years back, amounts times 1.37 and
identifiers suffixed `-SE`. Pass B clones the 19 largest of those 81 a second time, with the
names of column B, dates five years back, amounts times 0.61 and identifiers suffixed `-SG`, so
that 19 near duplicates do not stand in the room as a cluster of their own.

The folder, the ids, the two passes' constants, the names table and the counts the chain has to
hold are written out below, so this module is the specification and the knob is read against
it. The check that no planted value reaches a clone is written here too, from the key's own
rules, and is not the knob's own check. The harness of phases 1 to 5 on the variant is
tests/test_phase6.py, which picks the variant up from samples/atlas-twice/key.json.
"""

from __future__ import annotations

import datetime
import functools
import json
import re
from pathlib import Path

import pytest

import test_phase1
import test_phase6
from rlm import verify
from rlm import widen
from rlm.key import load_key

ROOT = Path(__file__).resolve().parents[1]

SOURCE = "atlas"
SOURCE_DIR = ROOT / "samples" / SOURCE
SOURCE_SECTIONS = ROOT / "runs" / SOURCE / "sections.jsonl"

KNOB = "twice"
TWICE = "atlas-twice"
TWICE_DIR = ROOT / "samples" / TWICE
DIGESTS_PATH = ROOT / "tests" / "phase6-twice-digests.json"

CONTROL_DIR = ROOT / "samples" / "atlas-control"

# The folder the sister entity's documents are written under, and the id the first clone takes.
FOLDER = "09_Sister_Entity"
FIRST_ID = "DR-201"

# What sample 1 carries, what each pass clones, and what the variant therefore carries.
SOURCE_DOCUMENTS = 100
CLONES = 81
SECOND_CLONES = 19
DOCUMENTS = SOURCE_DOCUMENTS + CLONES + SECOND_CLONES
FACTS = 53

# Pass A: the 81, ids DR-201 to DR-281.
SHIFT_YEARS = 2
FACTOR = 1.37
SUFFIX = "-SE"

# Pass B: the 19 largest of the 81 a second time, ids DR-282 to DR-300.
SECOND_SHIFT_YEARS = 5
SECOND_FACTOR = 0.61
SECOND_SUFFIX = "-SG"

# The two passes read by number, pass A first.
SHIFTS = (SHIFT_YEARS, SECOND_SHIFT_YEARS)
SUFFIXES = (SUFFIX, SECOND_SUFFIX)

# One row per name sample 1 uses: the name, the name pass A writes, the name pass B writes.
NAMES: tuple[tuple[str, str, str], ...] = (
    ("VistaPort", "Beaconvale", "Calderwood"),
    ("Northstar", "Eastridge", "Southgate"),
    ("AURORA", "BOREALIS", "ZEPHYR"),
    ("Trust Reset", "Confidence Rebuild", "Loyalty Restart"),
    ("IronLake", "Stonecreek", "Millbrook"),
    ("Juniper & Rowe", "Alder & Finch", "Birch & Kane"),
    ("Kestrel", "Osprey", "Harrier"),
)

# The two sections of the 81 that still carry a planted quote after the rewrites and are
# therefore dropped from their clone. Neither document is among the 19, so pass B drops none.
DROPPED_SECTIONS = 2

# The earlier slices' variants, which this slice leaves byte for byte as they are committed.
EARLIER = (
    ("control", "atlas-control"),
    ("names", "atlas-names"),
    ("unnamed", "atlas-unnamed"),
    ("second", "atlas-second"),
)

# An identifier, as the knob reads one: a word that carries a hyphen, an underscore, a dot or a
# slash inside it.
IDENTIFIER = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:[-_./][A-Za-z0-9]+)+\b")

# An ISO day, and a day month year surface that normalises to one.
ISO_DAY = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?\s+(\d{4})\b")
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

SKIP_NO_PIN = "runs/atlas/sections.jsonl absent; run phase 1 ingest first"
SKIP_NO_TWICE = "samples/atlas-twice has not been generated yet"


def generate(target: Path) -> int:
    """Runs the twice knob from sample 1's pinned sections into target."""
    return widen.main([KNOB, str(SOURCE_DIR), str(target), "--runs", str(ROOT / "runs")])


def needs_twice() -> None:
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)
    if not TWICE_DIR.exists():
        pytest.skip(SKIP_NO_TWICE)


# ---------------------------------------------------------------- what the knob clones


@functools.lru_cache(maxsize=1)
def source_key():
    """Sample 1's key, read once."""
    return load_key(SOURCE_DIR)


@functools.lru_cache(maxsize=1)
def source_texts() -> dict[str, tuple[str, ...]]:
    """The rendered text of every section of sample 1's pinned run, by document path."""
    return {doc: tuple(texts) for doc, texts in test_phase6.source_texts().items()}


def cloned_ids() -> list[str]:
    """The 81 document ids of sample 1 that are neither required nor decoys, ascending."""
    key = source_key()
    aside = set(key.required_documents) | {decoy.document for decoy in key.decoys}
    return sorted(set(key.documents) - aside)


def section_characters() -> dict[str, int]:
    """The total number of characters of each source document's section texts, by path."""
    return {doc: sum(len(text) for text in texts) for doc, texts in source_texts().items()}


def largest_ids(ids: list[str], count: int) -> list[str]:
    """The largest of these documents by section text characters, ties broken by ascending id,
    returned in ascending id order."""
    key = source_key()
    size = section_characters()
    ranked = sorted(ids, key=lambda one: (-size.get(key.documents[one], 0), one))
    return sorted(ranked[:count])


def clone_id(number: int) -> str:
    """The id the clone at this place in the run takes, counting from zero."""
    head, _, first = FIRST_ID.rpartition("-")
    return f"{head}-{int(first) + number:0{len(first)}d}"


def clones() -> list[tuple[str, str, int]]:
    """Every clone as its id, the id of the document it was cloned from, and its pass number:
    pass A's 81 in ascending source id order, then pass B's 19 in ascending source id order."""
    first = cloned_ids()
    second = largest_ids(first, SECOND_CLONES)
    run = [(clone_id(number), one, 0) for number, one in enumerate(first)]
    run += [(clone_id(len(first) + number), one, 1) for number, one in enumerate(second)]
    return run


def clone_path(clone: str, source_path: str) -> str:
    """The path one clone takes in the variant."""
    return f"{widen.ROOM}/{FOLDER}/{clone}_{source_path.rpartition('/')[2]}.md"


def source_of(clone: str, path: str) -> str:
    """The id of the document one clone was cloned from, read out of the clone's file name."""
    name = path.rpartition("/")[2][len(clone) + 1 : -len(".md")]
    by_name = {one.rpartition("/")[2]: doc for doc, one in source_key().documents.items()}
    return by_name[name]


def variant_text(path: str) -> str:
    """One file of the variant, read as utf-8 with its line endings folded to newlines."""
    return (TWICE_DIR / path).read_bytes().decode("utf-8").replace("\r\n", "\n")


def source_text(doc_id: str) -> str:
    """The section texts of one source document, joined the way a variant writes them."""
    return "\n\n".join(source_texts().get(source_key().documents[doc_id], ()))


def blocks(text: str) -> list[str]:
    """The blocks of one markdown file: the text split on a blank line, the empty ones out."""
    return [block for block in text.split("\n\n") if block.strip()]


# ---------------------------------------------------------------- what a clone may not carry


def spaced(value: str) -> str:
    """One value written as a pattern whose whitespace matches any whitespace."""
    return r"\s+".join(re.escape(part) for part in value.split())


def identifier_pattern(value: str) -> re.Pattern[str]:
    """A planted identifier as the check reads it: its whitespace free, its `&` free to carry
    spaces, and the match delimited so a suffix takes it out of reach."""
    body = r"\s*&\s*".join(spaced(part) for part in value.split("&"))
    return re.compile(rf"(?<![A-Za-z0-9&-]){body}(?![A-Za-z0-9-])", re.IGNORECASE)


def number_pattern(value: str) -> re.Pattern[str]:
    """A planted number as the check reads it: its whitespace free and the match delimited."""
    return re.compile(rf"(?<![\w.,$-]){spaced(value)}(?![\w.,-])", re.IGNORECASE)


def date_pattern(value: str) -> re.Pattern[str]:
    """A planted date as the check reads it: the ISO value, delimited."""
    return re.compile(rf"(?<![\w-]){re.escape(value)}(?![\w-])")


def date_surfaces(text: str) -> set[str]:
    """Every date this text writes, as the ISO day it normalises to."""
    found = set(ISO_DAY.findall(text))
    for day, month, year in DAY_MONTH_YEAR.findall(text):
        number = MONTHS.get(month.lower())
        if number is not None:
            found.add(f"{year}-{number:02d}-{int(day):02d}")
    return found


def planted(text: str, key) -> list[tuple[str, str]]:
    """Every planted value of the key this text carries, as the fact id and the surface found.

    A quote, a comparison and a document are read as a flattened lower cased substring. An
    identifier and a number are read delimited, so that a suffix or a factor takes them out of
    reach. A date is read as its ISO value delimited and as any date surface that normalises to
    it, so that a shift cannot land on a planted date by accident.
    """
    flat = test_phase1.flatten(text).lower()
    surfaces = date_surfaces(text)
    found = []
    for fact in key.facts:
        if fact.kind in ("quote", "comparison", "document"):
            wanted = test_phase1.flatten(fact.value).lower()
            if wanted in flat:
                found.append((fact.id, fact.value))
        elif fact.kind == "identifier":
            match = identifier_pattern(fact.value).search(text)
            if match:
                found.append((fact.id, match.group(0)))
        elif fact.kind == "number":
            match = number_pattern(fact.value).search(text)
            if match:
                found.append((fact.id, match.group(0)))
        elif fact.kind == "date":
            match = date_pattern(fact.value).search(text)
            if match:
                found.append((fact.id, match.group(0)))
            elif fact.value in surfaces:
                found.append((fact.id, fact.value))
    return found


def shifted(value: str, years: int) -> str:
    """One ISO day moved back by these years, a 29 February with no counterpart becoming the
    28th."""
    year, month, day = (int(part) for part in value.split("-"))
    try:
        moved = datetime.date(year - years, month, day)
    except ValueError:
        moved = datetime.date(year - years, month, day - 1)
    return moved.isoformat()


def name_pattern(name: str) -> re.Pattern[str]:
    """One name of the table as the room may write it: its words joined by a space, a hyphen or
    an underscore, its `&` free to carry spaces, the match delimited and the case free."""
    parts = [
        r"[\s_-]+".join(re.escape(word) for word in part.split()) for part in name.split("&")
    ]
    body = r"\s*&\s*".join(parts)
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.IGNORECASE)


def report_findings() -> list[tuple[str, set[str]]]:
    """The findings of the variant's report, in rank order, or a skip when it has none."""
    path = ROOT / "runs" / TWICE / "report.md"
    if not path.exists():
        pytest.skip("the chain has not written a report for the twice variant yet")
    found = verify.findings(path.read_text(encoding="utf-8"))
    if not found:
        pytest.skip("the report carries no findings section")
    return found


# ---------------------------------------------------------------- the knob


def test_the_knob_names_the_folder_the_first_id_and_the_two_passes():
    """The knob writes the clones under the folder this module names, gives the first clone the
    id this module names, and carries the two passes' shifts, factors and suffixes."""
    from rlm.widen import twice

    assert twice.NAME == KNOB
    assert twice.FOLDER == FOLDER
    assert twice.FIRST_ID == FIRST_ID
    assert twice.SHIFT_YEARS == SHIFT_YEARS
    assert twice.FACTOR == FACTOR
    assert twice.SUFFIX == SUFFIX
    assert twice.SECOND_SHIFT_YEARS == SECOND_SHIFT_YEARS
    assert twice.SECOND_FACTOR == SECOND_FACTOR
    assert twice.SECOND_SUFFIX == SECOND_SUFFIX


# ---------------------------------------------------------------- the generator


def test_generator_writes_the_committed_twice_variant_byte_for_byte(tmp_path):
    """Regenerating the variant into a temporary directory gives the committed sample back."""
    needs_twice()

    assert generate(tmp_path / TWICE) == 0

    assert test_phase6.tree(tmp_path / TWICE) == test_phase6.tree(TWICE_DIR)


def test_generator_writes_the_same_bytes_twice(tmp_path):
    """Two runs of the knob write the same files: no draw, no model, no clock, no socket."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)

    assert generate(tmp_path / "one" / TWICE) == 0
    assert generate(tmp_path / "two" / TWICE) == 0

    assert test_phase6.tree(tmp_path / "one" / TWICE) == test_phase6.tree(
        tmp_path / "two" / TWICE
    )


def test_the_earlier_variants_are_unchanged(tmp_path):
    """The generator's addition leaves the variants of the four earlier slices byte for byte as
    they are committed."""
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)

    for knob, name in EARLIER:
        directory = ROOT / "samples" / name
        if not directory.exists():
            continue
        argv = [knob, str(SOURCE_DIR), str(tmp_path / name), "--runs", str(ROOT / "runs")]
        assert widen.main(argv) == 0, name
        assert test_phase6.tree(tmp_path / name) == test_phase6.tree(directory), name


def test_the_generator_refuses_a_key_whose_fact_the_clones_cannot_avoid(tmp_path, capsys):
    """A key holding a value the clones cannot avoid stops the run before it writes a file.

    The temporary sample is sample 1's key and brief with one fact added, kind `identifier`,
    whose value is a word 55 of the 81 write and no rewrite reaches. The kind is `identifier`
    and not `quote` because a section carrying a planted quote is dropped from its clone, so a
    quote is not a value a clone cannot avoid.
    """
    if not SOURCE_SECTIONS.exists():
        pytest.skip(SKIP_NO_PIN)
    fake = tmp_path / SOURCE
    fake.mkdir()
    key = json.loads((SOURCE_DIR / "key.json").read_text(encoding="utf-8"))
    key["facts"] = list(key["facts"]) + [
        {
            "id": "cannot-avoid",
            "kind": "identifier",
            "value": "Confidential",
            "documents": ["DR-001"],
            "phase": 1,
        }
    ]
    (fake / "key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    (fake / key["brief"]).write_text(
        (SOURCE_DIR / key["brief"]).read_text(encoding="utf-8"), encoding="utf-8"
    )
    target = tmp_path / TWICE

    code = widen.main([KNOB, str(fake), str(target), "--runs", str(ROOT / "runs")])

    assert code == 2
    assert "cannot-avoid" in capsys.readouterr().out
    assert not target.exists()


# ---------------------------------------------------------------- the room


def test_the_room_holds_two_hundred_documents():
    """Every path of the key is a markdown file of the room and stands on disk."""
    needs_twice()

    key = load_key(TWICE_DIR)

    assert key.sample == TWICE
    assert len(key.documents) == DOCUMENTS
    for path in key.documents.values():
        assert path.startswith(f"{widen.ROOM}/") and path.endswith(".md"), path
        assert (TWICE_DIR / path).is_file(), path


def test_the_first_hundred_documents_are_the_controls():
    """Sample 1's hundred keep their ids and their paths, and each file is the control's own."""
    needs_twice()
    source = load_key(SOURCE_DIR)
    key = load_key(TWICE_DIR)

    ids = list(key.documents)
    assert ids[:SOURCE_DOCUMENTS] == list(source.documents)
    for doc_id, doc in source.documents.items():
        path = widen.markdown_path(doc)
        assert key.documents[doc_id] == path, doc_id
        if CONTROL_DIR.exists():
            assert (TWICE_DIR / path).read_bytes() == (CONTROL_DIR / path).read_bytes(), doc_id


def test_the_hundred_clones_take_their_ids_and_their_paths_in_order():
    """The clones are DR-201 to DR-300 in the order the two passes run, and each is written as
    the clone id and its source document's file name under the sister entity's folder."""
    needs_twice()
    source = load_key(SOURCE_DIR)
    key = load_key(TWICE_DIR)
    run = clones()

    assert len(run) == CLONES + SECOND_CLONES
    assert [clone for clone, _, _ in run] == list(key.documents)[SOURCE_DOCUMENTS:]
    assert run[0][0] == FIRST_ID
    for clone, doc_id, _ in run:
        assert key.documents[clone] == clone_path(clone, source.documents[doc_id]), clone


def test_pass_a_clones_the_eighty_one_that_are_neither_required_nor_decoys():
    """Pass A takes DR-201 to DR-281 and clones exactly the documents sample 1's key marks
    neither required nor a decoy, in ascending document id order."""
    needs_twice()
    key = load_key(TWICE_DIR)
    wanted = cloned_ids()

    assert len(wanted) == CLONES
    first = list(key.documents)[SOURCE_DOCUMENTS : SOURCE_DOCUMENTS + CLONES]
    assert [source_of(clone, key.documents[clone]) for clone in first] == wanted


def test_pass_b_clones_the_nineteen_largest_of_them():
    """Pass B takes DR-282 to DR-300 and clones the 19 of pass A's 81 with the most section
    text characters, ties broken by ascending id, written in ascending document id order."""
    needs_twice()
    key = load_key(TWICE_DIR)
    wanted = largest_ids(cloned_ids(), SECOND_CLONES)

    assert len(wanted) == SECOND_CLONES
    second = list(key.documents)[SOURCE_DOCUMENTS + CLONES :]
    assert [source_of(clone, key.documents[clone]) for clone in second] == wanted


def test_no_clone_carries_a_planted_value():
    """No file of the sister entity's folder carries a planted quote, comparison, document,
    identifier, number or date of sample 1's key, read by this module's own check."""
    needs_twice()
    source = load_key(SOURCE_DIR)
    key = load_key(TWICE_DIR)

    carried = []
    for clone, _, _ in clones():
        text = variant_text(key.documents[clone])
        carried += [(clone, fact_id, surface) for fact_id, surface in planted(text, source)]
    assert not carried, carried[:10]


def test_every_clone_shifts_its_source_documents_dates_back():
    """Each clone writes the dates of its source document moved back by its pass's years, and
    writes no other date."""
    needs_twice()
    key = load_key(TWICE_DIR)
    seen = [0, 0]

    for clone, doc_id, number in clones():
        was = set(ISO_DAY.findall(source_text(doc_id)))
        if not was:
            continue
        seen[number] += 1
        wanted = {shifted(one, SHIFTS[number]) for one in was}
        got = set(ISO_DAY.findall(variant_text(key.documents[clone])))
        assert got == wanted, (clone, sorted(got ^ wanted))
    assert seen[0] and seen[1], seen


def test_every_clone_suffixes_the_identifiers_it_writes():
    """No identifier a clone writes is an identifier of its source document, and every
    identifier a clone writes ends in its pass's suffix."""
    needs_twice()
    key = load_key(TWICE_DIR)

    for clone, doc_id, number in clones():
        suffix = SUFFIXES[number]
        was = set(IDENTIFIER.findall(source_text(doc_id)))
        got = set(IDENTIFIER.findall(variant_text(key.documents[clone])))
        assert not (got & was), (clone, sorted(got & was)[:5])
        assert all(one.endswith(suffix) for one in got), (
            clone,
            sorted(one for one in got if not one.endswith(suffix))[:5],
        )


def test_every_name_of_sample_one_is_gone_and_its_pass_name_is_there():
    """No clone writes a name of the table, and each pass writes its own name for it in at
    least one of its clones."""
    needs_twice()
    key = load_key(TWICE_DIR)
    texts = {
        clone: (number, variant_text(key.documents[clone])) for clone, _, number in clones()
    }

    for name, first, second in NAMES:
        gone = name_pattern(name)
        assert not [clone for clone, (_, text) in texts.items() if gone.search(text)], name
        for number, written in ((0, first), (1, second)):
            there = name_pattern(written)
            assert [
                clone
                for clone, (pass_number, text) in texts.items()
                if pass_number == number and there.search(text)
            ], written


# ---------------------------------------------------------------- the key


def test_the_key_is_sample_ones_key_with_the_clones_added():
    """The 53 facts, the required documents, the decoys, the answer, the rubric and the bar are
    sample 1's, and only the documents map grows."""
    needs_twice()
    source = load_key(SOURCE_DIR)
    key = load_key(TWICE_DIR)

    assert len(key.facts) == FACTS
    assert key.facts == source.facts
    assert key.required_documents == source.required_documents
    assert key.decoys == source.decoys
    assert key.answer == source.answer
    assert key.rubric == source.rubric
    assert key.bar == source.bar
    assert len(key.documents) == DOCUMENTS


# ---------------------------------------------------------------- the brief and the README


def test_the_brief_is_sample_ones_brief_with_one_paragraph_added():
    """Sample 1's brief stands as a prefix, and one paragraph is added at the end naming the
    sister entity's folder and the range of ids its documents take."""
    needs_twice()
    was = (SOURCE_DIR / "brief.md").read_text(encoding="utf-8")
    brief = (TWICE_DIR / "brief.md").read_text(encoding="utf-8")

    assert brief.startswith(was)
    added = brief[len(was) :]
    paragraphs = [block for block in added.split("\n\n") if block.strip()]
    assert len(paragraphs) == 1, paragraphs
    for said in (FOLDER, FIRST_ID, clone_id(CLONES + SECOND_CLONES - 1)):
        assert said in added, said


def test_the_readme_names_the_knob_and_counts_the_sections_it_dropped():
    """The README names the knob, drops no fact, counts sample 1's 53, and says how many
    sections it dropped for still carrying a planted quote."""
    needs_twice()
    key = load_key(TWICE_DIR)

    text = (TWICE_DIR / "README.md").read_text(encoding="utf-8")

    assert KNOB in text
    assert "Facts dropped: none" in text
    assert f"Facts: {FACTS}." in text
    dropped = sum(
        len(blocks(source_text(doc_id))) - len(blocks(variant_text(key.documents[clone])))
        for clone, doc_id, _ in clones()
    )
    assert dropped == DROPPED_SECTIONS
    assert re.search(rf"\b{DROPPED_SECTIONS} sections?\b", text), text


# ---------------------------------------------------------------- the chain


def test_the_first_finding_cites_sample_ones_matter():
    """The report leads with sample 1's matter: the first finding cites only documents of
    sample 1's hundred, and at least one of sample 1's fourteen required documents."""
    needs_twice()
    source = load_key(SOURCE_DIR)
    found = report_findings()

    _, cited = found[0]
    assert cited, found[0][0]
    assert cited <= set(source.documents), sorted(cited - set(source.documents))
    assert cited & set(source.required_documents), sorted(cited)


def test_no_finding_cites_a_clone():
    """The sister entity's documents carry no truth, so no finding of the report cites one."""
    needs_twice()
    cloned = {clone for clone, _, _ in clones()}
    found = report_findings()

    citing = [line for line, cited in found if cited & cloned]
    assert not citing, citing[:3]


# ---------------------------------------------------------------- the pinned digests


def test_twice_digests_are_pinned(tmp_path, capsys):
    """tests/phase6-twice-digests.json holds what phases 1 to 5 pin for the variant."""
    if not (ROOT / "runs" / TWICE / "grade.json").exists():
        pytest.skip("the chain has not run on the twice variant yet")
    if not DIGESTS_PATH.exists():
        pytest.skip("no twice digests pinned yet")

    wanted = test_phase6.pinned_digests(ROOT / "runs", TWICE, tmp_path)
    capsys.readouterr()

    assert json.loads(DIGESTS_PATH.read_text(encoding="utf-8")) == {TWICE: wanted}
