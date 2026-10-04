"""The local API: upload a room, read its estimate, start the run, follow it, fetch the report.

`uvicorn app.main:app --host 127.0.0.1 --port 8000` serves it. A run's folder is
<runs root>/<id> and the uploaded room is <runs root>/<id>/<id>, a folder named by the run id so
the stages name the sample after the run; the runs root is RLM_RUNS, runs under the current
folder by default. The key comes in the X-OpenRouter-Key header and is held
in this process's memory by run id until the runner starts the command with it; it is never
written to a file, a log or a response. The web page in web/ is served at / when the folder is
there; it reads the version and whether to check for a newer release from /api/config, and a
cited document's sections from /runs/<id>/documents/<doc>.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

from fastapi import FastAPI, File, Form, Header, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import events
from app.runner import Runner, runner_from_env
from rlm import __version__, cli
from rlm import ingest as ingest_stage
from rlm import notes as notes_stage
from rlm import write as write_stage
from rlm.gateway import Meter

# A name a run may be given: lower case letters, digits and dashes, 64 at most.
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

# Each export: the file in the run folder, its media type, and the download's name after the id.
EXPORTS = {
    "md": ("report.md", "text/markdown", "report.md"),
    "docx": (
        "report.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "report.docx",
    ),
    "pdf": ("report.pdf", "application/pdf", "report.pdf"),
    "csv": ("evidence.csv", "text/csv", "evidence.csv"),
}

WEB_DIR = Path(__file__).resolve().parents[1] / "web"


class Refused(Exception):
    """A request the API answers with an error status and a code, and a message that names no key."""

    def __init__(self, status: int, code: str, message: str = ""):
        super().__init__(message or code)
        self.status = status
        self.code = code
        self.message = message or code


def room_of(run_dir: Path) -> Path:
    """A run's room: a folder inside the run folder named by the run id."""
    return run_dir / run_dir.name


def room_path(name: str) -> PurePosixPath:
    """An uploaded file's path inside the room, refusing one that is absolute or climbs out."""
    windows = PureWindowsPath(name)
    parts = [part for part in re.split(r"[\\/]", name) if part not in ("", ".")]
    if (
        not parts
        or name.startswith(("/", "\\"))
        or windows.drive
        or windows.is_absolute()
        or ".." in parts
    ):
        raise Refused(400, "bad-path", f"a file path leaves the room: {name}")
    return PurePosixPath(*parts)


def room_entries(uploads: list[tuple[str, bytes]]) -> list[tuple[PurePosixPath, bytes]]:
    """The room's files as path and bytes: one zip opened, every path checked, a shared top folder dropped."""
    if len(uploads) == 1 and uploads[0][0].lower().endswith(".zip"):
        try:
            archive = zipfile.ZipFile(io.BytesIO(uploads[0][1]))
        except zipfile.BadZipFile as exc:
            raise Refused(400, "bad-zip", "the upload is not a zip that opens") from exc
        with archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            paths = [room_path(info.filename) for info in members]
            entries = [(path, archive.read(info)) for path, info in zip(paths, members)]
    else:
        entries = [(room_path(name), data) for name, data in uploads]
    if not entries:
        raise Refused(400, "empty-room", "the upload holds no file")
    tops = {path.parts[0] for path, _ in entries}
    if len(tops) == 1 and all(len(path.parts) > 1 for path, _ in entries):
        entries = [(PurePosixPath(*path.parts[1:]), data) for path, data in entries]
    return entries


