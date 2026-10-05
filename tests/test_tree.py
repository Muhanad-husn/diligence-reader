"""Issue #160: the tree writer, where models choose what the report reads, level by level.

Every test here is free: the gateway is a fake on an httpx mock transport, the ledger is a
temporary file, and the rooms are the small room of test_pick or a copy of sample 3's.
"""

import json
import math
from pathlib import Path

import httpx
import pytest

from rlm import cli, tree, write
from rlm.gateway import CapExceeded, Gateway, estimate_tokens
from rlm.key import room_documents
from test_phase8_command import RoomTransport, copy_room, reply, write_ledger
from test_pick import small_room

LOAN = "The borrower shall repay $5,000,000 on a change of control."
LEASE = "Rent is $10 per month."
BONUS = "The officer is paid a bonus of $200,000 on a change of control."
QUOTES = {"a.txt": LOAN, "b.txt": LEASE, "c.txt": BONUS}


def ids_in(body: dict) -> list[str]:
    """The document ids one group call carries, in the order it carries them."""
    return [line[4:].strip() for line in body["messages"][1]["content"].splitlines() if line.startswith("id: ")]


class TreeTransport(httpx.MockTransport):
    """Answers every group call with answer(body, call), call counting from 0 per group."""

    def __init__(self, answer):
        self.answer = answer
        self.bodies: list[dict] = []
        self.calls: dict[tuple, int] = {}
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.bodies.append(body)
        group = tuple(ids_in(body))
        call = self.calls.get(group, 0)
        self.calls[group] = call + 1
        return httpx.Response(200, json=reply(self.answer(body, call), 4000, 300))


def findings_json(rows: list[dict]) -> str:
    return json.dumps({"findings": rows})


def one_per_doc(body, call):
    return findings_json([{"doc": d, "finding": f"finding of {d}", "quote": QUOTES[d]} for d in ids_in(body)])


def gateway_for(transport) -> Gateway:
    return Gateway(api_key="k", transport=transport, rate_limit_waits=())


# ---------------------------------------------------------------- the groups


def test_the_budget_is_derived_from_the_context_window_with_a_margin():
    instructions = "x" * 4000
    budget = tree.group_budget(tree.DEFAULT_MODEL, instructions)
    window = tree.CONTEXT_WINDOWS[tree.DEFAULT_MODEL]
    assert budget == int(window * tree.MARGIN) - estimate_tokens(instructions) - tree.MAX_OUTPUT_TOKENS
    assert 0 < tree.MARGIN < 1
    assert budget < window
    assert tree.DEFAULT_MODEL == "z-ai/glm-5.3-flash"


def test_grouping_keeps_every_document_in_order_and_fits_the_budget():
    sizes = {"a": 40, "b": 30, "c": 50, "d": 10, "e": 200, "f": 5}
    groups = tree.make_groups(sizes, 100)
    assert [doc for group in groups for doc in group] == list(sizes)
    assert groups == [["a", "b"], ["c", "d"], ["e"], ["f"]]
    for group in groups:
        assert sum(sizes[doc] for doc in group) <= 100 or len(group) == 1


def test_one_group_when_everything_fits():
    assert tree.make_groups({"a": 1, "b": 2}, 100) == [["a", "b"]]


def test_the_cap_per_group_shares_the_digest_rows():
    assert tree.group_cap(1) == write.DIGEST_ROWS == 150
    assert tree.group_cap(2) == 75
    assert tree.group_cap(4) == math.ceil(150 / 4) == 38


# ---------------------------------------------------------------- the quote check


