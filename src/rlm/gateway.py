"""The one module that calls a model, and the ledger that pays for the call.

Every model call in this repository goes through Gateway.complete. A claude-code/ id goes to
headless Claude Code, and any other id to OpenRouter, where complete posts one chat completion
with temperature 0, a fixed seed, JSON output mode, the reasoning object REASONING gives its
model, and the providers of IGNORED_PROVIDERS left out of the routing. Nothing else opens a
socket.

An empty content is not a reply, and neither is a reply the model was cut off in the middle of.
The failure the ignore list is for reaches the routing from any provider that is not yet on it:
the whole max_tokens budget goes on reasoning, and what comes back is a null content with a
finish reason of length, or the few sentences the budget had left over stopping mid sentence on
the same finish reason. Either way the call pays in full and there is no report in it. complete
refuses both. Where a draw carries no content, or stops on the length finish reason, it sends
the request once more so the router picks again, and where the second draw does the same it
raises NoReply naming the model, the provider each draw named, the finish reason, the
completion tokens and the characters the gateway returned. Both draws' tokens go onto the
completion the second draw returns, so the ledger books what was paid either way. z-ai/glm-5.3
did this to the writer on 2026-09-09: two re-asks came back at nothing at all, one first draw
came back at 652 characters of 24000 completion tokens, and complete handed all three on as
though they were answers, so a schedule with no report on it was written to disk and graded.
A report that is genuinely too long is not what this catches: every pass that came back whole
sits well under the cap, pass a of atlas at 13627 completion tokens of 24000.

Money is a ceiling the code enforces. A batch of calls runs inside Ledger.batch, which prints
the estimated tokens and the price before anything is sent, refuses when the estimate would
take the phase past its cap or the total past the $50 ceiling, and on a clean exit appends one
row to LEDGER.md with the gateway's own reported token counts. A batch that raises writes
nothing. Nothing else writes LEDGER.md.

A user's run of the command is not this build's spending, so it books nothing. Meter has the
batch shape of Ledger and counts what every batch's calls cost, raise or not, for the run's
own record. Given no ledger it applies no cap, prints its estimate and writes nothing; given a
ledger, each of its batches is that ledger's batch underneath, so the cap and the row stand
as they do for any phase, and the meter still counts.

A request the gateway answers with 429 is sent again after each wait of RATE_LIMIT_WAITS, and
a 429 after the last wait is raised like any other status. A 401, 402, 403 or 429 says that
the key, the account or the rate refuses every call and not one document, and stops_every_call
says so to a pass that would otherwise drop the document and go on to the next.
"""

from __future__ import annotations

import datetime
import math
import json as jsonlib
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

import httpx

# Per million tokens, prompt then completion: the estimate printed before a batch and the cap
# check, never what a row of LEDGER.md books, which is the cost the gateway reports for the call.
# The two GLM rows are the dearest rate over the providers the gateway may route to, the highest
# input rate and the highest output rate on OpenRouter's endpoints list of 2026-10-05 with
# IGNORED_PROVIDERS left out, so the cap check is never under. The others are from the gateway's
# model list on 2026-09-07.
PRICES: dict[str, tuple[float, float]] = {
    "openai/gpt-5.6-luna": (0.200, 1.200),
    "deepseek/deepseek-v4-flash-0731": (0.0152, 1.280),
    "deepseek/deepseek-v4-pro": (0.2088, 0.4176),
    "z-ai/glm-5.3": (2.800, 12.000),
    "z-ai/glm-5.3-flash": (0.300, 1.000),
    # TypeSafe's Jev on TypeSafe's own API, not the gateway: input tokens only, output free.
    "typesafe/jev-1.13.0": (0.042, 0.0),
}

# The models PRICES carries that the gateway does not serve. Their calls are priced and booked
# like any other, but Gateway.complete never sends them and no bake-off chooses between them.
OFF_GATEWAY = frozenset({"typesafe/jev-1.13.0"})

# The models served by headless Claude Code on the founder's subscription, by the id this
# repository names them with, each with the id the claude command line takes. A call to one
# costs no cash: price reads it at zero and the ledger books it at $0.00.
CLAUDE_CODE_MODELS: dict[str, str] = {"claude-code/claude-sonnet-5-5": "claude-sonnet-5-5"}

