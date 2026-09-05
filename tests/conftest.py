"""Every phase test is parametrised over the three gate samples. Phase tests read a sample's
key from samples/<name>/key.json and the phase's artefact from runs/<name>/."""

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
