"""Issue #170: the sealed room has a phase of its own, 9, capped at $10.50 by code."""

import pytest

from rlm import gateway as gateway_module
from rlm.gateway import PHASE_CAPS, CapExceeded
from test_phase8_command import write_ledger

PRICED = "deepseek/deepseek-v4-flash-0731"


def tokens_out_for(dollars: float) -> int:
    return round(dollars / (gateway_module.PRICES[PRICED][1] / 1_000_000))


def test_phase_9_is_capped_at_ten_dollars_fifty():
    assert PHASE_CAPS[9] == 10.5


def test_a_phase_9_batch_past_the_cap_is_refused(tmp_path):
    ledger = write_ledger(tmp_path / "L.md")
    with pytest.raises(CapExceeded, match="phase 9"):
        with ledger.batch("sealed", 9, PRICED, 0, tokens_out_for(10.6)):
            pass


def test_a_phase_9_batch_under_the_cap_is_allowed(tmp_path):
    ledger = write_ledger(tmp_path / "L.md")
    with ledger.batch("sealed", 9, PRICED, 0, tokens_out_for(10.0)):
        pass
