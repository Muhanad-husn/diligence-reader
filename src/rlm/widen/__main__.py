"""Runs the widen generator as `python -m rlm.widen`."""

import sys

from rlm.widen import main

raise SystemExit(main(sys.argv[1:]))
