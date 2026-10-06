"""KubernetesRunner: each run is one Kubernetes Job, and the Job's side of the key handover.

The API pod creates the Job, reads its status and deletes it through the Kubernetes API with
httpx and the pod's service account token: three requests, no client package. The Job runs the
same image with the volumes the API has (RLM_K8S_VOLUMES and RLM_K8S_VOLUME_MOUNTS, which the
chart writes), so it reads the room from and writes the run into the API's runs folder.

The key never goes into the Job. The Job carries a one-time run token instead, and its command,
`python -m app.runner_k8s`, posts that token to the API pod's /runner/key over the cluster
network once. The API hands the key over, forgets the token, and forgets the keys it held for the
run, so a retry sends the keys again. A run on the Anthropic API has a second key, which comes
over with the first under "env" and which the Job gives the gateway directly. The Job holds the
keys in its own memory; they are never set in an environment, written to a file or logged.
The run's model settings are in the run folder as models.json and the Job passes them to the
command. AWS credentials of a bedrock/ model are the pod's own, from its service account role.

A watcher thread per run reads the Job's status every poll seconds and deletes the Job, with its
pod, when it has succeeded or failed.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import ssl
import sys
import threading
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.runner import deal_args, models_args

# Where Kubernetes mounts a pod's service account: its token, its namespace and the cluster CA.
ACCOUNT_DIR = Path("/var/run/secrets/kubernetes.io/serviceaccount")

# The labels every run Job and its pod carry.
LABELS = {"app.kubernetes.io/name": "diligence-reader", "app.kubernetes.io/component": "run"}

# The seconds a finished Job is kept by Kubernetes itself if the API is gone before it deletes it.
TTL_SECONDS = 3600


class Handover(BaseModel):
    token: str


class KubernetesRunner:
    """Starts each run as one Job, watches it, and deletes it when it ends."""

    def __init__(
        self,
        server: str | None = None,
        account_dir: Path | None = None,
        namespace: str | None = None,
        image: str | None = None,
        pull_policy: str | None = None,
        volumes: list[dict] | None = None,
        volume_mounts: list[dict] | None = None,
        api_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
        poll: float = 2.0,
    ):
        env = os.environ
        if server is None:
            host = env.get("KUBERNETES_SERVICE_HOST", "kubernetes.default.svc")
            server = f"https://{host}:{env.get('KUBERNETES_SERVICE_PORT', '443')}"
        self.server = server.rstrip("/")
        self.account_dir = Path(account_dir) if account_dir is not None else ACCOUNT_DIR
        self._namespace = namespace or env.get("RLM_K8S_NAMESPACE")
        self.image = image or env.get("RLM_K8S_IMAGE", "ghcr.io/muhanad-husn/diligence-reader:latest")
        self.pull_policy = pull_policy or env.get("RLM_K8S_PULL_POLICY", "IfNotPresent")
        self.volumes = volumes if volumes is not None else json.loads(env.get("RLM_K8S_VOLUMES", "[]"))
        self.volume_mounts = (
            volume_mounts if volume_mounts is not None else json.loads(env.get("RLM_K8S_VOLUME_MOUNTS", "[]"))
        )
        self.api_url = (api_url or env.get("RLM_K8S_API_URL", "http://localhost:8000")).rstrip("/")
        self.poll = poll
        ca = self.account_dir / "ca.crt"
        verify: ssl.SSLContext | bool = True
        if transport is None and ca.exists():
            verify = ssl.create_default_context(cafile=str(ca))
        self._client = httpx.Client(transport=transport, verify=verify, timeout=30)
        self.jobs: dict[str, str] = {}
        self.states: dict[str, str] = {}
        self.tokens: dict[str, tuple[str, str, dict[str, str]]] = {}
        self._lock = threading.Lock()
        self._closing = threading.Event()
        self._watchers: list[threading.Thread] = []
        self.router = self._handover_router()

    # ------------------------------------------------------------ the Kubernetes API

    @property
    def namespace(self) -> str:
        if self._namespace:
            return self._namespace
        path = self.account_dir / "namespace"
        return path.read_text(encoding="utf-8").strip() if path.exists() else "default"

    def _headers(self) -> dict[str, str]:
        """The service account token, read on every request since Kubernetes rotates it."""
        token = (self.account_dir / "token").read_text(encoding="utf-8").strip()
        return {"Authorization": f"Bearer {token}"}

    def _jobs_url(self) -> str:
        return f"{self.server}/apis/batch/v1/namespaces/{self.namespace}/jobs"

    def _delete(self, name: str) -> None:
        """Deletes a Job and its pod; a Job already gone is not an error."""
        response = self._client.delete(
            f"{self._jobs_url()}/{name}", params={"propagationPolicy": "Background"}, headers=self._headers()
        )
        if response.status_code != 404:
            response.raise_for_status()

    # ------------------------------------------------------------ the Job

    def args(self, room: Path, run_dir: Path) -> list[str]:
        """The Job's arguments; it books to LEDGER.md under phase 8 only when RLM_PHASE=8."""
        found = ["--api", self.api_url, str(room), str(run_dir)]
        if os.environ.get("RLM_PHASE") == "8":
            found += ["--phase", "8"]
        return found

    def job(self, name: str, run_id: str, room: Path, run_dir: Path, token: str) -> dict:
        """The Job for one run: the API's image and volumes, the one-time token, never the key."""
        return {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {"name": name, "labels": LABELS, "annotations": {"diligence-reader/run": run_id}},
            "spec": {
                "backoffLimit": 0,
                "ttlSecondsAfterFinished": TTL_SECONDS,
                "template": {
                    "metadata": {"labels": LABELS},
                    "spec": {
                        "restartPolicy": "Never",
                        "automountServiceAccountToken": False,
                        "volumes": self.volumes,
                        "containers": [
                            {
                                "name": "run",
                                "image": self.image,
                                "imagePullPolicy": self.pull_policy,
                                "command": ["python", "-m", "app.runner_k8s"],
                                "args": self.args(room, run_dir),
                                "env": [{"name": "RLM_RUN_TOKEN", "value": token}],
                                "volumeMounts": self.volume_mounts,
                            }
                        ],
                    },
                },
            },
        }

    def start(
        self, run_id: str, room: Path, run_dir: Path, key: str, extra_env: dict[str, str] | None = None
    ) -> None:
        """Creates the run's Job with a fresh one-time token held against the keys, and watches it."""
        with self._lock:
            if self.states.get(run_id) == "running":
                raise RuntimeError(f"run {run_id} is already running")
            token = secrets.token_urlsafe(32)
            name = f"run-{run_id}"[:57].rstrip("-") + "-" + secrets.token_hex(2)
            self.tokens[token] = (run_id, key, dict(extra_env or {}))
            self.states[run_id] = "running"
        try:
            response = self._client.post(
                self._jobs_url(), json=self.job(name, run_id, room, run_dir, token), headers=self._headers()
            )
            response.raise_for_status()
        except Exception:
            with self._lock:
                self.tokens.pop(token, None)
                self.states.pop(run_id, None)
            raise
        with self._lock:
            self.jobs[run_id] = name
        watcher = threading.Thread(target=self._watch, args=(run_id, name), daemon=True)
        self._watchers.append(watcher)
        watcher.start()

    def _watch(self, run_id: str, name: str) -> None:
        """Reads the Job's status until it has succeeded or failed, then deletes it."""
        while not self._closing.wait(self.poll):
            try:
                response = self._client.get(f"{self._jobs_url()}/{name}", headers=self._headers())
            except httpx.HTTPError:
                continue
            if response.status_code == 404:
                break
            if response.status_code != 200:
                continue
            if ended(response.json().get("status") or {}):
                break
        else:
            return
        self._finish(run_id, name)

    def _finish(self, run_id: str, name: str) -> None:
        try:
            self._delete(name)
        except httpx.HTTPError:
            pass
        with self._lock:
            if self.jobs.get(run_id) == name:
                self.states[run_id] = "exited"
            for token, (held, _, _) in list(self.tokens.items()):
                if held == run_id:
                    self.tokens.pop(token)

    def status(self, run_id: str) -> str:
        """"none" when this runner never started the run, "running" or "exited"."""
        return self.states.get(run_id, "none")

    def cancel(self, run_id: str) -> None:
        """Deletes the run's Job when it is running."""
        name = self.jobs.get(run_id)
        if name is None or self.states.get(run_id) != "running":
            return
        self._finish(run_id, name)

    def close(self) -> None:
        """Stops the watchers without deleting the Jobs they watch."""
        self._closing.set()
        for watcher in self._watchers:
            watcher.join(timeout=5)
        self._client.close()

    # ------------------------------------------------------------ the handover

    def _handover_router(self) -> APIRouter:
        router = APIRouter()

        @router.post("/runner/key")
        async def hand_over(body: Handover, request: Request):
            with self._lock:
                held = self.tokens.pop(body.token, None)
            if held is None:
                return JSONResponse(
                    {"code": "no-token", "message": "no key is held for this token"}, status_code=404
                )
            run_id, key, env = held
            for name in ("keys", "anthropic_keys"):
                held_keys = getattr(request.app.state, name, None)
                if held_keys is not None:
                    held_keys.pop(run_id, None)
            return {"key": key, "env": env} if env else {"key": key}

        return router


