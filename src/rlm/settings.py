"""The model settings: one model per task, saved on this machine, checked before any call.

A run has three model tasks. Notes is one call per document. The group step is the tree's
calls, in which a model keeps the findings a committee must see group by group, and the writer
assembles the report. Settings hold one model id for each, how the report is built (write),
whether the notes go through the Message Batches API (batch), the AWS region of a bedrock/ id
and the preset the values came from. The group step runs only where write names the tree.

Where the values come from, first to last: what the command line gives, a preset, the run's own
settings file, the file saved on this machine, the defaults. The defaults are the open models of today, or Sonnet 5.5
through Claude Code for the group step and the writer, with the tree, when Claude Code is on
the machine. The preset `client` is the all-Claude room: Haiku 4.5 for the notes, in a batch,
and Sonnet 5.5 for the group step and the writer, on the Anthropic API.

validate refuses an id before any call is made: a direct id not in its table, a claude-code id
Claude Code does not serve here, an OpenRouter id that the model list does not carry. The list
is read by the caller, since reading it is a request and a refusal must cost none.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable

from rlm import models
from rlm.gateway import CLAUDE_CODE_MODELS, OFF_GATEWAY, PRICES

TASKS = ("notes", "group", "writer")

# What each task is called to a person.
TASK_NAMES = {"notes": "notes", "group": "group step", "writer": "writer"}

# The ways the report is built that run the tree, and so the group step.
TREE_MODES = ("tree", "both", "both-tree-first")

PRESET_NAMES = ("default", "client")

_REGION = re.compile(r"^[a-z]{2}(-[a-z]+)+-\d$")

# The open models a person is offered beside the Claude ones, from the five of PLAN.md.
OPEN_CHOICES = (
    "z-ai/glm-5.3-flash",
    "z-ai/glm-5.3",
    "deepseek/deepseek-v4-flash-0731",
    "deepseek/deepseek-v4-pro",
    "openai/gpt-5.6-luna",
)


class SettingsError(ValueError):
    """Settings that cannot be run; the message says which one and why."""


class UnknownModel(SettingsError):
    """A model id no provider of this tool serves; the message names it."""


@dataclass(frozen=True)
class Settings:
    """One model per task and how the run is built."""

    notes: str
    group: str
    writer: str
    write: str | None = None
    batch: bool = False
    region: str = models.DEFAULT_REGION
    preset: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def task(self, name: str) -> str:
        return getattr(self, name)


# The open models of today, the defaults of the open source repository. The stage modules name
# the same three as their own DEFAULT_MODEL, and a test holds the two together.
OPEN_DEFAULTS = Settings(notes="z-ai/glm-5.3-flash", group="z-ai/glm-5.3-flash", writer="z-ai/glm-5.3")

# The same with Sonnet 5.5 through Claude Code for the two tasks that read the findings.
CLAUDE_CODE_DEFAULTS = Settings(
    notes="z-ai/glm-5.3-flash",
    group="claude-code/claude-sonnet-5-5",
    writer="claude-code/claude-sonnet-5-5",
    write="both-tree-first",
)

PRESETS: dict[str, Settings] = {
    "client": Settings(
        notes="anthropic/claude-haiku-4-5",
        group="anthropic/claude-sonnet-5-5",
        writer="anthropic/claude-sonnet-5-5",
        write="both-tree-first",
        batch=True,
        preset="client",
    ),
}


def claude_code_found(
    which: Callable[[str], str | None] | None = None, env: dict | None = None
) -> bool:
    """Says whether the claude command is on this machine. RLM_CLAUDE_CODE=off says it is not."""
    env = os.environ if env is None else env
    if env.get("RLM_CLAUDE_CODE", "").strip().lower() == "off":
        return False
    return (which or shutil.which)("claude") is not None


def default_settings(claude_code: bool | None = None) -> Settings:
    """The defaults: Claude Code's Sonnet for the group step and the writer when Claude Code is
    found, the open models of today when it is not."""
    found = claude_code_found() if claude_code is None else claude_code
    return CLAUDE_CODE_DEFAULTS if found else OPEN_DEFAULTS


def preset(name: str, claude_code: bool | None = None) -> Settings:
    """A named preset's settings. Raises SettingsError for a name that is none."""
    if name == "default":
        return default_settings(claude_code)
    if name in PRESETS:
        return PRESETS[name]
    raise SettingsError(f"no such preset: {name}; the presets are {', '.join(PRESET_NAMES)}")


def settings_path(env: dict | None = None) -> Path:
    """The file the settings are saved in: RLM_SETTINGS, else ~/.diligence-reader/settings.json."""
    env = os.environ if env is None else env
    if env.get("RLM_SETTINGS"):
        return Path(env["RLM_SETTINGS"])
    return Path.home() / ".diligence-reader" / "settings.json"


