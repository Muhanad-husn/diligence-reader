"""The twice knob: sample 1's room with a sister entity's hundred documents cloned into it.

`python -m rlm.widen twice samples/atlas samples/atlas-twice` writes sample 1's hundred
documents exactly as the control writes them and adds a hundred clones under
`data_room/09_Sister_Entity/`, ids DR-201 to DR-300, so the room holds 200 documents and the
map has twice as much to read for the same truth.

Pass A clones the 81 documents that are neither required nor decoys, in ascending document id
order, with the names of column A of the table, dates two years back, amounts times 1.46 and
identifiers suffixed `-SE`. Pass B clones the 19 of those 81 that write the most section text a
second time, in ascending document id order, with the names of column B, dates five years back,
amounts times 0.64 and identifiers suffixed `-SG`. Pass B carries its own names and its own
suffix, as well as its own shift and its own factor, because 19 clones written the way pass A
writes them would stand in the room as 19 near duplicates of 19 documents already there, and
the map would read that cluster rather than the room's size. The knob measures what twice the
documents cost, not what a duplicate costs.

A clone carries none of the planted truth. Before a file is written every clone is read against
every fact of sample 1's key: a quote, a comparison and a document as a flattened lower cased
substring, an identifier and a number delimited so that a suffix and a factor take them out of
reach, and a date both as its ISO value and as any date surface that normalises to it, so that
a shift cannot land on a planted date. One match raises ValueError naming the fact, the clone
and the surface, and the run writes nothing.

The two shifts pass that check as they were first written. The two factors did not. 1.37 wrote
`$12m` in DR-019, DR-021 and DR-078 from `$9m` and `$6m`, and `$240m` in DR-022 and DR-089 from
`$175m`, and 0.61 wrote `$12m` in DR-018 from `$20m`; every factor from 1.38 to 1.45 and 0.62
to 0.63 was refused as well. The factors used are the next ones that pass, 1.46 and 0.64, and
the check is not weakened to take a factor that does not.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal

from rlm.widen import ROOM, Document, Source, Variant, identity, wrap

NAME = "twice"

# The folder the sister entity's documents are written under, beside sample 1's eight.
FOLDER = "09_Sister_Entity"

# The id the first clone takes; the rest follow it in the order the two passes run.
FIRST_ID = "DR-201"

# What each pass clones: pass A the 81 that are neither required nor decoys, pass B the 19 of
# those that write the most section text.
CLONES = 81
SECOND_CLONES = 19

# Pass A: the 81, ids DR-201 to DR-281.
SHIFT_YEARS = 2
FACTOR = 1.46
SUFFIX = "-SE"

# Pass B: the 19 largest of the 81 a second time, ids DR-282 to DR-300.
SECOND_SHIFT_YEARS = 5
SECOND_FACTOR = 0.64
SECOND_SUFFIX = "-SG"

# One row per name sample 1 uses: the name, the name pass A writes, the name pass B writes.
# Five of the seven are planted identifiers of sample 1's key, and a suffix rule does not reach
# a name, so a clone that still wrote one would carry a planted value.
NAMES: tuple[tuple[str, str, str], ...] = (
    ("VistaPort", "Beaconvale", "Calderwood"),
    ("Northstar", "Eastridge", "Southgate"),
    ("AURORA", "BOREALIS", "ZEPHYR"),
    ("Trust Reset", "Confidence Rebuild", "Loyalty Restart"),
    ("IronLake", "Stonecreek", "Millbrook"),
    ("Juniper & Rowe", "Alder & Finch", "Birch & Kane"),
    ("Kestrel", "Osprey", "Harrier"),
)

# The months a date surface may be written with, and the number each one carries.
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

MONTH_NAMES = "|".join(sorted(MONTHS, key=len, reverse=True))

# The one alternation the rewrite scans a section with, left to right, first match wins. An
# identifier is read before a date because it holds digits a date rule would move, and a date
# before a number because it holds digits a number rule would multiply.
SCAN = re.compile(
    "|".join(
        (
            r"(?P<ident>\b[A-Za-z][A-Za-z0-9]*(?:[-_./][A-Za-z0-9]+)+\b)",
            r"(?P<iso_day>\b\d{4}-\d{2}-\d{2}\b)",
            r"(?P<iso_month>\b(?P<iso_month_year>\d{4})-\d{2}\b)",
            rf"(?P<dmy>\b\d{{1,2}}\s+(?:{MONTH_NAMES})\.?\s+(?P<dmy_year>\d{{4}})\b)",
            rf"(?P<my>\b(?:{MONTH_NAMES})\.?\s+(?P<my_year>\d{{4}})\b)",
            r"(?P<quarter>\bQ[1-4]\s*(?P<quarter_year>\d{4})\b)",
            r"(?P<fy>\bFY\s*(?P<fy_year>\d{4})\b)",
            r"(?<![\w.,$])(?P<year>(?P<year_year>(?:19|20)\d{2}))(?![\w%]|[.,]\d)",
            r"(?<![A-Za-z0-9.,$])(?P<number>(?P<currency>[$£€]\s*)?"
            r"(?P<whole>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<decimals>\d+))?"
            r"(?P<scale>\s*(?:bn|m|k|%)(?![A-Za-z0-9]))?)",
        )
    ),
    re.IGNORECASE,
)

# The alternatives whose only change is the year, and the group each one writes it in.
YEAR_GROUPS = ("iso_month", "dmy", "my", "quarter", "fy", "year")

# The names of the table as one alternation, the longest first so that a long name is read
# before a short one. A name matches on whole words, whatever separator the room writes it
# with, and whatever case, so that `Trust_Reset` in a heading is the same name as `Trust Reset`.
NAME_SEPARATOR = r"[\s_-]+"


def name_body(name: str) -> str:
    """One name of the table as a pattern: its words joined by any separator and its `&` free
    to carry spaces."""
    parts = [
        NAME_SEPARATOR.join(re.escape(word) for word in part.split())
        for part in name.split("&")
    ]
    return r"\s*&\s*".join(parts)


FOUND = re.compile(
    "(?<![A-Za-z0-9])(?:"
    + "|".join(name_body(name) for name, _, _ in sorted(NAMES, key=lambda row: -len(row[0])))
    + ")(?![A-Za-z0-9])",
    re.IGNORECASE,
)

WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Pass:
    """One pass of the knob: the names it writes, how far back it moves a year, what it
    multiplies an amount by and what it puts on the end of an identifier."""

    names: dict[str, str]
    shift: int
    factor: float
    suffix: str


def folded(text: str) -> str:
    """One name as it is looked up: its separators one space, its `&` spaced, lower cased."""
    return re.sub(r"\s*&\s*", " & ", re.sub(NAME_SEPARATOR, " ", text)).strip().lower()


def written_names(column: int) -> dict[str, str]:
    """The name each name of the table is written as in one pass, by the looked up name."""
    return {folded(row[0]): row[column] for row in NAMES}


PASSES = (
    Pass(names=written_names(1), shift=SHIFT_YEARS, factor=FACTOR, suffix=SUFFIX),
    Pass(
        names=written_names(2),
        shift=SECOND_SHIFT_YEARS,
        factor=SECOND_FACTOR,
        suffix=SECOND_SUFFIX,
    ),
)


def flatten(text: str) -> str:
    """Collapses runs of whitespace to one space and strips the ends."""
    return WHITESPACE.sub(" ", text).strip()


# ---------------------------------------------------------------- the rewrite of one section


def separator(found: str) -> str:
    """The separator one name was written with, the one the replacement is written with."""
    runs = re.findall(NAME_SEPARATOR, found)
    if any("_" in run for run in runs):
        return "_"
    if any("-" in run for run in runs):
        return "-"
    return runs[0] if runs else " "


def write_names(text: str, names: dict[str, str]) -> str:
    """One text with every name of the table written as the pass's own name.

    The replacement carries the separator the match wrote, so `Trust_Reset` becomes
    `Confidence_Rebuild`, and is written in capitals where the match was.
    """

    def swap(match: re.Match) -> str:
        found = match.group(0)
        written = names.get(folded(found))
        if written is None:
            return found
        replacement = separator(found).join(written.split())
        if found.upper() == found and any(one.isalpha() for one in found):
            return replacement.upper()
        return replacement

    return FOUND.sub(swap, text)


def shifted(value: str, years: int) -> str:
    """One ISO day moved back by these years, a 29 February with no counterpart becoming the
    28th."""
    year, month, day = (int(part) for part in value.split("-"))
    try:
        moved = datetime.date(year - years, month, day)
    except ValueError:
        moved = datetime.date(year - years, month, day - 1)
    return moved.isoformat()


def moved_year(match: re.Match, group: str, years: int) -> str:
    """One date surface with the year it writes moved back and nothing else changed."""
    text = match.group(0)
    start = match.start(group) - match.start()
    end = match.end(group) - match.start()
    return text[:start] + str(int(match.group(group)) - years) + text[end:]


def multiplied(match: re.Match, factor: float) -> str:
    """One number times the pass's factor, rounded to the places the source writes and written
    with the source's thousands separators, currency symbol, scale suffix and spacing."""
    whole = match.group("whole")
    decimals = match.group("decimals")
    places = len(decimals) if decimals else 0
    value = Decimal(whole.replace(",", "") + ("." + decimals if decimals else ""))
    grown = (value * Decimal(str(factor))).quantize(
        Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP
    )
    written = f"{grown:f}"
    if "," in whole:
        head, point, rest = written.partition(".")
        written = f"{int(head):,}{point}{rest}"
    return (match.group("currency") or "") + written + (match.group("scale") or "")


