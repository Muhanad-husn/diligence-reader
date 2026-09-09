"""Phase 7 compare tests, sample 1 only.

The artefact is `runs/atlas-rlm/`. Code builds `corpus.txt` out of the pinned phase 5 run and
installs the upstream RLM skill into the checkout; the session runs `/rlm` twice on that corpus
with sample 1's brief as the query and saves the two reports; then `rlm.compare grade` grades
both reports against sample 1's key and writes `compare.json`, `manifest.json` and the digests.

These tests have two halves. The first half is unit work on small in-memory inputs and runs
whether or not the RLM has been run: the corpus builder's header and order, the ledger sum, the
spread, and which audit manifests name a corpus. The second half reads `runs/atlas-rlm/` off
disk and skips with a reason where it is absent.

The readout prints one line: the RLM's score a, score b, spread and seconds against ours.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from rlm import compare
from rlm.gateway import Ledger

ROOT = Path(__file__).resolve().parents[1]

# The sample this slice compares on, the run the RLM writes, and the pinned run it is put beside.
SAMPLE = "atlas"
RLM_RUN = "atlas-rlm"
SAMPLE_DIR = ROOT / "samples" / SAMPLE
OURS_RUN_DIR = ROOT / "runs" / SAMPLE
RLM_RUN_DIR = ROOT / "runs" / RLM_RUN

# The phase this slice belongs to, and the phase whose ledger rows are our dollars.
PHASE = 7
OURS_PHASE = 5

# The four files the digests pin, named the way compare writes them.
GRADED_FILES = ("report.md", "grade.json", "b/report.md", "b/grade.json")
DIGESTS_PATH = ROOT / "tests" / "phase7-rlm-digests.json"

# The six numbers compare.json carries for each side.
NUMBERS = ("score_a", "score_b", "spread", "recall_a", "seconds", "dollars")

SKIP_NO_CORPUS = "corpus.txt has not been built for the RLM run yet"
SKIP_NO_COMPARE = "the RLM has not been run and graded on sample 1 yet"
SKIP_NO_PINNED_RUN = "the pinned phase 5 run of sample 1 is not in this checkout"
SKIP_NO_DIGESTS = "no RLM reports pinned yet"


# ---------------------------------------------------------------- the skill and the ignore rule


def test_the_skill_sits_under_reference_at_the_upstream_commit():
    """reference/rlm-skill/skill/ is the upstream skill, and UPSTREAM_COMMIT names 0039c005."""
    source = compare.SKILL_SOURCE
    assert (source / "SKILL.md").is_file()
    assert (source / "scripts" / "rlm_repl.py").is_file()
    commit = (ROOT / "reference" / "rlm-skill" / "UPSTREAM_COMMIT").read_text(encoding="utf-8")
    assert commit.strip() == compare.SKILL_COMMIT
    assert compare.SKILL_COMMIT.startswith("0039c005")


def test_the_installed_skill_is_ignored_by_git():
    """.gitignore holds .claude/skills/, so the copy prepare installs is never committed."""
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".claude/skills/" in lines


def test_the_skill_is_installed_under_the_checkout_of_the_running_code():
    """The target is <checkout>/.claude/skills/rlm, where the checkout holds src/rlm."""
    assert compare.checkout() == ROOT
    assert compare.skill_target() == ROOT / ".claude" / "skills" / "rlm"


def test_install_skill_copies_every_file_of_the_source(tmp_path):
    """The installed tree holds the same relative paths and the same bytes as the source."""
    target = tmp_path / "skills" / "rlm"
    compare.install_skill(compare.SKILL_SOURCE, target)
    for path in sorted(compare.SKILL_SOURCE.rglob("*")):
        if not path.is_file():
            continue
        copied = target / path.relative_to(compare.SKILL_SOURCE)
        assert copied.read_bytes() == path.read_bytes()


def test_install_skill_replaces_an_older_copy(tmp_path):
    """A file left by an earlier install that the source does not hold is gone afterwards."""
    target = tmp_path / "skills" / "rlm"
    (target / "scripts").mkdir(parents=True)
    (target / "scripts" / "stale.py").write_text("old\n", encoding="utf-8")
    compare.install_skill(compare.SKILL_SOURCE, target)
    assert not (target / "scripts" / "stale.py").exists()
    assert (target / "SKILL.md").is_file()


# ---------------------------------------------------------------- the corpus builder


DOCUMENTS = {
    "DR-001": "data_room/00_Index/Index.xlsx",
    "DR-002": "data_room/01_Board/Minutes.pdf",
}

SECTIONS = [
    {"doc": "data_room/00_Index/Index.xlsx", "ordinal": 1, "text": "Project Atlas index"},
    {"doc": "data_room/00_Index/Index.xlsx", "ordinal": 2, "text": "VistaPort Media Inc."},
    {"doc": "data_room/01_Board/Minutes.pdf", "ordinal": 1, "text": "The board met."},
]


def test_corpus_writes_one_header_per_document_naming_the_id_and_the_path():
    """Each document opens with a header carrying its DR id and its path, and nothing else."""
    text = compare.build_corpus(DOCUMENTS, SECTIONS)
    headers = [line for line in text.splitlines() if line.startswith(compare.HEADER_MARK)]
    assert len(headers) == 2
    assert "DR-001" in headers[0] and "data_room/00_Index/Index.xlsx" in headers[0]
    assert "DR-002" in headers[1] and "data_room/01_Board/Minutes.pdf" in headers[1]


def test_corpus_carries_every_section_text_in_the_order_it_was_given():
    """The section texts follow their header in the order the sections arrive in."""
    text = compare.build_corpus(DOCUMENTS, SECTIONS)
    places = [text.index(section["text"]) for section in SECTIONS]
    assert places == sorted(places)
    assert text.endswith("\n")


def test_corpus_is_the_same_string_when_it_is_built_twice_from_the_same_sections():
    """Nothing in the builder reads a clock, a set order or the file system."""
    assert compare.build_corpus(DOCUMENTS, SECTIONS) == compare.build_corpus(DOCUMENTS, SECTIONS)


def test_corpus_drops_a_section_of_a_document_the_key_does_not_name():
    """A section whose document is not in the key has no header to sit under, so it is left out."""
    sections = SECTIONS + [{"doc": "notes/scratch.txt", "ordinal": 1, "text": "scratch"}]
    assert "scratch" not in compare.build_corpus(DOCUMENTS, sections)


# ---------------------------------------------------------------- the ledger sum and the spread


LEDGER_ROWS = [
    {"sample": "atlas", "phase": "5", "dollars": 0.0169},
    {"sample": "atlas", "phase": "5", "dollars": 0.0900},
    {"sample": "atlas", "phase": "2", "dollars": 1.0000},
    {"sample": "northwind", "phase": "5", "dollars": 2.0000},
    {"sample": "atlas-rlm", "phase": "7", "dollars": 3.0000},
]


def test_ledger_dollars_sums_the_rows_of_one_sample_and_one_phase():
    """Another sample's rows and another phase's rows are not in the sum."""
    assert compare.ledger_dollars(LEDGER_ROWS, "atlas", 5) == pytest.approx(0.1069)
    assert compare.ledger_dollars(LEDGER_ROWS, "atlas", 2) == pytest.approx(1.0)
    assert compare.ledger_dollars(LEDGER_ROWS, "atlas", 7) == 0.0


def test_spread_is_the_distance_between_the_two_scores():
    """The spread has no sign, and two equal scores spread nothing."""
    assert compare.spread(91.0, 88.0) == pytest.approx(3.0)
    assert compare.spread(88.0, 91.0) == pytest.approx(3.0)
    assert compare.spread(100.0, 100.0) == 0.0


# ---------------------------------------------------------------- the audit run contract


def _write_manifest(runs_root: Path, run_id: str, digest: str, started: float) -> None:
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "context_file_sha256": digest,
                "initialized_at": started,
                "updated_at": started + 100.0,
            }
        ),
        encoding="utf-8",
    )


def test_audit_runs_are_the_manifests_that_name_the_corpus_oldest_first(tmp_path):
    """A run over another context is not one of ours, and the older run is pass a."""
    corpus = tmp_path / "corpus.txt"
    corpus.write_text("hello\n", encoding="utf-8")
    digest = hashlib.sha256(corpus.read_bytes()).hexdigest()
    runs_root = tmp_path / "rlm_runs"
    _write_manifest(runs_root, "run_b", digest, 200.0)
    _write_manifest(runs_root, "run_a", digest, 100.0)
    _write_manifest(runs_root, "run_other", "0" * 64, 150.0)
    found = compare.audit_manifests(corpus, runs_root)
    assert [manifest["run_id"] for manifest in found] == ["run_a", "run_b"]


def test_rlm_seconds_is_the_wall_time_of_the_two_audit_runs():
    """Each run's seconds are its last step's time less the time its context was loaded."""
    manifests = [
        {"initialized_at": 100.0, "updated_at": 160.0},
        {"initialized_at": 200.0, "updated_at": 230.0},
    ]
    assert compare.rlm_seconds(manifests, {}) == pytest.approx(90.0)


def test_a_session_note_overrides_what_the_manifests_say():
    """What the session writes in session.json is taken as written."""
    note = {"seconds": 412.5}
    assert compare.rlm_seconds([{"initialized_at": 0.0, "updated_at": 1.0}], note) == 412.5


def test_models_come_from_the_session_note_before_the_defaults():
    """The root is the session and the leaf is the skill's claude -p, both nameable by the note."""
    assert compare.models({}) == {
        "root_model": compare.DEFAULT_ROOT_MODEL,
        "leaf_model": compare.DEFAULT_LEAF_MODEL,
    }
    named = compare.models({"root_model": "claude-opus-5", "leaf_model": "haiku"})
    assert named == {"root_model": "claude-opus-5", "leaf_model": "haiku"}


