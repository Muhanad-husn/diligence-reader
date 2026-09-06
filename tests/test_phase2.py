"""Phase 2 notes tests. A note is one JSON file per document under runs/<sample>/notes/, written
from one gateway call, with every quote and figure verified against the document's own sections
and anchored by code. These tests read the artefact and never call the model. The gateway's
estimate, refusal and ledger logic is tested with a fake transport that never opens a socket. A
sample whose notes directory is absent is skipped."""

from __future__ import annotations

import json
import re
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
    NOTE_KEYS,
    QUOTED_FIELDS,
    locate_quote,
    main,
    note_name,
    straighten,
)
from rlm.sections import parse_anchor

ROOT = Path(__file__).resolve().parents[1]
SKIP_REASON = "notes not run for this sample yet"
MODEL = "deepseek/deepseek-v4-flash-0731"
PHASE = 2
PHASE_CAP = 8.0
DR_069 = "data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf"

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
    """A transport that records every request and answers each with the next canned reply."""

    def __init__(self, replies: list[dict]):
        self.requests: list[httpx.Request] = []
        self._replies = list(replies)
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
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


def test_one_document_note_name_is_the_key_document_id():
    assert note_name("DR-069") == "DR-069.json"
    assert note_name("sample_data_room/Northwind_Logistics/arr_schedule.xlsx.md") == (
        "sample_data_room__Northwind_Logistics__arr_schedule.xlsx.md.json"
    )


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


def test_one_document_main_writes_a_verified_note_a_verify_log_and_one_ledger_line(tmp_path, capsys):
    sections = atlas_sections()
    doc_sections = [record for record in sections if record["doc"] == DR_069]
    assert doc_sections
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    transport = FakeTransport([reply(json.dumps(CANNED_NOTE), tokens_in=2500, tokens_out=400)])
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
    assert len(transport.requests) == 1

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
    assert note["flags"][0]["anchor"] == f"{DR_069}#p1l25"
    assert note["flags"][0]["consequence"] == "Contradicts the final report's softer wording."

    assert [figure["surface"] for figure in note["figures"]] == ["~8.4m"]
    assert note["figures"][0]["anchor"] in {f"{DR_069}#p1l49", f"{DR_069}#p1t1r5"}

    assert [(ref["kind"], ref["value"]) for ref in note["cross_references"]] == [("code", "AURORA"), ("person", "Renata Castellano")]
    assert all(ref["anchor"].startswith(DR_069 + "#") for ref in note["cross_references"])

    assert len(note["concealed"]) == 1
    assert note["concealed"][0]["anchor"] == f"{DR_069}#p2l23"

    assert note["usage"]["tokens_in"] == 2500
    assert note["usage"]["tokens_out"] == 400
    assert note["usage"]["dollars"] == pytest.approx(price(MODEL, 2500, 400))
    assert note["usage"]["calls"] == 1
    assert note["usage"]["seconds"] >= 0

    # The verify log: one record per dropped item, sorted by document then field then item.
    log_path = out / "notes-verify.jsonl"
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [(r["field"], r["item"], r["outcome"], r["attempt"]) for r in records] == [
        ("figures", 1, "dropped", 1),
        ("flags", 1, "dropped", 1),
    ]
    assert records[0]["quote"] == "Peak/cumulative egress on the legacy backup prefix"
    assert records[1]["quote"] == "the attacker was identified as a state actor"
    assert all(r["doc"] == DR_069 for r in records)

    # The ledger line.
    rows = ledger_rows(ledger_path)
    assert len(rows) == 2
    assert (rows[-1]["sample"], rows[-1]["phase"], rows[-1]["model"]) == ("atlas", "2", MODEL)
    assert (rows[-1]["tokens_in"], rows[-1]["tokens_out"]) == (2500, 400)
    assert rows[-1]["dollars"] == round(price(MODEL, 2500, 400), 4)
    assert rows[-1]["balance"] == pytest.approx(round(50.0 - rows[-1]["dollars"], 4))


def test_one_document_main_drops_a_note_whose_reply_does_not_parse(tmp_path, capsys):
    atlas_sections()
    ledger_path = tmp_path / "LEDGER.md"
    write_ledger(ledger_path, [("2026-09-05", "", "", "", 0, 0, 0.0, 50.0)])
    transport = FakeTransport([reply("not json at all", tokens_in=2500, tokens_out=10)])
    gateway = Gateway(api_key="k", transport=transport)
    out = tmp_path / "out"

    code = main(
        [str(ROOT / "samples" / "atlas"), str(ROOT / "runs" / "atlas"), "--model", MODEL, "--only", DR_069, "--out", str(out)],
        gateway=gateway,
        ledger=Ledger(ledger_path),
    )
    capsys.readouterr()
    assert code == 0
    assert not (out / "notes" / "DR-069.json").exists()
    records = [json.loads(line) for line in (out / "notes-verify.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert (records[0]["doc"], records[0]["field"], records[0]["outcome"]) == (DR_069, None, "note-dropped")
    # The call was made and is paid for, so the ledger carries it.
    assert len(ledger_rows(ledger_path)) == 2


# ---------------------------------------------------------------- notes: the artefact


@pytest.fixture
def key(sample_dir):
    return load_key(sample_dir)


@pytest.fixture
def notes(run_dir):
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
        assert set(record) == {"doc", "field", "item", "quote", "outcome", "attempt"}
        assert record["outcome"] in ("re-asked", "dropped", "note-dropped")
        assert record["attempt"] in (1, 2)
        if record["outcome"] == "note-dropped":
            assert record["field"] is None and record["item"] is None
        else:
            assert record["field"] in QUOTED_FIELDS and isinstance(record["item"], int)
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
