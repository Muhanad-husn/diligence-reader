"""Phase 5 report tests. Code chooses the evidence and the model writes it up: build_digest
keeps about a hundred and fifty rows of the dossier's first matter, digest.md is the user
message of one model call, and report.md comes back with an executive summary, the findings
ranked by materiality, the most material issue quantified, the lesser issues and the open
items. These tests read the digest and the report off disk and check that the digest is
deterministic and holds every comparison row and every lesser matter the dossier kept, that
the schedule of evidence the code writes under the sixth heading is the same bytes twice and
every line of it ends in a citation on a dossier row, that the report carries the brief's five
headings in its order and then Evidence, with one trailing newline, that every sentence
outside the recommendation line and the Calculation lines ends in one or more citations, that
every citation names a document and an anchor that appear together on one row of the dossier,
that recall over the key's facts reads 100, and that LEDGER.md gained a phase 5 row for the
sample.

A citation is `[<doc> | <anchor>]`. A row of the dossier is any line the dossier writes under
one of its headings: the four field rows of Timeline, Names, Figures and the models section,
the triples of Comparisons joined by ` || `, and the rows of Lesser matters. A document and an
anchor go together when the dossier writes them on the same row.

A sentence is what the writer's own parse says it is, so the split is imported from rlm.write
rather than written again here: each body line, with its list marker dropped, is split on
sentence ending punctuation followed by whitespace, and a sentence is cited when its text,
with trailing whitespace and trailing sentence punctuation trimmed, ends in a citation.
Headings, blank lines, the recommendation line and the Calculation lines are not body lines.
A full stop inside a quotation ends nothing: the report quotes dossier rows whole and a row
often carries a full stop of its own, which is the room's punctuation and not the writer's,
so the split skips any position inside a pair of quotation marks.

The verifier reads the written report back against the room. verify.json holds one round per
model call the writer made, each round the failures of four checks: every citation parses,
names a document of index.jsonl and an anchor of sections.jsonl, and carries the DR id
map.json gives that path; every number of a cited sentence is in one of its cited sections,
and a Calculation line's operands are in the cited sentences of its own section; no cited
sentence's certainty word sits above the highest rung of its cited sections; and the first
finding cites a document of the dossier's first matter while no finding citing only lesser
matters comes before one that cites the set. These tests read verify.json off disk, recompute
it from the files on disk, and read the key's decoys to check that none of them is cited above
the first finding of the matter. The unit tests run each check on small in-memory inputs.

The rest of the tests run on a fake transport and need no key and no network: the default
model, a model outside the price table, the json flag of the gateway, the refusal when the
dossier, sections.jsonl or index.jsonl is absent, what build_messages puts in each message,
and the second call the writer makes when round one fails, which carries the first reply and
the failure list. One static test reads src/rlm/write.py and asserts that no line of it reads
the key, and another reads src/rlm/verify.py and asserts that it reads no key and makes no
call.

All three gate samples are enabled. Samples 2 and 3 carry no rubric, so their grade file
holds no rubric row and its score is the recall; every test that reads a rubric row reads the
key's own rubric and asks for nine rows only where the key has nine. A sample whose report.md
is absent is skipped.

The bake-off over the five models is tested on a fake transport and a fake grader: the order
inside a tier, the pro tier skipped when a flash model passes, the table written after each
model, the winner the cheapest passing row, and --recount and --dry-run making no call. The
pinning of the winner's two passes and the digest of the three pinned files are tested the
same way."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from rlm import pin
from rlm import verify as verifier
from rlm import write as writer
from rlm import writebakeoff
from rlm.carry import days_of, numbers_of, stem, words_of
from rlm.gateway import PRICES, Gateway, Ledger, price
from rlm.grade import CONNECTIVES, measure_recall, normalise, side_carried
from rlm.key import load_key
from rlm.notes import straighten
from rlm.sections import parse_anchor

ROOT = Path(__file__).resolve().parents[1]

# The samples this phase writes a report for. Slice 05 added samples 2 and 3.
ENABLED = ("atlas", "northwind", "northstar-dental")
SKIP_REASON = "report not written for this sample yet"

# The six second level headings: the brief's five deliverables in its order, and then the
# schedule of the room's own words, which code writes after the model has answered.
HEADINGS = (
    "Executive summary",
    "Findings ranked by materiality",
    "The most material issue quantified",
    "Lesser issues",
    "Open items",
    "Evidence",
)

# The model the writer calls when the command line names none.
MODEL = "z-ai/glm-5.3"

# What a ledger a fake run writes into starts as.
LEDGER_HEADER = (
    "# Ledger\n\n"
    "| date | sample | phase | model | tokens in | tokens out | dollars | balance |\n"
    "|---|---|---|---|---|---|---|---|\n"
)

_REPORTS: dict[str, "Report"] = {}


@dataclass(frozen=True)
class Report:
    """One sample's written report: the file, its text, its digest and its dossier."""

    path: Path
    text: str
    dossier: str
    digest: str


# ---------------------------------------------------------------- reading the artefacts back


@pytest.fixture
def report(sample, run_dir):
    """The report of one sample, read once and reused."""
    if sample not in ENABLED:
        pytest.skip(SKIP_REASON)
    path = run_dir / "report.md"
    dossier = run_dir / "dossier.md"
    if not path.exists() or not dossier.exists():
        pytest.skip(SKIP_REASON)
    digest = run_dir / "digest.md"
    if not digest.exists():
        pytest.skip(SKIP_REASON)
    if sample not in _REPORTS:
        _REPORTS[sample] = Report(
            path=path,
            text=path.read_text(encoding="utf-8"),
            dossier=dossier.read_text(encoding="utf-8"),
            digest=digest.read_text(encoding="utf-8"),
        )
    return _REPORTS[sample]


@pytest.fixture
def key(sample_dir):
    return load_key(sample_dir)


@pytest.fixture
def room(report, run_dir):
    """The sections, the index records and the DR id to path mapping of one run."""
    sections_path = run_dir / "sections.jsonl"
    index_path = run_dir / "index.jsonl"
    if not sections_path.exists() or not index_path.exists():
        pytest.skip(SKIP_REASON)
    return (
        verifier.read_jsonl(sections_path),
        verifier.read_jsonl(index_path),
        verifier.read_mapping(run_dir / "map.json"),
    )


@pytest.fixture
def verified(report, run_dir):
    """The verify.json the writer left, skipped when the report predates the verifier."""
    path = run_dir / "verify.json"
    if not path.exists():
        pytest.skip("verify.json not written for this sample yet")
    return json.loads(path.read_text(encoding="utf-8"))


def row_documents(line: str) -> set[str]:
    """The documents one dossier row names, whatever the room calls a document.

    Sample 1 writes a `DR-###` id in the document field and samples 2 and 3 write the file
    path, so the ids are read where a row has them and the writer's own field readers answer
    where it has none: the first field of each triple of a comparison row, the second field of
    a four field row.
    """
    ids = set(re.findall(r"DR-\d+", line))
    if ids:
        return ids
    if " || " in line:
        return {doc for doc in writer.comparison_documents(line) if doc}
    return {writer.row_document(line)} - {""}


def dossier_pairs(dossier: str) -> set[tuple[str, str]]:
    """Every document and anchor the dossier writes on one row, as a set of pairs.

    A row is a list line under a heading. The documents of a row are what row_documents reads
    off it and the anchors are the fields that carry a `#`, so a comparison row of several
    triples gives up every pair it writes.
    """
    found: set[tuple[str, str]] = set()
    for line in dossier.splitlines():
        if not line.startswith("- "):
            continue
        docs = row_documents(line)
        if not docs:
            continue
        anchors = set()
        for part in line[2:].split(" || "):
            for field in part.split(" | "):
                field = field.strip()
                if "#" in field:
                    anchors.add(field)
        for doc in docs:
            for anchor in anchors:
                found.add((doc, anchor))
    return found


def headings_of(text: str) -> list[str]:
    """The second level headings of the report, in file order."""
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


# ---------------------------------------------------------------- the artefact


def test_cited_sentences_count_a_citation_in_the_middle_of_a_sentence():
    """A citation written mid-sentence still names a section the sentence came from."""
    line = (
        "The draft shows \"$3,404m\" [DR-018 | a/b.pdf#p2l3] against the memo \"$240m\" "
        "[DR-088 | c/d.pdf#p1l56]. A second sentence cites once [DR-001 | e/f.pdf#p1l1]."
    )

    found = verifier.cited_sentences(line)

    assert [cites for _, cites in found] == [
        [("DR-018", "a/b.pdf#p2l3"), ("DR-088", "c/d.pdf#p1l56")],
        [("DR-001", "e/f.pdf#p1l1")],
    ]


def test_report_is_markdown_with_one_trailing_newline(report):
    assert report.text
    assert report.text.endswith("\n") and not report.text.endswith("\n\n")


def test_report_carries_the_six_headings_in_order(report):
    """The brief's five deliverables in its order, then the schedule of evidence."""
    assert headings_of(report.text) == list(HEADINGS)


def test_report_every_sentence_ends_in_a_citation(report):
    """Outside the recommendation line and the Calculation lines, nothing is uncited."""
    sentences = writer.sentences(report.text)
    assert len(sentences) >= 20, "the report is too short to be the whole matter"
    uncited = [sentence for sentence in sentences if not writer.is_cited(sentence)]
    assert not uncited, "uncited sentences: " + " || ".join(uncited[:10])


def test_report_every_citation_is_a_dossier_row(report):
    """A citation names a document and an anchor the dossier wrote on one row, not a new place."""
    citations = writer.citations(report.text)
    assert citations, "the report cites nothing"
    pairs = dossier_pairs(report.dossier)
    unknown = [pair for pair in citations if pair not in pairs]
    assert not unknown, "citations on no dossier row: " + " || ".join(
        f"[{doc} | {anchor}]" for doc, anchor in unknown[:10]
    )


def test_report_recall_over_the_key_is_100(report, key):
    """Every planted fact of the key is carried by the report, with one of its documents cited."""
    recall, _, missed = measure_recall(key, report.text)
    assert recall == 100.0, f"recall {recall}, missed {missed}"


def test_ledger_holds_a_phase_5_row_for_the_sample(report, sample):
    """The call that wrote the report paid for itself in LEDGER.md."""
    rows = Ledger(ROOT / "LEDGER.md").rows()
    phase_5 = [row for row in rows if row["phase"] == "5" and row["sample"] == sample]
    assert phase_5, f"no phase 5 ledger row for {sample}"


# ---------------------------------------------------------------- the verifier on the artefact


def test_verify_json_holds_one_round_per_call_and_passes(verified):
    """One round per model call, each a list of failures, and the last round is empty."""
    rounds = verified["rounds"]
    assert 1 <= len(rounds) <= 2
    for failures in rounds:
        assert isinstance(failures, list)
        for failure in failures:
            assert set(failure) >= {"check", "line", "reason"}
            assert failure["check"] in verifier.CHECKS
    assert verified["passes"] is True, f"last round: {rounds[-1][:5]}"
    assert not rounds[-1]


def test_verify_recomputed_from_the_files_on_disk_agrees(report, room, verified):
    """Running the verifier again on report.md, sections.jsonl and index.jsonl says the same."""
    sections, index, mapping = room
    result = verifier.verify(report.text, sections, index, report.dossier, mapping)
    assert result["passes"] is True, "failures: " + " || ".join(
        verifier.failure_line(failure) for failure in result["failures"][:10]
    )
    assert result["passes"] == verified["passes"]


def test_every_citation_of_the_report_resolves_to_a_section_and_a_document(report, room):
    """Every citation of all six sections parses, names an index document and a section."""
    sections, index, _ = room
    texts = verifier.section_index(sections)
    documents = verifier.index_documents(index)
    unknown = []
    for doc, anchor in writer.citations(report.text):
        parsed = parse_anchor(anchor)
        if anchor not in texts or parsed.doc not in documents:
            unknown.append(f"[{doc} | {anchor}]")
    assert not unknown, "citations that do not resolve: " + " || ".join(unknown[:10])


def test_a_second_round_kept_the_first_reply(report, verified):
    """Where the writer called twice, both raw replies are on disk and they differ."""
    if len(verified["rounds"]) < 2:
        pytest.skip("one round, so there is only one reply")
    run_dir = report.path.parent
    first = run_dir / "report-raw-1.txt"
    last = run_dir / "report-raw.txt"
    assert first.exists() and last.exists()
    assert first.read_text(encoding="utf-8") != last.read_text(encoding="utf-8")


