"""Issue #161: a model per task. The settings, the refusal of an unknown id, the preset and the
price arithmetic of the two direct providers.

Every test here is free: nothing is sent and no key is read.
"""

import json

import pytest

from rlm import models, notes, settings, tree, write
from rlm.gateway import PRICES, price, priced

HAIKU = "anthropic/claude-haiku-4-5"
SONNET = "anthropic/claude-sonnet-5-5"
CODE_SONNET = "claude-code/claude-sonnet-5-5"


# ---------------------------------------------------------------- defaults and the preset


def test_the_open_defaults_are_the_stage_defaults_of_today():
    found = settings.default_settings(claude_code=False)
    assert (found.notes, found.group, found.writer) == (
        notes.DEFAULT_MODEL,
        tree.DEFAULT_MODEL,
        write.DEFAULT_MODEL,
    )
    assert found.write is None
    assert found.batch is False
    assert found.region == "eu-central-1"


def test_with_claude_code_on_the_machine_the_group_step_and_the_writer_default_to_its_sonnet():
    found = settings.default_settings(claude_code=True)
    assert found.notes == notes.DEFAULT_MODEL
    assert (found.group, found.writer) == (CODE_SONNET, CODE_SONNET)
    assert found.write == "both-tree-first"


def test_claude_code_is_found_by_the_claude_command_and_an_env_switch_can_say_it_is_not():
    assert settings.claude_code_found(which=lambda name: "/usr/bin/claude", env={}) is True
    assert settings.claude_code_found(which=lambda name: None, env={}) is False
    assert settings.claude_code_found(which=lambda name: "/usr/bin/claude", env={"RLM_CLAUDE_CODE": "off"}) is False


def test_the_client_preset_is_all_claude_through_the_anthropic_api_with_the_notes_in_a_batch():
    found = settings.preset("client")
    assert found.notes == HAIKU
    assert found.group == SONNET
    assert found.writer == SONNET
    assert found.batch is True
    assert found.write == "both-tree-first"
    assert found.preset == "client"
    settings.validate(found)


def test_the_default_preset_is_the_defaults_and_another_name_is_refused():
    assert settings.preset("default", claude_code=False) == settings.default_settings(claude_code=False)
    with pytest.raises(settings.SettingsError, match="no such preset: fast"):
        settings.preset("fast")


# ---------------------------------------------------------------- saved settings


def test_settings_save_to_a_local_file_and_read_back(tmp_path):
    path = tmp_path / "saved" / "settings.json"
    assert settings.load_settings(path) is None
    chosen = settings.Settings(
        notes=HAIKU, group=SONNET, writer="bedrock/claude-sonnet-5-5",
        write="both", batch=True, region="eu-west-1", preset=None,
    )
    assert settings.save_settings(chosen, path) == path
    assert settings.load_settings(path) == chosen
    assert json.loads(path.read_text(encoding="utf-8"))["writer"] == "bedrock/claude-sonnet-5-5"


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
        ("notes", "bedrock/claude-opus-9"),
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
    assert settings.needs_listing(settings.preset("client")) is False


def test_an_anthropic_id_the_table_lacks_may_still_be_an_open_router_id():
    chosen = settings.from_dict({"writer": "anthropic/claude-3.5-haiku"}, settings.default_settings(False))
    assert models.provider_of("anthropic/claude-3.5-haiku") == models.OPENROUTER
    settings.validate(chosen, listing={"anthropic/claude-3.5-haiku": (0.8, 4.0)})
    with pytest.raises(settings.UnknownModel, match="anthropic/claude-3.5-haiku"):
        settings.validate(chosen, listing={})


def test_claude_code_is_refused_by_the_page_when_it_is_not_on_the_machine(monkeypatch):
    chosen = settings.from_dict({"writer": CODE_SONNET}, settings.default_settings(False))
    settings.validate(chosen)
    with pytest.raises(settings.SettingsError, match="needs Claude Code"):
        settings.validate(chosen, require_claude_code=True)


def test_a_batch_needs_the_notes_on_the_anthropic_api():
    chosen = settings.from_dict({"batch": True}, settings.default_settings(False))
    with pytest.raises(settings.SettingsError, match="batch"):
        settings.validate(chosen)
    settings.validate(settings.from_dict({"batch": True, "notes": HAIKU}, chosen))


@pytest.mark.parametrize("field, value", [("write", "everything"), ("region", "mars"), ("notes", " ")])
def test_a_field_that_cannot_run_is_refused(field, value):
    with pytest.raises(settings.SettingsError):
        settings.validate(settings.from_dict({field: value}, settings.default_settings(False)))


