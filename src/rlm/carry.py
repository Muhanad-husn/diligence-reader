"""Says whether a piece of text carries a value, by numbers, days and stemmed words.

This is the rule phase 4 wrote for the dossier's comparison rows and phase 5 now grades a
report's comparisons by, so it lives here and both read it from one place. A value is carried
when every number of it appears, every day of it appears, and every word of it that says
something appears with one plural or tense ending dropped. Days are cut out of the text before
the numbers and the words are read, so 2025-10-18 is one day and not the numbers 2025, 10 and
18.
"""

from __future__ import annotations

import re

from rlm.amounts import date_matches
from rlm.notes import straighten

# The words a value carries that say nothing about where it came from, before stemming.
STOP_SOURCE = (
    "a an and any are as at be been by for from has have in is it its no not of on or "
    "that the their there this to was were what which with"
)

_LETTERS = re.compile(r"[A-Za-z]{2,}")
_DIGITS = re.compile(r"[0-9]+")

# The endings one pass of the stemmer drops, longest first.
_ENDINGS = ("ings", "ing", "ions", "ion", "ies", "ied", "ees", "ed", "es", "ly", "s", "e", "y")


def stem(word: str) -> str:
    """The word lower cased with one plural or tense ending dropped.

    The ending is dropped only where at least three letters are left, so `days` reads `day`,
    `drafted` reads `draft`, `creation` reads `creat` and `was` is left alone.
    """
    word = word.lower()
    for ending in _ENDINGS:
        if word.endswith(ending) and len(word) - len(ending) >= 3:
            return word[: -len(ending)]
    return word


STOP_WORDS = frozenset(stem(word) for word in STOP_SOURCE.split())


def cut_days(text) -> str:
    """The text with every day it names cut out, so a day is not read as a number or a word."""
    text = straighten(str(text))
    for start, end, _ in reversed(date_matches(text)):
        text = text[:start] + " " + text[end:]
    return text


def words_of(text) -> set[str]:
    """Every word of the text that says something, stemmed, with the days cut out first."""
    return {stem(word) for word in _LETTERS.findall(cut_days(text))} - STOP_WORDS


def numbers_of(text) -> set[str]:
    """Every run of digits the text names, with the days cut out and the thousands marks gone."""
    return set(_DIGITS.findall(cut_days(text).replace(",", "")))


def days_of(text) -> set[str]:
    """Every day the text names, as ISO days."""
    return {day for _, _, day in date_matches(straighten(str(text)))}