def matter_documents(key) -> set[str]:
    """The documents of the matter, off the key.

    Sample 1 and sample 3 name them on a `matter-documents` fact. Sample 2 has no such fact,
    so the matter is every document its facts are planted in, less the decoys, which is the
    same set said the long way round.
    """
    named = {doc for fact in key.facts if fact.id == "matter-documents" for doc in fact.documents}
    if named:
        return named
    planted = {doc for fact in key.facts for doc in fact.documents}
    return planted - {decoy.document for decoy in key.decoys}


def test_no_decoy_is_cited_above_the_first_finding_of_the_matter(report, key):
    """A decoy ranked over the matter is the failure the room was built to catch."""
    matter = matter_documents(key)
    assert matter, "the key names no document of the matter"
    decoys = {decoy.document for decoy in key.decoys}
    findings = verifier.findings(report.text)
    assert findings, "the report ranks no findings"
    above = []
    for line, cited in findings:
        if cited & matter:
            break
        above.extend(f"{doc}: {line[:80]}" for doc in sorted(cited & decoys))
    assert not above, "decoys ranked above the matter: " + " || ".join(above[:5])


# ---------------------------------------------------------------- the digest


def test_digest_is_written_and_is_the_size_the_writer_prints(report):
    """digest.md is on disk and holds no more charged rows than DIGEST_ROWS allows.

    The lesser matters beyond LESSER_ROWS are the rows naming a document the matter does not
    hold, and the digest does not charge them against its room, so the file runs longer than
    DIGEST_ROWS by however many of them the dossier carries.
    """
    rows = [line for line in report.digest.splitlines() if line.startswith("- ")]
    assert rows
    lesser = writer.digest_sections(report.dossier).get("Lesser matters", [])
    uncharged = max(0, len(lesser) - writer.LESSER_ROWS)
    assert len(rows) - uncharged <= writer.DIGEST_ROWS
    assert report.digest.endswith("\n")


def test_digest_is_the_same_twice_from_the_same_dossier(report):
    """The digest is code and nothing else, so two builds of it are the same file."""
    first = writer.digest_markdown(report.dossier)
    second = writer.digest_markdown(report.dossier)
    assert first == second
    assert first == report.digest
    assert writer.build_digest(report.dossier) == writer.build_digest(report.dossier)


def test_digest_holds_every_comparison_row_of_the_dossier(report):
    """The comparisons are the matter contradicting itself, so none of them is dropped."""
    sections = writer.dossier_sections(report.dossier)
    for row in sections.get("Comparisons", []):
        assert row in report.digest, row[:120]


def test_digest_holds_the_lesser_matters_and_the_models(report):
    """The lesser matters go in largest first, and every model blind to the matter goes in."""
    sections = writer.dossier_sections(report.dossier)
    lesser = writer.quotable_first(sections.get("Lesser matters", []))
    for row in lesser[: writer.LESSER_ROWS]:
        assert row in report.digest, row[:120]
    for row in sections.get("Models blind to it", []):
        assert row in report.digest, row[:120]


def test_digest_gives_one_row_to_each_distinct_name(report):
    """Every name the dossier gives the matter reaches the digest once, and only once."""
    sections = writer.dossier_sections(report.dossier)
    names = writer.named_rows(sections.get("Names", []))
    assert len(names) == len({writer.row_fields(row)[0] for row in sections.get("Names", [])})
    for row in names:
        assert row in report.digest, row[:120]


def test_digest_rows_come_only_from_the_dossier(report):
    """A digest row is a dossier row, copied whole and not written."""
    dossier_rows = set()
    for rows in writer.dossier_sections(report.dossier).values():
        dossier_rows.update(rows)
    for row in writer.build_digest(report.dossier):
        assert row in dossier_rows, row[:120]


def test_evidence_section_is_the_same_twice_from_the_same_dossier(report):
    """The schedule is code and nothing else, so two builds of it are the same bytes."""
    first, cut = writer.evidence_within_reach(report.dossier)
    second, again = writer.evidence_within_reach(report.dossier)
    assert first.encode("utf-8") == second.encode("utf-8")
    assert cut == again
    assert first in report.text


def test_evidence_section_carries_every_comparison_and_lesser_matter(report):
    """Nothing drops a comparison or a lesser matter, whatever the schedule had to give up."""
    evidence, _ = writer.evidence_within_reach(report.dossier)
    sections = writer.dossier_sections(report.dossier)
    for row in sections.get("Comparisons", []):
        assert writer.comparison_line(row) in evidence, row[:100]
    for row in sections.get("Lesser matters", []):
        assert writer.evidence_line(row) in evidence, row[:100]
    for row in sections.get("Names", []):
        assert writer.evidence_line(row) in evidence, row[:100]


def test_every_evidence_line_ends_in_a_citation_on_a_dossier_row(report):
    """A schedule line is a dossier row written out, so its citation is that row's own."""
    evidence, _ = writer.evidence_within_reach(report.dossier)
    lines = [line for line in evidence.splitlines() if line.startswith("- ")]
    assert lines
    uncited = [line for line in lines if not writer.is_cited(line[2:])]
    assert not uncited, "uncited evidence lines: " + " || ".join(line[:80] for line in uncited[:5])
    pairs = dossier_pairs(report.dossier)
    unknown = [pair for pair in writer.citations(evidence) if pair not in pairs]
    assert not unknown, "evidence citations on no dossier row: " + " || ".join(
        f"[{doc} | {anchor}]" for doc, anchor in unknown[:5]
    )


def test_evidence_section_gives_each_document_its_own_heading(report):
    """Every document of the matter that has rows is a heading of the schedule, in rank order."""
    evidence, _ = writer.evidence_within_reach(report.dossier)
    headings = [line[4:].split(" | ")[0] for line in evidence.splitlines() if line.startswith("### ")]
    listed = [doc for doc, _, _ in writer.document_rows(report.dossier)]
    documents = [name for name in headings if name in listed]
    assert documents == [doc for doc in listed if doc in set(documents)]
    assert "Comparisons" in headings and "Lesser matters" in headings


# ---------------------------------------------------------------- the grade on the artefact

# The bar for the rubric score on sample 1, PLAN.md section 10, set by the founder for this
# phase. Samples 2 and 3 have no rubric, so rlm.grade.grade writes their recall as the score
# and the same bar reads as recall at or above 85.
RUBRIC_BAR = 85

# The keys every grade.json holds, as rlm.grade.grade writes them.
GRADE_KEYS = {"sample", "report", "recall", "recalled", "missed", "rubric", "score", "model", "seconds"}


@pytest.fixture
def graded(report, run_dir):
    """Pass a's grade.json, skipped when the report has not been graded yet."""
    path = run_dir / "grade.json"
    if not path.exists():
        pytest.skip("grade.json not written for this sample yet")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def pass_b(report, run_dir):
    """Pass b's directory, skipped when the writer ran once."""
    directory = run_dir / "b"
    if not (directory / "grade.json").exists():
        pytest.skip("pass b not written for this sample yet")
    return directory


def test_grade_json_holds_recall_the_rubric_the_score_the_model_and_the_seconds(graded, key):
    """The grader wrote every field, one rubric row per key row with points and a reason."""
    assert GRADE_KEYS <= set(graded)
    assert graded["sample"] == key.sample
    assert graded["report"] == "report.md"
    assert graded["recall"] == 100.0, f"missed {graded['missed']}"
    assert graded["missed"] == []
    assert len(graded["rubric"]) == len(key.rubric)
    for row, expected in zip(graded["rubric"], key.rubric):
        assert row["id"] == expected.id
        assert 0 <= row["points"] <= expected.points
        assert row["reason"].strip()
    if key.rubric:
        # Sample 1 is the sample with a rubric, and its rubric has nine rows.
        assert len(key.rubric) == 9
        assert graded["score"] == sum(row["points"] for row in graded["rubric"])
        assert graded["model"] and graded["model"] != "none"
    else:
        # Samples 2 and 3 have no rubric, so the score is the recall and no grader ran.
        assert graded["score"] == graded["recall"]
        assert graded["model"] == "none"
    assert graded["seconds"] > 0


def test_pass_a_rubric_score_is_at_or_above_the_bar(graded):
    """Pass a's score meets the phase 5 bar: the rubric total on sample 1, the recall on the
    two samples whose key carries no rubric."""
    reasons = " || ".join(
        f"{row['id']}: {row['points']} ({row['reason']})" for row in graded["rubric"]
    )
    assert graded["score"] >= RUBRIC_BAR, f"score {graded['score']}: {reasons}"


def test_pass_a_verifier_passes(graded, verified):
    """The report the grade was read off is the one the verifier passed."""
    assert verified["passes"] is True


def test_pass_b_holds_a_report_a_verify_json_and_a_grade_json(pass_b, key):
    """Pass b wrote the same three files under b/, and its grade has the same shape as pass a's."""
    for name in ("report.md", "verify.json", "grade.json"):
        assert (pass_b / name).exists(), f"pass b has no {name}"
    grade_b = json.loads((pass_b / "grade.json").read_text(encoding="utf-8"))
    assert GRADE_KEYS <= set(grade_b)
    assert grade_b["sample"] == key.sample
    assert len(grade_b["rubric"]) == len(key.rubric)
    if key.rubric:
        assert grade_b["score"] == sum(row["points"] for row in grade_b["rubric"])
    else:
        assert grade_b["score"] == grade_b["recall"]
    assert "spread" not in grade_b and "score_b" not in grade_b


def test_pass_a_grade_holds_the_spread_and_score_b(graded, pass_b):
    """The spread is the absolute difference of the two rubric scores, written into pass a."""
    grade_b = json.loads((pass_b / "grade.json").read_text(encoding="utf-8"))
    assert graded["score_b"] == grade_b["score"]
    assert graded["spread"] == abs(graded["score"] - grade_b["score"])


def test_pass_b_report_is_a_second_draw_of_the_same_request(pass_b, report):
    """Pass b's report carries the six headings and the same evidence schedule as pass a's."""
    text = (pass_b / "report.md").read_text(encoding="utf-8")
    assert headings_of(text) == list(HEADINGS)
    evidence_a = report.text.split(f"## {HEADINGS[-1]}", 1)[1]
    evidence_b = text.split(f"## {HEADINGS[-1]}", 1)[1]
    assert evidence_a == evidence_b


# The three files pin writes a digest of, per sample.
PINNED_FILES = ("report.md", "verify.json", "grade.json")


def test_report_digest_is_pinned(report, run_dir, sample):
    """The sha256 of report.md, verify.json and grade.json are the ones
    tests/phase5-digests.json holds."""
    path = ROOT / "tests" / "phase5-digests.json"
    if not path.exists():
        pytest.skip("no report pinned yet")
    digests = json.loads(path.read_text(encoding="utf-8"))
    assert sample in digests, f"{sample} has no pinned report digest"
    assert set(digests[sample]) == set(PINNED_FILES)
    for name in PINNED_FILES:
        got = hashlib.sha256((run_dir / name).read_bytes()).hexdigest()
        assert got == digests[sample][name], name


def test_ledger_holds_no_row_for_the_grader(report, sample):
    """Every phase 5 row names a gateway model; the grader runs on the subscription."""
    rows = Ledger(ROOT / "LEDGER.md").rows()
    phase_5 = [row for row in rows if row["phase"] == "5" and row["sample"] == sample]
    assert phase_5
    assert all(row["model"] in PRICES for row in phase_5), [row["model"] for row in phase_5]


# ---------------------------------------------------------------- the fake transport


def reply(text: str, tokens_in: int = 1000, tokens_out: int = 200) -> dict:
    """One canned chat completion body, shaped as the gateway reads it."""
    return {
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": tokens_in,
            "completion_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
        },
    }


class FakeTransport(httpx.MockTransport):
    """A transport that records every request and answers each with the next canned reply."""

    def __init__(self, replies: list[dict]):
        self.requests: list[httpx.Request] = []
        self._replies = list(replies)
        self._lock = threading.Lock()
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        with self._lock:
            self.requests.append(request)
            body = self._replies.pop(0)
        return httpx.Response(200, json=body)


FAKE_REPORT = """## Executive summary

Recommendation: reprice by $400m.
The room contradicts itself [DR-001 | a/b.pdf#p1l1].

## Findings ranked by materiality

The draft says one thing [DR-001 | a/b.pdf#p1l1].

## The most material issue quantified

The exposure is a range of $240m to $465m [DR-001 | a/b.pdf#p1l1].
Calculation: ($240m + $465m) / 2 = $352.5m, rounded to $400m, range $240m to $465m.
Recommendation: reprice by $400m.

## Lesser issues

The tax memo is smaller [DR-002 | c/d.pdf#p2l1].

## Open items

The final report is outstanding [DR-001 | a/b.pdf#p1l1].
"""

