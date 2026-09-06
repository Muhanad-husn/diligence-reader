"""Phase 2 notes tests. A note is one JSON file per document under runs/<sample>/notes/, written
from one gateway call, with every quote and figure verified against the document's own sections
and anchored by code. These tests read the artefact and never call the model. The gateway's
estimate, refusal and ledger logic is tested with a fake transport that never opens a socket. A
sample whose notes directory is absent is skipped."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

import httpx
import pytest

from rlm.gateway import (
    PRICES,
    TOTAL_CEILING,
    CapExceeded,
    Completion,
    Gateway,
    Ledger,
    estimate_tokens,
    price,
)
from rlm.key import load_key
from rlm.notes import (
    CROSS_REFERENCE_KINDS,
    LOG_KEYS,
    MAX_OUTPUT_TOKENS,
    NOTE_KEYS,
    QUOTED_FIELDS,
    SYSTEM_PROMPT,
    build_messages,
    item_detail,
    locate_quote,
    main,
    note_name,
    straighten,
    verify_items,
    well_shaped,
)
from rlm.sections import parse_anchor

ROOT = Path(__file__).resolve().parents[1]
SKIP_REASON = "notes not run for this sample yet"
MODEL = "deepseek/deepseek-v4-flash-0731"
PHASE = 2
PHASE_CAP = 8.0
DR_069 = "data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf"

# The keys of runs/<sample>/notes-summary.json, one per pass.
SUMMARY_KEYS = frozenset(
    {
        "documents",
        "noted",
        "dropped",
        "verified",
        "re_asked",
        "dropped_items",
        "tokens_in",
        "tokens_out",
        "dollars",
        "seconds",
        "model",
        "pass",
        "sample",
    }
)

_LEDGER_ROW = re.compile(r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|$")

LEDGER_HEAD = (
    "# Ledger\n\n"
    "Ceiling $50. Written by the code that makes gateway calls; a line added by hand says so.\n\n"
    "| date | sample | phase | model | tokens in | tokens out | dollars | balance |\n"
    "|---|---|---|---|---|---|---|---|\n"
)


def ledger_rows(path: Path) -> list[dict]:
    """Reads the ledger table into one dict per row, in file order."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _LEDGER_ROW.match(line)
        if not match or match.group(1) == "date" or match.group(1).startswith("-"):
            continue
        date, sample, phase, model, tokens_in, tokens_out, dollars, balance = match.groups()
        rows.append(
            {
                "date": date,
                "sample": sample,
                "phase": phase,
                "model": model,
                "tokens_in": int(tokens_in),
                "tokens_out": int(tokens_out),
                "dollars": float(dollars),
                "balance": float(balance),
            }
        )
    return rows


def write_ledger(path: Path, rows: list[tuple[str, str, str, str, int, int, float, float]]) -> None:
    lines = [f"| {d} | {s} | {p} | {m} | {ti} | {to} | {do:.4f} | {b:.4f} |" for d, s, p, m, ti, to, do, b in rows]
    path.write_text(LEDGER_HEAD + "\n".join(lines) + "\n", encoding="utf-8")


def reply(text: str, tokens_in: int = 1000, tokens_out: int = 200) -> dict:
    """The shape of one OpenRouter chat completion response."""
    return {
        "id": "gen-1",
        "model": MODEL,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out, "total_tokens": tokens_in + tokens_out},
    }


class FakeTransport(httpx.MockTransport):
    """A transport that records every request and answers each with the next canned reply.

    The pass runs eight documents at once, so the record and the pop are taken under a lock.
    """

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


# ---------------------------------------------------------------- gateway: pure functions


def test_gateway_estimate_tokens_is_characters_over_four_rounded_up():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcde") == 2
    assert estimate_tokens("x" * 4001) == 1001


def test_gateway_price_table_is_plan_section_5():
    """Per million tokens, prompt then completion, as PLAN.md section 5 reads on 2026-09-05."""
    assert PRICES == {
        "openai/gpt-5.6-luna": (0.200, 1.200),
        "deepseek/deepseek-v4-flash-0731": (0.065, 0.180),
        "deepseek/deepseek-v4-pro": (0.870, 1.740),
        "z-ai/glm-5.3": (1.400, 4.400),
        "z-ai/glm-5.3-flash": (0.075, 0.250),
    }
    assert price(MODEL, 1_000_000, 1_000_000) == pytest.approx(0.245)
    assert price(MODEL, 90_000, 60_000) == pytest.approx(0.00585 + 0.0108)
    assert price("z-ai/glm-5.3", 0, 0) == 0.0
    with pytest.raises(KeyError):
        price("google/gemini", 1, 1)
    assert TOTAL_CEILING == 50.0


# ---------------------------------------------------------------- gateway: transport


def test_gateway_complete_posts_one_chat_request_and_returns_the_reported_usage():
    transport = FakeTransport([reply('{"what": "x"}', tokens_in=1234, tokens_out=56)])
    gateway = Gateway(api_key="test-key", transport=transport)
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]

    completion = gateway.complete(MODEL, messages, max_tokens=4000)

    assert isinstance(completion, Completion)
    assert completion.text == '{"what": "x"}'
    assert completion.tokens_in == 1234
    assert completion.tokens_out == 56
    assert completion.seconds >= 0

    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == MODEL
    assert body["messages"] == messages
    assert body["temperature"] == 0
    assert body["max_tokens"] == 4000
    assert body["seed"] == 0
    assert body["response_format"] == {"type": "json_object"}
    assert body["reasoning"] == {"enabled": False}


def test_gateway_complete_turns_reasoning_off():
    transport = FakeTransport([reply('{"what": "x"}')])
    gateway = Gateway(api_key="test-key", transport=transport)

    gateway.complete(MODEL, [{"role": "user", "content": "u"}], max_tokens=100)

    body = json.loads(transport.requests[0].content)
    assert body["reasoning"] == {"enabled": False}


def test_gateway_complete_reads_a_null_content_as_empty_text():
    body = reply("placeholder", tokens_in=500, tokens_out=6000)
    body["choices"][0]["message"]["content"] = None
    transport = FakeTransport([body])
    gateway = Gateway(api_key="test-key", transport=transport)

    completion = gateway.complete(MODEL, [{"role": "user", "content": "u"}], max_tokens=6000)

    assert completion.text == ""
    assert completion.tokens_in == 500
    assert completion.tokens_out == 6000


def test_gateway_complete_raises_on_a_non_200_reply():
    transport = httpx.MockTransport(lambda request: httpx.Response(429, json={"error": {"message": "slow down"}}))
    gateway = Gateway(api_key="test-key", transport=transport)
    with pytest.raises(httpx.HTTPStatusError):
        gateway.complete(MODEL, [{"role": "user", "content": "u"}], max_tokens=10)


# ---------------------------------------------------------------- gateway: ledger


def test_gateway_ledger_reads_the_last_balance_and_the_phase_spend(tmp_path):
    path = tmp_path / "LEDGER.md"
    write_ledger(
        path,
        [
            ("2026-09-05", "", "", "", 0, 0, 0.0, 50.0),
            ("2026-09-06", "atlas", "2", MODEL, 100000, 50000, 0.0155, 49.9845),
            ("2026-09-06", "northwind", "2", MODEL, 10000, 5000, 0.0016, 49.9829),
            ("2026-09-07", "atlas", "5", MODEL, 10000, 5000, 0.0016, 49.9813),
        ],
    )
    ledger = Ledger(path)
    assert ledger.balance() == pytest.approx(49.9813)
    assert ledger.spent(2) == pytest.approx(0.0171)
    assert ledger.spent(5) == pytest.approx(0.0016)
    assert ledger.spent(3) == 0.0


