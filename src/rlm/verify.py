"""Reads a written report back against the room it was written from, and says where it fails.

Five checks run on the five sections the model wrote. The schedule under `## Evidence` is
built by code out of the dossier and is not read here.

check_citations asks that every citation parses with rlm.sections.parse_anchor, that the
anchor's path is a document of index.jsonl, that the anchor is one a record of sections.jsonl
carries, and that the DR id is the id map.json gives that path. A citation written in the
short form, `[<anchor>]`, is read by rlm.write.citations as the document in front of the
anchor's first # and that anchor, so a room whose document field is its own path is named by
the anchor alone and an anchor beginning with no document of the index fails here exactly as
an unknown anchor does. A workbook row is one section
anchored at its leftmost cell and the room's own rows cite the cell that holds the words, so
every cell of a record answers with that record. The DR id to path mapping comes from
map.json's documents list, because the dossier's Documents section carries titles and not
paths. Where map.json is absent the paths of index.jsonl still answer and the id check is
skipped.

check_numbers asks that every number of a cited sentence is a number of one of its cited
sections, and every day of it a day of one of them. Both sides are read with the days cut out
first and rlm.grade.normalise applied, so 240 million and $240m are one number and 912,800,000
is not 912.8m. A figure is read whole on both sides: 30.1% is 30.1 and $185,000.00 is
185000.00, the surfaces normalise leaves. On the sentence's side only a figure standing as its
own token counts, which is what keeps a DR id, a ticket like NQ-17, a key name like
kid=vpauth-legacy-2019 and an object like legacy_uap_backup_2021.tar.gz out of the numbers;
the citations are cut out before the sentence is read. On the section's side the whole figure
counts and so does every digit run inside it, because the room may write its figure inside a
compound the report unpacks. The `Calculation:` line carries no citation
and is read on its own: its operands, the numbers inside the brackets and the range, have to
be numbers of the cited sentences of the same section or of those sentences' sections. Its
divisor, its result and its rounded number are the arithmetic of the line and are not looked
for in the room.

check_certainty puts the words of CERTAINTY on three rungs and asks that no cited sentence
sits above the highest rung of its cited sections. A sentence with no ladder word is rung 0
and always passes. Words inside the sentence's quotation marks count, because they are the
room's own and the room's own section holds them.

check_order reads the findings section. The document set is the Documents list of the
dossier's first matter and the lesser documents are its Lesser matters rows outside that set.
The first finding has to cite a document of the set, and no finding citing only lesser
documents may come before the first that cites the set.

check_sections asks that the report carries a section the model wrote at all. A reply that came
back empty leaves report.md opening straight at `## Evidence`, and the four checks above pass
it: there is no sentence to fail and the schedule's own citations all resolve. A schedule with
no report on it is a failure of the whole report and not of a line, so the check names the line
the report opens on and says which five headings are missing.

verify runs the five and returns the failures, the counts and whether the report passes.
main prints that readout and exits 1 when it does not pass. Nothing here reads an answer key,
opens a socket or makes a model call.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from rlm.carry import cut_days, days_of
from rlm.grade import normalise
from rlm.notes import straighten
from rlm.sections import parse_anchor
from rlm.write import (
    CALCULATION,
    CITATION_TEXT,
    EVIDENCE_HEADING,
    HEADINGS,
    _CITATION,
    body_lines,
    citations,
    dossier_sections,
    document_rows,
    is_cited,
    row_document,
    split_sentences,
)

# The heading of the section whose order is checked.
FINDINGS_HEADING = "Findings ranked by materiality"

# The five checks, in the order the readout prints them. The four that were here first keep
# the places they have always printed in, and the sections check follows them.
CHECKS = ("citations", "numbers", "certainty", "order", "sections")

# The five sections the model writes, which is HEADINGS without the schedule the code adds.
WRITTEN_HEADINGS = HEADINGS[:-1]

# The certainty ladder, rising. A sentence carries the rung of the highest word it holds, and a
# sentence holding none of them is rung 0.
CERTAINTY = (
    ("possible", ("may", "might", "could", "possible", "potential")),
    ("probable", ("likely", "probable", "indicative", "expected", "approximately", "estimated")),
    ("certain", ("confirmed", "certain", "conclusive", "definitive", "established")),
)

_LADDER = tuple(
    re.compile(r"\b(" + "|".join(words) + r")\b", re.IGNORECASE) for _, words in CERTAINTY
)

# What may stand on either side of a number and still leave it a number of its own. A hyphen
# and an underscore are not on the list, which is what keeps DR-069, NQ-17, VR-2025-0142,
# kid=vpauth-legacy-2019 and legacy_uap_backup_2021.tar.gz out of the numbers of a sentence.
_BOUNDARY = "\\s,.;:()\"'"

# A number of a sentence: a run of digits standing as its own token, with a currency mark
# allowed in front of it and a unit allowed behind it.
_STANDALONE_NUMBER = re.compile(
    rf"(?<![^{_BOUNDARY}])[$£€]?(\d[\d.]*)(?:%|m|k|bn|million)?(?![^{_BOUNDARY}])"
)

_DIGIT_RUN = re.compile(r"\d+")

# One number read whole: a run of digits with any decimal part still on it. 30.1 is one number
# and 185000.00 is one number, which is the surface rlm.grade.normalise leaves once the
# currency mark and the thousands marks are gone. A full stop with no digit after it is the
# end of a sentence and is not part of the number.
_WHOLE_NUMBER = re.compile(r"\d+(?:\.\d+)*")

# The citation group at the end of a sentence or a line, with the full stop after it. A
# citation of the group is written in either of the two forms rlm.write reads.
_TRAILING = re.compile(r"((?:\s*" + CITATION_TEXT + r")+)\s*[.!?\"']*\s*$")


# ---------------------------------------------------------------- reading the room off disk


def read_jsonl(path: Path) -> list[dict]:
    """Every record of one JSON lines file, in file order."""
    found = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            found.append(json.loads(line))
    return found


def read_mapping(path: Path) -> dict[str, str] | None:
    """The DR id of each document path, off map.json, or None where there is no map."""
    path = Path(path)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        document["doc"]: document["path"]
        for document in data.get("documents", [])
        if document.get("doc") and document.get("path")
    }


def section_index(records: list[dict]) -> dict[str, str]:
    """The text answering each anchor, and each cell anchor of a record answering with it."""
    found: dict[str, list[str]] = {}
    for record in records:
        anchor = record.get("anchor")
        if not anchor:
            continue
        text = record.get("text") or ""
        found.setdefault(anchor, []).append(text)
        stem, mark, _ = anchor.rpartition("!")
        if not mark:
            continue
        for cell in record.get("cells") or []:
            ref = cell.get("ref")
            key = f"{stem}!{ref}"
            if ref and key != anchor:
                found.setdefault(key, []).append(text)
    return {anchor: " ".join(texts) for anchor, texts in found.items()}


def index_documents(records: list[dict]) -> set[str]:
    """Every document path the index records name."""
    found: set[str] = set()
    for record in records:
        found.update(record.get("docs") or [])
    return found


# ---------------------------------------------------------------- reading the report


def narrative_blocks(report: str) -> list[tuple[str, str]]:
    """Each section the model wrote, as its heading and its lines, in file order.

    The schedule of evidence is written by code out of the dossier, so it is left out.
    """
    blocks: list[tuple[str, str]] = []
    heading: str | None = None
    lines: list[str] = []
    for line in report.splitlines():
        if line.startswith("## "):
            if heading is not None:
                blocks.append((heading, "\n".join(lines)))
            heading = line[3:].strip()
            lines = []
            continue
        if heading is not None:
            lines.append(line)
    if heading is not None:
        blocks.append((heading, "\n".join(lines)))
    return [(name, text) for name, text in blocks if name != EVIDENCE_HEADING]


def strip_citations(text: str) -> str:
    """The text with its citations cut out, so an anchor is read as neither number nor word."""
    return _CITATION.sub(" ", text)


def trailing_citations(text: str) -> list[tuple[str, str]]:
    """The citations of the group at the end of a sentence or a line, or none where there is none."""
    match = _TRAILING.search(text.rstrip())
    return citations(match.group(1)) if match else []


def cited_sentences(text: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Every sentence of these lines with the citations that cover it.

    A sentence's own citations are every citation written inside it, wherever it sits: the
    prompt asks for one group at the end, but a writer that cites in the middle of a sentence
    has still named the section that sentence came from, and the number check reads it. Where
    a sentence holds none, the group at the end of the line it sits on covers it, because a
    line of several sentences cites once.
    """
    found = []
    for line in body_lines(text):
        at_end = trailing_citations(line)
        for sentence in split_sentences(line):
            found.append((sentence, citations(sentence) or at_end))
    return found


