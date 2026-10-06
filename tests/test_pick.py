"""Issue #160 step 3: the pick stage, which ranks a room against the fixed acquisition checklist.

Every test here is free: the gateway and Jev are fakes on httpx mock transports, the ledger is a
temporary file, and the rooms are small ones written by the test or a copy of sample 3's.
"""

import json
import re
from pathlib import Path

import httpx
import pytest

from rlm import cli, ingest, pick, write
from rlm.gateway import PRICES, CapExceeded, Gateway, Ledger, price
from rlm.key import room_documents
from rlm.notes import note_name
from test_phase8_command import RoomTransport, copy_room, reply, write_ledger

SHARE_ONLY = {
    "financial-covenants",
    "debt-change-of-control",
    "cross-default",
    "equity-issuance",
    "anti-dilution",
    "registration-rights",
    "investor-rights",
    "equity-acceleration",
}

# ---------------------------------------------------------------- the checklist


def test_the_share_checklist_is_every_item_of_the_file():
    items = pick.load_checklist("share")
    ids = [item.id for item in items]
    assert len(ids) == 34
    assert len(set(ids)) == len(ids)
    assert ids[0] == "change-of-control"
    assert ids[-1] == "related-party"
    assert all(item.question.endswith("?") for item in items)
    assert all("share" in item.types for item in items)


def test_the_asset_checklist_leaves_out_the_share_only_items():
    share = {item.id for item in pick.load_checklist("share")}
    asset = {item.id for item in pick.load_checklist("asset")}
    assert asset == share - SHARE_ONLY
    assert len(asset) == 26


def test_an_unknown_deal_is_refused():
    with pytest.raises(ValueError):
        pick.load_checklist("merger")


def test_the_deal_line_names_the_deal_type_in_one_line():
    line = pick.deal_line("asset")
    assert "\n" not in line.strip()
    assert "asset" in line
    assert "purchase of the business's assets" in line


# ---------------------------------------------------------------- choosing


def notes_with(counts: dict[str, int]) -> dict[str, dict | None]:
    return {
        doc: (None if n is None else {"flags": [{"flag": f"f{i}"} for i in range(n)]})
        for doc, n in counts.items()
    }


def test_choosing_takes_whole_documents_until_the_next_would_pass_the_rows():
    notes = notes_with({"a": 100, "b": 40, "c": 30, "d": 5})
    chosen, rows = pick.choose(["a", "b", "c", "d"], notes, cap=150)
    # c would take the rows to 170, so the walk stops there, though d alone would still fit.
    assert chosen == ["a", "b"]
    assert rows == 140


def test_choosing_counts_a_document_with_no_note_as_no_rows():
    notes = notes_with({"a": 10, "b": None, "c": 5})
    chosen, rows = pick.choose(["b", "a", "c"], notes, cap=150)
    assert chosen == ["b", "a", "c"]
    assert rows == 15


def test_the_first_document_is_taken_whole_even_past_the_rows():
    notes = notes_with({"a": 300, "b": 5})
    chosen, rows = pick.choose(["a", "b"], notes, cap=150)
    assert chosen == ["a"]
    assert rows == 300


def test_choosing_uses_the_digest_rows_by_default():
    assert pick.choose.__defaults__[0] == write.DIGEST_ROWS == 150


# ---------------------------------------------------------------- arm A, the model's ranking


def test_ids_the_model_leaves_out_follow_in_index_order_and_invented_ids_are_dropped():
    ids = ["a", "b", "c", "d"]
    assert pick.order_reply(ids, ["c", "x", "a", "c", " b "]) == ["c", "a", "b", "d"]
    assert pick.order_reply(ids, []) == ids


