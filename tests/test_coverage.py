"""The coverage rule: every finding the writer was handed is in the report body or listed as left out.

Every test here is free. The small room is test_pick's, the gateway is a fake that returns a
fixed reply, and the ledger is a temporary file. The pinned runs are read from RLM_COVERAGE_RUNS,
runs/ of this checkout by default, and a test skips when its run is not there.
"""

import json
import os
import re
from pathlib import Path

import pytest

from conftest import ROOT
from rlm import coverage, tree, verify, write
from rlm.gateway import Completion, Ledger, NoReply
from test_phase8_command import write_ledger
from test_pick import small_room

MODEL = "z-ai/glm-5.3"

LOAN = "The borrower must repay $5,000,000 on a change of control."
LEASE = "The office lease charges a monthly rent of $10."
BONUS = "The officer is paid a bonus of $200,000 on a change of control."

FINDINGS = [
    {"doc": "a.txt", "finding": LOAN, "quote": "The borrower shall repay $5,000,000 on a change of control.",
     "anchor": "a.txt#l1"},
    {"doc": "b.txt", "finding": LEASE, "quote": "Rent is $10 per month.", "anchor": "b.txt#l1"},
    {"doc": "c.txt", "finding": BONUS,
     "quote": "The officer is paid a bonus of $200,000 on a change of control.", "anchor": "c.txt#l1"},
]

REPORT = (
    "## Executive summary\n\n"
    "Recommendation: proceed.\n\n"
    "The borrower must repay $5,000,000 on a change of control [a.txt | a.txt#l1].\n\n"
    "## Findings ranked by materiality\n\n"
    "1. The borrower must repay $5,000,000 on a change of control [a.txt | a.txt#l1].\n\n"
    "## The most material issue quantified\n\n"
    "The repayment is $5,000,000 [a.txt | a.txt#l1].\n\n"
    "## Lesser issues\n\n"
    "1. The lease is a lease [b.txt | b.txt#l1].\n"
    "2. The officer has an agreement [c.txt | c.txt#l1].\n\n"
    "## Open items\n\n"
    "1. Confirm the payoff amount [a.txt | a.txt#l1].\n\n"
    "## Evidence\n\n"
    "- The office lease charges a monthly rent of $10 | \"Rent is $10 per month.\" | [b.txt | b.txt#l1]\n"
)

GOOD_LEASE = "The office lease charges a monthly rent of $10 [b.txt | b.txt#l1]."
WRONG_ANCHOR_BONUS = "The officer is paid a bonus of $200,000 on a change of control [a.txt | a.txt#l1]."
WRONG_NUMBER_BONUS = "The officer is paid a bonus of $300,000 on a change of control [c.txt | c.txt#l1]."


class FakeGateway:
    """Answers every call with one fixed text, or raises one fixed error, and keeps the calls."""

    def __init__(self, text: str = "", error: Exception | None = None):
        self.text = text
        self.error = error
        self.calls: list[dict] = []

    def complete(self, model, messages, max_tokens, json=True):
        self.calls.append({"model": model, "messages": messages, "max_tokens": max_tokens, "json": json})
        if self.error is not None:
            raise self.error
        return Completion(text=self.text, tokens_in=1200, tokens_out=300, seconds=0.1, model=model)


def paragraphs_reply(items: list[tuple[str, str]]) -> str:
    return json.dumps({"paragraphs": [{"anchor": anchor, "paragraph": text} for anchor, text in items]})


def covered_room(tmp_path: Path) -> Path:
    """The small room's run folder with a tree of three findings and a report carrying one."""
    room, run_dir = small_room(tmp_path)
    built = {"model": MODEL, "groups": [{"docs": ["a.txt", "b.txt", "c.txt"], "findings": FINDINGS}]}
    (run_dir / "tree.json").write_text(json.dumps(built), encoding="utf-8")
    (run_dir / "digest.md").write_text(tree.tree_digest(room, run_dir, built), encoding="utf-8")
    (run_dir / "report.md").write_text(REPORT, encoding="utf-8")
    return run_dir


def run_cover(tmp_path: Path, gateway: FakeGateway, ledger_rows: str = "") -> tuple[Path, dict]:
    run_dir = covered_room(tmp_path)
    ledger = write_ledger(tmp_path / "LEDGER.md")
    if ledger_rows:
        with open(ledger.path, "a", encoding="utf-8") as handle:
            handle.write(ledger_rows)
    record = coverage.cover(run_dir, gateway=gateway, ledger=ledger, model=MODEL, sample="small")
    return run_dir, record


