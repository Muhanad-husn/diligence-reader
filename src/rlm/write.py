"""Writes one sample's findings report from its brief and its dossier, in one gateway call.

The report has two halves and only the first is written by a model. build_digest reads the
dossier's first matter and keeps about a hundred and fifty rows of it: every comparison, one
row for each name, the models blind to the matter, the largest lesser matters and every lesser
matter naming a document the matter does not hold, and the dated turning points and largest
figures of the documents the matter is made of. That digest goes to digest.md and
is the user message; the dossier itself is never sent, and the model sees no answer key,
because nothing here reads one. The reply is the five sections the brief asks for, every
sentence of them ending in a citation `[<doc> | <anchor>]` copied off a digest row.

build_evidence then writes the sixth section, `## Evidence`, out of the dossier in code and
with no model in it: every document of the matter with its own timeline, names, figures and
blind models, then every comparison, then the lesser matters, one line each ending in that
row's own citation. That schedule is what the reader checks the five sections against, and it
is why recall is a property of the artefact rather than of a draw. A schedule too long to read
gives up its figures that are not money and then its shortest timeline lines, in that order,
and never a name, a comparison, a lesser matter or a model.

The functions sentences, is_cited and citations here are how a sentence and its citation are
read, and rlm.verify and the phase 5 tests import them so that all three read them the same
way. A citation is read in two forms, `[<doc> | <anchor>]` and `[<anchor>]`, the second being
the first where the anchor begins with the document. The report is then verified by rlm.verify against sections.jsonl, index.jsonl and the
dossier, and where the first reply fails the failures go back to the model once, as a list, in
a second call carrying the first reply. The last reply is kept verbatim in report-raw.txt and
the first in report-raw-1.txt when there were two, the whole report in report.md and the
rounds in verify.json. A second reply that lost any of the five headings was cut short at the
cap, and then the first reply is the report and verify.json's report_round says so.

Both calls run inside one ledger batch, which prints the estimated tokens and the price before
anything is sent and writes one phase 5 row of LEDGER.md, summed over the calls, when they
return.

`--passes 2` runs the same request twice. Pass a writes into the run directory and pass b into
`b/` under it, off the same dossier, sections, index and map, so the two differ only by the
draw. Each pass is its own ledger batch and leaves its own phase 5 row.

`--out-dir` moves both passes somewhere else. The room is still read from the run directory,
so the dossier, the sections, the index and the map are the run's own; only what the passes
write lands under the directory given. That is how rlm.writebakeoff runs one model into
`runs/<sample>/write-bakeoff/<slug>/` without copying the room.

Where the sample has an answer key, rlm.grade.grade reads the report each pass wrote and leaves
grade.json beside it: the recall over the key's facts, the rubric rows with their points and
reasons, the score, and the grader's model and seconds. Nothing here opens the key; the writer
asks the grader whether there is one and the grader does the reading. The grader runs on the
subscription and writes no ledger row. After two passes the absolute difference of the scores
and pass b's score go into pass a's grade.json, and the run prints one line with both scores,
the spread, the dollars of the two passes and the seconds of the passes and the grading.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections.abc import Callable
from itertools import zip_longest
from pathlib import Path

from rlm.amounts import normalise_amount
from rlm.gateway import PRICES, Gateway, Ledger, estimate_tokens, price
from rlm.notes import reask_messages

PHASE = 5

# The phase 5 bake-off of 2026-09-07 chose this model: the only row whose pass a reads recall
# 100 with a passing verifier on all three samples and a rubric over 85 on sample 1.
DEFAULT_MODEL = "z-ai/glm-5.3"

# The report is a few thousand words; this cap is what the phase pays for. It was 8000 until
# 2026-09-07, when the digest grew to give every document of the matter a timeline row and
# the reply needed room to quote them.
MAX_OUTPUT_TOKENS = 12000

# What an empty field is written as, in the dossier and in the schedule.
EMPTY_FIELD = "-"

# The five deliverables of the brief, as the second level headings the report carries. The
# schedule of evidence follows them under a sixth heading, written by code.
HEADINGS = (
    "Executive summary",
    "Findings ranked by materiality",
    "The most material issue quantified",
    "Lesser issues",
    "Open items",
    "Evidence",
)

# The two lines that carry no citation: the recommendation and the arithmetic.
RECOMMENDATION = "Recommendation:"
CALCULATION = "Calculation:"

# What stands in one field of a citation, and what an anchor looks like. An anchor carries
# the # that divides its document path from the place inside that document.
_FIELD = r"[^\[\]|]+?"
_ANCHOR = r"[^\[\]|]*?#[^\[\]|]*?"

# A citation in either of its two forms. The long form writes the document and the anchor with
# a pipe between them. The short form writes the anchor alone, and its document is the path in
# front of the anchor's first #, which is the same row wherever the room's document field is
# that path. An anchor beginning with no document of the index then fails the verifier's
# citation check as any unknown anchor does. A bracket carrying no # is no citation at all.
_CITATION = re.compile(rf"\[\s*({_FIELD})\s*\|\s*({_FIELD})\s*\]|\[\s*({_ANCHOR})\s*\]")

# The same two forms with no capturing group, for a pattern reading a run of citations.
CITATION_TEXT = rf"\[\s*(?:{_FIELD}\s*\|\s*{_FIELD}|{_ANCHOR})\s*\]"

_LIST_MARKER = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")

# The marks that open and close a quotation, straight and curly.
_QUOTE_MARKS = '"“”'
_SENTENCE_PUNCTUATION = ".!?"

# The abbreviations whose full stop ends no sentence. A room writes Invoice No. 4471 and
# TelemetryWorks Inc. in the middle of a line, and the full stop belongs to the abbreviation.
# A single letter followed by a full stop is an initial and is read the same way, which is
# what keeps J. Okonkwo, U.S. and e.g. together.
ABBREVIATIONS = (
    "no.",
    "nos.",
    "inc.",
    "ltd.",
    "co.",
    "corp.",
    "llc.",
    "vs.",
    "v.",
    "e.g.",
    "i.e.",
    "etc.",
    "mr.",
    "ms.",
    "dr.",
    "st.",
)

# The text up to and including a full stop, where that full stop closes an abbreviation or an
# initial. What stands in front of the abbreviation is the start of the line, a space, an
# opening bracket, a quotation mark or a full stop of another initial.
_ABBREVIATION = re.compile(
    r"(?:^|[\s(\[\"“”'.])(?:"
    + "|".join(re.escape(word) for word in ABBREVIATIONS)
    + r"|[a-z]\.)$",
    re.IGNORECASE,
)
_FENCE_OPEN = re.compile(r"^```[a-zA-Z]*\n")
_FENCE_CLOSE = re.compile(r"\n```\s*$")

# The dossier sections a digest is built from, in the order the digest writes them.
DIGEST_SECTIONS = (
    "Timeline",
    "Names",
    "Figures",
    "Models blind to it",
    "Comparisons",
    "Lesser matters",
)

# The sections every row of which goes into the digest whole.
WHOLE_SECTIONS = ("Models blind to it", "Comparisons", "Lesser matters")

# The most rows the timeline and the figures may put into a digest, before the total is
# trimmed. The timeline gives one row per date it can before it gives a second row to any.
TIMELINE_ROWS = 60
MONEY_FIGURE_ROWS = 40
TERM_FIGURE_ROWS = 20

# The most rows a digest carries. Every row has to be quoted once in a report of at most
# MAX_OUTPUT_TOKENS tokens, and a comparison row costs three sentences rather than one, so the
# ceiling is what the reply can hold, not what the dossier can offer. At a cap of 8000 tokens a
# digest of 145 rows ran the reply out of room inside the fourth section on 2026-09-07 and 110
# fitted. At 110 the timeline had 20 rows over 64 documents and the writer never saw the
# insurance conditions or the regulator inquiries, so the rubric stopped at 81 with a spread
# of 1. The cap went to 12000 and the digest to 150 so that every document of the matter has a
# timeline row.
DIGEST_ROWS = 150

# The most comparison rows a digest carries. Each of them costs three sentences of the reply,
# one for the contradiction and one for each half quoted whole, and the halves are the longest
# quotes the dossier holds, so thirty of them is half a report. The rows that can be quoted
# inside a sentence come first and the dossier's own order decides the rest.
COMPARISON_ROWS = 30

# The most lesser matters a digest carries out of the documents the matter already holds. The
# dossier ranks that section by the largest money figure of each document, so these are its
# largest. Every digest row costs a quoted sentence of a capped reply, so the least material
# section is the one that gives room back, and this is the number the timeline and the figures
# are sized against.
LESSER_ROWS = 6

# The most words a row's quote may run to before the digest passes it over. A dossier row can
# be a whole spreadsheet line, a dozen cells joined by pipes, and a report asked to quote one
# of those whole either spends a paragraph on it or quietly shortens it. Where a section has
# rows to choose between, the digest takes one that can be quoted in a sentence.
MAX_QUOTE_WORDS = 40

# The words that mark a timeline row as a turning point rather than a background line.
STATUS_WORDS = (
    "draft",
    "final",
    "redacted",
    "privileged",
    "reclassified",
    "blocked",
    "exceeds",
    "exception",
    "notice",
    "terminate",
    "reserve",
    "probable",
    "determinable",
    "material",
)

# A count that says how big a thing is, as a figures row writes it.
COUNT_UNITS = ("m", "months", "day", "days")

_MONEY = re.compile(r"[$£€]\s?\d")
_PERCENT = re.compile(r"\d\s?%")
_DEFINED_TERM = re.compile(r"\b[A-Z][A-Z0-9_-]{2,}\b")
# A document id written inside a row is a pointer to another document, not a term the row
# defines, so it does not count as a turning mark.
_CROSS_REFERENCE = re.compile(r"\b[A-Z]{2,3}-\d{2,4}\b")
# A period in digits, a deadline or a term of a contract or a policy.
_PERIOD = re.compile(r"\b\d+[- ]?(?:day|days|month|months|year|years)\b", re.IGNORECASE)
_COUNT_WITH_UNIT = re.compile(
    r"\d[\d,.]*\s?-?\s?(?:" + "|".join(COUNT_UNITS) + r")\b", re.IGNORECASE
)


def first_matter(dossier: str) -> str:
    """The text of the dossier's first matter, from its heading to the next matter's."""
    start = dossier.find("## Matter ")
    if start < 0:
        return dossier
    nxt = dossier.find("\n## Matter ", start + 1)
    return dossier[start:] if nxt < 0 else dossier[start:nxt]


def dossier_sections(dossier: str) -> dict[str, list[str]]:
    """The rows of each `### ` section of the dossier's first matter, by heading.

    A row is a line beginning `- `, kept whole, exactly as the dossier wrote it.
    """
    found: dict[str, list[str]] = {}
    heading = None
    for line in first_matter(dossier).splitlines():
        if line.startswith("### "):
            heading = line[4:].strip()
            found.setdefault(heading, [])
        elif heading is not None and line.startswith("- "):
            found[heading].append(line)
    return found


def row_fields(row: str) -> list[str]:
    """The fields of one row, with the leading list marker dropped."""
    return row[2:].split(" | ")


def comparison_documents(row: str) -> list[str]:
    """The document of each triple of one comparison row, in the order the row writes them."""
    return [part.split(" | ")[0].strip() for part in row[2:].split(" || ")]


def row_document(row: str) -> str:
    """The document of a four field row, which is its second field."""
    fields = row_fields(row)
    return fields[1] if len(fields) > 1 else ""


def document_weight(sections: dict[str, list[str]]) -> dict[str, int]:
    """How much of the matter each document carries, read off the dossier and nothing else.

    A document weighs three for every comparison row that sets it against another, three for
    carrying a model blind to the matter, and one for every names row read out of it. Those
    three sections are short and every row of them is about this matter, so between them they
    say which of a hundred room documents the matter is actually made of. The timeline and the
    figures are then read only inside that set, heaviest document first. Without it the
    timeline of a hundred document room offers a hundred and fifty dates, almost none of them
    the matter's, and the dates that moved it are lost among them.
    """
    weight: dict[str, int] = {}
    for row in sections.get("Comparisons", []):
        for doc in comparison_documents(row):
            weight[doc] = weight.get(doc, 0) + 3
    for row in sections.get("Models blind to it", []):
        doc = row_document(row)
        weight[doc] = weight.get(doc, 0) + 3
    for row in sections.get("Names", []):
        doc = row_document(row)
        weight[doc] = weight.get(doc, 0) + 1
    weight.pop("", None)
    return weight


def row_quote(row: str) -> str:
    """The words field of a row, which is everything between its document and its anchor."""
    fields = row_fields(row)
    return " | ".join(fields[2:-1]) if len(fields) >= 4 else row


def is_quotable(row: str) -> bool:
    """Says whether a row's words can be quoted whole inside one sentence.

    A row can run to a whole spreadsheet line, a dozen cells the dossier could not tell apart,
    and a report asked to quote one of those whole either spends a paragraph on it or quietly
    shortens it. Where a section has rows to choose between, the digest takes a short one.
    """
    return len(row_quote(row).split()) <= MAX_QUOTE_WORDS


def quotable_first(rows: list[str]) -> list[str]:
    """The rows that can be quoted in a sentence first, then the rest, order kept inside each."""
    return [row for row in rows if is_quotable(row)] + [
        row for row in rows if not is_quotable(row)
    ]


def turning_signals(row: str) -> int:
    """How many marks of a turning point one row carries.

    A money figure counts one, a percentage counts one, a period in digits counts one, each
    distinct term written in capitals counts one unless it is another document's id, and each
    status word the row holds counts one. A row that carries several of
    them is where the room decided something, blocked something or qualified something, and a
    row that carries none is background.
    """
    quote = row_quote(row)
    found = len(set(_DEFINED_TERM.findall(quote)) - set(_CROSS_REFERENCE.findall(quote)))
    found += 1 if _MONEY.search(quote) else 0
    found += 1 if _PERCENT.search(quote) else 0
    found += 1 if _PERIOD.search(quote) else 0
    lowered = quote.lower()
    return found + sum(1 for word in STATUS_WORDS if word in lowered)


def is_turning_point(row: str) -> bool:
    """Says whether a row carries a figure, a defined term or a status word at all."""
    return turning_signals(row) > 0


def timeline_rows(rows: list[str], weight: dict[str, int], cap: int) -> list[str]:
    """The matter's dated turning points, heaviest document first, one row each in turn.

    Only the rows of a document the matter weighs are read. Each document offers two lists.
    The first is one row for each date it speaks of, that date's strongest row, the dates
    ordered by how much the room said on them: this is what a chronology is written from. The
    second is the document's own strongest rows in order, which is where the reason, the
    blocker, the exception and the assumption are written, and those rarely sit on the date
    the document is loudest about. The two lists are interleaved, and the documents then take
    one row each in turn, heaviest first, so every document of the matter reaches the digest
    before any document takes a second row. The rows come back in date order.
    """
    by_document: dict[str, list[str]] = {}
    for row in rows:
        doc = row_document(row)
        if doc in weight:
            by_document.setdefault(doc, []).append(row)
    ordered: dict[str, list[str]] = {}
    for doc, document_rows in by_document.items():
        dates: dict[str, list[str]] = {}
        for row in document_rows:
            dates.setdefault(row_fields(row)[0], []).append(row)
        by_date = [
            max(
                dates[date],
                key=lambda row: (is_quotable(row), turning_signals(row), -document_rows.index(row)),
            )
            for date in sorted(
                dates,
                key=lambda date: (-sum(turning_signals(row) for row in dates[date]), date),
            )
        ]
        by_strength = sorted(
            document_rows,
            key=lambda row: (not is_quotable(row), -turning_signals(row), document_rows.index(row)),
        )
        picked: list[str] = []
        for first, second in zip_longest(by_date, by_strength):
            for row in (first, second):
                if row is not None and row not in picked:
                    picked.append(row)
        ordered[doc] = picked
    documents = sorted(ordered, key=lambda doc: (-weight[doc], doc))
    found: list[str] = []
    depth = 0
    while len(found) < cap and any(len(ordered[doc]) > depth for doc in documents):
        for doc in documents:
            if len(found) >= cap:
                break
            if len(ordered[doc]) > depth:
                found.append(ordered[doc][depth])
        depth += 1
    return sorted(found, key=lambda row: (row_fields(row)[0], row_document(row)))


def money_of(field: str) -> float | None:
    """The dollar value a figures row's first field names, or None where it names none."""
    if not _MONEY.search(field):
        return None
    try:
        value, _ = normalise_amount(field)
    except ValueError:
        return None
    return value


