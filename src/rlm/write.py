"""Writes one sample's findings report from its brief and its dossier, in one gateway call.

Code chooses the evidence and the model writes it up. build_digest reads the dossier's first
matter and keeps about a hundred and fifty rows of it: every comparison, one row for each name,
the models blind to the matter, the largest lesser matters, and the dated turning points and
figures of the documents the matter is actually made of. That digest is written to digest.md
and is the user message; the dossier itself is never sent. The instructions and the brief are
the system message. The model sees no answer key: nothing here reads one.

The one rule the instructions give is that every row of the digest is quoted once, whole, with
its own citation, and that nothing outside the digest is asserted as fact. So the report's
evidence is chosen by code, and what the model adds is the ordering, the arithmetic and the
recommendation. The reply is written verbatim to report-raw.txt and the parsed markdown to
report.md.

The report has five second level headings in the brief's order, and every sentence outside the
recommendation line and the Calculation line ends in one or more citations `[<doc> | <anchor>]`
copied off a digest row. The functions sentences, is_cited and citations here are that reading,
and the phase 5 tests use them so that the writer and the tests split a sentence the same way.

The call runs inside one ledger batch, which prints the estimated tokens and the price before
anything is sent and writes one phase 5 row of LEDGER.md when the call returns.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from itertools import zip_longest
from pathlib import Path

from rlm.amounts import normalise_amount
from rlm.gateway import PRICES, Gateway, Ledger, estimate_tokens, price

PHASE = 5

# The bake-off of 2026-09-06 chose this model, and the whole dossier fits its context.
DEFAULT_MODEL = "z-ai/glm-5.3-flash"

# The report is a few thousand words; this cap is what the phase pays for.
MAX_OUTPUT_TOKENS = 16000

# The five deliverables of the brief, as the second level headings the report carries.
HEADINGS = (
    "Executive summary",
    "Findings ranked by materiality",
    "The most material issue quantified",
    "Lesser issues",
    "Open items",
)

# The two lines that carry no citation: the recommendation and the arithmetic.
RECOMMENDATION = "Recommendation:"
CALCULATION = "Calculation:"

_CITATION = re.compile(r"\[\s*([^\[\]|]+?)\s*\|\s*([^\[\]|]+?)\s*\]")
_LIST_MARKER = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")

# The marks that open and close a quotation, straight and curly.
_QUOTE_MARKS = '"“”'
_SENTENCE_PUNCTUATION = ".!?"
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
# ceiling is what the reply can hold, not what the dossier can offer. A digest of 145 rows ran
# the reply out of room inside the fourth section on 2026-09-07, 118 finished with a hundred
# tokens to spare, and 110 leaves about a tenth of the cap while losing no fact the larger
# digests carried.
DIGEST_ROWS = 110

# The most comparison rows a digest carries. Each of them costs three sentences of the reply,
# one for the contradiction and one for each half quoted whole, and the halves are the longest
# quotes the dossier holds, so thirty of them is half a report. The rows that can be quoted
# inside a sentence come first and the dossier's own order decides the rest.
COMPARISON_ROWS = 30

# The most lesser matters a digest carries. The dossier ranks that section by the largest money
# figure of each document, so these are its largest and the rest are what a report would have
# said least about. Every digest row costs a quoted sentence of a capped reply, so the least
# material section is the one that gives room back.
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

    A money figure counts one, a percentage counts one, each distinct term written in capitals
    counts one, and each status word the row holds counts one. A row that carries several of
    them is where the room decided something, blocked something or qualified something, and a
    row that carries none is background.
    """
    quote = row_quote(row)
    found = len(set(_DEFINED_TERM.findall(quote)))
    found += 1 if _MONEY.search(quote) else 0
    found += 1 if _PERCENT.search(quote) else 0
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