def calculation_lines(text: str) -> list[str]:
    """The `Calculation:` lines of one section, which body_lines leaves out."""
    return [line.strip() for line in text.splitlines() if line.strip().startswith(CALCULATION)]


def findings(report: str) -> list[tuple[str, set[str]]]:
    """Each finding of the findings section with the documents it cites, in rank order."""
    found = []
    for heading, text in narrative_blocks(report):
        if heading != FINDINGS_HEADING:
            continue
        for line in body_lines(text):
            found.append((line, {doc for doc, _ in citations(line)}))
    return found


def failure(check: str, line: str, reason: str) -> dict:
    """One failure: which check said so, the line it read, and why."""
    return {"check": check, "line": line.strip(), "reason": reason}


# ---------------------------------------------------------------- numbers, days and certainty


def sentence_numbers(text: str) -> set[str]:
    """Every number a sentence claims, read whole, with days, citations and ids left out.

    A decimal figure is one number and a money figure with cents is one number: 30.1% is 30.1
    and $185,000.00 is 185000.00, the surfaces normalise leaves.
    """
    folded = normalise(cut_days(strip_citations(text)))
    found: set[str] = set()
    for match in _STANDALONE_NUMBER.finditer(folded):
        found.update(_WHOLE_NUMBER.findall(match.group(1)))
    return found


