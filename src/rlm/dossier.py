"""Writes runs/<sample>/dossier.md from the map, the index, the sections and the notes.

The dossier is the matter read out as rows a person can check. It opens with the matter's
document set, the cluster the map built, one line per document with its rank, its title, its
folder, its first date and the status words the index read off it. Then the matter's timeline,
the names the notes gave it, its figures with their sources, and the models that were written
after it and still carry its old numbers. The comparisons and the lesser matters are headings
with no rows in this slice.

Every row is `- <date or figure> | <doc> | <quote> | <anchor>`. A `Documents` line is
`- <rank>. <doc> | <title> | <folder> | <date> | <status>`. The quote is what the note wrote or
what the section holds, with its whitespace collapsed to one line and nothing else changed; a
table row's cells are themselves written with pipes, so the quote is the one field that keeps
its own pipes, the anchor is the last field of a row and the quote is everything between the
document and it. A pipe anywhere else would end its field early, so a pipe in the date or
figure field is written as a slash.

The title is the document's file name without its extension. A heading is not a title in this
room: half the documents are prose the sections gave no heading at all, and the other half are
spreadsheets whose first heading is the name of a sheet.

The timeline is every statement of the set that carries a day. A note's flag or concealed item
is a statement the document makes, dated by the day its own words name and otherwise by the
document's first date. A note's figure is a timeline row where its quote names a day. The
index's dated sections are rows as well, which is how a day the document writes as `18 October
2025` reaches the timeline as `2025-10-18`: the date field carries the day, the quote carries
the words.

Nothing here reads the key's facts, its required documents or its decoys, opens a socket or
calls a model. The key is read for the id and path of each document and for nothing else.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from rlm.key import load_key
from rlm.map import as_day, as_iso, document_of, figure_number, read_jsonl, read_notes

# The headings one matter carries, in the order they are written.
SECTIONS = (
    "Documents",
    "Timeline",
    "Names",
    "Figures",
    "Models blind to it",
    "Comparisons",
    "Lesser matters",
)

# The cross reference kinds the Names section keeps. A person is not a name for the matter: a
# general counsel signs the tax memo and the forensic memo alike.
NAME_KINDS = frozenset({"code", "name", "ticket"})

# How many documents have to share a name before it is a name for the matter.
NAME_CARRIERS = 2

# What an empty field is written as, so every row has the same number of fields.
EMPTY = "-"

# What a row with no day sorts under, after every dated row.
UNDATED = "9999-99-99"

_WHITESPACE = re.compile(r"\s+")
_DAY = re.compile(r"\b([0-9]{1,2} [A-Z][a-z]+ [0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})\b")


def one_line(text) -> str:
    """The text with every run of whitespace collapsed to one space and the ends trimmed.

    Nothing else is changed, so a quote stays the note's own words and a markdown mark the note
    wrote is still there for a reader to see.
    """
    return _WHITESPACE.sub(" ", str(text)).strip()


def title_of(path: str) -> str:
    """The document's title: its file name up to the first dot, with underscores as spaces."""
    return Path(path).name.split(".", 1)[0].replace("_", " ")


def row(first, doc: str, quote, anchor: str) -> str:
    """One row of the dossier in the grammar the phase fixes.

    The quote is the only field allowed to hold a pipe, because a table row's cells are written
    that way and the quote is verbatim. A pipe in the date or figure field is written as a
    slash, so that a reader and a parser both find the document in the second field.
    """
    head = one_line(first).replace("|", "/") or EMPTY
    return f"- {head} | {doc} | {one_line(quote) or EMPTY} | {anchor}"


def day_in(text) -> str | None:
    """The first day the text names, as an ISO day, or None where it names none.

    A document writes `18 October 2025` and a spreadsheet writes `2025-10-18`; both read as
    2025-10-18.
    """
    for match in _DAY.finditer(str(text)):
        day = as_day(match.group(1))
        if day is not None:
            return day.isoformat()
    return None