def from_dict(data: dict, base: Settings) -> Settings:
    """The settings a dict names over a base: a field the dict leaves out keeps the base's."""
    fields = {}
    for name in ("notes", "group", "writer", "write", "region", "preset"):
        if name in data:
            value = data[name]
            if value is not None and not isinstance(value, str):
                raise SettingsError(f"{name} must be text")
            fields[name] = value or None if name in ("write", "preset") else value
    if "batch" in data:
        if not isinstance(data["batch"], bool):
            raise SettingsError("batch must be true or false")
        fields["batch"] = data["batch"]
    for name in ("notes", "group", "writer", "region"):
        if name in fields and not (fields[name] or "").strip():
            raise SettingsError(f"{name} is empty")
        if name in fields:
            fields[name] = fields[name].strip()
    return replace(base, **fields)


def load_settings(path: Path | None = None) -> Settings | None:
    """The saved settings over the defaults, or None where nothing usable is saved."""
    path = Path(path) if path is not None else settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return from_dict(data, default_settings())
    except (OSError, ValueError):
        return None


def save_settings(settings: Settings, path: Path | None = None) -> Path:
    """Saves the settings to the local file and returns its path."""
    path = Path(path) if path is not None else settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def current(path: Path | None = None) -> Settings:
    """The saved settings, else the defaults."""
    return load_settings(path) or default_settings()


def used_tasks(settings: Settings) -> tuple[str, ...]:
    """The tasks a run makes calls for: the group step only where the report is built on the tree."""
    return tuple(task for task in TASKS if task != "group" or settings.write in TREE_MODES)


def needs(settings: Settings) -> dict[str, bool]:
    """Which keys the used tasks call for: an OpenRouter key, an Anthropic key, AWS credentials."""
    found = {models.provider_of(settings.task(task)) for task in used_tasks(settings)}
    return {
        "openrouter": models.OPENROUTER in found,
        "anthropic": models.ANTHROPIC in found,
        "bedrock": models.BEDROCK in found,
    }


def needs_listing(settings: Settings) -> bool:
    """Says whether checking the settings needs OpenRouter's model list: an OpenRouter id the
    five models of PRICES do not already vouch for."""
    return any(
        models.provider_of(settings.task(task)) == models.OPENROUTER
        and settings.task(task) not in PRICES
        for task in used_tasks(settings)
    )


def refusal(model: str, task: str) -> str:
    """Why an id was refused, naming it."""
    name = TASK_NAMES[task]
    provider = models.provider_of(model)
    if provider == models.CLAUDE_CODE:
        return f"{model} (the {name}) is not a Claude Code model here; the choices are {', '.join(sorted(CLAUDE_CODE_MODELS))}"
    if provider == models.BEDROCK:
        return f"{model} (the {name}) is not a Bedrock model here; the choices are {', '.join(sorted(models.BEDROCK_IDS))}"
    if model.startswith("anthropic/"):
        return (
            f"{model} (the {name}) is neither a model of the Anthropic API here "
            f"({', '.join(sorted(models.ANTHROPIC_IDS))}) nor one OpenRouter lists"
        )
    return f"{model} (the {name}) is not a model OpenRouter lists"


def validate(
    settings: Settings,
    listing: dict | None = None,
    require_claude_code: bool = False,
) -> None:
    """Raises SettingsError, an UnknownModel where an id is the fault, unless every setting can run.

    listing is OpenRouter's model list as ids to rates, read by the caller; without it an
    OpenRouter id is known only if PRICES holds it. require_claude_code refuses a claude-code
    id when the claude command is not on this machine.
    """
    if settings.write is not None and settings.write not in TREE_MODES:
        raise SettingsError(f"write is one of {', '.join(TREE_MODES)} or empty, not {settings.write}")
    if not _REGION.match(settings.region):
        raise SettingsError(f"{settings.region} is not an AWS region name")
    for task in used_tasks(settings):
        model = settings.task(task)
        provider = models.provider_of(model)
        if provider == models.CLAUDE_CODE:
            known = model in CLAUDE_CODE_MODELS
            if known and require_claude_code and not claude_code_found():
                raise SettingsError(f"{model} (the {TASK_NAMES[task]}) needs Claude Code, which is not on this machine")
        elif provider == models.BEDROCK:
            known = model in models.BEDROCK_IDS
        elif provider == models.ANTHROPIC:
            known = True
        else:
            known = model in PRICES and model not in OFF_GATEWAY
            known = known or (listing is not None and model in listing)
        if not known:
            raise UnknownModel(refusal(model, task))
    if settings.batch and models.provider_of(settings.notes) != models.ANTHROPIC:
        raise SettingsError("batch applies to notes on an anthropic/ model; the notes are on " + settings.notes)


def models_line(settings: Settings) -> str:
    """The one line a report opens with: the model of each task."""
    group = settings.group if "group" in used_tasks(settings) else "not run"
    notes = settings.notes + (" (batch)" if settings.batch else "")
    return f"Models: notes {notes}, group step {group}, writer {settings.writer}."
