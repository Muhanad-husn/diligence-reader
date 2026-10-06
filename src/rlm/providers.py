"""The two direct providers behind the gateway: the Anthropic API and AWS Bedrock.

Gateway.complete sends an `anthropic/` id to AnthropicProvider and a `bedrock/` id to
BedrockProvider; nothing else calls them. Each draw is one request. It comes back as a Draw: the
reply text, the tokens its usage reports split as the provider splits them, why it stopped and
the dollars it cost at the rates of rlm.models, cache reads and writes and the batch discount
included. The gateway asks again once where a draw has no reply, as it does for OpenRouter.

The system message is the one fixed block of a request: the instructions that every call of a
stage repeats. It is sent as a cached block (cache_control on the Anthropic API, a cachePoint on
Bedrock), so a call after the first reads it at a tenth of the input rate. A provider caches a
prefix only once it holds the model's minimum, 4096 tokens on Haiku 4.5 and 512 on Sonnet 5.5;
a shorter block is sent the same and is not cached, and costs nothing extra.

A reply is the text blocks of the answer. Thinking blocks are not the reply, though their tokens
are billed as output and counted so. Sonnet 5.5 refuses a temperature, so it is sent none; Haiku
4.5 is asked at zero. Neither is asked for JSON by a parameter, since the prompts ask for it.

The Message Batches API serves notes on an anthropic/ id when the user ticks batch. A call sent
as a batch waits in BatchQueue until no call has joined it for `window` seconds, is then sent in
one batch with every call that waited with it, and returns when the batch has ended. The first
asks of a whole pass of notes therefore go as one batch and the re-asks as a second. A request
the batch did not answer, errored, expired or canceled, is not billed and is a draw with no
reply.

A failure of either provider that carries an HTTP status is raised as ProviderError with the
status, which is what lets a refused key or an empty account stop the run on its code.
"""

from __future__ import annotations

import itertools
import threading
import time
from dataclasses import dataclass
from types import SimpleNamespace

from rlm import models
from rlm.gateway import ProviderError

# The seconds one Anthropic request or one Bedrock request may take.
TIMEOUT_SECONDS = 1800.0

# How long a batch call waits for others to join it, and how often a batch is polled.
BATCH_WINDOW_SECONDS = 5.0
BATCH_POLL_SECONDS = 30.0

# The Message Batches API takes 100000 requests and 256 MB a batch; a batch is cut well inside.
MAX_BATCH_REQUESTS = 5000
MAX_BATCH_BYTES = 200_000_000

# The stop a draw carries when it ran out of max_tokens.
CUT_OFF = "length"


@dataclass(frozen=True)
class Draw:
    """One request's answer: its text, its tokens as the provider splits them, why it stopped
    and what it cost."""

    text: str
    fresh: int
    cache_read: int
    cache_write: int
    tokens_out: int
    stop: str | None
    cost: float
    seconds: float


def provider_error(name: str, exc: Exception) -> Exception:
    """The ProviderError a failure of a provider stands for, or the failure itself where it
    carries no HTTP status.

    A credit balance too low is the account refusing every call whatever status it answers
    with, so it is read as 402.
    """
    status = getattr(exc, "status_code", None)
    if not isinstance(status, int):
        response = getattr(exc, "response", None)
        if isinstance(response, dict):
            status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    if not isinstance(status, int):
        return exc
    if "credit balance" in str(exc).lower():
        status = 402
    return ProviderError(status, f"{name} answered {status}: {exc}")


def split_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """The system text of a conversation and its other messages."""
    system = "\n\n".join(message["content"] for message in messages if message["role"] == "system")
    return system, [message for message in messages if message["role"] != "system"]


