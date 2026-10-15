"""Finds the findings of tree.json that a written report does not carry, and adds them or lists them.

A finding is carried when the report body holds it. The body is the report above `## Left out`,
or above `## Evidence` where there is no left out list, cut into paragraphs at each blank line
and before each list item. The paragraphs that hold the finding's anchor are joined, and the
finding is carried when that text is not empty, holds every figure of three or more digits the
finding states, read as whole numbers with and without their thousands commas, and holds at
least half of the finding's content words, the distinct words of four letters or more outside
STOPWORDS. uncarried lists the findings that are not, at no cost and with no model call.

cover runs after the writer. It sends the uncarried findings, and nothing of the report or the
digest, to one model call that writes one paragraph per finding ending in the finding's own
citation. The report is not rewritten: each paragraph is checked by code, its citations have to
be the finding's anchor and the citation and number checks of rlm.verify have to pass on it,
and the paragraphs that hold go under `### Further findings` at the end of the lesser issues,
numbered on from the last lesser issue. Every finding still uncarried after that is listed by
code under `## Left out`, after the open items and before the schedule, with its citation. A
call that fails or returns nothing usable leaves every uncarried finding on that list.

The call is booked on LEDGER.md on phase 8 as one row whose sample ends in -coverage, and the
rows of that task are held to COVERAGE_CAP_DOLLARS in place of phase 8's cap. The writer's
report is kept as report-pre-coverage.md, and a rerun starts from it, so a run can be covered
again without covering its own additions. coverage.json records what was uncarried, what was
added, what was dropped and why, what was left out, the tokens, the model and the dollars.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import httpx

from rlm.gateway import (
    CapExceeded,
    ClaudeCodeError,
    Completion,
    Gateway,
    Ledger,
    NoReply,
    WrongModel,
    call_dollars,
    estimate_tokens,
    json_object,
    priced,
    register_listing,
)
from rlm.verify import check_citations, check_numbers, read_jsonl
from rlm.write import EVIDENCE_HEADING, HEADINGS, LEFT_OUT_HEADING, citations

PHASE = 8

# The model the coverage call runs on unless told otherwise.
DEFAULT_MODEL = "anthropic/claude-sonnet-5.5"

# What the coverage calls may spend in all, over every room and every try, read off the rows
# of LEDGER.md whose sample ends in -coverage.
COVERAGE_TASK = "coverage"
COVERAGE_CAP_DOLLARS = 3.50

# The reply tokens a call asks for: a base for the JSON and any thinking, and a share for each
# finding's paragraph, up to a ceiling.
BASE_OUTPUT_TOKENS = 2000
TOKENS_PER_FINDING = 250
MAX_OUTPUT_TOKENS = 32000

FURTHER_HEADING = "Further findings"
LESSER_HEADING = HEADINGS[3]
PRE_COVERAGE_FILE = "report-pre-coverage.md"
COVERAGE_FILE = "coverage.json"

STOPWORDS = frozenset(
    "this that with from have will been their they them shall which would under into than then "
    "also only such upon each other were before after more most when where what about there "
    "these those within without against between including".split()
)

_NUMBER = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?")
_WORD = re.compile(r"[a-z][a-z\-]{3,}")
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n|\n(?=[-*] |\d+\. )")
_BODY_END = re.compile(rf"^## (?:{re.escape(LEFT_OUT_HEADING)}|{re.escape(EVIDENCE_HEADING)})\s*$", re.M)
_ITEM_NUMBER = re.compile(r"^\s*(\d+)\.\s")

SYSTEM = """A due diligence report left out the findings listed below. Write one paragraph for each \
finding, to be added to the report's lesser issues as the report stands.

Each paragraph states the finding in plain words: its names, its dates and its figures exactly as \
the finding gives them, and the words of the quote where they help. Write one or two sentences, and \
end every sentence with the finding's citation, written exactly as it is given: [<doc> | <anchor>]. \
Cite nothing else. Use only figures the finding or its quote states, and compute none. Do not use \
may, might, could, likely, probable, confirmed or certain unless the quote uses the word.

