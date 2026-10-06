"""Phase 8 slice 02: `diligence-reader run`, one command from a room to a verified report.

The tests at $0 run the command on a temporary copy of sample 3's room, with a fake transport
injected into the gateway, so nothing leaves the machine and nothing is booked to the real
LEDGER.md. The fake answers a note call with a note quoting the document's first line and a
write call with FAKE_REPORT, whose sentences cite the room's own first line and verify, so a
fake run is done unless a test makes it stop. BAD_REPORT cites a line the room does not have.

The end-to-end tests read the run folders the paid runs leave under runs/<sample>-cli and skip
when a folder is missing, the way the export tests skip without a pinned report.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import httpx
import pytest

import rlm
from conftest import ROOT
from rlm import cli, ingest, notes, write
from rlm.gateway import Gateway, Ledger
from rlm.key import load_key, room_documents

ROOM = "northstar-dental"
NOTES_MODEL = notes.DEFAULT_MODEL
WRITE_MODEL = write.DEFAULT_MODEL
PACKAGE_LEDGER = Path(rlm.__file__).resolve().parents[2] / "LEDGER.md"
DEFAULT_BRIEF = Path(rlm.__file__).resolve().parent / "brief.md"

LATER_THAN_INGEST = (
    "notes-summary.json",
    "map.json",
    "dossier.md",
    "digest.md",
    "report.md",
    "verify.json",
    "report.docx",
    "report.pdf",
    "evidence.csv",
)

FAKE_REPORT = """## Executive summary