def figure_rows(
    rows: list[str], weight: dict[str, int], money_cap: int, term_cap: int
) -> list[str]:
    """The matter's own figures, its heaviest documents first and the largest money of each.

    Only the rows of a document the matter weighs are read. A row whose first field is a
    dollar amount is ranked by its document's weight and then by that amount, largest first,
    because the largest figure in a hundred document room belongs to the room's revenue and
    not to the matter, while the largest figure inside the matter's own paper is what the
    matter costs. A row whose first field is not money is kept when its quote holds a defined
    term in capitals or a count with a unit, again heaviest document first.
    """
    money: list[tuple[int, float, int, str]] = []
    other: list[tuple[int, int, str]] = []
    for index, row in enumerate(rows):
        doc = row_document(row)
        if doc not in weight:
            continue
        fields = row_fields(row)
        value = money_of(fields[0])
        if value is not None:
            money.append((-weight[doc], -value, index, row))
            continue
        quote = row_quote(row)
        if _DEFINED_TERM.search(quote) or _COUNT_WITH_UNIT.search(quote):
            other.append((-weight[doc], index, row))
    money.sort()
    other.sort()
    money = [item for item in money if is_quotable(item[-1])] or money
    other = [item for item in other if is_quotable(item[-1])] or other
    return [row for *_, row in money[:money_cap]] + [row for *_, row in other[:term_cap]]


