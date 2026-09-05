"""The section record and its anchor.

A section is one piece of a document: a block of text or a table row. Both flavours carry the
document, an ordinal within the document, a kind, an anchor, a heading, the text and a warning.
A row also carries its cells with their cell references.

The anchor is one string, `<doc>#<place>`, and it is what a later stage cites. There are six
places, one per format:

- `#p2l14`   page 2, line 14 of a PDF, both 1-based
- `#p2t1r3`  page 2, table 1, row 3 of a PDF, all 1-based
- `#l14`     line 14 of plain text, markdown or one mail body, 1-based
- `#m3l14`   message 3 of an mbox, line 14 of its body, both 1-based
- `#Sheet1!A14`  row 14 of sheet Sheet1 of a workbook, at the row's leftmost non-empty column
- `#r14`     row 14 of a CSV file, 1-based

A cell reference is the workbook's own reference for a workbook cell, `r<row>c<col>` for a CSV
cell and `t<table>r<row>c<col>` for a PDF table cell, all 1-based.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

KINDS = frozenset({"text", "row"})

_PAGE_LINE = re.compile(r"^p(\d+)l(\d+)$")
_PAGE_TABLE_ROW = re.compile(r"^p(\d+)t(\d+)r(\d+)$")
_LINE = re.compile(r"^l(\d+)$")
_MESSAGE_LINE = re.compile(r"^m(\d+)l(\d+)$")
_ROW = re.compile(r"^r(\d+)$")
_SHEET_CELL = re.compile(r"^(.+)!([A-Z]+)(\d+)$")


@dataclass(frozen=True)
class Cell:
    """One cell of a table row: its reference within the file and its value."""

    ref: str
    value: str | int | float


@dataclass(frozen=True)
class Section:
    """One block of text or one table row of one document."""

    doc: str
    ordinal: int
    kind: str
    anchor: str
    heading: str | None
    text: str
    warning: str | None
    cells: tuple[Cell, ...] | None = None


@dataclass(frozen=True)
class Anchor:
    """An anchor read back into the document and the place it names.

    The fields a kind does not use are None.
    """

    doc: str
    kind: str
    page: int | None = None
    line: int | None = None
    message: int | None = None
    table: int | None = None
    sheet: str | None = None
    column: str | None = None
    row: int | None = None


def page_line_anchor(doc: str, page: int, line: int) -> str:
    """Builds the anchor of a line on a page of a PDF."""
    return f"{doc}#p{page}l{line}"


def page_table_row_anchor(doc: str, page: int, table: int, row: int) -> str:
    """Builds the anchor of a row of a ruled table on a page of a PDF."""
    return f"{doc}#p{page}t{table}r{row}"


def line_anchor(doc: str, line: int) -> str:
    """Builds the anchor of a line of plain text, markdown or one mail body."""
    return f"{doc}#l{line}"


def message_line_anchor(doc: str, message: int, line: int) -> str:
    """Builds the anchor of a line of one message inside an mbox."""
    return f"{doc}#m{message}l{line}"


def sheet_cell_anchor(doc: str, sheet: str, column: str, row: int) -> str:
    """Builds the anchor of a workbook row at the column its leftmost non-empty cell sits in."""
    return f"{doc}#{sheet}!{column}{row}"


def row_anchor(doc: str, row: int) -> str:
    """Builds the anchor of a row of a CSV file."""
    return f"{doc}#r{row}"


def parse_anchor(anchor: str) -> Anchor:
    """Reads an anchor back into its document and the place it names.

    Raises ValueError when the string is not one of the six anchors this phase writes.
    """
    doc, separator, place = anchor.rpartition("#")
    if not separator or not doc or not place:
        raise ValueError(f"not an anchor: {anchor!r}")

    match = _PAGE_TABLE_ROW.match(place)
    if match:
        page, table, row = (int(group) for group in match.groups())
        return Anchor(doc=doc, kind="page-table-row", page=page, table=table, row=row)

    match = _PAGE_LINE.match(place)
    if match:
        page, line = (int(group) for group in match.groups())
        return Anchor(doc=doc, kind="page-line", page=page, line=line)

    match = _MESSAGE_LINE.match(place)
    if match:
        message, line = (int(group) for group in match.groups())
        return Anchor(doc=doc, kind="message-line", message=message, line=line)

    match = _LINE.match(place)
    if match:
        return Anchor(doc=doc, kind="line", line=int(match.group(1)))

    match = _ROW.match(place)
    if match:
        return Anchor(doc=doc, kind="row", row=int(match.group(1)))

    match = _SHEET_CELL.match(place)
    if match:
        sheet, column, row = match.groups()
        return Anchor(doc=doc, kind="sheet-cell", sheet=sheet, column=column, row=int(row))

    raise ValueError(f"not an anchor: {anchor!r}")


def to_record(section: Section) -> dict:
    """Turns a section into the dict one line of sections.jsonl holds.

    A text section has no cells key at all; a row section carries one entry per cell.
    """
    record = {
        "anchor": section.anchor,
        "doc": section.doc,
        "heading": section.heading,
        "kind": section.kind,
        "ordinal": section.ordinal,
        "text": section.text,
        "warning": section.warning,
    }
    if section.cells is not None:
        record["cells"] = [{"ref": cell.ref, "value": cell.value} for cell in section.cells]
    return record