def rewritten(match: re.Match, one: Pass) -> str:
    """What one match of the scan is written as."""
    if match.group("ident") is not None:
        return match.group(0) + one.suffix
    if match.group("iso_day") is not None:
        return shifted(match.group(0), one.shift)
    for group in YEAR_GROUPS:
        if match.group(group) is not None:
            return moved_year(match, f"{group}_year", one.shift)
    return multiplied(match, one.factor)


def rewrite(text: str, one: Pass) -> str:
    """One section text as a clone of this pass writes it: the names first, then one left to
    right scan of the identifiers, the dates and the numbers."""
    return SCAN.sub(lambda match: rewritten(match, one), write_names(text, one.names))


# ---------------------------------------------------------------- what a clone may not carry


def spaced(value: str) -> str:
    """One value written as a pattern whose whitespace matches any whitespace."""
    return r"\s+".join(re.escape(part) for part in value.split())


def identifier_pattern(value: str) -> re.Pattern[str]:
    """A planted identifier as the check reads it: its whitespace free, its `&` free to carry
    spaces, and the match delimited so a suffix takes it out of reach."""
    body = r"\s*&\s*".join(spaced(part) for part in value.split("&"))
    return re.compile(rf"(?<![A-Za-z0-9&-]){body}(?![A-Za-z0-9-])", re.IGNORECASE)