# ---------------------------------------------------------------- the corpus on disk


def _corpus_path() -> Path:
    return RLM_RUN_DIR / "corpus.txt"


def test_corpus_is_byte_identical_when_it_is_built_twice(tmp_path):
    """prepare's corpus, rebuilt into a fresh directory, is the same bytes."""
    if not _corpus_path().exists():
        pytest.skip(SKIP_NO_CORPUS)
    if not (OURS_RUN_DIR / "sections.jsonl").exists():
        pytest.skip(SKIP_NO_PINNED_RUN)
    again = compare.write_corpus(SAMPLE_DIR, OURS_RUN_DIR, tmp_path)
    assert again.read_bytes() == _corpus_path().read_bytes()


def test_corpus_carries_every_document_of_the_room_under_its_own_header():
    """One header per document the key names, in the order the sections arrive in."""
    if not _corpus_path().exists():
        pytest.skip(SKIP_NO_CORPUS)
    from rlm.key import load_key

    key = load_key(SAMPLE_DIR)
    text = _corpus_path().read_text(encoding="utf-8")
    headers = [line for line in text.splitlines() if line.startswith(compare.HEADER_MARK)]
    assert len(headers) == len(key.documents)
    for doc_id, path in key.documents.items():
        assert compare.header(doc_id, path) in headers