def small_room(tmp_path: Path) -> tuple[Path, Path]:
    """A room of three documents, ingested, with a note for each quoting its own lines."""
    room = tmp_path / "room"
    room.mkdir()
    texts = {
        "a.txt": "Loan agreement.\nThe borrower shall repay $5,000,000 on a change of control.",
        "b.txt": "Lease of office.\nRent is $10 per month.",
        "c.txt": "Employment agreement.\nThe officer is paid a bonus of $200,000 on a change of control.",
    }
    for name, text in texts.items():
        (room / name).write_text(text + "\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    ingest.ingest(room, run_dir)
    (run_dir / "notes").mkdir()
    flags = {"a.txt": 3, "b.txt": 1, "c.txt": 2}
    for doc, text in texts.items():
        first, second = text.split("\n")
        note = {
            "doc": doc,
            "what": f"what {doc}",
            "flags": [
                {
                    "flag": f"flag {i} of {doc}",
                    "quote": second,
                    "consequence": f"consequence {i} of {doc}",
                    "about": [],
                    "anchor": f"{doc}#l1",
                }
                for i in range(flags[doc])
            ],
            "figures": [{"surface": re.search(r"\$[\d,]+", second).group(0), "quote": second, "anchor": f"{doc}#l1"}],
            "cross_references": [],
            "concealed": [],
        }
        (run_dir / "notes" / note_name(doc)).write_text(json.dumps(note), encoding="utf-8")
    (run_dir / "notes-summary.json").write_text(json.dumps({"noted": 3}), encoding="utf-8")
    return room, run_dir


class RankTransport(httpx.MockTransport):
    """Answers every chat completion with one ranking reply and records the bodies."""

    def __init__(self, ranked):
        self.requests: list[dict] = []
        self.ranked = ranked
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append(body)
        return httpx.Response(200, json=reply(json.dumps({"ranked": self.ranked}), 3000, 100))


def test_the_llm_arm_ranks_every_document_in_one_call_and_books_it(tmp_path, capsys):
    room, run_dir = small_room(tmp_path)
    ledger = write_ledger(tmp_path / "LEDGER.md")
    transport = RankTransport(["c.txt", "a.txt", "made-up.txt"])
    gateway = Gateway(api_key="k", transport=transport, rate_limit_waits=())

    picked = pick.pick(room, run_dir, "llm", "share", gateway=gateway, ledger=ledger)

    assert len(transport.requests) == 1
    body = transport.requests[0]
    assert body["model"] == pick.DEFAULT_MODEL == "z-ai/glm-5.3-flash"
    sent = "\n".join(message["content"] for message in body["messages"])
    for item in pick.load_checklist("share"):
        assert item.question in sent
    for doc in ("a.txt", "b.txt", "c.txt"):
        assert f"what {doc}" in sent
        assert f"flag 0 of {doc}" in sent
    assert "consequence 0 of a.txt" not in sent

    assert [row["doc"] for row in picked["ranked"]] == ["c.txt", "a.txt", "b.txt"]
    written = json.loads((run_dir / "pick.json").read_text(encoding="utf-8"))
    assert written == picked
    assert set(written) == {"arm", "deal", "model", "ranked", "chosen", "rows"}
    assert written["arm"] == "llm"
    assert written["deal"] == "share"
    assert written["model"] == pick.DEFAULT_MODEL
    assert written["chosen"] == ["c.txt", "a.txt", "b.txt"]
    assert written["rows"] == 6

    rows = ledger.rows()
    assert rows[-1]["phase"] == "8"
    assert rows[-1]["model"] == pick.DEFAULT_MODEL
    assert (rows[-1]["tokens_in"], rows[-1]["tokens_out"]) == (3000, 100)
    assert "estimate:" in capsys.readouterr().out


def test_the_asset_deal_sends_the_asset_checklist(tmp_path):
    room, run_dir = small_room(tmp_path)
    transport = RankTransport([])
    gateway = Gateway(api_key="k", transport=transport, rate_limit_waits=())

    picked = pick.pick(room, run_dir, "llm", "asset", gateway=gateway, ledger=write_ledger(tmp_path / "L.md"))

    sent = "\n".join(message["content"] for message in transport.requests[0]["messages"])
    assert "Does this contract impose financial covenants" not in sent
    assert "Is this contract a lease of real property" in sent
    assert picked["deal"] == "asset"
    assert [row["doc"] for row in picked["ranked"]] == ["a.txt", "b.txt", "c.txt"]


def test_the_llm_arm_refuses_past_the_phase_cap_and_sends_nothing(tmp_path):
    room, run_dir = small_room(tmp_path)
    ledger = write_ledger(tmp_path / "LEDGER.md")
    with ledger.path.open("a", encoding="utf-8") as handle:
        handle.write("| 2026-10-05 | x | 8 | z-ai/glm-5.3 | 0 | 0 | 11.5000 | 38.5000 |\n")
    transport = RankTransport([])
    gateway = Gateway(api_key="k", transport=transport, rate_limit_waits=())

    with pytest.raises(CapExceeded):
        pick.pick(room, run_dir, "llm", "share", gateway=gateway, ledger=ledger)
    assert transport.requests == []
    assert not (run_dir / "pick.json").exists()


# ---------------------------------------------------------------- arm B, Jev


def test_jev_is_priced_on_its_input_alone():
    assert PRICES[pick.JEV_MODEL] == (0.042, 0.0)
    assert pick.JEV_MODEL == "typesafe/jev-1.13.0"
    assert price(pick.JEV_MODEL, 1_000_000, 5_000_000) == pytest.approx(0.042)


def test_every_checklist_item_is_a_noul_question_under_its_id():
    questions = pick.jev_questions(pick.load_checklist("share"))
    assert list(questions) == [item.id for item in pick.load_checklist("share")]
    assert questions["lease"] == {
        "type": "noul",
        "instructions": "Is this contract a lease of real property by the company?",
    }


def test_a_document_too_long_for_jev_is_split_into_consecutive_pieces_that_fit():
    questions = pick.jev_questions(pick.load_checklist("share"))
    line = "The licensee shall pay the royalty in full on each quarter day of the term. "
    text = "\n".join(f"{i} {line * 3}" for i in range(4000))
    pieces = pick.jev_pieces(text, questions)
    assert len(pieces) > 1
    assert "\n".join(pieces) == text
    for piece in pieces:
        assert pick.request_tokens(piece, questions) <= pick.JEV_TOKEN_LIMIT * pick.JEV_MARGIN
    assert pick.JEV_MARGIN < 1


def test_a_single_line_longer_than_a_piece_is_cut_inside_the_line():
    questions = pick.jev_questions(pick.load_checklist("share"))
    text = "x" * 400_000
    pieces = pick.jev_pieces(text, questions)
    assert len(pieces) > 1
    assert "".join(pieces) == text
    assert all(pick.request_tokens(p, questions) <= pick.JEV_TOKEN_LIMIT * pick.JEV_MARGIN for p in pieces)


def test_a_short_document_is_one_piece():
    questions = pick.jev_questions(pick.load_checklist("share"))
    assert pick.jev_pieces("one line", questions) == ["one line"]


class JevTransport(httpx.MockTransport):
    """Answers Jev with a noul per question from a table of (state word, ask) to a probability.

    The first request is answered 429 when busy_first is set, and the requests are recorded.
    """

    def __init__(self, nouls, busy_first=False, tokens=1000):
        self.requests: list[httpx.Request] = []
        self.nouls = nouls
        self.busy = busy_first
        self.tokens = tokens
        self.asked: dict[str, int] = {}
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.busy:
            self.busy = False
            return httpx.Response(429, json={"error": "busy"})
        body = json.loads(request.content)
        word = body["state"].split()[0]
        ask = self.asked.get(body["state"], 0)
        self.asked[body["state"]] = ask + 1
        value = self.nouls[word][ask]
        answers = {
            name: {"type": "noul", "noul": value if i == 0 else value / 2}
            for i, name in enumerate(body["questions"])
        }
        return httpx.Response(
            200,
            json={"model": "jev-1.13.0", "usage": {"input_tokens": self.tokens}, "answers": answers},
        )


def jev_client(transport) -> "pick.JevClient":
    return pick.JevClient(api_key="ts-key", transport=transport, waits=(0.0,) * 6)


def test_the_jev_arm_asks_each_document_twice_and_ranks_by_the_mean_of_its_highest_noul(tmp_path, capsys):
    room, run_dir = small_room(tmp_path)
    ledger = write_ledger(tmp_path / "LEDGER.md")
    # a scores 0.9 then 0.5, mean 0.7; b scores 0.7 twice; c scores 0.2 then 1.0, mean 0.6.
    transport = JevTransport({"Loan": [0.9, 0.5], "Lease": [0.7, 0.7], "Employment": [0.2, 1.0]}, busy_first=True)

    picked = pick.pick(room, run_dir, "jev", "share", ledger=ledger, jev=jev_client(transport))

    assert [row["doc"] for row in picked["ranked"]] == ["a.txt", "b.txt", "c.txt"]
    assert [row["score"] for row in picked["ranked"]] == pytest.approx([0.7, 0.7, 0.6])
    assert picked["model"] == pick.JEV_MODEL
    assert picked["arm"] == "jev"
    # six answered requests and the one 429 sent again
    assert len(transport.requests) == 7
    first = transport.requests[-1]
    assert first.url == httpx.URL(pick.JEV_URL)
    assert first.headers["authorization"] == "Bearer ts-key"
    body = json.loads(first.content)
    assert set(body) == {"model", "state", "questions"}
    assert body["model"] == "jev-1.13.0"
    assert body["questions"] == pick.jev_questions(pick.load_checklist("share"))

    raw = (run_dir / pick.JEV_RAW).read_text(encoding="utf-8").splitlines()
    assert len(raw) == 6
    assert all(json.loads(line)["response"]["answers"] for line in raw)

    rows = ledger.rows()
    assert rows[-1]["model"] == pick.JEV_MODEL
    assert rows[-1]["phase"] == "8"
    assert (rows[-1]["tokens_in"], rows[-1]["tokens_out"]) == (6000, 0)
    printed = capsys.readouterr().out
    assert f"on {pick.JEV_MODEL}" in printed
    assert "estimate:" in printed


def test_ties_are_broken_by_document_id(tmp_path):
    room, run_dir = small_room(tmp_path)
    transport = JevTransport({"Loan": [0.5, 0.5], "Lease": [0.5, 0.5], "Employment": [0.5, 0.5]})
    picked = pick.pick(room, run_dir, "jev", "share", ledger=write_ledger(tmp_path / "L.md"), jev=jev_client(transport))
    assert [row["doc"] for row in picked["ranked"]] == ["a.txt", "b.txt", "c.txt"]


def test_a_long_document_scores_its_best_piece(tmp_path, monkeypatch):
    room, run_dir = small_room(tmp_path)
    monkeypatch.setattr(pick, "jev_pieces", lambda text, questions: text.split("\n"))
    nouls = {"Loan": [0.1, 0.1], "The": [0.8, 0.6], "Lease": [0.2, 0.2], "Rent": [0.3, 0.3],
             "Employment": [0.1, 0.1]}
    transport = JevTransport(nouls)
    picked = pick.pick(room, run_dir, "jev", "share", ledger=write_ledger(tmp_path / "L.md"), jev=jev_client(transport))
    scores = {row["doc"]: row["score"] for row in picked["ranked"]}
    assert scores["a.txt"] == pytest.approx(0.7)
    assert scores["b.txt"] == pytest.approx(0.3)


def test_the_jev_arm_refuses_past_the_phase_cap_and_sends_nothing(tmp_path):
    room, run_dir = small_room(tmp_path)
    ledger = write_ledger(tmp_path / "LEDGER.md")
    with ledger.path.open("a", encoding="utf-8") as handle:
        handle.write("| 2026-10-05 | x | 8 | z-ai/glm-5.3 | 0 | 0 | 11.5000 | 38.5000 |\n")
    transport = JevTransport({})
    with pytest.raises(CapExceeded):
        pick.pick(room, run_dir, "jev", "share", ledger=ledger, jev=jev_client(transport))
    assert transport.requests == []


def test_the_jev_key_is_read_from_the_environment_first(monkeypatch, tmp_path):
    monkeypatch.setenv("TYPESAFE_API_KEY", "from-env")
    assert pick.jev_key([tmp_path / ".env"]) == "from-env"
    monkeypatch.delenv("TYPESAFE_API_KEY")
    (tmp_path / ".env").write_text("OTHER=1\nTYPESAFE_API_KEY='from-file'\n", encoding="utf-8")
    assert pick.jev_key([tmp_path / "none.env", tmp_path / ".env"]) == "from-file"
    assert pick.jev_key([tmp_path / "none.env"]) == ""


# ---------------------------------------------------------------- the writer in pick mode


def test_the_pick_digest_holds_the_chosen_notes_whole_in_rank_order(tmp_path):
    room, run_dir = small_room(tmp_path)
    picked = {"arm": "llm", "deal": "share", "model": "m",
              "ranked": [{"doc": d, "score": 0} for d in ("c.txt", "a.txt", "b.txt")],
              "chosen": ["c.txt", "a.txt"], "rows": 5}
    digest = pick.pick_digest(room, run_dir, picked)
    assert "b.txt" not in digest
    assert digest.index("### 1. c.txt") < digest.index("### 2. a.txt")
    for i in range(3):
        assert f"flag {i} of a.txt" in digest
        assert f"consequence {i} of a.txt" in digest
    assert "The borrower shall repay $5,000,000 on a change of control." in digest
    assert "$200,000" in digest
    assert "share" in digest
    # no second level heading, so the writer asks for the one matter shape
    assert not write.holds_further_matter(digest)
    # the verifier reads the chosen documents as the matter
    assert [doc for doc, _, _ in write.document_rows(digest)] == ["c.txt", "a.txt"]


def test_the_writer_in_pick_mode_writes_from_the_chosen_notes_and_verifies(tmp_path):
    room, run_dir = small_room(tmp_path)
    (run_dir / "pick.json").write_text(json.dumps(
        {"arm": "llm", "deal": "asset", "model": "m",
         "ranked": [{"doc": d, "score": 0} for d in ("a.txt", "c.txt", "b.txt")],
         "chosen": ["a.txt", "c.txt"], "rows": 5}), encoding="utf-8")
    report = (
        "## Executive summary\n\nRecommendation: proceed.\n\n"
        'The loan says "The borrower shall repay $5,000,000 on a change of control" [a.txt | a.txt#l1].\n\n'
        "## Findings ranked by materiality\n\n"
        'The loan is repaid on a change of control, "The borrower shall repay $5,000,000 on a change of control" [a.txt | a.txt#l1].\n\n'
        "## The most material issue quantified\n\nNone [a.txt | a.txt#l1].\n\n"
        "## Lesser issues\n\nNone [c.txt | c.txt#l1].\n\n## Open items\n\nNone [c.txt | c.txt#l1].\n"
    )

    class Fake(httpx.MockTransport):
        def __init__(self):
            self.bodies = []
            super().__init__(self._handle)

        def _handle(self, request):
            self.bodies.append(json.loads(request.content))
            return httpx.Response(200, json=reply(report, 5000, 800))

    transport = Fake()
    gateway = Gateway(api_key="k", transport=transport, rate_limit_waits=())
    code = write.main([str(room), str(run_dir), "--pick", "--phase", "8"], gateway=gateway,
                      ledger=write_ledger(tmp_path / "L.md"))
    assert code == 0
    assert len(transport.bodies) == 1
    body = transport.bodies[0]
    assert body["model"] == write.DEFAULT_MODEL
    assert body["messages"][0]["content"].startswith(write.PROMPT)
    assert body["messages"][1]["content"] == (run_dir / "digest.md").read_text(encoding="utf-8")
    assert "flag 2 of a.txt" in body["messages"][1]["content"]
    assert "b.txt" not in body["messages"][1]["content"]
    assert not (run_dir / "dossier.md").exists()

    written = (run_dir / "report.md").read_text(encoding="utf-8")
    assert written.splitlines()[0] == pick.deal_line("asset")
    evidence = written.split("## Evidence", 1)[1]
    assert '- flag 0 of a.txt | "The borrower shall repay $5,000,000 on a change of control." | [a.txt | a.txt#l1]' in evidence
    assert "c.txt" in evidence and "b.txt" not in evidence
    assert json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))["passes"] is True


