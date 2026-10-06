"""A run's progress as AG-UI events, derived from its run.json as that file changes.

The command writes run.json at every stage boundary. A Deriver is fed each reading of it, with
the count of notes written so far and the runner's status, and gives the events that reading
adds: RUN_STARTED and a STATE_SNAPSHOT first, a STEP_STARTED and a STEP_FINISHED per stage in
the order the stages run, a STATE_DELTA whenever the documents noted, the dollars, the stage or
the estimate move, and one RUN_FINISHED or RUN_ERROR at the end. stream() polls the run folder
and sends those events as server-sent events.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator

from ag_ui.core import (
    BaseEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateDeltaEvent,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepStartedEvent,
)
from ag_ui.encoder import EventEncoder

from rlm.cli import RUN_FILE, STAGES

# The one-line fix shown beside each code a run stops on.
FIXES = {
    "key-refused": "The model provider refused the key. Check the OpenRouter or Anthropic key, or the AWS credentials, and retry.",
    "no-credits": "The account is out of credits. Add credits with the provider that refused, then retry.",
    "rate-limited": "The provider is limiting requests. Wait a few minutes, then retry.",
    "empty-reply": "The model sent back nothing. Retry; the stages already done are kept.",
    "unreadable-file": "A file in the room could not be read. Remove or replace it and upload again.",
    "verify-failed": "The report did not pass its checks. Retry to write it again.",
    "unknown-model": "A model id is not one this tool can run. Pick the models again and retry.",
    "bad-settings": "The model settings cannot be run. Change them and retry.",
    "declined": "The estimate was not accepted, so nothing was sent.",
    "stopped": "You stopped the run. Retry resumes from the stage that stopped.",
    "unexpected": "The run stopped for an unexpected reason. Read run.log in the run folder, then retry.",
}

# The mark a stop leaves in the run folder; a retry or a confirm removes it.
STOPPED_FILE = "stopped"

# The values of the shared state, in the order a delta lists them.
FIELDS = ("documents_noted", "dollars", "stage", "estimate")


class Deriver:
    """Turns successive readings of one run into the AG-UI events each reading adds."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.begun = False
        self.ended = False
        self.started: set[str] = set()
        self.finished: set[str] = set()
        self.values = {"stage": None, "documents_noted": 0, "dollars": 0.0, "estimate": None}

    def feed(
        self, state: dict | None, live_noted: int, process: str, stopped: bool = False
    ) -> list[BaseEvent]:
        """The events since the last feed, from run.json, the notes written and the runner status.

        stopped says the run folder holds the mark a stop leaves: a run that ends without
        finishing then ends with the code `stopped`, not `unexpected`.

        A run.json is final only once the process has stopped: while a retry's child runs, the
        file the attempt before it left is still there.
        """
        if self.ended or (state is None and process != "running" and not stopped):
            return []
        found: list[BaseEvent] = []
        if not self.begun:
            self.begun = True
            found.append(RunStartedEvent(thread_id=self.run_id, run_id=self.run_id))
            found.append(StateSnapshotEvent(snapshot=dict(self.values)))
        if state is None:
            if stopped and process != "running":
                found.append(RunErrorEvent(message=FIXES["stopped"], code="stopped"))
                self.ended = True
            return found

        stage = state.get("stage")
        if stage in STAGES:
            found += self.reach(STAGES.index(stage))
        found += self.delta(state, live_noted)

        if process == "running":
            return found
        status = state.get("status")
        if status == "done":
            found += self.reach(len(STAGES))
            found.append(
                RunFinishedEvent(
                    thread_id=self.run_id,
                    run_id=self.run_id,
                    result={"recall": state.get("recall"), "dollars": state.get("dollars")},
                )
            )
        else:
            code = state.get("code") if status == "failed" else "unexpected"
            if stopped:
                code = "stopped"
            code = code if code in FIXES else "unexpected"
            found.append(RunErrorEvent(message=FIXES[code], code=code))
        self.ended = True
        return found

    def reach(self, position: int) -> list[BaseEvent]:
        """Finishes every stage before position, starting any not yet started, and starts the one at it."""
        found: list[BaseEvent] = []
        for stage in STAGES[:position]:
            found += self.start(stage)
            if stage not in self.finished:
                self.finished.add(stage)
                found.append(StepFinishedEvent(step_name=stage))
        if position < len(STAGES):
            found += self.start(STAGES[position])
        return found

    def start(self, stage: str) -> list[BaseEvent]:
        """A STEP_STARTED for a stage not yet started, else nothing."""
        if stage in self.started:
            return []
        self.started.add(stage)
        return [StepStartedEvent(step_name=stage)]

    def delta(self, state: dict, live_noted: int) -> list[BaseEvent]:
        """A STATE_DELTA replacing every value that moved since the last one, or nothing."""
        now = {
            "documents_noted": max(int(state.get("documents_noted") or 0), live_noted),
            "dollars": state.get("dollars") or 0.0,
            "stage": state.get("stage"),
            "estimate": state.get("estimate"),
        }
        ops = [
            {"op": "replace", "path": f"/{field}", "value": now[field]}
            for field in FIELDS
            if now[field] != self.values[field]
        ]
        self.values = now
        return [StateDeltaEvent(delta=ops)] if ops else []


def read_state(run_dir: Path) -> dict | None:
    """run.json, or None when it is not there; raises ValueError on a file caught mid-write."""
    path = run_dir / RUN_FILE
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def stopped_mark(run_dir: Path) -> Path:
    """The file a stop leaves in the run folder, so the stream can tell a stop from a crash."""
    return run_dir / STOPPED_FILE


def notes_written(run_dir: Path) -> int:
    """How many documents the notes pass has written a note for so far."""
    folder = run_dir / "notes"
    return sum(1 for _ in folder.glob("*.json")) if folder.is_dir() else 0


async def stream(run_id: str, run_dir: Path, runner, poll: float = 0.5) -> AsyncIterator[str]:
    """Server-sent events for one run, read off its folder every poll seconds, to its end."""
    encoder = EventEncoder()
    deriver = Deriver(run_id)
    while True:
        # The status is read before the file, so a stopped process's run.json is its last.
        process = runner.status(run_id)
        try:
            state = read_state(run_dir)
        except (ValueError, OSError):
            await asyncio.sleep(poll)
            continue
        for event in deriver.feed(state, notes_written(run_dir), process, stopped_mark(run_dir).exists()):
            yield encoder.encode(event)
        if deriver.ended:
            return
        await asyncio.sleep(poll)
