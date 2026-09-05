"""Normalises the surface of a number or a date to one comparable value.

`normalise_amount` maps a surface such as `$12,400,000`, `$12.4m`, `912.8m`, `30.1%`, `45-day`
or `twenty-four (24) months` to a float and, where the surface itself says one, a unit. The
spelled-out form is read from its parenthesised digits, so no English number table is needed.
`normalise_date` maps `2025-10-18`, `18 October 2025`, `11 Dec 2025` and `October 18, 2025` to
one ISO string.

The index applies these functions to what it reads out of a document and the phase 1 tests
apply them to the key's own values, so both sides of a comparison go through the same code and
no rule is written against a key string.
"""

from __future__ import annotations

import datetime
import re

# The units an index record may carry. A record whose unit is not one of these carries null.
UNITS = frozenset({"USD", "percent", "records", "months", "days", "count"})

_SCALES = {
    "k": 1_000.0,
    "thousand": 1_000.0,
    "m": 1_000_000.0,
    "mm": 1_000_000.0,
    "million": 1_000_000.0,
    "b": 1_000_000_000.0,
    "bn": 1_000_000_000.0,
    "billion": 1_000_000_000.0,
    "tn": 1_000_000_000_000.0,
    "trillion": 1_000_000_000_000.0,
}

_NUMBER = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"

# One amount: an optional dollar sign, the number with an optional magnitude suffix, an
# optional percent sign and an optional unit word right next to it. A number in parentheses is
# taken with its brackets so that "(24) months" reads as twenty-four months.
AMOUNT = re.compile(
    r"(?P<currency>\$\s?)?"
    r"(?P<open>\()?"
    rf"(?P<number>{_NUMBER})"
    r"(?:(?P<suffix>mm|bn|tn|[mkb])(?![A-Za-z0-9]))?"
    r"(?P<close>\))?"
    r"(?:\s?(?P<spelled>million|billion|thousand|trillion)\b)?"
    r"(?P<percent>\s?%)?"
    r"(?:[\s-]?(?P<word>records?|months?|days?)\b)?",
    re.IGNORECASE,
)

_MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

_ISO_DATE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")
_MONTH_DAY_YEAR = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),\s*(\d{4})\b")

_WORD_UNITS = {"record": "records", "month": "months", "day": "days"}


def _amount_of(match: re.Match) -> tuple[float, str | None]:
    """Turns one AMOUNT match into its value and the unit its own surface names."""
    value = float(match.group("number").replace(",", ""))
    scale = match.group("suffix") or match.group("spelled")
    if scale:
        value *= _SCALES[scale.lower()]
    unit = None
    if match.group("currency"):
        unit = "USD"
    elif match.group("percent"):
        unit = "percent"
    elif match.group("word"):
        unit = _WORD_UNITS[match.group("word").lower().rstrip("s")]
    return value, unit


def normalise_amount(surface: str) -> tuple[float, str | None]:
    """Reads a surface into its value and the unit the surface itself names, or None.

    Raises ValueError when the surface holds no number.
    """
    match = AMOUNT.search(str(surface))
    if match is None:
        raise ValueError(f"no amount in {surface!r}")
    return _amount_of(match)


def date_matches(text: str) -> list[tuple[int, int, str]]:
    """Finds every date in a text and returns each one's span and its ISO string."""
    found = []
    for pattern, order in (
        (_ISO_DATE, "ymd"),
        (_DAY_MONTH_YEAR, "dmy"),
        (_MONTH_DAY_YEAR, "mdy"),
    ):
        for match in pattern.finditer(text):
            first, second, third = match.groups()
            if order == "ymd":
                year, month, day = int(first), int(second), int(third)
            elif order == "dmy":
                month = _MONTHS.get(second.lower())
                year, day = int(third), int(first)
            else:
                month = _MONTHS.get(first.lower())
                year, day = int(third), int(second)
            if month is None:
                continue
            try:
                datetime.date(year, month, day)
            except ValueError:
                continue
            found.append((match.start(), match.end(), f"{year:04d}-{month:02d}-{day:02d}"))
    found.sort()
    return found


def normalise_date(surface: str) -> str:
    """Reads a surface into one ISO date string.

    Raises ValueError when the surface holds no date this phase reads.
    """
    found = date_matches(str(surface))
    if not found:
        raise ValueError(f"no date in {surface!r}")
    return found[0][2]
