"""Issue #161: a model per task on the command line.

Every test here is free: the OpenRouter transport is a fake, the room is a copy of sample 3's,
the ledger is a temporary file, and no key is read. A fake that is asked for a call it should
not be asked for fails the test.
"""

import json
import threading

import httpx
import pytest

from rlm import cli, ingest, notes, settings, tree, write
from rlm.gateway import Gateway, price, register_listing
from test_phase8_command import FAKE_REPORT, copy_room, fake_note, reply, run_json, write_ledger

OPEN = "acme/real-model"
OPEN_SONNET = "anthropic/claude-sonnet-5.5"
CODE_SONNET = "claude-code/claude-sonnet-5-5"


class NoNetwork(httpx.MockTransport):
    """An OpenRouter transport that fails the test when anything reaches it."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        super().__init__(self._handle)

    def _handle(self, request):
        self.requests.append(request)
        raise AssertionError(f"a call reached OpenRouter: {request.url}")


def listing(*ids):
    """OpenRouter's model list carrying ids at 0.5 in and 2 out per million tokens."""
    return {
        "data": [
            {"id": id_, "pricing": {"prompt": "0.0000005", "completion": "0.000002"}, "context_length": 200000}
            for id_ in ids
        ]
    }


# ---------------------------------------------------------------- the flags


def test_a_model_for_each_task_and_a_settings_file_are_flags_and_default_to_none():
    args = cli.parse_args(["run", "room"])
    assert (args.notes_model, args.middle_model, args.writer_model, args.settings) == (None, None, None, None)
    args = cli.parse_args([
        "run", "room", "--notes-model", OPEN, "--middle-model", CODE_SONNET, "--writer-model", OPEN_SONNET,
        "--settings", "s.json",
    ])
    assert (args.notes_model, args.middle_model, args.writer_model) == (OPEN, CODE_SONNET, OPEN_SONNET)
    assert args.settings == "s.json"


@pytest.mark.parametrize("flag", [["--preset", "client"], ["--batch"], ["--region", "eu-west-1"]])
def test_there_is_no_preset_batch_or_region_flag(flag):
    with pytest.raises(SystemExit):
        cli.parse_args(["run", "room", *flag])


def args_of(*flags):
    return cli.parse_args(["run", "room", *flags])


def test_with_no_flags_and_nothing_saved_the_models_are_the_defaults_of_today():
    assert cli.resolve_settings(args_of()) == settings.default_settings(claude_code=False)


def test_the_saved_settings_are_what_a_run_with_no_flags_uses(tmp_path):
    settings.save_settings(settings.from_dict({"writer": "z-ai/glm-5.3-flash"}, settings.default_settings(False)))
    assert cli.resolve_settings(args_of()).writer == "z-ai/glm-5.3-flash"


def test_a_flag_replaces_the_saved_setting_of_its_task_alone(tmp_path):
    settings.save_settings(settings.from_dict({"writer": "z-ai/glm-5.3-flash", "notes": OPEN}, settings.default_settings(False)))
    found = cli.resolve_settings(args_of("--writer-model", OPEN_SONNET))
    assert (found.notes, found.writer) == (OPEN, OPEN_SONNET)


def test_a_settings_file_of_the_run_sits_over_the_saved_settings(tmp_path):
    settings.save_settings(settings.from_dict({"notes": OPEN}, settings.default_settings(False)))
    path = tmp_path / "models.json"
    path.write_text(json.dumps({"writer": OPEN_SONNET, "write": "both"}), encoding="utf-8")
    found = cli.resolve_settings(args_of("--settings", str(path)))
    assert (found.notes, found.writer, found.write) == (OPEN, OPEN_SONNET, "both")


def test_a_ranker_runs_no_group_step_whatever_the_saved_write_says():
    settings.save_settings(settings.CLAUDE_CODE_DEFAULTS)
    assert cli.resolve_settings(args_of("--rank", "llm")).write is None
    assert cli.resolve_settings(args_of()).write == "both-tree-first"


# ---------------------------------------------------------------- refused before any call


class ListingTransport(httpx.MockTransport):
    """An OpenRouter transport that lists OPEN and fails the test on any model call."""

    def __init__(self):
        self.gets: list[str] = []
        self.posts: list[dict] = []
        super().__init__(self._handle)

    def _handle(self, request):
        if request.method == "GET":
            self.gets.append(str(request.url))
            return httpx.Response(200, json=listing(OPEN))
        self.posts.append(json.loads(request.content))
        raise AssertionError("a model call was made")


