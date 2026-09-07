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

# The marks that open and close a quotation, straight and curly.
_QUOTE_MARKS = '"“”'
_SENTENCE_PUNCTUATION = ".!?"
_FENCE_OPEN = re.compile(r"^```[a-zA-Z]*\n")
_FENCE_CLOSE = re.compile(r"\n```\s*$")

PROMPT = """You are the buy-side diligence lead. You write the findings report of one matter
from two things and nothing else: the brief below, and the dossier in the next message. You
have read no other document. Invent nothing.

ANSWER WITH THE REPORT AND NOTHING ELSE

You have 8000 tokens for the whole reply, and anything you think is spent out of them, so
spend them on the report. Do not deliberate before you answer. Do not plan, do not take
notes, do not list the rows to yourself, do not restate these instructions and do not say
what you are about to do. Read the dossier once and write the report as you read it. The
first characters of your reply are `## Executive summary`, and the last section you write is
`## Open items`. If you are running out of room, cut sentences, never sections.

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

Markdown, with exactly these five second level headings, in this order, spelled this way, and
with the sentence budget each one is given:

## Executive summary
  One line beginning `Recommendation:` and then four sentences.
## Findings ranked by materiality
  Three third level headings, in this order:
  ### Chronology
    One line for each date at which the matter moved, at most twelve lines, each line the
    date as the timeline writes it, then what happened in a dozen words, then one citation.
  ### The room against itself
    For each of eight comparison rows of the matter, three lines: the short `against`
    sentence in the form set out under COMPARISONS below, then one sentence quoting the first
    half of that row whole with its own citation, then one sentence quoting the second half
    whole with its own citation.
  ### The findings
    Two findings, each opened by a `#### ` line naming it and each of four
    sentences, on what the comparisons above do not already carry.
## The most material issue quantified
  Three sentences, then the `Calculation:` line, then one `Recommendation:` line.
## Lesser issues
  Four sentences.
## Open items
  Three sentences.

Write nothing before the first heading and nothing after the last section. Write no table, no
block quote, and no bold label standing on a line of its own.

CITATIONS

Every sentence ends with one citation and then its full stop, like this:

  The key had not been rotated since then [DR-000 | folder/File_Name.pdf#p1l20].

A citation is [<doc> | <anchor>]. Both halves are copied character for character from one row
of the dossier: the document id of that row, and the anchor of that same row. Copy the whole
anchor, the path and the # and everything after it. Never write an anchor you did not read on
a row, never shorten one, never invent one, and never join a document to another row's anchor.

The citation sits at the end of the sentence and nowhere else. A citation in the middle of a
sentence is wrong, even when the sentence names two documents: put both citations together at
the end, then the full stop.

A line carries no citation only when it begins `Recommendation:` or `Calculation:`. Any line
that states what you recommend begins `Recommendation:` and stands alone on its line. Every
other sentence in the report ends in a citation, the sentence that lists the names included,
and a judgement of your own is no exception: cite the row that made you form it. If you cannot
cite a sentence, do not write it.

WORDS

Report what a document says by quoting it, not by restating it. Every sentence that reports
what a document says carries that row's own words inside double quotation marks, copied
character for character from the row, followed by the citation of that row.

Quote the row's words field whole. A row is `- <first field> | <doc> | <words> | <anchor>`,
and the words field is everything between the document id and the anchor. Copy that field from
its first character to its last, and put the quotation marks around all of it. A quotation
that starts after the subject, or stops before the qualifier at the end, or stops at a
semicolon, is wrong: the subject and the qualifier are usually where the finding is. Do not
restate any part of a row in your own words outside the quotation marks, and do not join two
rows inside one pair of quotation marks.

The words field may hold a full stop of its own. Keep it and keep everything after it: that
full stop belongs to the room, not to you, and it does not end your sentence. Your sentence
ends after the closing quotation mark and the citation.

Never write three dots inside a quotation. Cutting the middle out of a clause is what a seller
does; quote the field whole instead.

Where a document says the same thing on more than one row, quote the row that carries the
reason, the blocker, the decision or the assumption in words, not the row that carries only a
status, a label, a code or a count.

Keep the row's case, its punctuation, its units, its spelling and its hyphens, and where a row
shouts a word in capitals keep the capitals. Keep the row's own word for a thing: where a row
writes "cybersecurity" do not write "security", and where a row writes a number in words and
in digits, keep both.

Every figure, date, name, identifier, code name, key name, file name, ticket and amount is
copied from a row exactly as the row writes it, with its unit. Write every date anywhere in
the report the way the timeline writes it, four digits, a hyphen, two digits, a hyphen, two
digits, in the chronology and in the prose alike, and never as a month in words. Certainty
words are the source's: where the room writes "probable", write "probable"; where it writes
"not yet determinable", write "not yet determinable". Do not write "e.g.", "i.e.", "approx."
or any other abbreviation ending in a full stop inside a sentence. Write no em dash of your
own; an em dash inside a quote you copy stays as its row writes it.

COVERAGE

The report is the whole matter, not a summary of it, and these four rules say what it has to
reach.

One. Quote at least one row of every document that the comparisons section names, and of every
document that the models blind to the matter section names, and cite each of them. For each
blind model, say what it assumed, give every figure it assumed with its unit, and quote a row
of the document whose series broke under it, including the row that names the programme behind
the break and the wave it ran in. Give every count of records, accounts, users or sessions the
forensic work found, each with the unit its row writes, and give the blocker on any key that
was not rotated.

Two. The names section gives the matter its names, one name in the first field of each of its
rows. Every distinct name of that first field is written into the report at least once,
spelled exactly as the section spells it, ampersands, full stops, underscores and equals signs
included. There are a few dozen of them. The findings end with one or two sentences that name
every one of them the report has not used yet, all of them, not one of them. For the names of
the matter's own things, its workstream, its ticket, its programme, its key, its backup object
and its store, quote whole one names row of each, because the row is where the room used the
name.

Three. Every date at which something in the matter was opened, renamed, reclassified, drafted,
finalised, created, rotated, decided, recommended or sent is in the chronology, written as the
timeline writes it. A document that was drafted on one date and finalised on another gives two
lines, not one.

Four. Quote the rows where the room qualifies itself: the exception that was renewed, the
reclassification, the assumption a model rests on, the reserve that was recommended, the
retention limit that was exceeded, the wave a programme ran in, the exclusion in the policy,
the clock that was missed, the notice clause and the termination clause. Those rows are the
findings, and each of them is quoted whole. Where a figure is booked, added back or adjusted
in a schedule, quote the row of the schedule that books it and cite that schedule itself, not
only the memo that repeats it.

Under the lesser issues, name the largest of the matters the dossier holds outside the set and
say why each is smaller.

COMPARISONS

The comparisons are what the room says twice and differently. Under the third level heading
`The room against itself`, write one sentence for each comparison row of the matter, in this
form:

  <side A> against <side B> [<doc> | <anchor>] [<doc> | <anchor>].

Write one for every comparison row the dossier holds for this matter, up to sixteen of them.
Do not leave a contradiction out because it looks small: a covenant, a clock, a retention
limit and a model assumption each get their own sentence.

Each side is a plain statement of at most eight words, built from its own triple, and it is
not in quotation marks. Keep the number, the date, the identifier or the file name, and the
two or three words that name it. Drop every article, every hedging clause set between commas,
and every word that carries no fact. Write a spelled out number as its digits, write a date as
the timeline writes it, and write an amount with the unit its row writes. Keep a negative
source negative, so a row saying a thing was not established becomes "no" and the thing. Keep
the row's own word, not a near one.

A side takes the shortest form that fits what it is. A limit is written as a limit. A window is
the number of days from the event that started it, with that event's own date. A measurement is
the number and its unit followed straight by the week or day it was measured in, with nothing
in between. A model assumption is the number, what it measures, and how it was assumed. A
representation over a period ends with that period in digits. A statement made on a day ends
with that day. A document event is the document, what was done to it, and the date. A right in
a contract is the right and its trigger. A finding not reached is "no" and the finding.

Here is the form on a matter that is not this one, with invented rows and values:

  lease signed 2019-04-01 and renewed against a 12-month limit [DR-000 | folder/One.pdf#p1l4]
  [DR-000 | folder/Two.pdf#p2l9].
  no fault in 36 months against fault not yet established on 2019-06-30 [DR-000 |
  folder/Three.pdf#p1l7] [DR-000 | folder/Four.pdf#p3l2].
  notice drafted 2019-08-02 against 90 days from the claim opened 2019-04-04 [DR-000 |
  folder/Five.pdf#p1l2] [DR-000 | folder/Six.pdf#p2l1].
  40k units assumed flat against 31k in the week of 2019-09-02 [DR-000 | folder/Seven.pdf#p1l9]
  [DR-000 | folder/Eight.pdf#p1l3].
  termination for a Material Breach against a probable removal [DR-000 |
  folder/Nine.pdf#p1l1] [DR-000 | folder/Ten.pdf#p1l6].

Put the side that is the room's own act or measurement first and the standard, the limit or
the window it is measured against second, the way the invented lines above do.

The word "against" joins the two sides and appears once in that sentence.

Under each `against` sentence, quote both halves of that row whole, one sentence each, each
ending in that half's own citation. Copy each half's words field entire, exactly as the row
writes it, by the rule under WORDS. These quotations are the heart of the report: they are the
room contradicting itself in its own words, and a half quoted in part proves nothing. Choose
the eight rows whose halves come from the documents of the matter itself, and cover the
covenant, the clock, the retention limit, the representation, the reserve, the model
assumption and the forensic finding among them.

THE NUMBER

The most material issue carries one dollar number and a range. The number is the middle of the
exposure the room itself estimates, rounded to the nearest whole hundred in the unit the room
writes its amounts in, because a committee acts on a round number. Do not add an estimate of
your own to it and do not add a value no row puts a figure on.

Rounding to the nearest whole hundred means the digits after the hundreds place go, and the
hundreds digit goes up when what is dropped is fifty or more. On invented numbers: 173.4
rounds to 200, 141.0 rounds to 100, 250.0 rounds to 300, 862.5 rounds to 900. Write the
rounded number, not the middle, everywhere you name the number.

The line that carries the arithmetic begins `Calculation:` and names its operands, like this:

  Calculation: (<low> + <high>) / 2 = <middle>, rounded to <number>, range <low> to <high>.

The `Recommendation:` line under it names the deal action and repeats the rounded number.

LENGTH

About sixty sentences in all and never more than sixty-five, short ones, one citation each, and no sentence that says
nothing. The reply has to reach the open items inside 8000 tokens, so do not run long in the
findings. Begin now, with `## Executive summary`, and write no word of anything else.

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