def digest_sections(dossier: str) -> dict[str, list[str]]:
    """The rows the digest keeps, by the dossier heading they came from.

    Every comparison row, every lesser matter and every model blind to the matter goes in
    whole, because those are the matter's contradictions, its rest and its blind spots and
    there are few of them. The names give one row each. The timeline gives its dated turning
    points and the figures give the largest money and the counts and defined terms, and those
    two are what a total over DIGEST_ROWS is trimmed out of, the figures before the timeline,
    because a date the report loses is a date the report cannot write.
    """
    sections = dossier_sections(dossier)
    names = named_rows(sections.get("Names", []))
    weight = document_weight(sections)
    lesser = quotable_first(sections.get("Lesser matters", []))[:LESSER_ROWS]
    models = sections.get("Models blind to it", [])
    comparisons = quotable_first(sections.get("Comparisons", []))[:COMPARISON_ROWS]
    room = max(0, DIGEST_ROWS - len(names) - len(lesser) - len(models) - len(comparisons))
    timeline = timeline_rows(
        sections.get("Timeline", []), weight, min(TIMELINE_ROWS, room * 2 // 3)
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


PROMPT = """You are the buy-side diligence lead. You write the findings report of one matter from two
things and nothing else: the brief below, and the digest in the next message.

ANSWER WITH THE REPORT AND NOTHING ELSE

Do not deliberate before you answer. Do not plan, do not take notes, do not list the rows to
yourself and do not say what you are about to do. Read the digest once and write the report as
you read it. The first characters of your reply are `## Executive summary` and the last
section you write is `## Open items`.

THE DIGEST

The digest is the matter, chosen by code out of a much larger dossier. It has six parts.

Timeline, Names, Figures and Models blind to it hold rows of four fields:

  - <date or figure or name> | <doc> | <words> | <anchor>

Comparisons holds the room contradicting itself. A comparison row is two or more
`<doc> | <words> | <anchor>` triples joined by ` || `, and each triple is one half of what the
room said twice. Lesser matters holds what the room carries outside this matter, ranked by its
largest money figure.

THE ONE RULE

Every row of the digest is quoted once in your report, and nothing outside the digest is
asserted as fact. There is no other source. A row is quoted like this:

  The exception log says "Rotation blocked by legacy session compatibility" [DR-000 |
  folder/File_Name.xlsx#Sheet!A12].

The quotation is the row's words field, copied from its first character to its last, and
nothing of it left out. Never write three dots inside a quotation and never quote half a
clause. The citation is `[<doc> | <anchor>]`, both halves copied character for character from
that same row, the whole anchor with its path and its # and everything after it. Put the
citation at the end of the sentence, then the full stop. One row, one sentence, one citation:
never two rows in one sentence and never one row in two.

Copy the anchor character for character, spelling and all. Where an anchor looks misspelled,
copy the misspelling: it is the address of a file and a corrected address points nowhere.

A row's words field may hold a full stop of its own. Keep it and everything after it: that
full stop is the room's and it does not end your sentence.

Every identifier, code name, key name, file name, ticket, firm and object name a row writes
appears in your own prose as the row writes it, character for character, ampersands and
underscores and equals signs included. Write every date the way the digest writes it, four
digits, a hyphen, two digits, a hyphen, two digits, and never as a month in words. Write every
figure with the unit its row gives it. Certainty words are the room's: where a row writes
"probable", write "probable"; where it writes "not yet determinable", write "not yet
determinable".

COMPARISONS

Each comparison row gives three sentences. First the contradiction in one line, in this form,
with no quotation marks and no more than eight words a side:

  <side A> against <side B> [<doc> | <anchor>] [<doc> | <anchor>].

Each side is built from its own triple's words: keep the number, the date, the identifier and
the two or three words that name them, drop every article and every hedge, write a spelled out
number as its digits, and keep a negative negative. A side that was said on a day ends with
that day. A side that is a measurement is the number and its unit followed straight by the
week or day it was measured in. A side that is a limit is written as a limit. A side that is a
period ends with the period in digits. A side that is a right in a contract is the right and
its trigger.

Then quote both halves of that row whole, one sentence each, each with its own citation, by
the rule above.

THE SHAPE

## Executive summary
  A first line beginning `Recommendation:`, then four sentences, each of them quoting a row
  of the digest and ending in its citation like every other sentence of the report.
## Findings ranked by materiality
  ### Chronology
    Every Timeline row, in date order, one sentence each, the date first. All of them, not a
    summary of them.
  ### The room against itself
    The Comparisons rows, three sentences each as set out above.
  ### The names and the figures
    The Names rows and the Figures rows, one sentence each.
  ### The models blind to it
    The Models blind to it rows, one sentence each, saying what each model assumed.
## The most material issue quantified
  Three sentences on the largest exposure the figures carry, each quoting a row and ending in
  its citation, then the `Calculation:` line, then one `Recommendation:` line.
## Lesser issues
  The Lesser matters rows, one sentence each, and why each is smaller than the matter.
## Open items
  Three sentences on what you would still need, each ending in a citation like any other.

A line carries no citation only when it begins `Recommendation:` or `Calculation:`. No summary
sentence and no judgement of your own is exempt: if you cannot cite it, do not write it. Any
line that states what you recommend begins `Recommendation:` and stands alone. Every other sentence
of the report ends in a citation. Write no table, no block quote and no bold label on a line
of its own. Write no em dash of your own. Do not write "e.g.", "i.e." or "approx." inside a
sentence.

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
    is not a sentence end.
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


def citations(report: str) -> list[tuple[str, str]]:
    """Every citation of the report, as document and anchor pairs, in file order."""
    return [(match.group(1), match.group(2)) for match in _CITATION.finditer(report)]


def summary_line(summary: dict) -> str:
    """The one line a write run prints when it ends."""
    return (
        f"write {summary['sample']}: sentences {summary['sentences']}, "
        f"citations {summary['citations']}, tokens_in {summary['tokens_in']}, "
        f"tokens_out {summary['tokens_out']}, seconds {summary['seconds']:.1f}"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Reads the command line of one write run."""
    parser = argparse.ArgumentParser(prog="python -m rlm.write")
    parser.add_argument("sample_dir")
    parser.add_argument("run_dir")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--out",
        default=None,
        help="a second file name under the run directory to keep this draw's report under",
    )
    return parser.parse_args(argv)


def main(argv: list[str], gateway: Gateway | None = None, ledger: Ledger | None = None) -> int:
    """Writes one sample's report.md from its brief and its dossier in one gateway call."""
    args = parse_args(argv)
    if args.model not in PRICES:
        print(f"no such model in the price table: {args.model}")
        return 2

    sample_dir = Path(args.sample_dir)
    run_dir = Path(args.run_dir)
    brief_path = sample_dir / "brief.md"
    dossier_path = run_dir / "dossier.md"
    if not dossier_path.exists():
        print(f"no dossier at {dossier_path}")
        return 2
    if not brief_path.exists():
        print(f"no brief at {brief_path}")
        return 2

    dossier = dossier_path.read_text(encoding="utf-8")
    digest = digest_markdown(dossier)
    rows = build_digest(dossier)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "digest.md").write_text(digest, encoding="utf-8")
    print(f"digest {sample_dir.name}: {len(rows)} rows, {estimate_tokens(digest)} tokens")

    messages = build_messages(brief_path.read_text(encoding="utf-8"), digest)

    if gateway is None:
        gateway = Gateway()
    if ledger is None:
        ledger = Ledger(Path(__file__).resolve().parents[2] / "LEDGER.md")

    estimated_in = estimate_tokens("\n".join(message["content"] for message in messages))
    started = time.monotonic()
    with ledger.batch(
        sample_dir.name, PHASE, args.model, tokens_in=estimated_in, tokens_out=MAX_OUTPUT_TOKENS
    ) as batch:
        completion = batch.record(
            gateway.complete(args.model, messages, max_tokens=MAX_OUTPUT_TOKENS, json=False)
        )
    seconds = time.monotonic() - started

    (run_dir / "report-raw.txt").write_text(completion.text, encoding="utf-8")
    report = parse_reply(completion.text)
    write_report(run_dir, report)
    if args.out:
        (run_dir / args.out).write_text(report, encoding="utf-8")

    summary = {
        "sample": sample_dir.name,
        "model": args.model,
        "digest_rows": len(rows),
        "sentences": len(sentences(report)),
        "citations": len(citations(report)),
        "tokens_in": completion.tokens_in,
        "tokens_out": completion.tokens_out,
        "dollars": price(args.model, completion.tokens_in, completion.tokens_out),
        "seconds": seconds,
    }
    (run_dir / "write-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(summary_line(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