def headings(report: str) -> list[str]:
    return [line[3:].strip() for line in report.splitlines() if line.startswith("## ")]


def section(report: str, heading: str) -> str:
    return report.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


def anchors(found: list[dict]) -> list[str]:
    return [item["anchor"] for item in found]


# ---------------------------------------------------------------- the free check


def test_a_finding_whose_anchor_is_in_no_body_paragraph_is_uncarried():
    built = {"groups": [{"findings": FINDINGS}]}
    assert anchors(coverage.uncarried(built, REPORT)) == ["b.txt#l1", "c.txt#l1"]


def test_the_schedule_under_evidence_carries_nothing():
    built = {"groups": [{"findings": FINDINGS}]}
    report = REPORT.replace("1. The lease is a lease [b.txt | b.txt#l1].", f"1. {GOOD_LEASE}")
    assert anchors(coverage.uncarried(built, report)) == ["c.txt#l1"]
    # the same words in the schedule alone do not carry it
    assert "b.txt#l1" in anchors(coverage.uncarried(built, REPORT))


def test_a_paragraph_missing_a_figure_of_three_digits_does_not_carry_the_finding():
    built = {"groups": [{"findings": [FINDINGS[2]]}]}
    report = REPORT.replace(
        "2. The officer has an agreement [c.txt | c.txt#l1].",
        "2. The officer is paid a bonus on a change of control [c.txt | c.txt#l1].",
    )
    assert anchors(coverage.uncarried(built, report)) == ["c.txt#l1"]
    carried = report.replace("paid a bonus on", "paid a bonus of $200,000 on")
    assert coverage.uncarried(built, carried) == []


def test_a_paragraph_with_under_half_the_content_words_does_not_carry_the_finding():
    built = {"groups": [{"findings": [FINDINGS[1]]}]}
    assert anchors(coverage.uncarried(built, REPORT)) == ["b.txt#l1"]
    half = REPORT.replace("1. The lease is a lease", "1. The office lease charges rent")
    assert coverage.uncarried(built, half) == []


def test_the_check_command_prints_the_counts_and_calls_no_model(tmp_path, capsys):
    run_dir = covered_room(tmp_path)
    gateway = FakeGateway(error=AssertionError("the free check made a call"))
    assert coverage.main([str(run_dir), "--check"], gateway=gateway) == 0
    out = capsys.readouterr().out
    assert "findings 3" in out and "uncarried 2" in out
    assert gateway.calls == []
    assert (run_dir / "report.md").read_text(encoding="utf-8") == REPORT


# ---------------------------------------------------------------- the coverage call


def test_the_call_is_given_only_the_uncarried_findings(tmp_path):
    gateway = FakeGateway(paragraphs_reply([("b.txt#l1", GOOD_LEASE)]))
    run_cover(tmp_path, gateway)
    assert len(gateway.calls) == 1
    sent = "\n".join(message["content"] for message in gateway.calls[0]["messages"])
    for finding in FINDINGS[1:]:
        assert finding["anchor"] in sent and finding["finding"] in sent and finding["quote"] in sent
        assert finding["doc"] in sent
    assert "a.txt#l1" not in sent
    assert "Recommendation: proceed" not in sent
    assert "Findings from every document" not in sent
    assert gateway.calls[0]["messages"] == coverage.coverage_messages(FINDINGS[1:])


def test_a_kept_paragraph_goes_under_further_findings_at_the_end_of_the_lesser_issues(tmp_path):
    gateway = FakeGateway(paragraphs_reply([("b.txt#l1", GOOD_LEASE), ("c.txt#l1", WRONG_ANCHOR_BONUS)]))
    run_dir, record = run_cover(tmp_path, gateway)
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    lesser = section(report, "Lesser issues")
    assert "### Further findings" in lesser
    assert f"3. {GOOD_LEASE}" in lesser.split("### Further findings", 1)[1]
    # the writer's own lesser issues are left as they were
    assert lesser.index("1. The lease is a lease") < lesser.index("### Further findings")
    assert report.index("### Further findings") < report.index("## Open items")
    assert anchors(record["added"]) == ["b.txt#l1"]