def text_by_anchor(sections: list[dict]) -> dict[str, str]:
    """What every section and every table cell of the run holds, by the anchor that names it."""
    found: dict[str, str] = {}
    for section in sections:
        found.setdefault(section["anchor"], section["text"])
        for cell in section.get("cells") or []:
            anchor = f"{section['doc']}#{section['heading']}!{cell['ref']}"
            found.setdefault(anchor, section["text"])
    return found


def statements(note: dict) -> list[tuple[str, str, str]]:
    """A note's flags and concealed items, as (field, anchor, quote), in the note's own order."""
    found = []
    for flag in note["flags"]:
        found.append(("flag", flag["anchor"], flag["quote"]))
    for item in note["concealed"]:
        found.append(("concealed", item["anchor"], item["quote"]))
    return found


def documents_rows(matter: dict, nodes: dict[str, dict]) -> list[str]:
    """One line per document of the matter's set, in the order the map ranked them."""
    inside = set(matter["cluster"])
    lines = []
    for rank, ranked in enumerate(matter["ranked"], start=1):
        doc = ranked["doc"]
        if doc not in inside:
            continue
        node = nodes[doc]
        status = ", ".join(node["status"]) or EMPTY
        lines.append(
            f"- {rank}. {doc} | {title_of(node['path'])} | {node['folder'] or EMPTY} "
            f"| {node['date'] or EMPTY} | {status}"
        )
    return lines


def timeline_rows(
    cluster: list[str],
    notes: dict[str, dict],
    nodes: dict[str, dict],
    records: list[dict],
    held: dict[str, str],
    ids_by_path: dict[str, str],
) -> list[str]:
    """Every dated statement of the set, one row per statement, sorted by day.

    A flag or a concealed item is dated by the day its own quote names, and where it names none
    by the document's first date. A figure is a row where its quote names a day. Every dated
    section the index read is a row as well, which is what puts the index's own ISO day beside
    the words the document used.
    """
    inside = set(cluster)
    found: set[tuple[str, str, str, str]] = set()
    for doc in inside:
        note = notes.get(doc)
        if not note:
            continue
        for _, anchor, quote in statements(note):
            day = day_in(quote) or nodes[doc]["date"] or UNDATED
            found.add((day, doc, one_line(quote), anchor))
        for figure in note["figures"]:
            day = day_in(figure["quote"])
            if day:
                found.add((day, doc, one_line(figure["quote"]), figure["anchor"]))
    for record in records:
        if record["kind"] != "date" or as_iso(record["value"]) is None:
            continue
        for anchor in record["anchors"]:
            doc = document_of(anchor, ids_by_path)
            if doc not in inside:
                continue
            found.add((str(record["value"]), doc, one_line(held.get(anchor, "")), anchor))
    return [
        row(day if day != UNDATED else EMPTY, doc, quote, anchor)
        for day, doc, quote, anchor in sorted(found)
    ]


def names_rows(cluster: list[str], notes: dict[str, dict]) -> list[str]:
    """Every ticket, code or name two or more documents of the set share, with a place each."""
    inside = set(cluster)
    carriers: dict[str, dict[str, tuple[str, str]]] = {}
    for doc in sorted(inside):
        note = notes.get(doc)
        if not note:
            continue
        for reference in note["cross_references"]:
            if reference["kind"] not in NAME_KINDS:
                continue
            carriers.setdefault(reference["value"], {}).setdefault(
                doc, (reference["quote"], reference["anchor"])
            )
    lines = []
    for value in sorted(carriers):
        held = carriers[value]
        if len(held) < NAME_CARRIERS:
            continue
        for doc in sorted(held):
            quote, anchor = held[doc]
            lines.append(row(value, doc, quote, anchor))
    return lines


