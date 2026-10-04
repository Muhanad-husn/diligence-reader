"""Phase 8 slice 05: the image, the release build, the Helm chart with its KubernetesRunner, upkeep.

The tests at $0 read the files the slice ships: the Dockerfile and its whitelist, the three
workflows, the Dependabot file and the chart as `helm template` renders it (skipped when helm is
not installed). The KubernetesRunner is driven against a fake Kubernetes API, a transport that
keeps Jobs in a dict, and a run goes through it end to end on test_phase8_command's fake model
transport: the Job is created, fetches the key once from the API with its one-time token, runs
the command, and is deleted when it ends.

The tests that build the image and install the chart on kind take minutes, so they run only with
RLM_PACKAGE=1 and skip with a reason when docker, kind or helm is absent. The image tests run
tests/test_phase8_api.py inside the container and check that a code-only change rebuilds the code
layer alone. The kind tests start a run through the API in the cluster on a key OpenRouter
refuses, which costs nothing; with RLM_PACKAGE_LIVE=1 and OPENROUTER_API_KEY set they also run
sample 3 on the real key, booked to LEDGER.md under phase 8 the way the API's live run is.
"""

import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from app import runner_k8s
from app.main import create_app
from app.runner import runner_from_env
from app.runner_k8s import KubernetesRunner
from conftest import ROOT
from test_phase8_api import (
    EXPORTS,
    GOOD_KEY,
    LIVE_BAD_KEY,
    files_holding,
    free_port,
    live_upload,
    read_events,
    run_json,
    started,
    steps,
    EVERY_STEP,
)
from test_phase8_command import RoomTransport

DEPLOY = ROOT / "deploy"
DOCKERFILE = DEPLOY / "Dockerfile"
DOCKERIGNORE = DEPLOY / "Dockerfile.dockerignore"
CHART = DEPLOY / "helm" / "diligence-reader"
WORKFLOWS = ROOT / ".github" / "workflows"

NAMESPACE = "rlm"
API_URL = "http://dr-diligence-reader:8000"
VOLUMES = [{"name": "runs", "persistentVolumeClaim": {"claimName": "dr-diligence-reader-runs"}}]
MOUNTS = [{"name": "runs", "mountPath": "/app/runs"}]


def workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def triggers(found: dict) -> dict:
    """A workflow's `on` block; YAML 1.1 reads the bare key on as true."""
    return found.get("on", found.get(True))


def steps_text(job: dict) -> str:
    return json.dumps(job.get("steps", []))


def instructions() -> list[str]:
    """The Dockerfile's instructions, one per entry, continuation lines joined."""
    text = DOCKERFILE.read_text(encoding="utf-8").replace("\\\n", " ")
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]


# ---------------------------------------------------------------- the image


def test_the_dockerfile_pins_its_base_by_digest_and_installs_with_uv():
    found = instructions()
    bases = [line for line in found if line.startswith("FROM python")]

    assert len(bases) == 1
    assert re.match(r"FROM python:3\.13-slim(-\w+)?@sha256:[0-9a-f]{64} AS \w+", bases[0])
    uv = [line for line in found if "astral-sh/uv" in line]
    assert uv and all(re.search(r"@sha256:[0-9a-f]{64}", line) for line in uv)
    assert any("uv pip install" in line and "-r pyproject.toml" in line for line in found)
    assert not any(re.search(r"\bpip install\b", line) and "uv pip" not in line for line in found)


def test_the_layers_go_system_then_dependencies_then_code():
    found = instructions()
    first = found.index(next(line for line in found if line.startswith("FROM python")))
    runtime = found.index(next(line for line in found if re.match(r"FROM \w+ AS runtime", line)))
    deps_copy = next(i for i, line in enumerate(found) if line.startswith("COPY") and "pyproject.toml" in line)
    deps_install = next(i for i, line in enumerate(found) if "uv pip install" in line)
    system = next(i for i, line in enumerate(found) if line.startswith("RUN") and i > first)
    code = next(i for i, line in enumerate(found) if i > runtime and line.startswith("COPY"))

    assert first < system < deps_copy < deps_install < runtime < code
    assert found[deps_copy].split()[-2:] == ["pyproject.toml", "/app/"]
    assert not any(line.startswith("RUN") for line in found[code:])
    assert re.match(r"FROM \w+ AS runtime", found[runtime]) and found[runtime] == [
        line for line in found if line.startswith("FROM")
    ][-1]


def test_the_image_carries_no_weasyprint_and_no_pango():
    text = DOCKERFILE.read_text(encoding="utf-8").lower()

    assert "weasyprint" not in text
    assert "pango" not in text