def source_numbers(text: str) -> set[str]:
    """Every number the room's own words hold, whole and in its parts, read from anywhere.

    A figure the room writes whole answers a sentence that writes it whole, and each digit run
    inside it answers a sentence that writes that run on its own.
    """
    folded = normalise(cut_days(text))
    return set(_WHOLE_NUMBER.findall(folded)) | set(_DIGIT_RUN.findall(folded))


def calculation_operands(line: str) -> set[str]:
    """The numbers of a `Calculation:` line that have to be in the room.

    Those are the numbers inside the brackets and the numbers of the range. The divisor of the
    average, the result and the rounded number are the arithmetic of the line: the prompt asks
    for them and the room never wrote them.
    """
    head, _, tail = line.partition("=")
    bracketed = re.findall(r"\(([^)]*)\)", head)
    found: set[str] = set()
    for part in bracketed:
        found |= sentence_numbers(part)
    if not bracketed:
        found |= sentence_numbers(head)
    _, ranged, rest = tail.partition("range")
    if ranged:
        found |= sentence_numbers(rest)
    return found


def rung(text: str) -> int:
    """The highest certainty rung a piece of text sits on, 0 when it carries no ladder word."""
    straightened = straighten(text)
    highest = 0
    for level, pattern in enumerate(_LADDER, start=1):
        if pattern.search(straightened):
            highest = level
    return highest


def highest_word(text: str) -> str:
    """The ladder word of the highest rung the text carries, or an empty string for none."""
    straightened = straighten(text)
    found = ""
    for pattern in _LADDER:
        match = pattern.search(straightened)
        if match:
            found = match.group(1)
    return found


def rung_name(level: int) -> str:
    """What a rung is called, and what rung 0 is called."""
    return CERTAINTY[level - 1][0] if level else "no certainty word"


# ---------------------------------------------------------------- the five checks


