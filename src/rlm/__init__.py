"""One module per stage: ingest, notes, map, dossier, write, verify, grade. See PLAN.md.

__version__ is the version pyproject.toml carries when the package runs from a source checkout,
and the installed distribution's version, read from its metadata, otherwise. A checkout reads
its own pyproject.toml first because an editable install keeps the metadata of the day it was
installed, and src on PYTHONPATH has no metadata at all.
"""

import tomllib
from importlib.metadata import version
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"

if _PYPROJECT.exists():
    __version__ = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
else:
    __version__ = version("diligence-reader")