class BatchQueue:
    """Holds calls for the Message Batches API and sends them together.

    submit blocks until the call's batch has ended and returns the call's outcome. Calls are
    sent once none has joined for window seconds, cut into batches of at most max_requests calls
    and max_bytes of request, and every batch is polled until it has ended.
    """

    def __init__(self, client, window: float, poll: float, max_requests: int, max_bytes: int, sleep=time.sleep):
        self._client = client
        self.window = window
        self.poll = poll
        self.max_requests = max_requests
        self.max_bytes = max_bytes
        self._sleep = sleep
        self._cond = threading.Condition()
        self._queue: list[SimpleNamespace] = []
        self._last = 0.0
        self._flushing = False
        self._ids = itertools.count()

    def submit(self, params: dict) -> SimpleNamespace:
        """Sends one request in a batch and returns its outcome: type, and message when it succeeded."""
        held = SimpleNamespace(
            params=params, custom_id=f"r{next(self._ids)}", event=threading.Event(), outcome=None, error=None
        )
        with self._cond:
            self._queue.append(held)
            self._last = time.monotonic()
            if not self._flushing:
                self._flushing = True
                threading.Thread(target=self._flush, daemon=True).start()
            self._cond.notify_all()
        held.event.wait()
        if held.error is not None:
            raise held.error
        return held.outcome

    def _flush(self) -> None:
        while True:
            with self._cond:
                while True:
                    if not self._queue:
                        self._flushing = False
                        return
                    quiet = time.monotonic() - self._last
                    if quiet >= self.window:
                        waiting, self._queue = self._queue, []
                        break
                    self._cond.wait(self.window - quiet)
            self._send(waiting)

    def _chunks(self, waiting: list[SimpleNamespace]) -> list[list[SimpleNamespace]]:
        chunks: list[list[SimpleNamespace]] = [[]]
        size = 0
        for held in waiting:
            weight = len(repr(held.params))
            if chunks[-1] and (len(chunks[-1]) >= self.max_requests or size + weight > self.max_bytes):
                chunks.append([])
                size = 0
            chunks[-1].append(held)
            size += weight
        return chunks

    def _send(self, waiting: list[SimpleNamespace]) -> None:
        """Makes every waiting call's batches, polls them to their end and hands each call its outcome."""
        try:
            made = []
            for chunk in self._chunks(waiting):
                batch = self._client.messages.batches.create(
                    requests=[{"custom_id": held.custom_id, "params": held.params} for held in chunk]
                )
                made.append((batch.id, chunk))
            for batch_id, chunk in made:
                while self._client.messages.batches.retrieve(batch_id).processing_status != "ended":
                    self._sleep(self.poll)
                by_id = {held.custom_id: held for held in chunk}
                for result in self._client.messages.batches.results(batch_id):
                    held = by_id.pop(result.custom_id, None)
                    if held is not None:
                        held.outcome = result.result
                        held.event.set()
                for held in by_id.values():
                    held.outcome = SimpleNamespace(type="expired", message=None)
                    held.event.set()
        except Exception as exc:
            error = provider_error("anthropic", exc)
            for held in waiting:
                if not held.event.is_set():
                    held.error = error
                    held.event.set()


