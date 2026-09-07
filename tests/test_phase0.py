"""Phase 0 tests. The key tests check that a sample's key.json is well formed and that every
document it names is a file in the sample. The grader tests check that the grader gives the
hand-written perfect report the key's perfect score and the wrong report less than its bar."""

import json
from pathlib import Path

import pytest

from rlm.grade import grade, normalise
from rlm.key import KINDS, load_key

ROOT = Path(__file__).resolve().parents[1]

# Counts and answers fixed by construction for the samples whose raw keys state them.
EXPECTED_ANSWER = {"atlas": (400, 375, 525)}
EXPECTED_COUNTS = {"atlas": (14, 5)}


@pytest.fixture
def key(sample_dir):
    return load_key(sample_dir)


def test_key_loads(key, sample):
    assert key.sample == sample
    assert key.documents
    assert key.facts


def test_key_documents_are_files(key, sample_dir):
    for doc_id, rel in key.documents.items():
        assert (sample_dir / rel).is_file(), f"{doc_id} -> {rel}"
    assert len(set(key.documents.values())) == len(key.documents)


def test_key_facts_resolve(key):
    ids = {f.id for f in key.facts}
    assert len(ids) == len(key.facts)
    for fact in key.facts:
        assert fact.kind in KINDS, fact.id
        assert fact.phase in range(1, 6), fact.id
        assert fact.documents, fact.id
        for doc in fact.documents:
            assert doc in key.documents, f"{fact.id} names {doc}"


def test_key_required_and_decoys_disjoint(key, sample):
    required = set(key.required_documents)
    decoys = {d.document for d in key.decoys}
    assert required <= set(key.documents)
    assert decoys <= set(key.documents)
    assert not required & decoys
    if sample in EXPECTED_COUNTS:
        assert (len(required), len(decoys)) == EXPECTED_COUNTS[sample]


def test_key_answer(key, sample):
    assert key.answer.low <= key.answer.number <= key.answer.high
    assert key.answer.unit
    if sample in EXPECTED_ANSWER:
        assert (key.answer.number, key.answer.low, key.answer.high) == EXPECTED_ANSWER[sample]


def test_key_rubric_and_bar(key):
    if key.rubric:
        assert sum(row.points for row in key.rubric) == 100
        assert [row.id for row in key.rubric] == list(range(1, len(key.rubric) + 1))
    assert key.bar.perfect == 100
    assert key.bar.wrong_under <= 40


def test_key_brief_exists(key, sample_dir):
    assert (sample_dir / key.brief).is_file()


# The grader tests. A sample with no hand-written fixture reports yet is skipped.

REPORTS = {"perfect": "report-perfect.md", "wrong": "report-wrong.md"}


def test_normalise_folds_units_separators_and_currency():
    assert normalise("912.8 million") == normalise("912.8m") == normalise("912.8 m")
    assert normalise("US$240m") == normalise("$240m") == normalise("240m")
    assert normalise("USD 240 million") == normalise("240m")
    assert normalise("1,200") == normalise("1200")
    assert normalise("  Bulk   EXPORT  is   probable ") == normalise("bulk export is probable")
    assert normalise("36 months") == "36 months"


def test_grade_seconds_positive_with_no_rubric(tmp_path, monkeypatch):
    """A sample with no rubric makes no model call, so grade() can finish inside a millisecond.
    The seconds it writes must still be a positive number, never a rounded-away zero."""
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    (sample_dir / "doc.txt").write_text("", encoding="utf-8")
    (sample_dir / "brief.md").write_text("brief", encoding="utf-8")
    key_data = {
        "sample": "mini",
        "brief": "brief.md",
        "documents": {"DOC-001": "doc.txt"},
        "required_documents": ["DOC-001"],
        "decoys": [],
        "facts": [
            {"id": "F1", "kind": "number", "value": "42", "documents": ["DOC-001"], "phase": 1}
        ],
        "answer": {"action": "invest", "number": 42, "low": 40, "high": 50, "unit": "m"},
        "rubric": [],
        "bar": {"perfect": 100, "wrong_under": 40},
    }
    (sample_dir / "key.json").write_text(json.dumps(key_data), encoding="utf-8")

    report_path = tmp_path / "report.md"
    report_path.write_text("DOC-001 shows 42.", encoding="utf-8")

    run_dir = tmp_path / "runs"

    # The first call to time.monotonic() returns 0.0, every call after it returns 0.001, so
    # the elapsed time is a fixed 0.001 seconds no matter how many times grade() reads the
    # clock. This makes the test deterministic and independent of machine speed.
    calls = {"count": 0}

    def fake_monotonic():
        value = 0.0 if calls["count"] == 0 else 0.001
        calls["count"] += 1
        return value

    monkeypatch.setattr("rlm.grade.time.monotonic", fake_monotonic)

    result = grade(sample_dir, report_path, run_dir, "grade-perfect.json")

    assert result["seconds"] > 0
    written = json.loads((run_dir / "grade-perfect.json").read_text(encoding="utf-8"))
    assert written == result


@pytest.fixture
def reports_dir(sample_dir):
    directory = sample_dir / "fixtures"
    for filename in REPORTS.values():
        if not (directory / filename).is_file():
            pytest.skip("no fixtures yet")
    return directory


@pytest.mark.parametrize("name", ["perfect", "wrong"])
def test_grade(name, key, sample, sample_dir, reports_dir, run_dir):
    ledger = ROOT / "LEDGER.md"
    before = ledger.read_bytes()

    result = grade(sample_dir, reports_dir / REPORTS[name], run_dir, f"grade-{name}.json")

    assert ledger.read_bytes() == before, "the grader must not write LEDGER.md"

    written = json.loads((run_dir / f"grade-{name}.json").read_text(encoding="utf-8"))
    assert written == result
    assert written["sample"] == sample
    assert set(written) == {
        "sample",
        "report",
        "recall",
        "recalled",
        "missed",
        "rubric",
        "score",
        "model",
        "seconds",
    }
    assert written["model"]
    assert written["seconds"] > 0
    assert len(written["recalled"]) + len(written["missed"]) == len(key.facts)
    assert len(written["rubric"]) == len(key.rubric)
    for row, expected in zip(written["rubric"], key.rubric):
        assert row["id"] == expected.id
        assert 0 <= row["points"] <= expected.points
        assert row["reason"]

    if name == "perfect":
        assert written["missed"] == []
        assert written["recall"] == 100.0
        assert written["score"] == key.bar.perfect
    else:
        assert written["score"] < key.bar.wrong_under