# The prefix that sends an id to headless Claude Code in place of OpenRouter.
CLAUDE_CODE_PREFIX = "claude-code/"

# What the same tokens would cost on Anthropic's API, per million tokens, prompt then completion.
# It is written beside the run, never in the ledger.
API_EQUIVALENT: dict[str, tuple[float, float]] = {"claude-code/claude-sonnet-5-5": (2.0, 10.0)}

# The model id each Claude Code model's reply must name, from its usage by model.
CLAUDE_CODE_REPLY = {"claude-code/claude-sonnet-5-5": re.compile(r"^claude-sonnet-5-5(?![0-9])")}

# The tables the repository has priced a call at before, newest first. A ledger row written
# before a price moved reconciles at one of these, so it is kept here.
PAST_PRICES: tuple[dict[str, tuple[float, float]], ...] = (
    {
        "openai/gpt-5.6-luna": (0.200, 1.200),
        "deepseek/deepseek-v4-flash-0731": (0.0152, 1.280),
        "deepseek/deepseek-v4-pro": (0.2088, 0.4176),
        "z-ai/glm-5.3": (1.400, 4.400),
        "z-ai/glm-5.3-flash": (0.150, 0.500),
    },
    {
        "openai/gpt-5.6-luna": (0.200, 1.200),
        "deepseek/deepseek-v4-flash-0731": (0.140, 0.280),
        "deepseek/deepseek-v4-pro": (0.955, 1.911),
        "z-ai/glm-5.3": (1.400, 4.400),
        "z-ai/glm-5.3-flash": (0.075, 0.250),
    },
    {
        "openai/gpt-5.6-luna": (0.200, 1.200),
        "deepseek/deepseek-v4-flash-0731": (0.050, 0.100),
        "deepseek/deepseek-v4-pro": (0.657, 1.314),
        "z-ai/glm-5.3": (1.400, 4.400),
        "z-ai/glm-5.3-flash": (0.075, 0.250),
    },
    {
        "openai/gpt-5.6-luna": (0.200, 1.200),
        "deepseek/deepseek-v4-flash-0731": (0.065, 0.180),
        "deepseek/deepseek-v4-pro": (0.870, 1.740),
        "z-ai/glm-5.3": (1.400, 4.400),
        "z-ai/glm-5.3-flash": (0.075, 0.250),
    },
)

# The effort a Claude model is asked to think at. Sonnet 5.5 thinks at high effort unless told
# otherwise, and its thinking counts against the reply cap, so a call left at high can be cut
# off before it answers. Every Claude Code call passes it, and Sonnet 5.5 on OpenRouter carries
# it.
CLAUDE_THINKING_EFFORT = "medium"

# The reasoning object each model's request carries. The two GLM endpoints answer 400 when
# reasoning is disabled, so they carry a low effort object instead; every other model of PRICES
# carries reasoning off. Sonnet 5.5, which a user may pick through OpenRouter though PRICES does
# not carry it, thinks at CLAUDE_THINKING_EFFORT. Any other model carries reasoning off.
REASONING: dict[str, dict] = {
    "openai/gpt-5.6-luna": {"enabled": False},
    "deepseek/deepseek-v4-flash-0731": {"enabled": False},
    "deepseek/deepseek-v4-pro": {"enabled": False},
    "z-ai/glm-5.3": {"effort": "low"},
    "z-ai/glm-5.3-flash": {"effort": "low"},
    "anthropic/claude-sonnet-5.5": {"effort": CLAUDE_THINKING_EFFORT},
}

# The gateway serves one model from several providers and picks one per call. A provider named
# here ignores the reasoning object above: it spends the whole max_tokens budget on reasoning
# and answers with a null content and a finish reason of length, so the call pays in full and
# returns nothing. Every call leaves these out. Wafer was found doing this to z-ai/glm-5.3-flash
# on 2026-09-09, burning 6000 reasoning tokens on a prompt the other providers answer with 10
# to 26; the same prompt had been answered a day earlier and the ten documents it hit came back
# with no note at all, three runs in a row. GMICloud was found doing the same to
# z-ai/glm-5.3-flash on 2026-10-04 in the phase 8 gate, twice on one atlas document (DR-029),
# whose note was dropped and with it a planted fact. Morph was found doing the same to
# z-ai/glm-5.3 on 2026-10-05 in the Avid report write, twice, 12000 reasoning tokens each and
# no content.
IGNORED_PROVIDERS = ("Wafer", "GMICloud", "Morph")