def test_the_quote_check_keeps_copied_quotes_and_drops_invented_ones(tmp_path):
    room, run_dir = small_room(tmp_path)
    notes = tree.read_notes(room, run_dir)
    returned = [
        {"doc": "a.txt", "finding": "kept whole", "quote": "The borrower  shall repay\n$5,000,000 on a change of control."},
        {"doc": "a.txt", "finding": "kept as a part", "quote": "repay $5,000,000"},
        {"doc": "a.txt", "finding": "invented", "quote": "The borrower shall repay $9,000,000."},
        {"doc": "b.txt", "finding": "quote of another document", "quote": LOAN},
        {"doc": "z.txt", "finding": "no such document in the group", "quote": LOAN},
        {"doc": "a.txt", "finding": "no quote", "quote": ""},
    ]
    kept, dropped = tree.check_findings(returned, ["a.txt", "b.txt"], notes)
    assert [item["finding"] for item in kept] == ["kept whole", "kept as a part"]
    assert all(item["anchor"] == "a.txt#l1" for item in kept)
    assert [item["finding"] for item in dropped] == [
        "invented", "quote of another document", "no such document in the group", "no quote"
    ]
    assert all(item["reason"] for item in dropped)


# ---------------------------------------------------------------- the stage


def test_one_group_call_per_group_carries_the_brief_the_checklist_and_the_notes(tmp_path, capsys):
    room, run_dir = small_room(tmp_path)
    (room / "brief.md").write_text("THE ROOM'S OWN BRIEF\n", encoding="utf-8")
    ledger = write_ledger(tmp_path / "LEDGER.md")
    transport = TreeTransport(one_per_doc)

    built = tree.tree(room, run_dir, gateway=gateway_for(transport), ledger=ledger)

    assert len(transport.bodies) == 1
    body = transport.bodies[0]
    assert body["model"] == "z-ai/glm-5.3-flash"
    assert body["reasoning"] == {"effort": "low"}
    system = body["messages"][0]["content"]
    assert "buy-side diligence lead" in system
    assert "acquisition" in system
    assert "THE ROOM'S OWN BRIEF" in system
    assert "Does this contract let a party terminate without cause?" in system
    assert "at most 150" in system
    user = body["messages"][1]["content"]
    assert ids_in(body) == list(room_documents(room))
    for doc in ("a.txt", "b.txt", "c.txt"):
        assert f"what {doc}" in user
        assert f"flag 0 of {doc}" in user
        assert f"consequence 0 of {doc}" in user
    assert LOAN in user and "$200,000" in user

    written = json.loads((run_dir / tree.TREE_FILE).read_text(encoding="utf-8"))
    assert written == built
    assert written["model"] == tree.DEFAULT_MODEL
    assert written["cap"] == 150
    assert [group["docs"] for group in written["groups"]] == [["a.txt", "b.txt", "c.txt"]]
    group = written["groups"][0]
    assert len(group["returned"]) == 3
    assert [item["doc"] for item in group["findings"]] == ["a.txt", "b.txt", "c.txt"]
    assert group["dropped"] == []
    assert group["calls"] == 1

    rows = ledger.rows()
    assert rows[-1]["phase"] == "8"
    assert rows[-1]["model"] == tree.DEFAULT_MODEL
    assert (rows[-1]["tokens_in"], rows[-1]["tokens_out"]) == (4000, 300)
    assert "estimate:" in capsys.readouterr().out


def test_a_room_without_a_brief_is_given_the_package_brief(tmp_path):
    room, run_dir = small_room(tmp_path)
    transport = TreeTransport(one_per_doc)
    tree.tree(room, run_dir, gateway=gateway_for(transport), ledger=write_ledger(tmp_path / "L.md"))
    system = transport.bodies[0]["messages"][0]["content"]
    assert write.DEFAULT_BRIEF.read_text(encoding="utf-8").strip() in system


def test_each_group_keeps_at_most_its_share_of_the_rows(tmp_path):
    room, run_dir = small_room(tmp_path)

    def sixty(body, call):
        doc = ids_in(body)[0]
        return findings_json([{"doc": doc, "finding": f"finding {i}", "quote": QUOTES[doc]} for i in range(60)])

    transport = TreeTransport(sixty)
    built = tree.tree(room, run_dir, gateway=gateway_for(transport), ledger=write_ledger(tmp_path / "L.md"), budget=1)

    assert [group["docs"] for group in built["groups"]] == [["a.txt"], ["b.txt"], ["c.txt"]]
    assert built["cap"] == 50
    for body in transport.bodies:
        assert "at most 50" in body["messages"][0]["content"]
    for group in built["groups"]:
        assert len(group["returned"]) == 60
        assert [item["finding"] for item in group["findings"]] == [f"finding {i}" for i in range(50)]
        assert len(group["dropped"]) == 10