class AnthropicProvider:
    """Draws from the Anthropic API. The client is injectable so a test can fake it; without
    one the SDK's client is built on first use, with the key given or ANTHROPIC_API_KEY."""

    name = "anthropic"

    def __init__(
        self,
        client=None,
        api_key: str | None = None,
        window: float = BATCH_WINDOW_SECONDS,
        poll: float = BATCH_POLL_SECONDS,
        max_requests: int = MAX_BATCH_REQUESTS,
        max_bytes: int = MAX_BATCH_BYTES,
        sleep=time.sleep,
    ):
        self._client = client
        self._api_key = api_key
        self._built = threading.Lock()
        self._queue: BatchQueue | None = None
        self._queue_settings = (window, poll, max_requests, max_bytes, sleep)

    def client(self):
        """The Anthropic client, built on first use. Raises ProviderError 401 with no key."""
        with self._built:
            if self._client is None:
                import os

                key = self._api_key or os.environ.get("ANTHROPIC_API_KEY", "")
                if not key:
                    raise ProviderError(401, "ANTHROPIC_API_KEY is not set")
                import anthropic

                self._client = anthropic.Anthropic(api_key=key, timeout=TIMEOUT_SECONDS, max_retries=3)
            return self._client

    def queue(self) -> BatchQueue:
        client = self.client()
        with self._built:
            if self._queue is None:
                window, poll, max_requests, max_bytes, sleep = self._queue_settings
                self._queue = BatchQueue(client, window, poll, max_requests, max_bytes, sleep)
            return self._queue

    @staticmethod
    def request(model: str, messages: list[dict], max_tokens: int) -> dict:
        """The body of one request: the cached system block, the other messages and the cap."""
        system, turns = split_messages(messages)
        params = {
            "model": models.anthropic_model_id(model),
            "max_tokens": max_tokens,
            "messages": [{"role": turn["role"], "content": turn["content"]} for turn in turns],
        }
        if system:
            params["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        if models.family_of(model).sampling:
            params["temperature"] = 0
        return params

    def draw(self, model: str, messages: list[dict], max_tokens: int, batch: bool = False) -> Draw:
        """One request, live or in a batch, and its answer."""
        params = self.request(model, messages, max_tokens)
        started = time.monotonic()
        try:
            if batch:
                outcome = self.queue().submit(params)
                if outcome.type != "succeeded":
                    return Draw("", 0, 0, 0, 0, outcome.type, 0.0, time.monotonic() - started)
                reply = outcome.message
            else:
                with self.client().messages.stream(**params) as stream:
                    reply = stream.get_final_message()
        except ProviderError:
            raise
        except Exception as exc:
            raise provider_error(self.name, exc) from exc
        usage = reply.usage
        fresh = int(getattr(usage, "input_tokens", 0) or 0)
        read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        written = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        out = int(getattr(usage, "output_tokens", 0) or 0)
        text = "".join(block.text or "" for block in reply.content if getattr(block, "type", None) == "text")
        stop = reply.stop_reason
        return Draw(
            text=text,
            fresh=fresh,
            cache_read=read,
            cache_write=written,
            tokens_out=out,
            stop=CUT_OFF if stop == "max_tokens" else stop,
            cost=models.cost(model, fresh, out, read, written, batch=batch),
            seconds=time.monotonic() - started,
        )


class BedrockProvider:
    """Draws from AWS Bedrock through boto3's Converse call, on the standard AWS credential
    chain. The client is injectable so a test can fake it."""

    name = "bedrock"

    def __init__(self, client=None, region: str = models.DEFAULT_REGION):
        self._client = client
        self.region = region
        self._built = threading.Lock()

    def client(self):
        """The bedrock-runtime client of the region, built on first use."""
        with self._built:
            if self._client is None:
                import boto3
                from botocore.config import Config

                self._client = boto3.client(
                    "bedrock-runtime",
                    region_name=self.region,
                    config=Config(
                        read_timeout=TIMEOUT_SECONDS,
                        connect_timeout=30,
                        retries={"max_attempts": 4, "mode": "standard"},
                    ),
                )
            return self._client

    def request(self, model: str, messages: list[dict], max_tokens: int) -> dict:
        """The arguments of one Converse call: the region's profile, the cached system block,
        the other messages and the cap."""
        system, turns = split_messages(messages)
        config = {"maxTokens": max_tokens}
        if models.family_of(model).sampling:
            config["temperature"] = 0
        kwargs = {
            "modelId": models.bedrock_model_id(model, self.region),
            "messages": [{"role": turn["role"], "content": [{"text": turn["content"]}]} for turn in turns],
            "inferenceConfig": config,
        }
        if system:
            kwargs["system"] = [{"text": system}, {"cachePoint": {"type": "default"}}]
        return kwargs

    def draw(self, model: str, messages: list[dict], max_tokens: int, batch: bool = False) -> Draw:
        """One Converse call and its answer."""
        kwargs = self.request(model, messages, max_tokens)
        started = time.monotonic()
        try:
            response = self.client().converse(**kwargs)
        except ProviderError:
            raise
        except Exception as exc:
            if type(exc).__name__ == "NoCredentialsError":
                raise ProviderError(401, "no AWS credentials were found in the standard credential chain") from exc
            raise provider_error(self.name, exc) from exc
        usage = response.get("usage") or {}
        fresh = int(usage.get("inputTokens") or 0)
        read = int(usage.get("cacheReadInputTokens") or 0)
        written = int(usage.get("cacheWriteInputTokens") or 0)
        out = int(usage.get("outputTokens") or 0)
        blocks = ((response.get("output") or {}).get("message") or {}).get("content") or []
        text = "".join(block.get("text") or "" for block in blocks if "text" in block)
        stop = response.get("stopReason")
        return Draw(
            text=text,
            fresh=fresh,
            cache_read=read,
            cache_write=written,
            tokens_out=out,
            stop=CUT_OFF if stop == "max_tokens" else stop,
            cost=models.cost(model, fresh, out, read, written, region=self.region),
            seconds=time.monotonic() - started,
        )