def test_gateway_batch_prints_the_estimate_and_the_price_before_any_request(tmp_path, capsys):
    path = tmp_path / "LEDGER.md"
    write_ledger(path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    ledger = Ledger(path)
    transport = FakeTransport([reply("{}", tokens_in=3000, tokens_out=700)])
    gateway = Gateway(api_key="k", transport=transport)

    with ledger.batch("atlas", PHASE, MODEL, tokens_in=2800, tokens_out=800) as batch:
        printed = capsys.readouterr().out
        assert transport.requests == []
        assert "estimate" in printed
        assert "2800" in printed
        assert f"${price(MODEL, 2800, 800):.4f}" in printed
        batch.record(gateway.complete(MODEL, [{"role": "user", "content": "u"}], max_tokens=800))

    rows = ledger_rows(path)
    assert len(rows) == 2
    row = rows[-1]
    assert (row["sample"], row["phase"], row["model"]) == ("atlas", "2", MODEL)
    assert (row["tokens_in"], row["tokens_out"]) == (3000, 700)
    assert row["dollars"] == round(price(MODEL, 3000, 700), 4)
    assert row["balance"] == pytest.approx(round(50.0 - row["dollars"], 4))
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["date"])
    assert path.read_text(encoding="utf-8").endswith("|\n")


