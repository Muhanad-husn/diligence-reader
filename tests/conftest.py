"""Every phase test is parametrised over the three gate samples and runs on all three. Phase
tests read a sample's key from samples/<name>/key.json and the phase's artefact from
runs/<name>/."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ["atlas", "northwind", "northstar-dental"]


@pytest.fixture(params=SAMPLES)
def sample(request):
    return request.param


@pytest.fixture
def sample_dir(sample):
    return ROOT / "samples" / sample


@pytest.fixture
def run_dir(sample):
    return ROOT / "runs" / sample


def pytest_terminal_summary(terminalreporter):
    """Prints each phase's readout at the end of the session, when that phase's tests ran.

    Every loaded test_phase<N> module that defines readout(terminalreporter) is called, in
    phase order.
    """
    seen = {}
    for name, module in list(sys.modules.items()):
        base = name.rsplit(".", 1)[-1]
        if base.startswith("test_phase") and hasattr(module, "readout"):
            seen[base] = module
    for base in sorted(seen):
        seen[base].readout(terminalreporter)
