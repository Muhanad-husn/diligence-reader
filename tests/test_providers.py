"""Issue #161: the Anthropic API and AWS Bedrock behind the gateway.

Every test here is free: the Anthropic client, the Bedrock client, the OpenRouter transport and
the Claude Code runner are fakes, no key is read and nothing is sent. The fakes record every
request so a test can read what the gateway would have sent.
"""

import threading
from types import SimpleNamespace

import httpx
import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from rlm import cli, models
from rlm.gateway import (
    ClaudeCode,
    Gateway,
    Ledger,
    Meter,
    NoReply,
    ProviderError,
    stops_every_call,
)
from rlm.providers import AnthropicProvider, BedrockProvider
from test_phase8_command import write_ledger

HAIKU = "anthropic/claude-haiku-4-5"
SONNET = "anthropic/claude-sonnet-5-5"
BEDROCK_HAIKU = "bedrock/claude-haiku-4-5"
BEDROCK_SONNET = "bedrock/claude-sonnet-5-5"
MESSAGES = [{"role": "system", "content": "SYSTEM WORDS"}, {"role": "user", "content": "USER WORDS"}]


# ---------------------------------------------------------------- the fakes


def message(text="{}", fresh=100, out=20, read=0, write=0, stop="end_turn"):
    """An Anthropic message as the SDK returns it, as far as the provider reads it."""
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)] if text is not None else [],
        usage=SimpleNamespace(
            input_tokens=fresh,
            output_tokens=out,
            cache_read_input_tokens=read,
            cache_creation_input_tokens=write,
        ),
        stop_reason=stop,
    )


class FakeAnthropic:
    """Stands in for anthropic.Anthropic: answer(params, index) gives the message of each call.

    stream records the live calls; batches records the batches made, the polls and the results,
    and answers each request of a batch with answer too, in the order the batch lists them.
    """

    def __init__(self, answer=lambda params, index: message(), polls=1):
        self.answer = answer
        self.calls: list[dict] = []
        self.batches_made: list[list[dict]] = []
        self.polls = polls
        self._polled: dict[str, int] = {}
        self._lock = threading.Lock()
        self.messages = SimpleNamespace(
            stream=self._stream,
            batches=SimpleNamespace(create=self._create, retrieve=self._retrieve, results=self._results),
        )

    def _stream(self, **params):
        with self._lock:
            self.calls.append(params)
            index = len(self.calls) - 1
        answer = self.answer
        final = lambda: answer(params, index)  # noqa: E731

        class Stream:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def get_final_message(self):
                return final()

        return Stream()

    def _create(self, requests):
        with self._lock:
            self.batches_made.append(list(requests))
            batch_id = f"msgbatch_{len(self.batches_made)}"
        return SimpleNamespace(id=batch_id, processing_status="in_progress")

    def _retrieve(self, batch_id):
        with self._lock:
            seen = self._polled[batch_id] = self._polled.get(batch_id, 0) + 1
        return SimpleNamespace(id=batch_id, processing_status="ended" if seen > self.polls else "in_progress")

    def _results(self, batch_id):
        requests = self.batches_made[int(batch_id.rsplit("_", 1)[1]) - 1]
        for index, request in enumerate(requests):
            outcome = self.answer(request["params"], index)
            if isinstance(outcome, str):
                yield SimpleNamespace(custom_id=request["custom_id"], result=SimpleNamespace(type=outcome))
            else:
                yield SimpleNamespace(
                    custom_id=request["custom_id"],
                    result=SimpleNamespace(type="succeeded", message=outcome),
                )


class FakeBedrock:
    """Stands in for boto3's bedrock-runtime client: answer(kwargs, index) gives each response."""

    def __init__(self, answer=None):
        self.answer = answer or (lambda kwargs, index: converse())
        self.calls: list[dict] = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return self.answer(kwargs, len(self.calls) - 1)


def converse(text="{}", fresh=100, out=20, read=0, write=0, stop="end_turn"):
    """A Converse response as boto3 returns it."""
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}] if text is not None else []}},
        "stopReason": stop,
        "usage": {
            "inputTokens": fresh,
            "outputTokens": out,
            "totalTokens": fresh + out + read + write,
            "cacheReadInputTokens": read,
            "cacheWriteInputTokens": write,
        },
    }