def create_app(
    runner: Runner | None = None, runs_root: Path | None = None, web_dir: Path | None = None
) -> FastAPI:
    """The API on a runner and a runs root, with the web page mounted when its folder is there."""
    runner = runner if runner is not None else runner_from_env()
    runs_root = Path(runs_root if runs_root is not None else os.environ.get("RLM_RUNS", "runs"))
    web_dir = Path(web_dir) if web_dir is not None else WEB_DIR

    app = FastAPI(title="diligence-reader")
    app.state.runner = runner
    app.state.keys = {}
    keys: dict[str, str] = app.state.keys

    @app.exception_handler(Refused)
    async def refused(request, exc: Refused):
        return JSONResponse({"code": exc.code, "message": exc.message}, status_code=exc.status)

    def folder(run_id: str) -> Path:
        """The run's folder, refusing an id that names none."""
        if not NAME.match(run_id) or not (runs_root / run_id).is_dir():
            raise Refused(404, "no-run", f"no run {run_id}")
        return runs_root / run_id

    def given(key: str | None) -> str | None:
        return key.strip() if key and key.strip() else None

    def launch(run_id: str, key: str | None) -> JSONResponse:
        """Starts the runner on the run with the key given, else the key held."""
        run_dir = folder(run_id)
        key = given(key) or keys.get(run_id)
        if not key:
            raise Refused(400, "key-missing", "no OpenRouter key is held for this run")
        keys[run_id] = key
        if runner.status(run_id) == "running":
            raise Refused(409, "running", "the run is already running")
        events.stopped_mark(run_dir).unlink(missing_ok=True)
        runner.start(run_id, room_of(run_dir), run_dir, key)
        return JSONResponse({"id": run_id}, status_code=202)

    @app.post("/runs", status_code=201)
    async def create_run(
        files: list[UploadFile] = File(...),
        name: str | None = Form(None),
        x_openrouter_key: str | None = Header(None),
    ):
        key = given(x_openrouter_key)
        if not key:
            raise Refused(400, "key-missing", "send the OpenRouter key in X-OpenRouter-Key")
        if name is not None and not NAME.match(name):
            raise Refused(400, "bad-name", "a name is lower case letters, digits and dashes")
        run_id = name or uuid.uuid4().hex[:12]
        if (runs_root / run_id).exists():
            raise Refused(409, "name-taken", f"a run named {run_id} exists")
        uploads = [(upload.filename or "", await upload.read()) for upload in files]
        entries = room_entries(uploads)
        room = room_of(runs_root / run_id)
        try:
            for path, data in entries:
                target = room / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        except OSError:
            shutil.rmtree(runs_root / run_id, ignore_errors=True)
            raise
        keys[run_id] = key
        return {"id": run_id}

    def summary(run_id: str, run_dir: Path) -> dict:
        """One run for the list: its id, when it was created, its status and its dollars.

        The status says what the event stream would say: running while the runner has the
        process; done when run.json says so; stopped when the stop mark is there; uploaded when
        run.json is not (the run was never confirmed); else failed, which includes a run.json
        that says running with its process gone. Created is the modification time of the run's
        room folder: the upload writes it once and no stage touches it again, where the run
        folder's own times move with every stage and a creation time is not kept on Linux.
        """
        try:
            state = cli.read_json(run_dir / cli.RUN_FILE)
        except (ValueError, OSError):
            state = None
        if runner.status(run_id) == "running":
            status = "running"
        elif state and state.get("status") == "done":
            status = "done"
        elif events.stopped_mark(run_dir).exists():
            status = "stopped"
        elif state is None:
            status = "uploaded"
        else:
            status = "failed"
        room = room_of(run_dir)
        made = (room if room.is_dir() else run_dir).stat().st_mtime
        return {
            "id": run_id,
            "created": datetime.fromtimestamp(made, timezone.utc).isoformat(timespec="seconds"),
            "status": status,
            "dollars": float((state or {}).get("dollars") or 0),
            "_made": made,
        }

    @app.get("/runs")
    async def list_runs():
        """Every run folder named by the run rule, newest first; no key and no document text."""
        found = []
        if runs_root.is_dir():
            for path in runs_root.iterdir():
                if path.is_dir() and NAME.match(path.name):
                    found.append(summary(path.name, path))
        found.sort(key=lambda row: (row["_made"], row["id"]), reverse=True)
        return {"runs": [{k: v for k, v in row.items() if k != "_made"} for row in found]}

    @app.get("/runs/{run_id}")
    async def read_run(run_id: str):
        run_dir = folder(run_id)
        try:
            state = cli.read_json(run_dir / cli.RUN_FILE)
        except ValueError:
            state = None
        return {"state": state, "process": runner.status(run_id)}

    @app.get("/runs/{run_id}/estimate")
    async def read_estimate(run_id: str):
        run_dir = folder(run_id)
        room = room_of(run_dir)
        if not cli.done("ingest", run_dir):
            try:
                await run_in_threadpool(ingest_stage.ingest, room, run_dir)
            except ingest_stage.UnreadableFile as exc:
                cli.RunState(run_dir, Meter()).write("failed", "unreadable-file")
                raise Refused(422, "unreadable-file", str(exc)) from exc
        found = await run_in_threadpool(
            cli.estimate,
            room,
            run_dir,
            not cli.done("notes", run_dir),
            not cli.done("write", run_dir),
        )
        return {
            "tokens": found.tokens,
            "notes_tokens": found.notes_tokens,
            "write_tokens": found.write_tokens,
            "dollars": found.dollars,
            "notes_model": notes_stage.DEFAULT_MODEL,
            "write_model": write_stage.DEFAULT_MODEL,
        }

    @app.post("/runs/{run_id}/confirm")
    async def confirm(run_id: str, x_openrouter_key: str | None = Header(None)):
        return launch(run_id, x_openrouter_key)

    @app.post("/runs/{run_id}/retry")
    async def retry(run_id: str, x_openrouter_key: str | None = Header(None)):
        return launch(run_id, x_openrouter_key)

    @app.post("/runs/{run_id}/stop")
    async def stop(run_id: str):
        run_dir = folder(run_id)
        if runner.status(run_id) != "running":
            raise Refused(409, "not-running", "the run is not running")
        # The mark goes down first, so the stream never reads the exit as a crash.
        events.stopped_mark(run_dir).write_text("stopped", encoding="utf-8")
        await run_in_threadpool(runner.cancel, run_id)
        return {"id": run_id}

    @app.get("/runs/{run_id}/events")
    async def read_events(run_id: str):
        run_dir = folder(run_id)
        return StreamingResponse(
            events.stream(run_id, run_dir, runner), media_type="text/event-stream"
        )

    @app.get("/runs/{run_id}/report")
    async def read_report(run_id: str):
        path = folder(run_id) / "report.md"
        if not path.exists():
            raise Refused(404, "no-report", "the run has no report yet")
        return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")

    @app.get("/runs/{run_id}/sections/{anchor:path}")
    async def read_section(run_id: str, anchor: str):
        path = folder(run_id) / "sections.jsonl"
        if path.exists():
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    if row["anchor"] == anchor:
                        return {field: row.get(field) for field in ("anchor", "doc", "heading", "text")}
        raise Refused(404, "no-section", f"no section {anchor}")

    @app.get("/runs/{run_id}/documents/{doc:path}")
    async def read_document(run_id: str, doc: str):
        """Every section of one document, in order, read from sections.jsonl and never from the room."""
        path = folder(run_id) / "sections.jsonl"
        found = []
        if path.exists():
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    if row["doc"] == doc:
                        found.append({field: row.get(field) for field in ("anchor", "heading", "text")})
        if not found:
            raise Refused(404, "no-document", f"no document {doc}")
        return {"doc": doc, "sections": found}

    @app.get("/api/config")
    async def read_config():
        """The version, and whether the page may ask GitHub for a newer release: RLM_UPDATE_CHECK=off says no."""
        check = os.environ.get("RLM_UPDATE_CHECK", "on").strip().lower() != "off"
        return {"version": __version__, "update_check": check}

    @app.get("/runs/{run_id}/export/{fmt}")
    async def export(run_id: str, fmt: str):
        run_dir = folder(run_id)
        if fmt not in EXPORTS:
            raise Refused(400, "bad-format", "an export is md, docx, pdf or csv")
        name, media, download = EXPORTS[fmt]
        path = run_dir / name
        if not path.exists():
            raise Refused(404, "no-export", f"the run has no {name} yet")
        return FileResponse(path, media_type=media, filename=f"{run_id}-{download}")

    if runner.router is not None:
        app.include_router(runner.router)
    if web_dir.is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app


app = create_app()
