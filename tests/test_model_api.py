"""Issue #161: a model per task on the local API and the page's server side.

Every test here is free. The runner is a fake that records what it is asked to start, so no run
begins and no key leaves this process; OpenRouter's model list is a function the test hands the
app. The room is sample 3's, uploaded the way a browser sends a folder.
"""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.runner import LocalRunner
from rlm import settings
from test_phase8_api import GOOD_KEY, room_files

HAIKU = "anthropic/claude-haiku-4-5"
SONNET = "anthropic/claude-sonnet-5-5"
ANTHROPIC_KEY = "sk-ant-test-ANTHROPICKEY-0123456789"
LISTED = {"acme/real-model": (0.5, 2.0)}


class RecordingRunner:
    """Records every start; says a run is running until it is cancelled."""

    router = None

    def __init__(self):
        self.starts: list[dict] = []
        self.running: set[str] = set()

    def start(self, run_id, room, run_dir, key, extra_env=None):
        self.starts.append({"id": run_id, "key": key, "extra_env": dict(extra_env or {}), "run_dir": Path(run_dir)})
        self.running.add(run_id)

    def status(self, run_id):
        return "running" if run_id in self.running else "none"

    def cancel(self, run_id):
        self.running.discard(run_id)


@pytest.fixture
def api(tmp_path):
    runner = RecordingRunner()
    app = create_app(runner=runner, runs_root=tmp_path / "runs", web_dir=tmp_path / "noweb")
    app.state.listing = lambda: dict(LISTED)
    with TestClient(app) as client:
        client.runner = runner
        client.runs = tmp_path / "runs"
        client.app_ = app
        yield client


def upload(client, tmp_path, models=None, openrouter=GOOD_KEY, anthropic=None, name=None):
    headers = {}
    if openrouter is not None:
        headers["X-OpenRouter-Key"] = openrouter
    if anthropic is not None:
        headers["X-Anthropic-Key"] = anthropic
    data = {}
    if models is not None:
        data["models"] = json.dumps(models)
    if name is not None:
        data["name"] = name
    return client.post("/runs", files=room_files(tmp_path), data=data, headers=headers)


# ---------------------------------------------------------------- the saved settings


def test_the_settings_are_the_defaults_until_some_are_saved_and_carry_what_the_page_offers(api):
    found = api.get("/api/settings").json()
    assert found["settings"] == settings.default_settings(claude_code=False).to_dict()
    assert found["claude_code"] is False
    assert found["presets"]["client"] == settings.preset("client").to_dict()
    assert found["presets"]["default"] == settings.default_settings(claude_code=False).to_dict()
    choices = found["choices"]
    assert "anthropic/claude-haiku-4-5" in choices and "bedrock/claude-sonnet-5-5" in choices
    assert "z-ai/glm-5.3-flash" in choices
    assert "claude-code/claude-sonnet-5-5" not in choices
    assert found["needs"] == {"openrouter": True, "anthropic": False, "bedrock": False}


def test_a_put_saves_the_settings_on_this_machine_and_a_new_server_reads_them_back(api, tmp_path):
    client_preset = settings.preset("client").to_dict()
    response = api.put("/api/settings", json=client_preset)
    assert response.status_code == 200, response.text
    assert response.json()["settings"] == client_preset
    assert response.json()["needs"] == {"openrouter": False, "anthropic": True, "bedrock": False}
    assert api.get("/api/settings").json()["settings"] == client_preset

    saved = json.loads(settings.settings_path().read_text(encoding="utf-8"))
    assert saved["writer"] == SONNET and saved["batch"] is True

    other = create_app(runner=RecordingRunner(), runs_root=tmp_path / "other", web_dir=tmp_path / "noweb")
    with TestClient(other) as second:
        assert second.get("/api/settings").json()["settings"] == client_preset


def test_a_put_may_name_some_fields_and_keeps_the_rest(api):
    api.put("/api/settings", json=settings.preset("client").to_dict())
    found = api.put("/api/settings", json={"writer": "bedrock/claude-sonnet-5-5", "region": "eu-west-1", "preset": None}).json()
    assert found["settings"]["writer"] == "bedrock/claude-sonnet-5-5"
    assert found["settings"]["notes"] == HAIKU
    assert found["settings"]["region"] == "eu-west-1"


