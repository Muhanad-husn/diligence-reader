"""Issue #160: the tree and the writer on the subscription's Sonnet 5.5.

A group call on Sonnet reads a smaller share of the room than its window allows, and keeps more
findings in all. A writer on Sonnet is asked for every finding the digest carries, by a prompt
of its own with no 12000 token cap in it, reads every finding the tree kept, and has its reply
cap passed to headless Claude Code.

Every test here is free: the subprocess is a fake runner and the ledger a temporary file.
"""

import json
import math

from rlm import tree, write
from rlm.gateway import ClaudeCode, Gateway
from test_claude_code import SONNET, FakeRunner, cli_reply, gateway_with, system_of, tree_answer
from test_phase8_command import write_ledger
from test_pick import small_room
from test_tree import LOAN, LEASE, built_tree

GLM = tree.DEFAULT_MODEL


# ---------------------------------------------------------------- the tree on Sonnet


def test_a_sonnet_group_carries_at_most_its_own_share_of_tokens():
    system = "x" * 4000
    window_budget = int(tree.CONTEXT_WINDOWS[SONNET] * tree.MARGIN) - 1000 - tree.MAX_OUTPUT_TOKENS
    assert 0 < tree.GROUP_TOKENS[SONNET] < window_budget
    assert tree.group_budget(SONNET, system) == tree.GROUP_TOKENS[SONNET]
    assert GLM not in tree.GROUP_TOKENS
    assert tree.group_budget(GLM, system) == int(tree.CONTEXT_WINDOWS[GLM] * tree.MARGIN) - 1000 - tree.MAX_OUTPUT_TOKENS


def test_a_sonnet_tree_shares_its_own_total_of_findings_over_the_groups():
    assert tree.FINDING_ROWS[SONNET] > write.DIGEST_ROWS
    assert tree.group_cap(4, SONNET) == math.ceil(tree.FINDING_ROWS[SONNET] / 4)
    assert tree.group_cap(4) == tree.group_cap(4, GLM) == math.ceil(write.DIGEST_ROWS / 4)


def test_the_tree_on_sonnet_groups_by_its_share_and_asks_for_its_cap(tmp_path):
    room, run_dir = small_room(tmp_path)
    runner = FakeRunner(tree_answer)
    built = tree.tree(room, run_dir, gateway=gateway_with(runner), ledger=write_ledger(tmp_path / "L.md"), model=SONNET)
    assert built["budget"] == tree.GROUP_TOKENS[SONNET]
    assert built["cap"] == tree.FINDING_ROWS[SONNET]
    assert f"at most {tree.FINDING_ROWS[SONNET]}" in system_of(runner.calls[0]["args"])


# ---------------------------------------------------------------- the writer on Sonnet


def test_a_sonnet_writer_is_asked_for_every_finding_by_a_prompt_with_no_token_cap():
    assert "12000" not in write.FULL_PROMPT
    assert "12000" not in write.FULL_REASK
    assert "every row" in write.FULL_PROMPT.lower()
    assert write.FULL_OUTPUT_TOKENS > write.MAX_OUTPUT_TOKENS
    messages = write.build_messages("THE BRIEF", "# Digest\n", full=True)
    assert messages[0]["content"] == write.FULL_PROMPT + "THE BRIEF"
    assert write.build_messages("THE BRIEF", "# Digest\n")[0]["content"] == write.PROMPT + "THE BRIEF"
    two = write.build_messages("B", "# Digest\n\n## Matter 2\n", full=True)[0]["content"]
    assert write.SECOND_MATTER_HEADING in two
    assert write.SECOND_MATTER_HEADING not in messages[0]["content"]