@pytest.mark.parametrize(
    "flags, named",
    [
        (["--writer-model", "acme/not-a-model"], "acme/not-a-model"),
        (["--notes-model", "acme/not-a-model"], "acme/not-a-model"),
        (["--write", "tree", "--middle-model", "acme/not-a-model"], "acme/not-a-model"),
        (["--notes-model", "anthropic/claude-haiku-9"], "anthropic/claude-haiku-9"),
        (["--writer-model", "bedrock/claude-sonnet-5-5"], "bedrock/claude-sonnet-5-5"),
    ],
)
def test_an_id_open_router_does_not_list_is_refused_with_its_name_before_any_call(tmp_path, capsys, flags, named):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    transport = ListingTransport()
    ledger = write_ledger(tmp_path / "L.md")
    code = cli.main(
        ["run", str(room), "--out", str(run_dir), "--yes", "--phase", "8", *flags],
        gateway=Gateway(api_key="k", transport=transport, rate_limit_waits=()),
        ledger=ledger,
    )

    assert code == 1
    assert named in capsys.readouterr().out
    assert transport.gets and not transport.posts
    state = run_json(run_dir)
    assert (state["status"], state["code"]) == ("failed", "unknown-model")
    assert len(ledger.rows()) == 1


def test_an_unknown_claude_code_id_is_refused_without_asking_open_router_anything(tmp_path, capsys):
    room = copy_room(tmp_path)
    network = NoNetwork()
    code = cli.main(
        ["run", str(room), "--out", str(tmp_path / "run"), "--yes", "--write", "tree",
         "--middle-model", "claude-code/claude-opus-9"],
        gateway=Gateway(api_key="k", transport=network, rate_limit_waits=()),
    )
    assert code == 1
    assert "claude-code/claude-opus-9" in capsys.readouterr().out
    assert not network.requests
    assert run_json(tmp_path / "run")["code"] == "unknown-model"