def test_a_group_that_returns_nothing_usable_is_asked_once_more(tmp_path):
    room, run_dir = small_room(tmp_path)

    def invented_then_good(body, call):
        if call == 0:
            return findings_json([{"doc": "a.txt", "finding": "x", "quote": "words the note never had"}])
        return one_per_doc(body, call)

    transport = TreeTransport(invented_then_good)
    built = tree.tree(room, run_dir, gateway=gateway_for(transport), ledger=write_ledger(tmp_path / "L.md"))

    assert len(transport.bodies) == 2
    assert len(transport.bodies[1]["messages"]) == 4
    group = built["groups"][0]
    assert group["calls"] == 2
    assert [item["doc"] for item in group["findings"]] == ["a.txt", "b.txt", "c.txt"]
    assert [item["quote"] for item in group["dropped"]] == ["words the note never had"]
    assert len(group["returned"]) == 4


def test_an_unreadable_reply_is_asked_once_more_and_never_a_third_time(tmp_path):
    room, run_dir = small_room(tmp_path)
    transport = TreeTransport(lambda body, call: "not json at all")
    built = tree.tree(room, run_dir, gateway=gateway_for(transport), ledger=write_ledger(tmp_path / "L.md"))
    assert len(transport.bodies) == 2
    group = built["groups"][0]
    assert group["calls"] == 2
    assert group["findings"] == []


def test_the_tree_refuses_past_the_phase_cap_and_sends_nothing(tmp_path):
    room, run_dir = small_room(tmp_path)
    ledger = write_ledger(tmp_path / "LEDGER.md")
    with ledger.path.open("a", encoding="utf-8") as handle:
        handle.write("| 2026-10-05 | x | 8 | z-ai/glm-5.3 | 0 | 0 | 11.5000 | 38.5000 |\n")
    transport = TreeTransport(one_per_doc)
    with pytest.raises(CapExceeded):
        tree.tree(room, run_dir, gateway=gateway_for(transport), ledger=ledger)
    assert transport.bodies == []
    assert not (run_dir / tree.TREE_FILE).exists()


# ---------------------------------------------------------------- what the writer reads


def built_tree() -> dict:
    """A tree.json whose findings come back out of room order."""
    return {
        "model": tree.DEFAULT_MODEL, "budget": 1, "cap": 75,
        "groups": [
            {"docs": ["a.txt", "b.txt"], "tokens": 1, "calls": 1, "returned": [], "dropped": [],
             "findings": [
                 {"doc": "b.txt", "finding": "the lease | rent", "quote": LEASE, "anchor": "b.txt#l1"},
                 {"doc": "a.txt", "finding": "the loan is repaid", "quote": LOAN, "anchor": "a.txt#l1"},
             ]},
            {"docs": ["c.txt"], "tokens": 1, "calls": 1, "returned": [], "dropped": [],
             "findings": [{"doc": "c.txt", "finding": "the bonus", "quote": BONUS, "anchor": "c.txt#l1"}]},
        ],
    }


def test_the_tree_digest_groups_the_findings_by_document_in_room_order(tmp_path):
    room, run_dir = small_room(tmp_path)
    digest = tree.tree_digest(room, run_dir, built_tree())
    assert digest.index("### 1. a.txt") < digest.index("### 2. b.txt") < digest.index("### 3. c.txt")
    assert f"- the loan is repaid | a.txt | {LOAN} | a.txt#l1" in digest
    assert f"- the lease / rent | b.txt | {LEASE} | b.txt#l1" in digest
    assert not write.holds_further_matter(digest)
    assert [doc for doc, _, _ in write.document_rows(digest)] == ["a.txt", "b.txt", "c.txt"]
    assert len(tree.digest_rows(digest)) == 3
    evidence = tree.tree_evidence(room, run_dir, built_tree())
    assert f'- the loan is repaid | "{LOAN}" | [a.txt | a.txt#l1]' in evidence


