"""Issue #160: the ledger books what the gateway says a call cost, and PRICES only estimates.

Every test is free: the gateway is a fake on an httpx mock transport and the ledger a temporary
file.
"""

import json

import httpx
import pytest

from rlm import modelcheck
from rlm.gateway import PRICES, Completion, Gateway, Ledger, Meter, NoReply, price
from test_phase8_command import write_ledger

MODEL = "z-ai/glm-5.3"


def body_with(cost, tokens_in=1000, tokens_out=200, content="{}", finish="stop"):
    usage = {"prompt_tokens": tokens_in, "completion_tokens": tokens_out}
    if cost is not None:
        usage["cost"] = cost
    return {
        "id": "x", "provider": "p", "usage": usage,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": finish}],
    }


class Seen(httpx.MockTransport):
    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.requests: list[dict] = []
        super().__init__(self._handle)

    def _handle(self, request):
        self.requests.append(json.loads(request.content))
        return httpx.Response(200, json=self.bodies.pop(0))


def gateway_for(transport) -> Gateway:
    return Gateway(api_key="k", transport=transport, rate_limit_waits=())


def test_the_request_asks_for_the_cost():
    transport = Seen([body_with(0.01)])
    gateway_for(transport).complete(MODEL, [{"role": "user", "content": "hi"}], 100)
    assert transport.requests[0]["usage"] == {"include": True}


def test_a_completion_carries_the_cost_the_gateway_reported():
    transport = Seen([body_with(0.0123)])
    done = gateway_for(transport).complete(MODEL, [{"role": "user", "content": "hi"}], 100)
    assert done.cost == pytest.approx(0.0123)


def test_a_completion_without_a_reported_cost_has_none():
    transport = Seen([body_with(None)])
    done = gateway_for(transport).complete(MODEL, [{"role": "user", "content": "hi"}], 100)
    assert done.cost is None


def test_the_cost_of_every_draw_is_summed():
    transport = Seen([body_with(0.004, content="", finish="length"), body_with(0.006)])
    done = gateway_for(transport).complete(MODEL, [{"role": "user", "content": "hi"}], 100)
    assert done.cost == pytest.approx(0.010)


def test_a_call_with_no_reply_carries_the_cost_of_its_draws():
    transport = Seen([body_with(0.004, content="", finish="length"), body_with(0.005, content="", finish="length")])
    with pytest.raises(NoReply) as caught:
        gateway_for(transport).complete(MODEL, [{"role": "user", "content": "hi"}], 100)
    assert caught.value.cost == pytest.approx(0.009)


def test_the_ledger_row_books_the_reported_cost_not_the_table_price(tmp_path):
    ledger = write_ledger(tmp_path / "L.md")
    with ledger.batch("room", 8, MODEL, 1000, 200) as batch:
        batch.record(Completion("{}", 1_000_000, 1_000_000, 1.0, MODEL, cost=0.0321))
        batch.record(Completion("{}", 1_000_000, 1_000_000, 1.0, MODEL, cost=0.0100))
    row = ledger.rows()[-1]
    assert row["dollars"] == pytest.approx(0.0421)
    assert row["dollars"] != pytest.approx(round(price(MODEL, 2_000_000, 2_000_000), 4))
    assert row["balance"] == pytest.approx(50 - 0.0421)
    assert row["tokens_in"] == 2_000_000


def test_a_call_with_no_reported_cost_is_booked_at_the_table_price(tmp_path):
    ledger = write_ledger(tmp_path / "L.md")
    with ledger.batch("room", 8, MODEL, 1000, 200) as batch:
        batch.record(Completion("{}", 1000, 200, 1.0, MODEL))
    assert ledger.rows()[-1]["dollars"] == pytest.approx(round(price(MODEL, 1000, 200), 4))


def test_the_meter_counts_the_reported_cost(tmp_path):
    meter = Meter(write_ledger(tmp_path / "L.md"))
    with meter.batch("room", 8, MODEL, 10, 10) as batch:
        batch.record(Completion("{}", 1_000_000, 0, 1.0, MODEL, cost=0.05))
    assert meter.dollars == pytest.approx(0.05)


def test_the_estimate_and_the_cap_still_use_the_table(tmp_path, capsys):
    ledger = write_ledger(tmp_path / "L.md")
    with ledger.batch("room", 8, MODEL, 1_000_000, 100_000):
        pass
    want = price(MODEL, 1_000_000, 100_000)
    assert f"${want:.4f} on {MODEL}" in capsys.readouterr().out


def test_the_table_is_the_dearest_provider_the_gateway_may_route_to():
    # OpenRouter's endpoints for each model on 2026-10-05, Wafer and GMICloud left out: the
    # highest input rate and the highest output rate over the rest.
    assert PRICES["z-ai/glm-5.3"] == (2.8, 12.0)
    assert PRICES["z-ai/glm-5.3-flash"] == (0.3, 1.0)


def test_the_model_check_fails_only_where_the_list_is_dearer_than_the_table():
    listed = {model: rate for model, rate in PRICES.items()}
    assert modelcheck.problems(listed) == []
    cheaper = {**listed, MODEL: (PRICES[MODEL][0] / 2, PRICES[MODEL][1] / 2)}
    assert modelcheck.problems(cheaper) == []
    dearer = {**listed, MODEL: (PRICES[MODEL][0], PRICES[MODEL][1] * 2)}
    assert modelcheck.problems(dearer) != []