def test_a_paragraph_citing_another_anchor_is_dropped_and_its_finding_is_left_out(tmp_path):
    gateway = FakeGateway(paragraphs_reply([("b.txt#l1", GOOD_LEASE), ("c.txt#l1", WRONG_ANCHOR_BONUS)]))
    run_dir, record = run_cover(tmp_path, gateway)
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert WRONG_ANCHOR_BONUS not in report
    assert anchors(record["dropped"]) == ["c.txt#l1"]
    assert "a.txt#l1" in record["dropped"][0]["reason"]
    left_out = section(report, "Left out")
    assert BONUS in left_out and "[c.txt | c.txt#l1]" in left_out
    assert anchors(record["left_out"]) == ["c.txt#l1"]


def test_a_paragraph_whose_figure_is_not_in_its_section_is_dropped(tmp_path):
    gateway = FakeGateway(paragraphs_reply([("b.txt#l1", GOOD_LEASE), ("c.txt#l1", WRONG_NUMBER_BONUS)]))
    run_dir, record = run_cover(tmp_path, gateway)
    assert anchors(record["dropped"]) == ["c.txt#l1"]
    assert "300" in record["dropped"][0]["reason"]
    assert WRONG_NUMBER_BONUS not in (run_dir / "report.md").read_text(encoding="utf-8")
    assert anchors(record["left_out"]) == ["c.txt#l1"]


def test_the_headings_keep_their_order_and_left_out_sits_before_the_evidence(tmp_path):
    gateway = FakeGateway(paragraphs_reply([("b.txt#l1", GOOD_LEASE), ("c.txt#l1", WRONG_ANCHOR_BONUS)]))
    run_dir, _ = run_cover(tmp_path, gateway)
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert headings(report) == [*write.HEADINGS[:-1], coverage.LEFT_OUT_HEADING, write.EVIDENCE_HEADING]
    assert write.is_whole(report.split("\n## Evidence", 1)[0])
    assert report.split("## Evidence", 1)[1] == REPORT.split("## Evidence", 1)[1]


def test_after_coverage_no_finding_is_missing_from_both_the_body_and_left_out(tmp_path):
    gateway = FakeGateway(paragraphs_reply([("b.txt#l1", GOOD_LEASE), ("c.txt#l1", WRONG_ANCHOR_BONUS)]))
    run_dir, _ = run_cover(tmp_path, gateway)
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    built = json.loads((run_dir / "tree.json").read_text(encoding="utf-8"))
    left_out = section(report, "Left out")
    for finding in coverage.uncarried(built, report):
        assert f"[{finding['doc']} | {finding['anchor']}]" in left_out
    assert anchors(coverage.uncarried(built, report)) == ["c.txt#l1"]


def test_the_covered_report_still_verifies(tmp_path):
    gateway = FakeGateway(paragraphs_reply([("b.txt#l1", GOOD_LEASE), ("c.txt#l1", WRONG_ANCHOR_BONUS)]))
    run_dir, _ = run_cover(tmp_path, gateway)
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    sections = verify.read_jsonl(run_dir / "sections.jsonl")
    index = verify.read_jsonl(run_dir / "index.jsonl")
    digest = (run_dir / "digest.md").read_text(encoding="utf-8")
    assert verify.check_citations(report, sections, index) == []
    assert verify.check_numbers(report, sections, digest) == []
    assert verify.check_sections(report) == []
    # the left out list is code's and is not read as the model's prose
    assert coverage.LEFT_OUT_HEADING not in [name for name, _ in verify.narrative_blocks(report)]


def test_the_pre_coverage_report_and_the_record_are_kept(tmp_path):
    gateway = FakeGateway(paragraphs_reply([("b.txt#l1", GOOD_LEASE), ("c.txt#l1", WRONG_ANCHOR_BONUS)]))
    run_dir, record = run_cover(tmp_path, gateway)
    assert (run_dir / "report-pre-coverage.md").read_text(encoding="utf-8") == REPORT
    written = json.loads((run_dir / "coverage.json").read_text(encoding="utf-8"))
    assert written == record
    assert anchors(written["uncarried_before"]) == ["b.txt#l1", "c.txt#l1"]
    assert written["model"] == MODEL
    assert written["tokens_in"] == 1200 and written["tokens_out"] == 300
    assert written["dollars"] > 0