def test_the_writer_in_tree_mode_writes_from_the_tree_digest_and_verifies(tmp_path):
    room, run_dir = small_room(tmp_path)
    (run_dir / tree.TREE_FILE).write_text(json.dumps(built_tree()), encoding="utf-8")
    report = (
        "## Executive summary\n\nRecommendation: proceed.\n\n"
        f'The loan says "{LOAN[:-1]}" [a.txt | a.txt#l1].\n\n'
        "## Findings ranked by materiality\n\n"
        f'The loan is repaid on a change of control, "{LOAN[:-1]}" [a.txt | a.txt#l1].\n\n'
        "## The most material issue quantified\n\nNone [a.txt | a.txt#l1].\n\n"
        "## Lesser issues\n\nNone [c.txt | c.txt#l1].\n\n## Open items\n\nNone [c.txt | c.txt#l1].\n"
    )
    transport = TreeTransport(lambda body, call: report)
    code = write.main([str(room), str(run_dir), "--tree", "--phase", "8"], gateway=gateway_for(transport),
                      ledger=write_ledger(tmp_path / "L.md"))
    assert code == 0
    assert len(transport.bodies) == 1
    body = transport.bodies[0]
    assert body["model"] == write.DEFAULT_MODEL
    assert body["messages"][0]["content"].startswith(write.PROMPT)
    assert body["messages"][1]["content"] == (run_dir / "digest.md").read_text(encoding="utf-8")
    assert "the bonus" in body["messages"][1]["content"]
    written = (run_dir / "report.md").read_text(encoding="utf-8")
    assert written.startswith("## Executive summary")
    assert "the bonus" in written.split("## Evidence", 1)[1]
    assert json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))["passes"] is True


# ---------------------------------------------------------------- the command


class TreeRoomTransport(RoomTransport):
    """Sample 3's fake room transport, answering each group call with one finding per document
    quoting the first quote its note carries."""

    def __init__(self, **kwargs):
        self.group_bodies: list[dict] = []
        super().__init__(**kwargs)

    def _handle(self, request):
        body = json.loads(request.content)
        if body["messages"][0]["content"].startswith(tree.TREE_PROMPT[:60]):
            self.group_bodies.append(body)
            rows, doc = [], None
            for line in body["messages"][1]["content"].splitlines():
                if line.startswith("id: "):
                    doc = line[4:].strip()
                elif line.startswith("quote: ") and doc:
                    rows.append({"doc": doc, "finding": f"finding of {doc}", "quote": line[7:]})
                    doc = None
            return httpx.Response(200, json=reply(findings_json(rows)))
        return super()._handle(request)


def test_the_command_with_write_tree_runs_the_tree_in_place_of_map_and_dossier(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    transport = TreeRoomTransport()
    argv = ["run", str(room), "--out", str(run_dir), "--yes", "--write", "tree"]
    code = cli.main(argv, gateway=gateway_for(transport), ledger=write_ledger(tmp_path / "L.md"))

    assert code == 0, (run_dir / "run.json").read_text(encoding="utf-8")
    assert len(transport.group_bodies) == 1
    assert not (run_dir / "map.json").exists()
    assert not (run_dir / "dossier.md").exists()
    assert not (run_dir / "pick.json").exists()
    built = json.loads((run_dir / tree.TREE_FILE).read_text(encoding="utf-8"))
    assert [doc for group in built["groups"] for doc in group["docs"]] == list(room_documents(room))
    for name in ("report.md", "verify.json", "report.docx", "report.pdf", "evidence.csv", "grade.json"):
        assert (run_dir / name).exists(), name
    assert json.loads((run_dir / "run.json").read_text(encoding="utf-8"))["status"] == "done"


def test_the_stages_with_the_tree_writer():
    assert cli.stages_for(None, "tree") == ("ingest", "notes", "tree", "write", "export")
    assert cli.stages_for(None) == cli.STAGES
    assert cli.parse_args(["run", "room"]).write is None
    assert cli.parse_args(["run", "room", "--write", "tree"]).write == "tree"
    with pytest.raises(SystemExit):
        cli.parse_args(["run", "room", "--write", "leaf"])