# The finish reason a draw carries when it ran out of the max_tokens budget. The reply then
# stops wherever the budget ran out, which is usually mid sentence, and on a provider that
# ignores the reasoning object it stops after a few hundred characters of a paid full budget.
CUT_OFF = "length"

# How many times one request is drawn before an answer with no reply in it is given up on. The
# second draw is what the router sends somewhere else; a third would pay a third time for the
# same answer.
MAX_DRAWS = 2

# The total ceiling and the per phase caps, from PLAN.md section 6. Phase 5 carries $1 borrowed
# from the reserve on 2026-09-09 to rewrite the three gate samples' reports, whose artefacts were
# lost with PR #119's worktree; the reason is written at the head of LEDGER.md. Phase 8 carries
# $3 from the reserve on 2026-10-04 and $6 more on 2026-10-05 for #160, whose two rankers are
# tried on two sealed rooms; that reason is written there too.
TOTAL_CEILING = 50.0
PHASE_CAPS: dict[int, float] = {
    0: 0.0, 1: 0.0, 2: 8.0, 3: 0.0, 4: 0.0, 5: 9.0, 6: 15.0, 7: 4.0, 8: 11.5
}

BASE_URL = "https://openrouter.ai/api/v1"
TIMEOUT_SECONDS = 300.0

# The seconds waited before each further try of a request the gateway answered with 429. Two
# waits make three tries; the 429 of the third is raised.
RATE_LIMIT_WAITS: tuple[float, ...] = (2.0, 8.0)

# The seconds waited before a request is sent again after the connection dropped (a transport
# failure, not a status). It is sent again once; the second failure is raised.
TRANSPORT_RETRY_WAIT = 3.0

# The statuses that refuse every call of a run rather than one request: the key refused (401,
# 403), the account out of credits (402), and the rate limit still in force after the waits
# (429).
STOPPING_STATUSES = frozenset({401, 402, 403, 429})

_LEDGER_ROW = re.compile(
    r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|$"
)


class CapExceeded(Exception):
    """Raised before a request when its estimate would pass a phase cap or the total ceiling."""


class NoReply(Exception):
    """Raised when two draws of one request both came back with no reply in them.

    tokens_in, tokens_out and seconds are the sums over the draws, which were paid though they
    gave no text. cut_off is true when every draw finished on the length reason, which is a
    request too large for its max_tokens budget and not a gateway that answered with nothing.
    cost is the dollars the gateway reported for the draws, or None where it reported none.
    """

    def __init__(
        self,
        message: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        seconds: float = 0.0,
        cut_off: bool = False,
        cost: float | None = None,
    ):
        super().__init__(message)
        self.cost = cost
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.seconds = seconds
        self.cut_off = cut_off


@dataclass(frozen=True)
class Completion:
    """One model reply: its text, the gateway's reported usage, the wall seconds and the model."""

    text: str
    tokens_in: int
    tokens_out: int
    seconds: float
    model: str
    cost: float | None = None


def stops_every_call(exc: BaseException) -> bool:
    """Says whether an exception is a gateway status that refuses every call, not one request."""
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code in STOPPING_STATUSES
    )


def estimate_tokens(text: str) -> int:
    """Estimates the tokens of a string as its characters divided by four, rounded up."""
    return math.ceil(len(text) / 4)


def refused_draw(
    provider: str | None, finish_reason: str | None, tokens_out: int, characters: int
) -> str:
    """One refused answer written out: who served it, why it stopped, what it billed and how
    much text it returned.

    A body that names no provider and a body that gives no finish reason are written as that,
    because what the gateway did not say is not guessed at here.
    """
    returned = f"{characters} characters" if characters else "no content"
    return (
        f"{provider or 'no provider named'} finished on "
        f"{finish_reason or 'no finish reason'} after {tokens_out} completion tokens "
        f"and returned {returned}"
    )