def named_rows(rows: list[str]) -> list[str]:
    """One row for each distinct name of the names section, in the dossier's order.

    The row taken for a name is the first one that can be quoted inside a sentence, and the
    first row of the name when none of them can.
    """
    found = []
    seen = set()
    for row in quotable_first(rows):
        name = row_fields(row)[0]
        if name in seen:
            continue
        seen.add(name)
        found.append(row)
    order = {row: index for index, row in enumerate(rows)}
    return sorted(found, key=lambda row: order[row])


def lesser_rows(rows: list[str], held: set[str]) -> list[str]:
    """The lesser matters the digest keeps: the largest by money, then every row naming a
    document the matter does not hold.

    The dossier ranks this section by the largest money figure of each document, so the first
    LESSER_ROWS of it are the largest. A report that has to say what is smaller has to have
    seen it, and a row whose document sits outside the matter is the only line the writer will
    ever have on that document, so it is kept whatever its figure. On sample 1 the largest six
    are the room's revenue and its audit opinions, and the licence clean-up, the search partner
    and the mail gateway sit at ranks 45 and past it, which is why the rank alone did not reach
    them.
    """
    ordered = quotable_first(rows)
    kept = list(ordered[:LESSER_ROWS])
    kept.extend(row for row in ordered[LESSER_ROWS:] if row_document(row) not in held)
    return kept