def test_the_call_books_one_ledger_row_on_phase_8(tmp_path):
    gateway = FakeGateway(paragraphs_reply([("b.txt#l1", GOOD_LEASE)]))
    run_cover(tmp_path, gateway)
    rows = Ledger(tmp_path / "LEDGER.md").rows()
    booked = [row for row in rows if row["model"] == MODEL]
    assert len(booked) == 1
    assert booked[0]["phase"] == "8" and booked[0]["sample"] == "small-coverage"
    assert (booked[0]["tokens_in"], booked[0]["tokens_out"]) == (1200, 300)


def test_a_failed_call_puts_every_uncarried_finding_in_left_out(tmp_path):
    gateway = FakeGateway(error=NoReply("no reply", tokens_in=10, tokens_out=5))
    run_dir, record = run_cover(tmp_path, gateway)
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "### Further findings" not in report
    assert anchors(record["left_out"]) == ["b.txt#l1", "c.txt#l1"]
    left_out = section(report, "Left out")
    assert "[b.txt | b.txt#l1]" in left_out and "[c.txt | c.txt#l1]" in left_out
    assert record["error"]
    assert headings(report)[-2:] == [coverage.LEFT_OUT_HEADING, write.EVIDENCE_HEADING]


def test_a_reply_that_is_not_json_puts_every_uncarried_finding_in_left_out(tmp_path):
    run_dir, record = run_cover(tmp_path, FakeGateway("I could not do this."))
    assert anchors(record["left_out"]) == ["b.txt#l1", "c.txt#l1"]
    assert record["added"] == []


def test_the_coverage_cap_refuses_the_call_and_everything_goes_to_left_out(tmp_path):
    spent = f"| 2026-10-15 | avid-coverage | 8 | {MODEL} | 1 | 1 | 3.4999 | 46.5001 |\n"
    gateway = FakeGateway(paragraphs_reply([("b.txt#l1", GOOD_LEASE)]))
    run_dir, record = run_cover(tmp_path, gateway, spent)
    assert gateway.calls == []
    assert anchors(record["left_out"]) == ["b.txt#l1", "c.txt#l1"]
    assert "cap" in record["error"]
    assert coverage.COVERAGE_CAP_DOLLARS == 3.50


def test_a_full_phase_8_does_not_refuse_the_coverage_call(tmp_path):
    spent = f"| 2026-10-15 | avid | 8 | {MODEL} | 1 | 1 | 11.4900 | 38.5100 |\n"
    gateway = FakeGateway(paragraphs_reply([("b.txt#l1", GOOD_LEASE)]))
    _, record = run_cover(tmp_path, gateway, spent)
    assert len(gateway.calls) == 1
    assert anchors(record["added"]) == ["b.txt#l1"]


def test_nothing_uncarried_makes_no_call(tmp_path):
    run_dir = covered_room(tmp_path)
    built = {"groups": [{"findings": FINDINGS[:1]}]}
    (run_dir / "tree.json").write_text(json.dumps(built), encoding="utf-8")
    gateway = FakeGateway(error=AssertionError("called"))
    record = coverage.cover(run_dir, gateway=gateway, ledger=write_ledger(tmp_path / "L.md"),
                            model=MODEL, sample="small")
    assert gateway.calls == [] and record["left_out"] == []
    assert coverage.LEFT_OUT_HEADING not in headings((run_dir / "report.md").read_text(encoding="utf-8"))


def test_the_default_model_is_sonnet():
    assert coverage.DEFAULT_MODEL == "anthropic/claude-sonnet-5.5"


# ---------------------------------------------------------------- wired into the writer


