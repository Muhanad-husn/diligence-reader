"""Phase 8 slice 05: `python -m rlm.modelcheck`, the weekly check of the models the tasks use.

The check reads OpenRouter's free model list through Gateway.models() with no key and fails when
a task module's DEFAULT_MODEL is gone from the list or listed at a price other than PRICES. The
fixture lists are built from PRICES and answered by a fake transport, so those tests cost $0 and
need no network. The live test reads the real list, which costs nothing and needs no key, and
skips when the list cannot be reached.
"""

import httpx
import pytest

from rlm import modelcheck, notes, write
from rlm.gateway import PRICES


def per_token(rate: float) -> str:
    """A rate per million tokens written the way the model list writes it, per token."""
    return f"{rate / 1_000_000:.12f}".rstrip("0")


def listing(prices: dict[str, tuple[float, float]]) -> dict:
    """A model list in the shape OpenRouter answers /models with."""
    return {
        "data": [
            {"id": model, "pricing": {"prompt": per_token(rate_in), "completion": per_token(rate_out)}}
            for model, (rate_in, rate_out) in prices.items()
        ]
    }


class ListTransport(httpx.MockTransport):
    """Answers GET /models with one listing and records every request."""

    def __init__(self, body: dict):
        self.requests: list[httpx.Request] = []
        self.body = body
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert request.method == "GET"
        assert request.url.path.endswith("/models")
        return httpx.Response(200, json=self.body)


def test_every_task_module_with_a_default_model_is_checked():
    found = modelcheck.defaults()

    assert found["rlm.notes"] == notes.DEFAULT_MODEL
    assert found["rlm.write"] == write.DEFAULT_MODEL
    assert all(model in PRICES for model in found.values())


def test_the_list_as_priced_passes(monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    transport = ListTransport(listing(PRICES))

    assert modelcheck.main([], transport=transport) == 0
    assert len(transport.requests) == 1
    assert "authorization" not in transport.requests[0].headers
    assert "ok" in capsys.readouterr().out


def test_a_default_model_gone_from_the_list_fails(monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    prices = {model: rate for model, rate in PRICES.items() if model != notes.DEFAULT_MODEL}

    assert modelcheck.main([], transport=ListTransport(listing(prices))) == 1
    out = capsys.readouterr().out
    assert "rlm.notes" in out
    assert notes.DEFAULT_MODEL in out
    assert "gone" in out


def test_a_default_model_at_a_changed_price_fails(monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    rate_in, rate_out = PRICES[write.DEFAULT_MODEL]
    prices = {**PRICES, write.DEFAULT_MODEL: (rate_in, rate_out * 2)}

    assert modelcheck.main([], transport=ListTransport(listing(prices))) == 1
    out = capsys.readouterr().out
    assert "rlm.write" in out
    assert write.DEFAULT_MODEL in out
    assert f"{rate_out * 2:g}" in out


def test_a_model_no_task_uses_may_change_price():
    unused = [model for model in PRICES if model not in modelcheck.defaults().values()]
    prices = {**PRICES, **{model: (9.0, 9.0) for model in unused}}

    assert modelcheck.problems(modelcheck.read_list(ListTransport(listing(prices)))) == []


def test_the_live_list_passes(monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    try:
        code = modelcheck.main([])
    except httpx.TransportError as exc:
        pytest.skip(f"the model list could not be reached: {exc}")
    assert code == 0, capsys.readouterr().out
