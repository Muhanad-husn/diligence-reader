"""The models a task may run on, by provider, and what a token of each costs.

A model id names its provider by its prefix. `claude-code/<model>` runs on headless Claude
Code. `bedrock/<model>` runs on AWS Bedrock through boto3. `anthropic/<model>` runs on the
Anthropic API when the id is one of ANTHROPIC_IDS. Every other id is an OpenRouter id, which
is checked against OpenRouter's own model list, so an `anthropic/` id that ANTHROPIC_IDS does
not carry is read as an OpenRouter id and refused there when OpenRouter does not list it.

The two direct providers keep a small table each. An id outside the table is refused before any
call is made, so a misspelt id costs nothing. A Bedrock id differs from the Anthropic one, and
the table holds both.

Prices are per million tokens, from Anthropic's pricing page read on 2026-10-06: Haiku 4.5 is
$1 in and $5 out, Sonnet 5.5 is $2 in and $10 out. A cache read costs a tenth of the input
rate and a five minute cache write a quarter more. The Message Batches API takes half off every
rate and stacks with caching. Bedrock's global inference profile is priced as Anthropic's API
is; a geographic profile (eu. or us.) carries the ten percent premium the same page gives for
regional endpoints of Sonnet 4.5 and later, which the estimate and the books apply to both
models so that a cap is never under.
"""

from __future__ import annotations

from dataclasses import dataclass

CLAUDE_CODE = "claude-code"
ANTHROPIC = "anthropic"
BEDROCK = "bedrock"
OPENROUTER = "openrouter"

# The region Bedrock calls go to when the user sets none.
DEFAULT_REGION = "eu-central-1"

# What the Message Batches API takes off every rate.
BATCH_DISCOUNT = 0.5

# What a geographic inference profile of Bedrock costs over the global one.
BEDROCK_GEO_PREMIUM = 1.10


@dataclass(frozen=True)
class Rates:
    """Dollars per million tokens: input, output, cache read and a five minute cache write."""

    input: float
    output: float
    cache_read: float
    cache_write: float


@dataclass(frozen=True)
class Family:
    """What one Claude model is, whichever provider serves it.

    sampling says whether the model takes a temperature: Sonnet 5.5 answers 400 to one.
    context is its window in tokens. cache_minimum is the shortest prompt it caches.
    """

    rates: Rates
    context: int
    sampling: bool
    cache_minimum: int


FAMILIES: dict[str, Family] = {
    "claude-haiku-4-5": Family(Rates(1.0, 5.0, 0.10, 1.25), 200_000, True, 4096),
    "claude-sonnet-5-5": Family(Rates(2.0, 10.0, 0.20, 2.50), 1_000_000, False, 512),
}

# anthropic/<id> as the user types it: the family and the id the Anthropic API takes.
ANTHROPIC_IDS: dict[str, tuple[str, str]] = {
    "anthropic/claude-haiku-4-5": ("claude-haiku-4-5", "claude-haiku-4-5-20251001"),
    "anthropic/claude-haiku-4-5-20251001": ("claude-haiku-4-5", "claude-haiku-4-5-20251001"),
    "anthropic/claude-sonnet-5-5": ("claude-sonnet-5-5", "claude-sonnet-5-5"),
}

# bedrock/<id> as the user types it: the family and the Bedrock model id, to which a region's
# inference profile prefix is put in front.
BEDROCK_IDS: dict[str, tuple[str, str]] = {
    "bedrock/claude-haiku-4-5": ("claude-haiku-4-5", "anthropic.claude-haiku-4-5-20251001-v1:0"),
    "bedrock/claude-sonnet-5-5": ("claude-sonnet-5-5", "anthropic.claude-sonnet-5-5"),
}

# The direct ids a person may be offered, one per model.
DIRECT_CHOICES = (
    "anthropic/claude-haiku-4-5",
    "anthropic/claude-sonnet-5-5",
    "bedrock/claude-haiku-4-5",
    "bedrock/claude-sonnet-5-5",
)


