"""Phase 5 report tests. Code chooses the evidence and the model writes it up: build_digest
keeps about a hundred and fifty rows of the dossier's first matter, digest.md is the user
message of one model call, and report.md comes back with an executive summary, the findings
ranked by materiality, the most material issue quantified, the lesser issues and the open
items. These tests read the digest and the report off disk and check that the digest is
deterministic and holds every comparison row and every lesser matter the dossier kept, that
every digest row is quoted whole in the report with its citation, that the report carries the
five second level headings in the brief's order with one trailing newline, that every sentence
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

The rest of the tests run on a fake transport and need no key and no network: the default
model, a model outside the price table, the json flag of the gateway, the refusal when the
dossier is absent, and what build_messages puts in each message. One static test reads
src/rlm/write.py and asserts that no line of it reads the key.

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

from rlm import write as writer
from rlm.carry import days_of, numbers_of, stem, words_of
from rlm.gateway import PRICES, Gateway, Ledger, price
from rlm.grade import CONNECTIVES, measure_recall, side_carried
from rlm.key import load_key
from rlm.notes import straighten

ROOT = Path(__file__).resolve().parents[1]

# The sample this slice writes a report for. Samples 2 and 3 are slice 05.
ENABLED = ("atlas",)
SKIP_REASON = "report not written for this sample yet"

# The five second level headings, in the order the brief asks for its deliverables.
HEADINGS = (
    "Executive summary",
    "Findings ranked by materiality",
    "The most material issue quantified",
    "Lesser issues",
    "Open items",
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


def test_report_is_markdown_with_one_trailing_newline(report):
    assert report.text
    assert report.text.endswith("\n") and not report.text.endswith("\n\n")


def test_report_carries_the_five_headings_in_order(report):
    """The report answers the brief's five deliverables under five headings, in that order."""
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
    lesser = sections.get("Lesser matters", [])
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


def test_report_quotes_every_digest_row_whole_with_its_citation(report):
    """The one rule of the prompt: every row of the digest is quoted once, whole, and cited."""
    straightened = straighten(report.text)
    missing = []
    for row in writer.build_digest(report.dossier):
        if row.count(" || "):
            halves = [part.split(" | ") for part in row[2:].split(" || ")]
            quotes = [(part[0], " | ".join(part[1:-1]), part[-1]) for part in halves]
        else:
            fields = writer.row_fields(row)
            quotes = [(fields[1], writer.row_quote(row), fields[-1])]
        for doc, quote, anchor in quotes:
            if straighten(quote) not in straightened:
                missing.append(f"{doc} {quote[:60]}")
                continue
            if f"[{doc} | {anchor}]" not in report.text:
                missing.append(f"{doc} uncited {quote[:40]}")
    assert not missing, f"{len(missing)} digest rows not quoted whole and cited: " + " || ".join(
        missing[:8]
    )


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

Calculation: 240 + 465 / 2 = 400, range 375 to 525.
The exposure is a range [DR-001 | a/b.pdf#p1l1].

## Lesser issues

The tax memo is smaller [DR-001 | a/b.pdf#p1l1].

## Open items

The final report is outstanding [DR-001 | a/b.pdf#p1l1].
"""


@pytest.fixture
def fake_sample(tmp_path):
    """A sample directory with a brief, a run directory with a dossier, and an empty ledger."""
    sample_dir = tmp_path / "atlas"
    run_dir = tmp_path / "run"
    sample_dir.mkdir()
    run_dir.mkdir()
    (sample_dir / "brief.md").write_text("# Brief\n\nFind the matter.\n", encoding="utf-8")
    (run_dir / "dossier.md").write_text(
        "# Dossier: atlas\n\n## Matter 1\n\n### Timeline\n\n"
        "- 2025-10-18 | DR-001 | a quote | a/b.pdf#p1l1\n\n"
        "### Names\n\n- AURORA | DR-001 | a name | a/b.pdf#p1l2\n\n"
        "### Comparisons\n\n"
        "- DR-001 | one half | a/b.pdf#p1l3 || DR-002 | the other half | c/d.pdf#p2l1\n",
        encoding="utf-8",
    )
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
    assert body["max_tokens"] == writer.MAX_OUTPUT_TOKENS == 16000
    assert (run_dir / "report.md").read_text(encoding="utf-8").startswith("## Executive summary")
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
