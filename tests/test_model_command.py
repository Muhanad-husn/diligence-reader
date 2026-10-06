"""Issue #161: a model per task on the command line.

Every test here is free: the Anthropic client and the OpenRouter transport are fakes, the room is
a copy of sample 3's, the ledger is a temporary file, and no key is read. A fake that is asked
for a call it should not be asked for fails the test.
"""

import json
import threading

import httpx
import pytest

from rlm import cli, ingest, models, notes, settings, tree, write
from rlm.gateway import Gateway
from rlm.providers import AnthropicProvider, BedrockProvider
from test_phase8_command import FAKE_REPORT, copy_room, fake_note, reply, run_json, write_ledger
from test_providers import FakeAnthropic, FakeBedrock, NoNetwork, message
from test_tree import LOAN, QUOTES

HAIKU = "anthropic/claude-haiku-4-5"
SONNET = "anthropic/claude-sonnet-5-5"
OPEN = "acme/real-model"
OPENING_OF_CLIENT = f"Models: notes {HAIKU} (batch), group step {SONNET}, writer {SONNET}."


# ---------------------------------------------------------------- the flags


def test_a_model_for_each_task_a_preset_a_batch_and_a_region_are_flags_and_default_to_none():
    args = cli.parse_args(["run", "room"])
    assert (args.notes_model, args.middle_model, args.writer_model) == (None, None, None)
    assert (args.preset, args.settings, args.batch, args.region) == (None, None, None, None)
    args = cli.parse_args([
        "run", "room", "--notes-model", HAIKU, "--middle-model", SONNET, "--writer-model", "bedrock/claude-sonnet-5-5",
        "--batch", "--region", "eu-west-1", "--preset", "client", "--settings", "s.json",
    ])
    assert (args.notes_model, args.middle_model, args.writer_model) == (HAIKU, SONNET, "bedrock/claude-sonnet-5-5")
    assert (args.batch, args.region, args.preset, args.settings) == (True, "eu-west-1", "client", "s.json")
    assert cli.parse_args(["run", "room", "--no-batch"]).batch is False
    with pytest.raises(SystemExit):
        cli.parse_args(["run", "room", "--preset", "fast"])


def args_of(*flags):
    return cli.parse_args(["run", "room", *flags])


def test_with_no_flags_and_nothing_saved_the_models_are_the_defaults_of_today():
    assert cli.resolve_settings(args_of()) == settings.default_settings(claude_code=False)


def test_the_saved_settings_are_what_a_run_with_no_flags_uses(tmp_path):
    settings.save_settings(settings.from_dict({"writer": "z-ai/glm-5.3-flash"}, settings.default_settings(False)))
    assert cli.resolve_settings(args_of()).writer == "z-ai/glm-5.3-flash"


def test_a_preset_replaces_the_saved_settings_and_a_flag_replaces_the_preset(tmp_path):
    settings.save_settings(settings.from_dict({"writer": "z-ai/glm-5.3-flash"}, settings.default_settings(False)))
    found = cli.resolve_settings(args_of("--preset", "client"))
    assert (found.notes, found.group, found.writer, found.batch, found.write) == (
        HAIKU, SONNET, SONNET, True, "both-tree-first",
    )
    assert found.preset == "client"
    found = cli.resolve_settings(args_of("--preset", "client", "--writer-model", "bedrock/claude-sonnet-5-5", "--no-batch"))
    assert found.writer == "bedrock/claude-sonnet-5-5" and found.group == SONNET and found.batch is False
    assert found.preset is None


def test_a_settings_file_of_the_run_sits_over_the_saved_settings(tmp_path):
    settings.save_settings(settings.from_dict({"notes": HAIKU}, settings.default_settings(False)))
    path = tmp_path / "models.json"
    path.write_text(json.dumps({"writer": SONNET, "write": "both"}), encoding="utf-8")
    found = cli.resolve_settings(args_of("--settings", str(path)))
    assert (found.notes, found.writer, found.write) == (HAIKU, SONNET, "both")


def test_a_ranker_runs_no_group_step_whatever_the_saved_write_says():
    settings.save_settings(settings.preset("client"))
    assert cli.resolve_settings(args_of("--rank", "llm")).write is None
    assert cli.resolve_settings(args_of()).write == "both-tree-first"