def figures_rows(cluster: list[str], notes: dict[str, dict]) -> list[str]:
    """Every figure of the set's notes with its quote and its anchor, by document then anchor."""
    lines = []
    for doc in sorted(set(cluster)):
        note = notes.get(doc)
        if not note:
            continue
        seen = sorted(
            (figure["anchor"], figure["surface"], one_line(figure["quote"]))
            for figure in note["figures"]
        )
        for anchor, surface, quote in seen:
            lines.append(row(surface, doc, quote, anchor))
    return lines


def blind_rows(matter: dict, notes: dict[str, dict]) -> list[str]:
    """The map's consequences, one row each: the period or the date, the document, what kind of
    consequence it is with the series that turned or the figure that outlived the matter, and
    the anchor."""
    lines = []
    for found in matter["consequences"]:
        doc = found["doc"]
        if found["kind"] == "series-break":
            when = found["period"]
            what = f"series-break {found['series']}"
        else:
            when = found["date"]
            surface = EMPTY
            for figure in notes.get(doc, {}).get("figures", []):
                if figure["anchor"] == found["anchor"]:
                    surface = figure_number(figure["surface"]) or figure["surface"]
                    break
            what = f"model-after {surface}"
        lines.append(row(when, doc, what, found["anchor"]))
    return lines


def build_dossier(sample_dir: Path, run_dir: Path) -> str:
    """Reads a sample's map, index, sections and notes and returns the dossier's markdown."""
    key = load_key(sample_dir)
    ids_by_path = {path: doc_id for doc_id, path in key.documents.items()}

    document = json.loads((run_dir / "map.json").read_text(encoding="utf-8"))
    sections = read_jsonl(run_dir / "sections.jsonl")
    records = read_jsonl(run_dir / "index.jsonl")
    notes = read_notes(run_dir, ids_by_path)
    held = text_by_anchor(sections)
    nodes = {node["doc"]: node for node in document["documents"]}

    lines = [f"# Dossier: {document['sample']}", ""]
    for matter in document["matters"]:
        cluster = matter["cluster"]
        written = {
            "Documents": documents_rows(matter, nodes),
            "Timeline": timeline_rows(cluster, notes, nodes, records, held, ids_by_path),
            "Names": names_rows(cluster, notes),
            "Figures": figures_rows(cluster, notes),
            "Models blind to it": blind_rows(matter, notes),
            "Comparisons": [],
            "Lesser matters": [],
        }
        lines.append(f"## Matter {matter['id']}")
        lines.append("")
        lines.append(f"Seed {', '.join(matter['seed'])}. Date {matter['date'] or EMPTY}.")
        lines.append("")
        for heading in SECTIONS:
            lines.append(f"### {heading}")
            lines.append("")
            lines.extend(written[heading])
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def write_dossier(text: str, run_dir: Path) -> Path:
    """Writes the dossier to runs/<sample>/dossier.md with one trailing newline."""
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "dossier.md"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def readout_line(sample: str, text: str, seconds: float) -> str:
    """The one line a dossier run prints: the counts per section and the time it took."""
    counted = {heading: 0 for heading in SECTIONS}
    heading = None
    for line in text.splitlines():
        if line.startswith("### "):
            heading = line[4:].strip()
        elif heading and line.startswith("- "):
            counted[heading] += 1
    return (
        f"dossier {sample}: documents {counted['Documents']}, "
        f"timeline {counted['Timeline']}, "
        f"names {counted['Names']}, "
        f"figures {counted['Figures']}, "
        f"consequences {counted['Models blind to it']}, "
        f"seconds {seconds:.1f}"
    )


def main(argv: list[str]) -> int:
    """Writes one sample's dossier from the command line and prints the readout line."""
    if len(argv) != 2:
        print("usage: python -m rlm.dossier <sample_dir> <run_dir>")
        return 2
    sample_dir, run_dir = Path(argv[0]), Path(argv[1])
    started = time.monotonic()
    text = build_dossier(sample_dir, run_dir)
    write_dossier(text, run_dir)
    sample = json.loads((run_dir / "map.json").read_text(encoding="utf-8"))["sample"]
    print(readout_line(sample, text, time.monotonic() - started))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