def digest_sections(dossier: str) -> dict[str, list[str]]:
    """The rows the digest keeps, by the dossier heading they came from.

    Every comparison row and every model blind to the matter goes in whole, because those are
    the matter's contradictions and its blind spots and there are few of them. The lesser
    matters give their largest by money and every row naming a document the matter does not
    hold. The names give one row each. The timeline gives its dated turning points and the
    figures give the largest money and the counts and defined terms, and those two are what a
    total over DIGEST_ROWS is trimmed out of, the figures before the timeline, because a date
    the report loses is a date the report cannot write.
    """
    sections = dossier_sections(dossier)
    names = named_rows(sections.get("Names", []))
    weight = document_weight(sections)
    lesser = lesser_rows(sections.get("Lesser matters", []), set(weight))
    models = sections.get("Models blind to it", [])
    comparisons = quotable_first(sections.get("Comparisons", []))[:COMPARISON_ROWS]
    # The lesser matters outside the matter are not charged against the timeline and the
    # figures: a date the report loses is a date the report cannot write, and the rows that
    # name what is smaller are one short line each.
    charged = min(LESSER_ROWS, len(lesser))
    room = max(0, DIGEST_ROWS - len(names) - charged - len(models) - len(comparisons))
    # Every document of the matter gets a timeline row before any document takes a second,
    # so the timeline is at least as long as the matter is wide, within the room there is.
    timeline = timeline_rows(
        sections.get("Timeline", []),
        weight,
        min(room, max(len(weight), min(TIMELINE_ROWS, room * 2 // 3))),
    )
    figure_room = max(0, room - len(timeline))
    money_cap = min(MONEY_FIGURE_ROWS, figure_room)
    figures = figure_rows(
        sections.get("Figures", []),
        weight,
        money_cap,
        min(TERM_FIGURE_ROWS, figure_room - money_cap),
    )
    return {
        "Timeline": timeline,
        "Names": names,
        "Figures": figures,
        "Models blind to it": models,
        "Comparisons": comparisons,
        "Lesser matters": lesser,
    }


def build_digest(dossier: str) -> list[str]:
    """Every row the digest keeps, in the order the digest writes them."""
    chosen = digest_sections(dossier)
    found = []
    for name in DIGEST_SECTIONS:
        found.extend(chosen.get(name, []))
    return found


def digest_markdown(dossier: str) -> str:
    """The digest as a markdown file, its rows under the headings the dossier gave them."""
    chosen = digest_sections(dossier)
    lines = ["# Digest", ""]
    for name in DIGEST_SECTIONS:
        if not chosen.get(name):
            continue
        lines.append(f"### {name}")
        lines.append("")
        lines.extend(chosen[name])
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


# The heading the code written schedule of the room's own words sits under.
EVIDENCE_HEADING = "Evidence"

# The sections of a document's own evidence, in the order the schedule writes them.
EVIDENCE_SECTIONS = ("Timeline", "Names", "Figures", "Models blind to it")

# How long the schedule may run before it is cut. A hundred and twenty thousand characters is
# about thirty pages, which is a schedule a reader can hold; past that it stops being a
# schedule and becomes the dossier again.
EVIDENCE_MAX_CHARS = 120_000

# The shortest a timeline quote may be and still say something, once the schedule has to cut.
EVIDENCE_MIN_QUOTE = 25


def document_rows(dossier: str) -> list[tuple[str, str, str]]:
    """The Documents list of the first matter, as document, title and date, in rank order."""
    found = []
    for row in dossier_sections(dossier).get("Documents", []):
        _, _, rest = row[2:].partition(". ")
        fields = rest.split(" | ")
        if not fields[0]:
            continue
        title = fields[1] if len(fields) > 1 else ""
        date = fields[3] if len(fields) > 3 else EMPTY_FIELD
        found.append((fields[0], title, date))
    return found


def evidence_line(row: str) -> str:
    """One row of the dossier written as a line of the schedule, ending in its citation.

    The words go inside quotation marks. They are a quotation, and a quotation is also where a
    full stop of the room's own stops being read as the end of a sentence of ours.
    """
    fields = row_fields(row)
    return f'- {fields[0]} | "{row_quote(row)}" | [{fields[1]} | {fields[-1]}]'


def comparison_line(row: str) -> str:
    """One comparison row written as one line, its halves chained by the word against."""
    halves = []
    for part in row[2:].split(" || "):
        fields = part.split(" | ")
        doc, quote, anchor = fields[0], " | ".join(fields[1:-1]), fields[-1]
        halves.append(f'{doc} says "{quote}" [{doc} | {anchor}]')
    return "- " + " against ".join(halves)


def is_money_figure(row: str) -> bool:
    """Says whether a figures row's own figure field is a money amount."""
    return money_of(row_fields(row)[0]) is not None


def build_evidence(dossier: str, cut: int = 0) -> str:
    """The schedule of what the room says, written from the dossier by code and by nothing else.

    Every document of the matter takes a heading and, under it, its timeline, the names read
    out of it, its figures and any model blind to the matter built on it, one line each ending
    in that row's own citation. The comparisons and the lesser matters follow, whole. Two rows
    of one document that say the same thing in the same place are written once.

    cut says how much of it has been given up to keep the schedule readable: one drops the
    figures that are not money, two drops the timeline lines too short to say anything. Nothing
    drops a name, a comparison, a lesser matter or a model, because those are the matter.
    """
    sections = dossier_sections(dossier)
    by_document: dict[str, dict[str, list[str]]] = {}
    for name in EVIDENCE_SECTIONS:
        for row in sections.get(name, []):
            if name == "Figures" and cut >= 1 and not is_money_figure(row):
                continue
            if name == "Timeline" and cut >= 2 and len(row_quote(row)) < EVIDENCE_MIN_QUOTE:
                continue
            by_document.setdefault(row_document(row), {}).setdefault(name, []).append(row)

    lines: list[str] = []
    for doc, title, date in document_rows(dossier):
        kept = by_document.get(doc)
        if not kept:
            continue
        block: list[str] = []
        seen: set[str] = set()
        for name in EVIDENCE_SECTIONS:
            for row in kept.get(name, []):
                line = evidence_line(row)
                if line in seen:
                    continue
                seen.add(line)
                block.append(line)
        if not block:
            continue
        lines.append(f"### {doc} | {title} | {date}")
        lines.append("")
        lines.extend(block)
        lines.append("")

    comparisons = sections.get("Comparisons", [])
    if comparisons:
        lines.append("### Comparisons")
        lines.append("")
        lines.extend(comparison_line(row) for row in comparisons)
        lines.append("")

    lesser = sections.get("Lesser matters", [])
    if lesser:
        lines.append("### Lesser matters")
        lines.append("")
        lines.extend(evidence_line(row) for row in lesser)
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def evidence_within_reach(dossier: str) -> tuple[str, int]:
    """The schedule and the cut it took to get it under EVIDENCE_MAX_CHARS.

    The cuts are tried in order and the first one that fits wins. The last cut is returned
    whether or not it fits, because a schedule that is still long is better than none.
    """
    for cut in (0, 1, 2):
        evidence = build_evidence(dossier, cut)
        if len(evidence) <= EVIDENCE_MAX_CHARS:
            return evidence, cut
    return evidence, 2


PROMPT = """You are the buy-side diligence lead. You write the findings report of one matter from two
things and nothing else: the brief below, and the digest in the next message.

ANSWER WITH THE REPORT AND NOTHING ELSE

Do not deliberate before you answer. Do not plan, do not take notes and do not say what you
are about to do. Read the digest once and write the report as you read it. The first
characters of your reply are `## Executive summary`.

You have 12000 tokens for the whole reply and anything you think is spent out of them. Write
about a hundred sentences, short ones.

THE DIGEST

The digest is the matter, chosen by code out of a larger dossier. Timeline, Names, Figures and
Models blind to it hold rows of four fields:

  - <date or figure or name> | <doc> | <words> | <anchor>

Comparisons holds the room contradicting itself: a row is two or more
`<doc> | <words> | <anchor>` triples joined by ` || `, each triple one half of what the room
said twice. Lesser matters holds what the room carries outside this matter.

CITATIONS

Every sentence ends with its citation and then the full stop:

  The exception log records "Rotation blocked by legacy session compatibility" [DR-000 |
  folder/File_Name.xlsx#Sheet!A12].

A citation is `[<doc> | <anchor>]`, both halves copied character for character from the row
the sentence came from: the whole anchor, its path and its # and everything after it. Copy the
anchor exactly, spelling and all, and where one looks misspelled copy the misspelling: it is
the address of a file. Put the citation at the end of the sentence, never in the middle. Nothing follows it but the
full stop: no trailing clause, no aside, no comparison of your own. If you want to say what a
quotation means, say it before the quotation.

Every figure in a sentence is cited on the row it was copied from, and a sentence carrying
figures from two rows cites both rows. A figure a row does not carry goes out of the sentence.

Two lines carry no citation, and only two: the line beginning `Recommendation:` and the line
beginning `Calculation:`. No summary sentence and no judgement of your own is exempt. If you
cannot cite a sentence, do not write it.

WORDS

Quote the decisive clause of a row, in double quotation marks, copied character for character:
the clause carrying the finding, the number, the date or the hedge, whole from its first word
to its last. Not the whole row and not half a clause. Never write three dots inside a
quotation. Where the clause holds a full stop of its own, keep it and everything after it
inside the quotation marks.

Every identifier, code name, key name, file name, ticket, firm and object name you write
appears as its row writes it, character for character. Every figure carries the unit its row
gives it. Every date is written the way the rows write it, four digits, a hyphen, two digits, a
hyphen, two digits, and never as a month in words. Certainty words are the room's: where a row
writes "probable", write "probable"; where it writes "not yet determinable", write "not yet
determinable". Do not write "e.g.", "i.e." or "approx." inside a sentence, and write no em
dash of your own.

COMPARISONS

Each comparison row gives one sentence, in this form:

  <side A> against <side B>, "<quote A>" and "<quote B>" [<doc A> | <anchor A>] [<doc B> |
  <anchor B>].

Each side is a plain statement of at most eight words built from its own triple: the number,
the date, the identifier and the two or three words that name them, no articles and no hedges,
a spelled out number in digits, a negative kept negative. A side said on a day ends with that
day. A side that is a measurement is the number and its unit followed straight by the week or
day it was measured in. A side that is a limit is written as a limit. A side that is a period
ends with the period in digits. A side that is a right in a contract is the right and its
trigger. The quotes are the two halves' own words.

THE SHAPE

Five second level headings, in this order, and nothing after the fifth:

## Executive summary
  A first line beginning `Recommendation:`, then four sentences, each cited.
## Findings ranked by materiality
  The matter in order of what it costs: the chronology of the dates that moved it, the
  comparisons one sentence each, the names and the figures that bear on it, and what the
  models blind to it assumed. One sentence a row, each cited.
## The most material issue quantified
  Three cited sentences on the largest exposure, then the `Calculation:` line, then one
  `Recommendation:` line.
## Lesser issues
  The lesser matters, one cited sentence each. Say why it is smaller first and quote it last,
  so that the citation is still the last thing in the sentence before the full stop.
## Open items
  Three cited sentences on what you would still need.

Write no sixth heading. A schedule of the room's own words is added under `## Evidence` after
your reply by the code that calls you; do not write it and do not refer to it.

Write no table, no block quote and no bold label on a line of its own.

THE NUMBER

The most material issue carries one dollar number and a range. The number is the middle of the
exposure the room itself estimates, rounded to the nearest whole hundred in the unit the room
writes its amounts in, because a committee acts on a round number. Do not add an estimate of
your own. Rounding to the nearest whole hundred means what is under the hundreds place goes,
and the hundreds digit goes up when what is dropped is fifty or more: on invented numbers
173.4 rounds to 200, 141.0 to 100, 250.0 to 300 and 862.5 to 900. The arithmetic line reads

  Calculation: (<low> + <high>) / 2 = <middle>, rounded to <number>, range <low> to <high>.

and the `Recommendation:` line under it names the deal action and repeats the rounded number.

Begin now, with `## Executive summary`.

THE BRIEF

"""


REASK_FAILURES = """These sentences of your report did not verify. Each line is the check, the
reason, then the sentence as you wrote it:

{items}

Return the whole report again, from `## Executive summary`, and do not rewrite it: copy your
first reply line for line and change only the sentences listed above, each one either fixed
from its row or left out. Keep the same five headings in the same order, one short sentence
per line as before, every sentence ending in its citation copied character for character off
its row, every quotation the room's own words, and every certainty word the room's own. A
number, a date or a certainty word that its row does not carry goes out of the sentence. You
have 12000 tokens for the whole reply, so do not deliberate and do not lengthen anything."""


def failure_items(failures: list[dict]) -> str:
    """The failures of one round, one line each: the check, the reason, then the sentence."""
    return "\n".join(
        f"- {item['check']}: {item['reason']}: {item['line']}" for item in failures
    )


def build_messages(brief: str, digest: str) -> list[dict]:
    """The two messages of the call: the instructions with the brief, then the digest."""
    return [
        {"role": "system", "content": PROMPT + brief},
        {"role": "user", "content": digest},
    ]


def parse_reply(reply: str) -> str:
    """Reads the model's markdown out of its reply, with one trailing newline.

    A code fence around the whole reply is dropped, and so is anything the model wrote before
    the first second level heading.
    """
    text = reply.strip()
    text = _FENCE_OPEN.sub("", text)
    text = _FENCE_CLOSE.sub("", text)
    start = text.find("## ")
    if start > 0 and text[start - 1] != "\n":
        start = text.find("\n## ") + 1
    if start > 0:
        text = text[start:]
    return text.strip() + "\n"


def is_whole(narrative: str) -> bool:
    """Says whether a reply carries the brief's five headings in order.

    A reply cut short at the token cap loses its last sections, and the writer falls back to
    the reply before it rather than write a report with no lesser issues and no open items.
    """
    found = [line[3:].strip() for line in narrative.splitlines() if line.startswith("## ")]
    return found[: len(HEADINGS) - 1] == list(HEADINGS[:-1])


def write_report(run_dir: Path, report: str) -> Path:
    """Writes report.md under the run directory and returns its path."""
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "report.md"
    path.write_text(report, encoding="utf-8")
    return path


def body_lines(report: str) -> list[str]:
    """The lines of the report that carry sentences, with any list marker dropped.

    A heading, a blank line, the recommendation line and a Calculation line are not body
    lines, because those four carry no citation.
    """
    found = []
    for line in report.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        stripped = _LIST_MARKER.sub("", stripped).strip()
        if not stripped or stripped.startswith(RECOMMENDATION) or stripped.startswith(CALCULATION):
            continue
        found.append(stripped)
    return found


def split_sentences(line: str) -> list[str]:
    """Splits one body line at each sentence end that is not inside a quotation.

    A sentence ends at a full stop, an exclamation mark or a question mark followed by
    whitespace. A row quoted whole often carries a full stop of its own, and that full stop
    ends nothing: it is the row's punctuation, not the writer's, so a break inside a quotation
    is not a sentence end. The full stop of an abbreviation of ABBREVIATIONS, and of an
    initial, ends nothing either, so the words after it stay in the same sentence.
    """
    found = []
    start = 0
    quoted = False
    for index, character in enumerate(line):
        if character in _QUOTE_MARKS:
            quoted = not quoted
            continue
        if quoted or character not in _SENTENCE_PUNCTUATION:
            continue
        if index + 1 < len(line) and line[index + 1].isspace():
            rest = line[index + 1 :].lstrip()
            if rest.startswith("|"):
                # A pipe is the edge of a field, not the start of a sentence: a schedule line
                # reading `- VistaPort Media Inc. | "..." | [DR-000 | ...]` is one sentence.
                continue
            if _ABBREVIATION.search(line[: index + 1]):
                # The full stop closes an abbreviation or an initial, so it ends no sentence.
                continue
            part = line[start : index + 1].strip()
            if part:
                found.append(part)
            start = index + 1
    tail = line[start:].strip()
    if tail:
        found.append(tail)
    return found


def sentences(report: str) -> list[str]:
    """Every sentence of the report's body, in file order."""
    found = []
    for line in body_lines(report):
        found.extend(split_sentences(line))
    return found


def is_cited(sentence: str) -> bool:
    """Says whether a sentence ends in one or more citations.

    The trailing whitespace and the trailing sentence punctuation are trimmed; what is left
    has to end in a citation that parses into a document and an anchor.
    """
    trimmed = sentence.rstrip().rstrip(".!?").rstrip()
    if not trimmed.endswith("]"):
        return False
    match = _CITATION.search(trimmed)
    return bool(match) and _CITATION.match(trimmed, trimmed.rfind("[")) is not None


def citation_pair(match: re.Match) -> tuple[str, str]:
    """The document and the anchor of one citation, whichever form it was written in.

    The long form gives both halves. The short form gives the anchor, and its document is the
    path in front of the anchor's first #.
    """
    if match.group(3) is None:
        return match.group(1), match.group(2)
    anchor = match.group(3)
    return anchor.partition("#")[0], anchor


def citations(report: str) -> list[tuple[str, str]]:
    """Every citation of the report, as document and anchor pairs, in file order."""
    return [citation_pair(match) for match in _CITATION.finditer(report)]


def summary_line(summary: dict) -> str:
    """The one line a write run prints when it ends."""
    return (
        f"write {summary['sample']}: sentences {summary['sentences']}, "
        f"citations {summary['citations']}, evidence {summary['evidence_lines']} lines, "
        f"calls {summary['calls']}, verify_failures {summary['verify_failures']}, "
        f"tokens_in {summary['tokens_in']}, tokens_out {summary['tokens_out']}, "
        f"seconds {summary['seconds']:.1f}"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Reads the command line of one write run."""
    parser = argparse.ArgumentParser(prog="python -m rlm.write")
    parser.add_argument("sample_dir")
    parser.add_argument("run_dir")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--from-reply",
        dest="from_reply",
        default=None,
        help="a saved reply to rebuild the report from, making no call and paying nothing",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="a second file name under the run directory to keep this draw's report under",
    )
    parser.add_argument(
        "--out-dir",
        dest="out_dir",
        default=None,
        help="a directory to write the passes into, when it is not the run directory",
    )
    parser.add_argument(
        "--passes",
        type=int,
        choices=(1, 2),
        default=1,
        help="how many times to write the same request, the second one under b/",
    )
    return parser.parse_args(argv)


def graded_line(sample: str, letter: str, result: dict, passes: bool) -> str:
    """The one line a graded pass prints: its recall, its score, its grader and its verifier."""
    return (
        f"graded {sample} pass {letter}: recall {result['recall']} "
        f"score {result['score']:g} model {result['model']} "
        f"verify {'passes' if passes else 'fails'}"
    )


def spread_line(sample: str, score_a: float, score_b: float, dollars: float, seconds: float) -> str:
    """The one line two passes print: both scores, the spread between them, and what they cost."""
    return (
        f"grade {sample}: score_a {score_a:g} score_b {score_b:g} "
        f"spread {abs(score_a - score_b):g} dollars {dollars:.4f} seconds {seconds:.1f}"
    )


def main(
    argv: list[str],
    gateway: Gateway | None = None,
    ledger: Ledger | None = None,
    grader: Callable[[Path, Path, Path, str], dict] | None = None,
) -> int:
    """Writes one sample's report.md, verifies it, grades it, and prints the spread of two passes."""
    # rlm.verify reads a sentence and a citation the way this module does, so it imports from
    # here, and rlm.grade runs a subagent that nothing else here needs. Both imports sit inside
    # main so that the modules do not import each other while they are still loading.
    from rlm import verify as verifier
    from rlm.grade import grade as default_grader
    from rlm.grade import has_key

    args = parse_args(argv)
    if args.model not in PRICES:
        print(f"no such model in the price table: {args.model}")
        return 2
    if args.from_reply and args.passes != 1:
        print("--from-reply rebuilds one pass and does not go with --passes 2")
        return 2

    sample_dir = Path(args.sample_dir)
    run_dir = Path(args.run_dir)
    brief_path = sample_dir / "brief.md"
    dossier_path = run_dir / "dossier.md"
    sections_path = run_dir / "sections.jsonl"
    index_path = run_dir / "index.jsonl"
    if not dossier_path.exists():
        print(f"no dossier at {dossier_path}")
        return 2
    if not brief_path.exists():
        print(f"no brief at {brief_path}")
        return 2
    if not sections_path.exists():
        print(f"no sections.jsonl at {sections_path}")
        return 2
    if not index_path.exists():
        print(f"no index.jsonl at {index_path}")
        return 2

    dossier = dossier_path.read_text(encoding="utf-8")
    digest = digest_markdown(dossier)
    rows = build_digest(dossier)

    messages = build_messages(brief_path.read_text(encoding="utf-8"), digest)

    evidence, cut = evidence_within_reach(dossier)
    sections = verifier.read_jsonl(sections_path)
    index = verifier.read_jsonl(index_path)
    mapping = verifier.read_mapping(run_dir / "map.json")

    def build(text: str) -> str:
        """The whole report of one reply: the narrative it holds and the schedule under it."""
        return f"{parse_reply(text)}\n## {EVIDENCE_HEADING}\n\n{evidence}"

    def check(text: str) -> list[dict]:
        """The failures of one report, read against the room the dossier was built from."""
        return verifier.verify(text, sections, index, dossier, mapping)["failures"]

    def write_pass(out_dir: Path) -> tuple[dict, dict]:
        """One write of the request into out_dir, returning its summary and its verify record.

        The room is read from the run directory whichever pass this is, and every file the
        pass writes lands in out_dir: digest.md, the raw replies, report.md, verify.json and
        write-summary.json. The calls of one pass are one ledger batch, so two passes leave
        two rows of LEDGER.md.
        """
        nonlocal gateway, ledger
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "digest.md").write_text(digest, encoding="utf-8")
        print(f"digest {sample_dir.name}: {len(rows)} rows, {estimate_tokens(digest)} tokens")

        rounds: list[list[dict]] = []
        replies: list[str] = []

        if args.from_reply:
            # A saved reply rebuilds the report with no call and no ledger row, which is how
            # the schedule is changed and measured without paying again for a narrative that
            # has not changed. The tokens and the seconds of the draw that wrote the reply
            # carry forward from the summary it left, because they are still what it cost.
            replies.append(Path(args.from_reply).read_text(encoding="utf-8"))
            previous = out_dir / "write-summary.json"
            before = json.loads(previous.read_text(encoding="utf-8")) if previous.exists() else {}
            tokens_in = int(before.get("tokens_in", 0))
            tokens_out = int(before.get("tokens_out", 0))
            seconds = float(before.get("seconds", 0.0))
            rounds.append(check(build(replies[0])))
            print(f"reply {sample_dir.name}: rebuilt from {args.from_reply}, no call made")
        else:
            if gateway is None:
                gateway = Gateway()
            if ledger is None:
                ledger = Ledger(Path(__file__).resolve().parents[2] / "LEDGER.md")

            estimated_in = estimate_tokens("\n".join(message["content"] for message in messages))
            started = time.monotonic()
            completions = []
            with ledger.batch(
                sample_dir.name,
                PHASE,
                args.model,
                tokens_in=estimated_in,
                tokens_out=MAX_OUTPUT_TOKENS,
            ) as batch:
                completions.append(
                    batch.record(
                        gateway.complete(
                            args.model, messages, max_tokens=MAX_OUTPUT_TOKENS, json=False
                        )
                    )
                )
                replies.append(completions[0].text)
                rounds.append(check(build(replies[0])))
                if rounds[0]:
                    # One second call, and only one: the first reply and the failures under it,
                    # so that the model fixes the sentences the room does not carry and leaves
                    # the rest of its report alone. Both calls pay on this batch's one row.
                    asking = REASK_FAILURES.format(items=failure_items(rounds[0]))
                    completions.append(
                        batch.record(
                            gateway.complete(
                                args.model,
                                reask_messages(messages, replies[0], asking),
                                max_tokens=MAX_OUTPUT_TOKENS,
                                json=False,
                            )
                        )
                    )
                    replies.append(completions[1].text)
            seconds = time.monotonic() - started
            tokens_in = sum(completion.tokens_in for completion in completions)
            tokens_out = sum(completion.tokens_out for completion in completions)
            (out_dir / "report-raw.txt").write_text(replies[-1], encoding="utf-8")
            if len(replies) > 1:
                (out_dir / "report-raw-1.txt").write_text(replies[0], encoding="utf-8")

        kept = len(replies)
        if len(replies) > 1:
            rounds.append(check(build(replies[1])))
            if not is_whole(parse_reply(replies[1])):
                # The second reply lost headings, which is what a reply cut short at the cap
                # looks like. The first reply is the report then, and verify.json says so.
                kept = 1
                print(
                    f"verify {sample_dir.name}: second reply cut short, "
                    "report.md is the first reply"
                )
        report = build(replies[kept - 1])
        write_report(out_dir, report)
        evidence_lines = [line for line in evidence.splitlines() if line.startswith("- ")]
        if args.out:
            (out_dir / args.out).write_text(report, encoding="utf-8")

        calls = 0 if args.from_reply else len(replies)
        record = {
            "sample": sample_dir.name,
            "model": args.model,
            "rounds": rounds,
            "report_round": kept,
            "passes": not rounds[kept - 1],
            "calls": calls,
        }
        (out_dir / "verify.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
        for number, failures in enumerate(rounds, start=1):
            print(verifier.counts_line(sample_dir.name, verifier.counts_of(failures), number))
            for item in failures:
                print(verifier.failure_line(item))

        summary = {
            "sample": sample_dir.name,
            "model": args.model,
            "digest_rows": len(rows),
            "evidence_lines": len(evidence_lines),
            "evidence_chars": len(evidence),
            "evidence_cut": cut,
            "sentences": len(sentences(report)),
            "citations": len(citations(report)),
            "calls": calls,
            "verify_failures": len(rounds[kept - 1]),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "dollars": price(args.model, tokens_in, tokens_out),
            "seconds": seconds,
        }
        (out_dir / "write-summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        print(summary_line(summary))
        return summary, record

    if grader is None:
        grader = default_grader
    # Nothing is graded without an answer key, and the key is read by the grader alone.
    graded = has_key(sample_dir)

    out_root = Path(args.out_dir) if args.out_dir else run_dir
    directories = [(out_root, "a")]
    if args.passes == 2:
        directories.append((out_root / "b", "b"))

    summaries: list[dict] = []
    grades: list[dict] = []
    for out_dir, letter in directories:
        summary, record = write_pass(out_dir)
        summaries.append(summary)
        if graded:
            result = grader(sample_dir, out_dir / "report.md", out_dir, "grade.json")
            grades.append(result)
            print(graded_line(sample_dir.name, letter, result, record["passes"]))

    if len(grades) == 2:
        # The spread of the two draws lives with pass a's grade, which is the graded artefact
        # of the run; pass b's grade file holds its own score and nothing about pass a.
        path = out_root / "grade.json"
        written = json.loads(path.read_text(encoding="utf-8"))
        written["score_b"] = grades[1]["score"]
        written["spread"] = abs(grades[0]["score"] - grades[1]["score"])
        path.write_text(json.dumps(written, indent=2) + "\n", encoding="utf-8")
        dollars = sum(summary["dollars"] for summary in summaries)
        seconds = sum(summary["seconds"] for summary in summaries)
        seconds += sum(result["seconds"] for result in grades)
        print(
            spread_line(sample_dir.name, grades[0]["score"], grades[1]["score"], dollars, seconds)
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