Reply with one JSON object and nothing else, one entry per finding in the order given:
{"paragraphs": [{"anchor": "<the finding's anchor>", "paragraph": "<the paragraph>"}]}"""


# ---------------------------------------------------------------- the free check


def all_findings(tree: dict) -> list[dict]:
    """Every finding the tree kept, group by group, in file order."""
    return [finding for group in tree.get("groups", []) for finding in group.get("findings", [])]


def report_body(report: str) -> str:
    """The report above its left out list, or above its schedule where there is no list."""
    match = _BODY_END.search(report)
    return report[: match.start()] if match else report


def body_paragraphs(report: str) -> list[str]:
    """The paragraphs of the report body: blank line separated, and each list item its own."""
    return _PARAGRAPH_BREAK.split(report_body(report))


def plain_number(surface: str) -> str:
    """A figure as compared: its currency mark and any trailing full stop or comma cut off."""
    return surface.lstrip("$").rstrip(".,")


def figures(text: str) -> list[str]:
    """The figures of a finding that the body has to hold: those of three or more digits."""
    found = [plain_number(match) for match in _NUMBER.findall(text)]
    return [figure for figure in found if sum(character.isdigit() for character in figure) >= 3]


def content_words(text: str) -> set[str]:
    """The distinct words of four letters or more of a text, lowercased, outside STOPWORDS."""
    return {word for word in _WORD.findall(text.lower()) if word not in STOPWORDS}


def carries(text: str, finding: dict) -> bool:
    """Says whether a text holds a finding: every figure of it, and half its content words."""
    if not text.strip():
        return False
    held = {plain_number(match) for match in _NUMBER.findall(text)}
    bare = {figure.replace(",", "") for figure in held}
    for figure in figures(finding["finding"]):
        if figure not in held and figure.replace(",", "") not in bare:
            return False
    wanted = content_words(finding["finding"])
    if not wanted:
        return True
    present = set(_WORD.findall(text.lower()))
    return len(wanted & present) / len(wanted) >= 0.5


def uncarried(tree: dict, report: str) -> list[dict]:
    """The findings of the tree that the report body does not carry, in the tree's order."""
    paragraphs = body_paragraphs(report)
    found = []
    for finding in all_findings(tree):
        text = " ".join(paragraph for paragraph in paragraphs if finding["anchor"] in paragraph)
        if not carries(text, finding):
            found.append(finding)
    return found


def check_line(run_dir: Path) -> str:
    """The one line the free check prints for a run: its findings and how many are uncarried."""
    tree = json.loads((run_dir / "tree.json").read_text(encoding="utf-8"))
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    return f"coverage {run_dir}: findings {len(all_findings(tree))}, uncarried {len(uncarried(tree, report))}"


# ---------------------------------------------------------------- the call


def citation_of(finding: dict) -> str:
    """A finding's citation in the report's long form."""
    return f"[{finding['doc']} | {finding['anchor']}]"


def flat(text: str) -> str:
    """A text on one line, its runs of whitespace made single spaces."""
    return " ".join(str(text).split())


def coverage_messages(findings: list[dict]) -> list[dict]:
    """The messages of the coverage call: the instructions, then each finding with its doc,
    anchor, citation and quote. Nothing of the report or the digest is sent."""
    blocks = []
    for number, finding in enumerate(findings, start=1):
        blocks.append(
            f"{number}. citation: {citation_of(finding)}\n"
            f"doc: {finding['doc']}\n"
            f"anchor: {finding['anchor']}\n"
            f"finding: {flat(finding['finding'])}\n"
            f'quote: "{flat(finding.get("quote", ""))}"'
        )
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "FINDINGS\n\n" + "\n\n".join(blocks)},
    ]


def reply_cap(count: int) -> int:
    """The reply tokens a call for this many findings asks for."""
    return min(MAX_OUTPUT_TOKENS, BASE_OUTPUT_TOKENS + TOKENS_PER_FINDING * count)


def parse_paragraphs(text: str) -> list[dict] | None:
    """The anchor and paragraph pairs of a reply, or None where the reply holds no such list.

    The list is read under a "paragraphs" key of an object, or as the reply itself where the
    reply is a bare list.
    """
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        data = json.loads(stripped)
    except ValueError:
        try:
            data = json.loads(json_object(text))
        except ValueError:
            return None
    items = data.get("paragraphs") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return None
    return [
        {"anchor": item["anchor"], "paragraph": flat(item["paragraph"])}
        for item in items
        if isinstance(item, dict) and isinstance(item.get("anchor"), str) and isinstance(item.get("paragraph"), str)
    ]