# The rates of the OpenRouter models a run was told about by the gateway's model list, which
# a model outside PRICES is priced at, and their context windows in tokens. register_listing
# fills them; PRICES stays what the five models are priced at, never overwritten.
LIVE_PRICES: dict[str, tuple[float, float]] = {}
LIVE_CONTEXT: dict[str, int] = {}


def register_listing(listing: dict[str, tuple[float, float]], contexts: dict[str, int] | None = None) -> None:
    """Remembers the rates and windows of the gateway's model list for the models PRICES lacks."""
    for model, rate in listing.items():
        if model not in PRICES:
            LIVE_PRICES[model] = rate
    LIVE_CONTEXT.update(contexts or {})


def price(model: str, tokens_in: int, tokens_out: int) -> float:
    """Prices a call at the PRICES rate, else at the listed rate of an OpenRouter model, and a
    Claude Code model at zero. Raises KeyError for a model in none."""
    if model in CLAUDE_CODE_MODELS:
        return 0.0
    rate_in, rate_out = PRICES[model] if model in PRICES else LIVE_PRICES[model]
    return tokens_in * rate_in / 1_000_000 + tokens_out * rate_out / 1_000_000


def reported_cost(costs: list[float | None]) -> float | None:
    """The dollars the gateway reported for a call's draws, or None where any draw reported none."""
    if not costs or any(cost is None for cost in costs):
        return None
    return sum(costs)


def call_dollars(completion: Completion) -> float:
    """What a completion cost: the gateway's reported cost, else the PRICES rate of its tokens."""
    if completion.cost is not None:
        return completion.cost
    return price(completion.model, completion.tokens_in, completion.tokens_out)


def priced(model: str) -> bool:
    """Says whether price knows a model."""
    return model in PRICES or model in CLAUDE_CODE_MODELS or model in LIVE_PRICES


def api_price(model: str, tokens_in: int, tokens_out: int) -> float:
    """What a call would cost on its maker's API: API_EQUIVALENT for a Claude Code model, the
    PRICES rate for every other."""
    if model not in API_EQUIVALENT:
        return price(model, tokens_in, tokens_out)
    rate_in, rate_out = API_EQUIVALENT[model]
    return tokens_in * rate_in / 1_000_000 + tokens_out * rate_out / 1_000_000


class WrongModel(Exception):
    """Raised when a Claude Code reply names a model other than the one asked for."""


class ClaudeCodeError(Exception):
    """Raised when the claude command exits non-zero or reports an error."""


# The parent session's variables that would tie the child to it.
DROP_ENV_PREFIXES = ("CLAUDE_CODE_", "AEO_")
DROP_ENV = frozenset({"CLAUDECODE", "CLAUDE_PID", "CLAUDE_EFFORT"})

# The seconds one claude call may take, and the seconds waited between two calls.
CLAUDE_TIMEOUT_SECONDS = 1800
CLAUDE_PAUSE_SECONDS = 5.0

# A command line on Windows ends at 32767 characters, and the system prompt rides on it.
MAX_COMMAND_LINE = 32_000


def run_claude(args: list[str], cwd: Path, env: dict, stdin: str) -> tuple[int, str, str]:
    """Runs one claude command and returns its exit code, its output and its errors."""
    done = subprocess.run(args, cwd=cwd, env=env, input=stdin, capture_output=True, text=True,
                          encoding="utf-8", timeout=CLAUDE_TIMEOUT_SECONDS)
    return done.returncode, done.stdout, done.stderr


def json_object(text: str) -> str:
    """The first JSON object a reply holds, as text, or the reply as it came when it holds none."""
    decoder = jsonlib.JSONDecoder()
    start = text.find("{")
    while start >= 0:
        try:
            _, end = decoder.raw_decode(text, start)
        except ValueError:
            start = text.find("{", start + 1)
            continue
        return text[start:end]
    return text