def number_pattern(value: str) -> re.Pattern[str]:
    """A planted number as the check reads it: its whitespace free and the match delimited."""
    return re.compile(rf"(?<![\w.,$-]){spaced(value)}(?![\w.,-])", re.IGNORECASE)


def date_pattern(value: str) -> re.Pattern[str]:
    """A planted date as the check reads it: the ISO value, delimited."""
    return re.compile(rf"(?<![\w-]){re.escape(value)}(?![\w-])")


ISO_DAY = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?\s+(\d{4})\b")


def date_surfaces(text: str) -> set[str]:
    """Every date this text writes, as the ISO day it normalises to."""
    found = set(ISO_DAY.findall(text))
    for day, month, year in DAY_MONTH_YEAR.findall(text):
        number = MONTHS.get(month.lower())
        if number is not None:
            found.add(f"{year}-{number:02d}-{int(day):02d}")
    return found


def planted(text: str, facts: list[dict]) -> tuple[str, str] | None:
    """The first planted value of the key this text carries, as the fact id and the surface
    found, or None where it carries none."""
    flat = flatten(text).lower()
    surfaces = date_surfaces(text)
    for fact in facts:
        kind, value = fact["kind"], fact["value"]
        if kind in ("quote", "comparison", "document"):
            if flatten(value).lower() in flat:
                return fact["id"], value
        elif kind == "identifier":
            match = identifier_pattern(value).search(text)
            if match:
                return fact["id"], match.group(0)
        elif kind == "number":
            match = number_pattern(value).search(text)
            if match:
                return fact["id"], match.group(0)
        elif kind == "date":
            match = date_pattern(value).search(text)
            if match:
                return fact["id"], match.group(0)
            if value in surfaces:
                return fact["id"], value
    return None


def carries_quote(text: str, facts: list[dict]) -> bool:
    """Says whether one rewritten section still holds a planted quote or comparison."""
    flat = flatten(text).lower()
    return any(
        flatten(fact["value"]).lower() in flat
        for fact in facts
        if fact["kind"] in ("quote", "comparison")
    )


# ---------------------------------------------------------------- what is cloned


def cloned_ids(source: Source) -> list[str]:
    """The document ids of the source that are neither required nor decoys, ascending."""
    aside = set(source.key["required_documents"])
    aside |= {decoy["document"] for decoy in source.key["decoys"]}
    return sorted(set(source.key["documents"]) - aside)


def largest_ids(source: Source, ids: list[str], count: int) -> list[str]:
    """The largest of these documents by section text characters, ties broken by ascending id,
    returned in ascending id order."""
    documents = source.key["documents"]

    def size(one: str) -> int:
        return sum(len(text) for text in source.sections.get(documents[one], ()))

    return sorted(sorted(ids, key=lambda one: (-size(one), one))[:count])


def clone_id(number: int) -> str:
    """The id the clone at this place in the run takes, counting from zero."""
    head, _, first = FIRST_ID.rpartition("-")
    return f"{head}-{int(first) + number:0{len(first)}d}"


def clone_path(clone: str, source_path: str) -> str:
    """The path one clone takes in the variant: the clone id and its source document's file
    name, under the sister entity's folder."""
    return f"{ROOM}/{FOLDER}/{clone}_{source_path.rpartition('/')[2]}.md"