# The same report with one number the room never wrote, which is one numbers failure.
FAKE_REPORT_WITH_A_BAD_NUMBER = FAKE_REPORT.replace(
    "The exposure is a range of $240m to $465m",
    "The exposure is a range of $240m to $999m",
)

# The two sections of the fake room, holding the words and the numbers the fake report cites.
FAKE_SECTIONS = [
    {
        "anchor": "a/b.pdf#p1l1",
        "doc": "a/b.pdf",
        "kind": "line",
        "cells": [],
        "text": "The room contradicts itself: the exposure runs $240m to $465m.",
    },
    {
        "anchor": "c/d.pdf#p2l1",
        "doc": "c/d.pdf",
        "kind": "line",
        "cells": [],
        "text": "The tax memo is smaller than the rest.",
    },
]

FAKE_INDEX = [
    {"docs": ["a/b.pdf"], "surface": "240", "kind": "amount"},
    {"docs": ["c/d.pdf"], "surface": "12", "kind": "amount"},
]

FAKE_MAP = {
    "documents": [
        {"doc": "DR-001", "path": "a/b.pdf"},
        {"doc": "DR-002", "path": "c/d.pdf"},
    ]
}

FAKE_DOSSIER = (
    "# Dossier: atlas\n\n## Matter 1\n\n### Documents\n\n"
    "- 1. DR-001 | A draft memo | 03_Commercial | 2025-10-18\n\n"
    "### Timeline\n\n"
    "- 2025-10-18 | DR-001 | a quote | a/b.pdf#p1l1\n\n"
    "### Names\n\n- AURORA | DR-001 | a name | a/b.pdf#p1l2\n\n"
    "### Comparisons\n\n"
    "- DR-001 | one half | a/b.pdf#p1l3 || DR-002 | the other half | c/d.pdf#p2l1\n\n"
    "### Lesser matters\n\n- 1 | DR-002 | a smaller thing | c/d.pdf#p2l1\n"
)


def write_jsonl(path: Path, records: list[dict]) -> None:
    """Writes one JSON object per line, as the room's artefacts are written."""
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8"
    )


@pytest.fixture
def fake_sample(tmp_path):
    """A sample directory with a brief, a run directory with the room, and an empty ledger."""
    sample_dir = tmp_path / "atlas"
    run_dir = tmp_path / "run"
    sample_dir.mkdir()
    run_dir.mkdir()
    (sample_dir / "brief.md").write_text("# Brief\n\nFind the matter.\n", encoding="utf-8")
    (run_dir / "dossier.md").write_text(FAKE_DOSSIER, encoding="utf-8")
    write_jsonl(run_dir / "sections.jsonl", FAKE_SECTIONS)
    write_jsonl(run_dir / "index.jsonl", FAKE_INDEX)
    (run_dir / "map.json").write_text(json.dumps(FAKE_MAP, indent=1) + "\n", encoding="utf-8")
    ledger_path = tmp_path / "LEDGER.md"
    ledger_path.write_text(LEDGER_HEADER, encoding="utf-8")
    return sample_dir, run_dir, Ledger(ledger_path)


def test_write_default_model_is_glm_5_3(fake_sample):
    """Without --model the call goes to z-ai/glm-5.3 and the report lands on disk."""
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)

    assert writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger) == 0

    assert writer.DEFAULT_MODEL == MODEL
    body = json.loads(transport.requests[0].content)
    assert body["model"] == MODEL
    assert body["max_tokens"] == writer.MAX_OUTPUT_TOKENS == 12000
    written = (run_dir / "report.md").read_text(encoding="utf-8")
    assert written.startswith("## Executive summary")
    assert f"## {writer.EVIDENCE_HEADING}" in written
    assert (run_dir / "report-raw.txt").read_text(encoding="utf-8") == FAKE_REPORT


def test_write_takes_any_model_of_the_price_table(fake_sample):
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)

    code = writer.main(
        [str(sample_dir), str(run_dir), "--model", "deepseek/deepseek-v4-pro"],
        gateway=gateway,
        ledger=ledger,
    )

    assert code == 0
    assert json.loads(transport.requests[0].content)["model"] == "deepseek/deepseek-v4-pro"


def test_write_refuses_a_model_outside_the_price_table(fake_sample, capsys):
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)

    code = writer.main(
        [str(sample_dir), str(run_dir), "--model", "acme/not-a-model"],
        gateway=gateway,
        ledger=ledger,
    )

    assert code != 0
    assert "acme/not-a-model" in capsys.readouterr().out
    assert not transport.requests
    assert not (run_dir / "report.md").exists()
    assert "acme/not-a-model" not in PRICES


def test_write_refuses_when_the_dossier_is_absent(fake_sample, capsys):
    sample_dir, run_dir, ledger = fake_sample
    (run_dir / "dossier.md").unlink()
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)

    code = writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger)

    assert code != 0
    assert "dossier" in capsys.readouterr().out
    assert not transport.requests
    assert not (run_dir / "report.md").exists()
    assert ledger.rows() == []


def test_write_records_one_phase_5_ledger_row(fake_sample):
    """One call, one row, with the tokens the gateway reported."""
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport([reply(FAKE_REPORT, tokens_in=1234, tokens_out=56)])
    gateway = Gateway(api_key="test-key", transport=transport)

    assert writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger) == 0

    rows = ledger.rows()
    assert len(rows) == 1
    assert rows[0]["phase"] == "5"
    assert rows[0]["sample"] == "atlas"
    assert rows[0]["tokens_in"] == 1234
    assert rows[0]["tokens_out"] == 56


def test_write_prints_the_estimate_before_the_call(fake_sample, capsys):
    """Ledger.batch prints the estimated tokens and the price, and it prints before the post."""
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)

    writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger)

    printed = capsys.readouterr().out
    assert "estimate:" in printed
    assert "tokens in" in printed and MODEL in printed
    assert printed.index("estimate:") < printed.index("write atlas:")


def test_write_prints_one_readout_line(fake_sample, capsys):
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport([reply(FAKE_REPORT, tokens_in=1234, tokens_out=56)])
    gateway = Gateway(api_key="test-key", transport=transport)

    writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger)

    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith("write atlas:")]
    assert len(lines) == 1
    assert "sentences" in lines[0] and "citations" in lines[0]
    assert "tokens_in 1234" in lines[0] and "tokens_out 56" in lines[0]


# ---------------------------------------------------------------- the verifier inside the writer


def test_write_writes_verify_json_with_one_round_when_the_report_verifies(fake_sample, capsys):
    """A report that verifies costs one call, and verify.json holds that one round."""
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)

    assert writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger) == 0

    assert len(transport.requests) == 1
    record = json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))
    assert record["sample"] == "atlas"
    assert record["calls"] == 1
    assert record["rounds"] == [[]]
    assert record["passes"] is True
    assert not (run_dir / "report-raw-1.txt").exists()
    assert "verify atlas round 1: citations 0, numbers 0, certainty 0, order 0" in capsys.readouterr().out


def test_write_sends_the_failures_back_once_and_keeps_both_replies(fake_sample):
    """Round one's failures go back with the first reply, and report.md is the second reply."""
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport(
        [reply(FAKE_REPORT_WITH_A_BAD_NUMBER), reply(FAKE_REPORT, tokens_in=10, tokens_out=20)]
    )
    gateway = Gateway(api_key="test-key", transport=transport)

    assert writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger) == 0

    assert len(transport.requests) == 2
    first = json.loads(transport.requests[0].content)["messages"]
    second = json.loads(transport.requests[1].content)["messages"]
    assert second[:2] == first
    assert second[2] == {"role": "assistant", "content": FAKE_REPORT_WITH_A_BAD_NUMBER}
    assert second[3]["role"] == "user"
    assert "numbers:" in second[3]["content"]
    assert "999" in second[3]["content"]

    record = json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))
    assert len(record["rounds"]) == 2
    assert record["calls"] == 2
    assert [failure["check"] for failure in record["rounds"][0]] == ["numbers"]
    assert record["rounds"][1] == []
    assert record["report_round"] == 2
    assert record["passes"] is True

    assert (run_dir / "report-raw-1.txt").read_text(encoding="utf-8") == FAKE_REPORT_WITH_A_BAD_NUMBER
    assert (run_dir / "report-raw.txt").read_text(encoding="utf-8") == FAKE_REPORT
    written = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "$999m" not in written and "$240m to $465m" in written


def test_write_keeps_the_first_reply_when_the_second_is_cut_short(fake_sample, capsys):
    """A second reply that lost headings was cut at the cap, so report.md is the first reply."""
    sample_dir, run_dir, ledger = fake_sample
    cut_short = FAKE_REPORT.split("## The most material issue quantified")[0]
    transport = FakeTransport([reply(FAKE_REPORT_WITH_A_BAD_NUMBER), reply(cut_short)])
    gateway = Gateway(api_key="test-key", transport=transport)

    assert writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger) == 0

    assert len(transport.requests) == 2
    record = json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))
    assert len(record["rounds"]) == 2
    assert record["report_round"] == 1
    assert record["passes"] is False
    written = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "$999m" in written
    assert headings_of(written) == list(HEADINGS)
    assert (run_dir / "report-raw.txt").read_text(encoding="utf-8") == cut_short
    assert "second reply cut short" in capsys.readouterr().out
    assert not writer.is_whole(cut_short) and writer.is_whole(FAKE_REPORT)


def test_write_sums_both_calls_into_one_ledger_row(fake_sample):
    """Two calls inside one batch write one phase 5 row carrying the tokens of both."""
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport(
        [
            reply(FAKE_REPORT_WITH_A_BAD_NUMBER, tokens_in=1000, tokens_out=100),
            reply(FAKE_REPORT, tokens_in=200, tokens_out=30),
        ]
    )
    gateway = Gateway(api_key="test-key", transport=transport)

    writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger)

    rows = ledger.rows()
    assert len(rows) == 1
    assert rows[0]["tokens_in"] == 1200
    assert rows[0]["tokens_out"] == 130
    summary = json.loads((run_dir / "write-summary.json").read_text(encoding="utf-8"))
    assert summary["calls"] == 2
    assert summary["verify_failures"] == 0
    assert summary["tokens_in"] == 1200 and summary["tokens_out"] == 130


def test_write_refuses_when_the_sections_are_absent(fake_sample, capsys):
    """Without sections.jsonl there is nothing to verify against, so nothing is sent."""
    sample_dir, run_dir, ledger = fake_sample
    (run_dir / "sections.jsonl").unlink()
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)

    code = writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger)

    assert code == 2
    assert "no sections.jsonl at" in capsys.readouterr().out
    assert not transport.requests
    assert not (run_dir / "report.md").exists()
    assert ledger.rows() == []


def test_write_refuses_when_the_index_is_absent(fake_sample, capsys):
    sample_dir, run_dir, ledger = fake_sample
    (run_dir / "index.jsonl").unlink()
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)

    code = writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger)

    assert code == 2
    assert "no index.jsonl at" in capsys.readouterr().out
    assert not transport.requests


def test_write_from_a_saved_reply_verifies_once_and_makes_no_call(fake_sample):
    """--from-reply rebuilds the report, verifies it once and sends nothing."""
    sample_dir, run_dir, ledger = fake_sample
    saved = run_dir / "saved-reply.txt"
    saved.write_text(FAKE_REPORT_WITH_A_BAD_NUMBER, encoding="utf-8")
    transport = FakeTransport([])
    gateway = Gateway(api_key="test-key", transport=transport)

    code = writer.main(
        [str(sample_dir), str(run_dir), "--from-reply", str(saved)], gateway=gateway, ledger=ledger
    )

    assert code == 0
    assert not transport.requests
    record = json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))
    assert len(record["rounds"]) == 1
    assert record["passes"] is False
    assert record["calls"] == 0


# ---------------------------------------------------------------- the gateway json flag


def test_gateway_complete_keeps_response_format_by_default():
    transport = FakeTransport([reply('{"a": 1}')])
    gateway = Gateway(api_key="test-key", transport=transport)

    gateway.complete(MODEL, [{"role": "user", "content": "u"}], max_tokens=100)

    body = json.loads(transport.requests[0].content)
    assert body["response_format"] == {"type": "json_object"}


