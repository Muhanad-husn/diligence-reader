"""The one module that calls the gateway, and the ledger that pays for the call.

Every model call in this repository goes through Gateway.complete, which posts one chat
completion to OpenRouter with temperature 0, a fixed seed, JSON output mode, the reasoning
object REASONING gives its model, and the providers of IGNORED_PROVIDERS left out of the
routing. Nothing else opens a socket.

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
"""

from __future__ import annotations

import datetime
import math
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

import httpx

# Per million tokens, prompt then completion, as PLAN.md section 5 reads, from the gateway's
# model list on 2026-09-07. DeepSeek V4 Flash and DeepSeek V4 Pro both went up; Luna and the
# two GLM endpoints read what they read on 2026-09-06.
PRICES: dict[str, tuple[float, float]] = {
    "openai/gpt-5.6-luna": (0.200, 1.200),
    "deepseek/deepseek-v4-flash-0731": (0.140, 0.280),
    "deepseek/deepseek-v4-pro": (0.955, 1.911),
    "z-ai/glm-5.3": (1.400, 4.400),
    "z-ai/glm-5.3-flash": (0.075, 0.250),
}

# The tables the repository has priced a call at before, newest first. A ledger row written
# before a price moved reconciles at one of these, so it is kept here.
PAST_PRICES: tuple[dict[str, tuple[float, float]], ...] = (
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

# The reasoning object each model's request carries. The two GLM endpoints answer 400 when
# reasoning is disabled, so they carry a low effort object instead; every other model of PRICES
# carries reasoning off.
REASONING: dict[str, dict] = {
    "openai/gpt-5.6-luna": {"enabled": False},
    "deepseek/deepseek-v4-flash-0731": {"enabled": False},
    "deepseek/deepseek-v4-pro": {"enabled": False},
    "z-ai/glm-5.3": {"effort": "low"},
    "z-ai/glm-5.3-flash": {"effort": "low"},
}

# The gateway serves one model from several providers and picks one per call. A provider named
# here ignores the reasoning object above: it spends the whole max_tokens budget on reasoning
# and answers with a null content and a finish reason of length, so the call pays in full and
# returns nothing. Every call leaves these out. Wafer was found doing this to z-ai/glm-5.3-flash
# on 2026-09-09, burning 6000 reasoning tokens on a prompt the other providers answer with 10
# to 26; the same prompt had been answered a day earlier and the ten documents it hit came back
# with no note at all, three runs in a row.
IGNORED_PROVIDERS = ("Wafer",)

# The finish reason a draw carries when it ran out of the max_tokens budget. The reply then
# stops wherever the budget ran out, which is usually mid sentence, and on a provider that
# ignores the reasoning object it stops after a few hundred characters of a paid full budget.
CUT_OFF = "length"

# How many times one request is drawn before an answer with no reply in it is given up on. The
# second draw is what the router sends somewhere else; a third would pay a third time for the
# same answer.
MAX_DRAWS = 2

# The total ceiling and the per phase caps, from PLAN.md section 6.
TOTAL_CEILING = 50.0
PHASE_CAPS: dict[int, float] = {0: 0.0, 1: 0.0, 2: 8.0, 3: 0.0, 4: 0.0, 5: 8.0, 6: 15.0, 7: 4.0}

BASE_URL = "https://openrouter.ai/api/v1"
TIMEOUT_SECONDS = 300.0

_LEDGER_ROW = re.compile(
    r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|$"
)


class CapExceeded(Exception):
    """Raised before a request when its estimate would pass a phase cap or the total ceiling."""


class NoReply(Exception):
    """Raised when two draws of one request both came back with no reply in them."""


@dataclass(frozen=True)
class Completion:
    """One model reply: its text, the gateway's reported usage, the wall seconds and the model."""

    text: str
    tokens_in: int
    tokens_out: int
    seconds: float
    model: str


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


def price(model: str, tokens_in: int, tokens_out: int) -> float:
    """Prices a call at the PRICES rate. Raises KeyError for a model outside the table."""
    rate_in, rate_out = PRICES[model]
    return tokens_in * rate_in / 1_000_000 + tokens_out * rate_out / 1_000_000


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
    """Posts chat completions to the gateway. The transport is injectable so a test can fake it."""

    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        base_url: str = BASE_URL,
    ):
        self.api_key = api_key if api_key is not None else os.environ["OPENROUTER_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(transport=transport, timeout=TIMEOUT_SECONDS)

    def models(self) -> dict[str, tuple[float, float]]:
        """Reads the gateway's model list into one rate per model, per million tokens.

        The list prices per token as a string; each rate is multiplied by a million and rounded
        to six decimals. Raises httpx.HTTPStatusError when the gateway answers outside 2xx.
        """
        response = self._client.get(
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
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
        return found

    def _send(self, body: dict) -> tuple[dict, float]:
        """Posts one chat completion and returns the answered body and the wall seconds.

        Raises httpx.HTTPStatusError when the gateway answers outside the 2xx range.
        """
        started = time.monotonic()
        response = self._client.post(
            f"{self.base_url}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
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
        httpx.HTTPStatusError when the gateway answers outside the 2xx range.
        """
        body = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "seed": 0,
            "max_tokens": max_tokens,
            "reasoning": REASONING.get(model, {"enabled": False}),
            "provider": {"ignore": list(IGNORED_PROVIDERS)},
        }
        if json:
            body["response_format"] = {"type": "json_object"}
        seconds = 0.0
        tokens_in = 0
        tokens_out = 0
        refused: list[str] = []
        for _ in range(MAX_DRAWS):
            data, took = self._send(body)
            seconds += took
            usage = data.get("usage") or {}
            drawn_out = int(usage.get("completion_tokens", 0))
            tokens_in += int(usage.get("prompt_tokens", 0))
            tokens_out += drawn_out
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
                )
            # OpenRouter names the provider that served the call at the top of the body, so
            # the message can say which one answered with no reply in it.
            refused.append(
                refused_draw(data.get("provider"), finish_reason, drawn_out, len(text))
            )
        raise NoReply(
            f"{model} returned no reply on {len(refused)} draws: " + ", then ".join(refused)
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
        self._lock = threading.Lock()

    def record(self, completion: Completion) -> Completion:
        """Adds one completion's reported tokens to the batch and returns it."""
        with self._lock:
            self.tokens_in += completion.tokens_in
            self.tokens_out += completion.tokens_out
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
        if exc_type is None:
            self._ledger.append(self.sample, self.phase, self.model, self.tokens_in, self.tokens_out)
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

    def append(self, sample: str, phase: int, model: str, tokens_in: int, tokens_out: int) -> None:
        """Appends one row with the reported tokens, the price and the new balance."""
        dollars = round(price(model, tokens_in, tokens_out), 4)
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