def test_corpus_carries_every_section_text_of_the_pinned_run():
    """Every section the pinned ingest wrote is in the corpus."""
    if not _corpus_path().exists():
        pytest.skip(SKIP_NO_CORPUS)
    if not (OURS_RUN_DIR / "sections.jsonl").exists():
        pytest.skip(SKIP_NO_PINNED_RUN)
    text = _corpus_path().read_text(encoding="utf-8")
    sections = compare.read_jsonl(OURS_RUN_DIR / "sections.jsonl")
    for section in sections:
        body = section["text"].strip()
        if body:
            assert body in text, section["anchor"]


# ---------------------------------------------------------------- compare.json and manifest.json


def _compare() -> dict:
    path = RLM_RUN_DIR / "compare.json"
    if not path.exists():
        pytest.skip(SKIP_NO_COMPARE)
    return json.loads(path.read_text(encoding="utf-8"))


def test_compare_holds_the_six_numbers_for_the_rlm_and_for_ours():
    """Both sides carry score a, score b, spread, recall a, seconds and dollars."""
    record = _compare()
    assert record["sample"] == SAMPLE
    for side in ("rlm", "ours"):
        assert set(record[side]) == set(NUMBERS), side
        for name in NUMBERS:
            assert isinstance(record[side][name], (int, float)), f"{side}.{name}"


def test_the_spread_of_each_side_is_the_distance_between_its_two_scores():
    """compare.json's own numbers agree with each other."""
    record = _compare()
    for side in ("rlm", "ours"):
        numbers = record[side]
        assert numbers["spread"] == pytest.approx(
            compare.spread(numbers["score_a"], numbers["score_b"])
        ), side


