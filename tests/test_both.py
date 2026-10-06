"""Issue #160: the writer reads both digests, the dossier's and the tree's, behind --write both.

Every test is free: the gateway is a fake on an httpx mock transport and the ledger a temporary
file.
"""

import json

import pytest

from rlm import cli, tree, write
from rlm.key import room_documents
from test_phase8_command import copy_room, write_ledger
from test_pick import small_room
from test_tree import LEASE, LOAN, BONUS, TreeRoomTransport, TreeTransport, built_tree, gateway_for


def test_the_stages_with_both_writers():
    assert cli.stages_for(None, "both") == (
        "ingest", "notes", "map", "dossier", "tree", "write", "export",
    )
    assert cli.stages_for(None, "tree") == cli.TREE_STAGES
    assert cli.stages_for(None) == cli.STAGES
    assert cli.parse_args(["run", "room", "--write", "both"]).write == "both"


def test_both_does_not_go_with_a_ranker(tmp_path, capsys):
    room = copy_room(tmp_path)
    code = cli.main(["run", str(room), "--out", str(tmp_path / "run"), "--yes", "--write", "both", "--rank", "llm"])
    assert code == 2


def test_a_tree_finding_whose_quote_the_dossier_digest_holds_is_dropped(tmp_path):
    room, run_dir = small_room(tmp_path)
    seen = f"# Digest\n\n### Figures\n\n- a loan | a.txt | {LOAN.replace(' ', '  ')} | a.txt#l1\n"
    section = tree.unseen_digest(room, built_tree(), seen)
    assert LOAN not in section
    assert f"- the lease / rent | b.txt | {LEASE} | b.txt#l1" in section
    assert f"- the bonus | c.txt | {BONUS} | c.txt#l1" in section
    assert section.index("b.txt") < section.index("c.txt")
    evidence = tree.unseen_evidence(room, built_tree(), seen)
    assert LOAN not in evidence
    assert f'- the bonus | "{BONUS}" | [c.txt | c.txt#l1]' in evidence


def test_the_section_is_empty_when_the_dossier_digest_holds_every_quote(tmp_path):
    room, run_dir = small_room(tmp_path)
    seen = " ".join([LOAN, LEASE, BONUS])
    assert tree.unseen_digest(room, built_tree(), seen) == ""
    assert tree.unseen_evidence(room, built_tree(), seen) == ""


def test_the_section_rows_are_rows_the_writer_and_the_verifier_read(tmp_path):
    room, run_dir = small_room(tmp_path)
    section = tree.unseen_digest(room, built_tree(), "")
    assert len(tree.digest_rows(section)) == 3
    assert "## Matter " not in section
    assert not write.holds_further_matter(section)


def test_the_command_with_write_both_gives_the_writer_the_dossier_digest_then_the_tree_section(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    transport = TreeRoomTransport()
    argv = ["run", str(room), "--out", str(run_dir), "--yes", "--write", "both"]
    code = cli.main(argv, gateway=gateway_for(transport), ledger=write_ledger(tmp_path / "L.md"))

    assert code == 0, (run_dir / "run.json").read_text(encoding="utf-8")
    assert len(transport.group_bodies) == 1
    for name in ("map.json", "dossier.md", tree.TREE_FILE, "report.md", "report.docx", "grade.json"):
        assert (run_dir / name).exists(), name
    dossier = (run_dir / "dossier.md").read_text(encoding="utf-8")
    plain = write.digest_markdown(dossier)
    digest = (run_dir / "digest.md").read_text(encoding="utf-8")
    assert digest.startswith(plain)
    built = tree.read_tree(run_dir)
    after = digest[len(plain):]
    flat = " ".join(plain.split())
    for group in built["groups"]:
        for item in group["findings"]:
            quote = " ".join(item["quote"].split())
            assert (quote in " ".join(after.split())) == (quote not in flat)
    writer_message = [b for b in transport.requests if b["model"] == write.DEFAULT_MODEL][0]["messages"][1]["content"]
    assert writer_message == digest
    assert writer_message.startswith(write.digest_markdown(dossier))
    assert json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))["passes"] is True


def test_a_run_without_the_flag_has_no_tree_section(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    transport = TreeRoomTransport()
    argv = ["run", str(room), "--out", str(run_dir), "--yes"]
    assert cli.main(argv, gateway=gateway_for(transport), ledger=write_ledger(tmp_path / "L.md")) == 0
    assert transport.group_bodies == []
    assert not (run_dir / tree.TREE_FILE).exists()
    dossier = (run_dir / "dossier.md").read_text(encoding="utf-8")
    assert (run_dir / "digest.md").read_text(encoding="utf-8") == write.digest_markdown(dossier)


def test_the_writer_of_both_records_its_cost_in_tree_json(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    argv = ["run", str(room), "--out", str(run_dir), "--yes", "--write", "both"]
    cli.main(argv, gateway=gateway_for(TreeRoomTransport()), ledger=write_ledger(tmp_path / "L.md"))
    assert json.loads((run_dir / tree.TREE_FILE).read_text(encoding="utf-8"))["writer"]["model"] == write.DEFAULT_MODEL


def test_the_stages_and_flag_of_the_tree_first_order():
    assert cli.stages_for(None, "both-tree-first") == cli.BOTH_STAGES
    assert cli.parse_args(["run", "room", "--write", "both-tree-first"]).write == "both-tree-first"


def test_the_command_with_both_tree_first_puts_the_tree_section_before_the_dossier_digest(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    transport = TreeRoomTransport()
    argv = ["run", str(room), "--out", str(run_dir), "--yes", "--write", "both-tree-first"]
    code = cli.main(argv, gateway=gateway_for(transport), ledger=write_ledger(tmp_path / "L.md"))

    assert code == 0, (run_dir / "run.json").read_text(encoding="utf-8")
    dossier = (run_dir / "dossier.md").read_text(encoding="utf-8")
    plain = write.digest_markdown(dossier)
    digest = (run_dir / "digest.md").read_text(encoding="utf-8")
    built = tree.read_tree(run_dir)
    section = tree.unseen_digest(room, built, plain)
    assert section
    assert digest == f"{section}\n{plain}"
    writer_message = [b for b in transport.requests if b["model"] == write.DEFAULT_MODEL][0]["messages"][1]["content"]
    assert writer_message == digest
    assert json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))["passes"] is True