def check_citations(
    report: str, sections: list[dict], index: list[dict], mapping: dict[str, str] | None = None
) -> list[dict]:
    """Every sentence of the five written sections ends in a citation, and every citation
    resolves to a section of a known document."""
    texts = section_index(sections)
    documents = index_documents(index)
    found = []
    for _, text in narrative_blocks(report):
        for line in body_lines(text):
            for sentence in split_sentences(line):
                if not is_cited(sentence):
                    # A sentence with no citation of its own has nothing to resolve, and the
                    # prompt exempts no sentence but the recommendation and the arithmetic.
                    found.append(failure("citations", sentence, "the sentence ends in no citation"))
            for doc, anchor in citations(line):
                try:
                    parsed = parse_anchor(anchor)
                except ValueError as error:
                    found.append(failure("citations", line, str(error)))
                    continue
                if parsed.doc not in documents:
                    found.append(
                        failure("citations", line, f"{parsed.doc} is on no record of the index")
                    )
                if anchor not in texts:
                    found.append(failure("citations", line, f"{anchor} is no section of the room"))
                if mapping is None:
                    continue
                if doc not in mapping:
                    found.append(failure("citations", line, f"{doc} is on no document of the map"))
                elif mapping[doc] != parsed.doc:
                    found.append(
                        failure("citations", line, f"{doc} is {mapping[doc]}, not {parsed.doc}")
                    )
    return found


def dossier_rows_by_anchor(dossier: str) -> dict[str, str]:
    """The rows of the dossier's first matter that carry each anchor, joined as one text.

    A timeline row carries a date in its first field and a figures row a figure, and the code
    that wrote the row read that field out of the document and anchored the row at the words
    beside it, which is not always the line the date sits on: a mail's date is in its header
    and its subject line is what the row cites. The writer copies the field off the row it was
    handed, so the row is part of what the sentence's citation names.
    """
    found: dict[str, list[str]] = {}
    for rows in dossier_sections(dossier).values():
        for row in rows:
            for part in row[2:].split(" || "):
                for field in part.split(" | "):
                    if "#" in field:
                        found.setdefault(field.strip(), []).append(part)
    return {anchor: " ".join(parts) for anchor, parts in found.items()}


def check_numbers(report: str, sections: list[dict], dossier: str = "") -> list[dict]:
    """Every number and every day of a cited sentence is in one of its cited sections, or on
    the dossier row that cites that section."""
    texts = section_index(sections)
    rows = dossier_rows_by_anchor(dossier) if dossier else {}
    found = []
    for _, text in narrative_blocks(report):
        cited = [(sentence, cites) for sentence, cites in cited_sentences(text) if cites]
        room: set[str] = set()
        for sentence, cites in cited:
            source = " ".join(
                texts.get(anchor, "") + " " + rows.get(anchor, "") for _, anchor in cites
            )
            numbers = source_numbers(source)
            days = days_of(source)
            room |= numbers | sentence_numbers(sentence)
            for number in sorted(sentence_numbers(sentence)):
                if number not in numbers:
                    found.append(failure("numbers", sentence, f"{number} is in no cited section"))
            for day in sorted(days_of(strip_citations(sentence))):
                if day not in days:
                    found.append(failure("numbers", sentence, f"{day} is in no cited section"))
        for line in calculation_lines(text):
            for number in sorted(calculation_operands(line)):
                if number not in room:
                    found.append(
                        failure("numbers", line, f"{number} is on no cited sentence of the section")
                    )
    return found


def check_certainty(report: str, sections: list[dict]) -> list[dict]:
    """No cited sentence sits on a certainty rung above the highest of its cited sections."""
    texts = section_index(sections)
    found = []
    for _, text in narrative_blocks(report):
        for sentence, cites in cited_sentences(text):
            if not cites:
                continue
            said = rung(strip_citations(sentence))
            if not said:
                continue
            source = max(rung(texts.get(anchor, "")) for _, anchor in cites)
            if said > source:
                word = highest_word(strip_citations(sentence))
                found.append(
                    failure(
                        "certainty",
                        sentence,
                        f'"{word}" is {rung_name(said)} over a source at {rung_name(source)}',
                    )
                )
    return found