def test_gateway_complete_drops_response_format_when_json_is_false():
    transport = FakeTransport([reply("# a report")])
    gateway = Gateway(api_key="test-key", transport=transport)

    completion = gateway.complete(MODEL, [{"role": "user", "content": "u"}], max_tokens=100, json=False)

    body = json.loads(transport.requests[0].content)
    assert "response_format" not in body
    assert body["temperature"] == 0 and body["seed"] == 0
    assert body["reasoning"] == {"effort": "low"}
    assert completion.text == "# a report"


def test_write_asks_the_gateway_for_prose_not_json(fake_sample):
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)

    writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger)

    assert "response_format" not in json.loads(transport.requests[0].content)


# ---------------------------------------------------------------- the prompt and the parse


def test_build_messages_carries_the_headings_and_the_whole_digest():
    """The five headings are in the instructions and the digest is the user message, whole."""
    brief = "# Brief\n\nFind the matter.\n"
    dossier = "# Digest\n\n### Timeline\n\n- 2025-10-18 | DR-001 | a quote | a/b.pdf#p1l1\n"

    messages = writer.build_messages(brief, dossier)

    assert [message["role"] for message in messages] == ["system", "user"]
    for heading in HEADINGS:
        assert f"## {heading}" in messages[0]["content"]
    assert "[<doc> | <anchor>]" in messages[0]["content"]
    assert "Recommendation:" in messages[0]["content"]
    assert "Calculation:" in messages[0]["content"]
    assert brief in messages[0]["content"]
    assert messages[1]["content"] == dossier


def test_parse_reply_drops_a_fence_and_anything_before_the_first_heading():
    raw = "```markdown\nHere is the report.\n\n## Executive summary\n\nRecommendation: hold.\n```"

    parsed = writer.parse_reply(raw)

    assert parsed.startswith("## Executive summary\n")
    assert parsed.endswith("\n") and not parsed.endswith("\n\n")
    assert "```" not in parsed and "Here is the report." not in parsed


def test_sentences_skip_the_headings_the_recommendation_and_the_calculation():
    text = (
        "## Executive summary\n\n"
        "Recommendation: reprice by $400m.\n"
        "The room says one thing [DR-001 | a/b.pdf#p1l1]. It says another [DR-002 | c/d.pdf#p1l2].\n"
        "- A bullet also counts [DR-003 | e/f.pdf#p1l3].\n"
        "Calculation: 240 + 465 / 2 = 400, range 375 to 525.\n"
    )

    found = writer.sentences(text)

    assert found == [
        "The room says one thing [DR-001 | a/b.pdf#p1l1].",
        "It says another [DR-002 | c/d.pdf#p1l2].",
        "A bullet also counts [DR-003 | e/f.pdf#p1l3].",
    ]
    assert all(writer.is_cited(sentence) for sentence in found)
    assert not writer.is_cited("A sentence with no citation.")
    assert not writer.is_cited("A sentence citing nothing [DR-001].")


def test_sentences_do_not_break_on_a_full_stop_inside_a_quotation():
    """A quoted row carries the room's own full stops, and those end no sentence of ours."""
    text = (
        "## Findings ranked by materiality\n\n"
        'The draft says "It is probable. The volume agrees" [DR-001 | a/b.pdf#p1l1]. '
        'The final says "no determination" [DR-002 | c/d.pdf#p1l2].\n'
    )

    found = writer.sentences(text)

    assert found == [
        'The draft says "It is probable. The volume agrees" [DR-001 | a/b.pdf#p1l1].',
        'The final says "no determination" [DR-002 | c/d.pdf#p1l2].',
    ]
    assert all(writer.is_cited(sentence) for sentence in found)


def test_sentences_do_not_break_inside_a_common_abbreviation():
    """An abbreviation carries a full stop of its own and that full stop ends no sentence."""
    text = (
        "## Findings ranked by materiality\n\n"
        "Invoice No. 4471 was paid in full [DR-001 | a/b.pdf#p1l1].\n"
        "The processor is TelemetryWorks Inc. in Portland [DR-002 | c/d.pdf#p1l2].\n"
    )

    found = writer.sentences(text)

    assert found == [
        "Invoice No. 4471 was paid in full [DR-001 | a/b.pdf#p1l1].",
        "The processor is TelemetryWorks Inc. in Portland [DR-002 | c/d.pdf#p1l2].",
    ]
    assert all(writer.is_cited(sentence) for sentence in found)


def test_sentences_still_break_at_a_real_sentence_end_on_a_line_holding_an_abbreviation():
    """The abbreviation rule keeps every full stop that does end a sentence."""
    text = (
        "## Findings ranked by materiality\n\n"
        "The processor is TelemetryWorks Inc. in Portland [DR-001 | a/b.pdf#p1l1]. "
        "The transfer mechanism is none [DR-002 | c/d.pdf#p1l2].\n"
    )

    found = writer.sentences(text)

    assert found == [
        "The processor is TelemetryWorks Inc. in Portland [DR-001 | a/b.pdf#p1l1].",
        "The transfer mechanism is none [DR-002 | c/d.pdf#p1l2].",
    ]
    assert all(writer.is_cited(sentence) for sentence in found)


def test_the_abbreviations_are_a_module_constant_of_the_split():
    """The list the split reads is one constant, and a single letter is an initial."""
    assert set(writer.ABBREVIATIONS) >= {
        "no.",
        "nos.",
        "inc.",
        "ltd.",
        "co.",
        "corp.",
        "llc.",
        "vs.",
        "v.",
        "e.g.",
        "i.e.",
        "etc.",
        "mr.",
        "ms.",
        "dr.",
        "st.",
    }
    assert writer.split_sentences("Signed by J. Okonkwo for the board.") == [
        "Signed by J. Okonkwo for the board."
    ]
    assert writer.split_sentences("The fee, e.g. the annual one, ran on. It then stopped.") == [
        "The fee, e.g. the annual one, ran on.",
        "It then stopped.",
    ]


def test_citations_read_the_document_and_the_anchor():
    text = "One thing [DR-001 | a/b.pdf#p1l1] and another [DR-002 | c/d.xlsx#Q&A Log!A11].\n"

    assert writer.citations(text) == [
        ("DR-001", "a/b.pdf#p1l1"),
        ("DR-002", "c/d.xlsx#Q&A Log!A11"),
    ]


def test_citations_read_the_short_form_as_the_row_the_anchor_names():
    """`[<doc>#<line>]` is the same citation as `[<doc> | <doc>#<line>]`."""
    short = "One thing [a/b.pdf#p1l1] and another [c/d.xlsx#Q&A Log!A11].\n"
    long = "One thing [a/b.pdf | a/b.pdf#p1l1] and another [c/d.xlsx | c/d.xlsx#Q&A Log!A11].\n"

    assert writer.citations(short) == writer.citations(long)
    assert writer.citations(short) == [
        ("a/b.pdf", "a/b.pdf#p1l1"),
        ("c/d.xlsx", "c/d.xlsx#Q&A Log!A11"),
    ]


def test_a_sentence_ending_in_the_short_form_is_cited():
    """Both forms end a sentence, and a bracket carrying no anchor ends none."""
    assert writer.is_cited("A thing [a/b.pdf#p1l1].")
    assert writer.is_cited("A thing [DR-001 | a/b.pdf#p1l1].")
    assert not writer.is_cited("A thing [see below].")
    assert writer.citations("A thing [see below].") == []


def test_dossier_pairs_read_the_document_field_whatever_it_holds():
    """Sample 1 writes a DR id in the document field; samples 2 and 3 write the path."""
    dossier = "\n".join(
        [
            "# Dossier: one",
            "",
            "## Matter 1",
            "",
            "### Timeline",
            "",
            "- 2025-12-11 | DR-001 | a quote | data_room/a/b.pdf#p1l1",
            "- 2025-12-12 | a/b.pdf | a quote | a/b.pdf#p1l2",
            "",
            "### Comparisons",
            "",
            "- e/f.md | said once | e/f.md#l1 || g/h.md | said twice | g/h.md#l2",
            "",
        ]
    )

    pairs = dossier_pairs(dossier)

    assert ("DR-001", "data_room/a/b.pdf#p1l1") in pairs
    assert ("a/b.pdf", "a/b.pdf#p1l2") in pairs
    assert ("e/f.md", "e/f.md#l1") in pairs
    assert ("g/h.md", "g/h.md#l2") in pairs


def test_a_short_form_citation_on_no_dossier_row_is_still_unknown():
    """The short form names one row, and a row the dossier never wrote is no row of it."""
    dossier = "\n".join(
        [
            "# Dossier: one",
            "",
            "## Matter 1",
            "",
            "### Timeline",
            "",
            "- 2025-12-11 | a/b.pdf | a quote | a/b.pdf#p1l1",
            "",
        ]
    )
    pairs = dossier_pairs(dossier)

    assert writer.citations("A thing [a/b.pdf#p1l1].")[0] in pairs
    assert writer.citations("A thing [a/b.pdf#p9l9].")[0] not in pairs


def test_the_prompt_asks_that_every_figure_is_cited_on_the_row_it_came_from():
    """One rule, beside the citation rules, on the row a figure is copied from."""
    assert "cited on the row it was copied from" in writer.PROMPT
    assert "figures from two rows cites both rows" in writer.PROMPT


def test_the_writer_never_reads_the_key():
    """No line of the writer reads a sample's answer key. The key is the tests' alone."""
    source = (ROOT / "src" / "rlm" / "write.py").read_text(encoding="utf-8")
    assert "load_key" not in source
    assert "key.json" not in source
    assert "rlm.key" not in source


# ---------------------------------------------------------------- the four checks


def section_record(anchor: str, text: str, cells: list[dict] | None = None) -> dict:
    """One record of sections.jsonl, as the room writes it."""
    record = {"anchor": anchor, "doc": anchor.rpartition("#")[0], "kind": "line", "text": text}
    if cells is not None:
        record["cells"] = cells
    return record


def one_finding(sentence: str) -> str:
    """A report of one section holding one sentence, which is what a check reads."""
    return f"## Findings ranked by materiality\n\n{sentence}\n"


ROOM_SECTIONS = [
    section_record("a/b.pdf#p1l1", "The exposure runs $240m to $465m and a bulk export is probable."),
    section_record(
        "c/d.xlsx#Inventory!A5",
        "912,800,000 records retained on 18 October 2025.",
        cells=[{"ref": "A5", "value": "912,800,000"}, {"ref": "D5", "value": "retained"}],
    ),
]
ROOM_INDEX = [{"docs": ["a/b.pdf"]}, {"docs": ["c/d.xlsx"]}]
ROOM_MAP = {"DR-001": "a/b.pdf", "DR-002": "c/d.xlsx"}

# The same room read by a map whose document is its own path, which is how samples 2 and 3
# write theirs and is where a short form citation names the row it came from.
ROOM_PATH_MAP = {"a/b.pdf": "a/b.pdf", "c/d.xlsx": "c/d.xlsx"}


def citation_failures(sentence: str) -> list[dict]:
    """The citation failures of one sentence read against the fake room."""
    return verifier.check_citations(one_finding(sentence), ROOM_SECTIONS, ROOM_INDEX, ROOM_MAP)


def path_citation_failures(sentence: str) -> list[dict]:
    """The citation failures of one sentence read against the room whose ids are its paths."""
    return verifier.check_citations(
        one_finding(sentence), ROOM_SECTIONS, ROOM_INDEX, ROOM_PATH_MAP
    )


def test_check_numbers_takes_a_day_off_the_dossier_row_that_cites_the_section():
    """A date the row carries beside its anchor is sourced, even when the section lacks it."""
    dossier = "\n".join(
        ["# Dossier: atlas", "", "## Matter 1", "", "### Timeline", "",
         "- 2025-12-11 | DR-001 | a quote | a/b.pdf#p1l1", ""]
    )
    report = one_finding("The notice was drafted on 2025-12-11 [DR-001 | a/b.pdf#p1l1].")

    assert verifier.check_numbers(report, ROOM_SECTIONS, dossier) == []
    failures = verifier.check_numbers(report, ROOM_SECTIONS)
    assert [failure["reason"] for failure in failures] == ["2025-12-11 is in no cited section"]
    assert verifier.dossier_rows_by_anchor(dossier) == {
        "a/b.pdf#p1l1": "2025-12-11 | DR-001 | a quote | a/b.pdf#p1l1"
    }


