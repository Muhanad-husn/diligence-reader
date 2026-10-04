"""Phase 8 gate: the three gate samples run twice each through the Docker image, from the web page.

The live test builds the runtime image from this checkout, serves it with `docker run` and
RLM_PHASE=8, and starts each sample twice from the web page in Playwright on a real key: the
key pasted, the room chosen as a folder, the estimate confirmed, every stage watched to the end
and every export fetched through the page into the run folder's downloads/. It runs only with
RLM_GATE_LIVE=1 and spends money; the runs book phase 8 to this checkout's LEDGER.md, which is
mounted into the container. The runs root is RLM_GATE_RUNS, runs/ of this checkout by default.

The page sends no run name, so the server names each run with a random id. The test writes a
gate.json into each run folder naming its sample and attempt, and the readback finds the runs
by it. The readback tests are free: they read the runs the live test leaves and skip when one
is missing. They check both runs are done and verified, the first run's recall against the
command line's, every planted fact out of the docx, the PDF and the CSV of each run, the
dollars booked and the key kept out of every file.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from playwright.sync_api import Page, expect

from conftest import ROOT, SAMPLES
from test_phase8_api import EXPORTS as EXPORT_FILES
from test_phase8_api import files_holding, free_port, run_json, sample_room_files
from test_phase8_command import KNOWN_MISSES
from test_phase8_export import EVIDENCE_ABSENT, docx_text, evidence_section, pdf_text, recall
from test_phase8_package import answers, build, docker_answers, sh, wait_for
from test_phase8_web import EXPORTS, Watched, browser, expect_every_stage, paste_key, upload_and_confirm  # noqa: F401

ISSUE = 141
ATTEMPTS = (1, 2)
IMAGE = "diligence-reader:gate"
SERVER_LOG = f"gate-{ISSUE}.server.log"
LIVE = pytest.mark.skipif(
    os.environ.get("RLM_GATE_LIVE") != "1",
    reason="the gate runs three samples twice on a real key and spends money; RLM_GATE_LIVE=1",
)
# A run of atlas takes many minutes; the wait for the last stage allows this much.
GATE_TIMEOUT = 45 * 60_000
# The upload, the estimate and the report page of a large room take longer than a small one's.
STEP_TIMEOUT = 120_000


def runs_root() -> Path:
    return Path(os.environ.get("RLM_GATE_RUNS", ROOT / "runs"))


def label(sample: str, attempt: int) -> str:
    return f"{sample}-{ISSUE}-{attempt}"


def gate_runs(sample: str) -> dict[int, Path]:
    """The run folders under the runs root whose gate.json names this sample, by attempt."""
    found = {}
    root = runs_root()
    if root.exists():
        for marker in root.glob("*/gate.json"):
            said = json.loads(marker.read_text(encoding="utf-8"))
            if said.get("issue") == ISSUE and said.get("sample") == sample:
                found[said["attempt"]] = marker.parent
    return found


def download(folder: Path, fmt: str) -> Path:
    """A run's export as the page downloaded it, named by the run id the way the server names it."""
    return folder / "downloads" / f"{folder.name}-{EXPORT_FILES[fmt][1]}"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- the live gate