class ClaudeCode:
    """Sends a call to headless Claude Code: `claude -p` with no tools, no settings, no MCP and
    no saved session, from an empty folder outside the repository, the system prompt on the
    command line, the rest of the conversation on stdin, the call's max_tokens as the reply cap
    and CLAUDE_THINKING_EFFORT as the effort. Calls go one at a time, with pause seconds
    between them. The runner is injectable so a test can fake the subprocess."""

    _lock = threading.Lock()

    def __init__(self, runner=None, pause: float = CLAUDE_PAUSE_SECONDS):
        self.runner = runner or run_claude
        self.pause = pause
        self._sent = 0

    @staticmethod
    def stdin_of(messages: list[dict]) -> str:
        """The conversation after the system prompt as one text: the first message as it is,
        and a later turn under a line saying whose it is."""
        turns = [message for message in messages if message["role"] != "system"]
        parts = [turns[0]["content"]] if turns else []
        for message in turns[1:]:
            who = "YOUR REPLY" if message["role"] == "assistant" else "THE NEXT MESSAGE"
            parts.append(f"{who}\n\n{message['content']}")
        return "\n\n".join(parts)

    def complete(self, model: str, messages: list[dict], max_tokens: int, json: bool = True) -> Completion:
        """One call, its reply text and its usage. Raises WrongModel when the reply names
        another model, ClaudeCodeError when the command fails, NoReply when it returns no text
        or a reply continued past its cap, of which only the last part comes back."""
        system = "\n\n".join(message["content"] for message in messages if message["role"] == "system")
        args = [
            "claude", "-p",
            "--output-format", "json",
            "--model", CLAUDE_CODE_MODELS[model],
            "--effort", CLAUDE_THINKING_EFFORT,
            "--tools", "",
            "--strict-mcp-config",
            "--disable-slash-commands",
            "--setting-sources", "",
            "--no-session-persistence",
            "--system-prompt", system,
        ]
        if len(subprocess.list2cmdline(args)) > MAX_COMMAND_LINE:
            raise ClaudeCodeError("the system prompt is too long for one command line")
        env = {name: value for name, value in os.environ.items()
               if name not in DROP_ENV and not name.startswith(DROP_ENV_PREFIXES)}
        # The command line takes no reply cap; headless Claude Code reads it from this variable.
        env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(max_tokens)
        with self._lock:
            if self._sent and self.pause:
                time.sleep(self.pause)
            self._sent += 1
            cwd = Path(tempfile.mkdtemp(prefix="rlm-claude-"))
            started = time.monotonic()
            try:
                code, out, err = self.runner(args, cwd, env, self.stdin_of(messages))
            finally:
                shutil.rmtree(cwd, ignore_errors=True)
            seconds = time.monotonic() - started
        try:
            reply = jsonlib.loads(out)
        except (ValueError, TypeError):
            reply = None
        if code != 0 or not isinstance(reply, dict) or reply.get("is_error"):
            raise ClaudeCodeError(f"claude exited {code}: {(err or out or '').strip()[:300]}")
        named = sorted(reply.get("modelUsage") or {})
        if not named or not all(CLAUDE_CODE_REPLY[model].match(name) for name in named):
            raise WrongModel(f"the reply for {model} came from {named or 'no model named'}")
        usage = reply.get("usage") or {}
        tokens_in = sum(int(usage.get(name) or 0) for name in
                        ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        tokens_out = int(usage.get("output_tokens") or 0)
        text = reply.get("result") or ""
        if int(reply.get("num_turns") or 1) > 1:
            # A reply that ran past its cap is continued in a further turn, and the result holds
            # only the last turn's text: the rest of the reply is lost.
            raise NoReply(f"{model} ran past its reply cap and was continued", tokens_in=tokens_in,
                          tokens_out=tokens_out, seconds=seconds)
        if not text.strip():
            raise NoReply(f"{model} returned no reply", tokens_in=tokens_in, tokens_out=tokens_out,
                          seconds=seconds)
        if json:
            text = json_object(text)
        return Completion(text=text, tokens_in=tokens_in, tokens_out=tokens_out, seconds=seconds, model=model)


def known_prices(model: str) -> list[tuple[float, float]]:
    """Every rate the repository has priced a model at, the current one first.

    Raises KeyError for a model outside the current table. A past table that repeats the
    current rate is left out, so each rate appears once.
    """
    rates = [PRICES[model]]
    for table in PAST_PRICES:
        rate = table.get(model)
        if rate is not None and rate not in rates:
            rates.append(rate)
    return rates


class Gateway:
    """Sends model calls to OpenRouter or to headless Claude Code. The transport and the Claude
    Code runner are injectable so a test can fake each.

    The OpenRouter key is api_key, else OPENROUTER_API_KEY, and may be empty: a run that names
    no OpenRouter model needs none.
    """

    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        base_url: str = BASE_URL,
        rate_limit_waits: tuple[float, ...] = RATE_LIMIT_WAITS,
        claude_code: "ClaudeCode | None" = None,
    ):
        self.claude_code = claude_code or ClaudeCode()
        self.api_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.rate_limit_waits = tuple(rate_limit_waits)
        self.context_lengths: dict[str, int] = {}
        self._client = httpx.Client(transport=transport, timeout=TIMEOUT_SECONDS)

    def models(self) -> dict[str, tuple[float, float]]:
        """Reads the gateway's model list into one rate per model, per million tokens.

        The list prices per token as a string; each rate is multiplied by a million and rounded
        to six decimals. The list is free and needs no key: with an empty key no Authorization
        header is sent. Raises httpx.HTTPStatusError when the gateway answers outside 2xx.
        """
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        response = self._client.get(f"{self.base_url}/models", headers=headers)
        response.raise_for_status()
        found: dict[str, tuple[float, float]] = {}
        for entry in response.json().get("data", []):
            pricing = entry.get("pricing") or {}
            if "prompt" not in pricing or "completion" not in pricing:
                continue
            found[entry["id"]] = (
                round(float(pricing["prompt"]) * 1_000_000, 6),
                round(float(pricing["completion"]) * 1_000_000, 6),
            )
            if entry.get("context_length"):
                self.context_lengths[entry["id"]] = int(entry["context_length"])
        return found

    def _post(self, body: dict) -> httpx.Response:
        """Posts one chat completion. A dropped connection is posted again once after
        TRANSPORT_RETRY_WAIT seconds; a second transport failure is raised."""
        try:
            return self._client.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except httpx.TransportError:
            time.sleep(TRANSPORT_RETRY_WAIT)
            return self._client.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )

    def _send(self, body: dict) -> tuple[dict, float]:
        """Posts one chat completion and returns the answered body and the wall seconds.

        A 429 is posted again after each wait of rate_limit_waits, and the seconds waited count
        in the wall seconds. Raises httpx.HTTPStatusError when the gateway answers outside the
        2xx range, a 429 included once the waits are spent, or httpx.TransportError when the
        connection drops twice in a row.
        """
        started = time.monotonic()
        for wait in (*self.rate_limit_waits, None):
            response = self._post(body)
            if response.status_code != 429 or wait is None:
                break
            time.sleep(wait)
        response.raise_for_status()
        return response.json(), time.monotonic() - started

    def complete(
        self, model: str, messages: list[dict], max_tokens: int, json: bool = True
    ) -> Completion:
        """Sends one chat completion and returns its text with the reported usage.

        The body asks for a JSON object unless json is false, which is how a call that wants
        prose back is made. An answer carrying no content, and an answer cut off by the
        max_tokens budget, are not replies: either is sent again once, and two of them raise
        NoReply. The completion carries the tokens of every draw it took. Raises
        httpx.HTTPStatusError when the gateway answers outside the 2xx range. A claude-code/ id
        goes to headless Claude Code instead, through ClaudeCode.complete, and one that
        CLAUDE_CODE_MODELS does not hold raises KeyError before anything is sent.
        """
        if model.startswith(CLAUDE_CODE_PREFIX):
            if model not in CLAUDE_CODE_MODELS:
                raise KeyError(model)
            return self.claude_code.complete(model, messages, max_tokens, json=json)
        body = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "seed": 0,
            "max_tokens": max_tokens,
            "reasoning": REASONING.get(model, {"enabled": False}),
            "provider": {"ignore": list(IGNORED_PROVIDERS)},
            "usage": {"include": True},
        }
        if json:
            body["response_format"] = {"type": "json_object"}
        seconds = 0.0
        tokens_in = 0
        tokens_out = 0
        refused: list[str] = []
        costs: list[float | None] = []
        all_cut_off = True
        for _ in range(MAX_DRAWS):
            data, took = self._send(body)
            seconds += took
            usage = data.get("usage") or {}
            drawn_out = int(usage.get("completion_tokens", 0))
            tokens_in += int(usage.get("prompt_tokens", 0))
            tokens_out += drawn_out
            costs.append(None if usage.get("cost") is None else float(usage["cost"]))
            choice = (data.get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content") or ""
            finish_reason = choice.get("finish_reason")
            if text and finish_reason != CUT_OFF:
                return Completion(
                    text=text,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    seconds=seconds,
                    model=model,
                    cost=reported_cost(costs),
                )
            all_cut_off = all_cut_off and finish_reason == CUT_OFF
            # OpenRouter names the provider that served the call at the top of the body, so
            # the message can say which one answered with no reply in it.
            refused.append(
                refused_draw(data.get("provider"), finish_reason, drawn_out, len(text))
            )
        raise NoReply(
            f"{model} returned no reply on {len(refused)} draws: " + ", then ".join(refused),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            seconds=seconds,
            cut_off=all_cut_off,
            cost=reported_cost(costs),
        )


class Batch:
    """One run of calls that becomes one ledger row. Accumulates the reported token counts.

    A pass runs several documents at once, so record is called from many threads and takes a
    lock.
    """

    def __init__(self, ledger: "Ledger", sample: str, phase: int, model: str, tokens_in: int, tokens_out: int):
        self._ledger = ledger
        self.sample = sample
        self.phase = phase
        self.model = model
        self.estimated_in = tokens_in
        self.estimated_out = tokens_out
        self.tokens_in = 0
        self.tokens_out = 0
        self.dollars = 0.0
        self._lock = threading.Lock()

    def record(self, completion: Completion) -> Completion:
        """Adds one completion's reported tokens and its cost to the batch and returns it."""
        with self._lock:
            self.tokens_in += completion.tokens_in
            self.tokens_out += completion.tokens_out
            self.dollars += call_dollars(completion)
        return completion

    def __enter__(self) -> "Batch":
        estimate = price(self.model, self.estimated_in, self.estimated_out)
        print(
            f"estimate: {self.estimated_in} tokens in, {self.estimated_out} tokens out, "
            f"${estimate:.4f} on {self.model}"
        )
        spent = self._ledger.spent(self.phase)
        cap = PHASE_CAPS[self.phase]
        if spent + estimate > cap:
            raise CapExceeded(
                f"phase {self.phase} has spent ${spent:.4f} and this batch estimates "
                f"${estimate:.4f}, past the ${cap:.2f} cap"
            )
        balance = self._ledger.balance()
        if balance - estimate < 0:
            raise CapExceeded(
                f"${balance:.4f} left of the ${TOTAL_CEILING:.2f} ceiling and this batch "
                f"estimates ${estimate:.4f}"
            )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        paid_for_nothing = exc_type is not None and issubclass(exc_type, NoReply) and (self.tokens_in or self.tokens_out)
        if exc_type is None or paid_for_nothing:
            self._ledger.append(
                self.sample, self.phase, self.model, self.tokens_in, self.tokens_out, dollars=self.dollars
            )
        return False


class Ledger:
    """Reads and appends the markdown table of LEDGER.md."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def rows(self) -> list[dict]:
        """Reads the table into one dict per row, in file order."""
        found = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            match = _LEDGER_ROW.match(line)
            if not match or match.group(1) == "date" or match.group(1).startswith("-"):
                continue
            date, sample, phase, model, tokens_in, tokens_out, dollars, balance = match.groups()
            found.append(
                {
                    "date": date,
                    "sample": sample,
                    "phase": phase,
                    "model": model,
                    "tokens_in": int(tokens_in),
                    "tokens_out": int(tokens_out),
                    "dollars": float(dollars),
                    "balance": float(balance),
                }
            )
        return found

    def balance(self) -> float:
        """The balance the last row carries, or the total ceiling when the table is empty."""
        rows = self.rows()
        return rows[-1]["balance"] if rows else TOTAL_CEILING

    def spent(self, phase: int) -> float:
        """Sums the dollars of every row of one phase."""
        return sum(row["dollars"] for row in self.rows() if row["phase"] == str(phase))

    def batch(self, sample: str, phase: int, model: str, tokens_in: int, tokens_out: int) -> Batch:
        """Opens a batch that prints its estimate, refuses past a cap, and writes one row."""
        return Batch(self, sample, phase, model, tokens_in, tokens_out)

    def append(
        self, sample: str, phase: int, model: str, tokens_in: int, tokens_out: int, dollars: float | None = None
    ) -> None:
        """Appends one row with the reported tokens, the dollars and the new balance. Without
        dollars the row is priced at the PRICES rate."""
        if dollars is None:
            dollars = price(model, tokens_in, tokens_out)
        dollars = round(dollars, 4)
        balance = round(self.balance() - dollars, 4)
        date = datetime.date.today().isoformat()
        row = (
            f"| {date} | {sample} | {phase} | {model} | {tokens_in} | {tokens_out} | "
            f"{dollars:.4f} | {balance:.4f} |\n"
        )
        text = self.path.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        self.path.write_text(text + row, encoding="utf-8")


class MeteredBatch:
    """One batch of a Meter: the tokens its calls reported, counted onto the meter as they come.

    With a ledger batch underneath, entering and leaving are that batch's, so it prints the
    estimate, refuses past a cap and books its row on a clean exit. Without one, entering prints
    the estimate and nothing is refused or written.
    """

    def __init__(
        self,
        meter: "Meter",
        inner: Batch | None,
        model: str,
        tokens_in: int,
        tokens_out: int,
    ):
        self._meter = meter
        self._inner = inner
        self.model = model
        self.estimated_in = tokens_in
        self.estimated_out = tokens_out
        self.tokens_in = 0
        self.tokens_out = 0
        self._lock = threading.Lock()

    def record(self, completion: Completion) -> Completion:
        """Adds one completion's reported tokens to the batch and the meter and returns it."""
        if self._inner is not None:
            self._inner.record(completion)
        with self._lock:
            self.tokens_in += completion.tokens_in
            self.tokens_out += completion.tokens_out
        self._meter.add(self.model, completion.tokens_in, completion.tokens_out, completion.cost)
        return completion

    def __enter__(self) -> "MeteredBatch":
        if self._inner is not None:
            self._inner.__enter__()
        else:
            estimate = price(self.model, self.estimated_in, self.estimated_out)
            print(
                f"estimate: {self.estimated_in} tokens in, {self.estimated_out} tokens out, "
                f"${estimate:.4f} on {self.model}"
            )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if self._inner is not None:
            return bool(self._inner.__exit__(exc_type, exc, traceback))
        return False


class Meter:
    """Counts the dollars of every batch it opens, as the gateway reported them, whether the batch ends
    cleanly or raises, since a call that returned was paid either way.

    It has the batch shape of Ledger, so a stage takes it where it takes a ledger. Without a
    ledger nothing is capped and nothing is written; with one, each batch is also booked there.
    """

    def __init__(self, ledger: Ledger | None = None):
        self.ledger = ledger
        self.tokens_in = 0
        self.tokens_out = 0
        self.dollars = 0.0
        self._lock = threading.Lock()

    def add(self, model: str, tokens_in: int, tokens_out: int, cost: float | None = None) -> None:
        """Counts one call's reported tokens and its cost, or their PRICES rate where it has none."""
        with self._lock:
            self.tokens_in += tokens_in
            self.tokens_out += tokens_out
            self.dollars += price(model, tokens_in, tokens_out) if cost is None else cost

    def batch(
        self, sample: str, phase: int, model: str, tokens_in: int, tokens_out: int
    ) -> MeteredBatch:
        """Opens a batch that counts onto this meter, and onto the ledger's row when there is one."""
        inner = (
            self.ledger.batch(sample, phase, model, tokens_in, tokens_out)
            if self.ledger is not None
            else None
        )
        return MeteredBatch(self, inner, model, tokens_in, tokens_out)