class NoNetwork(httpx.MockTransport):
    """An OpenRouter transport that fails the test when anything reaches it."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        super().__init__(self._handle)

    def _handle(self, request):
        self.requests.append(request)
        raise AssertionError(f"a call reached OpenRouter: {request.url}")


def gateway_with(anthropic=None, bedrock=None, region="eu-central-1", transport=None, claude_code=None, **provider) -> Gateway:
    """A gateway with no key and no network, its two direct providers on fake clients."""
    return Gateway(
        api_key="",
        transport=transport or NoNetwork(),
        rate_limit_waits=(),
        claude_code=claude_code,
        anthropic=AnthropicProvider(client=anthropic or FakeAnthropic(), window=0.3, poll=0.0, **provider),
        bedrock=BedrockProvider(client=bedrock or FakeBedrock(), region=region),
        region=region,
    )


# ---------------------------------------------------------------- routing by prefix


def test_an_anthropic_id_goes_to_the_anthropic_client_and_nowhere_else():
    client = FakeAnthropic(lambda params, index: message('{"ok": true}'))
    bedrock = FakeBedrock()
    network = NoNetwork()
    completion = gateway_with(client, bedrock, transport=network).complete(HAIKU, MESSAGES, max_tokens=500)

    assert completion.text == '{"ok": true}'
    assert completion.model == HAIKU
    assert len(client.calls) == 1 and not bedrock.calls and not network.requests


def test_a_bedrock_id_goes_to_the_bedrock_client_and_nowhere_else():
    client = FakeAnthropic()
    bedrock = FakeBedrock(lambda kwargs, index: converse("hello"))
    network = NoNetwork()
    completion = gateway_with(client, bedrock, transport=network).complete(
        BEDROCK_HAIKU, MESSAGES, max_tokens=500, json=False
    )

    assert completion.text == "hello"
    assert completion.model == BEDROCK_HAIKU
    assert len(bedrock.calls) == 1 and not client.calls and not network.requests


def test_an_open_router_id_goes_to_the_transport_and_a_claude_code_id_to_the_claude_command():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "provider": "p",
                "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
        )

    client, bedrock = FakeAnthropic(), FakeBedrock()
    gateway = gateway_with(client, bedrock, transport=httpx.MockTransport(handler))
    gateway.api_key = "sk-test"
    gateway.complete("z-ai/glm-5.3-flash", MESSAGES, max_tokens=100)
    assert len(seen) == 1 and not client.calls and not bedrock.calls

    import json as jsonlib

    ran = []

    def runner(args, cwd, env, stdin):
        ran.append(args)
        reply = {"result": "{}", "usage": {"input_tokens": 5, "output_tokens": 1},
                 "modelUsage": {"claude-sonnet-5-5": {}}, "is_error": False}
        return 0, jsonlib.dumps(reply), ""

    code = gateway_with(client, bedrock, claude_code=ClaudeCode(runner=runner, pause=0.0))
    code.complete("claude-code/claude-sonnet-5-5", MESSAGES, max_tokens=100)
    assert len(ran) == 1 and not client.calls and not bedrock.calls


@pytest.mark.parametrize("model", ["bedrock/claude-opus-9", "claude-code/claude-opus-9"])
def test_an_unknown_direct_or_claude_code_id_is_refused_before_any_call(model):
    client, bedrock, network = FakeAnthropic(), FakeBedrock(), NoNetwork()
    with pytest.raises(KeyError):
        gateway_with(client, bedrock, transport=network).complete(model, MESSAGES, max_tokens=100)
    assert not client.calls and not bedrock.calls and not network.requests


def test_a_gateway_with_no_keys_at_all_builds_and_answers_a_claude_code_free_run_of_nothing(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    gateway = Gateway(transport=NoNetwork())
    with pytest.raises(ProviderError) as raised:
        gateway.complete(HAIKU, MESSAGES, max_tokens=100)
    assert raised.value.status == 401 and "ANTHROPIC_API_KEY" in str(raised.value)
    with pytest.raises(ProviderError) as raised:
        gateway.complete("z-ai/glm-5.3", MESSAGES, max_tokens=100)
    assert raised.value.status == 401 and "OPENROUTER_API_KEY" in str(raised.value)


# ---------------------------------------------------------------- the Anthropic request


def test_the_system_prompt_is_a_cached_block_and_the_rest_are_the_messages():
    client = FakeAnthropic()
    history = [*MESSAGES, {"role": "assistant", "content": "FIRST"}, {"role": "user", "content": "AGAIN"}]
    gateway_with(client).complete(HAIKU, history, max_tokens=700)

    params = client.calls[0]
    assert params["model"] == "claude-haiku-4-5-20251001"
    assert params["max_tokens"] == 700
    assert params["system"] == [
        {"type": "text", "text": "SYSTEM WORDS", "cache_control": {"type": "ephemeral"}}
    ]
    assert params["messages"] == [
        {"role": "user", "content": "USER WORDS"},
        {"role": "assistant", "content": "FIRST"},
        {"role": "user", "content": "AGAIN"},
    ]


def test_haiku_is_asked_at_temperature_zero_and_sonnet_5_5_is_sent_none():
    haiku, sonnet = FakeAnthropic(), FakeAnthropic()
    gateway_with(haiku).complete(HAIKU, MESSAGES, max_tokens=100)
    gateway_with(sonnet).complete(SONNET, MESSAGES, max_tokens=100)
    assert haiku.calls[0]["temperature"] == 0
    assert "temperature" not in sonnet.calls[0]
    assert sonnet.calls[0]["model"] == "claude-sonnet-5-5"
    assert "thinking" not in sonnet.calls[0]


def test_a_call_with_no_system_message_sends_no_system_block():
    client = FakeAnthropic()
    gateway_with(client).complete(HAIKU, MESSAGES[1:], max_tokens=100)
    assert "system" not in client.calls[0]


def test_the_cache_reads_and_writes_count_in_the_tokens_and_the_dollars_of_a_completion():
    client = FakeAnthropic(lambda params, index: message("{}", fresh=1000, out=500, read=4000, write=2000))
    completion = gateway_with(client).complete(HAIKU, MESSAGES, max_tokens=100)
    assert completion.tokens_in == 7000
    assert completion.tokens_out == 500
    assert completion.cache_read == 4000 and completion.cache_write == 2000
    assert completion.cost == pytest.approx(models.cost(HAIKU, 1000, 500, cache_read=4000, cache_write=2000))
    assert completion.cost == pytest.approx(0.0064)


def test_a_reply_cut_off_by_the_cap_or_empty_is_asked_again_once_and_both_draws_are_paid():
    answers = iter([message("half a rep", fresh=100, out=50, stop="max_tokens"), message('{"a": 1}', fresh=100, out=30)])
    client = FakeAnthropic(lambda params, index: next(answers))
    completion = gateway_with(client).complete(HAIKU, MESSAGES, max_tokens=50)
    assert completion.text == '{"a": 1}'
    assert len(client.calls) == 2
    assert completion.tokens_in == 200 and completion.tokens_out == 80
    assert completion.cost == pytest.approx(models.cost(HAIKU, 200, 80))


def test_two_empty_draws_raise_no_reply_that_carries_what_was_paid():
    client = FakeAnthropic(lambda params, index: message(None, fresh=100, out=40, stop="end_turn"))
    with pytest.raises(NoReply) as raised:
        gateway_with(client).complete(HAIKU, MESSAGES, max_tokens=50)
    assert raised.value.tokens_in == 200 and raised.value.tokens_out == 80
    assert raised.value.cost == pytest.approx(models.cost(HAIKU, 200, 80))
    assert len(client.calls) == 2


def test_a_refusal_is_not_a_reply():
    client = FakeAnthropic(lambda params, index: message("", stop="refusal"))
    with pytest.raises(NoReply, match="refusal"):
        gateway_with(client).complete(SONNET, MESSAGES, max_tokens=50)


def test_thinking_blocks_are_not_the_reply():
    reply = message("ignored")
    reply.content = [
        SimpleNamespace(type="thinking", thinking="private", text=None),
        SimpleNamespace(type="text", text="the answer"),
    ]
    completion = gateway_with(FakeAnthropic(lambda params, index: reply)).complete(SONNET, MESSAGES, max_tokens=50)
    assert completion.text == "the answer"


# ---------------------------------------------------------------- the Bedrock request


def test_a_bedrock_call_names_the_regions_profile_caches_the_system_block_and_sets_the_cap():
    client = FakeBedrock()
    history = [*MESSAGES, {"role": "assistant", "content": "FIRST"}, {"role": "user", "content": "AGAIN"}]
    gateway_with(bedrock=client, region="eu-central-1").complete(BEDROCK_HAIKU, history, max_tokens=700)

    kwargs = client.calls[0]
    assert kwargs["modelId"] == "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
    assert kwargs["system"] == [{"text": "SYSTEM WORDS"}, {"cachePoint": {"type": "default"}}]
    assert kwargs["messages"] == [
        {"role": "user", "content": [{"text": "USER WORDS"}]},
        {"role": "assistant", "content": [{"text": "FIRST"}]},
        {"role": "user", "content": [{"text": "AGAIN"}]},
    ]
    assert kwargs["inferenceConfig"] == {"maxTokens": 700, "temperature": 0}


def test_a_bedrock_sonnet_5_5_call_sends_no_temperature_and_the_us_profile_in_a_us_region():
    client = FakeBedrock()
    gateway_with(bedrock=client, region="us-east-1").complete(BEDROCK_SONNET, MESSAGES, max_tokens=700)
    assert client.calls[0]["modelId"] == "us.anthropic.claude-sonnet-5-5"
    assert client.calls[0]["inferenceConfig"] == {"maxTokens": 700}


def test_a_bedrock_completion_carries_its_cache_tokens_and_the_regions_premium():
    client = FakeBedrock(lambda kwargs, index: converse("{}", fresh=1000, out=500, read=4000, write=2000))
    completion = gateway_with(bedrock=client, region="eu-central-1").complete(BEDROCK_HAIKU, MESSAGES, max_tokens=100)
    assert completion.tokens_in == 7000 and completion.tokens_out == 500
    assert completion.cache_read == 4000 and completion.cache_write == 2000
    assert completion.cost == pytest.approx(0.0064 * 1.10)


def test_a_bedrock_reply_cut_off_by_the_cap_is_asked_again_once():
    answers = iter([converse("half", out=40, stop="max_tokens"), converse('{"a": 1}', out=10)])
    client = FakeBedrock(lambda kwargs, index: next(answers))
    completion = gateway_with(bedrock=client).complete(BEDROCK_HAIKU, MESSAGES, max_tokens=40)
    assert completion.text == '{"a": 1}' and completion.tokens_out == 50 and len(client.calls) == 2


# ---------------------------------------------------------------- failures stop a run the way a status does


class StatusError(Exception):
    def __init__(self, status_code, message="refused"):
        super().__init__(message)
        self.status_code = status_code


@pytest.mark.parametrize("status, code", [(401, "key-refused"), (403, "key-refused"), (429, "rate-limited")])
def test_an_anthropic_status_that_refuses_every_call_stops_the_run_on_its_code(status, code):
    def answer(params, index):
        raise StatusError(status)

    with pytest.raises(ProviderError) as raised:
        gateway_with(FakeAnthropic(answer)).complete(HAIKU, MESSAGES, max_tokens=100)
    assert raised.value.status == status
    assert stops_every_call(raised.value)
    assert cli.code_of(raised.value) == code


def test_a_credit_balance_too_low_is_no_credits_whatever_status_the_api_gives_it():
    def answer(params, index):
        raise StatusError(400, "Your credit balance is too low to access the Anthropic API")

    with pytest.raises(ProviderError) as raised:
        gateway_with(FakeAnthropic(answer)).complete(HAIKU, MESSAGES, max_tokens=100)
    assert raised.value.status == 402
    assert cli.code_of(raised.value) == "no-credits"


def test_another_anthropic_error_is_not_a_status_that_stops_every_call():
    def answer(params, index):
        raise StatusError(500, "overloaded")

    with pytest.raises(ProviderError) as raised:
        gateway_with(FakeAnthropic(answer)).complete(HAIKU, MESSAGES, max_tokens=100)
    assert not stops_every_call(raised.value)
    assert cli.code_of(raised.value) == "unexpected"


def test_a_bedrock_access_denied_and_missing_credentials_stop_the_run_as_a_refused_key():
    def denied(kwargs, index):
        raise ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "not allowed"}, "ResponseMetadata": {"HTTPStatusCode": 403}},
            "Converse",
        )

    with pytest.raises(ProviderError) as raised:
        gateway_with(bedrock=FakeBedrock(denied)).complete(BEDROCK_HAIKU, MESSAGES, max_tokens=100)
    assert cli.code_of(raised.value) == "key-refused"

    def none(kwargs, index):
        raise NoCredentialsError()

    with pytest.raises(ProviderError) as raised:
        gateway_with(bedrock=FakeBedrock(none)).complete(BEDROCK_HAIKU, MESSAGES, max_tokens=100)
    assert raised.value.status == 401 and "AWS credentials" in str(raised.value)


def test_a_throttled_bedrock_call_is_rate_limited():
    def throttled(kwargs, index):
        raise ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "slow"}, "ResponseMetadata": {"HTTPStatusCode": 429}},
            "Converse",
        )

    with pytest.raises(ProviderError) as raised:
        gateway_with(bedrock=FakeBedrock(throttled)).complete(BEDROCK_HAIKU, MESSAGES, max_tokens=100)
    assert cli.code_of(raised.value) == "rate-limited"


# ---------------------------------------------------------------- the ledger books what the call cost


def test_an_anthropic_call_is_booked_with_its_real_tokens_and_its_cache_priced_dollars(tmp_path):
    ledger = write_ledger(tmp_path / "L.md")
    client = FakeAnthropic(lambda params, index: message("{}", fresh=2000, out=3000, read=40000, write=20000))
    gateway = gateway_with(client)
    with ledger.batch("room", 8, HAIKU, 62000, 3000) as batch:
        batch.record(gateway.complete(HAIKU, MESSAGES, max_tokens=3000))

    row = ledger.rows()[-1]
    assert row["model"] == HAIKU
    assert (row["tokens_in"], row["tokens_out"]) == (62000, 3000)
    # (2000 * 1 + 3000 * 5 + 40000 * 0.10 + 20000 * 1.25) / 1e6
    assert row["dollars"] == pytest.approx(0.046)
    assert row["balance"] == pytest.approx(50 - 0.046)


def test_a_bedrock_call_is_booked_at_the_regions_rates(tmp_path):
    ledger = write_ledger(tmp_path / "L.md")
    client = FakeBedrock(lambda kwargs, index: converse("{}", fresh=2000, out=3000, read=40000, write=20000))
    with ledger.batch("room", 8, BEDROCK_HAIKU, 62000, 3000) as batch:
        batch.record(gateway_with(bedrock=client).complete(BEDROCK_HAIKU, MESSAGES, max_tokens=3000))
    row = ledger.rows()[-1]
    assert row["model"] == BEDROCK_HAIKU
    assert row["dollars"] == pytest.approx(0.046 * 1.10, abs=1e-4)


def test_the_estimate_of_a_direct_batch_is_printed_before_the_call_and_the_cap_still_refuses(tmp_path, capsys):
    ledger = write_ledger(tmp_path / "L.md")
    with ledger.batch("room", 8, SONNET, 1_000_000, 100_000):
        pass
    assert "estimate: 1000000 tokens in, 100000 tokens out, $3.0000 on " + SONNET in capsys.readouterr().out
    from rlm.gateway import CapExceeded

    with pytest.raises(CapExceeded):
        with ledger.batch("room", 8, SONNET, 10_000_000, 1_000_000):
            raise AssertionError("the batch must be refused before it opens")


def test_a_meter_counts_a_direct_call_at_its_real_dollars():
    meter = Meter()
    client = FakeAnthropic(lambda params, index: message("{}", fresh=1000, out=500, read=4000, write=2000))
    gateway = gateway_with(client)
    with meter.batch("room", 8, HAIKU, 7000, 500) as batch:
        batch.record(gateway.complete(HAIKU, MESSAGES, max_tokens=500))
    assert meter.dollars == pytest.approx(0.0064)
    assert meter.tokens_in == 7000


# ---------------------------------------------------------------- the Message Batches API


def submit_together(gateway, count, model=HAIKU):
    """count threads each sending one batch call at the same moment; the completions in thread order."""
    results = [None] * count
    barrier = threading.Barrier(count)

    def one(index):
        barrier.wait()
        messages = [MESSAGES[0], {"role": "user", "content": f"DOC {index}"}]
        results[index] = gateway.complete(model, messages, max_tokens=500, batch=True)

    threads = [threading.Thread(target=one, args=(index,)) for index in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


def echo(params, index):
    return message(params["messages"][-1]["content"], fresh=100, out=20, read=300)


def test_calls_sent_together_are_one_batch_and_each_gets_its_own_answer_back():
    client = FakeAnthropic(echo)
    results = submit_together(gateway_with(client), 5)

    assert len(client.batches_made) == 1
    requests = client.batches_made[0]
    assert len(requests) == 5
    assert len({request["custom_id"] for request in requests}) == 5
    assert not client.calls
    assert [completion.text for completion in results] == [f"DOC {index}" for index in range(5)]


def test_a_batched_request_is_the_live_request_with_the_system_block_cached():
    client = FakeAnthropic(echo)
    submit_together(gateway_with(client), 2)
    params = client.batches_made[0][0]["params"]
    assert params["model"] == "claude-haiku-4-5-20251001"
    assert params["max_tokens"] == 500
    assert params["temperature"] == 0
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_a_batched_call_is_booked_at_half_price_with_its_cache_reads():
    client = FakeAnthropic(echo)
    results = submit_together(gateway_with(client), 3)
    for completion in results:
        assert completion.tokens_in == 400 and completion.tokens_out == 20
        assert completion.cost == pytest.approx(models.cost(HAIKU, 100, 20, cache_read=300, batch=True))
        assert completion.cost == pytest.approx(models.cost(HAIKU, 100, 20, cache_read=300) / 2)


def test_a_second_round_of_calls_is_a_second_batch():
    client = FakeAnthropic(echo)
    gateway = gateway_with(client)
    submit_together(gateway, 3)
    submit_together(gateway, 2)
    assert [len(batch) for batch in client.batches_made] == [3, 2]


def test_a_batch_is_polled_until_it_has_ended():
    client = FakeAnthropic(echo, polls=3)
    submit_together(gateway_with(client), 2)
    assert client._polled["msgbatch_1"] == 4


def test_a_batch_over_the_request_limit_is_cut_into_batches():
    client = FakeAnthropic(echo)
    results = submit_together(gateway_with(client, max_requests=2), 5)
    assert sorted(len(batch) for batch in client.batches_made) == [1, 2, 2]
    assert [completion.text for completion in results] == [f"DOC {index}" for index in range(5)]


@pytest.mark.parametrize("outcome", ["errored", "expired", "canceled"])
def test_a_request_the_batch_did_not_answer_is_no_reply_and_costs_nothing(outcome):
    client = FakeAnthropic(lambda params, index: outcome)
    with pytest.raises(NoReply) as raised:
        gateway_with(client).complete(HAIKU, MESSAGES, max_tokens=100, batch=True)
    assert raised.value.tokens_in == 0 and outcome in str(raised.value)


def test_only_an_anthropic_model_may_be_sent_as_a_batch():
    client, bedrock = FakeAnthropic(), FakeBedrock()
    for model in (BEDROCK_HAIKU, "z-ai/glm-5.3-flash"):
        with pytest.raises(ValueError, match="batch"):
            gateway_with(client, bedrock).complete(model, MESSAGES, max_tokens=100, batch=True)
    assert not client.calls and not client.batches_made and not bedrock.calls
