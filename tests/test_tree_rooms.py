"""Issue #160: the tree writer on the three samples and on the Avid practice room.

The tests are free: they read the run folders the paid runs leave and skip when one is missing.
The runs root is RLM_TREE_RUNS, runs/ of this checkout by default. Each sample runs once under
<runs>/<sample>-tree and its planted-fact recall must be at least what phase 8 scored on it.
Avid, the open practice room, runs under <runs>/avid/tree and is checked for shape only; its
score is read by hand against its open key.
"""

import json
import os
from pathlib import Path

import pytest

from conftest import ROOT
from rlm import tree
from rlm.key import room_documents

# The planted-fact recall phase 8 scored on each sample, from PLAN.md's status table.
PHASE_8_RECALL = {"atlas": 100.0, "northwind": 87.5, "northstar-dental": 100.0}


def runs_root() -> Path:
    return Path(os.environ.get("RLM_TREE_RUNS", ROOT / "runs"))


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_tree(room: Path, run_dir: Path) -> dict:
    """tree.json groups every document once in room order, each group within its budget and its
    cap, and every kept finding quotes its own document's note."""
    built = read(run_dir / tree.TREE_FILE)
    groups = built["groups"]
    assert [doc for group in groups for doc in group["docs"]] == list(room_documents(room))
    assert built["cap"] == tree.group_cap(len(groups))
    notes = tree.read_notes(room, run_dir)
    for group in groups:
        assert group["tokens"] <= built["budget"] or len(group["docs"]) == 1
        assert len(group["findings"]) <= built["cap"]
        assert 1 <= group["calls"] <= 2
        kept, _ = tree.check_findings(group["findings"], group["docs"], notes)
        assert len(kept) == len(group["findings"])
    return built


def sample_run(sample: str) -> Path:
    run_dir = runs_root() / f"{sample}-tree"
    if not (run_dir / "grade.json").exists():
        pytest.skip(f"no tree run of {sample} under {runs_root()}")
    return run_dir


def test_each_sample_keeps_its_phase_8_recall_with_the_tree_writer(sample):
    run_dir = sample_run(sample)
    grade = read(run_dir / "grade.json")
    assert grade["recall"] >= PHASE_8_RECALL[sample], grade["missed"]


def test_each_sample_tree_groups_every_document_and_keeps_only_quoted_findings(sample):
    run_dir = sample_run(sample)
    check_tree(ROOT / "samples" / sample, run_dir)
    assert read(run_dir / "run.json")["status"] == "done"
    assert not (run_dir / "map.json").exists()
    assert not (run_dir / "dossier.md").exists()


def test_the_avid_tree_run_groups_every_document_and_verifies():
    run_dir = runs_root() / "avid" / "tree"
    if not (run_dir / "report.md").exists():
        pytest.skip(f"no Avid tree run under {runs_root()}")
    built = check_tree(runs_root() / "avid" / "room", run_dir)
    assert read(run_dir / "verify.json")["passes"] is True
    kept = sum(len(group["findings"]) for group in built["groups"])
    print(f"avid tree: {len(built['groups'])} groups, {kept} findings kept")