The room holds one matter [cim.md | cim.md#l1].

## Key findings, ranked by materiality

Revenue is restated [cim.md | cim.md#l1].

## Most material issue, quantification

Calculation: none [cim.md | cim.md#l1].

## Lesser, lower-priority issues

None stated [cim.md | cim.md#l1].

## Confidence and open items

Open [cim.md | cim.md#l1].
"""


# A report citing an anchor no document of the room carries, so it fails the verifier twice.
BAD_REPORT = FAKE_REPORT.replace("cim.md#l1]", "cim.md#l99999]")


def reply(content, tokens_in: int = 1000, tokens_out: int = 200) -> dict:
    return {
        "id": "fake",
        "provider": "fake",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out},
    }


def fake_note(request_body: dict) -> str:
    """A note quoting the first line of the document the request carries."""
    document = request_body["messages"][1]["content"][len(notes.USER_PREFIX):]
    first = next(line for line in document.splitlines() if line.strip())
    return json.dumps(
        {
            "what": "a document of the room",
            "flags": [{"flag": "a line", "quote": first, "consequence": "none", "about": []}],
            "figures": [],
            "cross_references": [],
            "concealed": [],
        }
    )


class RoomTransport(httpx.MockTransport):
    """Answers note calls with a fake note and write calls with FAKE_REPORT.

    status answers every chat completion with that HTTP status instead; null answers every one
    with a null content; write_status answers only the write calls with that status; report is
    the text every write call is answered with. Every
    request is recorded with its model, and when events is given each request appends
    ("request", model) to it, so a test can read what reached the transport against what was
    printed.
    """

    def __init__(self, status=None, null=False, write_status=None, events=None, report=FAKE_REPORT):
        self.requests: list[dict] = []
        self.report = report
        self.status = status
        self.null = null
        self.write_status = write_status
        self.events = events
        self._lock = threading.Lock()
        super().__init__(self._handle)

    def models(self) -> list[str]:
        return [body["model"] for body in self.requests]

    def _handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        with self._lock:
            self.requests.append(body)
            if self.events is not None:
                self.events.append(("request", body["model"]))
        if self.status is not None:
            return httpx.Response(self.status, json={"error": {"message": "refused"}})
        if self.null:
            return httpx.Response(200, json=reply(None))
        if body["model"] == WRITE_MODEL:
            if self.write_status is not None:
                return httpx.Response(self.write_status, json={"error": {"message": "refused"}})
            return httpx.Response(200, json=reply(self.report, 20000, 5000))
        return httpx.Response(200, json=reply(fake_note(body)))


def gateway_for(transport: httpx.MockTransport) -> Gateway:
    return Gateway(api_key="test-key", transport=transport, rate_limit_waits=())


def copy_room(tmp_path: Path, brief: bool = True, key: bool = True) -> Path:
    """Copies sample 3's documents into tmp_path/room, with its brief and its key when asked."""
    source = ROOT / "samples" / ROOM
    room = tmp_path / "room"
    for relative in load_key(source).documents.values():
        target = room / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
    if brief:
        shutil.copyfile(source / "brief.md", room / "brief.md")
    if key:
        shutil.copyfile(source / "key.json", room / "key.json")
    return room


def write_ledger(path: Path) -> Ledger:
    path.write_text(
        "| date | sample | phase | model | tokens in | tokens out | dollars | balance |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 2026-09-05 | | | | 0 | 0 | 0.0000 | 50.0000 |\n",
        encoding="utf-8",
    )
    return Ledger(path)


def run_json(run_dir: Path) -> dict:
    return json.loads((run_dir / "run.json").read_text(encoding="utf-8"))


def run(room: Path, run_dir: Path, transport, *extra, ledger=None) -> int:
    argv = ["run", str(room), "--out", str(run_dir), "--yes", *extra]
    return cli.main(argv, gateway=gateway_for(transport), ledger=ledger)


# ---------------------------------------------------------------- version


def test_version_is_read_from_the_package_metadata():
    assert rlm.__version__ == "0.8.0"


def test_the_version_reads_from_a_source_checkout_with_nothing_installed():
    probe = "\n".join(
        [
            "import importlib.metadata as m",
            "def missing(name):",
            "    raise m.PackageNotFoundError(name)",
            "m.version = missing",
            "import rlm",
            "print(rlm.__version__)",
        ]
    )
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    done = subprocess.run(
        [sys.executable, "-c", probe], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "0.8.0"


def test_version_flag_prints_the_version(capsys):
    with pytest.raises(SystemExit) as raised:
        cli.main(["--version"])
    assert raised.value.code == 0
    assert "0.8.0" in capsys.readouterr().out


# ---------------------------------------------------------------- error codes


@pytest.mark.parametrize(
    "status, code",
    [(401, "key-refused"), (403, "key-refused"), (402, "no-credits"), (429, "rate-limited")],
)
def test_a_refused_call_stops_after_ingest_with_its_code(tmp_path, status, code):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    transport = RoomTransport(status=status)

    assert run(room, run_dir, transport) != 0

    state = run_json(run_dir)
    assert state["status"] == "failed"
    assert state["code"] == code
    assert state["stage"] == "notes"
    assert (run_dir / "sections.jsonl").exists()
    assert (run_dir / "index.jsonl").exists()
    for name in LATER_THAN_INGEST:
        assert not (run_dir / name).exists(), name
    assert not list((run_dir / "notes").glob("*.json")) if (run_dir / "notes").exists() else True


def test_a_null_content_on_every_call_gives_empty_reply(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"

    assert run(room, run_dir, RoomTransport(null=True)) != 0

    state = run_json(run_dir)
    assert state["status"] == "failed"
    assert state["code"] == "empty-reply"
    assert not (run_dir / "map.json").exists()


def test_a_null_write_reply_gives_empty_reply(tmp_path, monkeypatch):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"

    class NullWrite(RoomTransport):
        def _handle(self, request):
            body = json.loads(request.content)
            if body["model"] == WRITE_MODEL:
                self.requests.append(body)
                return httpx.Response(200, json=reply(None))
            return super()._handle(request)

    assert run(room, run_dir, NullWrite()) != 0

    state = run_json(run_dir)
    assert state["code"] == "empty-reply"
    assert state["stage"] == "write"


def test_a_report_that_fails_the_verifier_twice_gives_verify_failed(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    transport = RoomTransport(report=BAD_REPORT)

    assert run(room, run_dir, transport) != 0

    state = run_json(run_dir)
    assert state["status"] == "failed"
    assert state["code"] == "verify-failed"
    assert state["stage"] == "write"
    assert json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))["passes"] is False
    assert transport.models().count(WRITE_MODEL) == 2
    assert not (run_dir / "report.docx").exists()


def test_a_file_ingest_cannot_read_gives_unreadable_file(tmp_path):
    room = copy_room(tmp_path, key=False)
    (room / "broken.pdf").write_bytes(b"this is not a pdf")
    run_dir = tmp_path / "run"
    transport = RoomTransport()

    assert run(room, run_dir, transport) != 0

    state = run_json(run_dir)
    assert state["code"] == "unreadable-file"
    assert state["stage"] == "ingest"
    assert transport.requests == []


# ---------------------------------------------------------------- the estimate


def test_the_estimate_is_printed_before_the_first_request(tmp_path, monkeypatch):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    events: list[tuple[str, str]] = []

    class Recorder(io.StringIO):
        def write(self, text):
            if text.strip():
                events.append(("printed", text))
            return super().write(text)

    monkeypatch.setattr(sys, "stdout", Recorder())
    run(room, run_dir, RoomTransport(events=events))

    first_request = next(i for i, event in enumerate(events) if event[0] == "request")
    printed = [event[1] for event in events[:first_request] if event[0] == "printed"]
    assert any("estimate" in line and "$" in line and "tokens" in line for line in printed)
    assert run_json(run_dir)["estimate"] > 0


def test_answering_no_declines_and_sends_nothing(tmp_path, monkeypatch):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    transport = RoomTransport()
    asked: list[str] = []
    monkeypatch.setattr("builtins.input", lambda prompt="": asked.append(prompt) or "n")

    code = cli.main(["run", str(room), "--out", str(run_dir)], gateway=gateway_for(transport))

    assert code != 0
    assert asked, "the command did not ask"
    assert transport.requests == []
    state = run_json(run_dir)
    assert state["status"] == "failed"
    assert state["code"] == "declined"
    assert not (run_dir / "notes-summary.json").exists()


# ---------------------------------------------------------------- resume


def test_a_run_stopped_after_notes_resumes_without_noting_again(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    ledger = write_ledger(tmp_path / "LEDGER.md")

    assert run(room, run_dir, RoomTransport(write_status=401), "--phase", "8", ledger=ledger) != 0
    assert run_json(run_dir)["code"] == "key-refused"
    assert (run_dir / "notes-summary.json").exists()
    for name in ("map.json", "dossier.md", "digest.md"):
        (run_dir / name).unlink(missing_ok=True)
    rows_before = ledger.rows()
    assert [row["model"] for row in rows_before[1:]] == [NOTES_MODEL]
    spent_before = run_json(run_dir)["dollars"]
    sections_mtime = (run_dir / "sections.jsonl").stat().st_mtime_ns

    transport = RoomTransport()
    run(room, run_dir, transport, "--phase", "8", ledger=ledger)

    assert NOTES_MODEL not in transport.models()
    assert transport.models().count(WRITE_MODEL) == 1
    assert (run_dir / "sections.jsonl").stat().st_mtime_ns == sections_mtime
    new_rows = ledger.rows()[len(rows_before):]
    assert [(row["phase"], row["model"]) for row in new_rows] == [("8", WRITE_MODEL)]
    assert (run_dir / "map.json").exists()
    assert run_json(run_dir)["dollars"] > spent_before


# ---------------------------------------------------------------- the ledger


def test_without_phase_the_ledger_is_byte_identical(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    before = PACKAGE_LEDGER.read_bytes()

    run(room, run_dir, RoomTransport())

    assert PACKAGE_LEDGER.read_bytes() == before
    state = run_json(run_dir)
    assert state["dollars"] > 0
    assert state["documents_noted"] > 0


def test_with_phase_8_the_ledger_books_under_phase_8(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    ledger = write_ledger(tmp_path / "LEDGER.md")

    assert run(room, run_dir, RoomTransport(), "--phase", "8", ledger=ledger) == 0

    booked = ledger.rows()[1:]
    assert [(row["phase"], row["model"]) for row in booked] == [
        ("8", NOTES_MODEL),
        ("8", WRITE_MODEL),
    ]
    assert run_json(run_dir)["dollars"] == pytest.approx(sum(row["dollars"] for row in booked), abs=1e-3)


def test_a_keyed_room_is_graded_on_recall_alone(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"

    assert run(room, run_dir, RoomTransport()) == 0

    state = run_json(run_dir)
    assert state["status"] == "done"
    grade = json.loads((run_dir / "grade.json").read_text(encoding="utf-8"))
    assert grade["rubric"] == []
    assert grade["model"] == "none"
    assert state["recall"] == grade["recall"]
    for name in ("report.docx", "report.pdf", "evidence.csv"):
        assert (run_dir / name).exists(), name


# ---------------------------------------------------------------- the default brief


def test_a_room_without_a_brief_is_written_on_the_default_brief(tmp_path):
    room = copy_room(tmp_path, brief=False)
    run_dir = tmp_path / "run"
    transport = RoomTransport()

    run(room, run_dir, transport)

    brief = DEFAULT_BRIEF.read_text(encoding="utf-8")
    written = [body for body in transport.requests if body["model"] == WRITE_MODEL]
    assert written, "write was never called"
    assert brief.strip()[:400] in written[0]["messages"][0]["content"]


# ---------------------------------------------------------------- a room with no key


def test_a_room_with_no_key_lists_every_readable_file(tmp_path):
    keyed = room_documents(ROOT / "samples" / ROOM)
    assert keyed == load_key(ROOT / "samples" / ROOM).documents

    room = copy_room(tmp_path, key=False)
    (room / "notes.txt").write_text("A plain note.\n", encoding="utf-8")
    (room / "picture.png").write_bytes(b"\x89PNG")
    documents = room_documents(room)

    expected = sorted([*keyed.values(), "notes.txt"])
    assert list(documents.values()) == expected
    assert list(documents) == expected
    assert "brief.md" not in documents.values()

    coverage = ingest.ingest(room, tmp_path / "run")
    assert coverage.documents == len(expected)
    docs = {
        json.loads(line)["doc"]
        for line in (tmp_path / "run" / "sections.jsonl").read_text(encoding="utf-8").splitlines()
    }
    assert docs == set(expected)


def test_a_room_with_no_key_runs_to_the_end_and_is_not_graded(tmp_path):
    room = copy_room(tmp_path, key=False)
    run_dir = tmp_path / "run"

    assert run(room, run_dir, RoomTransport()) == 0

    state = run_json(run_dir)
    assert state["status"] == "done"
    assert state["code"] is None
    assert state["recall"] is None
    assert (run_dir / "report.docx").exists()
    assert not (run_dir / "grade.json").exists()


# ---------------------------------------------------------------- the gateway


def test_the_gateway_tries_a_rate_limited_call_again():
    answers = [httpx.Response(429, json={}), httpx.Response(200, json=reply("{}"))]
    gateway = Gateway(
        api_key="k", transport=httpx.MockTransport(lambda request: answers.pop(0)), rate_limit_waits=(0.0,)
    )
    assert gateway.complete(NOTES_MODEL, [{"role": "user", "content": "u"}], max_tokens=10).text == "{}"


# ---------------------------------------------------------------- the paid runs


@pytest.fixture
def cli_run(sample):
    path = ROOT / "runs" / f"{sample}-cli"
    if not (path / "run.json").exists():
        pytest.skip(f"no command line run for {sample}")
    return path


def test_the_command_line_run_is_done_and_paid(cli_run):
    state = run_json(cli_run)
    assert state["status"] == "done"
    assert state["code"] is None
    assert state["dollars"] > 0
    assert state["version"] == "0.8.0"
    for name in ("report.md", "report.docx", "report.pdf", "evidence.csv"):
        assert (cli_run / name).exists(), name


def test_the_command_line_run_passes_the_verifier(cli_run):
    assert json.loads((cli_run / "verify.json").read_text(encoding="utf-8"))["passes"] is True


# A fact a command line run misses for a reason outside phase 8, named so the test still fails
# when the miss changes. northwind's tidewater-subprocessor-gap: the fresh note quotes it, but
# the map links subprocessor_register.pdf.md to nothing on those notes, so it falls out of the
# matter set (11 documents against the pinned run's 12) and the report never carries it.
KNOWN_MISSES = {"northwind": ["tidewater-subprocessor-gap"]}


def test_the_command_line_run_recalls_every_planted_fact(cli_run, sample):
    grade = json.loads((cli_run / "grade.json").read_text(encoding="utf-8"))
    assert grade["missed"] == KNOWN_MISSES.get(sample, [])
    if not grade["missed"]:
        assert grade["recall"] == 100.0
    assert grade["rubric"] == []


def test_the_estimate_is_within_a_factor_of_two_of_the_dollars_spent(cli_run):
    state = run_json(cli_run)
    assert 0.5 <= state["estimate"] / state["dollars"] <= 2.0


def readout(terminalreporter):
    for sample in ("atlas", "northwind", "northstar-dental"):
        path = ROOT / "runs" / f"{sample}-cli" / "run.json"
        if not path.exists():
            continue
        state = json.loads(path.read_text(encoding="utf-8"))
        terminalreporter.write_line(
            f"phase 8 {sample} command line: status {state['status']}, recall {state.get('recall')}, "
            f"estimate ${state['estimate']:.4f}, spent ${state['dollars']:.4f}"
        )


def test_a_run_folder_with_summaries_and_no_run_json_counts_only_this_runs_calls(tmp_path):
    """Notes copied into a folder were paid for by an earlier run; this run did not spend them."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "notes-summary.json").write_text(json.dumps({"noted": 3, "dollars": 5.9}), encoding="utf-8")
    (run_dir / "write-summary.json").write_text(json.dumps({"dollars": 1.25}), encoding="utf-8")
    meter = cli.Meter()
    meter.add(NOTES_MODEL, 0, 0, 0.0)

    state = cli.RunState(run_dir, meter)
    state.write("done")

    assert run_json(run_dir)["dollars"] == 0.0