def test_check_citations_takes_a_citation_that_resolves():
    assert citation_failures("A thing [DR-001 | a/b.pdf#p1l1].") == []


def test_check_citations_takes_the_short_form_of_a_citation():
    """A room whose document is its path is named by the anchor on its own."""
    assert path_citation_failures("A thing [a/b.pdf#p1l1].") == []
    assert path_citation_failures("A thing [a/b.pdf | a/b.pdf#p1l1].") == []


def test_check_citations_refuses_a_short_form_naming_no_document_of_the_index():
    """An anchor beginning with no document of the index fails as an unknown anchor does."""
    failures = path_citation_failures("A thing [x/y.pdf#p1l1].")
    reasons = " ".join(failure["reason"] for failure in failures)

    assert [failure["check"] for failure in failures] == ["citations"] * len(failures)
    assert "x/y.pdf is on no record of the index" in reasons
    assert "x/y.pdf#p1l1 is no section of the room" in reasons


def test_check_citations_refuses_a_sentence_with_no_citation():
    """A topic sentence with no citation is a citation failure, so the re-ask can fix it."""
    failures = citation_failures("A thing with no citation. A cited thing [DR-001 | a/b.pdf#p1l1].")
    assert [failure["check"] for failure in failures] == ["citations"]
    assert failures[0]["line"] == "A thing with no citation."
    assert "no citation" in failures[0]["reason"]


def test_check_citations_refuses_an_anchor_that_does_not_parse():
    failures = citation_failures("A thing [DR-001 | a/b.pdf].")
    assert [failure["check"] for failure in failures] == ["citations"]
    assert "not an anchor" in failures[0]["reason"]


def test_check_citations_refuses_an_anchor_no_section_carries():
    failures = citation_failures("A thing [DR-001 | a/b.pdf#p9l9].")
    assert failures and "no section" in failures[0]["reason"]


def test_check_citations_refuses_a_document_id_that_maps_to_another_path():
    failures = citation_failures("A thing [DR-002 | a/b.pdf#p1l1].")
    assert failures
    assert "DR-002" in failures[0]["reason"] and "c/d.xlsx" in failures[0]["reason"]


def test_check_citations_resolves_a_cell_of_a_workbook_row():
    """A row is one section anchored at its first cell, so any cell of it resolves to that row."""
    assert citation_failures("A thing [DR-002 | c/d.xlsx#Inventory!D5].") == []


def number_failures(sentence: str) -> list[dict]:
    """The number failures of one sentence read against the fake room."""
    return verifier.check_numbers(one_finding(sentence), ROOM_SECTIONS)


def test_check_numbers_takes_a_number_the_cited_section_carries():
    assert number_failures("The range is $240m to $465m [DR-001 | a/b.pdf#p1l1].") == []


def test_check_numbers_refuses_a_number_the_cited_section_never_wrote():
    failures = number_failures("The reserve is $12m [DR-001 | a/b.pdf#p1l1].")
    assert [failure["check"] for failure in failures] == ["numbers"]
    assert "12" in failures[0]["reason"]


def test_check_numbers_folds_a_million_written_out_into_the_same_number():
    """$240m and 240 million are one number once normalise has folded both."""
    sections = [section_record("a/b.pdf#p1l1", "The room estimates 240 million of exposure.")]
    report = one_finding("The exposure is $240m [DR-001 | a/b.pdf#p1l1].")
    assert verifier.check_numbers(report, sections) == []


def test_check_numbers_does_not_fold_a_count_of_records_into_a_million():
    """912,800,000 is not 912.8m: the digits differ and the check says so."""
    failures = number_failures("The object holds 912.8m records [DR-002 | c/d.xlsx#Inventory!A5].")
    assert failures and any("912" in failure["reason"] for failure in failures)


def test_check_numbers_reads_a_decimal_figure_whole():
    """30.1% is one number and not a 30 beside a 1, on both sides of the check."""
    sections = [section_record("a/b.pdf#p1l1", "Meridian is 30.1% of total ARR.")]
    report = one_finding("Meridian is 30.1% of ARR [DR-001 | a/b.pdf#p1l1].")

    assert normalise("30.1%") == "30.1%"
    assert verifier.sentence_numbers("Meridian is 30.1% of ARR.") == {"30.1"}
    assert "30.1" in verifier.source_numbers("Meridian is 30.1% of total ARR.")
    assert verifier.check_numbers(report, sections) == []


def test_check_numbers_reads_a_money_figure_with_cents_whole():
    """$185,000.00 is one number, read as rlm.grade.normalise leaves it."""
    sections = [section_record("a/b.pdf#p1l1", "a fixed fee of $185,000.00 for the services")]
    report = one_finding("The fixed fee is $185,000.00 [DR-001 | a/b.pdf#p1l1].")

    assert normalise("$185,000.00") == "185000.00"
    assert verifier.sentence_numbers("The fixed fee is $185,000.00.") == {"185000.00"}
    assert "185000.00" in verifier.source_numbers("a fixed fee of $185,000.00 for the services")
    assert verifier.check_numbers(report, sections) == []


def test_check_numbers_refuses_a_decimal_the_cited_section_never_wrote():
    """A decimal in no cited section still fails, and its parts elsewhere do not save it."""
    sections = [section_record("a/b.pdf#p1l1", "Sections 11.1 and 12.2, within sixty (60) days.")]
    report = one_finding("The right runs against 30.1% of ARR [DR-001 | a/b.pdf#p1l1].")

    failures = verifier.check_numbers(report, sections)

    assert [failure["check"] for failure in failures] == ["numbers"]
    assert failures[0]["reason"] == "30.1 is in no cited section"


def test_check_numbers_reads_a_day_in_any_format_the_room_wrote_it_in():
    """2025-10-18 against a section saying 18 October 2025 is the same day."""
    report = one_finding("The reads began 2025-10-18 [DR-002 | c/d.xlsx#Inventory!A5].")
    assert verifier.check_numbers(report, ROOM_SECTIONS) == []


def test_check_numbers_refuses_a_day_the_cited_section_never_names():
    report = one_finding("The reads began 2025-10-19 [DR-002 | c/d.xlsx#Inventory!A5].")
    failures = verifier.check_numbers(report, ROOM_SECTIONS)
    assert failures and "2025-10-19" in failures[0]["reason"]


def test_check_numbers_takes_a_calculation_whose_operands_are_in_the_section():
    report = (
        "## The most material issue quantified\n\n"
        "The range is $240m to $465m [DR-001 | a/b.pdf#p1l1].\n"
        "Calculation: ($240m + $465m) / 2 = $352.5m, rounded to $400m, range $240m to $465m.\n"
    )
    assert verifier.check_numbers(report, ROOM_SECTIONS) == []


def test_check_numbers_refuses_a_calculation_whose_operand_is_nowhere():
    report = (
        "## The most material issue quantified\n\n"
        "The range is $240m to $465m [DR-001 | a/b.pdf#p1l1].\n"
        "Calculation: ($240m + $999m) / 2 = $619.5m, rounded to $600m, range $240m to $999m.\n"
    )
    failures = verifier.check_numbers(report, ROOM_SECTIONS)
    assert failures and all("999" in failure["reason"] for failure in failures)


def certainty_failures(sentence: str, source: str) -> list[dict]:
    """The certainty failures of one sentence over one section's words."""
    return verifier.check_certainty(one_finding(sentence), [section_record("a/b.pdf#p1l1", source)])


def test_check_certainty_refuses_a_word_above_its_source():
    failures = certainty_failures(
        "The export is confirmed [DR-001 | a/b.pdf#p1l1].", "A bulk export is probable."
    )
    assert [failure["check"] for failure in failures] == ["certainty"]
    assert "confirmed" in failures[0]["reason"]


def test_check_certainty_takes_a_word_at_the_rung_of_its_source():
    assert certainty_failures(
        "The export is probable [DR-001 | a/b.pdf#p1l1].", "A bulk export is probable."
    ) == []


def test_check_certainty_refuses_a_hedge_over_a_source_that_hedges_nothing():
    """A source with no certainty word sits at rung 0, and may sits above it."""
    failures = certainty_failures(
        "The export may have happened [DR-001 | a/b.pdf#p1l1].", "The object was retained."
    )
    assert failures and "may" in failures[0]["reason"]


def test_check_certainty_takes_a_sentence_that_hedges_nothing():
    assert certainty_failures(
        "The object was retained [DR-001 | a/b.pdf#p1l1].", "The object was retained."
    ) == []


ORDER_DOSSIER = (
    "# Dossier: atlas\n\n## Matter 1\n\n### Documents\n\n"
    "- 1. DR-069 | The forensic draft | 05_Security | 2025-12-01\n"
    "- 2. DR-073 | The backup inventory | 05_Security | 2025-11-01\n\n"
    "### Lesser matters\n\n"
    "- 1 | DR-031 | the tax memo | e/f.pdf#p1l1\n"
    "- 2 | DR-034 | the search partner | g/h.pdf#p1l1\n"
)

MATTER_FINDING = "The forensic draft is the matter [DR-069 | a/b.pdf#p1l1]."
LESSER_FINDING = "The tax memo is smaller [DR-031 | e/f.pdf#p1l1]."


def order_failures(*findings: str) -> list[dict]:
    """The order failures of a Findings section holding these lines in this order."""
    report = "## Findings ranked by materiality\n\n" + "\n\n".join(findings) + "\n"
    return verifier.check_order(report, ORDER_DOSSIER)


def test_check_order_takes_the_matter_ranked_first():
    assert order_failures(MATTER_FINDING, LESSER_FINDING) == []


def test_check_order_refuses_a_first_finding_on_a_lesser_document():
    failures = order_failures(LESSER_FINDING, MATTER_FINDING)
    assert len(failures) == 1 and failures[0]["check"] == "order"
    assert "first finding" in failures[0]["reason"]


def test_check_order_refuses_a_lesser_finding_ranked_above_the_matter():
    """A lesser matter may follow the set, but nothing lesser only comes before it."""
    assert order_failures(MATTER_FINDING, LESSER_FINDING, MATTER_FINDING) == []
    failures = order_failures(
        "An unranked document says something [DR-999 | i/j.pdf#p1l1].",
        LESSER_FINDING,
        MATTER_FINDING,
    )
    reasons = [failure["reason"] for failure in failures]
    assert len(failures) == 2
    assert any("first finding" in reason for reason in reasons)
    assert any("lesser" in reason for reason in reasons)


def test_verify_returns_the_four_counts_and_the_failures():
    report = (
        "## Findings ranked by materiality\n\n"
        "The forensic draft is the matter [DR-069 | a/b.pdf#p1l1].\n"
    )
    sections = [section_record("a/b.pdf#p1l1", "The forensic draft is the matter.")]
    index = [{"docs": ["a/b.pdf"]}]

    result = verifier.verify(report, sections, index, ORDER_DOSSIER, {"DR-069": "a/b.pdf"})

    assert result["passes"] is True
    assert result["failures"] == []
    assert set(result["counts"]) == set(verifier.CHECKS)
    assert sum(result["counts"].values()) == 0


def test_the_certainty_ladder_rises_from_possible_to_certain():
    assert [rung for rung, _ in verifier.CERTAINTY] == ["possible", "probable", "certain"]
    assert verifier.rung("nothing is said here") == 0
    assert verifier.rung("it could be so") == 1
    assert verifier.rung("it is likely") == 2
    assert verifier.rung("it is CONFIRMED") == 3
    assert verifier.rung("**probable**") == 2


def test_the_verifier_never_reads_the_key_and_never_calls_a_model():
    """The verifier reads the artefacts and nothing else: no key, no gateway, no socket."""
    source = (ROOT / "src" / "rlm" / "verify.py").read_text(encoding="utf-8")
    for forbidden in ("load_key", "key.json", "rlm.key", "Gateway", "httpx"):
        assert forbidden not in source, forbidden




# ---------------------------------------------------------------- the grader's carry rule


REPORT_WITH_THE_ROOMS_OWN_WORDS = (
    "The model assumed 615m monthly active users flat across the period "
    "[DR-096 | a/b.xlsx#Base Case!A5]. The dashboard read 594m in the week of 2025-11-10 "
    "[DR-048 | c/d.xlsx#Weekly MAU!A12]."
)


def carried(side: str, report: str) -> bool:
    """Whether one comparison side is carried by a report, by the grader's own rule."""
    return side_carried(side, numbers_of(report), days_of(report), words_of(report))