def test_a_run_on_open_router_with_no_key_stops_on_a_refused_key_before_any_call(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    room = copy_room(tmp_path)
    code = cli.main(["run", str(room), "--out", str(tmp_path / "run"), "--yes"])
    assert code == 1
    assert "OPENROUTER_API_KEY" in capsys.readouterr().out
    assert run_json(tmp_path / "run")["code"] == "key-refused"


def test_a_run_whose_models_are_all_on_claude_code_needs_no_open_router_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    room = copy_room(tmp_path)
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    # the run is declined at the estimate: it got as far as the question without a key it does not need
    code = cli.main(
        ["run", str(room), "--out", str(tmp_path / "run"), "--notes-model", CODE_SONNET, "--writer-model", CODE_SONNET]
    )
    assert code == 1
    assert run_json(tmp_path / "run")["code"] == "declined"


# ---------------------------------------------------------------- the estimate prices each task by its model


def ingested(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    ingest.ingest(room, run_dir)
    return room, run_dir


def test_the_estimate_prices_each_task_at_its_own_models_rate(tmp_path):
    room, run_dir = ingested(tmp_path)
    register_listing({OPEN: (0.5, 2.0)})
    chosen = settings.Settings(notes=OPEN, group=CODE_SONNET, writer=write.DEFAULT_MODEL, write="both-tree-first")
    found = cli.estimate(room, run_dir, True, True, chosen=chosen)

    n = found.notes_tokens
    assert found.tasks["notes"]["model"] == OPEN
    assert found.tasks["notes"]["dollars"] == pytest.approx(
        price(OPEN, round(n * cli.NOTES_BILLED_IN), round(n * cli.NOTES_BILLED_OUT))
    )
    assert found.tasks["notes"]["dollars"] > 0
    # a Claude Code task costs nothing in cash
    assert found.tasks["group"] == {"model": CODE_SONNET, "dollars": 0.0}
    assert found.tasks["writer"]["model"] == write.DEFAULT_MODEL and found.tasks["writer"]["dollars"] > 0
    assert found.dollars == pytest.approx(sum(task["dollars"] for task in found.tasks.values()))


def test_the_estimate_leaves_out_the_group_step_when_the_report_is_built_without_the_tree(tmp_path):
    room, run_dir = ingested(tmp_path)
    found = cli.estimate(room, run_dir, True, True, chosen=settings.default_settings(claude_code=False))
    assert "group" not in found.tasks
    assert found.tasks["notes"]["model"] == notes.DEFAULT_MODEL
    assert found.tasks["writer"]["model"] == write.DEFAULT_MODEL


def test_the_estimate_line_names_the_model_of_each_task_and_its_dollars(tmp_path, capsys):
    room, run_dir = ingested(tmp_path)
    found = cli.estimate(room, run_dir, True, True, chosen=settings.default_settings(claude_code=True))
    cli.confirm(found, yes=True)
    printed = capsys.readouterr().out
    assert printed.startswith("estimate:")
    for model in (notes.DEFAULT_MODEL, CODE_SONNET):
        assert model in printed
    assert "for the group step" in printed


# ---------------------------------------------------------------- a run on one model of the user's choice


class OneModelTransport(httpx.MockTransport):
    """Lists the ids given and answers every call: a note for a notes request, FAKE_REPORT for
    the rest. Every request body is recorded."""

    def __init__(self, *listed):
        self.listed_ids = listed or (OPEN,)
        self.bodies: list[dict] = []
        self.listed = 0
        self._lock = threading.Lock()
        super().__init__(self._handle)

    @property
    def models(self) -> list[str]:
        return [body["model"] for body in self.bodies]

    def _handle(self, request):
        if request.method == "GET":
            self.listed += 1
            return httpx.Response(200, json=listing(*self.listed_ids))
        body = json.loads(request.content)
        with self._lock:
            self.bodies.append(body)
        if body["messages"][0]["content"].startswith(notes.SYSTEM_PROMPT[:60]):
            return httpx.Response(200, json=reply(fake_note(body), 1000, 200))
        return httpx.Response(200, json=reply(FAKE_REPORT, 20000, 5000))


def test_all_three_tasks_on_one_open_router_model_of_the_users_choice_complete_and_are_written_into_run_json(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    transport = OneModelTransport()
    ledger = write_ledger(tmp_path / "L.md")
    code = cli.main(
        ["run", str(room), "--out", str(run_dir), "--yes", "--phase", "8",
         "--notes-model", OPEN, "--middle-model", OPEN, "--writer-model", OPEN],
        gateway=Gateway(api_key="k", transport=transport, rate_limit_waits=()),
        ledger=ledger,
    )

    state = run_json(run_dir)
    assert code == 0, state
    assert set(transport.models) == {OPEN}
    assert transport.listed == 1
    assert state["models"] == {"notes": OPEN, "group": OPEN, "writer": OPEN, "write": None}
    assert {row["model"] for row in ledger.rows()[1:]} == {OPEN}
    # priced from the live list: 0.5 in and 2 out per million
    assert state["dollars"] > 0
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert report.splitlines()[0] == f"Models: notes {OPEN}, group step not run, writer {OPEN}."


def test_sonnet_picked_through_open_router_is_sent_there_at_medium_effort(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    transport = OneModelTransport(OPEN_SONNET)
    code = cli.main(
        ["run", str(room), "--out", str(run_dir), "--yes", "--writer-model", OPEN_SONNET],
        gateway=Gateway(api_key="k", transport=transport, rate_limit_waits=()),
    )

    assert code == 0, run_json(run_dir)
    writer_calls = [body for body in transport.bodies if body["model"] == OPEN_SONNET]
    assert writer_calls
    assert all(body["reasoning"] == {"effort": "medium"} for body in writer_calls)
    assert run_json(run_dir)["models"]["writer"] == OPEN_SONNET


def test_a_default_run_writes_its_models_into_run_json_and_opens_its_report_with_them(tmp_path):
    from test_phase8_command import RoomTransport, gateway_for

    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    code = cli.main(["run", str(room), "--out", str(run_dir), "--yes"], gateway=gateway_for(RoomTransport()))
    assert code == 0
    assert run_json(run_dir)["models"]["notes"] == notes.DEFAULT_MODEL
    assert run_json(run_dir)["models"]["writer"] == write.DEFAULT_MODEL
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert report.splitlines()[0] == (
        f"Models: notes {notes.DEFAULT_MODEL}, group step not run, writer {write.DEFAULT_MODEL}."
    )


def test_a_user_run_without_a_phase_counts_its_dollars_in_run_json(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    code = cli.main(
        ["run", str(room), "--out", str(run_dir), "--yes", "--notes-model", OPEN, "--writer-model", OPEN],
        gateway=Gateway(api_key="k", transport=OneModelTransport(), rate_limit_waits=()),
    )
    assert code == 0
    assert run_json(run_dir)["dollars"] > 0


def test_the_stage_commands_default_to_the_same_models_as_the_settings():
    assert notes.parse_args(["room", "run"]).model == settings.OPEN_DEFAULTS.notes
    assert tree.parse_args(["room", "run"]).model == settings.OPEN_DEFAULTS.group
    assert write.parse_args(["room", "run"]).model == settings.OPEN_DEFAULTS.writer
    with pytest.raises(SystemExit):
        notes.parse_args(["room", "run", "--batch"])