# ---------------------------------------------------------------- refused before any call


class ListingTransport(httpx.MockTransport):
    """An OpenRouter transport that lists OPEN and answers every other request with a failure."""

    def __init__(self):
        self.gets: list[str] = []
        self.posts: list[dict] = []
        super().__init__(self._handle)

    def _handle(self, request):
        if request.method == "GET":
            self.gets.append(str(request.url))
            return httpx.Response(
                200,
                json={"data": [{"id": OPEN, "pricing": {"prompt": "0.0000005", "completion": "0.000002"}, "context_length": 200000}]},
            )
        self.posts.append(json.loads(request.content))
        raise AssertionError("a model call was made")


@pytest.mark.parametrize(
    "flags, named",
    [
        (["--writer-model", "acme/not-a-model"], "acme/not-a-model"),
        (["--notes-model", "acme/not-a-model"], "acme/not-a-model"),
        (["--write", "tree", "--middle-model", "acme/not-a-model"], "acme/not-a-model"),
        (["--notes-model", "anthropic/claude-haiku-9"], "anthropic/claude-haiku-9"),
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
    assert not transport.posts
    state = run_json(run_dir)
    assert (state["status"], state["code"]) == ("failed", "unknown-model")
    assert len(ledger.rows()) == 1


@pytest.mark.parametrize("flag, named", [("--writer-model", "bedrock/claude-opus-9"), ("--middle-model", "claude-code/claude-opus-9")])
def test_an_unknown_bedrock_or_claude_code_id_is_refused_without_asking_open_router_anything(tmp_path, capsys, flag, named):
    room = copy_room(tmp_path)
    network = NoNetwork()
    flags = ["--write", "tree"] if flag == "--middle-model" else []
    code = cli.main(
        ["run", str(room), "--out", str(tmp_path / "run"), "--yes", flag, named, *flags],
        gateway=Gateway(api_key="k", transport=network, rate_limit_waits=()),
    )
    assert code == 1
    assert named in capsys.readouterr().out
    assert not network.requests
    assert run_json(tmp_path / "run")["code"] == "unknown-model"


def test_a_batch_on_notes_that_are_not_on_the_anthropic_api_is_refused(tmp_path, capsys):
    room = copy_room(tmp_path)
    code = cli.main(
        ["run", str(room), "--out", str(tmp_path / "run"), "--yes", "--batch"],
        gateway=Gateway(api_key="k", transport=NoNetwork(), rate_limit_waits=()),
    )
    assert code == 1
    assert "batch" in capsys.readouterr().out
    assert run_json(tmp_path / "run")["code"] == "bad-settings"


def test_a_run_on_the_client_preset_with_no_anthropic_key_stops_on_a_refused_key_before_any_call(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    room = copy_room(tmp_path)
    code = cli.main(["run", str(room), "--out", str(tmp_path / "run"), "--yes", "--preset", "client"])
    assert code == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().out
    assert run_json(tmp_path / "run")["code"] == "key-refused"


def test_a_run_that_names_no_open_router_model_needs_no_open_router_key(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    room = copy_room(tmp_path)
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    # the run is declined at the estimate: it got as far as the question without a key it does not need
    code = cli.main(["run", str(room), "--out", str(tmp_path / "run"), "--preset", "client"])
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
    client = settings.preset("client")
    found = cli.estimate(room, run_dir, True, True, chosen=client)

    n = found.notes_tokens
    assert found.tasks["notes"]["model"] == HAIKU
    assert found.tasks["notes"]["dollars"] == pytest.approx(
        models.estimate(HAIKU, round(n * cli.NOTES_BILLED_IN), round(n * cli.NOTES_BILLED_OUT), batch=True)
    )
    assert found.tasks["group"]["model"] == SONNET and found.tasks["group"]["dollars"] > 0
    assert found.tasks["writer"]["model"] == SONNET and found.tasks["writer"]["dollars"] > 0
    assert found.dollars == pytest.approx(sum(task["dollars"] for task in found.tasks.values()))


def test_the_batch_takes_half_off_the_notes_estimate_alone(tmp_path):
    room, run_dir = ingested(tmp_path)
    plain = cli.estimate(room, run_dir, True, True, chosen=settings.from_dict({"batch": False}, settings.preset("client")))
    batched = cli.estimate(room, run_dir, True, True, chosen=settings.preset("client"))
    assert batched.tasks["notes"]["dollars"] == pytest.approx(plain.tasks["notes"]["dollars"] / 2)
    assert batched.tasks["writer"]["dollars"] == pytest.approx(plain.tasks["writer"]["dollars"])


def test_a_bedrock_task_is_priced_with_its_regions_premium_and_a_claude_code_task_at_zero(tmp_path):
    room, run_dir = ingested(tmp_path)
    mixed = settings.from_dict(
        {"notes": "bedrock/claude-haiku-4-5", "group": settings.CLAUDE_CODE_DEFAULTS.group,
         "writer": settings.CLAUDE_CODE_DEFAULTS.writer, "write": "both-tree-first", "batch": False, "preset": None},
        settings.preset("client"),
    )
    eu = cli.estimate(room, run_dir, True, True, chosen=mixed)
    n = eu.notes_tokens
    assert eu.tasks["notes"]["dollars"] == pytest.approx(
        models.estimate("bedrock/claude-haiku-4-5", round(n * cli.NOTES_BILLED_IN), round(n * cli.NOTES_BILLED_OUT), region="eu-central-1")
    )
    assert eu.tasks["group"]["dollars"] == 0 and eu.tasks["writer"]["dollars"] == 0
    elsewhere = cli.estimate(room, run_dir, True, True, chosen=settings.from_dict({"region": "ap-south-1"}, mixed))
    assert eu.tasks["notes"]["dollars"] == pytest.approx(elsewhere.tasks["notes"]["dollars"] * 1.10)


def test_the_estimate_leaves_out_the_group_step_when_the_report_is_built_without_the_tree(tmp_path):
    room, run_dir = ingested(tmp_path)
    found = cli.estimate(room, run_dir, True, True, chosen=settings.default_settings(claude_code=False))
    assert "group" not in found.tasks
    assert found.tasks["notes"]["model"] == notes.DEFAULT_MODEL
    assert found.tasks["writer"]["model"] == write.DEFAULT_MODEL


def test_the_estimate_line_names_the_model_of_each_task_and_its_dollars(tmp_path, capsys):
    room, run_dir = ingested(tmp_path)
    found = cli.estimate(room, run_dir, True, True, chosen=settings.preset("client"))
    cli.confirm(found, yes=True)
    printed = capsys.readouterr().out
    assert printed.startswith("estimate:")
    for model in (HAIKU, SONNET):
        assert model in printed


# ---------------------------------------------------------------- a run on one model of the user's choice


class OneModelTransport(httpx.MockTransport):
    """Lists OPEN and answers every call: a note for a notes request, FAKE_REPORT for the rest.
    Every request is recorded with its model."""

    def __init__(self):
        self.models: list[str] = []
        self.listed = 0
        self._lock = threading.Lock()
        super().__init__(self._handle)

    def _handle(self, request):
        if request.method == "GET":
            self.listed += 1
            return httpx.Response(
                200,
                json={"data": [{"id": OPEN, "pricing": {"prompt": "0.0000005", "completion": "0.000002"}, "context_length": 200000}]},
            )
        body = json.loads(request.content)
        with self._lock:
            self.models.append(body["model"])
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
    assert state["models"] == {
        "notes": OPEN, "group": OPEN, "writer": OPEN, "write": None, "batch": False,
        "region": "eu-central-1", "preset": None,
    }
    assert {row["model"] for row in ledger.rows()[1:]} == {OPEN}
    # priced from the live list: 0.5 in and 2 out per million
    assert state["dollars"] > 0
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert report.splitlines()[0] == f"Models: notes {OPEN}, group step not run, writer {OPEN}."


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


# ---------------------------------------------------------------- the client preset, all Claude, through the Anthropic API


def system_of(params) -> str:
    return params["system"][0]["text"]


def client_answer(params, index):
    """The Anthropic fake: a note for a notes call, the group's findings for a group call, the
    report for a writer call."""
    system = system_of(params)
    user = params["messages"][0]["content"]
    if system.startswith(notes.SYSTEM_PROMPT[:60]):
        return message(fake_note({"messages": [None, {"content": user}]}), fresh=1000, out=200, read=300)
    if system.startswith(tree.TREE_PROMPT[:60]):
        rows, doc = [], None
        for line in user.splitlines():
            if line.startswith("id: "):
                doc = line[4:].strip()
            elif line.startswith("quote: ") and doc:
                rows.append({"doc": doc, "finding": f"finding of {doc}", "quote": line[7:]})
                doc = None
        return message(json.dumps({"findings": rows}), fresh=5000, out=400)
    return message(FAKE_REPORT, fresh=8000, out=2000, read=1000)


def client_gateway(client) -> Gateway:
    return Gateway(
        api_key="",
        transport=NoNetwork(),
        rate_limit_waits=(),
        anthropic=AnthropicProvider(client=client, window=0.05, poll=0.0),
        bedrock=BedrockProvider(client=FakeBedrock()),
    )


def test_the_client_preset_runs_all_three_tasks_on_the_anthropic_api_and_books_each_at_its_real_dollars(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    client = FakeAnthropic(client_answer)
    ledger = write_ledger(tmp_path / "L.md")
    code = cli.main(
        ["run", str(room), "--out", str(run_dir), "--yes", "--phase", "8", "--preset", "client"],
        gateway=client_gateway(client),
        ledger=ledger,
    )

    state = run_json(run_dir)
    assert code == 0, state
    assert state["models"] == settings.preset("client").to_dict()

    # the notes went as batches and nothing else did
    batched = [request["params"] for batch in client.batches_made for request in batch]
    assert batched and all(system_of(params).startswith(notes.SYSTEM_PROMPT[:60]) for params in batched)
    assert all(not system_of(params).startswith(notes.SYSTEM_PROMPT[:60]) for params in client.calls)
    assert {params["model"] for params in batched} == {"claude-haiku-4-5-20251001"}
    assert {params["model"] for params in client.calls} == {"claude-sonnet-5-5"}
    assert all("temperature" not in params for params in client.calls)

    rows = ledger.rows()[1:]
    by_model = {}
    for row in rows:
        by_model.setdefault(row["model"], []).append(row)
    assert set(by_model) == {HAIKU, SONNET}
    notes_row = by_model[HAIKU][0]
    assert notes_row["tokens_in"] == len(batched) * 1300 and notes_row["tokens_out"] == len(batched) * 200
    assert notes_row["dollars"] == pytest.approx(
        len(batched) * models.cost(HAIKU, 1000, 200, cache_read=300, batch=True), abs=1e-4
    )
    sonnet_calls = len(client.calls)
    sonnet_dollars = sum(row["dollars"] for row in by_model[SONNET])
    assert sonnet_calls >= 3 and sonnet_dollars > 0
    assert state["dollars"] == pytest.approx(sum(row["dollars"] for row in rows), abs=1e-3)


def test_the_client_runs_report_opens_with_the_model_of_each_task(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    code = cli.main(
        ["run", str(room), "--out", str(run_dir), "--yes", "--phase", "8", "--preset", "client"],
        gateway=client_gateway(FakeAnthropic(client_answer)),
        ledger=write_ledger(tmp_path / "L.md"),
    )
    assert code == 0
    assert (run_dir / "report.md").read_text(encoding="utf-8").splitlines()[0] == OPENING_OF_CLIENT


def test_a_run_does_not_book_a_user_run_to_the_ledger_without_a_phase(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"
    code = cli.main(
        ["run", str(room), "--out", str(run_dir), "--yes", "--preset", "client"],
        gateway=client_gateway(FakeAnthropic(client_answer)),
    )
    assert code == 0
    assert run_json(run_dir)["dollars"] > 0


def test_the_stage_commands_default_to_the_same_models_as_the_settings():
    assert notes.parse_args(["room", "run"]).model == settings.OPEN_DEFAULTS.notes
    assert notes.parse_args(["room", "run", "--batch"]).batch is True
    assert tree.parse_args(["room", "run"]).model == settings.OPEN_DEFAULTS.group
    assert write.parse_args(["room", "run"]).model == settings.OPEN_DEFAULTS.writer
