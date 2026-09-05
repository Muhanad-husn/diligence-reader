"""Builds runs/<sample>/index.jsonl from the section records.

One builder per kind reads the sections and yields occurrences; equal occurrences are grouped
into one record carrying every document and anchor the value was seen at. This module writes
the kinds `date`, `amount`, `name` and `identifier`.

What each builder reads. A text section is read as its heading and its text together, so a mail
header block is read with the body it heads. A table row is read cell by cell, so nothing is
matched across the join between two cells; a numeric workbook cell is read as a number rather
than as text.

Where an amount's unit comes from, in order: the surface itself (`$12m`, `30.1%`, `45-day`);
the words right after the number (`912.8m historical profile records`); for a workbook cell,
the sheet's own header for that column (`Record count`); and where none of those says a unit, a
whole number is a count and a fractional number carries null.

Nothing here reads a key, opens a socket or calls a model.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from rlm.amounts import AMOUNT, date_matches, normalise_amount
from rlm.sections import parse_anchor

# How many words after a number are read for its unit, and what ends that reading early. A
# digit ends it because the words past it belong to the next number, not to this one.
_UNIT_WINDOW = 3
_UNIT_STOP = set("(),;|\t0123456789")

# The characters that, right before a number, mean the number is part of a token rather than an
# amount of its own: the 024 of DR-024, the 2019 of vpauth-legacy-2019, the 20 of 18-20.
_JOINED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_/.")

# A capitalised run of two words or more, which is where a multi-word name is read from.
_PHRASE = re.compile(r"[A-Z][A-Za-z]*(?:\s+(?:&\s+)?[A-Z][A-Za-z]*)+")

# One capitalised word of three letters or more, which is a name only when it repeats.
_WORD = re.compile(r"\b[A-Z][A-Za-z]{2,}\b")

# The longest multi-word name this reads out of one capitalised run.
_PHRASE_WORDS = 4

# A token joined by hyphens, underscores, dots or slashes and carrying a digit, such as
# NQ-17, vpauth-legacy-2019 or legacy_uap_backup_2021.tar.gz.
_IDENTIFIER = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:[-_./][A-Za-z0-9]+)+\b")

# A character that ends a sentence or opens a field, so a capitalised word right after one is
# capitalised by position rather than because it is a name.
_SENTENCE_END = set(".!?:;|•—–-([\"'*")

_CELL_REF = re.compile(r"^([A-Z]+)(\d+)$")

_WHITESPACE = re.compile(r"\s+")

# How much of a section's text a record carries as its context.
_CONTEXT = 240


def _flatten(text: str) -> str:
    """Collapses runs of whitespace to one space and strips the ends."""
    return _WHITESPACE.sub(" ", str(text)).strip()


def _text_pieces(section: dict) -> list[str]:
    """The strings of one section the index reads, each matched on its own."""
    if section.get("cells") is None:
        heading = section["heading"] or ""
        return [f"{heading}\n{section['text']}" if heading else section["text"]]
    return [cell["value"] for cell in section["cells"] if isinstance(cell["value"], str)]


def _context(section: dict) -> str:
    """The context a record carries: the section's own text, flattened and cut short."""
    return _flatten(section["text"])[:_CONTEXT]


def _group(occurrences: list[tuple]) -> list[dict]:
    """Turns occurrences of (kind, value, unit, surface, doc, anchor, context) into records.

    Occurrences of one kind, value and unit become one record. The surface and the context are
    the first occurrence's, and the documents and anchors are sorted, so the records of two
    runs of the same sample are the same.
    """
    records: dict[tuple, dict] = {}
    for kind, value, unit, surface, doc, anchor, context in occurrences:
        key = (kind, value, unit)
        record = records.get(key)
        if record is None:
            records[key] = {
                "kind": kind,
                "surface": surface,
                "value": value,
                "unit": unit,
                "docs": {doc},
                "anchors": {anchor},
                "context": context,
            }
        else:
            record["docs"].add(doc)
            record["anchors"].add(anchor)
    for record in records.values():
        record["docs"] = sorted(record["docs"])
        record["anchors"] = sorted(record["anchors"])
    return list(records.values())