def test_carry_reads_a_comparison_side_written_in_the_rooms_own_words():
    """A side the report says in its own order and its own words is still carried."""
    assert carried("615m MAU assumed flat", REPORT_WITH_THE_ROOMS_OWN_WORDS)
    assert carried("594m in the week of 2025-11-10", REPORT_WITH_THE_ROOMS_OWN_WORDS)


def test_carry_refuses_a_side_whose_number_is_missing():
    """A number is not a connective: a side whose figure the report never wrote is not carried."""
    assert not carried("408m mobile MAU assumed flat", REPORT_WITH_THE_ROOMS_OWN_WORDS)
    assert not carried("594m in the week of 2025-11-17", REPORT_WITH_THE_ROOMS_OWN_WORDS)


def test_carry_refuses_a_side_whose_word_the_report_never_wrote():
    """Only the connectives are forgiven; a word that carries meaning has to be there."""
    assert not carried("615m MAU assumed flat in Dublin", REPORT_WITH_THE_ROOMS_OWN_WORDS)


def test_carry_connectives_are_the_words_a_key_joins_a_side_with():
    """The list is small, it is stemmed, and every word of it joins rather than states."""
    for word in ("against", "assumed", "flat", "week", "drafted", "limit"):
        assert stem(word) in CONNECTIVES
    for word in ("aurora", "kestrel", "ironlake", "912.8m", "backup"):
        assert stem(word) not in CONNECTIVES


# ---------------------------------------------------------------- the readout


def readout(terminalreporter):
    """Writes, per sample with a report, its recall, its missed ids, citations and dollars."""
    if not _REPORTS:
        return
    terminalreporter.section("phase 5 readout")
    ledger_rows = Ledger(ROOT / "LEDGER.md").rows()
    for sample in ENABLED:
        if sample not in _REPORTS:
            continue
        written = _REPORTS[sample]
        key = load_key(ROOT / "samples" / sample)
        recall, _, missed = measure_recall(key, written.text)
        found = writer.citations(written.text)
        summary_path = written.path.parent / "write-summary.json"
        dollars = sum(
            row["dollars"] for row in ledger_rows if row["phase"] == "5" and row["sample"] == sample
        )
        seconds = 0.0
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            seconds = summary.get("seconds", 0.0)
            if summary.get("model") in PRICES:
                dollars = price(summary["model"], summary["tokens_in"], summary["tokens_out"])
        terminalreporter.write_line(
            f"phase 5 {sample}: recall {recall:.1f}%, citations {len(found)}, "
            f"sentences {len(writer.sentences(written.text))}, "
            f"${dollars:.4f}, seconds {seconds:.1f}"
        )
        for fact in missed:
            terminalreporter.write_line(f"phase 5 {sample}: missed {fact}")
        verify_path = written.path.parent / "verify.json"
        if not verify_path.exists():
            continue
        record = json.loads(verify_path.read_text(encoding="utf-8"))
        for number, failures in enumerate(record.get("rounds", []), start=1):
            counts = verifier.counts_of(failures)
            terminalreporter.write_line(verifier.counts_line(sample, counts, number))
            for failure in failures:
                terminalreporter.write_line(verifier.failure_line(failure))


# ---------------------------------------------------------------- two passes and the grader


FAKE_KEY = {
    "sample": "atlas",
    "brief": "brief.md",
    "documents": {"DR-001": "a/b.pdf", "DR-002": "c/d.pdf"},
    "required_documents": ["DR-001"],
    "decoys": [{"document": "DR-002", "why": "smaller"}],
    "facts": [
        {"id": "F1", "kind": "number", "value": "$240m", "documents": ["DR-001"], "phase": 5}
    ],
    "answer": {"action": "reprice", "number": 400, "low": 240, "high": 465, "unit": "m"},
    "rubric": [
        {"id": 1, "criterion": "names the matter", "points": 60, "earns": "the matter is named"},
        {"id": 2, "criterion": "quantifies it", "points": 40, "earns": "a range is given"},
    ],
    "bar": {"perfect": 100, "wrong_under": 40},
}


class FakeGrader:
    """A grader that writes a grade file like rlm.grade.grade and never calls claude."""

    def __init__(self, scores: list[float]):
        self.scores = list(scores)
        self.calls: list[tuple[Path, Path, Path, str]] = []

    def __call__(self, sample_dir: Path, report_path: Path, run_dir: Path, name: str) -> dict:
        self.calls.append((sample_dir, report_path, run_dir, name))
        score = self.scores.pop(0)
        result = {
            "sample": "atlas",
            "report": report_path.name,
            "recall": 100.0,
            "recalled": ["F1"],
            "missed": [],
            "rubric": [
                {"id": 1, "points": 60, "reason": "named"},
                {"id": 2, "points": int(score) - 60, "reason": "quantified"},
            ],
            "score": score,
            "model": "fake-grader",
            "seconds": 0.5,
        }
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / name).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result


@pytest.fixture
def keyed_sample(fake_sample):
    """The fake sample with a key, so that the writer grades what it wrote."""
    sample_dir, run_dir, ledger = fake_sample
    (sample_dir / "key.json").write_text(json.dumps(FAKE_KEY), encoding="utf-8")
    (sample_dir / "a").mkdir()
    (sample_dir / "c").mkdir()
    (sample_dir / "a" / "b.pdf").write_text("", encoding="utf-8")
    (sample_dir / "c" / "d.pdf").write_text("", encoding="utf-8")
    return sample_dir, run_dir, ledger


def test_write_without_a_key_grades_nothing(fake_sample):
    """A sample with no key.json is written and verified and no grade.json appears."""
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)
    grader = FakeGrader([90])

    assert writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger, grader=grader) == 0

    assert grader.calls == []
    assert not (run_dir / "grade.json").exists()


def test_write_grades_one_pass_into_grade_json(keyed_sample):
    """One pass, one grade file named grade.json, with no spread and no score_b."""
    sample_dir, run_dir, ledger = keyed_sample
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)
    grader = FakeGrader([90])

    assert writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger, grader=grader) == 0

    assert len(grader.calls) == 1
    assert grader.calls[0] == (sample_dir, run_dir / "report.md", run_dir, "grade.json")
    written = json.loads((run_dir / "grade.json").read_text(encoding="utf-8"))
    assert written["score"] == 90
    assert "spread" not in written and "score_b" not in written


def test_write_two_passes_writes_pass_b_under_b_and_the_spread_into_pass_a(keyed_sample):
    """--passes 2 calls the gateway twice, grades twice, and pass a's grade holds the spread."""
    sample_dir, run_dir, ledger = keyed_sample
    second = FAKE_REPORT.replace("The room contradicts itself", "The room disagrees with itself")
    transport = FakeTransport([reply(FAKE_REPORT, 1000, 200), reply(second, 1100, 210)])
    gateway = Gateway(api_key="test-key", transport=transport)
    grader = FakeGrader([92, 87])

    assert (
        writer.main(
            [str(sample_dir), str(run_dir), "--passes", "2"],
            gateway=gateway,
            ledger=ledger,
            grader=grader,
        )
        == 0
    )

    assert len(transport.requests) == 2
    pass_b = run_dir / "b"
    for name in ("report.md", "verify.json", "grade.json", "write-summary.json"):
        assert (pass_b / name).exists(), f"pass b has no {name}"
    assert (pass_b / "report.md").read_text(encoding="utf-8") != (run_dir / "report.md").read_text(encoding="utf-8")
    assert grader.calls == [
        (sample_dir, run_dir / "report.md", run_dir, "grade.json"),
        (sample_dir, pass_b / "report.md", pass_b, "grade.json"),
    ]

    grade_a = json.loads((run_dir / "grade.json").read_text(encoding="utf-8"))
    grade_b = json.loads((pass_b / "grade.json").read_text(encoding="utf-8"))
    assert grade_a["score"] == 92
    assert grade_b["score"] == 87
    assert grade_a["score_b"] == 87
    assert grade_a["spread"] == 5
    assert "spread" not in grade_b

    record_b = json.loads((pass_b / "verify.json").read_text(encoding="utf-8"))
    assert record_b["passes"] is True
    assert record_b["calls"] == 1


def test_write_two_passes_pays_two_ledger_rows_and_none_for_the_grader(keyed_sample):
    """Each pass is one ledger batch; the grader adds no row."""
    sample_dir, run_dir, ledger = keyed_sample
    transport = FakeTransport([reply(FAKE_REPORT, 1000, 200), reply(FAKE_REPORT, 1100, 210)])
    gateway = Gateway(api_key="test-key", transport=transport)
    grader = FakeGrader([92, 87])

    writer.main(
        [str(sample_dir), str(run_dir), "--passes", "2"], gateway=gateway, ledger=ledger, grader=grader
    )

    rows = ledger.rows()
    assert len(rows) == 2
    assert [row["tokens_in"] for row in rows] == [1000, 1100]
    assert all(row["phase"] == "5" and row["sample"] == "atlas" for row in rows)
    assert all(row["model"] == MODEL for row in rows)


def test_write_two_passes_prints_both_scores_the_spread_the_dollars_and_the_seconds(keyed_sample, capsys):
    """The readout ends in one grade line carrying score a, score b, spread, dollars and seconds."""
    sample_dir, run_dir, ledger = keyed_sample
    transport = FakeTransport([reply(FAKE_REPORT, 1000, 200), reply(FAKE_REPORT, 1100, 210)])
    gateway = Gateway(api_key="test-key", transport=transport)
    grader = FakeGrader([92, 87])

    writer.main(
        [str(sample_dir), str(run_dir), "--passes", "2"], gateway=gateway, ledger=ledger, grader=grader
    )

    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith("grade atlas:")]
    assert len(lines) == 1, lines
    line = lines[0]
    assert "score_a 92" in line and "score_b 87" in line and "spread 5" in line
    assert "dollars" in line and "seconds" in line
    expected = price(MODEL, 1000, 200) + price(MODEL, 1100, 210)
    assert f"dollars {expected:.4f}" in line


def test_write_refuses_passes_outside_one_or_two(keyed_sample):
    """--passes takes 1 or 2 and nothing else."""
    sample_dir, run_dir, ledger = keyed_sample
    with pytest.raises(SystemExit):
        writer.main([str(sample_dir), str(run_dir), "--passes", "3"], gateway=Gateway(api_key="k"), ledger=ledger)


# ---------------------------------------------------------------- the bake-off and the pin


DS_FLASH = "deepseek/deepseek-v4-flash-0731"
GLM_FLASH = "z-ai/glm-5.3-flash"
LUNA = "openai/gpt-5.6-luna"
DS_PRO = "deepseek/deepseek-v4-pro"
GLM = "z-ai/glm-5.3"

# The two samples a fake bake-off runs over, and the fields of a row that carry a measurement
# or "not run".
BAKEOFF_SAMPLES = ("atlas", "northwind")
BAKEOFF_MEASURED = ("passes", "dollars", "seconds", "samples")


class WriteTransport(httpx.MockTransport):
    """Answers every write call with the same report and the tokens the model is given.

    usage maps a model id to the tokens its replies report, so two models that write the same
    report are still measured at different dollars.
    """

    def __init__(self, usage: dict[str, tuple[int, int]] | None = None):
        self.requests: list[httpx.Request] = []
        self._usage = usage or {}
        self._lock = threading.Lock()
        super().__init__(self._handle)

    def models_asked(self) -> list[str]:
        return [json.loads(request.content)["model"] for request in self.requests]

    def _handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        with self._lock:
            self.requests.append(request)
        tokens_in, tokens_out = self._usage.get(body["model"], (1000, 200))
        return httpx.Response(200, json=reply(FAKE_REPORT, tokens_in, tokens_out))