def test_the_image_serves_the_api_on_port_8000_as_a_user_not_root():
    found = instructions()

    assert "EXPOSE 8000" in found
    assert any(line.startswith("USER ") and line.split()[1] not in ("root", "0") for line in found)
    cmd = next(line for line in found if line.startswith("CMD"))
    assert "app.main:app" in cmd and "0.0.0.0" in cmd and "8000" in cmd
    assert any("RLM_RUNS=/app/runs" in line for line in found if line.startswith("ENV"))


def test_the_build_context_is_a_whitelist_that_tolerates_no_web_folder():
    lines = [
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    assert lines[0] == "*"
    allowed = {line[1:].rstrip("/") for line in lines if line.startswith("!")}
    assert {"pyproject.toml", "src/rlm", "app", "web"} <= allowed
    assert not allowed & {"runs", "tests", "samples", ".env", "LEDGER.md"}
    code = [line for line in instructions() if line.startswith("COPY") and "web" in line]
    assert code == [], "web/ is copied by the whitelist, never by name, so its absence breaks nothing"


# ---------------------------------------------------------------- the workflows


def test_the_pull_request_build_publishes_nothing():
    found = workflow("image.yml")
    on = triggers(found)

    assert set(on) == {"pull_request"}
    assert set(on["pull_request"]["paths"]) >= {"deploy/**", "pyproject.toml", "app/**"}
    build = [
        step
        for job in found["jobs"].values()
        for step in job["steps"]
        if str(step.get("uses", "")).startswith("docker/build-push-action")
    ]
    assert len(build) == 1
    assert build[0]["with"]["push"] is False
    assert "type=gha" in build[0]["with"]["cache-from"]
    assert "type=gha" in build[0]["with"]["cache-to"]
    assert build[0]["with"]["file"] == "deploy/Dockerfile"


def test_the_release_publishes_three_ways_on_a_tag_and_dry_runs_on_a_pull_request():
    found = workflow("release.yml")
    on = triggers(found)
    text = (WORKFLOWS / "release.yml").read_text(encoding="utf-8")

    assert on["push"]["tags"] == ["v*"]
    assert on["pull_request"]["paths"] == [".github/workflows/release.yml"]
    runners = json.dumps(found["jobs"])
    assert "ubuntu-24.04-arm" in runners and "linux/arm64" in runners and "linux/amd64" in runners
    assert "ghcr.io/muhanad-husn/diligence-reader" in text
    assert "latest" in text
    assert "pypa/gh-action-pypi-publish" in text
    assert "id-token: write" in text
    assert "oci://ghcr.io/muhanad-husn/charts" in text
    assert "secrets.PYPI" not in text, "PyPI is reached by trusted publishing, not a token"
    publishing = [
        step
        for job in found["jobs"].values()
        for step in job.get("steps", [])
        if "pypi-publish" in str(step.get("uses", ""))
        or "helm push" in str(step.get("run", ""))
        or "imagetools create" in str(step.get("run", ""))
    ]
    assert len(publishing) == 3
    for step in publishing:
        guard = step.get("if", "") + json.dumps(
            [job.get("if", "") for job in found["jobs"].values() if step in job.get("steps", [])]
        )
        assert "refs/tags/v" in guard or "env.PUBLISH" in guard, step


def test_the_weekly_workflow_has_four_jobs_and_needs_no_key():
    found = workflow("weekly.yml")
    on = triggers(found)
    text = (WORKFLOWS / "weekly.yml").read_text(encoding="utf-8")

    assert "schedule" in on and on["schedule"][0]["cron"]
    assert on["pull_request"]["paths"] == [".github/workflows/weekly.yml"]
    assert len(found["jobs"]) == 4
    every = " ".join(steps_text(job) for job in found["jobs"].values())
    assert "python -m rlm.modelcheck" in every
    assert "pytest -q -W error::DeprecationWarning" in every
    assert "aquasecurity/trivy-action" in every
    assert "kind" in every and "helm install" in every and "rollout status" in every
    assert "secrets." not in text
    assert "OPENROUTER_API_KEY" not in text
    trivy = next(
        step for job in found["jobs"].values() for step in job["steps"] if "trivy-action" in str(step.get("uses", ""))
    )
    assert trivy["with"]["severity"] == "HIGH,CRITICAL"
    assert str(trivy["with"]["ignore-unfixed"]).lower() == "true"
    assert str(trivy["with"]["exit-code"]) == "1"


def test_dependabot_updates_weekly_in_groups():
    found = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    updates = {entry["package-ecosystem"]: entry for entry in found["updates"]}

    assert found["version"] == 2
    assert {"pip", "docker", "github-actions", "helm"} <= set(updates)
    assert "npm" not in updates
    assert updates["docker"]["directory"] == "/deploy"
    for entry in updates.values():
        assert entry["schedule"]["interval"] == "weekly"
        assert entry.get("groups"), entry["package-ecosystem"]


def test_workflow_actions_are_pinned_to_a_version():
    for path in WORKFLOWS.glob("*.yml"):
        for use in re.findall(r"uses:\s*(\S+)", path.read_text(encoding="utf-8")):
            assert "@" in use and not use.endswith(("@main", "@master")), f"{path.name}: {use}"


# ---------------------------------------------------------------- the chart

HELM = shutil.which("helm")
needs_helm = pytest.mark.skipif(HELM is None, reason="helm is not installed")


def rendered(*extra: str) -> list[dict]:
    done = subprocess.run(
        [HELM, "template", "dr", str(CHART), "--namespace", NAMESPACE, *extra],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    return [doc for doc in yaml.safe_load_all(done.stdout) if doc]


def of_kind(docs: list[dict], kind: str) -> list[dict]:
    return [doc for doc in docs if doc["kind"] == kind]


def env_of(container: dict) -> dict:
    return {entry["name"]: entry.get("value") for entry in container.get("env", [])}


@needs_helm
def test_the_chart_lints():
    done = subprocess.run([HELM, "lint", str(CHART)], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr


@needs_helm
def test_the_chart_holds_the_api_a_runs_volume_and_a_role_for_jobs_and_nothing_secret():
    docs = rendered()
    kinds = {doc["kind"] for doc in docs}

    assert {"Deployment", "Service", "ServiceAccount", "Role", "RoleBinding", "PersistentVolumeClaim"} <= kinds
    assert not kinds & {"Secret", "ConfigMap"}
    (role,) = of_kind(docs, "Role")
    assert role["rules"] == [{"apiGroups": ["batch"], "resources": ["jobs"], "verbs": ["create", "get", "delete"]}]
    (binding,) = of_kind(docs, "RoleBinding")
    (account,) = of_kind(docs, "ServiceAccount")
    assert binding["roleRef"]["name"] == role["metadata"]["name"]
    assert binding["subjects"][0]["name"] == account["metadata"]["name"]
    (service,) = of_kind(docs, "Service")
    assert service["spec"]["ports"][0]["port"] == 8000


@needs_helm
def test_the_api_runs_the_kubernetes_runner_with_the_same_volumes_it_gives_the_jobs():
    docs = rendered()
    (deployment,) = of_kind(docs, "Deployment")
    (service,) = of_kind(docs, "Service")
    (claim,) = of_kind(docs, "PersistentVolumeClaim")
    pod = deployment["spec"]["template"]["spec"]
    (container,) = pod["containers"]
    env = env_of(container)

    assert pod["serviceAccountName"] == of_kind(docs, "ServiceAccount")[0]["metadata"]["name"]
    assert env["RLM_RUNNER"] == "kubernetes"
    assert env["RLM_RUNS"] == "/app/runs"
    assert env["RLM_K8S_IMAGE"] == container["image"]
    assert env["RLM_K8S_PULL_POLICY"] == container["imagePullPolicy"]
    assert env["RLM_K8S_API_URL"] == f"http://{service['metadata']['name']}:8000"
    assert json.loads(env["RLM_K8S_VOLUMES"]) == pod["volumes"]
    assert json.loads(env["RLM_K8S_VOLUME_MOUNTS"]) == container["volumeMounts"]
    runs = next(volume for volume in pod["volumes"] if volume["name"] == "runs")
    assert runs["persistentVolumeClaim"]["claimName"] == claim["metadata"]["name"]
    assert {"name": "runs", "mountPath": "/app/runs"} in container["volumeMounts"]
    assert container["ports"][0]["containerPort"] == 8000
    assert container["readinessProbe"]
    assert container["image"].startswith("ghcr.io/muhanad-husn/diligence-reader:")


@needs_helm
def test_extra_volumes_and_env_reach_the_api_and_the_jobs():
    volume = {"name": "ledger", "hostPath": {"path": "/repo/LEDGER.md", "type": "File"}}
    mount = {"name": "ledger", "mountPath": "/app/LEDGER.md"}
    docs = rendered(
        "--set-json", f"extraVolumes=[{json.dumps(volume)}]",
        "--set-json", f"extraVolumeMounts=[{json.dumps(mount)}]",
        "--set", "extraEnv.RLM_PHASE=8",
    )
    (deployment,) = of_kind(docs, "Deployment")
    (container,) = deployment["spec"]["template"]["spec"]["containers"]
    env = env_of(container)

    assert volume in json.loads(env["RLM_K8S_VOLUMES"])
    assert mount in json.loads(env["RLM_K8S_VOLUME_MOUNTS"])
    assert env["RLM_PHASE"] == "8"


# ---------------------------------------------------------------- the runner, on a fake cluster


class FakeCluster(httpx.MockTransport):
    """The three Job requests of the Kubernetes API, with the Jobs kept in a dict."""

    PREFIX = f"/apis/batch/v1/namespaces/{NAMESPACE}/jobs"

    def __init__(self):
        self.jobs: dict[str, dict] = {}
        self.created: list[dict] = []
        self.deleted: list[tuple[str, str]] = []
        self.requests: list[httpx.Request] = []
        self._lock = threading.Lock()
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        with self._lock:
            self.requests.append(request)
            path = request.url.path
            if request.method == "POST" and path == self.PREFIX:
                body = json.loads(request.content)
                body["status"] = {"active": 1}
                self.jobs[body["metadata"]["name"]] = body
                self.created.append(body)
                return httpx.Response(201, json=body)
            name = path[len(self.PREFIX) + 1:]
            if request.method == "GET" and name in self.jobs:
                return httpx.Response(200, json=self.jobs[name])
            if request.method == "DELETE" and name in self.jobs:
                self.jobs.pop(name)
                self.deleted.append((name, request.url.params.get("propagationPolicy")))
                return httpx.Response(200, json={"kind": "Status", "status": "Success"})
            return httpx.Response(404, json={"kind": "Status", "reason": "NotFound"})

    def finish(self, name: str, ok: bool = True) -> None:
        with self._lock:
            self.jobs[name]["status"] = {"succeeded": 1} if ok else {"failed": 1}


@pytest.fixture
def k8s(tmp_path, monkeypatch):
    """A KubernetesRunner on a fake cluster, its service account files in a folder of the test."""
    monkeypatch.delenv("RLM_PHASE", raising=False)
    account = tmp_path / "serviceaccount"
    account.mkdir()
    (account / "token").write_text("sa-token-1", encoding="utf-8")
    (account / "namespace").write_text(NAMESPACE, encoding="utf-8")
    cluster = FakeCluster()
    runner = KubernetesRunner(
        server="https://kubernetes.test",
        account_dir=account,
        image="diligence-reader:dev",
        pull_policy="Never",
        volumes=VOLUMES,
        volume_mounts=MOUNTS,
        api_url=API_URL,
        transport=cluster,
        poll=0.01,
    )
    yield runner, cluster
    runner.close()


def wait_for(condition, seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


def container_of(job: dict) -> dict:
    (container,) = job["spec"]["template"]["spec"]["containers"]
    return container


def test_the_runner_is_kubernetes_when_named(monkeypatch):
    monkeypatch.setenv("RLM_RUNNER", "kubernetes")
    assert isinstance(runner_from_env(), KubernetesRunner)


def test_start_creates_one_job_that_carries_no_key(k8s, tmp_path):
    runner, cluster = k8s
    run_dir = tmp_path / "runs" / "r1"

    runner.start("r1", run_dir / "r1", run_dir, GOOD_KEY)

    assert len(cluster.created) == 1
    job = cluster.created[0]
    assert GOOD_KEY not in json.dumps(job)
    assert all(GOOD_KEY not in request.content.decode("utf-8", "replace") for request in cluster.requests)
    assert cluster.requests[0].headers["authorization"] == "Bearer sa-token-1"
    name = job["metadata"]["name"]
    assert re.fullmatch(r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?", name)
    spec = job["spec"]
    assert spec["backoffLimit"] == 0
    pod = spec["template"]["spec"]
    assert pod["restartPolicy"] == "Never"
    assert pod["automountServiceAccountToken"] is False
    assert pod["volumes"] == VOLUMES
    container = container_of(job)
    assert container["image"] == "diligence-reader:dev"
    assert container["imagePullPolicy"] == "Never"
    assert container["volumeMounts"] == MOUNTS
    assert container["command"] == ["python", "-m", "app.runner_k8s"]
    assert container["args"] == ["--api", API_URL, str(run_dir / "r1"), str(run_dir)]
    names = [entry["name"] for entry in container["env"]]
    assert "OPENROUTER_API_KEY" not in names
    assert "RLM_RUN_TOKEN" in names
    assert runner.status("r1") == "running"
    assert runner.status("never") == "none"


def test_the_job_books_phase_8_only_when_the_server_is_told(k8s, tmp_path, monkeypatch):
    runner, cluster = k8s
    monkeypatch.setenv("RLM_PHASE", "8")

    runner.start("p8", tmp_path / "p8" / "p8", tmp_path / "p8", GOOD_KEY)

    assert container_of(cluster.created[0])["args"][-2:] == ["--phase", "8"]


def test_a_finished_job_is_deleted_and_the_run_has_exited(k8s, tmp_path):
    runner, cluster = k8s
    runner.start("r2", tmp_path / "r2" / "r2", tmp_path / "r2", GOOD_KEY)
    name = cluster.created[0]["metadata"]["name"]

    cluster.finish(name, ok=False)

    assert wait_for(lambda: runner.status("r2") == "exited")
    assert cluster.deleted == [(name, "Background")]
    assert runner.tokens == {}


def test_cancel_deletes_the_job(k8s, tmp_path):
    runner, cluster = k8s
    runner.start("r3", tmp_path / "r3" / "r3", tmp_path / "r3", GOOD_KEY)
    name = cluster.created[0]["metadata"]["name"]

    runner.cancel("r3")

    assert (name, "Background") in cluster.deleted
    assert runner.status("r3") == "exited"


def test_a_second_start_while_running_is_refused(k8s, tmp_path):
    runner, _ = k8s
    runner.start("r4", tmp_path / "r4" / "r4", tmp_path / "r4", GOOD_KEY)

    with pytest.raises(RuntimeError):
        runner.start("r4", tmp_path / "r4" / "r4", tmp_path / "r4", GOOD_KEY)


def test_a_token_hands_the_key_over_once_and_the_api_forgets_it(k8s, tmp_path):
    runner, cluster = k8s
    app = create_app(runner=runner, runs_root=tmp_path / "runs", web_dir=tmp_path / "noweb")
    with TestClient(app) as client:
        run_id = started(client, tmp_path)
        token = {entry["name"]: entry["value"] for entry in container_of(cluster.created[0])["env"]}[
            "RLM_RUN_TOKEN"
        ]

        assert client.post("/runner/key", json={"token": "not-a-token"}).status_code == 404
        first = client.post("/runner/key", json={"token": token})
        second = client.post("/runner/key", json={"token": token})

        assert first.status_code == 200
        assert first.json() == {"key": GOOD_KEY}
        assert second.status_code == 404
        assert run_id not in client.app.state.keys
        assert runner.tokens == {}


class KeyedRoomTransport(RoomTransport):
    """test_phase8_command's fake model transport, recording the key each call carried."""

    def __init__(self, **kwargs):
        self.keys: set[str] = set()
        super().__init__(**kwargs)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.keys.add(request.headers["authorization"].removeprefix("Bearer "))
        return super()._handle(request)


def test_a_run_goes_through_its_job_on_the_key_it_fetched(k8s, tmp_path, monkeypatch, caplog):
    runner, cluster = k8s
    app = create_app(runner=runner, runs_root=tmp_path / "runs", web_dir=tmp_path / "noweb")
    with TestClient(app) as client:
        run_id = started(client, tmp_path)
        job = cluster.created[0]
        container = container_of(job)
        env = {entry["name"]: entry["value"] for entry in container["env"]}
        monkeypatch.setenv("RLM_RUN_TOKEN", env["RLM_RUN_TOKEN"])
        transport = KeyedRoomTransport()

        code = runner_k8s.main(container["args"], client=client, transport=transport)

        assert code == 0
        assert transport.keys == {GOOD_KEY}
        assert "RLM_RUN_TOKEN" not in os.environ
        assert GOOD_KEY not in os.environ.values()
        cluster.finish(job["metadata"]["name"])
        found = read_events(client, run_id)
        assert found[-1]["type"] == "RUN_FINISHED"
        assert steps(found) == EVERY_STEP
        assert wait_for(lambda: cluster.deleted)
        assert cluster.jobs == {}
        run_dir = tmp_path / "runs" / run_id
        assert run_json(run_dir)["status"] == "done"
        assert (run_dir / "run.log").exists()
        assert files_holding(run_dir, GOOD_KEY) == []
        assert GOOD_KEY not in caplog.text


def test_a_job_whose_token_is_refused_stops_without_a_key(tmp_path, monkeypatch):
    app = create_app(
        runner=KubernetesRunner(server="https://kubernetes.test", transport=FakeCluster()),
        runs_root=tmp_path / "runs",
        web_dir=tmp_path / "noweb",
    )
    monkeypatch.setenv("RLM_RUN_TOKEN", "not-a-token")
    run_dir = tmp_path / "runs" / "r5"
    run_dir.mkdir(parents=True)
    with TestClient(app) as client:
        code = runner_k8s.main(
            ["--api", "http://testserver", str(run_dir / "r5"), str(run_dir)],
            client=client,
            transport=KeyedRoomTransport(),
        )

    assert code != 0
    assert "key" in (run_dir / "run.log").read_text(encoding="utf-8")


# ---------------------------------------------------------------- the image, built

PACKAGE = os.environ.get("RLM_PACKAGE") == "1"
LIVE = os.environ.get("RLM_PACKAGE_LIVE") == "1"
IMAGE = "diligence-reader:dev"
TEST_IMAGE = "diligence-reader:test"
CLUSTER = "rlm-package"
RECORD: dict = {}


def docker_answers() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def need(*tools: str) -> None:
    """Skips unless RLM_PACKAGE=1 and every tool named is installed (docker: and answering)."""
    if not PACKAGE:
        pytest.skip("builds the image and a kind cluster, minutes of work; RLM_PACKAGE=1")
    for tool in tools:
        if tool == "docker" and not docker_answers():
            pytest.skip("docker is not installed or its engine is not running")
        if tool != "docker" and shutil.which(tool) is None:
            pytest.skip(f"{tool} is not installed")


def sh(*argv: str, timeout: float = 1800, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    done = subprocess.run(
        list(argv), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, **kwargs
    )
    if check:
        assert done.returncode == 0, f"{' '.join(argv[:4])}: {done.stdout[-3000:]}{done.stderr[-3000:]}"
    return done


def build(context: Path, target: str, tag: str, *extra: str) -> tuple[float, str]:
    """Builds one target of the Dockerfile; the seconds it took and BuildKit's plain output."""
    began = time.monotonic()
    done = sh(
        "docker", "build", "--progress=plain", "-f", str(context / "deploy" / "Dockerfile"),
        "--target", target, "-t", tag, *extra, str(context),
    )
    return time.monotonic() - began, done.stderr + done.stdout


@pytest.fixture(scope="module")
def image():
    need("docker")
    RECORD["build_seconds"], _ = build(ROOT, "runtime", IMAGE)
    build(ROOT, "test", TEST_IMAGE)
    return IMAGE


def test_the_api_tests_pass_inside_the_container(image):
    done = sh(
        "docker", "run", "--rm",
        "-v", f"{ROOT / 'tests'}:/app/tests:ro",
        "-v", f"{ROOT / 'samples'}:/app/samples:ro",
        TEST_IMAGE, "pytest", "-q", "-p", "no:cacheprovider", "tests/test_phase8_api.py",
        check=False,
    )
    RECORD["container_tests"] = (done.stdout.strip().splitlines() or [""])[-1]
    assert done.returncode == 0, done.stdout[-4000:] + done.stderr[-2000:]
    assert " passed" in done.stdout and " failed" not in done.stdout


def test_the_image_runs_as_a_user_with_no_weasyprint(image):
    assert sh("docker", "run", "--rm", image, "id", "-u").stdout.strip() != "0"
    probe = "import importlib.util as u; print(u.find_spec('weasyprint') is None)"
    assert sh("docker", "run", "--rm", image, "python", "-c", probe).stdout.strip() == "True"
    size = sh("docker", "image", "inspect", image, "--format", "{{.Size}}").stdout.strip()
    RECORD["image_megabytes"] = round(int(size) / 1_000_000)


def test_the_image_answers_on_port_8000(image):
    port = free_port()
    name = f"rlm-package-{port}"
    sh("docker", "run", "-d", "--rm", "--name", name, "-p", f"127.0.0.1:{port}:8000", image)
    try:
        assert wait_for(lambda: answers(f"http://127.0.0.1:{port}/runs/none-such"), 60)
        response = httpx.get(f"http://127.0.0.1:{port}/runs/none-such")
        assert response.status_code == 404
        assert response.json()["code"] == "no-run"
    finally:
        sh("docker", "rm", "-f", name, check=False)


def answers(url: str) -> bool:
    try:
        httpx.get(url, timeout=5)
        return True
    except httpx.TransportError:
        return False


# The steps a code-only change may run again: the copy of the code. A FROM line is resolved,
# not built, and BuildKit reports it as DONE either way.
STEP = re.compile(r"^#(\d+) \[(?:[\w-]+ )?\d+/\d+\] (.+)$")


def rebuilt_steps(output: str) -> list[str]:
    """The steps of a plain BuildKit log that were not served from the cache."""
    found: dict[str, str] = {}
    cached: set[str] = set()
    for line in output.splitlines():
        match = STEP.match(line.strip())
        if match:
            found[match.group(1)] = match.group(2)
        elif re.match(r"^#\d+ CACHED$", line.strip()):
            cached.add(line.strip().split()[0][1:])
    return [step for number, step in found.items() if number not in cached and not step.startswith("FROM")]


def test_a_code_only_change_rebuilds_the_code_layer_alone(image, tmp_path):
    context = tmp_path / "context"
    for relative in ("deploy", "src/rlm", "app", "web", "pyproject.toml", "README.md", "LICENSE", "NOTICE"):
        source = ROOT / relative
        if source.is_dir():
            shutil.copytree(source, context / relative, ignore=shutil.ignore_patterns("__pycache__"))
        elif source.exists():
            (context / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, context / relative)
    build(context, "runtime", "diligence-reader:cachecheck")
    with (context / "app" / "main.py").open("a", encoding="utf-8") as handle:
        handle.write("\n# a code-only change\n")

    seconds, output = build(context, "runtime", "diligence-reader:cachecheck")
    sh("docker", "image", "rm", "diligence-reader:cachecheck", check=False)

    RECORD["code_only_rebuild_seconds"] = round(seconds, 1)
    rebuilt = rebuilt_steps(output)
    assert len(rebuilt) == 1 and rebuilt[0].startswith("COPY"), rebuilt
    assert seconds < 60


# ---------------------------------------------------------------- the chart, on kind


def kubectl(*argv: str, **kwargs) -> subprocess.CompletedProcess:
    return sh("kubectl", "--context", f"kind-{CLUSTER}", *argv, **kwargs)


@pytest.fixture(scope="module")
def cluster(image, tmp_path_factory):
    """A kind cluster with the image loaded and the chart installed, its API forwarded to a port.

    The API books its runs under phase 8 (RLM_PHASE=8) to this checkout's LEDGER.md, mounted into
    the kind node at /repo and from there into every Job, the way the API's live run books.
    """
    need("docker", "kind", "helm", "kubectl")
    folder = tmp_path_factory.mktemp("kind")
    config = folder / "kind.yaml"
    config.write_text(
        json.dumps(
            {
                "kind": "Cluster",
                "apiVersion": "kind.x-k8s.io/v1alpha4",
                "nodes": [{"role": "control-plane", "extraMounts": [{"hostPath": str(ROOT), "containerPath": "/repo"}]}],
            }
        ),
        encoding="utf-8",
    )
    sh("kind", "delete", "cluster", "--name", CLUSTER, check=False)
    sh("kind", "create", "cluster", "--name", CLUSTER, "--config", str(config), "--wait", "180s")
    forward = None
    try:
        sh("kind", "load", "docker-image", IMAGE, "--name", CLUSTER)
        ledger = {"name": "ledger", "hostPath": {"path": "/repo/LEDGER.md", "type": "File"}}
        mount = {"name": "ledger", "mountPath": "/app/LEDGER.md"}
        sh(
            "helm", "install", "dr", str(CHART), "--kube-context", f"kind-{CLUSTER}",
            "--set", "image.repository=diligence-reader", "--set", "image.tag=dev",
            "--set", "image.pullPolicy=Never", "--set", "extraEnv.RLM_PHASE=8",
            "--set-json", f"extraVolumes=[{json.dumps(ledger)}]",
            "--set-json", f"extraVolumeMounts=[{json.dumps(mount)}]",
            "--wait", "--timeout", "5m",
        )
        port = free_port()
        forward = subprocess.Popen(
            ["kubectl", "--context", f"kind-{CLUSTER}", "port-forward", "svc/dr-diligence-reader", f"{port}:8000"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        base = f"http://127.0.0.1:{port}"
        assert wait_for(lambda: answers(f"{base}/runs/none-such"), 60), "the API did not answer"
        yield base
    finally:
        if forward is not None:
            forward.terminate()
        sh("kind", "delete", "cluster", "--name", CLUSTER, check=False)


class Watch(threading.Thread):
    """Lists the run Jobs every second and reads every Secret, ConfigMap, Job and Pod as YAML."""

    def __init__(self, key: str):
        super().__init__(daemon=True)
        self.key = key
        self.jobs: set[str] = set()
        self.reads = 0
        self.leaks: list[str] = []
        self.stopping = threading.Event()

    def run(self):
        while not self.stopping.is_set():
            listed = kubectl("get", "jobs", "-o", "json", check=False, timeout=60)
            if listed.returncode == 0:
                self.jobs |= {item["metadata"]["name"] for item in json.loads(listed.stdout)["items"]}
            dumped = kubectl("get", "secrets,configmaps,jobs,pods", "-A", "-o", "yaml", check=False, timeout=60)
            if dumped.returncode == 0:
                self.reads += 1
                if self.key in dumped.stdout:
                    self.leaks.append("kubectl get secrets,configmaps,jobs,pods")
            self.stopping.wait(1.0)


def run_on_kind(base: str, sample: str, name: str, key: str, tmp_path: Path) -> dict:
    """Starts a run of sample through the API in the cluster and follows it to its end and after."""
    watch = Watch(key)
    watch.start()
    try:
        with httpx.Client(base_url=base, timeout=120) as client:
            response = client.post(
                "/runs", files=live_upload(sample), data={"name": name}, headers={"X-OpenRouter-Key": key}
            )
            assert response.status_code == 201, response.text
            assert client.get(f"/runs/{name}/estimate").status_code == 200
            assert client.post(f"/runs/{name}/confirm").status_code == 202
            found = []
            with client.stream("GET", f"/runs/{name}/events", timeout=None) as stream:
                for line in stream.iter_lines():
                    if line.startswith("data: "):
                        found.append(json.loads(line[len("data: "):]))
            state = client.get(f"/runs/{name}").json()["state"]
            exports = {fmt: client.get(f"/runs/{name}/export/{fmt}").status_code for fmt in EXPORTS}
        gone = wait_for(lambda: kubectl("get", "jobs", "-o", "name", check=False).stdout.strip() == "", 120)
    finally:
        watch.stopping.set()
        watch.join(timeout=120)
    final = kubectl("get", "secrets,configmaps,jobs,pods", "-A", "-o", "yaml").stdout
    logs = kubectl("logs", "deploy/dr-diligence-reader").stdout
    pod = kubectl("get", "pods", "-l", "app.kubernetes.io/component=api", "-o", "jsonpath={.items[0].metadata.name}").stdout
    copied = tmp_path / name
    kubectl("cp", f"{pod}:/app/runs/{name}", str(copied))
    return {
        "events": found,
        "state": state,
        "exports": exports,
        "jobs": sorted(watch.jobs),
        "deleted": gone,
        "reads": watch.reads,
        "leaks": watch.leaks + (["final yaml"] if key in final else []) + (["api log"] if key in logs else []),
        "files_with_key": files_holding(copied, key),
    }


def test_a_run_on_kind_is_one_job_deleted_after_and_the_key_is_nowhere(cluster, tmp_path):
    found = run_on_kind(cluster, "northstar-dental", "refused-key", LIVE_BAD_KEY, tmp_path)
    RECORD["kind_refused_key"] = {key: found[key] for key in ("jobs", "deleted", "reads", "leaks")}

    assert found["events"][-1]["type"] == "RUN_ERROR"
    assert found["events"][-1]["code"] == "key-refused"
    assert len(found["jobs"]) == 1
    assert found["deleted"]
    assert found["reads"] > 0
    assert found["leaks"] == []
    assert found["files_with_key"] == []


@pytest.mark.skipif(not LIVE, reason="the kind run on a real key spends money; RLM_PACKAGE_LIVE=1")
def test_a_live_run_on_kind_recalls_every_planted_fact(cluster, tmp_path):
    key = os.environ["OPENROUTER_API_KEY"]
    found = run_on_kind(cluster, "northstar-dental", "northstar-dental", key, tmp_path)
    RECORD["kind_live"] = {
        "recall": found["state"]["recall"],
        "dollars": found["state"]["dollars"],
        **{key_: found[key_] for key_ in ("jobs", "deleted", "reads", "leaks", "exports")},
    }

    assert found["events"][-1]["type"] == "RUN_FINISHED", found["events"][-1]
    assert found["state"]["status"] == "done"
    assert found["state"]["recall"] == 100.0
    assert all(status == 200 for status in found["exports"].values())
    assert len(found["jobs"]) == 1
    assert found["deleted"]
    assert found["leaks"] == []
    assert found["files_with_key"] == []


def readout(terminalreporter):
    if RECORD:
        terminalreporter.write_line(f"phase 8 package: {json.dumps(RECORD)}")