# ---------------------------------------------------------------- the command


class PickRoomTransport(RoomTransport):
    """sample 3's fake room transport, answering the ranking call with the room in reverse."""

    def __init__(self, ids, **kwargs):
        self.ids = ids
        super().__init__(**kwargs)

    def _handle(self, request):
        body = json.loads(request.content)
        if body["messages"][0]["content"].startswith(pick.RANK_PROMPT[:60]):
            self.requests.append(body)
            return httpx.Response(200, json=reply(json.dumps({"ranked": self.ids[::-1]})))
        return super()._handle(request)


def test_the_command_with_a_ranker_runs_pick_in_place_of_map_and_dossier(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    ids = list(room_documents(room))
    transport = PickRoomTransport(ids)
    argv = ["run", str(room), "--out", str(run_dir), "--yes", "--rank", "llm", "--deal", "asset"]

    code = cli.main(argv, gateway=Gateway(api_key="k", transport=transport, rate_limit_waits=()),
                    ledger=write_ledger(tmp_path / "L.md"))

    assert code == 0, (run_dir / "run.json").read_text(encoding="utf-8")
    assert not (run_dir / "map.json").exists()
    assert not (run_dir / "dossier.md").exists()
    picked = json.loads((run_dir / "pick.json").read_text(encoding="utf-8"))
    assert picked["deal"] == "asset"
    assert [row["doc"] for row in picked["ranked"]] == ids[::-1]
    for name in ("report.md", "verify.json", "report.docx", "report.pdf", "evidence.csv", "grade.json"):
        assert (run_dir / name).exists(), name
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert state["status"] == "done"
    # the models line opens every report; the deal line follows it
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert report.startswith("Models: ")
    assert report.split("\n\n", 1)[1].startswith(pick.deal_line("asset"))


def test_the_command_without_a_ranker_runs_the_map_and_the_dossier_as_before(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    code = cli.main(["run", str(room), "--out", str(run_dir), "--yes", "--deal", "asset"],
                    gateway=Gateway(api_key="k", transport=RoomTransport(), rate_limit_waits=()),
                    ledger=write_ledger(tmp_path / "L.md"))
    assert code == 0
    assert (run_dir / "map.json").exists()
    assert (run_dir / "dossier.md").exists()
    assert not (run_dir / "pick.json").exists()


def test_the_stages_with_a_ranker():
    assert cli.stages_for("llm") == ("ingest", "notes", "pick", "write", "export")
    assert cli.stages_for("jev") == ("ingest", "notes", "pick", "write", "export")
    assert cli.stages_for(None) == cli.STAGES == ("ingest", "notes", "map", "dossier", "write", "export")


def test_the_command_refuses_an_unknown_ranker_or_deal():
    with pytest.raises(SystemExit):
        cli.parse_args(["run", "room", "--rank", "map"])
    with pytest.raises(SystemExit):
        cli.parse_args(["run", "room", "--deal", "merger"])
    assert cli.parse_args(["run", "room"]).deal == "share"
    assert cli.parse_args(["run", "room"]).rank is None


# ---------------------------------------------------------------- the web page


def test_the_page_offers_the_deal_type_with_share_first():
    page = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    assert '<select id="deal"' in page
    assert page.index('value="share"') < page.index('value="asset"')
    script = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    assert 'form.append("deal"' in script


def test_the_deal_chosen_on_the_page_reaches_the_command(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app, room_of
    from app.runner import LocalRunner

    monkeypatch.delenv("RLM_PHASE", raising=False)
    runner = LocalRunner(["prefix"])
    runs = tmp_path / "runs"
    app = create_app(runner=runner, runs_root=runs, web_dir=tmp_path / "noweb")
    upload = [("files", ("room/a.txt", b"a line\n", "text/plain"))]
    headers = {"X-OpenRouter-Key": "sk-or-v1-test"}
    with TestClient(app) as client:
        asset = client.post("/runs", files=upload, data={"deal": "asset"}, headers=headers)
        plain = client.post("/runs", files=upload, headers=headers)
        bad = client.post("/runs", files=upload, data={"deal": "merger"}, headers=headers)

    assert asset.status_code == 201
    run_dir = runs / asset.json()["id"]
    assert runner.argv(room_of(run_dir), run_dir)[-2:] == ["--deal", "asset"]
    run_dir = runs / plain.json()["id"]
    assert runner.argv(room_of(run_dir), run_dir)[-2:] == ["--deal", "share"]
    assert bad.status_code == 400
    assert bad.json()["code"] == "bad-deal"