class BakeoffGrader:
    """A grader that reads the model out of the pass it grades and scores it from a table.

    scores maps a model id to the score of pass a and of pass b, and recalls maps a model id to
    the recall of each pass; a model in neither table is graded a perfect pass. rubric says
    whether the fake key has one, which is what tells a rubric sample from a recall sample.
    Every call also keeps the bake-off table as it stood on disk at that moment, so a test
    reads what had been written by the time a later model was measured. Nothing here calls
    claude.
    """

    def __init__(
        self,
        runs_root: Path,
        scores: dict[str, tuple[float, float]] | None = None,
        recalls: dict[str, tuple[float, float]] | None = None,
        rubric: bool = True,
    ):
        self.runs_root = Path(runs_root)
        self.scores = scores or {}
        self.recalls = recalls or {}
        self.rubric = rubric
        self.calls: list[tuple[str, str, str]] = []
        self.tables: list[dict | None] = []

    def __call__(self, sample_dir: Path, report_path: Path, run_dir: Path, name: str) -> dict:
        summary = json.loads((run_dir / "write-summary.json").read_text(encoding="utf-8"))
        model = summary["model"]
        letter = "b" if run_dir.name == "b" else "a"
        index = 0 if letter == "a" else 1
        self.calls.append((model, sample_dir.name, letter))
        table_path = self.runs_root / BAKEOFF_SAMPLES[0] / "write-bakeoff.json"
        self.tables.append(
            json.loads(table_path.read_text(encoding="utf-8")) if table_path.exists() else None
        )
        score = self.scores.get(model, (100.0, 100.0))[index]
        recall = self.recalls.get(model, (100.0, 100.0))[index]
        rows = [{"id": 1, "points": score, "reason": "graded"}] if self.rubric else []
        result = {
            "sample": sample_dir.name,
            "report": report_path.name,
            "recall": recall,
            "recalled": ["F1"],
            "missed": [],
            "rubric": rows,
            "score": score if self.rubric else recall,
            "model": "fake-grader" if self.rubric else "none",
            "seconds": 0.5,
        }
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / name).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result


@pytest.fixture
def bakeoff_room(tmp_path):
    """A samples root and a runs root holding two fake samples, and an empty ledger.

    Each sample carries the brief, a key and the room the writer reads, so a bake-off runs both
    passes on both samples against a fake transport and a fake grader.
    """
    samples_root = tmp_path / "samples"
    runs_root = tmp_path / "runs"
    for name in BAKEOFF_SAMPLES:
        sample_dir = samples_root / name
        sample_dir.mkdir(parents=True)
        (sample_dir / "brief.md").write_text("# Brief\n\nFind the matter.\n", encoding="utf-8")
        (sample_dir / "key.json").write_text(
            json.dumps(dict(FAKE_KEY, sample=name)), encoding="utf-8"
        )
        for folder, leaf in (("a", "b.pdf"), ("c", "d.pdf")):
            (sample_dir / folder).mkdir()
            (sample_dir / folder / leaf).write_text("", encoding="utf-8")
        run_dir = runs_root / name
        run_dir.mkdir(parents=True)
        (run_dir / "dossier.md").write_text(FAKE_DOSSIER, encoding="utf-8")
        write_jsonl(run_dir / "sections.jsonl", FAKE_SECTIONS)
        write_jsonl(run_dir / "index.jsonl", FAKE_INDEX)
        (run_dir / "map.json").write_text(json.dumps(FAKE_MAP, indent=1) + "\n", encoding="utf-8")
    ledger_path = tmp_path / "LEDGER.md"
    ledger_path.write_text(LEDGER_HEADER, encoding="utf-8")
    return samples_root, runs_root, Ledger(ledger_path)


def bakeoff_row(table: dict, model: str) -> dict:
    """The one row of the bake-off table for a model."""
    found = [row for row in table["rows"] if row["model"] == model]
    assert len(found) == 1, model
    return found[0]


def read_table(runs_root: Path, sample: str = BAKEOFF_SAMPLES[0]) -> dict:
    """The bake-off table one sample's run directory holds."""
    return json.loads((runs_root / sample / "write-bakeoff.json").read_text(encoding="utf-8"))


def test_writebakeoff_tiers_run_cheapest_first_inside_a_tier():
    """The five models of the price table sit in two tiers, each ordered by one write."""
    assert writebakeoff.slug(GLM_FLASH) == "glm-5.3-flash"
    assert writebakeoff.slug(DS_PRO) == "deepseek-v4-pro"
    assert set(writebakeoff.TIERS) == {"flash", "pro"}
    assert set(writebakeoff.TIERS["flash"]) == {DS_FLASH, GLM_FLASH, LUNA}
    assert set(writebakeoff.TIERS["pro"]) == {DS_PRO, GLM}
    assert set(writebakeoff.TIERS["flash"]) | set(writebakeoff.TIERS["pro"]) == set(PRICES)
    assert writebakeoff.WRITE_TOKENS == (37_000, 8_000)
    assert writebakeoff.RUBRIC_BAR == 85
    for tier in writebakeoff.TIERS.values():
        costs = [price(model, *writebakeoff.WRITE_TOKENS) for model in tier]
        assert costs == sorted(costs), tier


def test_writebakeoff_two_passes_on_two_samples_fill_one_row_and_name_the_winner(
    bakeoff_room, capsys
):
    """One model writes pass a and pass b on every sample and its row carries both."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport()
    gateway = Gateway(api_key="k", transport=transport)
    grader = BakeoffGrader(runs_root, scores={GLM_FLASH: (90.0, 86.0)})

    code = writebakeoff.main(
        [
            str(samples_root),
            str(runs_root),
            "--samples",
            *BAKEOFF_SAMPLES,
            "--models",
            GLM_FLASH,
        ],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    printed = capsys.readouterr().out
    assert code == 0

    # Two samples, two passes each, one call per pass because the fake report verifies.
    assert transport.models_asked() == [GLM_FLASH] * 4
    rows = ledger.rows()
    assert len(rows) == 4
    assert all(row["phase"] == "5" and row["model"] == GLM_FLASH for row in rows)

    name = writebakeoff.slug(GLM_FLASH)
    for sample in BAKEOFF_SAMPLES:
        base = runs_root / sample / "write-bakeoff" / name
        for out_dir in (base, base / "b"):
            for leaf in ("report.md", "verify.json", "grade.json", "write-summary.json"):
                assert (out_dir / leaf).exists(), (sample, out_dir.name, leaf)

    first = (runs_root / BAKEOFF_SAMPLES[0] / "write-bakeoff.json").read_bytes()
    second = (runs_root / BAKEOFF_SAMPLES[1] / "write-bakeoff.json").read_bytes()
    assert first == second
    table = json.loads(first.decode("utf-8"))
    assert table["samples"] == list(BAKEOFF_SAMPLES)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", table["date"])
    assert set(table["prices"]) == set(PRICES)

    row = bakeoff_row(table, GLM_FLASH)
    assert row["passes"] is True
    assert row["tier"] == "flash"
    assert row["dollars"] > 0
    assert row["seconds"] >= 0
    assert set(row["samples"]) == set(BAKEOFF_SAMPLES)
    for sample in BAKEOFF_SAMPLES:
        entry = row["samples"][sample]
        assert entry["recall_a"] == 100.0 and entry["recall_b"] == 100.0
        assert entry["verifier_a"] is True and entry["verifier_b"] is True
        assert entry["rubric_a"] == 90.0 and entry["rubric_b"] == 86.0
        assert entry["spread"] == 4.0
    assert table["winner"] == GLM_FLASH
    for model in (DS_FLASH, LUNA, DS_PRO, GLM):
        blank = bakeoff_row(table, model)
        assert all(blank[field] == "not run" for field in BAKEOFF_MEASURED), model
    assert f"winner: {GLM_FLASH}" in printed


def test_writebakeoff_a_sample_without_a_rubric_is_gated_on_recall_and_the_verifier(
    bakeoff_room, capsys
):
    """A grade file with no rubric row carries no rubric field in the row and still gates."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport()
    gateway = Gateway(api_key="k", transport=transport)
    grader = BakeoffGrader(runs_root, rubric=False)

    code = writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES, "--models", GLM_FLASH],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()
    assert code == 0

    row = bakeoff_row(read_table(runs_root), GLM_FLASH)
    entry = row["samples"][BAKEOFF_SAMPLES[0]]
    assert "rubric_a" not in entry and "spread" not in entry
    assert entry["recall_a"] == 100.0 and entry["verifier_a"] is True
    assert row["passes"] is True


def test_writebakeoff_a_rubric_under_the_bar_fails_the_row(bakeoff_room, capsys):
    """Pass a at a rubric score under 85 fails the row even where recall is 100."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport()
    gateway = Gateway(api_key="k", transport=transport)
    grader = BakeoffGrader(runs_root, scores={GLM_FLASH: (84.0, 92.0)})

    writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES, "--models", GLM_FLASH],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()

    table = read_table(runs_root)
    assert bakeoff_row(table, GLM_FLASH)["passes"] is False
    assert table["winner"] is None


def test_writebakeoff_a_recall_under_a_hundred_fails_the_row(bakeoff_room, capsys):
    """Pass a at a recall under 100 fails the row even where the rubric clears the bar."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport()
    gateway = Gateway(api_key="k", transport=transport)
    grader = BakeoffGrader(
        runs_root,
        scores={GLM_FLASH: (95.0, 95.0)},
        recalls={GLM_FLASH: (96.0, 100.0)},
    )

    writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES, "--models", GLM_FLASH],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()

    assert bakeoff_row(read_table(runs_root), GLM_FLASH)["passes"] is False


def test_writebakeoff_a_passing_flash_model_stops_the_pro_tier(bakeoff_room, capsys):
    """No pro model runs when a flash model passes on every sample."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport()
    gateway = Gateway(api_key="k", transport=transport)
    grader = BakeoffGrader(
        runs_root, scores={model: (60.0, 60.0) for model in (DS_FLASH, LUNA)}
    )

    code = writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()
    assert code == 0

    assert set(transport.models_asked()) == set(writebakeoff.TIERS["flash"])
    for model in writebakeoff.TIERS["pro"]:
        directory = runs_root / BAKEOFF_SAMPLES[0] / "write-bakeoff" / writebakeoff.slug(model)
        assert not directory.exists()
    table = read_table(runs_root)
    assert table["winner"] == GLM_FLASH
    for model in writebakeoff.TIERS["pro"]:
        row = bakeoff_row(table, model)
        assert all(row[field] == "not run" for field in BAKEOFF_MEASURED), model


def test_writebakeoff_a_failing_flash_tier_escalates_and_stops_at_the_first_pro_model(
    bakeoff_room, capsys
):
    """Every flash model failing runs the pro tier, which stops at its first passing model."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport()
    gateway = Gateway(api_key="k", transport=transport)
    grader = BakeoffGrader(
        runs_root, scores={model: (60.0, 60.0) for model in writebakeoff.TIERS["flash"]}
    )

    code = writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()
    assert code == 0

    first_pro = writebakeoff.TIERS["pro"][0]
    assert set(transport.models_asked()) == set(writebakeoff.TIERS["flash"]) | {first_pro}
    table = read_table(runs_root)
    assert table["winner"] == first_pro
    for model in writebakeoff.TIERS["flash"]:
        assert bakeoff_row(table, model)["passes"] is False
    row = bakeoff_row(table, writebakeoff.TIERS["pro"][1])
    assert all(row[field] == "not run" for field in BAKEOFF_MEASURED)


