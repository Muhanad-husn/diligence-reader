"""Where a run's command runs: the Runner interface and LocalRunner, a child process on this machine.

A runner starts `diligence-reader run` on a room into its run folder, says whether it is still
running, and stops it. The key reaches the command through the child's environment alone: it is
never set in this process's environment, never written to a file and never logged.

RLM_RUNNER chooses the runner: unset or `local` gives LocalRunner, `kubernetes` gives the
KubernetesRunner of app/runner_k8s.py, imported only when named.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Protocol

from fastapi import APIRouter

# The file in a run folder holding the deal type the page chose, share or asset.
DEAL_FILE = "deal.txt"


def deal_args(run_dir: Path) -> list[str]:
    """`--deal <type>` when the run folder names a deal type, else nothing."""
    path = Path(run_dir) / DEAL_FILE
    return ["--deal", path.read_text(encoding="utf-8").strip()] if path.exists() else []


class Runner(Protocol):
    """Starts, watches and stops one run per run id. router, when set, is mounted on the app."""

    router: APIRouter | None

    def start(self, run_id: str, room: Path, run_dir: Path, key: str) -> None: ...

    def status(self, run_id: str) -> str:
        """"none" when never started here, "running" or "exited"."""
        ...

    def cancel(self, run_id: str) -> None: ...


class LocalRunner:
    """Runs the command as a child process of this server, its output appended to run.log."""

    router = None

    def __init__(self, command: list[str] | None = None):
        self.command = list(command) if command else [sys.executable, "-m", "rlm.cli"]
        self.processes: dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def argv(self, room: Path, run_dir: Path) -> list[str]:
        """The command line for one run; it books to LEDGER.md under phase 8 only when RLM_PHASE=8."""
        argv = [*self.command, "run", str(room), "--out", str(run_dir), "--yes"]
        if os.environ.get("RLM_PHASE") == "8":
            argv += ["--phase", "8"]
        return argv + deal_args(run_dir)

    def start(self, run_id: str, room: Path, run_dir: Path, key: str) -> None:
        """Starts the command on the room with the key in the child's environment alone."""
        with self._lock:
            if self.status(run_id) == "running":
                raise RuntimeError(f"run {run_id} is already running")
            env = {**os.environ, "OPENROUTER_API_KEY": key, "PYTHONIOENCODING": "utf-8"}
            run_dir.mkdir(parents=True, exist_ok=True)
            with (run_dir / "run.log").open("ab") as log:
                self.processes[run_id] = subprocess.Popen(
                    self.argv(room, run_dir),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )

    def status(self, run_id: str) -> str:
        """"none" when this runner never started the run, "running" or "exited"."""
        process = self.processes.get(run_id)
        if process is None:
            return "none"
        return "running" if process.poll() is None else "exited"

    def cancel(self, run_id: str) -> None:
        """Stops the run's child when it is running and waits for it to exit."""
        process = self.processes.get(run_id)
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def runner_from_env() -> Runner:
    """The runner RLM_RUNNER names: local when unset."""
    name = os.environ.get("RLM_RUNNER", "local") or "local"
    if name == "local":
        return LocalRunner()
    if name == "kubernetes":
        from app.runner_k8s import KubernetesRunner

        return KubernetesRunner()
    raise ValueError(f"no such runner: {name}; RLM_RUNNER is local or kubernetes")