def cloned(source: Source) -> tuple[tuple[Document, ...], int]:
    """The hundred clones in run order, and how many sections were dropped for still carrying a
    planted quote.

    Pass A takes the 81 in ascending document id order and pass B the 19 largest of them, also
    in ascending document id order, so the ids DR-201 to DR-300 follow the run.
    """
    facts = source.key["facts"]
    first = cloned_ids(source)
    run = [(first, PASSES[0]), (largest_ids(source, first, SECOND_CLONES), PASSES[1])]

    documents = []
    dropped = 0
    for ids, one in run:
        for doc_id in ids:
            clone = clone_id(len(documents))
            path = source.key["documents"][doc_id]
            texts = tuple(rewrite(text, one) for text in source.sections.get(path, ()))
            kept = tuple(text for text in texts if not carries_quote(text, facts))
            dropped += len(texts) - len(kept)
            if not kept:
                raise ValueError(f"{clone} is left with no section")
            documents.append(Document(id=clone, path=clone_path(clone, path), texts=kept))
    return tuple(documents), dropped


def refuse(documents: tuple[Document, ...], facts: list[dict]) -> None:
    """Raises ValueError where any clone carries a planted value of the key."""
    for document in documents:
        carried = planted("\n\n".join(document.texts), facts)
        if carried is not None:
            fact_id, surface = carried
            raise ValueError(
                f"fact {fact_id} is carried by {document.id} as {surface!r}"
            )


# ---------------------------------------------------------------- the brief and the README


def brief_paragraph(documents: tuple[Document, ...]) -> str:
    """The paragraph the knob adds to sample 1's brief."""
    return wrap(
        f"This room also holds the data room of a sister entity of the target: "
        f"{len(documents)} documents under `{ROOM}/{FOLDER}/`, with the ids "
        f"{documents[0].id} to {documents[-1].id}. They are the sister entity's own reports, "
        f"schedules and correspondence, with its own names, its own dates, its own amounts "
        f"and its own identifiers. They are not documents of the target and nothing in them "
        f"belongs to the matter above."
    )


def passes_table() -> str:
    """The README's table of what each pass writes."""
    return "\n".join(
        (
            "| | pass A | pass B |",
            "|---|---|---|",
            f"| clones | {CLONES} | {SECOND_CLONES} |",
            f"| ids | {clone_id(0)} to {clone_id(CLONES - 1)} | "
            f"{clone_id(CLONES)} to {clone_id(CLONES + SECOND_CLONES - 1)} |",
            f"| years shifted back | {SHIFT_YEARS} | {SECOND_SHIFT_YEARS} |",
            f"| factor | {FACTOR} | {SECOND_FACTOR} |",
            f"| identifier suffix | `{SUFFIX}` | `{SECOND_SUFFIX}` |",
        )
    )


def names_table() -> str:
    """The README's table of the names each pass writes."""
    lines = ["| sample 1 | pass A | pass B |", "|---|---|---|"]
    for name, first, second in NAMES:
        lines.append(f"| `{name}` | `{first}` | `{second}` |")
    return "\n".join(lines)


def notes(documents: tuple[Document, ...], dropped: int) -> str:
    """The section the knob adds to the variant's README."""
    said = wrap(
        f"The knob clones the {CLONES} documents sample 1's key marks neither required nor a "
        f"decoy into a sister entity's room, `{ROOM}/{FOLDER}/`, and clones the "
        f"{SECOND_CLONES} of them that write the most section text a second time, so the room "
        f"holds {len(documents)} clones with the ids {documents[0].id} to "
        f"{documents[-1].id}. Pass B writes its own names and its own suffix as well as its "
        f"own shift and its own factor, because 19 clones written the way pass A writes them "
        f"would stand in the room as near duplicates of documents already there."
    )
    check = wrap(
        f"A clone carries none of the planted truth. Every clone is read against every fact of "
        f"sample 1's key before a file is written: a quote, a comparison and a document as a "
        f"flattened lower cased substring, an identifier and a number delimited, and a date "
        f"both as its ISO value and as any date surface that normalises to it. One match "
        f"raises ValueError naming the fact, the clone and the surface, and the run writes "
        f"nothing."
    )
    counted = (
        f"After the rewrites {dropped} sections still held a planted quote and were dropped "
        f"from their clone."
    )
    return (
        f"## The sister entity\n\n{said}\n\n{passes_table()}\n\n{names_table()}\n\n"
        f"{counted}\n\n{check}\n"
    )


def build(source: Source) -> Variant:
    """The variant of sample 1 whose room holds a sister entity's hundred documents too."""
    documents, dropped = cloned(source)
    refuse(documents, source.key["facts"])

    variant = identity(source, NAME, brief_paragraph=brief_paragraph(documents))
    return replace(
        variant,
        documents=variant.documents + documents,
        notes=notes(documents, dropped),
    )
