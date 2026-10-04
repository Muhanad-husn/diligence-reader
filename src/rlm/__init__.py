"""One module per stage: ingest, notes, map, dossier, write, verify, grade. See PLAN.md.

__version__ is the installed distribution's version, read from its metadata.
"""

from importlib.metadata import version

__version__ = version("diligence-reader")