def _mask_dates(text: str) -> str:
    """Blanks every date in a text so that its parts are not read as amounts too."""
    found = date_matches(text)
    if not found:
        return text
    masked = list(text)
    for start, end, _ in found:
        masked[start:end] = " " * (end - start)
    return "".join(masked)


def _joined_to_a_token(text: str, at: int) -> bool:
    """Says whether the number at this position is part of a longer token."""
    if at == 0:
        return False
    before = text[at - 1]
    if before in _JOINED:
        return True
    return before == "-" and at > 1 and (text[at - 2].isalnum() or text[at - 2] == ".")


def _following_unit(text: str, at: int) -> str | None:
    """Reads the unit off the few words that follow a number, or None where they say none."""
    window = text[at : at + 60]
    for stop, character in enumerate(window):
        if character in _UNIT_STOP:
            window = window[:stop]
            break
    words = re.findall(r"[A-Za-z]+", window)[:_UNIT_WINDOW]
    for word in words:
        lowered = word.lower().rstrip("s")
        if lowered in ("record", "month", "day"):
            return lowered + "s"
        if lowered == "percent":
            return "percent"
    return None


def _header_unit(header: str) -> str | None:
    """Reads the unit a workbook column header names, or None where it names none."""
    lowered = header.lower()
    if "$" in header or "usd" in lowered:
        return "USD"
    if "%" in header or "percent" in lowered:
        return "percent"
    if "record" in lowered:
        return "records"
    if "month" in lowered:
        return "months"
    if "day" in lowered:
        return "days"
    return None


