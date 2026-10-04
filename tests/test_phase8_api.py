"""Phase 8 slice 03: the local API, which starts a run, streams its progress and serves the report.

The tests at $0 drive the app through FastAPI's test client on a temporary runs folder. A run is
started by the real LocalRunner as a real child process running the real command, but the child
is a small script the test writes: it builds a gateway on test_phase8_command's RoomTransport,
so nothing leaves the machine, nothing is booked to the real LEDGER.md, and a run on BAD_KEY is
refused the way OpenRouter refuses a bad key. The room is sample 3's, uploaded the way a browser
sends a folder or as one zip.

The live test starts a real server and runs samples 2 and 3 through it on a real key; it runs
only with RLM_API_LIVE=1 and spends money. The tests after it read the run folders it leaves
under runs/<sample>-api and skip when a folder is missing, the way the command line's do.
"""

import io
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import httpx
import pytest
from ag_ui.core import EventType
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import events as events_module
from app.events import Deriver
from app.main import create_app
from app.runner import LocalRunner, runner_from_env
from conftest import ROOT
from rlm import cli, notes, write
from test_phase8_command import KNOWN_MISSES, ROOM, copy_room

GOOD_KEY = "sk-or-v1-test-GOODKEY-0123456789abcdef"
BAD_KEY = "sk-or-v1-test-BADKEY-0123456789abcdef"

TESTS = Path(__file__).resolve().parent
SRC = TESTS.parent / "src"

# The child a test's LocalRunner starts: the real command on a fake transport, refused on BAD_KEY.
CHILD = """import os
import sys

sys.path[:0] = [{tests!r}, {src!r}]

from rlm import cli
from rlm.gateway import Gateway
from test_phase8_command import RoomTransport

key = os.environ["OPENROUTER_API_KEY"]
transport = RoomTransport(status=401 if key == {bad!r} else None)
gateway = Gateway(api_key=key, transport=transport, rate_limit_waits=())
sys.exit(cli.main(sys.argv[1:], gateway=gateway))
"""

EXPORTS = {
    "md": ("text/markdown", "report.md"),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "report.docx",
    ),
    "pdf": ("application/pdf", "report.pdf"),
    "csv": ("text/csv", "evidence.csv"),
}

STEP_TYPES = ("STEP_STARTED", "STEP_FINISHED")
EVERY_STEP = [(kind, stage) for stage in cli.STAGES for kind in STEP_TYPES]


@pytest.fixture
def api(tmp_path):
    """A test client on an app whose LocalRunner starts the fake child, and the runs folder."""
    script = tmp_path / "child.py"
    script.write_text(CHILD.format(tests=str(TESTS), src=str(SRC), bad=BAD_KEY), encoding="utf-8")
    runner = LocalRunner([sys.executable, str(script)])
    runs = tmp_path / "runs"
    app = create_app(runner=runner, runs_root=runs, web_dir=tmp_path / "noweb")
    with TestClient(app) as client:
        client.runner = runner
        client.runs = runs
        yield client
    for run_id in list(runner.processes):
        runner.cancel(run_id)


def room_files(tmp_path: Path, top: str = ROOM) -> list[tuple[str, tuple[str, bytes, str]]]:
    """Sample 3's room as a browser sends a folder: every file named by its path under top."""
    room = copy_room(tmp_path)
    return [
        ("files", (f"{top}/{path.relative_to(room).as_posix()}", path.read_bytes(), "text/plain"))
        for path in sorted(room.rglob("*"))
        if path.is_file()
    ]


def room_zip(tmp_path: Path, top: str = ROOM) -> bytes:
    """Sample 3's room as one zip, every member under top."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for _, (name, data, _) in room_files(tmp_path, top):
            archive.writestr(name, data)
    return buffer.getvalue()


def upload(client, files, key=GOOD_KEY, name=None):
    headers = {"X-OpenRouter-Key": key} if key is not None else {}
    data = {"name": name} if name is not None else {}
    return client.post("/runs", files=files, data=data, headers=headers)


def started(client, tmp_path, key=GOOD_KEY, name=None) -> str:
    """Uploads the room, asks for its estimate and confirms it; the run's id."""
    response = upload(client, room_files(tmp_path), key=key, name=name)
    assert response.status_code == 201, response.text
    run_id = response.json()["id"]
    assert client.get(f"/runs/{run_id}/estimate").status_code == 200
    assert client.post(f"/runs/{run_id}/confirm").status_code == 202
    return run_id