def test_gateway_batch_sums_every_completion_into_one_line(tmp_path):
    path = tmp_path / "LEDGER.md"
    write_ledger(path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    ledger = Ledger(path)
    transport = FakeTransport([reply("{}", 1000, 100), reply("{}", 2000, 200), reply("{}", 3000, 300)])
    gateway = Gateway(api_key="k", transport=transport)

    with ledger.batch("atlas", PHASE, MODEL, tokens_in=6000, tokens_out=600) as batch:
        for _ in range(3):
            batch.record(gateway.complete(MODEL, [{"role": "user", "content": "u"}], max_tokens=200))

    rows = ledger_rows(path)
    assert len(rows) == 2
    assert (rows[-1]["tokens_in"], rows[-1]["tokens_out"]) == (6000, 600)
    assert rows[-1]["dollars"] == round(price(MODEL, 6000, 600), 4)


def test_gateway_batch_refuses_past_the_phase_cap_before_any_request(tmp_path):
    path = tmp_path / "LEDGER.md"
    write_ledger(
        path,
        [
            ("2026-09-05", "", "", "", 0, 0, 0.0, 50.0),
            ("2026-09-06", "atlas", "2", MODEL, 100_000_000, 10_000_000, 7.9, 42.1),
        ],
    )
    before = path.read_bytes()
    ledger = Ledger(path)
    transport = FakeTransport([reply("{}")])
    gateway = Gateway(api_key="k", transport=transport)
    # $7.90 spent in phase 2; 2m tokens in at $0.065/m is $0.13 more, past the $8 cap.
    assert ledger.spent(PHASE) + price(MODEL, 2_000_000, 0) > PHASE_CAP

    with pytest.raises(CapExceeded):
        with ledger.batch("atlas", PHASE, MODEL, tokens_in=2_000_000, tokens_out=0) as batch:
            batch.record(gateway.complete(MODEL, [{"role": "user", "content": "u"}], max_tokens=10))

    assert transport.requests == []
    assert path.read_bytes() == before


def test_gateway_batch_refuses_past_the_total_ceiling_before_any_request(tmp_path):
    path = tmp_path / "LEDGER.md"
    write_ledger(
        path,
        [
            ("2026-09-05", "", "", "", 0, 0, 0.0, 50.0),
            ("2026-09-06", "atlas", "7", MODEL, 100_000_000, 10_000_000, 49.95, 0.05),
        ],
    )
    before = path.read_bytes()
    ledger = Ledger(path)
    transport = FakeTransport([reply("{}")])
    gateway = Gateway(api_key="k", transport=transport)
    # $0.05 left of the $50; 2m tokens in is $0.13, past the ceiling, though phase 2 has spent nothing.
    assert ledger.spent(PHASE) == 0.0

    with pytest.raises(CapExceeded):
        with ledger.batch("atlas", PHASE, MODEL, tokens_in=2_000_000, tokens_out=0) as batch:
            batch.record(gateway.complete(MODEL, [{"role": "user", "content": "u"}], max_tokens=10))

    assert transport.requests == []
    assert path.read_bytes() == before


def test_gateway_batch_writes_nothing_when_a_call_fails(tmp_path):
    path = tmp_path / "LEDGER.md"
    write_ledger(path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    before = path.read_bytes()
    ledger = Ledger(path)
    transport = httpx.MockTransport(lambda request: httpx.Response(500, json={"error": {"message": "down"}}))
    gateway = Gateway(api_key="k", transport=transport)

    with pytest.raises(httpx.HTTPStatusError):
        with ledger.batch("atlas", PHASE, MODEL, tokens_in=100, tokens_out=10) as batch:
            batch.record(gateway.complete(MODEL, [{"role": "user", "content": "u"}], max_tokens=10))

    assert path.read_bytes() == before


# ---------------------------------------------------------------- notes: quote verification


def section(ordinal: int, text: str, doc: str = DR_069) -> dict:
    return {
        "anchor": f"{doc}#p1l{ordinal * 10}",
        "doc": doc,
        "heading": None,
        "kind": "text",
        "ordinal": ordinal,
        "text": text,
        "warning": None,
    }


def test_one_document_straighten_collapses_whitespace_and_straightens_quotes():
    assert straighten("  a \n\t b  ") == "a b"
    assert straighten("“quoted” and ‘single’ and it’s") == '"quoted" and \'single\' and it\'s'
    assert straighten("Keep Case") == "Keep Case"


def test_one_document_locate_quote_finds_a_quote_in_one_section():
    sections = [
        section(1, "First block of text."),
        section(2, "On the present evidence,\na bulk export is probable; the read volume is large."),
        section(3, "Third."),
    ]
    assert locate_quote("bulk export is probable", sections) == f"{DR_069}#p1l20"
    assert locate_quote("a bulk export is probable; the read volume", sections) == f"{DR_069}#p1l20"
    assert locate_quote("First block of text.", sections) == f"{DR_069}#p1l10"


def test_one_document_locate_quote_spans_two_adjacent_sections_joined_by_one_space():
    sections = [
        section(1, "The access pattern is inconsistent with any"),
        section(2, "scheduled restore or analytics job."),
        section(3, "Unrelated."),
    ]
    assert locate_quote("inconsistent with any scheduled restore", sections) == f"{DR_069}#p1l10"
    assert locate_quote("any scheduled restore or analytics job. Unrelated.", sections) is None


def test_one_document_locate_quote_is_case_exact_and_straightens_the_quote():
    sections = [section(1, "It’s a “draft” finding.")]
    assert locate_quote("It's a \"draft\" finding.", sections) == f"{DR_069}#p1l10"
    assert locate_quote("it's a \"draft\" finding.", sections) is None
    assert locate_quote("not in the document", sections) is None
    assert locate_quote("", sections) is None


def test_one_document_straighten_drops_markdown_emphasis_marks():
    """A markdown rendering wraps words in ** or _ ; the model quotes the words without them."""
    assert straighten("The proposed acquisition **constitutes a Change of Control** under") == (
        "The proposed acquisition constitutes a Change of Control under"
    )
    assert straighten("(c) **Notwithstanding any other provision.**") == "(c) Notwithstanding any other provision."
    assert straighten("does **not** appear") == "does not appear"
    assert straighten("_Prepared by: the DPO_") == "Prepared by: the DPO"
    assert straighten("`code`") == "code"
    # An underscore inside a word is part of the word, not a mark.
    assert straighten("Aurora_Phase1_Technical_Findings_Draft.pdf") == "Aurora_Phase1_Technical_Findings_Draft.pdf"
    assert straighten("a * b") == "a * b"


def test_one_document_locate_quote_ignores_markdown_emphasis_in_the_source():
    sections = [
        section(1, "**5.2 Application to the Transaction.** The proposed acquisition **constitutes a Change of Control** under the foregoing definition."),
        section(2, "(c) **Notwithstanding any other provision of this Agreement, Customer may terminate this Agreement, effective immediately.**"),
        section(3, "| 3 | **TelemetryWorks Inc.** | **NOT LISTED** | **SCCs: none on file.** |"),
    ]
    assert locate_quote("The proposed acquisition constitutes a Change of Control under the foregoing definition.", sections) == f"{DR_069}#p1l10"
    assert locate_quote("Notwithstanding any other provision of this Agreement, Customer may terminate this Agreement, effective immediately.", sections) == f"{DR_069}#p1l20"
    assert locate_quote("SCCs: none on file.", sections) == f"{DR_069}#p1l30"
    # A quote that keeps the marks verifies as well.
    assert locate_quote("**constitutes a Change of Control**", sections) == f"{DR_069}#p1l10"


def test_one_document_verify_items_keeps_a_figure_whose_surface_was_bold_in_the_source():
    sections = [section(1, "an annual subscription fee of Twelve Million U.S. Dollars (**US $12,400,000**) per year")]
    items = [{"surface": "US $12,400,000", "quote": "an annual subscription fee of Twelve Million U.S. Dollars (US $12,400,000) per year"}]
    kept, dropped = verify_items(DR_069, "figures", items, sections)
    assert dropped == []
    assert kept[0]["anchor"] == f"{DR_069}#p1l10"


def test_one_document_the_prompt_asks_for_a_multi_sentence_clause_whole():
    """A termination or change-of-control clause of more than one sentence is quoted whole."""
    assert "whole" in SYSTEM_PROMPT
    assert "change of control" in SYSTEM_PROMPT.casefold()


def test_one_document_note_name_is_the_key_document_id():
    assert note_name("DR-069") == "DR-069.json"
    assert note_name("sample_data_room/Northwind_Logistics/arr_schedule.xlsx.md") == (
        "sample_data_room__Northwind_Logistics__arr_schedule.xlsx.md.json"
    )


# ---------------------------------------------------------------- notes: the shape of a reply


SENTENCE = "Management recommends a reserve of $12m at this time, pending counsel's view."
DRIFT_SECTIONS = [section(1, SENTENCE)]


def test_one_document_verify_items_keeps_an_item_that_carries_every_required_key():
    items = [{"surface": "$12m", "quote": "Management recommends a reserve of $12m"}]
    kept, dropped = verify_items(DR_069, "figures", items, DRIFT_SECTIONS)
    assert dropped == []
    assert kept == [
        {"surface": "$12m", "quote": "Management recommends a reserve of $12m", "anchor": f"{DR_069}#p1l10"}
    ]


def test_one_document_verify_items_drops_an_item_missing_a_required_key():
    """The model's own key names are not the schema: a figure without surface does not verify."""
    items = [{"figure": "$12m", "value": "12", "quote": "Management recommends a reserve of $12m"}]
    kept, dropped = verify_items(DR_069, "figures", items, DRIFT_SECTIONS)
    assert kept == []
    assert len(dropped) == 1
    assert dropped[0]["reason"] == "missing key surface"
    assert dropped[0]["detail"] is None
    assert dropped[0]["quote"] == "Management recommends a reserve of $12m"


def test_one_document_verify_items_drops_an_item_whose_required_key_is_not_a_string():
    items = [{"surface": 12, "quote": "Management recommends a reserve of $12m"}]
    kept, dropped = verify_items(DR_069, "figures", items, DRIFT_SECTIONS)
    assert kept == []
    assert dropped[0]["reason"] == "missing key surface"


def test_one_document_verify_items_drops_a_cross_reference_without_kind_or_value():
    items = [{"cross_reference": "AURORA", "quote": "Management recommends a reserve of $12m"}]
    kept, dropped = verify_items(DR_069, "cross_references", items, DRIFT_SECTIONS)
    assert kept == []
    assert dropped[0]["reason"] == "missing key kind"
    assert dropped[0]["detail"] is None


def test_one_document_verify_items_drops_a_concealed_item_without_claim():
    items = [{"concealed": "the reserve is soft", "quote": "Management recommends a reserve of $12m"}]
    kept, dropped = verify_items(DR_069, "concealed", items, DRIFT_SECTIONS)
    assert kept == []
    assert dropped[0]["reason"] == "missing key claim"


def test_one_document_verify_items_gives_the_reason_of_every_failure():
    quote = "Management recommends a reserve of $12m"
    _, not_verbatim = verify_items(DR_069, "figures", [{"surface": "$12m", "quote": "management recommends"}], DRIFT_SECTIONS)
    assert not_verbatim[0]["reason"] == "quote not found verbatim"
    _, bad_surface = verify_items(DR_069, "figures", [{"surface": "$12.0m", "quote": quote}], DRIFT_SECTIONS)
    assert bad_surface[0]["reason"] == "surface not inside the quote"
    _, bad_kind = verify_items(DR_069, "cross_references", [{"kind": "amount", "value": "$12m", "quote": quote}], DRIFT_SECTIONS)
    assert bad_kind[0]["reason"] == "kind not one of " + ", ".join(sorted(CROSS_REFERENCE_KINDS))


def test_one_document_item_detail_names_the_item_inside_its_field():
    quote = "Management recommends a reserve of $12m"
    assert item_detail("flags", {"flag": "The reserve is soft", "quote": quote}) == "The reserve is soft"
    assert item_detail("figures", {"surface": "$12m", "quote": quote}) == "$12m"
    assert item_detail("cross_references", {"kind": "code", "value": "AURORA", "quote": quote}) == "code: AURORA"
    assert item_detail("concealed", {"claim": "Counsel's view is not given", "quote": quote}) == "Counsel's view is not given"
    assert item_detail("figures", {"quote": quote}) is None
    assert item_detail("cross_references", {"kind": "code", "quote": quote}) is None
    assert item_detail("flags", "not a dict") is None


def test_one_document_verify_items_carries_the_detail_of_a_dropped_item():
    items = [{"surface": "$12.0m", "quote": "Management recommends a reserve of $12m"}]
    _, dropped = verify_items(DR_069, "figures", items, DRIFT_SECTIONS)
    assert dropped[0]["detail"] == "$12.0m"


def test_one_document_verify_items_keeps_an_exact_duplicate_once():
    """One reply often writes the same figure twice; the note carries it once."""
    item = {"surface": "$12m", "quote": "Management recommends a reserve of $12m"}
    kept, dropped = verify_items(DR_069, "figures", [dict(item), dict(item), dict(item)], DRIFT_SECTIONS)
    assert len(kept) == 1
    assert dropped == []


def test_one_document_verify_items_keeps_two_items_that_share_a_quote_and_differ():
    quote = "Management recommends a reserve of $12m at this time"
    items = [{"surface": "$12m", "quote": quote}, {"surface": "12m", "quote": quote}]
    kept, dropped = verify_items(DR_069, "figures", items, DRIFT_SECTIONS)
    assert [figure["surface"] for figure in kept] == ["$12m", "12m"]
    assert dropped == []


def test_one_document_well_shaped_wants_what_and_at_least_one_list_key():
    assert well_shaped({"what": "x", "flags": [], "figures": [], "cross_references": [], "concealed": []})
    assert well_shaped({"what": "x", "flags": []})
    assert not well_shaped({"what": "", "flags": []})
    assert not well_shaped({"flags": [], "figures": []})
    assert not well_shaped({"what": "x"})
    assert not well_shaped({"what": "x", "summary": [], "numbers": []})
    assert not well_shaped({"what": 3, "flags": []})


def test_one_document_the_prompt_stays_inside_its_budget():
    """The system prompt is under 3800 characters and one note is capped at 6000 output tokens."""
    assert len(SYSTEM_PROMPT) < 3800
    assert MAX_OUTPUT_TOKENS == 6000


# ---------------------------------------------------------------- notes: main with a fake gateway


def atlas_sections() -> list[dict]:
    path = ROOT / "runs" / "atlas" / "sections.jsonl"
    if not path.exists():
        pytest.skip("runs/atlas/sections.jsonl absent; run phase 1 ingest first")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


CANNED_NOTE = {
    "what": "Draft forensic findings on the October 2025 legacy backup exposure.",
    "flags": [
        {
            "flag": "Exfiltration assessed as probable",
            "quote": "On the present evidence, bulk export is probable",
            "consequence": "Contradicts the final report's softer wording.",
        },
        {
            "flag": "A quote the model made up",
            "quote": "the attacker was identified as a state actor",
            "consequence": "Should be dropped by verification.",
        },
    ],
    "figures": [
        {"surface": "~8.4m", "quote": "~8.4m legacy small-business accounts"},
        {"surface": "912.8m", "quote": "Peak/cumulative egress on the legacy backup prefix"},
    ],
    "cross_references": [
        {"kind": "code", "value": "AURORA", "quote": "AURORA"},
        {"kind": "person", "value": "Renata Castellano", "quote": "Prepared by / owner Renata Castellano"},
    ],
    "concealed": [
        {"claim": "Findings are hedged as draft.", "quote": "Further work is required before any of the above can be stated as a definitive finding."}
    ],
}


def canned_note_without_the_bad_items() -> dict:
    """CANNED_NOTE with the two items verification drops taken out, as a second reply."""
    clean = json.loads(json.dumps(CANNED_NOTE))
    del clean["flags"][1]
    del clean["figures"][1]
    return clean


def test_one_document_main_writes_a_verified_note_a_verify_log_and_one_ledger_line(tmp_path, capsys):
    sections = atlas_sections()
    doc_sections = [record for record in sections if record["doc"] == DR_069]
    assert doc_sections
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    transport = FakeTransport(
        [
            reply(json.dumps(CANNED_NOTE), tokens_in=2500, tokens_out=400),
            reply(json.dumps(canned_note_without_the_bad_items()), tokens_in=3000, tokens_out=300),
        ]
    )
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--only", "DR-069", "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    printed = capsys.readouterr().out
    assert code == 0

    # The estimate and the price are printed before the call.
    document_text = "\n".join(record["text"] for record in doc_sections)
    assert "estimate" in printed
    assert str(estimate_tokens(document_text)) in printed or "tokens" in printed
    assert "$" in printed
    # Two items of the canned reply fail verification, so the document is asked again.
    assert len(transport.requests) == 2

    # The model saw the section text in ordinal order and no anchor.
    body = json.loads(transport.requests[0].content)
    sent = "\n".join(message["content"] for message in body["messages"])
    assert "bulk export is probable" in sent
    assert "#p1l25" not in sent
    assert body["temperature"] == 0

    # The note.
    note_path = out / "notes" / "DR-069.json"
    assert note_path.exists()
    raw = note_path.read_text(encoding="utf-8")
    note = json.loads(raw)
    assert raw == json.dumps(note, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    assert set(note) == NOTE_KEYS
    assert note["doc"] == DR_069
    assert note["model"] == MODEL
    assert note["pass"] == "a"
    assert note["what"] == CANNED_NOTE["what"]

    assert [flag["flag"] for flag in note["flags"]] == ["Exfiltration assessed as probable"]
    assert note["flags"][0]["anchor"] == f"{DR_069}#p2l13"
    assert note["flags"][0]["consequence"] == "Contradicts the final report's softer wording."

    assert [figure["surface"] for figure in note["figures"]] == ["~8.4m"]
    assert note["figures"][0]["anchor"] in {f"{DR_069}#p1l49", f"{DR_069}#p1t1r5"}

    assert [(ref["kind"], ref["value"]) for ref in note["cross_references"]] == [("code", "AURORA"), ("person", "Renata Castellano")]
    assert all(ref["anchor"].startswith(DR_069 + "#") for ref in note["cross_references"])

    assert len(note["concealed"]) == 1
    assert note["concealed"][0]["anchor"] == f"{DR_069}#p2l23"

    assert note["usage"]["tokens_in"] == 5500
    assert note["usage"]["tokens_out"] == 700
    assert note["usage"]["dollars"] == pytest.approx(price(MODEL, 5500, 700))
    assert note["usage"]["calls"] == 2
    assert note["usage"]["seconds"] >= 0

    # The verify log: one record per failed item, sorted by document then field then item.
    log_path = out / "notes-verify.jsonl"
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [(r["field"], r["item"], r["outcome"], r["attempt"]) for r in records] == [
        ("figures", 1, "re-asked", 1),
        ("flags", 1, "re-asked", 1),
    ]
    assert records[0]["quote"] == "Peak/cumulative egress on the legacy backup prefix"
    assert records[0]["detail"] == "912.8m"
    assert records[1]["quote"] == "the attacker was identified as a state actor"
    assert records[1]["detail"] == "A quote the model made up"
    assert all(set(r) == LOG_KEYS for r in records)
    assert all(r["doc"] == DR_069 for r in records)

    # The ledger line.
    rows = ledger_rows(ledger_path)
    assert len(rows) == 2
    assert (rows[-1]["sample"], rows[-1]["phase"], rows[-1]["model"]) == ("atlas", "2", MODEL)
    assert (rows[-1]["tokens_in"], rows[-1]["tokens_out"]) == (5500, 700)
    assert rows[-1]["dollars"] == round(price(MODEL, 5500, 700), 4)
    assert rows[-1]["balance"] == pytest.approx(round(50.0 - rows[-1]["dollars"], 4))


def test_one_document_main_drops_a_note_whose_reply_does_not_parse(tmp_path, capsys):
    """A reply that is not one JSON object is asked again once, then the note is dropped whole."""
    atlas_sections()
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    transport = FakeTransport(
        [
            reply("not json at all", tokens_in=2500, tokens_out=10),
            reply("still not json", tokens_in=2600, tokens_out=20),
        ]
    )
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--only", DR_069, "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    capsys.readouterr()
    assert code == 0
    assert len(transport.requests) == 2
    second = json.loads(transport.requests[1].content)["messages"]
    assert [message["role"] for message in second] == ["system", "user", "assistant", "user"]
    assert second[2]["content"] == "not json at all"
    assert "JSON" in second[3]["content"]
    assert not (out / "notes" / "DR-069.json").exists()
    records = [json.loads(line) for line in (out / "notes-verify.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert (records[0]["doc"], records[0]["field"], records[0]["item"]) == (DR_069, None, None)
    assert (records[0]["outcome"], records[0]["attempt"]) == ("note-dropped", 2)
    # Both calls were made and are paid for, so the ledger carries them.
    rows = ledger_rows(ledger_path)
    assert len(rows) == 2
    assert (rows[-1]["tokens_in"], rows[-1]["tokens_out"]) == (5100, 30)


# ---------------------------------------------------------------- notes: the whole sample


MINIMAL_NOTE = {"what": "x", "flags": [], "figures": [], "cross_references": [], "concealed": []}


def atlas_sections_by_doc() -> dict[str, list[dict]]:
    """The sections of runs/atlas, one list per document in ordinal order."""
    by_doc: dict[str, list[dict]] = {}
    for record in atlas_sections():
        by_doc.setdefault(record["doc"], []).append(record)
    for records in by_doc.values():
        records.sort(key=lambda record: record["ordinal"])
    return by_doc


def test_all_documents_main_notes_every_document_of_the_key(tmp_path, capsys):
    """Without --only every document the key names is noted, under one estimate and one row."""
    by_doc = atlas_sections_by_doc()
    key = load_key(ROOT / "samples" / "atlas")
    assert len(key.documents) == 100
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    transport = FakeTransport(
        [reply(json.dumps(MINIMAL_NOTE), tokens_in=2500, tokens_out=400) for _ in key.documents]
    )
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    printed = capsys.readouterr().out
    assert code == 0
    assert len(transport.requests) == 100

    # One estimate, printed before any request, covering every document of the pass.
    expected_in = sum(
        estimate_tokens("\n".join(message["content"] for message in build_messages(by_doc[path])))
        for path in key.documents.values()
    )
    assert printed.count("estimate:") == 1
    assert str(expected_in) in printed
    assert printed.index("estimate:") < printed.index("noted 100")

    written = sorted(path.name for path in (out / "notes").glob("*.json"))
    assert written == sorted(note_name(doc_id) for doc_id in key.documents)

    rows = ledger_rows(ledger_path)
    assert len(rows) == 2
    assert (rows[-1]["tokens_in"], rows[-1]["tokens_out"]) == (250_000, 40_000)

    raw = (out / "notes-summary.json").read_text(encoding="utf-8")
    summary = json.loads(raw)
    assert set(summary) == SUMMARY_KEYS
    assert list(summary) == sorted(summary)
    assert raw.endswith("}\n")
    assert summary["documents"] == 100
    assert summary["noted"] == 100
    assert summary["dropped"] == 0
    assert summary["verified"] == 0
    assert summary["re_asked"] == 0
    assert summary["dropped_items"] == 0
    assert summary["tokens_in"] == 250_000
    assert summary["tokens_out"] == 40_000
    assert summary["dollars"] == pytest.approx(price(MODEL, 250_000, 40_000))
    assert summary["seconds"] >= 0
    assert (summary["model"], summary["pass"], summary["sample"]) == (MODEL, "a", "atlas")


def test_all_documents_reask_asks_again_with_the_failed_quotes(tmp_path, capsys):
    """A document whose items fail is asked once more, with those quotes and its first reply."""
    atlas_sections()
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    first_text = json.dumps(CANNED_NOTE)
    transport = FakeTransport(
        [
            reply(first_text, tokens_in=2500, tokens_out=400),
            reply(json.dumps(canned_note_without_the_bad_items()), tokens_in=3000, tokens_out=300),
        ]
    )
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--only", "DR-069", "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    capsys.readouterr()
    assert code == 0
    assert len(transport.requests) == 2

    first_messages = json.loads(transport.requests[0].content)["messages"]
    second_messages = json.loads(transport.requests[1].content)["messages"]
    assert [message["role"] for message in second_messages] == ["system", "user", "assistant", "user"]
    assert second_messages[:2] == first_messages
    assert second_messages[2]["content"] == first_text
    asked = second_messages[3]["content"]
    assert "the attacker was identified as a state actor" in asked
    assert "Peak/cumulative egress on the legacy backup prefix" in asked

    note = json.loads((out / "notes" / "DR-069.json").read_text(encoding="utf-8"))
    assert [flag["flag"] for flag in note["flags"]] == ["Exfiltration assessed as probable"]
    assert [figure["surface"] for figure in note["figures"]] == ["~8.4m"]
    assert len(note["cross_references"]) == 2
    assert note["usage"]["calls"] == 2
    assert note["usage"]["tokens_in"] == 5500
    assert note["usage"]["tokens_out"] == 700
    assert note["usage"]["dollars"] == pytest.approx(price(MODEL, 5500, 700))

    records = [json.loads(line) for line in (out / "notes-verify.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(r["field"], r["item"], r["outcome"], r["attempt"]) for r in records] == [
        ("figures", 1, "re-asked", 1),
        ("flags", 1, "re-asked", 1),
    ]


def test_all_documents_reask_drops_what_still_fails(tmp_path, capsys):
    """An item that fails again after the re-ask is dropped from the note and logged at attempt 2."""
    atlas_sections()
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    second_note = canned_note_without_the_bad_items()
    second_note["flags"].append(CANNED_NOTE["flags"][1])
    transport = FakeTransport(
        [
            reply(json.dumps(CANNED_NOTE), tokens_in=2500, tokens_out=400),
            reply(json.dumps(second_note), tokens_in=3000, tokens_out=300),
        ]
    )
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--only", "DR-069", "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    capsys.readouterr()
    assert code == 0
    assert len(transport.requests) == 2

    note = json.loads((out / "notes" / "DR-069.json").read_text(encoding="utf-8"))
    assert [flag["flag"] for flag in note["flags"]] == ["Exfiltration assessed as probable"]
    quotes = {straighten(item["quote"]) for _, _, item in quoted_items(note)}
    assert "the attacker was identified as a state actor" not in quotes

    records = [json.loads(line) for line in (out / "notes-verify.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(r["field"], r["item"], r["outcome"], r["attempt"]) for r in records] == [
        ("figures", 1, "re-asked", 1),
        ("flags", 1, "re-asked", 1),
        ("flags", 1, "dropped", 2),
    ]
    order = [(r["doc"], r["field"] or "", r["item"] if r["item"] is not None else -1, r["attempt"]) for r in records]
    assert order == sorted(order)


def test_all_documents_reask_keeps_an_item_the_second_reply_left_out(tmp_path, capsys):
    """The note is the union of both attempts, so a shrinking second reply loses nothing."""
    atlas_sections()
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    second_note = {
        "what": "A shorter answer.",
        "flags": [
            {
                "flag": "Five bulk-read events in the window",
                "quote": "5 distinct anomalous bulk-read events across the window.",
                "consequence": "Sizes the window of the exposure.",
            }
        ],
        "figures": [],
        "cross_references": [],
        "concealed": [],
    }
    transport = FakeTransport(
        [
            reply(json.dumps(CANNED_NOTE), tokens_in=2500, tokens_out=400),
            reply(json.dumps(second_note), tokens_in=3000, tokens_out=300),
        ]
    )
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--only", "DR-069", "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    capsys.readouterr()
    assert code == 0
    assert len(transport.requests) == 2

    note = json.loads((out / "notes" / "DR-069.json").read_text(encoding="utf-8"))
    assert [flag["flag"] for flag in note["flags"]] == [
        "Exfiltration assessed as probable",
        "Five bulk-read events in the window",
    ]
    assert [figure["surface"] for figure in note["figures"]] == ["~8.4m"]
    assert len(note["cross_references"]) == 2
    assert len(note["concealed"]) == 1
    assert note["what"] == CANNED_NOTE["what"]

    records = [json.loads(line) for line in (out / "notes-verify.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(r["field"], r["item"], r["outcome"], r["attempt"]) for r in records] == [
        ("figures", 1, "re-asked", 1),
        ("flags", 1, "re-asked", 1),
    ]


def test_all_documents_reask_keeps_a_repeated_item_once(tmp_path, capsys):
    """An item the second reply repeats exactly as the first wrote it is in the note once."""
    atlas_sections()
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    second_note = {
        "what": "The same items again.",
        "flags": [CANNED_NOTE["flags"][0]],
        "figures": [CANNED_NOTE["figures"][0]],
        "cross_references": list(CANNED_NOTE["cross_references"]),
        "concealed": list(CANNED_NOTE["concealed"]),
    }
    transport = FakeTransport(
        [
            reply(json.dumps(CANNED_NOTE), tokens_in=2500, tokens_out=400),
            reply(json.dumps(second_note), tokens_in=3000, tokens_out=300),
        ]
    )
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--only", "DR-069", "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    capsys.readouterr()
    assert code == 0

    note = json.loads((out / "notes" / "DR-069.json").read_text(encoding="utf-8"))
    assert [flag["flag"] for flag in note["flags"]] == ["Exfiltration assessed as probable"]
    assert [figure["surface"] for figure in note["figures"]] == ["~8.4m"]
    assert len(note["cross_references"]) == 2
    assert len(note["concealed"]) == 1


def test_all_documents_a_document_with_no_sections_is_dropped_without_a_call(tmp_path, capsys):
    """A key document that sections.jsonl does not carry is logged at attempt 1 and not called."""
    run = tmp_path / "run"
    run.mkdir()
    kept = [record for record in atlas_sections() if record["doc"] == DR_069]
    assert kept
    (run / "sections.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in kept), encoding="utf-8"
    )
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    transport = FakeTransport([reply(json.dumps(MINIMAL_NOTE), tokens_in=2500, tokens_out=400)])
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(run), "--model", MODEL, "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    capsys.readouterr()
    assert code == 0
    assert len(transport.requests) == 1
    assert sorted(path.name for path in (out / "notes").glob("*.json")) == ["DR-069.json"]

    records = [json.loads(line) for line in (out / "notes-verify.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 99
    assert all(r["outcome"] == "note-dropped" for r in records)
    assert all(r["attempt"] == 1 and r["field"] is None and r["item"] is None for r in records)
    assert DR_069 not in {r["doc"] for r in records}

    summary = json.loads((out / "notes-summary.json").read_text(encoding="utf-8"))
    assert (summary["documents"], summary["noted"], summary["dropped"]) == (100, 1, 99)


def test_all_documents_a_call_that_raises_drops_the_note_and_the_pass_goes_on(tmp_path, capsys):
    """A document whose call raises is dropped whole; the rest of the pass still gets noted."""
    atlas_sections()
    key = load_key(ROOT / "samples" / "atlas")
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent = "\n".join(message["content"] for message in body["messages"])
        if "bulk export is probable" in sent:
            return httpx.Response(500, json={"error": {"message": "boom"}})
        return httpx.Response(200, json=reply(json.dumps(MINIMAL_NOTE), tokens_in=2500, tokens_out=400))

    transport = httpx.MockTransport(handle)
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    printed = capsys.readouterr().out
    assert code == 0

    assert not (out / "notes" / "DR-069.json").exists()
    written = sorted(path.name for path in (out / "notes").glob("*.json"))
    expected = sorted(note_name(doc_id) for doc_id in key.documents if doc_id != "DR-069")
    assert written == expected

    records = [json.loads(line) for line in (out / "notes-verify.jsonl").read_text(encoding="utf-8").splitlines()]
    dropped_records = [r for r in records if r["doc"] == DR_069]
    assert dropped_records == [
        {
            "doc": DR_069,
            "field": None,
            "item": None,
            "quote": None,
            "detail": None,
            "outcome": "note-dropped",
            "attempt": 1,
        }
    ]

    rows = ledger_rows(ledger_path)
    assert len(rows) == 2
    assert (rows[-1]["tokens_in"], rows[-1]["tokens_out"]) == (2500 * 99, 400 * 99)

    summary = json.loads((out / "notes-summary.json").read_text(encoding="utf-8"))
    assert (summary["documents"], summary["noted"], summary["dropped"]) == (100, 99, 1)

    assert "DR-069: note dropped" in printed


# The shape a live reply took when the model used its own key names: no what, no surface, no kind.
DRIFTED_REPLY = {
    "summary": "A dashboard of weekly product metrics.",
    "figures": [
        {"figure": "~8.4m", "value": "8400000", "quote": "~8.4m legacy small-business accounts"}
    ],
    "cross_references": [{"cross_reference": "AURORA", "quote": "AURORA"}],
    "concealed": [{"concealed": "The draft hedges.", "quote": "Further work is required"}],
}


def test_all_documents_a_reply_with_the_models_own_keys_is_reasked_then_note_dropped(tmp_path, capsys):
    """A reply without what, or without any of the four lists, is asked again with the key names."""
    atlas_sections()
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    drifted = json.dumps(DRIFTED_REPLY)
    transport = FakeTransport(
        [reply(drifted, tokens_in=2500, tokens_out=179), reply(drifted, tokens_in=2600, tokens_out=179)]
    )
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--only", "DR-069", "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    capsys.readouterr()
    assert code == 0
    assert len(transport.requests) == 2

    asked = json.loads(transport.requests[1].content)["messages"][3]["content"]
    for name in ("what", "flags", "figures", "cross_references", "concealed", "surface", "kind", "claim"):
        assert name in asked, name

    assert not (out / "notes" / "DR-069.json").exists()
    records = [json.loads(line) for line in (out / "notes-verify.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert (records[0]["outcome"], records[0]["attempt"]) == ("note-dropped", 2)
    assert records[0]["detail"] is None
    assert set(records[0]) == LOG_KEYS


def test_all_documents_the_reask_names_the_field_the_reason_and_the_quote(tmp_path, capsys):
    """An item whose keys drifted is a failed item: the re-ask says which field and why."""
    atlas_sections()
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    first = {
        "what": "Draft forensic findings on the October 2025 legacy backup exposure.",
        "flags": [],
        "figures": [
            {"figure": "~8.4m", "value": "8400000", "quote": "~8.4m legacy small-business accounts"}
        ],
        "cross_references": [],
        "concealed": [],
    }
    second = json.loads(json.dumps(first))
    second["figures"] = [{"surface": "~8.4m", "quote": "~8.4m legacy small-business accounts"}]
    transport = FakeTransport(
        [
            reply(json.dumps(first), tokens_in=2500, tokens_out=400),
            reply(json.dumps(second), tokens_in=3000, tokens_out=300),
        ]
    )
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--only", "DR-069", "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    capsys.readouterr()
    assert code == 0
    assert len(transport.requests) == 2

    asked = json.loads(transport.requests[1].content)["messages"][3]["content"]
    assert "figures" in asked
    assert "missing key surface" in asked
    assert "~8.4m legacy small-business accounts" in asked

    note = json.loads((out / "notes" / "DR-069.json").read_text(encoding="utf-8"))
    assert [figure["surface"] for figure in note["figures"]] == ["~8.4m"]

    records = [json.loads(line) for line in (out / "notes-verify.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(r["field"], r["item"], r["detail"], r["outcome"], r["attempt"]) for r in records] == [
        ("figures", 0, None, "re-asked", 1)
    ]


def test_all_documents_every_reply_is_written_to_notes_raw(tmp_path, capsys):
    """Both replies of a re-asked document are kept verbatim under notes-raw, one per attempt."""
    atlas_sections()
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    first_text = json.dumps(CANNED_NOTE)
    second_text = json.dumps(canned_note_without_the_bad_items())
    transport = FakeTransport(
        [
            reply(first_text, tokens_in=2500, tokens_out=400),
            reply(second_text, tokens_in=3000, tokens_out=300),
        ]
    )
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--only", "DR-069", "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    capsys.readouterr()
    assert code == 0
    assert len(transport.requests) == 2

    raw_dir = out / "notes-raw"
    assert sorted(path.name for path in raw_dir.glob("*.txt")) == ["DR-069.1.txt", "DR-069.2.txt"]
    assert (raw_dir / "DR-069.1.txt").read_text(encoding="utf-8") == first_text
    assert (raw_dir / "DR-069.2.txt").read_text(encoding="utf-8") == second_text


# ---------------------------------------------------------------- notes: the artefact


# The three gate samples, in the order the readout prints them.
ENABLED = ("atlas", "northwind", "northstar-dental")

_NOTED: dict[str, tuple[Path, dict]] = {}


@pytest.fixture
def key(sample_dir):
    return load_key(sample_dir)


@pytest.fixture
def notes(run_dir, sample):
    """Every note under runs/<sample>/notes/, keyed by file name, or a skip when there are none."""
    notes_dir = run_dir / "notes"
    if not notes_dir.is_dir():
        pytest.skip(SKIP_REASON)
    found = {}
    for path in sorted(notes_dir.glob("*.json")):
        raw = path.read_text(encoding="utf-8")
        found[path.name] = (raw, json.loads(raw))
    if not found:
        pytest.skip(SKIP_REASON)
    _NOTED[sample] = (run_dir, found)
    return found


@pytest.fixture
def sections_by_doc(run_dir):
    path = run_dir / "sections.jsonl"
    by_doc: dict[str, list[dict]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        by_doc.setdefault(record["doc"], []).append(record)
    return by_doc


def quoted_items(note: dict):
    """Yields (field, index, item) for every item of the note's quoted fields."""
    for field in QUOTED_FIELDS:
        for index, item in enumerate(note[field]):
            yield field, index, item


def test_one_document_note_is_well_shaped(notes, key):
    ids_by_path = {path: doc_id for doc_id, path in key.documents.items()}
    for name, (raw, note) in notes.items():
        assert raw == json.dumps(note, indent=1, sort_keys=True, ensure_ascii=False) + "\n", name
        assert set(note) == NOTE_KEYS, name
        assert note["doc"] in ids_by_path, name
        assert name == note_name(ids_by_path[note["doc"]]), name
        assert note["model"] in PRICES, name
        assert note["pass"] in ("a", "b"), name
        assert isinstance(note["what"], str) and note["what"].strip(), name
        for field in QUOTED_FIELDS:
            assert isinstance(note[field], list), (name, field)
        for flag in note["flags"]:
            assert set(flag) == {"flag", "quote", "anchor", "consequence"}, name
        for figure in note["figures"]:
            assert set(figure) == {"surface", "quote", "anchor"}, name
        for ref in note["cross_references"]:
            assert set(ref) == {"kind", "value", "quote", "anchor"}, name
            assert ref["kind"] in CROSS_REFERENCE_KINDS, (name, ref["kind"])
        for item in note["concealed"]:
            assert set(item) == {"claim", "quote", "anchor"}, name
        usage = note["usage"]
        assert set(usage) == {"tokens_in", "tokens_out", "dollars", "seconds", "calls"}, name
        assert usage["tokens_in"] > 0 and usage["tokens_out"] > 0, name
        assert usage["calls"] in (1, 2), name
        assert usage["dollars"] == pytest.approx(price(note["model"], usage["tokens_in"], usage["tokens_out"])), name


def test_one_document_every_quote_is_verified_and_anchored_by_code(notes, sections_by_doc):
    for name, (_, note) in notes.items():
        doc_sections = sections_by_doc[note["doc"]]
        for field, index, item in quoted_items(note):
            where = (name, field, index)
            anchor = locate_quote(item["quote"], doc_sections)
            assert anchor is not None, where
            assert item["anchor"] == anchor, where
            parsed = parse_anchor(item["anchor"])
            assert parsed.doc == note["doc"], where
            assert item["anchor"] in {record["anchor"] for record in doc_sections}, where
        for index, figure in enumerate(note["figures"]):
            assert straighten(figure["surface"]) in straighten(figure["quote"]), (name, "figures", index)


def test_one_document_carries_its_planted_quotes(notes, key):
    """Every phase 2 fact whose document has a note is inside one verified quote of that note."""
    by_path = {note["doc"]: note for _, note in notes.values()}
    checked = 0
    for fact in key.facts:
        if fact.phase != PHASE:
            continue
        assert fact.kind == "quote", fact.id
        noted = [by_path[key.documents[doc_id]] for doc_id in fact.documents if key.documents[doc_id] in by_path]
        if not noted:
            continue
        checked += 1
        wanted = straighten(fact.value)
        hits = [
            note["doc"]
            for note in noted
            for _, _, item in quoted_items(note)
            if wanted in straighten(item["quote"])
        ]
        assert hits, f"{fact.id}: {fact.value!r} not inside any verified quote of {[n['doc'] for n in noted]}"
    assert checked >= 1


def test_one_document_verify_log_is_well_shaped_and_sorted(run_dir, notes):
    path = run_dir / "notes-verify.jsonl"
    assert path.exists()
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for record in records:
        assert set(record) == LOG_KEYS
        assert record["outcome"] in ("re-asked", "dropped", "note-dropped")
        assert record["attempt"] in (1, 2)
        if record["outcome"] == "note-dropped":
            assert record["field"] is None and record["item"] is None
            assert record["detail"] is None
        else:
            assert record["field"] in QUOTED_FIELDS and isinstance(record["item"], int)
            assert record["detail"] is None or isinstance(record["detail"], str)
    order = [(r["doc"], r["field"] or "", r["item"] if r["item"] is not None else -1, r["attempt"]) for r in records]
    assert order == sorted(order)


def test_one_document_ledger_carries_the_pass(notes, sample):
    """Each (model, pass) of the notes sums to one ledger line of this sample and phase, and
    every line's balance is the previous balance minus its dollars."""
    rows = ledger_rows(ROOT / "LEDGER.md")
    assert rows and rows[0]["balance"] == 50.0
    for previous, row in zip(rows, rows[1:]):
        assert row["balance"] == pytest.approx(round(previous["balance"] - row["dollars"], 4)), row
        if row["model"] in PRICES:
            assert row["dollars"] == round(price(row["model"], row["tokens_in"], row["tokens_out"]), 4), row

    sums: dict[tuple[str, str], list[int]] = {}
    for _, note in notes.values():
        total = sums.setdefault((note["model"], note["pass"]), [0, 0])
        total[0] += note["usage"]["tokens_in"]
        total[1] += note["usage"]["tokens_out"]
    for (model, _), (tokens_in, tokens_out) in sums.items():
        matching = [
            row
            for row in rows
            if (row["sample"], row["phase"], row["model"]) == (sample, str(PHASE), model)
            and row["tokens_in"] >= tokens_in
            and row["tokens_out"] >= tokens_out
        ]
        assert matching, (model, tokens_in, tokens_out)


def test_one_document_dr_069_is_noted_on_atlas(notes, sample):
    """The slice 01 deliverable: DR-069 of sample 1 has a note with the planted quote verified."""
    if sample != "atlas":
        pytest.skip("DR-069 is a document of atlas")
    assert "DR-069.json" in notes
    _, note = notes["DR-069.json"]
    assert note["doc"] == DR_069
    assert any("bulk export is probable" in straighten(item["quote"]) for _, _, item in quoted_items(note))


def fold(text: str) -> str:
    """The fold both sides of the recall check take: whitespace, curly quotes, then case."""
    return straighten(text).casefold()


def verify_records(run_dir: Path) -> list[dict]:
    """The records of runs/<sample>/notes-verify.jsonl, in file order."""
    path = run_dir / "notes-verify.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_all_documents_every_key_document_has_a_note_or_a_drop(notes, key, run_dir):
    """The pass leaves nothing silent: each key document is a note file or a note-dropped record."""
    noted = {note["doc"] for _, note in notes.values()}
    dropped = {record["doc"] for record in verify_records(run_dir) if record["outcome"] == "note-dropped"}
    for doc_id, path in key.documents.items():
        assert path in noted or path in dropped, doc_id


def test_all_documents_dropped_items_are_absent_from_their_note(notes, run_dir):
    """A dropped item is told from a kept one by its field, its detail and its quote together.

    Two items of one reply can share a quote and differ in surface or kind, one passing and one
    failing, so the quote alone does not say which record is which.
    """
    by_path = {note["doc"]: note for _, note in notes.values()}
    for record in verify_records(run_dir):
        if record["outcome"] != "dropped":
            continue
        note = by_path.get(record["doc"])
        if note is None:
            continue
        kept = {
            (field, item_detail(field, item), straighten(item["quote"]))
            for field, _, item in quoted_items(note)
        }
        triple = (record["field"], record["detail"], straighten(record["quote"] or ""))
        assert triple not in kept, record


def test_all_documents_summary_counts_the_pass(notes, key, run_dir, sample):
    path = run_dir / "notes-summary.json"
    assert path.exists()
    raw = path.read_text(encoding="utf-8")
    summary = json.loads(raw)
    assert set(summary) == SUMMARY_KEYS
    assert list(summary) == sorted(summary)
    assert raw.endswith("}\n")
    assert summary["sample"] == sample
    assert summary["model"] in PRICES
    assert summary["pass"] in ("a", "b")
    assert summary["documents"] == len(key.documents)
    assert summary["noted"] == len(notes)
    assert summary["noted"] + summary["dropped"] == summary["documents"]
    assert summary["verified"] == sum(
        len(note[field]) for _, note in notes.values() for field in QUOTED_FIELDS
    )
    assert summary["tokens_in"] > 0 and summary["tokens_out"] > 0
    assert summary["dollars"] == pytest.approx(
        price(summary["model"], summary["tokens_in"], summary["tokens_out"])
    )
    assert summary["seconds"] >= 0


def test_all_documents_carry_every_planted_quote(notes, key):
    """Every phase 2 fact of the sample is inside a verified quote of a note of its own documents.

    Both sides are folded the same way: whitespace collapsed, curly quotes straightened, case
    folded. A fact whose documents have no note fails; it is not skipped.
    """
    by_path = {note["doc"]: note for _, note in notes.values()}
    facts = [fact for fact in key.facts if fact.phase == PHASE]
    assert facts
    for fact in facts:
        assert fact.kind == "quote", fact.id
        paths = [key.documents[doc_id] for doc_id in fact.documents]
        noted = [by_path[path] for path in paths if path in by_path]
        wanted = fold(fact.value)
        hits = [
            note["doc"]
            for note in noted
            for _, _, item in quoted_items(note)
            if wanted in fold(item["quote"])
        ]
        quotes = [item["quote"] for note in noted for _, _, item in quoted_items(note)]
        assert hits, f"{fact.id}: {fact.value!r} not inside any verified quote of {paths}; the notes quote {quotes}"


def readout(terminalreporter):
    """Writes, per sample with notes, one pass line and one line per planted quote missed."""
    if not _NOTED:
        return
    terminalreporter.section("phase 2 readout")
    for sample in ENABLED:
        if sample not in _NOTED:
            continue
        run_dir, found = _NOTED[sample]
        summary_path = run_dir / "notes-summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
        key = load_key(ROOT / "samples" / sample)
        by_path = {note["doc"]: note for _, note in found.values()}

        missed = []
        hit = 0
        facts = [fact for fact in key.facts if fact.phase == PHASE]
        for fact in facts:
            noted = [by_path[key.documents[doc_id]] for doc_id in fact.documents if key.documents[doc_id] in by_path]
            wanted = fold(fact.value)
            if any(wanted in fold(item["quote"]) for note in noted for _, _, item in quoted_items(note)):
                hit += 1
            else:
                missed.append(fact)
        total = len(facts)
        recall = (hit / total * 100) if total else 0.0
        terminalreporter.write_line(
            f"phase 2 {sample}: documents noted {summary.get('noted', len(found))}, "
            f"notes dropped {summary.get('dropped', 0)}, "
            f"quotes verified {summary.get('verified', 0)}, "
            f"quotes re-asked {summary.get('re_asked', 0)}, "
            f"quotes dropped {summary.get('dropped_items', 0)}, "
            f"planted recall {recall:.1f}% ({hit} of {total}), "
            f"dollars {summary.get('dollars', 0.0):.4f}, "
            f"seconds {summary.get('seconds', 0.0):.1f}"
        )
        for fact in missed:
            terminalreporter.write_line(f"phase 2 {sample}: missed {fact.id} {fact.value!r}")
