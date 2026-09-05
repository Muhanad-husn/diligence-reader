"""Phase 0 tests. The key tests check that a sample's key.json is well formed and that every
document it names is a file in the sample. The grader tests arrive in slice 02."""

import pytest

from rlm.key import KINDS, load_key

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