def test_the_writer_in_tree_mode_runs_coverage_unless_told_not_to(tmp_path):
    from test_tree import TreeTransport, built_tree, gateway_for

    report = (
        "## Executive summary\n\nRecommendation: proceed.\n\n"
        "The loan is repaid on a change of control [a.txt | a.txt#l1].\n\n"
        "## Findings ranked by materiality\n\n"
        "1. The loan is repaid on a change of control [a.txt | a.txt#l1].\n\n"
        "## The most material issue quantified\n\nNone [a.txt | a.txt#l1].\n\n"
        "## Lesser issues\n\n1. None [c.txt | c.txt#l1].\n\n## Open items\n\n1. None [c.txt | c.txt#l1].\n"
    )
    covered = paragraphs_reply([("c.txt#l1", "The officer is paid the bonus [c.txt | c.txt#l1].")])
    for flag, calls in (([], 2), (["--no-coverage"], 1)):
        room, run_dir = small_room(tmp_path / str(calls))
        (run_dir / tree.TREE_FILE).write_text(json.dumps(built_tree()), encoding="utf-8")
        transport = TreeTransport(lambda body, call: covered if "paragraphs" in body["messages"][0]["content"] else report)
        code = write.main([str(room), str(run_dir), "--tree", "--phase", "8", *flag],
                          gateway=gateway_for(transport), ledger=write_ledger(tmp_path / f"L{calls}.md"))
        assert code == 0
        assert len(transport.bodies) == calls
        assert (run_dir / "coverage.json").exists() == (calls == 2)
    written = (tmp_path / "2" / "run" / "report.md").read_text(encoding="utf-8")
    assert "### Further findings" in written and "the bonus [c.txt | c.txt#l1]" in written


# ---------------------------------------------------------------- the pinned runs


PINNED = {
    "avid": ("avid/claude-t4", 235, 77),
    "mri": ("mri/claude-t4", 260, 69),
    "sensar": ("sensar/claude", 282, 123),
}

# The findings the writer was handed and dropped, which the free check has to find.
KNOWN_DROPS = {
    "avid": [
        "2007-12-19_000089684107000048_exhibit_10-1.txt#l57",
        "2005-03-21_000110465905012177_a05-5408_1ex10d1.txt#l38",
        "2005-03-21_000110465905012177_a05-5408_1ex10d2.txt#l38",
    ],
    "mri": [],
    "sensar": ["2004-10-13_000078985104000034_exh_10.txt#l125"],
}


def runs_root() -> Path:
    return Path(os.environ.get("RLM_COVERAGE_RUNS", ROOT / "runs"))


def pinned_run(room: str) -> Path:
    run_dir = runs_root() / PINNED[room][0]
    if not (run_dir / "tree.json").exists() or not (run_dir / "report.md").exists():
        pytest.skip(f"no pinned run of {room} under {runs_root()}")
    return run_dir


def pinned_report(run_dir: Path) -> str:
    """The writer's report: the pre-coverage copy where coverage has run on the pinned run."""
    before = run_dir / "report-pre-coverage.md"
    return (before if before.exists() else run_dir / "report.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("room", sorted(PINNED))
def test_the_free_check_counts_the_uncarried_findings_of_the_pinned_runs(room):
    run_dir = pinned_run(room)
    built = json.loads((run_dir / "tree.json").read_text(encoding="utf-8"))
    found = coverage.uncarried(built, pinned_report(run_dir))
    assert len(coverage.all_findings(built)) == PINNED[room][1]
    assert len(found) == PINNED[room][2]
    for anchor in KNOWN_DROPS[room]:
        assert anchor in anchors(found)


def test_the_known_drops_are_the_ones_the_issue_names():
    run_dir = pinned_run("avid")
    built = json.loads((run_dir / "tree.json").read_text(encoding="utf-8"))
    by_anchor = {item["anchor"]: item["finding"] for item in coverage.all_findings(built)}
    assert "725,000" in by_anchor[KNOWN_DROPS["avid"][0]]
    assert all("Voting Agreement" in by_anchor[anchor] for anchor in KNOWN_DROPS["avid"][1:])
    sensar = pinned_run("sensar")
    built = json.loads((sensar / "tree.json").read_text(encoding="utf-8"))
    finding = {item["anchor"]: item["finding"] for item in coverage.all_findings(built)}[KNOWN_DROPS["sensar"][0]]
    assert "Comerica" in finding and "$4,000,000" in finding


@pytest.mark.parametrize("room", sorted(PINNED))
def test_the_check_command_reads_the_pinned_runs(room, capsys):
    run_dir = pinned_run(room)
    if (run_dir / "report-pre-coverage.md").exists():
        pytest.skip(f"coverage has run on {run_dir}; the check reads the covered report")
    assert coverage.main([str(run_dir), "--check"]) == 0
    out = capsys.readouterr().out
    assert re.search(rf"findings {PINNED[room][1]}\b", out)
    assert re.search(rf"uncarried {PINNED[room][2]}\b", out)
