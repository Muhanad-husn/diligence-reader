"""Issue #160 step 3: both rankers on the three samples and on the Avid practice room.

The tests are free: they read the run folders the paid runs leave and skip when one is missing,
the way test_phase8_gate.py reads the gate's. The runs root is RLM_PICK_RUNS, runs/ of this
checkout by default. Each sample runs once per arm under <runs>/<sample>-pick-<arm>, and its
planted-fact recall in each arm must be at least what phase 8 scored on it. Avid, the open
practice room, runs once per arm under <runs>/avid/pick-<arm> and is checked for shape only;
its score is read by hand against its open key.
"""

import json
import os
from pathlib import Path

import pytest

from conftest import ROOT, SAMPLES
from rlm import pick
from rlm.key import room_documents
from rlm.notes import note_name

ARMS = ("llm", "jev")

# The planted-fact recall phase 8 scored on each sample, from PLAN.md's status table.
PHASE_8_RECALL = {"atlas": 100.0, "northwind": 87.5, "northstar-dental": 100.0}


def runs_root() -> Path:
    return Path(os.environ.get("RLM_PICK_RUNS", ROOT / "runs"))


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sample_run(sample: str, arm: str) -> Path:
    run_dir = runs_root() / f"{sample}-pick-{arm}"
    if not (run_dir / "grade.json").exists():
        pytest.skip(f"no pick run of {sample} by {arm} under {runs_root()}")
    return run_dir


def flag_count(run_dir: Path, doc: str) -> int:
    path = run_dir / "notes" / note_name(doc)
    return len(read(path).get("flags", [])) if path.exists() else 0


def check_pick(room: Path, run_dir: Path, arm: str) -> dict:
    """pick.json covers every document once, and chosen is the walk the choosing rule takes."""
    picked = read(run_dir / "pick.json")
    assert picked["arm"] == arm
    assert picked["deal"] in pick.DEALS
    ranked = [row["doc"] for row in picked["ranked"]]
    assert sorted(ranked) == sorted(room_documents(room))
    chosen = picked["chosen"]
    assert chosen and chosen == ranked[: len(chosen)]
    rows = sum(flag_count(run_dir, doc) for doc in chosen)
    assert picked["rows"] == rows
    assert rows <= pick.DIGEST_ROWS or len(chosen) == 1
    if len(chosen) < len(ranked):
        assert rows + flag_count(run_dir, ranked[len(chosen)]) > pick.DIGEST_ROWS
    return picked


@pytest.mark.parametrize("arm", ARMS)
def test_each_sample_keeps_its_phase_8_recall_in_each_arm(sample, arm):
    run_dir = sample_run(sample, arm)
    grade = read(run_dir / "grade.json")
    assert grade["recall"] >= PHASE_8_RECALL[sample], grade["missed"]


@pytest.mark.parametrize("arm", ARMS)
def test_each_sample_run_ranks_every_document_and_chooses_by_the_rule(sample, arm):
    run_dir = sample_run(sample, arm)
    check_pick(ROOT / "samples" / sample, run_dir, arm)
    assert read(run_dir / "run.json")["status"] == "done"
    assert not (run_dir / "map.json").exists()
    assert not (run_dir / "dossier.md").exists()
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert report.splitlines()[0] == pick.deal_line(read(run_dir / "pick.json")["deal"])


@pytest.mark.parametrize("arm", ARMS)
def test_the_avid_practice_run_ranks_every_document(arm):
    run_dir = runs_root() / "avid" / f"pick-{arm}"
    if not (run_dir / "report.md").exists():
        pytest.skip(f"no Avid practice run by {arm} under {runs_root()}")
    check_pick(runs_root() / "avid" / "room", run_dir, arm)
    assert read(run_dir / "verify.json")["passes"] is True


def test_the_second_jev_pass_on_avid_ranks_every_document():
    run_dir = runs_root() / "avid" / "pick-jev"
    if not (run_dir / "pick-2.json").exists():
        pytest.skip("no second Jev pass on Avid")
    first = read(run_dir / "pick.json")
    second = read(run_dir / "pick-2.json")
    assert sorted(row["doc"] for row in second["ranked"]) == sorted(row["doc"] for row in first["ranked"])
    same = set(first["chosen"]) & set(second["chosen"])
    print(f"jev avid: {len(same)} of {len(first['chosen'])} chosen documents the same in both passes")


assert set(PHASE_8_RECALL) == set(SAMPLES)
