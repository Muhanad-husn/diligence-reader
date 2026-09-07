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

Only sample 1 is enabled here. Samples 2 and 3 are the fifth slice of the phase. A sample
whose report.md is absent is skipped."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from rlm import verify as verifier
from rlm import write as writer
from rlm.carry import days_of, numbers_of, stem, words_of
from rlm.gateway import PRICES, Gateway, Ledger, price
from rlm.grade import CONNECTIVES, measure_recall, side_carried
from rlm.key import load_key
from rlm.notes import straighten
from rlm.sections import parse_anchor

ROOT = Path(__file__).resolve().parents[1]

# The sample this slice writes a report for. Samples 2 and 3 are slice 05.
ENABLED = ("atlas",)
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
MODEL = "z-ai/glm-5.3-flash"

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


def dossier_pairs(dossier: str) -> set[tuple[str, str]]:
    """Every document and anchor the dossier writes on one row, as a set of pairs.

    A row is a list line under a heading. The documents of a row are its `DR-###` ids and the
    anchors are the fields that carry a `#`, so a comparison row of several triples gives up
    every pair it writes.
    """
    found: set[tuple[str, str]] = set()
    for line in dossier.splitlines():
        if not line.startswith("- "):
            continue
        docs = set(re.findall(r"DR-\d+", line))
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


def test_no_decoy_is_cited_above_the_first_finding_of_the_matter(report, key):
    """A decoy ranked over the matter is the failure the room was built to catch."""
    matter = set()
    for fact in key.facts:
        if fact.id == "matter-documents":
            matter.update(fact.documents)
    assert matter, "the key names no matter-documents fact"
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
    """digest.md is on disk and holds no more rows than DIGEST_ROWS allows."""
    rows = [line for line in report.digest.splitlines() if line.startswith("- ")]
    assert rows
    assert len(rows) <= writer.DIGEST_ROWS
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


def test_write_default_model_is_glm_flash(fake_sample):
    """Without --model the call goes to z-ai/glm-5.3-flash and the report lands on disk."""
    sample_dir, run_dir, ledger = fake_sample
    transport = FakeTransport([reply(FAKE_REPORT)])
    gateway = Gateway(api_key="test-key", transport=transport)

    assert writer.main([str(sample_dir), str(run_dir)], gateway=gateway, ledger=ledger) == 0

    assert writer.DEFAULT_MODEL == MODEL
    body = json.loads(transport.requests[0].content)
    assert body["model"] == MODEL
    assert body["max_tokens"] == writer.MAX_OUTPUT_TOKENS == 8000
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


def test_citations_read_the_document_and_the_anchor():
    text = "One thing [DR-001 | a/b.pdf#p1l1] and another [DR-002 | c/d.xlsx#Q&A Log!A11].\n"

    assert writer.citations(text) == [
        ("DR-001", "a/b.pdf#p1l1"),
        ("DR-002", "c/d.xlsx#Q&A Log!A11"),
    ]


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


def citation_failures(sentence: str) -> list[dict]:
    """The citation failures of one sentence read against the fake room."""
    return verifier.check_citations(one_finding(sentence), ROOM_SECTIONS, ROOM_INDEX, ROOM_MAP)


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
