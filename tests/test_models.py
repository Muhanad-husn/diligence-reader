"""Issue #161: a model per task. The settings, the refusal of an unknown id and the price of a
model outside the five.

Every test here is free: nothing is sent and no key is read.
"""

import json

import pytest

from rlm import notes, settings, tree, write
from rlm.gateway import PRICES, price, priced, register_listing

CODE_SONNET = "claude-code/claude-sonnet-5-5"
CODE_HAIKU = "claude-code/claude-haiku-5-5"
OPEN_SONNET = "anthropic/claude-sonnet-5.5"


# ---------------------------------------------------------------- defaults


def test_the_open_defaults_are_the_stage_defaults_of_today():
    found = settings.default_settings(claude_code=False)
    assert (found.notes, found.group, found.writer) == (
        notes.DEFAULT_MODEL,
        tree.DEFAULT_MODEL,
        write.DEFAULT_MODEL,
    )
    assert found.write is None


def test_with_claude_code_on_the_machine_every_task_defaults_to_claude():
    """The notes on Haiku 5.5, the group step and the writer on Sonnet 5.5; a run on the
    defaults then needs no OpenRouter key."""
    found = settings.default_settings(claude_code=True)
    assert found.notes == CODE_HAIKU
    assert (found.group, found.writer) == (CODE_SONNET, CODE_SONNET)
    assert found.write == "both-tree-first"
    assert settings.needs_key(found) is False
    settings.validate(found)


def test_without_claude_code_the_open_defaults_are_unchanged():
    assert settings.OPEN_DEFAULTS == settings.Settings(
        notes="z-ai/glm-5.3-flash", group="z-ai/glm-5.3-flash", writer="z-ai/glm-5.3"
    )


def test_claude_code_is_found_by_the_claude_command_and_an_env_switch_can_say_it_is_not():
    assert settings.claude_code_found(which=lambda name: "/usr/bin/claude", env={}) is True
    assert settings.claude_code_found(which=lambda name: None, env={}) is False
    assert settings.claude_code_found(which=lambda name: "/usr/bin/claude", env={"RLM_CLAUDE_CODE": "off"}) is False


# ---------------------------------------------------------------- saved settings


def test_settings_save_to_a_local_file_and_read_back(tmp_path):
    path = tmp_path / "saved" / "settings.json"
    assert settings.load_settings(path) is None
    chosen = settings.Settings(notes="z-ai/glm-5.3", group=CODE_SONNET, writer=OPEN_SONNET, write="both")
    assert settings.save_settings(chosen, path) == path
    assert settings.load_settings(path) == chosen
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "notes": "z-ai/glm-5.3", "group": CODE_SONNET, "writer": OPEN_SONNET, "write": "both",
    }


def test_a_saved_file_with_some_fields_keeps_the_defaults_for_the_rest(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"writer": "z-ai/glm-5.3-flash"}), encoding="utf-8")
    found = settings.load_settings(path)
    assert found.writer == "z-ai/glm-5.3-flash"
    assert found.notes == notes.DEFAULT_MODEL


