"""The one module that calls the gateway, and the ledger that pays for the call.

Every model call in this repository goes through Gateway.complete, which posts one chat
completion to OpenRouter with temperature 0, a fixed seed, JSON output mode and reasoning off.
Nothing else opens a socket.

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
# model list on 2026-09-06.
PRICES: dict[str, tuple[float, float]] = {
    "openai/gpt-5.6-luna": (0.200, 1.200),
    "deepseek/deepseek-v4-flash-0731": (0.050, 0.100),
    "deepseek/deepseek-v4-pro": (0.657, 1.314),
    "z-ai/glm-5.3": (1.400, 4.400),
    "z-ai/glm-5.3-flash": (0.075, 0.250),
}

# The tables the repository has priced a call at before, newest first. A ledger row written
# before a price moved reconciles at one of these, so it is kept here.
PAST_PRICES: tuple[dict[str, tuple[float, float]], ...] = (
    {
        "openai/gpt-5.6-luna": (0.200, 1.200),
        "deepseek/deepseek-v4-flash-0731": (0.065, 0.180),
        "deepseek/deepseek-v4-pro": (0.870, 1.740),
        "z-ai/glm-5.3": (1.400, 4.400),
        "z-ai/glm-5.3-flash": (0.075, 0.250),
    },
)

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

    def complete(self, model: str, messages: list[dict], max_tokens: int) -> Completion:
        """Sends one chat completion and returns its text with the reported usage.

        Raises httpx.HTTPStatusError when the gateway answers outside the 2xx range.
        """
        body = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "seed": 0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "reasoning": {"enabled": False},
        }
        started = time.monotonic()
        response = self._client.post(
            f"{self.base_url}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        response.raise_for_status()
        seconds = time.monotonic() - started
        data = response.json()
        usage = data.get("usage") or {}
        return Completion(
            text=data["choices"][0]["message"].get("content") or "",
            tokens_in=int(usage.get("prompt_tokens", 0)),
            tokens_out=int(usage.get("completion_tokens", 0)),
            seconds=seconds,
            model=model,
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