def test_headless_claude_is_given_the_reply_cap_of_the_call(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    runner = FakeRunner(lambda args, stdin: cli_reply("{}"))
    gateway_with(runner).complete(SONNET, [{"role": "user", "content": "x"}], max_tokens=54321)
    env = runner.calls[0]["env"]
    assert env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "54321"
    assert [name for name in env if name.startswith("CLAUDE_CODE_")] == ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"]


class Recorder:
    """A fake gateway: records every call's model, messages and cap, answering with replies in turn."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, model, messages, max_tokens, json=True):
        from rlm.gateway import Completion
        self.calls.append({"model": model, "messages": messages, "max_tokens": max_tokens})
        return Completion(self.replies.pop(0), 100, 10, 0.0, model)


def both_room(tmp_path):
    """The small room with a dossier whose digest already holds the loan's quote, and a tree."""
    room, run_dir = small_room(tmp_path)
    dossier = (
        "# Dossier\n\n## Matter 1\n\n### Documents\n\n- 1. a.txt | Loan | - | - | -\n\n"
        f"### Names\n\n- the borrower | a.txt | {LOAN} | a.txt#l1\n"
    )
    (run_dir / "dossier.md").write_text(dossier, encoding="utf-8")
    (run_dir / tree.TREE_FILE).write_text(json.dumps(built_tree()), encoding="utf-8")
    return room, run_dir


REPORT = (
    "## Executive summary\n\nRecommendation: proceed.\n\n"
    f'The loan says "{LOAN[:-1]}" [a.txt | a.txt#l1].\n\n'
    "## Findings ranked by materiality\n\n"
    f'1. The loan is repaid on a change of control, "{LOAN[:-1]}" [a.txt | a.txt#l1].\n\n'
    "## The most material issue quantified\n\nNone [a.txt | a.txt#l1].\n\n"
    "## Lesser issues\n\n1. None [c.txt | c.txt#l1].\n\n## Open items\n\n1. None [c.txt | c.txt#l1].\n"
)


def test_a_sonnet_writer_of_both_reads_every_tree_finding_first_with_its_own_prompt_and_cap(tmp_path):
    room, run_dir = both_room(tmp_path)
    gateway = Recorder([REPORT])
    code = write.main([str(room), str(run_dir), "--both", "--tree-first", "--phase", "8", "--model", SONNET],
                      gateway=gateway, ledger=write_ledger(tmp_path / "L.md"))
    assert code == 0
    call = gateway.calls[0]
    assert call["max_tokens"] == write.FULL_OUTPUT_TOKENS
    assert call["messages"][0]["content"].startswith(write.FULL_PROMPT)
    digest = call["messages"][1]["content"]
    plain = write.digest_markdown((run_dir / "dossier.md").read_text(encoding="utf-8"))
    assert digest.endswith(plain)
    section = digest[: -len(plain)]
    # the loan's quote is in the dossier digest, and its finding still reaches the writer
    assert "the loan is repaid" in section and LEASE in section and "the bonus" in section
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    # the schedule carries the tree's quotes the dossier lacks, as before, and not the loan twice
    assert "the loan is repaid" not in report.split("## Evidence", 1)[1]
    assert json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))["passes"] is True


def test_a_sonnet_writer_is_asked_again_by_its_own_reask(tmp_path):
    room, run_dir = both_room(tmp_path)
    failing = REPORT.replace("None [c.txt | c.txt#l1].\n\n## Open", "An uncited sentence.\n\n## Open")
    gateway = Recorder([failing, REPORT])
    write.main([str(room), str(run_dir), "--both", "--tree-first", "--phase", "8", "--model", SONNET],
               gateway=gateway, ledger=write_ledger(tmp_path / "L.md"))
    assert len(gateway.calls) == 2
    asked = gateway.calls[1]["messages"][-1]["content"]
    assert asked.startswith(write.FULL_REASK.split("{items}")[0])
    assert gateway.calls[1]["max_tokens"] == write.FULL_OUTPUT_TOKENS


def test_a_glm_writer_of_both_is_unchanged(tmp_path):
    room, run_dir = both_room(tmp_path)
    gateway = Recorder([REPORT])
    write.main([str(room), str(run_dir), "--both", "--tree-first", "--phase", "8"],
               gateway=gateway, ledger=write_ledger(tmp_path / "L.md"))
    call = gateway.calls[0]
    assert call["max_tokens"] == write.MAX_OUTPUT_TOKENS
    assert call["messages"][0]["content"].startswith(write.PROMPT)
    assert "the loan is repaid" not in call["messages"][1]["content"]