def test_a_file_that_is_not_settings_reads_as_none(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    assert settings.load_settings(path) is None


def test_the_settings_file_is_named_by_the_environment_else_by_the_home_folder(tmp_path):
    assert settings.settings_path({"RLM_SETTINGS": str(tmp_path / "s.json")}) == tmp_path / "s.json"
    assert settings.settings_path({}).name == "settings.json"


# ---------------------------------------------------------------- refusing an id before any call


@pytest.mark.parametrize(
    "task, model",
    [
        ("writer", "claude-code/claude-opus-9"),
        ("writer", "anthropic/claude-haiku-9"),
        ("notes", "acme/not-a-model"),
    ],
)
def test_an_unknown_id_is_refused_with_a_message_that_names_it(task, model):
    chosen = settings.Settings(notes=notes.DEFAULT_MODEL, group=tree.DEFAULT_MODEL, writer=write.DEFAULT_MODEL)
    chosen = settings.from_dict({task: model}, chosen)
    with pytest.raises(settings.UnknownModel) as raised:
        settings.validate(chosen)
    assert model in str(raised.value)
    assert settings.TASK_NAMES[task] in str(raised.value)


def test_an_id_the_group_step_would_run_is_not_checked_when_the_report_does_not_use_the_tree():
    chosen = settings.Settings(notes=notes.DEFAULT_MODEL, group="acme/not-a-model", writer=write.DEFAULT_MODEL)
    settings.validate(chosen)
    with pytest.raises(settings.UnknownModel, match="acme/not-a-model"):
        settings.validate(settings.from_dict({"write": "tree"}, chosen))


def test_an_open_router_id_is_known_when_the_models_list_carries_it_and_the_five_need_no_list():
    chosen = settings.Settings(notes="acme/real-model", group=tree.DEFAULT_MODEL, writer=write.DEFAULT_MODEL)
    assert settings.needs_listing(chosen) is True
    with pytest.raises(settings.UnknownModel):
        settings.validate(chosen, listing={"other/model": (1.0, 2.0)})
    settings.validate(chosen, listing={"acme/real-model": (1.0, 2.0)})
    assert settings.needs_listing(settings.default_settings(claude_code=False)) is False


def test_an_anthropic_id_is_an_open_router_id_known_only_when_the_list_carries_it():
    chosen = settings.from_dict({"writer": OPEN_SONNET}, settings.default_settings(False))
    assert settings.needs_listing(chosen) is True
    assert settings.needs_key(chosen) is True
    settings.validate(chosen, listing={OPEN_SONNET: (2.0, 10.0)})
    with pytest.raises(settings.UnknownModel, match=OPEN_SONNET):
        settings.validate(chosen, listing={})
    with pytest.raises(settings.UnknownModel, match=OPEN_SONNET):
        settings.validate(chosen)


def test_claude_code_is_refused_by_the_page_when_it_is_not_on_the_machine(monkeypatch):
    chosen = settings.from_dict({"writer": CODE_SONNET}, settings.default_settings(False))
    settings.validate(chosen)
    with pytest.raises(settings.SettingsError, match="needs Claude Code"):
        settings.validate(chosen, require_claude_code=True)


@pytest.mark.parametrize("field, value", [("write", "everything"), ("notes", " ")])
def test_a_field_that_cannot_run_is_refused(field, value):
    with pytest.raises(settings.SettingsError):
        settings.validate(settings.from_dict({field: value}, settings.default_settings(False)))


def test_the_key_a_run_needs_follows_the_tasks_it_makes_calls_for():
    assert settings.needs_key(settings.default_settings(False)) is True
    on_code = settings.from_dict(
        {"notes": CODE_SONNET, "writer": CODE_SONNET, "group": "z-ai/glm-5.3-flash", "write": None},
        settings.default_settings(False),
    )
    assert settings.used_tasks(on_code) == ("notes", "writer")
    assert settings.needs_key(on_code) is False
    on_tree = settings.from_dict({"write": "tree"}, on_code)
    assert settings.used_tasks(on_tree) == ("notes", "group", "writer")
    assert settings.needs_key(on_tree) is True


def test_the_report_opens_with_the_model_of_each_task():
    assert settings.models_line(settings.default_settings(True)) == (
        f"Models: notes z-ai/glm-5.3-flash, group step {CODE_SONNET}, writer {CODE_SONNET}."
    )
    assert settings.models_line(settings.default_settings(False)) == (
        "Models: notes z-ai/glm-5.3-flash, group step not run, writer z-ai/glm-5.3."
    )


# ---------------------------------------------------------------- prices


def test_a_listed_model_outside_the_five_is_priced_at_its_listed_rate():
    assert OPEN_SONNET not in PRICES
    assert not priced(OPEN_SONNET)
    register_listing({OPEN_SONNET: (2.0, 10.0), "z-ai/glm-5.3": (9.0, 9.0)})
    assert priced(OPEN_SONNET)
    assert price(OPEN_SONNET, 1_000_000, 100_000) == pytest.approx(3.0)
    # the five keep the rate PRICES gives them
    assert price("z-ai/glm-5.3", 1_000_000, 0) == pytest.approx(PRICES["z-ai/glm-5.3"][0])
    assert price(CODE_SONNET, 1_000_000, 100_000) == 0.0