def provider_of(model: str) -> str:
    """The provider a model id names: claude-code, bedrock, anthropic or openrouter."""
    if model.startswith("claude-code/"):
        return CLAUDE_CODE
    if model.startswith("bedrock/"):
        return BEDROCK
    if model in ANTHROPIC_IDS:
        return ANTHROPIC
    return OPENROUTER


def is_direct(model: str) -> bool:
    """Says whether a model is served by the Anthropic API or Bedrock."""
    return provider_of(model) in (ANTHROPIC, BEDROCK)


def known_direct(model: str) -> bool:
    """Says whether a direct model id is in its provider's table."""
    return model in ANTHROPIC_IDS or model in BEDROCK_IDS


def family_name(model: str) -> str:
    """The family a direct model belongs to. Raises KeyError for an id outside both tables."""
    table = ANTHROPIC_IDS if model in ANTHROPIC_IDS else BEDROCK_IDS
    return table[model][0]


def family_of(model: str) -> Family:
    """The Family of a direct model. Raises KeyError for an id outside both tables."""
    return FAMILIES[family_name(model)]


# Sonnet 5.5 through Claude Code, the model the tree and the writer were tuned on.
CLAUDE_CODE_SONNET = "claude-code/claude-sonnet-5-5"


def is_sonnet_tier(model: str) -> bool:
    """Says whether a model is Sonnet 5.5 by any route: the tree's group step and the writer
    treat it alike, with a window of a million tokens and a reply that is not held to a short cap."""
    if model == CLAUDE_CODE_SONNET:
        return True
    return known_direct(model) and family_name(model) == "claude-sonnet-5-5"


def anthropic_model_id(model: str) -> str:
    """The id the Anthropic API takes for an anthropic/ id. Raises KeyError for an unknown one."""
    return ANTHROPIC_IDS[model][1]


def profile_prefix(region: str) -> str:
    """The inference profile prefix of a Bedrock region: eu., us., or global. for any other."""
    if region.startswith("eu-"):
        return "eu."
    if region.startswith("us-"):
        return "us."
    return "global."


def bedrock_model_id(model: str, region: str = DEFAULT_REGION) -> str:
    """The Bedrock model id of a bedrock/ id in a region, with its inference profile prefix.
    Raises KeyError for an unknown id."""
    return profile_prefix(region) + BEDROCK_IDS[model][1]


def regional_factor(model: str, region: str = DEFAULT_REGION) -> float:
    """What a model's rates are multiplied by in a region: the geographic premium on a Bedrock
    geographic profile, one on everything else."""
    if provider_of(model) == BEDROCK and profile_prefix(region) != "global.":
        return BEDROCK_GEO_PREMIUM
    return 1.0


def cost(
    model: str,
    fresh: int,
    output: int,
    cache_read: int = 0,
    cache_write: int = 0,
    batch: bool = False,
    region: str = DEFAULT_REGION,
) -> float:
    """The dollars one direct call cost, from the tokens its usage reports.

    fresh is the input tokens that were neither read from the cache nor written to it. The
    batch discount takes half off every rate and the regional factor scales them.
    """
    rates = family_of(model).rates
    dollars = (
        fresh * rates.input
        + output * rates.output
        + cache_read * rates.cache_read
        + cache_write * rates.cache_write
    ) / 1_000_000
    if batch:
        dollars *= 1 - BATCH_DISCOUNT
    return dollars * regional_factor(model, region)


def estimate(
    model: str,
    tokens_in: int,
    tokens_out: int,
    batch: bool = False,
    region: str = DEFAULT_REGION,
) -> float:
    """The dollars an estimate of tokens costs on a direct model, every input token at the
    plain input rate: the cache is a saving the estimate does not count on."""
    return cost(model, tokens_in, tokens_out, batch=batch, region=region)