@pytest.mark.parametrize("body, named", [
    ({"writer": "bedrock/claude-opus-9"}, "bedrock/claude-opus-9"),
    ({"notes": "acme/not-a-model"}, "acme/not-a-model"),
    ({"notes": HAIKU, "write": "tree", "group": "anthropic/claude-haiku-9"}, "anthropic/claude-haiku-9"),
])
def test_an_unknown_id_is_refused_with_its_name_and_nothing_is_saved(api, body, named):
    before = api.get("/api/settings").json()["settings"]
    response = api.put("/api/settings", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "unknown-model"
    assert named in response.json()["message"]
    assert api.get("/api/settings").json()["settings"] == before
    assert not settings.settings_path().exists()


def test_an_open_router_id_is_accepted_when_the_list_carries_it(api):
    response = api.put("/api/settings", json={"writer": "acme/real-model"})
    assert response.status_code == 200
    assert response.json()["settings"]["writer"] == "acme/real-model"


def test_a_setting_that_cannot_run_is_refused_on_its_own_code(api):
    response = api.put("/api/settings", json={"batch": True})
    assert (response.status_code, response.json()["code"]) == (422, "bad-settings")
    response = api.put("/api/settings", json={"write": "everything"})
    assert (response.status_code, response.json()["code"]) == (422, "bad-settings")


def test_claude_code_is_refused_when_the_machine_has_none(api):
    response = api.put("/api/settings", json={"writer": "claude-code/claude-sonnet-5-5"})
    assert response.status_code == 422 and "Claude Code" in response.json()["message"]


def test_claude_code_is_offered_and_defaulted_when_the_machine_has_it(api, monkeypatch):
    monkeypatch.delenv("RLM_CLAUDE_CODE")
    monkeypatch.setattr("rlm.settings.shutil.which", lambda name: "/usr/bin/claude")
    found = api.get("/api/settings").json()
    assert found["claude_code"] is True
    assert "claude-code/claude-sonnet-5-5" in found["choices"]
    assert found["settings"]["writer"] == "claude-code/claude-sonnet-5-5"
    assert found["settings"]["write"] == "both-tree-first"
    assert api.put("/api/settings", json={"writer": "claude-code/claude-sonnet-5-5"}).status_code == 200


# ---------------------------------------------------------------- a run takes the models and the keys they need


def test_an_upload_writes_the_models_into_the_run_folder(api, tmp_path):
    api.put("/api/settings", json=settings.preset("client").to_dict())
    response = upload(api, tmp_path, openrouter=None, anthropic=ANTHROPIC_KEY, name="client-room")
    assert response.status_code == 201, response.text
    written = json.loads((api.runs / "client-room" / "models.json").read_text(encoding="utf-8"))
    assert written == settings.preset("client").to_dict()


def test_the_models_an_upload_names_win_over_the_saved_settings_and_are_checked(api, tmp_path):
    chosen = {"notes": HAIKU, "writer": SONNET, "write": None, "batch": False}
    response = upload(api, tmp_path, models=chosen, openrouter=None, anthropic=ANTHROPIC_KEY, name="mine")
    assert response.status_code == 201, response.text
    written = json.loads((api.runs / "mine" / "models.json").read_text(encoding="utf-8"))
    assert (written["notes"], written["writer"], written["write"]) == (HAIKU, SONNET, None)

    refused = upload(api, tmp_path, models={"writer": "bedrock/claude-opus-9"}, name="bad")
    assert refused.status_code == 422 and refused.json()["code"] == "unknown-model"
    assert not (api.runs / "bad").exists()


def test_an_upload_needs_only_the_keys_its_models_call_for(api, tmp_path):
    api.put("/api/settings", json=settings.preset("client").to_dict())
    refused = upload(api, tmp_path, openrouter=GOOD_KEY, anthropic=None)
    assert refused.status_code == 400 and refused.json()["code"] == "key-missing"
    assert "Anthropic" in refused.json()["message"]
    assert upload(api, tmp_path, openrouter=None, anthropic=ANTHROPIC_KEY).status_code == 201

    api.put("/api/settings", json=settings.default_settings(False).to_dict())
    refused = upload(api, tmp_path, openrouter=None, anthropic=ANTHROPIC_KEY)
    assert refused.status_code == 400 and refused.json()["code"] == "key-missing"
    assert "OpenRouter" in refused.json()["message"]


def test_a_confirm_hands_the_runner_each_key_and_none_of_them_reaches_a_file(api, tmp_path):
    api.put("/api/settings", json=settings.from_dict({"notes": "z-ai/glm-5.3-flash", "writer": SONNET}, settings.default_settings(False)).to_dict())
    made = upload(api, tmp_path, openrouter=GOOD_KEY, anthropic=ANTHROPIC_KEY, name="both-keys")
    assert made.status_code == 201, made.text
    assert api.post("/runs/both-keys/confirm").status_code == 202

    start = api.runner.starts[0]
    assert start["key"] == GOOD_KEY
    assert start["extra_env"] == {"ANTHROPIC_API_KEY": ANTHROPIC_KEY}
    for path in (api.runs / "both-keys").rglob("*"):
        if path.is_file() and path.suffix in (".json", ".txt", ".log", ".jsonl", ".md"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert GOOD_KEY not in text and ANTHROPIC_KEY not in text, path


def test_a_client_run_needs_no_open_router_key_at_confirm(api, tmp_path):
    api.put("/api/settings", json=settings.preset("client").to_dict())
    assert upload(api, tmp_path, openrouter=None, anthropic=ANTHROPIC_KEY, name="c1").status_code == 201
    assert api.post("/runs/c1/confirm").status_code == 202
    assert api.runner.starts[0]["extra_env"] == {"ANTHROPIC_API_KEY": ANTHROPIC_KEY}


def test_a_confirm_with_the_anthropic_key_missing_is_refused(api, tmp_path):
    api.put("/api/settings", json=settings.preset("client").to_dict())
    upload(api, tmp_path, openrouter=None, anthropic=ANTHROPIC_KEY, name="c2")
    api.app_.state.anthropic_keys.pop("c2")
    response = api.post("/runs/c2/confirm")
    assert response.status_code == 400 and response.json()["code"] == "key-missing"
    assert not api.runner.starts


def test_the_models_of_a_run_can_be_changed_before_it_starts_and_not_after(api, tmp_path):
    upload(api, tmp_path, openrouter=GOOD_KEY, name="r1")
    response = api.put("/runs/r1/models", json={"writer": "acme/real-model"})
    assert response.status_code == 200, response.text
    written = json.loads((api.runs / "r1" / "models.json").read_text(encoding="utf-8"))
    assert written["writer"] == "acme/real-model"
    assert api.put("/runs/r1/models", json={"writer": "acme/not-a-model"}).status_code == 422

    api.post("/runs/r1/confirm")
    assert api.put("/runs/r1/models", json={"writer": "z-ai/glm-5.3"}).status_code == 409


def test_the_estimate_prices_each_task_at_the_model_of_the_run(api, tmp_path):
    api.put("/api/settings", json=settings.preset("client").to_dict())
    upload(api, tmp_path, openrouter=None, anthropic=ANTHROPIC_KEY, name="e1")
    found = api.get("/runs/e1/estimate").json()
    assert found["notes_model"] == HAIKU
    assert found["group_model"] == SONNET
    assert found["write_model"] == SONNET
    assert found["batch"] is True
    assert set(found["tasks"]) == {"notes", "group", "writer"}
    assert found["dollars"] == pytest.approx(sum(task["dollars"] for task in found["tasks"].values()))
    assert found["tasks"]["notes"]["model"] == HAIKU


# ---------------------------------------------------------------- the local runner


def test_the_command_a_run_starts_carries_the_runs_settings_file(tmp_path):
    runner = LocalRunner(["prefix"])
    room, run_dir = tmp_path / "room", tmp_path / "run"
    run_dir.mkdir()
    plain = ["prefix", "run", str(room), "--out", str(run_dir), "--yes"]
    assert runner.argv(room, run_dir) == plain
    (run_dir / "models.json").write_text("{}", encoding="utf-8")
    assert runner.argv(room, run_dir) == [*plain, "--settings", str(run_dir / "models.json")]


def test_each_key_reaches_the_child_in_its_environment_alone(tmp_path):
    seen = tmp_path / "seen.txt"
    probe = (
        "import os, pathlib; "
        f"pathlib.Path({str(seen)!r}).write_text(os.environ.get('OPENROUTER_API_KEY', 'none') + ' ' "
        "+ os.environ.get('ANTHROPIC_API_KEY', 'none'))"
    )
    runner = LocalRunner([sys.executable, "-c", probe])
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    runner.start("k1", tmp_path / "room", run_dir, "", extra_env={"ANTHROPIC_API_KEY": ANTHROPIC_KEY})
    runner.processes["k1"].wait(timeout=60)
    assert seen.read_text().split()[1] == ANTHROPIC_KEY
    assert ANTHROPIC_KEY not in "".join(p.read_text(errors="ignore") for p in run_dir.rglob("*") if p.is_file())


# ---------------------------------------------------------------- the page


def test_the_page_has_a_model_for_each_task_a_preset_a_batch_box_a_region_and_an_anthropic_key():
    html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    for element in ("model-notes", "model-group", "model-writer", "preset", "batch", "region", "anthropic-key-input", "settings-state"):
        assert f'id="{element}"' in html, element
    script = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    assert "/api/settings" in script and "X-Anthropic-Key" in script
    # the keys live in variables, never in the browser's storage
    assert "localStorage.setItem(\"anthropic" not in script.lower()