@pytest.fixture(scope="module")
def container():
    """The runtime image built from this checkout and served by docker run on a free port.

    The runs root is mounted at /app/runs and this checkout's LEDGER.md at /app/LEDGER.md, so a
    run books phase 8 there. The container's log is saved beside the runs when it stops.
    """
    if not os.environ.get("OPENROUTER_API_KEY"):
        pytest.skip("no OPENROUTER_API_KEY to run on")
    if not docker_answers():
        pytest.skip("docker is not installed or its engine is not running")
    build(ROOT, "runtime", IMAGE)
    runs = runs_root()
    runs.mkdir(parents=True, exist_ok=True)
    port = free_port()
    name = f"rlm-gate-{port}"
    sh(
        "docker", "run", "-d", "--rm", "--name", name, "-p", f"127.0.0.1:{port}:8000",
        "-e", "RLM_PHASE=8", "-e", "RLM_UPDATE_CHECK=off",
        "-v", f"{runs}:/app/runs", "-v", f"{ROOT / 'LEDGER.md'}:/app/LEDGER.md",
        IMAGE,
    )
    try:
        url = f"http://127.0.0.1:{port}"
        assert wait_for(lambda: answers(f"{url}/runs/none-such"), 60), "the container did not answer"
        yield SimpleNamespace(port=port, url=url)
    finally:
        logs = sh("docker", "logs", name, check=False)
        (runs / SERVER_LOG).write_text(logs.stdout + logs.stderr, encoding="utf-8")
        sh("docker", "rm", "-f", name, check=False)


def room_on_disk(tmp_path: Path, sample: str) -> Path:
    """The sample's room written under tmp_path: its key's documents, its brief and its key."""
    room = tmp_path / sample
    for relative, data in sample_room_files(sample):
        target = room / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return room


@LIVE
@pytest.mark.parametrize(
    ("gate_sample", "attempt"),
    [(sample, attempt) for sample in SAMPLES for attempt in ATTEMPTS],
    ids=[label(sample, attempt) for sample in SAMPLES for attempt in ATTEMPTS],
)
def test_the_page_runs_the_room_in_the_image(container, page: Page, tmp_path, gate_sample, attempt):
    key = os.environ["OPENROUTER_API_KEY"]
    stale = gate_runs(gate_sample).get(attempt)
    if stale is not None:
        shutil.rmtree(stale)
    watched = Watched(page, container)
    expect.set_options(timeout=STEP_TIMEOUT)
    try:
        page.goto(container.url)
        paste_key(page, key)
        upload_and_confirm(page, "#room-folder", room_on_disk(tmp_path, gate_sample))

        run_id = page.inner_text("#run-id").strip()
        folder = runs_root() / run_id
        assert run_id and folder.is_dir(), run_id
        marker = {"issue": ISSUE, "sample": gate_sample, "attempt": attempt, "label": label(gate_sample, attempt)}
        (folder / "gate.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")

        # The error card is in the page while hidden, so it joins the wait only when shown.
        ended = page.locator('#stages [data-stage="export"][data-state="finished"], #error:visible')
        expect(ended.first).to_be_visible(timeout=GATE_TIMEOUT)
        expect(page.locator("#error")).to_be_hidden()
        expect_every_stage(page, "finished")
        assert run_json(folder)["status"] == "done"

        downloads = folder / "downloads"
        downloads.mkdir(exist_ok=True)
        for fmt, _ in EXPORTS:
            link = page.locator(f'#exports a[data-format="{fmt}"]')
            expect(link).to_be_visible()
            fetched = page.request.get(link.evaluate("node => node.href"), timeout=STEP_TIMEOUT)
            assert fetched.status == 200, fmt
            target = download(folder, fmt)
            assert target.name in fetched.headers["content-disposition"], fmt
            target.write_bytes(fetched.body())
    finally:
        expect.set_options(timeout=5_000)

    watched.assert_kept_in(key)
    assert watched.github == []


# ---------------------------------------------------------------- the readback


@pytest.fixture
def gate(sample) -> list[Path]:
    """The sample's two gate runs, first then second; skips when either is missing."""
    found = gate_runs(sample)
    missing = [label(sample, a) for a in ATTEMPTS if a not in found or not (found[a] / "run.json").exists()]
    if missing:
        pytest.skip(f"no gate run {', '.join(missing)} under {runs_root()}")
    return [found[a] for a in ATTEMPTS]


def test_both_gate_runs_are_done_and_pass_the_verifier(gate):
    for folder in gate:
        assert run_json(folder)["status"] == "done", folder.name
        assert read(folder / "verify.json")["passes"] is True, folder.name


