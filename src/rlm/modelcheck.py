"""`python -m rlm.modelcheck`: checks that every model a task uses is still listed at its price.

A task module is a module of this package that sets DEFAULT_MODEL. The check reads OpenRouter's
model list through Gateway.models() with no key, since the list is free, and fails when a task's
DEFAULT_MODEL is gone from the list or is listed above its PRICES row in rlm.gateway, which is
the dearest provider's rate. The estimate the user confirms before a run and the cap check are
priced from PRICES, so a listed price above it makes them too low. It prints one line per task and exits 1 on any problem, 0 otherwise.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
import sys
from pathlib import Path

import httpx

import rlm
from rlm.gateway import PRICES, Gateway

# A module sets its default model on a line of its own.
DEFAULT_LINE = re.compile(r"^DEFAULT_MODEL\s*=", re.MULTILINE)

# Rates per million tokens are compared to this many decimals, the rounding models() applies.
PLACES = 6


def defaults() -> dict[str, str]:
    """Each task module's name and its DEFAULT_MODEL, found by reading the package's sources."""
    found: dict[str, str] = {}
    folder = Path(rlm.__file__).resolve().parent
    for info in pkgutil.walk_packages([str(folder)], prefix="rlm."):
        relative = info.name.split(".")[1:]
        source = folder.joinpath(*relative)
        path = source / "__init__.py" if info.ispkg else source.with_suffix(".py")
        if path.exists() and DEFAULT_LINE.search(path.read_text(encoding="utf-8")):
            found[info.name] = importlib.import_module(info.name).DEFAULT_MODEL
    return dict(sorted(found.items()))


def read_list(transport: httpx.BaseTransport | None = None) -> dict[str, tuple[float, float]]:
    """The gateway's model list, one rate per model, read with no key."""
    return Gateway(api_key="", transport=transport).models()


def problems(listed: dict[str, tuple[float, float]]) -> list[str]:
    """One line per task whose model is gone from the list or listed at another price."""
    found = []
    for module, model in defaults().items():
        if model not in listed:
            found.append(f"{module}: {model} is gone from the model list")
            continue
        want = tuple(round(rate, PLACES) for rate in PRICES[model])
        have = tuple(round(rate, PLACES) for rate in listed[model])
        if have[0] > want[0] or have[1] > want[1]:
            found.append(
                f"{module}: {model} is listed at {have[0]:g} in and {have[1]:g} out per million "
                f"tokens, PRICES has {want[0]:g} and {want[1]:g}"
            )
    return found


def main(argv: list[str] | None = None, transport: httpx.BaseTransport | None = None) -> int:
    """Prints each task's model and the check's result; 1 when any task's model is wrong."""
    listed = read_list(transport)
    found = problems(listed)
    for module, model in defaults().items():
        print(f"{module}: {model}")
    for line in found:
        print(f"fail: {line}")
    if not found:
        print(f"ok: every task's model is listed at its price ({len(listed)} models listed)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