def paragraph_failure(
    paragraph: str, finding: dict, sections: list[dict], index: list[dict], dossier: str
) -> str | None:
    """Why an added paragraph cannot be kept, or None where it can: its citations have to be
    the finding's own, and the citation and number checks of the verifier have to pass on it."""
    cited = citations(paragraph)
    if not cited:
        return "the paragraph cites nothing"
    for doc, anchor in cited:
        if anchor != finding["anchor"] or doc != finding["doc"]:
            return f"cites [{doc} | {anchor}], not {citation_of(finding)}"
    alone = f"## {LESSER_HEADING}\n\n1. {paragraph}\n"
    failures = check_citations(alone, sections, index) + check_numbers(alone, sections, dossier)
    if failures:
        return "; ".join(f"{item['check']}: {item['reason']}" for item in failures)
    return None


# ---------------------------------------------------------------- placing the paragraphs


def add_further(report: str, paragraphs: list[str]) -> str:
    """The report with the paragraphs under `### Further findings` at the end of the lesser
    issues, numbered on from the last lesser issue. Nothing else of the report changes."""
    if not paragraphs:
        return report
    lines = report.split("\n")
    start = next(i for i, line in enumerate(lines) if line.strip() == f"## {LESSER_HEADING}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    numbers = [int(match.group(1)) for line in lines[start + 1 : end] if (match := _ITEM_NUMBER.match(line))]
    first = max(numbers, default=0) + 1
    last = end
    while last > start + 1 and not lines[last - 1].strip():
        last -= 1
    items = [f"{first + offset}. {paragraph}" for offset, paragraph in enumerate(paragraphs)]
    block = ["", f"### {FURTHER_HEADING}", "", *items, ""]
    return "\n".join(lines[:last] + block + lines[end:])


def add_left_out(report: str, findings: list[dict]) -> str:
    """The report with each finding listed under `## Left out`, before the schedule, by its text
    and its citation."""
    if not findings:
        return report
    items = [f"{number}. {flat(finding['finding'])} {citation_of(finding)}" for number, finding in enumerate(findings, start=1)]
    block = f"## {LEFT_OUT_HEADING}\n\n" + "\n".join(items) + "\n\n"
    match = re.search(rf"^## {re.escape(EVIDENCE_HEADING)}\s*$", report, re.M)
    if match is None:
        return report.rstrip("\n") + "\n\n" + block
    head = report[: match.start()].rstrip("\n")
    return head + "\n\n" + block + report[match.start() :]


# ---------------------------------------------------------------- the step


def listed(finding: dict) -> dict:
    """A finding as coverage.json records it."""
    return {"doc": finding["doc"], "anchor": finding["anchor"], "finding": finding["finding"]}


def cover(
    run_dir: Path,
    gateway: Gateway,
    ledger: Ledger,
    model: str = DEFAULT_MODEL,
    sample: str | None = None,
    out_dir: Path | None = None,
) -> dict:
    """Covers one written report and returns what coverage.json records.

    The room is read from run_dir: tree.json, sections.jsonl and index.jsonl. The report, its
    digest and the files written are in out_dir, run_dir by default: report.md rewritten,
    report-pre-coverage.md and coverage.json.
    """
    run_dir = Path(run_dir)
    out_dir = Path(out_dir) if out_dir is not None else run_dir
    sample = sample or run_dir.name
    before_path = out_dir / PRE_COVERAGE_FILE
    report = (before_path if before_path.exists() else out_dir / "report.md").read_text(encoding="utf-8")
    before_path.write_text(report, encoding="utf-8")
    tree = json.loads((run_dir / "tree.json").read_text(encoding="utf-8"))
    missing = uncarried(tree, report)
    record: dict = {
        "sample": sample,
        "model": model,
        "findings": len(all_findings(tree)),
        "uncarried_before": [listed(finding) for finding in missing],
        "added": [],
        "dropped": [],
        "left_out": [],
        "tokens_in": 0,
        "tokens_out": 0,
        "dollars": 0.0,
        "error": None,
    }

    replies: list[dict] | None = None
    if missing:
        messages = coverage_messages(missing)
        cap = reply_cap(len(missing))
        estimated_in = estimate_tokens("\n".join(message["content"] for message in messages))
        completion: Completion | None = None
        try:
            with ledger.batch(
                f"{sample}-{COVERAGE_TASK}", PHASE, model, estimated_in, cap,
                cap=(COVERAGE_TASK, COVERAGE_CAP_DOLLARS),
            ) as batch:
                try:
                    completion = batch.record(gateway.complete(model, messages, max_tokens=cap, json=True))
                except NoReply as exc:
                    # The draws were paid though they gave nothing, so they are booked.
                    batch.record(Completion("", exc.tokens_in, exc.tokens_out, exc.seconds, model, cost=exc.cost))
                    record.update(tokens_in=exc.tokens_in, tokens_out=exc.tokens_out, error=f"NoReply: {exc}")
        except (CapExceeded, ClaudeCodeError, WrongModel, httpx.HTTPError) as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        if completion is not None:
            record.update(
                tokens_in=completion.tokens_in,
                tokens_out=completion.tokens_out,
                dollars=round(call_dollars(completion), 6),
            )
            (out_dir / "coverage-raw.txt").write_text(completion.text, encoding="utf-8")
            replies = parse_paragraphs(completion.text)
            if replies is None:
                record["error"] = "the reply holds no list of paragraphs"

    kept: list[str] = []
    if replies and not re.search(rf"^## {re.escape(LESSER_HEADING)}\s*$", report, re.M):
        record["dropped"] = [{**item, "reason": "the report has no lesser issues section"} for item in replies]
        replies = None
    if replies:
        sections = read_jsonl(run_dir / "sections.jsonl")
        index = read_jsonl(run_dir / "index.jsonl")
        digest_path = out_dir / "digest.md" if (out_dir / "digest.md").exists() else run_dir / "digest.md"
        dossier = digest_path.read_text(encoding="utf-8") if digest_path.exists() else ""
        open_findings = list(missing)
        for item in replies:
            finding = next((f for f in open_findings if f["anchor"] == item["anchor"]), None)
            if finding is None:
                reason = f"{item['anchor']} is no uncarried finding still open"
            else:
                reason = paragraph_failure(item["paragraph"], finding, sections, index, dossier)
            if reason is None:
                open_findings.remove(finding)
                kept.append(item["paragraph"])
                record["added"].append(item)
            else:
                record["dropped"].append({**item, "reason": reason})

    covered = add_further(report, kept)
    left_out = uncarried(tree, covered)
    covered = add_left_out(covered, left_out)
    record["left_out"] = [listed(finding) for finding in left_out]
    (out_dir / "report.md").write_text(covered, encoding="utf-8")
    (out_dir / COVERAGE_FILE).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(summary_line(record))
    if record["error"]:
        print(f"coverage {sample}: {record['error']}")
    return record


def summary_line(record: dict) -> str:
    """The one line a coverage step prints when it ends."""
    return (
        f"coverage {record['sample']}: findings {record['findings']}, "
        f"uncarried {len(record['uncarried_before'])}, added {len(record['added'])}, "
        f"dropped {len(record['dropped'])}, left out {len(record['left_out'])}, "
        f"tokens_in {record['tokens_in']}, tokens_out {record['tokens_out']}, "
        f"dollars {record['dollars']:.4f}"
    )


# ---------------------------------------------------------------- the command


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Reads the command line of one coverage run."""
    parser = argparse.ArgumentParser(prog="python -m rlm.coverage")
    parser.add_argument("run_dirs", nargs="+", metavar="run_dir")
    parser.add_argument("--check", action="store_true", help="count the uncarried findings, with no model call")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--sample", default=None, help="the sample name the ledger row books under")
    return parser.parse_args(argv)


def main(argv: list[str], gateway: Gateway | None = None, ledger: Ledger | None = None) -> int:
    """Prints the free check of each run, or covers one run's report with one model call."""
    args = parse_args(argv)
    run_dirs = [Path(path) for path in args.run_dirs]
    for run_dir in run_dirs:
        for name in ("tree.json", "report.md"):
            if not (run_dir / name).exists():
                print(f"no {name} at {run_dir / name}")
                return 2
    if args.check:
        for run_dir in run_dirs:
            print(check_line(run_dir))
        return 0
    if len(run_dirs) != 1:
        print("coverage writes one run at a time")
        return 2
    run_dir = run_dirs[0]
    for name in ("sections.jsonl", "index.jsonl"):
        if not (run_dir / name).exists():
            print(f"no {name} at {run_dir / name}")
            return 2
    if gateway is None:
        gateway = Gateway()
    if not priced(args.model):
        # A model outside the price table is priced off the gateway's model list, which is free.
        try:
            register_listing(gateway.models(), gateway.context_lengths)
        except httpx.HTTPError:
            pass
        if not priced(args.model):
            print(f"no such model in the price table: {args.model}")
            return 2
    if ledger is None:
        ledger = Ledger(Path(__file__).resolve().parents[2] / "LEDGER.md")
    cover(run_dir, gateway, ledger, args.model, args.sample)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