def test_writebakeoff_writes_the_table_after_each_model(bakeoff_room, capsys):
    """The table on disk already carries the first model's row when the second one is graded."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport()
    gateway = Gateway(api_key="k", transport=transport)
    grader = BakeoffGrader(
        runs_root, scores={model: (60.0, 60.0) for model in writebakeoff.TIERS["flash"]}
    )

    writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()

    first, second = writebakeoff.TIERS["flash"][0], writebakeoff.TIERS["flash"][1]
    later = [number for number, call in enumerate(grader.calls) if call[0] == second]
    assert later, "the second model was never graded"
    table = grader.tables[later[0]]
    assert table is not None, "no table was on disk when the second model was graded"
    assert bakeoff_row(table, first)["passes"] is False
    assert bakeoff_row(table, second)["passes"] == "not run"


def test_writebakeoff_the_winner_is_the_cheapest_measured_row(bakeoff_room, capsys):
    """Two models pass; the winner is the one whose measured dollars are lower."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport(usage={DS_FLASH: (100, 100), GLM_FLASH: (100_000, 10_000)})
    gateway = Gateway(api_key="k", transport=transport)
    grader = BakeoffGrader(runs_root)

    code = writebakeoff.main(
        [
            str(samples_root),
            str(runs_root),
            "--samples",
            *BAKEOFF_SAMPLES,
            "--models",
            DS_FLASH,
            GLM_FLASH,
        ],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()
    assert code == 0

    table = read_table(runs_root)
    cheap = bakeoff_row(table, DS_FLASH)
    dear = bakeoff_row(table, GLM_FLASH)
    assert cheap["passes"] is True and dear["passes"] is True
    assert cheap["dollars"] < dear["dollars"]
    assert table["winner"] == DS_FLASH
    # The winner is the row measured cheaper, not the one the price table calls cheaper.
    assert price(DS_FLASH, *writebakeoff.WRITE_TOKENS) > price(
        GLM_FLASH, *writebakeoff.WRITE_TOKENS
    )


def test_writebakeoff_recount_rebuilds_the_rows_from_disk_with_no_call(bakeoff_room, capsys):
    """--recount reads the passes already on disk, makes no call and writes no ledger row."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport()
    gateway = Gateway(api_key="k", transport=transport)
    grader = BakeoffGrader(runs_root, scores={GLM_FLASH: (90.0, 86.0)})

    writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES, "--models", GLM_FLASH],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()
    before = read_table(runs_root)
    calls = len(transport.requests)
    rows = len(ledger.rows())

    code = writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES, "--recount"],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()
    assert code == 0
    assert len(transport.requests) == calls
    assert len(ledger.rows()) == rows

    after = read_table(runs_root)
    assert bakeoff_row(after, GLM_FLASH)["samples"] == bakeoff_row(before, GLM_FLASH)["samples"]
    assert bakeoff_row(after, GLM_FLASH)["passes"] is True
    assert after["winner"] == GLM_FLASH
    for model in (DS_FLASH, LUNA, DS_PRO, GLM):
        row = bakeoff_row(after, model)
        assert all(row[field] == "not run" for field in BAKEOFF_MEASURED), model


STALE_VERIFY = (
    json.dumps(
        {
            "sample": "atlas",
            "rounds": [[{"check": "numbers", "line": "a line", "reason": "an old reading"}]],
            "passes": False,
        },
        indent=2,
    )
    + "\n"
)


def test_writebakeoff_recount_reverifies_each_report_under_the_verifier_of_the_day(
    bakeoff_room, capsys
):
    """A recount reads each pass's report.md again and leaves verify.json where it is."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport()
    gateway = Gateway(api_key="k", transport=transport)
    grader = BakeoffGrader(runs_root, scores={GLM_FLASH: (90.0, 86.0)})

    writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES, "--models", GLM_FLASH],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()

    name = writebakeoff.slug(GLM_FLASH)
    pass_dirs = [
        out_dir
        for sample in BAKEOFF_SAMPLES
        for out_dir in (
            runs_root / sample / "write-bakeoff" / name,
            runs_root / sample / "write-bakeoff" / name / "b",
        )
    ]
    for out_dir in pass_dirs:
        (out_dir / "verify.json").write_text(STALE_VERIFY, encoding="utf-8")

    code = writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES, "--recount"],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()
    assert code == 0

    row = bakeoff_row(read_table(runs_root), GLM_FLASH)
    for sample in BAKEOFF_SAMPLES:
        entry = row["samples"][sample]
        assert entry["verifier_a"] is True, sample
        assert entry["verifier_b"] is True, sample
    assert row["passes"] is True
    for out_dir in pass_dirs:
        assert (out_dir / "verify.json").read_text(encoding="utf-8") == STALE_VERIFY


def test_writebakeoff_a_rerun_of_one_sample_keeps_the_other_samples_of_the_row(
    bakeoff_room, capsys
):
    """A run restricted to one sample rewrites that sample and the table stays whole."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport()
    gateway = Gateway(api_key="k", transport=transport)
    grader = BakeoffGrader(runs_root, scores={GLM_FLASH: (90.0, 86.0)})

    writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES, "--models", GLM_FLASH],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()
    calls = len(transport.requests)

    code = writebakeoff.main(
        [
            str(samples_root),
            str(runs_root),
            "--samples",
            BAKEOFF_SAMPLES[1],
            "--models",
            GLM_FLASH,
        ],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    capsys.readouterr()
    assert code == 0
    # Two passes on the one sample the rerun names, and none on the other.
    assert len(transport.requests) == calls + 2

    table = read_table(runs_root)
    assert table["samples"] == list(BAKEOFF_SAMPLES)
    row = bakeoff_row(table, GLM_FLASH)
    assert set(row["samples"]) == set(BAKEOFF_SAMPLES)
    assert row["passes"] is True
    first = (runs_root / BAKEOFF_SAMPLES[0] / "write-bakeoff.json").read_bytes()
    second = (runs_root / BAKEOFF_SAMPLES[1] / "write-bakeoff.json").read_bytes()
    assert first == second


def test_writebakeoff_dry_run_writes_a_blank_table_and_makes_no_request(bakeoff_room, capsys):
    """--dry-run prints one estimate per model and leaves a table of not run rows."""
    samples_root, runs_root, ledger = bakeoff_room
    transport = WriteTransport()
    gateway = Gateway(api_key="k", transport=transport)
    before = len(ledger.rows())

    code = writebakeoff.main(
        [str(samples_root), str(runs_root), "--samples", *BAKEOFF_SAMPLES, "--dry-run"],
        gateway=gateway,
        ledger=ledger,
    )
    printed = capsys.readouterr().out
    assert code == 0
    assert transport.requests == []
    assert len(ledger.rows()) == before

    table = read_table(runs_root)
    assert [row["model"] for row in table["rows"]] == list(writebakeoff.TIERS["flash"]) + list(
        writebakeoff.TIERS["pro"]
    )
    for row in table["rows"]:
        assert all(row[field] == "not run" for field in BAKEOFF_MEASURED), row["model"]
    assert table["winner"] is None
    for model in PRICES:
        assert model in printed, model
    assert "$" in printed


def test_writebakeoff_refuses_a_model_outside_the_price_table(bakeoff_room, capsys):
    """--models names a model of the price table and nothing else."""
    samples_root, runs_root, ledger = bakeoff_room
    code = writebakeoff.main(
        [
            str(samples_root),
            str(runs_root),
            "--samples",
            *BAKEOFF_SAMPLES,
            "--models",
            "google/gemini",
        ],
        gateway=Gateway(api_key="k", transport=WriteTransport()),
        ledger=ledger,
    )
    out = capsys.readouterr().out
    assert code == 2
    assert "google/gemini" in out


def test_write_out_dir_puts_both_passes_under_it_and_reads_the_room_from_the_run_directory(
    keyed_sample,
):
    """--out-dir writes pass a and pass b under it and leaves the run directory's room alone."""
    sample_dir, run_dir, ledger = keyed_sample
    transport = FakeTransport([reply(FAKE_REPORT, 1000, 200), reply(FAKE_REPORT, 1100, 210)])
    gateway = Gateway(api_key="test-key", transport=transport)
    grader = FakeGrader([92, 87])
    out_dir = run_dir.parent / "elsewhere"

    code = writer.main(
        [str(sample_dir), str(run_dir), "--passes", "2", "--out-dir", str(out_dir)],
        gateway=gateway,
        ledger=ledger,
        grader=grader,
    )
    assert code == 0

    for name in ("report.md", "verify.json", "grade.json", "write-summary.json", "digest.md"):
        assert (out_dir / name).exists(), name
    assert (out_dir / "b" / "report.md").exists()
    assert not (run_dir / "report.md").exists()
    assert not (run_dir / "b").exists()
    grade_a = json.loads((out_dir / "grade.json").read_text(encoding="utf-8"))
    assert grade_a["score_b"] == 87 and grade_a["spread"] == 5


# ---------------------------------------------------------------- the gate


def fake_bakeoff_table(winner: str | None) -> dict:
    """A bake-off table naming one winner, as pin reads it."""
    return {
        "date": "2026-09-07",
        "samples": list(BAKEOFF_SAMPLES),
        "prices": {model: list(PRICES[model]) for model in PRICES},
        "rows": [],
        "winner": winner,
    }


def lay_out_a_winner(runs_root: Path, sample: str, winner: str) -> dict[str, bytes]:
    """Writes one sample's winning bake-off pass a and pass b under runs_root and returns the
    bytes of the three files pin digests."""
    sample_dir = runs_root / sample
    pass_a = sample_dir / "write-bakeoff" / writebakeoff.slug(winner)
    pass_b = pass_a / "b"
    pass_b.mkdir(parents=True)
    (sample_dir / "write-bakeoff.json").write_text(
        json.dumps(fake_bakeoff_table(winner)), encoding="utf-8"
    )
    wanted: dict[str, bytes] = {}
    for name in PINNED_FILES:
        body = f"{sample} a {name}\n".encode()
        (pass_a / name).write_bytes(body)
        (pass_b / name).write_bytes(f"{sample} b {name}\n".encode())
        wanted[name] = body
    (pass_a / "digest.md").write_bytes(f"{sample} digest\n".encode())
    (pass_a / "write-summary.json").write_bytes(b"{}\n")
    (pass_a / "report-raw.txt").write_bytes(f"{sample} raw\n".encode())
    (pass_a / "report-raw-1.txt").write_bytes(f"{sample} raw one\n".encode())
    return wanted


def test_gate_pin_reports_copies_the_winners_two_passes_and_digests_pass_a(tmp_path, capsys):
    """pin.main --reports copies the winner's pass a into the run directory and pass b under
    b/, and writes the sha256 of the three pinned files per sample."""
    runs_root = tmp_path / "runs"
    wanted = {}
    for sample in BAKEOFF_SAMPLES:
        files = lay_out_a_winner(runs_root, sample, GLM_FLASH)
        wanted[sample] = {name: hashlib.sha256(body).hexdigest() for name, body in files.items()}

    digests_path = tmp_path / "phase5-digests.json"
    code = pin.main(
        [
            str(runs_root),
            "--reports",
            "--samples",
            *BAKEOFF_SAMPLES,
            "--digests",
            str(digests_path),
        ]
    )
    out = capsys.readouterr().out

    assert code == 0
    assert json.loads(digests_path.read_text(encoding="utf-8")) == wanted
    raw = digests_path.read_text(encoding="utf-8")
    assert raw == json.dumps(wanted, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    for sample in BAKEOFF_SAMPLES:
        sample_dir = runs_root / sample
        for name in PINNED_FILES:
            assert (sample_dir / name).read_bytes() == f"{sample} a {name}\n".encode()
            assert (sample_dir / "b" / name).read_bytes() == f"{sample} b {name}\n".encode()
        assert (sample_dir / "digest.md").exists()
        assert (sample_dir / "write-summary.json").exists()
        assert (sample_dir / "report-raw.txt").exists()
        assert (sample_dir / "report-raw-1.txt").exists()
        assert sample in out
    assert GLM_FLASH in out


def test_gate_pin_reports_refuses_a_sample_with_no_winner(tmp_path, capsys):
    """pin.main --reports refuses, names the sample and copies and digests nothing."""
    runs_root = tmp_path / "runs"
    lay_out_a_winner(runs_root, BAKEOFF_SAMPLES[0], GLM_FLASH)
    other = runs_root / BAKEOFF_SAMPLES[1]
    other.mkdir(parents=True)
    (other / "write-bakeoff.json").write_text(
        json.dumps(fake_bakeoff_table(None)), encoding="utf-8"
    )

    digests_path = tmp_path / "phase5-digests.json"
    code = pin.main(
        [
            str(runs_root),
            "--reports",
            "--samples",
            *BAKEOFF_SAMPLES,
            "--digests",
            str(digests_path),
        ]
    )
    out = capsys.readouterr().out

    assert code == 1
    assert not digests_path.exists()
    assert BAKEOFF_SAMPLES[1] in out
    assert not (runs_root / BAKEOFF_SAMPLES[0] / "report.md").exists()


def test_gate_pin_reports_refuses_a_sample_with_no_table(tmp_path, capsys):
    """A sample with no write-bakeoff.json is the same refusal as a table naming no winner."""
    runs_root = tmp_path / "runs"
    lay_out_a_winner(runs_root, BAKEOFF_SAMPLES[0], GLM_FLASH)
    (runs_root / BAKEOFF_SAMPLES[1]).mkdir(parents=True)

    digests_path = tmp_path / "phase5-digests.json"
    code = pin.main(
        [
            str(runs_root),
            "--reports",
            "--samples",
            *BAKEOFF_SAMPLES,
            "--digests",
            str(digests_path),
        ]
    )
    out = capsys.readouterr().out

    assert code == 1
    assert not digests_path.exists()
    assert BAKEOFF_SAMPLES[1] in out


def test_gate_default_digests_path_names_the_phase_5_file():
    """The default digest file of the reports mode is tests/phase5-digests.json."""
    assert pin.default_digests_path(reports=True).name == "phase5-digests.json"
    assert pin.default_digests_path(reports=True).parent == ROOT / "tests"
    assert pin.default_digests_path(dossiers=True).name == "phase4-digests.json"
    assert pin.default_digests_path().name == "phase2-digests.json"