def test_the_rlm_run_spent_no_dollars():
    """It ran on the Claude Code subscription, so its dollars are zero."""
    assert _compare()["rlm"]["dollars"] == 0.0


def test_our_dollars_are_the_phase_five_rows_of_the_ledger_for_sample_one():
    """ours.dollars is the sum of every phase 5 atlas row LEDGER.md holds."""
    record = _compare()
    rows = Ledger(ROOT / "LEDGER.md").rows()
    assert record["ours"]["dollars"] == pytest.approx(
        compare.ledger_dollars(rows, SAMPLE, OURS_PHASE)
    )


def test_both_sides_took_time():
    """The RLM's seconds and ours are both above zero, so neither was read as a blank."""
    record = _compare()
    assert record["rlm"]["seconds"] > 0
    assert record["ours"]["seconds"] > 0


def test_manifest_names_the_models_the_commit_and_the_two_audit_runs():
    """manifest.json says what ran: the root, the leaf, the skill commit and both run ids."""
    path = RLM_RUN_DIR / "manifest.json"
    if not path.exists():
        pytest.skip(SKIP_NO_COMPARE)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["sample"] == SAMPLE
    assert manifest["skill_commit"] == compare.SKILL_COMMIT
    assert manifest["root_model"]
    assert manifest["leaf_model"]
    assert set(manifest["audit_runs"]) == {"a", "b"}
    assert manifest["audit_runs"]["a"] != manifest["audit_runs"]["b"]
    assert manifest["corpus_sha256"] == hashlib.sha256(_corpus_path().read_bytes()).hexdigest()


def test_both_reports_were_graded_against_sample_ones_key():
    """grade.json and b/grade.json name the sample and carry a score and a recall."""
    if not (RLM_RUN_DIR / "compare.json").exists():
        pytest.skip(SKIP_NO_COMPARE)
    for name in ("grade.json", "b/grade.json"):
        graded = json.loads((RLM_RUN_DIR / name).read_text(encoding="utf-8"))
        assert graded["sample"] == SAMPLE
        assert isinstance(graded["score"], (int, float))
        assert isinstance(graded["recall"], (int, float))


# ---------------------------------------------------------------- the ledger and the digests


def test_the_ledger_holds_no_phase_seven_row_for_the_rlm_run():
    """The comparison runs on the subscription, so it books nothing."""
    rows = Ledger(ROOT / "LEDGER.md").rows()
    booked = [row for row in rows if row["phase"] == str(PHASE) and row["sample"] == RLM_RUN]
    assert booked == []


def test_the_four_graded_files_carry_the_pinned_digests():
    """tests/phase7-rlm-digests.json holds the sha256 of both reports and both grades."""
    if not (RLM_RUN_DIR / "compare.json").exists():
        pytest.skip(SKIP_NO_COMPARE)
    if not DIGESTS_PATH.exists():
        pytest.skip(SKIP_NO_DIGESTS)
    digests = json.loads(DIGESTS_PATH.read_text(encoding="utf-8"))
    assert set(digests) == {RLM_RUN}
    assert set(digests[RLM_RUN]) == set(GRADED_FILES)
    for name in GRADED_FILES:
        got = hashlib.sha256((RLM_RUN_DIR / name).read_bytes()).hexdigest()
        assert got == digests[RLM_RUN][name], name


# ---------------------------------------------------------------- the readout


def readout(terminalreporter):
    """Writes one line: the RLM's score a, score b, spread and seconds against ours."""
    path = RLM_RUN_DIR / "compare.json"
    if not path.exists():
        return
    record = json.loads(path.read_text(encoding="utf-8"))
    rlm, ours = record["rlm"], record["ours"]
    terminalreporter.section("phase 7 readout")
    terminalreporter.write_line(
        f"phase 7 {record['sample']}: rlm {rlm['score_a']:g} / {rlm['score_b']:g}, "
        f"spread {rlm['spread']:g}, seconds {rlm['seconds']:.1f}, ${rlm['dollars']:.4f} "
        f"against ours {ours['score_a']:g} / {ours['score_b']:g}, "
        f"spread {ours['spread']:g}, seconds {ours['seconds']:.1f}, ${ours['dollars']:.4f}"
    )