def test_the_keys_a_run_needs_follow_the_tasks_it_makes_calls_for():
    assert settings.needs(settings.preset("client")) == {"openrouter": False, "anthropic": True, "bedrock": False}
    assert settings.needs(settings.default_settings(False)) == {"openrouter": True, "anthropic": False, "bedrock": False}
    mixed = settings.from_dict(
        {"notes": HAIKU, "writer": "bedrock/claude-sonnet-5-5", "write": None}, settings.default_settings(False)
    )
    assert settings.needs(mixed) == {"openrouter": False, "anthropic": True, "bedrock": True}
    assert settings.used_tasks(mixed) == ("notes", "writer")
    assert settings.used_tasks(settings.preset("client")) == ("notes", "group", "writer")


def test_the_report_opens_with_the_model_of_each_task():
    assert settings.models_line(settings.preset("client")) == (
        f"Models: notes {HAIKU} (batch), group step {SONNET}, writer {SONNET}."
    )
    assert settings.models_line(settings.default_settings(False)) == (
        "Models: notes z-ai/glm-5.3-flash, group step not run, writer z-ai/glm-5.3."
    )


# ---------------------------------------------------------------- providers, ids and prices


def test_a_prefix_names_the_provider():
    assert models.provider_of("claude-code/claude-sonnet-5-5") == models.CLAUDE_CODE
    assert models.provider_of("bedrock/claude-haiku-4-5") == models.BEDROCK
    assert models.provider_of(HAIKU) == models.ANTHROPIC
    assert models.provider_of("z-ai/glm-5.3") == models.OPENROUTER


def test_the_bedrock_id_differs_from_the_anthropic_id_and_takes_its_regions_profile():
    assert models.anthropic_model_id(HAIKU) == "claude-haiku-4-5-20251001"
    assert models.anthropic_model_id(SONNET) == "claude-sonnet-5-5"
    assert models.bedrock_model_id("bedrock/claude-haiku-4-5", "eu-central-1") == (
        "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
    )
    assert models.bedrock_model_id("bedrock/claude-sonnet-5-5", "us-east-1") == "us.anthropic.claude-sonnet-5-5"
    assert models.bedrock_model_id("bedrock/claude-sonnet-5-5", "ap-south-1") == "global.anthropic.claude-sonnet-5-5"
    with pytest.raises(KeyError):
        models.bedrock_model_id("bedrock/claude-opus-9")


def test_the_rates_are_the_ones_the_founder_gave():
    haiku = models.FAMILIES["claude-haiku-4-5"].rates
    sonnet = models.FAMILIES["claude-sonnet-5-5"].rates
    assert (haiku.input, haiku.output, haiku.cache_read, haiku.cache_write) == (1.0, 5.0, 0.10, 1.25)
    assert (sonnet.input, sonnet.output, sonnet.cache_read, sonnet.cache_write) == (2.0, 10.0, 0.20, 2.50)
    assert models.BATCH_DISCOUNT == 0.5


def test_a_call_is_priced_on_every_kind_of_token():
    # 1000 fresh in, 500 out, 4000 read from the cache, 2000 written to it, on Haiku:
    # (1000 * 1 + 500 * 5 + 4000 * 0.10 + 2000 * 1.25) / 1e6
    assert models.cost(HAIKU, 1000, 500, cache_read=4000, cache_write=2000) == pytest.approx(0.0064)
    # the same on Sonnet: (1000 * 2 + 500 * 10 + 4000 * 0.20 + 2000 * 2.50) / 1e6
    assert models.cost(SONNET, 1000, 500, cache_read=4000, cache_write=2000) == pytest.approx(0.0128)


def test_a_batch_takes_half_off_every_rate_and_stacks_with_the_cache():
    plain = models.cost(HAIKU, 1000, 500, cache_read=4000, cache_write=2000)
    assert models.cost(HAIKU, 1000, 500, cache_read=4000, cache_write=2000, batch=True) == pytest.approx(plain / 2)
    assert models.cost(SONNET, 1_000_000, 0, batch=True) == pytest.approx(1.0)


def test_a_bedrock_geographic_profile_carries_the_premium_and_the_global_profile_does_not():
    base = models.cost(SONNET, 1000, 500)
    assert models.cost("bedrock/claude-sonnet-5-5", 1000, 500, region="eu-central-1") == pytest.approx(base * 1.10)
    assert models.cost("bedrock/claude-sonnet-5-5", 1000, 500, region="ap-south-1") == pytest.approx(base)
    assert models.cost(SONNET, 1000, 500, region="eu-central-1") == pytest.approx(base)


def test_the_gateway_prices_a_direct_model_by_the_same_table():
    assert priced(HAIKU) and priced("bedrock/claude-sonnet-5-5")
    assert not priced("bedrock/claude-opus-9")
    assert price(HAIKU, 1_000_000, 100_000) == pytest.approx(1.5)
    assert price(SONNET, 1_000_000, 100_000, batch=True) == pytest.approx(1.0 + 0.5)
    assert price(CODE_SONNET, 1_000_000, 100_000) == 0.0
    assert HAIKU not in PRICES and SONNET not in PRICES