def check_order(report: str, dossier: str) -> list[dict]:
    """The matter is ranked first and nothing lesser only comes before it."""
    documents = {doc for doc, _, _ in document_rows(dossier)}
    lesser = {
        row_document(row) for row in dossier_sections(dossier).get("Lesser matters", [])
    } - documents
    ranked = findings(report)
    if not ranked:
        return []
    found = []
    if not ranked[0][1] & documents:
        found.append(
            failure("order", ranked[0][0], "the first finding cites no document of the matter")
        )
    first = next((place for place, (_, cited) in enumerate(ranked) if cited & documents), None)
    if first is None:
        return found
    for line, cited in ranked[1:first]:
        if cited and cited <= lesser:
            found.append(failure("order", line, "a lesser matter is ranked above the matter"))
    return found


def first_line(report: str) -> str:
    """The first line of the report that says anything, or an empty string for an empty file."""
    for line in report.splitlines():
        if line.strip():
            return line.strip()
    return ""


def check_sections(report: str) -> list[dict]:
    """The report carries a section the model wrote, and is not the schedule on its own."""
    if narrative_blocks(report):
        return []
    return [
        failure(
            "sections",
            first_line(report),
            "the report is the schedule alone and carries none of the five sections: "
            + ", ".join(WRITTEN_HEADINGS),
        )
    ]


def verify(
    report: str,
    sections: list[dict],
    index: list[dict],
    dossier: str,
    mapping: dict[str, str] | None = None,
) -> dict:
    """Runs the five checks over one report and returns the failures, the counts and the verdict."""
    failures = []
    failures.extend(check_citations(report, sections, index, mapping))
    failures.extend(check_numbers(report, sections, dossier))
    failures.extend(check_certainty(report, sections))
    failures.extend(check_order(report, dossier))
    failures.extend(check_sections(report))
    return {"failures": failures, "passes": not failures, "counts": counts_of(failures)}


# ---------------------------------------------------------------- the readout


def counts_of(failures: list[dict]) -> dict[str, int]:
    """How many failures each check found, one entry per check whether or not it found any."""
    return {name: sum(1 for item in failures if item["check"] == name) for name in CHECKS}


def counts_line(sample: str, counts: dict, round_number: int | None = None) -> str:
    """The one line a round prints: the failures of each check, in the order of CHECKS."""
    where = f"verify {sample}" if round_number is None else f"verify {sample} round {round_number}"
    return where + ": " + ", ".join(f"{name} {counts.get(name, 0)}" for name in CHECKS)


def failure_line(item: dict) -> str:
    """One failure written out: the check, the reason, then the line as the report wrote it."""
    return f"{item['check']} | {item['reason']} | {item['line'][:120]}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Reads the command line of one verify run."""
    parser = argparse.ArgumentParser(prog="python -m rlm.verify")
    parser.add_argument("sample_dir")
    parser.add_argument("run_dir")
    parser.add_argument(
        "--out",
        default=None,
        help="a file name under the run directory to write the failures to, printed otherwise",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Verifies the report.md on disk and prints the failures of each check."""
    args = parse_args(argv)
    sample = Path(args.sample_dir).name
    run_dir = Path(args.run_dir)
    for name in ("report.md", "sections.jsonl", "index.jsonl", "dossier.md"):
        if not (run_dir / name).exists():
            print(f"no {name} at {run_dir / name}")
            return 2

    result = verify(
        (run_dir / "report.md").read_text(encoding="utf-8"),
        read_jsonl(run_dir / "sections.jsonl"),
        read_jsonl(run_dir / "index.jsonl"),
        (run_dir / "dossier.md").read_text(encoding="utf-8"),
        read_mapping(run_dir / "map.json"),
    )
    if args.out:
        record = {
            "sample": sample,
            "rounds": [result["failures"]],
            "passes": result["passes"],
        }
        (run_dir / args.out).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    print(counts_line(sample, result["counts"]))
    for item in result["failures"]:
        print(failure_line(item))
    return 0 if result["passes"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
