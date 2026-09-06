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
    """Prints each phase's readout at the end of the session, when that phase's tests ran."""
    for name, module in list(sys.modules.items()):
        if name.rsplit(".", 1)[-1] == "test_phase1" and hasattr(module, "readout"):
            module.readout(terminalreporter)