def _is_number(value) -> bool:
    """Says whether a cell value is a number rather than text."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _sheet_headers(sections: list[dict]) -> dict[tuple[str, str], dict[str, str]]:
    """Finds each workbook sheet's header row and returns its text by column.

    The header row is the last row of text-only cells above the sheet's first row holding a
    number. A sheet whose first row already holds a number has no header.
    """
    rows: dict[tuple[str, str], dict[int, dict[str, object]]] = {}
    for section in sections:
        if section.get("cells") is None:
            continue
        anchor = parse_anchor(section["anchor"])
        if anchor.kind != "sheet-cell":
            continue
        cells = {}
        for cell in section["cells"]:
            match = _CELL_REF.match(cell["ref"])
            if match:
                cells[match.group(1)] = cell["value"]
        rows.setdefault((section["doc"], anchor.sheet), {})[anchor.row] = cells

    headers: dict[tuple[str, str], dict[str, str]] = {}
    for sheet, by_row in rows.items():
        numbered = sorted(by_row)
        first_data = next(
            (row for row in numbered if any(_is_number(value) for value in by_row[row].values())),
            None,
        )
        if first_data is None:
            continue
        above = [
            row
            for row in numbered
            if row < first_data and not any(_is_number(value) for value in by_row[row].values())
        ]
        if above:
            headers[sheet] = {
                column: str(value) for column, value in by_row[above[-1]].items()
            }
    return headers


def _dates(sections: list[dict]) -> list[dict]:
    """Reads every date out of the sections."""
    occurrences = []
    for section in sections:
        for piece in _text_pieces(section):
            for start, end, iso in date_matches(piece):
                occurrences.append(
                    (
                        "date",
                        iso,
                        None,
                        piece[start:end],
                        section["doc"],
                        section["anchor"],
                        _context(section),
                    )
                )
    return _group(occurrences)


def _amounts(sections: list[dict]) -> list[dict]:
    """Reads every amount out of the sections, in text and in workbook cells."""
    headers = _sheet_headers(sections)
    occurrences = []
    for section in sections:
        for piece in _text_pieces(section):
            masked = _mask_dates(piece)
            for match in AMOUNT.finditer(masked):
                if _joined_to_a_token(piece, match.start()):
                    continue
                surface = piece[match.start() : match.end()].strip()
                value, unit = normalise_amount(surface)
                if unit is None:
                    unit = _following_unit(piece, match.end())
                if unit is None and value.is_integer():
                    unit = "count"
                occurrences.append(
                    (
                        "amount",
                        value,
                        unit,
                        surface,
                        section["doc"],
                        section["anchor"],
                        _context(section),
                    )
                )
        if section.get("cells") is None:
            continue
        anchor = parse_anchor(section["anchor"])
        if anchor.kind != "sheet-cell":
            continue
        header = headers.get((section["doc"], anchor.sheet), {})
        for cell in section["cells"]:
            if not _is_number(cell["value"]):
                continue
            match = _CELL_REF.match(cell["ref"])
            unit = _header_unit(header.get(match.group(1), "")) if match else None
            value = float(cell["value"])
            if unit is None and value.is_integer():
                unit = "count"
            occurrences.append(
                (
                    "amount",
                    value,
                    unit,
                    str(cell["value"]),
                    section["doc"],
                    section["anchor"],
                    _context(section),
                )
            )
    return _group(occurrences)


def _mid_sentence(text: str, at: int) -> bool:
    """Says whether the word at this position follows another word of the same sentence."""
    before = at - 1
    while before >= 0 and text[before] == " ":
        before -= 1
    if before < 0 or text[before] == "\n":
        return False
    return text[before] not in _SENTENCE_END


def _phrases(piece: str) -> list[str]:
    """Reads every capitalised name of two to four words out of a piece of text."""
    found = []
    for match in _PHRASE.finditer(piece):
        tokens = re.findall(r"[A-Za-z]+|&", match.group(0))
        for start in range(len(tokens)):
            if tokens[start] == "&":
                continue
            for length in range(2, _PHRASE_WORDS + 1):
                end = start + length
                if end > len(tokens) or tokens[end - 1] == "&":
                    continue
                found.append(" ".join(tokens[start:end]))
    return found


def _names(sections: list[dict]) -> list[dict]:
    """Reads names: the capitalised multi-word forms, and words that repeat across documents.

    A single word is a name where it stands inside a sentence rather than at its start, and
    where it is in more than one document. That repetition is what stands in for a dictionary.
    """
    phrases = []
    words = []
    for section in sections:
        for piece in _text_pieces(section):
            place = (section["doc"], section["anchor"], _context(section))
            for phrase in _phrases(piece):
                phrases.append(("name", phrase, None, phrase, *place))
            for match in _WORD.finditer(piece):
                if _mid_sentence(piece, match.start()):
                    words.append(("name", match.group(0), None, match.group(0), *place))

    repeated = {}
    for occurrence in words:
        repeated.setdefault(occurrence[1], set()).add(occurrence[4])
    kept = [occurrence for occurrence in words if len(repeated[occurrence[1]]) > 1]
    return _group(phrases + kept)


def _identifiers(sections: list[dict]) -> list[dict]:
    """Reads every joined token carrying a digit, which is what an identifier looks like."""
    occurrences = []
    for section in sections:
        for piece in _text_pieces(section):
            for match in _IDENTIFIER.finditer(piece):
                surface = match.group(0)
                if not any(character.isdigit() for character in surface):
                    continue
                occurrences.append(
                    (
                        "identifier",
                        surface,
                        None,
                        surface,
                        section["doc"],
                        section["anchor"],
                        _context(section),
                    )
                )
    return _group(occurrences)


# The builders build_index runs, one per kind. Slice 03 appends its three to this tuple.
BUILDERS = (_dates, _amounts, _names, _identifiers)


def _order(record: dict) -> tuple:
    """Orders records by kind, then value, then the first anchor."""
    return (record["kind"], json.dumps(record["value"], sort_keys=True), record["anchors"][0])


def build_index(sections: list[dict]) -> list[dict]:
    """Reads the section records and returns the index records, in the order they are written."""
    records: list[dict] = []
    for builder in BUILDERS:
        records.extend(builder(sections))
    records.sort(key=_order)
    return records


def write_index(run_dir: Path, records: list[dict]) -> None:
    """Writes one JSON object per line, keys sorted, lines ending in a single newline."""
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "index.jsonl").write_text(
        "".join(
            json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
            for record in sorted(records, key=_order)
        ),
        encoding="utf-8",
        newline="\n",
    )