def read_events(client, run_id: str) -> list[dict]:
    """The run's event stream read to its end, one decoded event per entry."""
    found = []
    with client.stream("GET", f"/runs/{run_id}/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        for line in response.iter_lines():
            if line.startswith("data: "):
                found.append(json.loads(line[len("data: "):]))
    return found


def steps(found: list[dict]) -> list[tuple[str, str]]:
    return [(event["type"], event["stepName"]) for event in found if event["type"] in STEP_TYPES]


def noted_and_paid(found: list[dict]) -> bool:
    """Says whether one STATE_DELTA carries documents noted and dollars both above zero."""
    for event in found:
        if event["type"] != "STATE_DELTA":
            continue
        values = {op["path"]: op["value"] for op in event["delta"]}
        if (values.get("/documents_noted") or 0) > 0 and (values.get("/dollars") or 0) > 0:
            return True
    return False


def files_holding(folder: Path, *secrets: str) -> list[str]:
    """Every file under folder whose bytes hold one of the secrets."""
    found = []
    for path in folder.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            if any(secret.encode("utf-8") in data for secret in secrets):
                found.append(str(path))
    return found


def run_json(folder: Path) -> dict:
    return json.loads((folder / "run.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- the upload


def test_a_folder_upload_lands_at_the_room_root(api, tmp_path):
    response = upload(api, room_files(tmp_path))

    assert response.status_code == 201
    room = api.runs / response.json()["id"] / response.json()["id"]
    assert (room / "cim.md").exists()
    assert (room / "brief.md").exists()
    assert (room / "key.json").exists()
    assert not (room / ROOM).exists()


def test_a_zip_upload_lands_at_the_room_root(api, tmp_path):
    files = [("files", ("room.zip", room_zip(tmp_path), "application/zip"))]

    response = upload(api, files, name="zipped")

    assert response.status_code == 201
    assert response.json() == {"id": "zipped"}
    room = api.runs / "zipped" / "zipped"
    assert (room / "cim.md").exists()
    assert (room / "key.json").exists()
    assert not (room / ROOM).exists()
    assert not (room / "room.zip").exists()


@pytest.mark.parametrize("bad", ["../evil.md", "room/../../evil.md", "/evil.md", "C:/evil.md"])
def test_a_file_path_that_leaves_the_room_is_refused(api, tmp_path, bad):
    files = [("files", ("room/cim.md", b"a line", "text/plain")), ("files", (bad, b"x", "text/plain"))]

    response = upload(api, files)

    assert response.status_code == 400
    assert not list(tmp_path.rglob("evil.md"))


@pytest.mark.parametrize("bad", ["../evil.md", "room/../../evil.md", "/evil.md"])
def test_a_zip_member_that_leaves_the_room_is_refused(api, tmp_path, bad):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("room/cim.md", "a line")
        archive.writestr(bad, "x")
    files = [("files", ("room.zip", buffer.getvalue(), "application/zip"))]

    response = upload(api, files)

    assert response.status_code == 400
    assert not list(tmp_path.rglob("evil.md"))


@pytest.mark.parametrize("key", [None, "", "   "])
def test_an_upload_without_a_key_is_refused(api, tmp_path, key):
    response = upload(api, room_files(tmp_path), key=key)

    assert response.status_code == 400
    assert response.json()["code"] == "key-missing"
    assert not api.runs.exists() or not any(api.runs.iterdir())


@pytest.mark.parametrize("name", ["Upper", "-dash", "has space", "a" * 65, "../up"])
def test_a_bad_name_is_refused(api, tmp_path, name):
    assert upload(api, room_files(tmp_path), name=name).status_code == 400


def test_a_taken_name_is_refused(api, tmp_path):
    assert upload(api, room_files(tmp_path), name="taken").status_code == 201
    assert upload(api, room_files(tmp_path), name="taken").status_code == 409


def test_an_unknown_run_is_not_found(api):
    assert api.get("/runs/nosuchrun").status_code == 404


# ---------------------------------------------------------------- the estimate


def test_the_estimate_ingests_and_prices_and_starts_nothing(api, tmp_path):
    run_id = upload(api, room_files(tmp_path)).json()["id"]

    response = api.get(f"/runs/{run_id}/estimate")

    assert response.status_code == 200
    found = response.json()
    assert found["tokens"] > 0
    assert found["tokens"] == found["notes_tokens"] + found["write_tokens"]
    assert found["dollars"] > 0
    assert found["notes_model"] == notes.DEFAULT_MODEL
    assert found["write_model"] == write.DEFAULT_MODEL
    run_dir = api.runs / run_id
    assert (run_dir / "sections.jsonl").exists()
    assert (run_dir / "index.jsonl").exists()
    assert api.runner.status(run_id) == "none"
    assert api.get(f"/runs/{run_id}").json() == {"state": None, "process": "none"}


def test_an_unreadable_file_fails_the_estimate_with_its_code(api, tmp_path):
    files = room_files(tmp_path)
    files.append(("files", (f"{ROOM}/broken.pdf", b"this is not a pdf", "application/pdf")))
    files = [entry for entry in files if not entry[1][0].endswith("key.json")]
    run_id = upload(api, files).json()["id"]

    response = api.get(f"/runs/{run_id}/estimate")

    assert response.status_code == 422
    assert response.json()["code"] == "unreadable-file"
    state = run_json(api.runs / run_id)
    assert (state["status"], state["stage"], state["code"]) == ("failed", "ingest", "unreadable-file")


# ---------------------------------------------------------------- a run


def test_a_confirmed_run_streams_every_stage_and_serves_the_report(api, tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    run_id = started(api, tmp_path)
    assert GOOD_KEY not in os.environ.values()

    found = read_events(api, run_id)

    assert found[0]["type"] == "RUN_STARTED"
    assert found[0]["runId"] == run_id
    assert found[-1]["type"] == "RUN_FINISHED"
    assert steps(found) == EVERY_STEP
    assert noted_and_paid(found)
    assert found[-1]["result"]["dollars"] > 0

    report = api.get(f"/runs/{run_id}/report")
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("text/markdown")
    assert "## Executive summary" in report.text

    for fmt, (media, _) in EXPORTS.items():
        response = api.get(f"/runs/{run_id}/export/{fmt}")
        assert response.status_code == 200, fmt
        assert response.headers["content-type"].startswith(media), fmt
        assert response.content, fmt
        name = f"{run_id}-evidence.csv" if fmt == "csv" else f"{run_id}-report.{fmt}"
        assert name in response.headers["content-disposition"], fmt
    assert api.get(f"/runs/{run_id}/export/html").status_code == 400

    state = api.get(f"/runs/{run_id}").json()
    assert state["state"]["status"] == "done"
    assert state["process"] == "exited"
    assert files_holding(api.runs / run_id, GOOD_KEY) == []
    assert GOOD_KEY not in caplog.text
    assert all(GOOD_KEY not in record.getMessage() for record in caplog.records)
    assert GOOD_KEY not in os.environ.values()


def test_an_api_runs_summaries_name_the_run(api, tmp_path):
    run_id = started(api, tmp_path, name="named-run")
    assert run_id == "named-run"
    assert read_events(api, run_id)[-1]["type"] == "RUN_FINISHED"

    for summary in ("notes-summary.json", "write-summary.json"):
        found = json.loads((api.runs / run_id / summary).read_text(encoding="utf-8"))
        assert found["sample"] == run_id, summary


def test_a_running_run_cannot_be_confirmed_twice(api, tmp_path):
    run_id = started(api, tmp_path)

    assert api.post(f"/runs/{run_id}/confirm").status_code == 409
    assert api.post(f"/runs/{run_id}/retry").status_code == 409
    read_events(api, run_id)


def test_a_missing_report_and_export_are_not_found(api, tmp_path):
    run_id = upload(api, room_files(tmp_path)).json()["id"]

    assert api.get(f"/runs/{run_id}/report").status_code == 404
    assert api.get(f"/runs/{run_id}/export/pdf").status_code == 404


def test_a_bad_key_stops_at_notes_and_a_retry_with_a_good_key_resumes(api, tmp_path):
    run_id = started(api, tmp_path, key=BAD_KEY)
    run_dir = api.runs / run_id

    first = read_events(api, run_id)

    assert first[-1]["type"] == "RUN_ERROR"
    assert first[-1]["code"] == "key-refused"
    assert first[-1]["message"]
    assert run_json(run_dir)["stage"] == "notes"
    assert run_json(run_dir)["status"] == "failed"
    sections_mtime = (run_dir / "sections.jsonl").stat().st_mtime_ns

    response = api.post(f"/runs/{run_id}/retry", headers={"X-OpenRouter-Key": GOOD_KEY})
    assert response.status_code == 202
    second = read_events(api, run_id)

    assert second[0]["type"] == "RUN_STARTED"
    assert second[-1]["type"] == "RUN_FINISHED"
    assert steps(second) == EVERY_STEP
    assert (run_dir / "sections.jsonl").stat().st_mtime_ns == sections_mtime
    assert run_json(run_dir)["status"] == "done"
    assert files_holding(run_dir, GOOD_KEY, BAD_KEY) == []


def test_a_confirm_with_no_key_held_or_given_is_refused(api, tmp_path):
    run_id = upload(api, room_files(tmp_path)).json()["id"]
    api.get(f"/runs/{run_id}/estimate")
    api.app.state.keys.pop(run_id)

    response = api.post(f"/runs/{run_id}/confirm")

    assert response.status_code == 400
    assert response.json()["code"] == "key-missing"
    assert api.runner.status(run_id) == "none"


# ---------------------------------------------------------------- the cited section


def test_the_sections_endpoint_returns_a_cited_section(api, tmp_path):
    run_id = upload(api, room_files(tmp_path)).json()["id"]
    api.get(f"/runs/{run_id}/estimate")

    response = api.get(f"/runs/{run_id}/sections/cim.md%23l1")

    assert response.status_code == 200
    found = response.json()
    assert found["anchor"] == "cim.md#l1"
    assert found["doc"] == "cim.md"
    assert set(found) == {"anchor", "doc", "heading", "text"}
    assert found["text"].strip()
    nested = api.get(f"/runs/{run_id}/sections/board_materials/q1-board-update.md%23l1")
    assert nested.status_code == 200
    assert nested.json()["doc"] == "board_materials/q1-board-update.md"
    assert api.get(f"/runs/{run_id}/sections/cim.md%23l99999").status_code == 404


# ---------------------------------------------------------------- the events, derived


def state(stage, status="running", code=None, noted=0, dollars=0.0, estimate=0.05, recall=None):
    return {
        "stage": stage,
        "status": status,
        "code": code,
        "documents_noted": noted,
        "dollars": dollars,
        "estimate": estimate,
        "recall": recall,
        "version": "0.8.0",
    }


def kinds(found) -> list[str]:
    return [event.type.value for event in found]


def step_pairs(found) -> list[tuple[str, str]]:
    return [(event.type.value, event.step_name) for event in found if event.type.value in STEP_TYPES]


def test_a_run_that_jumps_stages_still_gets_every_pair_in_order():
    deriver = Deriver("r1")
    found = []
    found += deriver.feed(None, 0, "running")
    assert kinds(found) == ["RUN_STARTED", "STATE_SNAPSHOT"]
    assert found[1].snapshot == {"stage": None, "documents_noted": 0, "dollars": 0.0, "estimate": None}
    found += deriver.feed(state("ingest"), 0, "running")
    found += deriver.feed(state("notes", noted=0), 3, "running")
    found += deriver.feed(state("dossier", noted=5, dollars=0.01), 5, "running")
    found += deriver.feed(state("export", "done", noted=5, dollars=0.02, recall=100.0), 5, "exited")

    assert found[0].type == EventType.RUN_STARTED
    assert found[0].run_id == "r1" and found[0].thread_id == "r1"
    assert found[-1].type == EventType.RUN_FINISHED
    assert found[-1].result == {"recall": 100.0, "dollars": 0.02}
    assert step_pairs(found) == EVERY_STEP
    noted = [
        op.value if hasattr(op, "value") else op["value"]
        for event in found
        if event.type == EventType.STATE_DELTA
        for op in event.delta
        if (op.path if hasattr(op, "path") else op["path"]) == "/documents_noted"
    ]
    assert 3 in noted and 5 in noted
    assert deriver.feed(state("export", "done"), 5, "exited") == []


def test_a_failed_state_while_the_process_runs_is_not_terminal():
    deriver = Deriver("r2")
    found = deriver.feed(state("notes", "failed", "key-refused"), 0, "running")

    assert "RUN_ERROR" not in kinds(found)
    assert "RUN_FINISHED" not in kinds(found)

    found = deriver.feed(state("notes", "failed", "key-refused"), 0, "exited")
    assert kinds(found)[-1] == "RUN_ERROR"
    assert found[-1].code == "key-refused"
    assert "key" in found[-1].message.lower()
    assert deriver.feed(state("notes", "failed", "key-refused"), 0, "exited") == []


def test_a_running_state_with_its_process_gone_is_unexpected():
    deriver = Deriver("r3")
    found = deriver.feed(state("write"), 4, "exited")

    assert kinds(found)[0] == "RUN_STARTED"
    assert kinds(found)[-1] == "RUN_ERROR"
    assert found[-1].code == "unexpected"
    assert deriver.feed(state("write"), 4, "exited") == []


def test_every_error_code_has_a_one_line_fix():
    for code in cli.ERROR_CODES:
        deriver = Deriver("r")
        found = deriver.feed(state("notes", "failed", code), 0, "exited")
        assert found[-1].code == code
        assert found[-1].message and "\n" not in found[-1].message


def test_a_run_not_yet_confirmed_gives_nothing():
    assert Deriver("r4").feed(None, 0, "none") == []


def test_the_stream_encodes_server_sent_events(tmp_path):
    import asyncio

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run.json").write_text(
        json.dumps(state("export", "done", noted=2, dollars=0.01, recall=100.0)), encoding="utf-8"
    )

    class Gone:
        def status(self, run_id):
            return "exited"

    async def collect():
        return [chunk async for chunk in events_module.stream("r5", run_dir, Gone(), poll=0.01)]

    chunks = asyncio.run(collect())
    assert all(chunk.startswith("data: ") and chunk.endswith("\n\n") for chunk in chunks)
    decoded = [json.loads(chunk[len("data: "):]) for chunk in chunks]
    assert decoded[0]["type"] == "RUN_STARTED"
    assert decoded[-1]["type"] == "RUN_FINISHED"


# ---------------------------------------------------------------- the runner


def test_the_runner_is_local_unless_named(monkeypatch):
    monkeypatch.delenv("RLM_RUNNER", raising=False)
    assert isinstance(runner_from_env(), LocalRunner)
    monkeypatch.setenv("RLM_RUNNER", "local")
    assert isinstance(runner_from_env(), LocalRunner)
    assert LocalRunner().router is None


def test_the_kubernetes_runner_is_imported_only_when_named(monkeypatch):
    import app.main  # noqa: F401

    assert "app.runner_k8s" not in sys.modules
    monkeypatch.setenv("RLM_RUNNER", "kubernetes")
    with pytest.raises(ModuleNotFoundError, match="app.runner_k8s"):
        runner_from_env()


def test_any_other_runner_is_refused(monkeypatch):
    monkeypatch.setenv("RLM_RUNNER", "docker")
    with pytest.raises(ValueError):
        runner_from_env()


def test_the_command_books_phase_8_only_when_the_server_is_told(monkeypatch, tmp_path):
    runner = LocalRunner(["prefix"])
    room, run_dir = tmp_path / "room", tmp_path / "run"
    plain = ["prefix", "run", str(room), "--out", str(run_dir), "--yes"]

    monkeypatch.delenv("RLM_PHASE", raising=False)
    assert runner.argv(room, run_dir) == plain
    monkeypatch.setenv("RLM_PHASE", "7")
    assert runner.argv(room, run_dir) == plain
    monkeypatch.setenv("RLM_PHASE", "8")
    assert runner.argv(room, run_dir) == [*plain, "--phase", "8"]


def test_the_default_command_is_the_package_module():
    assert LocalRunner().argv(Path("r"), Path("o"))[:3] == [sys.executable, "-m", "rlm.cli"]


def test_the_key_reaches_the_child_alone(tmp_path):
    seen = tmp_path / "seen.txt"
    probe = (
        "import os, pathlib, sys; "
        f"pathlib.Path({str(seen)!r}).write_text(os.environ['OPENROUTER_API_KEY'] == {GOOD_KEY!r} "
        "and str(os.environ.get('PYTHONIOENCODING')))"
    )
    runner = LocalRunner([sys.executable, "-c", probe])
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    runner.start("k1", tmp_path / "room", run_dir, GOOD_KEY)
    runner.processes["k1"].wait(timeout=60)

    assert seen.read_text() == "utf-8"
    assert runner.status("k1") == "exited"
    assert GOOD_KEY not in os.environ.values()
    assert (run_dir / "run.log").exists()
    assert files_holding(tmp_path / "run", GOOD_KEY) == []


def test_a_second_start_while_running_is_refused_and_cancel_stops_it(tmp_path):
    runner = LocalRunner([sys.executable, "-c", "import time; time.sleep(60)"])
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    assert runner.status("s1") == "none"
    runner.start("s1", tmp_path / "room", run_dir, GOOD_KEY)
    assert runner.status("s1") == "running"
    with pytest.raises(RuntimeError):
        runner.start("s1", tmp_path / "room", run_dir, GOOD_KEY)
    runner.cancel("s1")
    assert runner.status("s1") == "exited"


# ---------------------------------------------------------------- the web page


def test_the_web_folder_is_served_at_the_root(tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<h1>diligence-reader</h1>", encoding="utf-8")
    app = create_app(runner=LocalRunner(), runs_root=tmp_path / "runs", web_dir=web)

    with TestClient(app) as client:
        assert "diligence-reader" in client.get("/").text
        assert client.get("/runs/nosuchrun").status_code == 404


def test_without_a_web_folder_the_root_is_not_found_and_the_api_answers(api, tmp_path):
    assert api.get("/").status_code == 404
    assert upload(api, room_files(tmp_path)).status_code == 201


def test_the_module_exposes_the_app():
    import app.main

    assert isinstance(app.main.app, FastAPI)


# ---------------------------------------------------------------- the live server


API_SAMPLES = ["northwind", "northstar-dental"]
LIVE_BAD_KEY = "sk-or-v1-bad-" + "0" * 64
LIVE = pytest.mark.skipif(
    os.environ.get("RLM_API_LIVE") != "1", reason="the live server run spends money; RLM_API_LIVE=1"
)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def sample_room_files(sample: str) -> list[tuple[str, bytes]]:
    """A sample's room as path and bytes: its key's documents, its brief and its key."""
    source = ROOT / "samples" / sample
    relatives = [*json.loads((source / "key.json").read_text(encoding="utf-8"))["documents"].values()]
    relatives += ["brief.md", "key.json"]
    return [(relative, (source / relative).read_bytes()) for relative in relatives]


def live_upload(sample: str) -> list:
    """northwind as one zip, northstar-dental as separate files under a top folder."""
    files = sample_room_files(sample)
    if sample == "northwind":
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for relative, data in files:
                archive.writestr(f"{sample}/{relative}", data)
        return [("files", (f"{sample}.zip", buffer.getvalue(), "application/zip"))]
    return [("files", (f"{sample}/{relative}", data, "text/plain")) for relative, data in files]


def live_events(client: httpx.Client, run_id: str, path: Path) -> list[dict]:
    """Reads the event stream to its end and saves it to path, one decoded event per line."""
    found = []
    with client.stream("GET", f"/runs/{run_id}/events", timeout=None) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith("data: "):
                found.append(json.loads(line[len("data: "):]))
    path.write_text("".join(json.dumps(event) + "\n" for event in found), encoding="utf-8")
    return found


@LIVE
@pytest.mark.parametrize("api_sample", API_SAMPLES)
def test_a_live_server_runs_the_room(api_sample):
    key = os.environ["OPENROUTER_API_KEY"]
    runs = ROOT / "runs"
    run_id = f"{api_sample}-api"
    folder = runs / run_id
    if folder.exists():
        shutil.rmtree(folder)
    runs.mkdir(exist_ok=True)
    port = free_port()
    env = {
        **os.environ,
        "RLM_PHASE": "8",
        "RLM_RUNS": str(runs),
        "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT)]),
        "PYTHONIOENCODING": "utf-8",
    }
    env.pop("OPENROUTER_API_KEY", None)
    env.pop("RLM_RUNNER", None)
    log = (runs / f"{run_id}.server.log").open("wb")
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=120) as client:
            deadline = time.monotonic() + 60
            while True:
                try:
                    client.get("/runs/none-such")
                    break
                except httpx.TransportError:
                    assert server.poll() is None, "the server stopped"
                    assert time.monotonic() < deadline, "the server did not answer"
                    time.sleep(0.5)

            first_key = LIVE_BAD_KEY if api_sample == "northstar-dental" else key
            response = client.post(
                "/runs",
                files=live_upload(api_sample),
                data={"name": run_id},
                headers={"X-OpenRouter-Key": first_key},
            )
            assert response.status_code == 201, response.text
            assert client.get(f"/runs/{run_id}/estimate").status_code == 200
            assert client.post(f"/runs/{run_id}/confirm").status_code == 202

            if api_sample == "northstar-dental":
                first = live_events(client, run_id, folder / "events-1.jsonl")
                assert first[-1]["type"] == "RUN_ERROR"
                assert first[-1]["code"] == "key-refused"
                retried = client.post(f"/runs/{run_id}/retry", headers={"X-OpenRouter-Key": key})
                assert retried.status_code == 202

            found = live_events(client, run_id, folder / "events.jsonl")
            assert found[-1]["type"] == "RUN_FINISHED", found[-1]

            downloads = folder / "downloads"
            downloads.mkdir(exist_ok=True)
            for fmt in EXPORTS:
                response = client.get(f"/runs/{run_id}/export/{fmt}")
                assert response.status_code == 200, fmt
                name = f"{run_id}-evidence.csv" if fmt == "csv" else f"{run_id}-report.{fmt}"
                (downloads / name).write_bytes(response.content)
    finally:
        server.terminate()
        server.wait(timeout=30)
        log.close()


@pytest.fixture(params=API_SAMPLES)
def api_run(request):
    path = ROOT / "runs" / f"{request.param}-api"
    if not (path / "events.jsonl").exists():
        pytest.skip(f"no API run for {request.param}")
    return request.param, path


def saved_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_the_api_run_streams_every_stage(api_run):
    _, path = api_run
    found = saved_events(path / "events.jsonl")

    assert found[0]["type"] == "RUN_STARTED"
    assert found[-1]["type"] == "RUN_FINISHED"
    assert steps(found) == EVERY_STEP
    assert noted_and_paid(found)


def test_the_api_run_recalls_every_planted_fact(api_run):
    sample, path = api_run
    grade = json.loads((path / "grade.json").read_text(encoding="utf-8"))
    assert grade["missed"] == KNOWN_MISSES.get(sample, [])
    if not grade["missed"]:
        assert grade["recall"] == 100.0


def test_the_api_run_is_done_and_every_export_downloaded(api_run):
    sample, path = api_run
    assert run_json(path)["status"] == "done"
    for fmt in EXPORTS:
        name = f"{sample}-api-evidence.csv" if fmt == "csv" else f"{sample}-api-report.{fmt}"
        download = path / "downloads" / name
        assert download.exists() and download.stat().st_size > 0, name


def test_the_bad_key_stopped_the_first_attempt(api_run):
    sample, path = api_run
    if sample != "northstar-dental":
        pytest.skip("only northstar-dental is started on a bad key")
    first = saved_events(path / "events-1.jsonl")
    assert first[-1]["type"] == "RUN_ERROR"
    assert first[-1]["code"] == "key-refused"
    assert run_json(path)["status"] == "done"


def test_the_key_is_in_no_file_of_the_api_run_and_not_in_the_server_log(api_run):
    sample, path = api_run
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("no OPENROUTER_API_KEY to look for")
    assert files_holding(path, key) == []
    server_log = path.parent / f"{sample}-api.server.log"
    assert key.encode("utf-8") not in server_log.read_bytes()


def readout(terminalreporter):
    for sample in API_SAMPLES:
        path = ROOT / "runs" / f"{sample}-api" / "run.json"
        if not path.exists():
            continue
        found = json.loads(path.read_text(encoding="utf-8"))
        terminalreporter.write_line(
            f"phase 8 {sample} API: status {found['status']}, recall {found.get('recall')}, "
            f"estimate ${(found.get('estimate') or 0.0):.4f}, spent ${found['dollars']:.4f}"
        )
