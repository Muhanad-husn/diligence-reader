"""Issue #161: a model per task on the local API and the page's server side.

Every test here is free. The runner is a fake that records what it is asked to start, so no run
begins and no key leaves this process; OpenRouter's model list is a function the test hands the
app. The room is sample 3's, uploaded the way a browser sends a folder.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.runner import LocalRunner
from rlm import settings
from test_phase8_api import GOOD_KEY, room_files

OPEN = "acme/real-model"
OPEN_SONNET = "anthropic/claude-sonnet-5.5"
CODE_SONNET = "claude-code/claude-sonnet-5-5"
CODE_HAIKU = "claude-code/claude-haiku-5-5"
LISTED = {OPEN: (0.5, 2.0), OPEN_SONNET: (2.0, 10.0)}


class RecordingRunner:
    """Records every start; says a run is running until it is cancelled."""

    router = None

    def __init__(self):
        self.starts: list[dict] = []
        self.running: set[str] = set()

    def start(self, run_id, room, run_dir, key):
        self.starts.append({"id": run_id, "key": key, "run_dir": Path(run_dir)})
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


@pytest.fixture
def with_claude_code(monkeypatch):
    monkeypatch.delenv("RLM_CLAUDE_CODE")
    monkeypatch.setattr("rlm.settings.shutil.which", lambda name: "/usr/bin/claude")


def upload(client, tmp_path, models=None, openrouter=GOOD_KEY, name=None):
    headers = {}
    if openrouter is not None:
        headers["X-OpenRouter-Key"] = openrouter
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
    assert found["defaults"] == settings.default_settings(claude_code=False).to_dict()
    assert found["claude_code"] is False
    choices = found["choices"]
    assert "z-ai/glm-5.3-flash" in choices and OPEN_SONNET in choices
    assert CODE_SONNET not in choices and CODE_HAIKU not in choices
    assert not any(choice.startswith("bedrock/") for choice in choices)
    assert found["needs_key"] is True
    assert "presets" not in found and "regions" not in found


def test_a_put_saves_the_settings_on_this_machine_and_a_new_server_reads_them_back(api, tmp_path):
    chosen = {"notes": OPEN, "group": OPEN_SONNET, "writer": OPEN_SONNET, "write": "both-tree-first"}
    response = api.put("/api/settings", json=chosen)
    assert response.status_code == 200, response.text
    assert response.json()["settings"] == chosen
    assert api.get("/api/settings").json()["settings"] == chosen

    saved = json.loads(settings.settings_path().read_text(encoding="utf-8"))
    assert saved == chosen

    other = create_app(runner=RecordingRunner(), runs_root=tmp_path / "other", web_dir=tmp_path / "noweb")
    with TestClient(other) as second:
        assert second.get("/api/settings").json()["settings"] == chosen


def test_a_put_may_name_some_fields_and_keeps_the_rest(api):
    api.put("/api/settings", json={"notes": OPEN, "writer": OPEN})
    found = api.put("/api/settings", json={"writer": OPEN_SONNET}).json()
    assert found["settings"]["writer"] == OPEN_SONNET
    assert found["settings"]["notes"] == OPEN


@pytest.mark.parametrize("body, named", [
    ({"writer": "bedrock/claude-sonnet-5-5"}, "bedrock/claude-sonnet-5-5"),
    ({"notes": "acme/not-a-model"}, "acme/not-a-model"),
    ({"write": "tree", "group": "anthropic/claude-haiku-9"}, "anthropic/claude-haiku-9"),
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
    response = api.put("/api/settings", json={"writer": OPEN})
    assert response.status_code == 200
    assert response.json()["settings"]["writer"] == OPEN


def test_a_setting_that_cannot_run_is_refused_on_its_own_code(api):
    response = api.put("/api/settings", json={"write": "everything"})
    assert (response.status_code, response.json()["code"]) == (422, "bad-settings")
    response = api.put("/api/settings", json={"notes": " "})
    assert (response.status_code, response.json()["code"]) == (422, "bad-settings")


def test_claude_code_is_refused_when_the_machine_has_none(api):
    response = api.put("/api/settings", json={"writer": CODE_SONNET})
    assert response.status_code == 422 and "Claude Code" in response.json()["message"]


def test_claude_code_is_offered_and_defaulted_when_the_machine_has_it(api, with_claude_code):
    found = api.get("/api/settings").json()
    assert found["claude_code"] is True
    assert CODE_SONNET in found["choices"] and CODE_HAIKU in found["choices"]
    assert found["settings"]["notes"] == CODE_HAIKU
    assert found["settings"]["writer"] == CODE_SONNET
    assert found["settings"]["write"] == "both-tree-first"
    assert api.put("/api/settings", json={"writer": CODE_SONNET}).status_code == 200


# ---------------------------------------------------------------- a run takes the models and the key they need


def test_an_upload_writes_the_models_into_the_run_folder(api, tmp_path):
    chosen = {"notes": OPEN, "group": OPEN, "writer": OPEN_SONNET, "write": "tree"}
    api.put("/api/settings", json=chosen)
    response = upload(api, tmp_path, name="my-room")
    assert response.status_code == 201, response.text
    written = json.loads((api.runs / "my-room" / "models.json").read_text(encoding="utf-8"))
    assert written == chosen


def test_the_models_an_upload_names_win_over_the_saved_settings_and_are_checked(api, tmp_path):
    chosen = {"notes": OPEN, "writer": OPEN_SONNET, "write": None}
    response = upload(api, tmp_path, models=chosen, name="mine")
    assert response.status_code == 201, response.text
    written = json.loads((api.runs / "mine" / "models.json").read_text(encoding="utf-8"))
    assert (written["notes"], written["writer"], written["write"]) == (OPEN, OPEN_SONNET, None)

    refused = upload(api, tmp_path, models={"writer": "anthropic/claude-haiku-9"}, name="bad")
    assert refused.status_code == 422 and refused.json()["code"] == "unknown-model"
    assert not (api.runs / "bad").exists()


def test_an_upload_needs_the_key_only_when_a_task_runs_on_open_router(api, tmp_path, with_claude_code):
    refused = upload(api, tmp_path, models={"notes": "z-ai/glm-5.3-flash"}, openrouter=None)
    assert refused.status_code == 400 and refused.json()["code"] == "key-missing"
    assert "OpenRouter" in refused.json()["message"]

    on_code = {"notes": CODE_SONNET, "group": CODE_SONNET, "writer": CODE_SONNET, "write": "tree"}
    made = upload(api, tmp_path, models=on_code, openrouter=None, name="on-code")
    assert made.status_code == 201, made.text
    assert api.post("/runs/on-code/confirm").status_code == 202
    assert api.runner.starts[0]["key"] == ""


def test_a_confirm_hands_the_runner_the_key_and_it_reaches_no_file(api, tmp_path):
    made = upload(api, tmp_path, models={"writer": OPEN_SONNET}, name="one-key")
    assert made.status_code == 201, made.text
    assert api.post("/runs/one-key/confirm").status_code == 202

    assert api.runner.starts[0]["key"] == GOOD_KEY
    for path in (api.runs / "one-key").rglob("*"):
        if path.is_file() and path.suffix in (".json", ".txt", ".log", ".jsonl", ".md"):
            assert GOOD_KEY not in path.read_text(encoding="utf-8", errors="ignore"), path


def test_the_models_of_a_run_can_be_changed_before_it_starts_and_not_after(api, tmp_path):
    upload(api, tmp_path, name="r1")
    response = api.put("/runs/r1/models", json={"writer": OPEN})
    assert response.status_code == 200, response.text
    written = json.loads((api.runs / "r1" / "models.json").read_text(encoding="utf-8"))
    assert written["writer"] == OPEN
    assert api.put("/runs/r1/models", json={"writer": "acme/not-a-model"}).status_code == 422

    api.post("/runs/r1/confirm")
    assert api.put("/runs/r1/models", json={"writer": "z-ai/glm-5.3"}).status_code == 409


def test_the_estimate_prices_each_task_at_the_model_of_the_run(api, tmp_path):
    api.put("/api/settings", json={"notes": OPEN, "group": OPEN_SONNET, "writer": OPEN_SONNET, "write": "tree"})
    upload(api, tmp_path, name="e1")
    found = api.get("/runs/e1/estimate").json()
    assert found["notes_model"] == OPEN
    assert found["group_model"] == OPEN_SONNET
    assert found["write_model"] == OPEN_SONNET
    assert set(found["tasks"]) == {"notes", "group", "writer"}
    assert all(task["dollars"] > 0 for task in found["tasks"].values())
    assert found["dollars"] == pytest.approx(sum(task["dollars"] for task in found["tasks"].values()))
    assert "batch" not in found


# ---------------------------------------------------------------- the local runner


def test_the_command_a_run_starts_carries_the_runs_settings_file(tmp_path):
    runner = LocalRunner(["prefix"])
    room, run_dir = tmp_path / "room", tmp_path / "run"
    run_dir.mkdir()
    plain = ["prefix", "run", str(room), "--out", str(run_dir), "--yes"]
    assert runner.argv(room, run_dir) == plain
    (run_dir / "models.json").write_text("{}", encoding="utf-8")
    assert runner.argv(room, run_dir) == [*plain, "--settings", str(run_dir / "models.json")]


# ---------------------------------------------------------------- the page


def test_the_page_has_a_model_for_each_task_and_the_way_the_report_is_built():
    html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    for element in ("model-notes", "model-group", "model-writer", "write-mode", "settings-save", "settings-state"):
        assert f'id="{element}"' in html, element
    for element in ("preset", "batch", "region", "anthropic-key-input"):
        assert f'id="{element}"' not in html, element
    script = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    assert "/api/settings" in script
    assert "X-Anthropic-Key" not in script