# The facts a fresh run may miss for a reason outside phase 8: the command line's own known
# misses, and northwind's cap table, which the map leaves out of the matter on some fresh notes
# (see tests/test_phase3.py, test_map_keeps_the_cap_table_in_northwind_matter_on_fresh_notes).
FRESH_MISSES = {**KNOWN_MISSES, "northwind": [*KNOWN_MISSES["northwind"], "captable-coc-confirmation"]}


def test_the_first_gate_run_recalls_what_the_command_line_does(sample, gate):
    grade = read(gate[0] / "grade.json")
    assert set(grade["missed"]) <= set(FRESH_MISSES.get(sample, []))
    if not grade["missed"]:
        assert grade["recall"] == 100.0
    for root in (runs_root(), ROOT / "runs"):
        cli = root / f"{sample}-cli" / "grade.json"
        if cli.exists() and grade["missed"] == read(cli)["missed"]:
            assert grade["recall"] == read(cli)["recall"]
            break


def test_every_planted_fact_of_the_report_reads_out_of_the_docx_and_the_pdf(sample_dir, gate):
    for folder in gate:
        report = (folder / "report.md").read_text(encoding="utf-8")
        assert download(folder, "md").read_text(encoding="utf-8") == report, folder.name
        _, from_report, _ = recall(sample_dir, report)
        for fmt, text_of in (("docx", docx_text), ("pdf", pdf_text)):
            _, found, _ = recall(sample_dir, text_of(download(folder, fmt)))
            lost = sorted(set(from_report) - set(found))
            assert set(found) == set(from_report), f"{folder.name} {fmt} loses {lost}"


def test_the_csv_carries_every_fact_of_the_evidence_section(sample, sample_dir, gate):
    for folder in gate:
        report = (folder / "report.md").read_text(encoding="utf-8")
        _, from_csv, _ = recall(sample_dir, download(folder, "csv").read_text(encoding="utf-8-sig"))
        _, from_section, _ = recall(sample_dir, evidence_section(report))
        _, from_report, _ = recall(sample_dir, report)
        lost = sorted(set(from_section) - set(from_csv))
        assert set(from_csv) == set(from_section), f"{folder.name} evidence.csv loses {lost}"
        # A fact the report body may carry that the Evidence section does not; a run whose
        # writer did not compute it carries it nowhere.
        assert set(from_report) - set(from_csv) <= EVIDENCE_ABSENT[sample], folder.name


def test_the_gate_runs_booked_their_dollars(gate):
    for folder in gate:
        assert run_json(folder)["dollars"] > 0, folder.name


def test_the_key_is_in_no_file_of_a_gate_run_and_not_in_the_server_log(gate):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("no OPENROUTER_API_KEY to look for")
    for folder in gate:
        assert files_holding(folder, key) == []
    log = runs_root() / SERVER_LOG
    if log.exists():
        assert key.encode("utf-8") not in log.read_bytes()


def readout(terminalreporter):
    firsts, spreads, dollars = [], [], 0.0
    for sample in SAMPLES:
        found = gate_runs(sample)
        recalls = []
        for attempt in ATTEMPTS:
            folder = found.get(attempt)
            if folder is None or not (folder / "grade.json").exists():
                recalls.append(None)
                continue
            recalls.append(read(folder / "grade.json")["recall"])
            spent = run_json(folder)["dollars"]
            dollars += spent
            terminalreporter.write_line(
                f"phase 8 gate {label(sample, attempt)} (run {folder.name}): "
                f"recall {recalls[-1]:g}, spent ${spent:.4f}"
            )
        firsts.append("-" if recalls[0] is None else f"{recalls[0]:g}")
        spreads.append("-" if None in recalls else f"{abs(recalls[0] - recalls[1]):g}")
    if any(value != "-" for value in firsts):
        terminalreporter.write_line(
            f"phase 8 gate: first-run recall {' / '.join(firsts)}, spread {' / '.join(spreads)}, "
            f"six runs ${dollars:.4f}"
        )
