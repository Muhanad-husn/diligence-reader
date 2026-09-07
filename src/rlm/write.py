"""Writes one sample's findings report from its brief and its dossier, in one gateway call.

The model sees the instructions and the brief as the system message and the whole dossier as
the user message, and answers with markdown. It sees no answer key: nothing here reads one.
The reply is written verbatim to report-raw.txt, and the report itself, with any fence and any
preamble before the first heading dropped, to report.md.

The report the instructions ask for has five second level headings in the brief's order, and
every sentence outside the recommendation line and the Calculation line ends in one or more
citations `[<doc> | <anchor>]` copied off a dossier row. The functions sentences, is_cited and
citations here are that reading, and the phase 5 tests use them so that the writer and the
tests split a sentence the same way.

The call runs inside one ledger batch, which prints the estimated tokens and the price before
anything is sent and writes one phase 5 row of LEDGER.md when the call returns.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from rlm.gateway import PRICES, Gateway, Ledger, estimate_tokens, price

PHASE = 5

# The bake-off of 2026-09-06 chose this model, and the whole dossier fits its context.
DEFAULT_MODEL = "z-ai/glm-5.3-flash"

# The report is a few thousand words; this cap is what the phase pays for.
MAX_OUTPUT_TOKENS = 8000

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
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_FENCE_OPEN = re.compile(r"^```[a-zA-Z]*\n")
_FENCE_CLOSE = re.compile(r"\n```\s*$")

PROMPT = """You are the buy-side diligence lead. You write the findings report of one matter
from two things and nothing else: the brief below, and the dossier in the next message. You
have read no other document. Invent nothing.

THE DOSSIER

The dossier is one matter. It lists the matter's documents, then its timeline, the names the
room gives it, its figures, the models blind to it, the comparisons the room's own words make,
and the lesser matters the room holds outside the set. A row of the timeline, the names, the
figures and the models reads

  - <date or figure> | <doc> | <quote> | <anchor>

A row of the comparisons is two or more `<doc> | <quote> | <anchor>` triples joined by ` || `,
and each triple is one side of what the room says twice. A row of the lesser matters reads
`- <figure> | <doc> | <quote> | <anchor>`.

THE SHAPE OF THE REPORT

Markdown, with exactly these five second level headings, in this order, spelled this way:

## Executive summary
## Findings ranked by materiality
## The most material issue quantified
## Lesser issues
## Open items

Write nothing before the first heading and nothing after the last section. You may open a
third level heading (### ) inside a section. Write no table, no block quote, and no bold label
standing on a line of its own.

CITATIONS

Every sentence ends with one or two citations and then its full stop, like this:

  The key had not been rotated since that date [DR-000 | folder/File_Name.pdf#p1l20].

A citation is [<doc> | <anchor>]. Both halves are copied character for character from one row
of the dossier: the document id of that row, and the anchor of that same row. Copy the whole
anchor, the path and the # and everything after it. Never write an anchor you did not read on
a row, never shorten one, never invent one, and never join a document to another row's anchor.
Put the citations before the full stop, never after it.

Exactly two kinds of line carry no citation. The first line of the executive summary is your
recommendation and begins `Recommendation:`. The one line under the most material issue that
carries the arithmetic begins `Calculation:`. Every other line of prose is sentences, and
every one of them ends in a citation.

WORDS

Every quote, figure, date, name, identifier, code name, key name, file name, firm, ticket and
amount is copied from a dossier row exactly as the row writes it, with its unit, its case and
its punctuation. Paraphrase nothing a row states. Certainty words are the source's: where the
room writes "probable", write "probable"; where it writes "not yet determinable", write "not
yet determinable"; where it writes "does not permit", write "does not permit". Do not write
"e.g.", "i.e.", "approx." or any other abbreviation ending in a full stop inside a sentence,
and never end a sentence inside a quotation.

COVERAGE

The report is the whole matter, not a summary of it. Name every identifier, code name, key
name, file name, firm, ticket and workstream the dossier names for the matter, each written
exactly as the dossier writes it. Give every date of the timeline at which something changed.
Give every figure that bears on the matter, with the unit the row writes and the number the
row writes. Cite every document id that the comparisons section names, and every document
whose row you use, so that no document of the matter's set goes unnamed. Under the lesser
issues, name the largest of the matters the dossier holds outside the set and say why each is
smaller.

COMPARISONS

The comparisons are what the room says twice and differently, and they are the body of the
findings. Write one sentence for each comparison that bears on the matter, in this form:

  <side A> against <side B> [<doc> | <anchor>] [<doc> | <anchor>].

Each side is a plain statement of at most ten words, built from its own triple: keep the
number, the date, the identifier or the file name, and the two or three words that name it;
drop a hedging clause set between commas inside the quote; write a spelled out number as its
digits; keep a negative source negative. The word "against" joins the two sides and appears
once in that sentence. Then, in the sentence or two that follow, quote both halves in full
from their own rows with their own citations, so the reader sees the room's own words as well
as the contradiction.

THE NUMBER

The most material issue carries one dollar number and a range around it. The line that carries
them begins `Calculation:` and names its operands, like this:

  Calculation: <operand> <operator> <operand> = <number>, range <low> to <high>.

Both the number and the two ends of the range are written with the unit the dossier writes its
amounts in. The number is your own estimate, read off the figures of the dossier, and the
recommendation line names the deal action it goes with.

LENGTH

At most 8000 tokens. Short sentences, one citation each, and no sentence that says nothing.

THE BRIEF

"""


def build_messages(brief: str, dossier: str) -> list[dict]:
    """The two messages of the call: the instructions with the brief, then the whole dossier."""
    return [
        {"role": "system", "content": PROMPT + brief},
        {"role": "user", "content": dossier},
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


def sentences(report: str) -> list[str]:
    """Every sentence of the report's body, split on sentence punctuation before whitespace."""
    found = []
    for line in body_lines(report):
        for part in _SENTENCE_END.split(line):
            part = part.strip()
            if part:
                found.append(part)
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

    messages = build_messages(
        brief_path.read_text(encoding="utf-8"), dossier_path.read_text(encoding="utf-8")
    )

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

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "report-raw.txt").write_text(completion.text, encoding="utf-8")
    report = parse_reply(completion.text)
    write_report(run_dir, report)

    summary = {
        "sample": sample_dir.name,
        "model": args.model,
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