def ended(status: dict) -> bool:
    """Says whether a Job's status reads succeeded or failed."""
    if status.get("succeeded") or status.get("failed"):
        return True
    return any(
        condition.get("type") in ("Complete", "Failed") and condition.get("status") == "True"
        for condition in status.get("conditions") or []
    )


# ---------------------------------------------------------------- the Job's command


def fetch_keys(api_url: str, token: str, client: httpx.Client | None = None) -> tuple[str, dict[str, str]]:
    """Posts the one-time token to the API and returns the key it hands over and the other keys."""
    own = client is None
    client = client if client is not None else httpx.Client(timeout=30)
    try:
        response = client.post(f"{api_url.rstrip('/')}/runner/key", json={"token": token})
        response.raise_for_status()
        body = response.json()
        return body["key"], dict(body.get("env") or {})
    finally:
        if own:
            client.close()


def fetch_key(api_url: str, token: str, client: httpx.Client | None = None) -> str:
    """Posts the one-time token to the API and returns the OpenRouter key it hands over."""
    return fetch_keys(api_url, token, client)[0]


def main(
    argv: list[str] | None = None,
    client: httpx.Client | None = None,
    transport: httpx.BaseTransport | None = None,
) -> int:
    """The Job: fetches the key once, then runs the command on the room, its output in run.log."""
    from rlm import cli
    from rlm.gateway import Gateway

    parser = argparse.ArgumentParser(prog="python -m app.runner_k8s")
    parser.add_argument("--api", required=True, help="the API's address inside the cluster")
    parser.add_argument("room")
    parser.add_argument("run_dir")
    parser.add_argument("--phase", default=None)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    token = os.environ.pop("RLM_RUN_TOKEN", "")
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "run.log").open("a", encoding="utf-8") as log, redirect_stdout(log), redirect_stderr(log):
        try:
            key, env = fetch_keys(args.api, token, client)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", "")
            print(f"error: the API did not hand the run's key over: {type(exc).__name__} {status}".rstrip())
            return 2
        command = ["run", args.room, "--out", str(run_dir), "--yes"]
        if args.phase is not None:
            command += ["--phase", args.phase]
        command += models_args(run_dir)
        command += deal_args(run_dir)
        gateway = Gateway(api_key=key, anthropic_key=env.get("ANTHROPIC_API_KEY"), transport=transport)
        return cli.main(command, gateway=gateway)


if __name__ == "__main__":
    sys.exit(main())
