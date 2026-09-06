"""Builds runs/<sample>/index.jsonl from the section records.

One builder per kind reads the sections and yields occurrences; equal occurrences are grouped
into one record carrying every document and anchor the value was seen at. This module writes
all seven kinds: `date`, `amount`, `name`, `identifier`, `status`, `version-pair` and `series`.
A status is a document-level record with one anchor as its proof; a version pair joins two
documents that share an identifier, carry opposite status words and are ordered by their dates;
a series is either files whose names differ in a period token or a table column of consecutive
periods.

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

import datetime
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


def _text_pieces(section: dict) -> list[tuple[str, str]]:
    """The text pieces of one section the index reads, each with its own anchor.

    A non-workbook section yields one piece anchored to the section itself. A workbook section
    yields one piece per text cell, each anchored to that cell rather than to the row.
    """
    if section.get("cells") is None:
        heading = section["heading"] or ""
        text = f"{heading}\n{section['text']}" if heading else section["text"]
        return [(text, section["anchor"])]
    anchor = parse_anchor(section["anchor"])
    if anchor.kind != "sheet-cell":
        return [
            (cell["value"], section["anchor"])
            for cell in section["cells"]
            if isinstance(cell["value"], str)
        ]
    doc = section["doc"]
    return [
        (cell["value"], f"{doc}#{anchor.sheet}!{cell['ref']}")
        for cell in section["cells"]
        if isinstance(cell["value"], str)
    ]


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


_SCALE_TOKENS = {
    "mm": 1_000_000,
    "m": 1_000_000,
    "million": 1_000_000,
    "millions": 1_000_000,
    "k": 1_000,
    "000s": 1_000,
    "000": 1_000,
    "thousand": 1_000,
    "thousands": 1_000,
    "bn": 1_000_000_000,
    "b": 1_000_000_000,
    "billion": 1_000_000_000,
    "billions": 1_000_000_000,
}

_SCALE_TOKEN_PATTERN = re.compile(
    r"(?:\(([^()]*)\)|\$([A-Za-z0-9]+))", re.IGNORECASE
)


def _header_scale(header: str) -> float:
    """Reads a scale token off a workbook column header, or 1.0 where it names none.

    The token counts only inside brackets or right after a currency sign, so
    "Revenue ($M)", "($m)", "$m", "(m)", "(£m)", "$000s", "(USD m)" and "Revenue (millions)"
    all scale, while "Month", "Members", "Maturity" and "Market" do not.
    """
    for bracketed, after_sign in _SCALE_TOKEN_PATTERN.findall(header):
        for candidate in (bracketed, after_sign):
            if not candidate:
                continue
            for word in re.findall(r"[A-Za-z]+|[0-9]+s?", candidate):
                lowered = word.lower()
                if lowered in _SCALE_TOKENS:
                    return float(_SCALE_TOKENS[lowered])
    return 1.0


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
        for piece, anchor in _text_pieces(section):
            for start, end, iso in date_matches(piece):
                occurrences.append(
                    (
                        "date",
                        iso,
                        None,
                        piece[start:end],
                        section["doc"],
                        anchor,
                        _context(section),
                    )
                )
    return _group(occurrences)


def _amounts(sections: list[dict]) -> list[dict]:
    """Reads every amount out of the sections, in text and in workbook cells."""
    headers = _sheet_headers(sections)
    occurrences = []
    for section in sections:
        for piece, anchor in _text_pieces(section):
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
                        anchor,
                        _context(section),
                    )
                )
        if section.get("cells") is None:
            continue
        section_anchor = parse_anchor(section["anchor"])
        if section_anchor.kind != "sheet-cell":
            continue
        header = headers.get((section["doc"], section_anchor.sheet), {})
        for cell in section["cells"]:
            if not _is_number(cell["value"]):
                continue
            match = _CELL_REF.match(cell["ref"])
            column_header = header.get(match.group(1), "") if match else ""
            unit = _header_unit(column_header)
            value = float(cell["value"]) * _header_scale(column_header)
            if unit is None and value.is_integer():
                unit = "count"
            cell_anchor = f"{section['doc']}#{section_anchor.sheet}!{cell['ref']}"
            occurrences.append(
                (
                    "amount",
                    value,
                    unit,
                    str(cell["value"]),
                    section["doc"],
                    cell_anchor,
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

    A single word is a name where it stands inside a sentence, rather than at its start, in
    more than one document. That repetition is what stands in for a dictionary. Once a word is
    a name, every occurrence of it is recorded, the start of a line included.
    """
    phrases = []
    words = []
    for section in sections:
        for piece, anchor in _text_pieces(section):
            place = (section["doc"], anchor, _context(section))
            for phrase in _phrases(piece):
                phrases.append(("name", phrase, None, phrase, *place))
            for match in _WORD.finditer(piece):
                mid = _mid_sentence(piece, match.start())
                words.append((mid, ("name", match.group(0), None, match.group(0), *place)))

    repeated = {}
    for mid, occurrence in words:
        if mid:
            repeated.setdefault(occurrence[1], set()).add(occurrence[4])
    established = {surface for surface, docs in repeated.items() if len(docs) > 1}
    kept = [occurrence for mid, occurrence in words if occurrence[1] in established]
    return _group(phrases + kept)


def _identifiers(sections: list[dict]) -> list[dict]:
    """Reads every joined token carrying a digit, which is what an identifier looks like."""
    occurrences = []
    for section in sections:
        for piece, anchor in _text_pieces(section):
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
                        anchor,
                        _context(section),
                    )
                )
    return _group(occurrences)


def _record(kind: str, surface, value, unit, docs: list[str], anchors: list[str], context: str) -> dict:
    """Builds one index record with the seven keys every kind carries.

    `docs` and `anchors` are sorted and unique on every kind; where an order matters, as for
    the draft and the final of a version pair or the members of a series, the value carries it.
    """
    return {
        "kind": kind,
        "surface": surface,
        "value": value,
        "unit": unit,
        "docs": sorted(set(docs)),
        "anchors": sorted(set(anchors)),
        "context": context,
    }


def _by_document(sections: list[dict]) -> dict[str, list[dict]]:
    """Groups the section records by document, keeping each document's own order."""
    grouped: dict[str, list[dict]] = {}
    for section in sections:
        grouped.setdefault(section["doc"], []).append(section)
    return grouped


def _file_name(doc: str) -> str:
    """The document's file name without its directories."""
    return doc.rsplit("/", 1)[-1]


def _name_words(doc: str) -> str:
    """The file name with its separators and its extension turned into spaces.

    `Cyber_Insurance_Notice_Draft_Email.eml` reads as `Cyber Insurance Notice Draft Email`, so
    a word rule sees the words a file name is built from.
    """
    stem = _file_name(doc).rsplit(".", 1)[0]
    return " ".join(part for part in re.split(r"[^A-Za-z0-9]+", stem) if part)


def _front_matter(sections: list[dict], cap: int = 10) -> list[dict]:
    """The document's leading text sections, up to its first heading and at most cap of them.

    This is the block a document states its own status and its own workstream in: the banner,
    the title, the metadata table and the notice under it. A mail message carries its headers
    as the heading of every section, so a mail file has no front matter and only its file name
    speaks for it.
    """
    front = []
    for section in sections:
        if section["kind"] != "text" or section["heading"] is not None:
            break
        front.append(section)
        if len(front) == cap:
            break
    return front



# Each surface a status word is said with, and the word it says. `Audited` is how the two
# audited years say final: neither of them uses the word final anywhere.
_STATUS_SURFACES = {
    "draft": "draft",
    "final": "final",
    "finalised": "final",
    "finalized": "final",
    "audited": "final",
    "redacted": "redacted",
    "privileged": "privileged",
    "confidential": "confidential",
}

_STATUS_WORD = re.compile(r"\b(?:" + "|".join(_STATUS_SURFACES) + r")\b", re.IGNORECASE)



def _status_claims(doc: str, sections: list[dict]) -> dict[str, tuple[str, str, str]]:
    """The status words one document claims, each with the anchor, surface and line saying it.

    A status word counts where the front matter says it with a capital letter, which is how a
    document declares its own state: `Status DRAFT`, `AURORA - Executive Summary (Final)`,
    `CONFIDENTIAL - Project Atlas`. The same word in running prose is lower case and says
    nothing about the document it sits in. The file name is read last, so a word a line of the
    document says is anchored to that line and a word only the file name says is anchored to
    the document's first section.
    """
    claims: dict[str, tuple[str, str, str]] = {}
    lines = []
    for section in _front_matter(sections):
        lines.extend((line, section["anchor"], line) for line in section["text"].split("\n"))
    lines.append((_name_words(doc), sections[0]["anchor"], _file_name(doc)))
    for text, anchor, context in lines:
        for match in _STATUS_WORD.finditer(text):
            surface = match.group(0)
            if surface[0].isupper():
                claims.setdefault(_STATUS_SURFACES[surface.lower()], (anchor, surface, context))
    return claims


def _statuses(sections: list[dict]) -> dict[str, dict[str, tuple[str, str, str]]]:
    """The status claims of every document that makes one."""
    claimed = {}
    for doc, own in _by_document(sections).items():
        claims = _status_claims(doc, own)
        if claims:
            claimed[doc] = claims
    return claimed


def _status_records(sections: list[dict]) -> list[dict]:
    """One record per document and status word, anchored to the line that says it."""
    records = []
    for doc, claims in sorted(_statuses(sections).items()):
        for value, (anchor, surface, context) in sorted(claims.items()):
            records.append(
                _record("status", surface, value, None, [doc], [anchor], context.strip())
            )
    return records


def _first_date(sections: list[dict]) -> str | None:
    """The first date the document's front matter states, as an ISO string.

    These documents put `Date 12 November 2025` in the metadata block under the title, so the
    first date of the front matter is the date the document carries.
    """
    for section in _front_matter(sections):
        for line in section["text"].split("\n"):
            found = date_matches(line)
            if found:
                return found[0][2]
    return None


def _pairs_from(
    identifiers: dict[str, list[str]],
    statuses: dict[str, dict[str, tuple[str, str, str]]],
    dates: dict[str, str],
    first_anchor: dict[str, str],
) -> list[dict]:
    """Pairs a draft with its final over the identifiers they share.

    Two documents are one version pair where they share an identifier, one is a draft and the
    other a final, and their dates order the draft before the final. Where an identifier leaves
    more than one such pair, the identifier is dropped rather than guessed at; where a document
    falls in more than one pair, every pair it is in is dropped.

    Two documents share several identifiers: the pair is named by the one the fewest documents
    in the room carry, which is the one that says what the pair is about. AURORA names the
    forensic pair; NDA, which every document in the room carries, does not.
    """
    named: dict[tuple[str, str], tuple[int, str]] = {}
    for identifier, docs in identifiers.items():
        drafts = [doc for doc in docs if "draft" in statuses.get(doc, {})]
        finals = [doc for doc in docs if "final" in statuses.get(doc, {})]
        candidates = [
            (draft, final)
            for draft in drafts
            for final in finals
            if draft != final
            and dates.get(draft)
            and dates.get(final)
            and dates[draft] < dates[final]
        ]
        if len(candidates) != 1:
            continue
        name = (len(docs), identifier)
        if name < named.get(candidates[0], (len(docs) + 1, "")):
            named[candidates[0]] = name

    counted: dict[str, int] = {}
    for draft, final in named:
        counted[draft] = counted.get(draft, 0) + 1
        counted[final] = counted.get(final, 0) + 1

    records = []
    for (draft, final), (_carried, identifier) in sorted(named.items()):
        if counted[draft] > 1 or counted[final] > 1:
            continue
        records.append(
            _record(
                "version-pair",
                identifier,
                {
                    "draft": draft,
                    "draft_date": dates[draft],
                    "final": final,
                    "final_date": dates[final],
                },
                None,
                [draft, final],
                [first_anchor[draft], first_anchor[final]],
                f"{identifier}, draft {dates[draft]} and final {dates[final]}",
            )
        )
    return records


def _shared_identifiers(sections: list[dict]) -> dict[str, list[str]]:
    """The identifiers two or more documents share, each with the documents that carry it.

    These are the index's own `identifier` records and the `name` records that are one word in
    capitals, which is what a workstream code such as AURORA looks like; a multi-word name is
    a person, a firm or a phrase, not what a draft and its final are the same matter under.
    """
    shared = {}
    for record in _identifiers(sections):
        if len(record["docs"]) > 1:
            shared[record["surface"]] = record["docs"]
    for record in _names(sections):
        surface = record["surface"]
        if len(record["docs"]) > 1 and " " not in surface and surface.isupper():
            shared[surface] = record["docs"]
    return dict(sorted(shared.items()))


def _version_pair_records(sections: list[dict]) -> list[dict]:
    """One record per pair of documents that are the same matter at two moments."""
    by_doc = _by_document(sections)
    dates = {doc: _first_date(own) for doc, own in by_doc.items()}
    return _pairs_from(
        _shared_identifiers(sections),
        _statuses(sections),
        {doc: date for doc, date in dates.items() if date},
        {doc: own[0]["anchor"] for doc, own in by_doc.items()},
    )


_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)

_DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b")


def _iso_day(year: int, month: int, day: int) -> str | None:
    """The ISO string of a day, or None where those three numbers are not a day."""
    try:
        return datetime.date(year, month, day).isoformat()
    except ValueError:
        return None


# A series steps by a week, a month or a quarter. A day is not a step: a column of consecutive


_STEPS = ("week", "month", "quarter")

_CELL_DAY = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?")
_CELL_MONTH = re.compile(r"(\d{4})-(\d{2})")
_CELL_MONTH_NAME = re.compile(r"([A-Za-z]+)\s+(\d{4})")
_CELL_YEAR_QUARTER = re.compile(r"(?:FY)?(\d{4})[ _-]?Q([1-4])", re.IGNORECASE)
_CELL_QUARTER_YEAR = re.compile(r"Q([1-4])[ _-]?(?:FY)?(\d{4})", re.IGNORECASE)


def _period(surface) -> tuple[str, tuple[int, int, int]] | None:
    """Reads a cell into a period: its grain and the three numbers that order it.

    A day is `("day", (year, month, day))`, a month `("month", (year, month, 0))` and a quarter
    `("quarter", (year, quarter, 0))`. Anything else is not a period.
    """
    text = str(surface).strip()
    match = _CELL_DAY.fullmatch(text)
    if match:
        year, month, day = (int(group) for group in match.groups())
        return ("day", (year, month, day)) if _iso_day(year, month, day) else None
    match = _DAY_MONTH_YEAR.fullmatch(text)
    if match and match.group(2).lower() in _MONTHS:
        year, month = int(match.group(3)), _MONTHS.index(match.group(2).lower()) + 1
        day = int(match.group(1))
        return ("day", (year, month, day)) if _iso_day(year, month, day) else None
    match = _CELL_MONTH.fullmatch(text)
    if match and 1 <= int(match.group(2)) <= 12:
        return "month", (int(match.group(1)), int(match.group(2)), 0)
    match = _CELL_MONTH_NAME.fullmatch(text)
    if match and match.group(1).lower() in _MONTHS:
        return "month", (int(match.group(2)), _MONTHS.index(match.group(1).lower()) + 1, 0)
    match = _CELL_YEAR_QUARTER.fullmatch(text)
    if match:
        return "quarter", (int(match.group(1)), int(match.group(2)), 0)
    match = _CELL_QUARTER_YEAR.fullmatch(text)
    if match:
        return "quarter", (int(match.group(2)), int(match.group(1)), 0)
    return None


def _period_text(period: tuple[str, tuple[int, int, int]]) -> str:
    """Writes a period back as the string a record's context shows."""
    grain, (year, second, day) = period
    if grain == "day":
        return f"{year:04d}-{second:02d}-{day:02d}"
    if grain == "month":
        return f"{year:04d}-{second:02d}"
    return f"{year:04d}-Q{second}"


def _step_between(before, after) -> str | None:
    """The step from one period to the next, or None where the two do not step by one."""
    grain, first = before
    other, second = after
    if grain != other:
        return None
    if grain == "day":
        return "week" if (datetime.date(*second) - datetime.date(*first)).days == 7 else None
    if grain == "month":
        gap = (second[0] - first[0]) * 12 + second[1] - first[1]
        return "month" if gap == 1 else "quarter" if gap == 3 else None
    return "quarter" if (second[0] - first[0]) * 4 + second[1] - first[1] == 1 else None


def _step_of(periods: list) -> str | None:
    """The one step a run of periods advances by, or None where it does not advance by one."""
    steps = {_step_between(periods[at], periods[at + 1]) for at in range(len(periods) - 1)}
    return steps.pop() if len(steps) == 1 else None


# A period token in a file name, with the group its year sits in. A year on its own is not a
# period: FY2023 against FY2024 is two years of accounts, not a series with a step.
_PERIOD_IN_NAME = (
    ("month", re.compile(r"(?<![0-9])(\d{4})[_-](0[1-9]|1[0-2])(?![0-9])"), 1),
    ("quarter", re.compile(r"(?<![0-9])(\d{4})[_-]Q([1-4])(?![0-9])", re.IGNORECASE), 1),
    ("quarter", re.compile(r"(?<![A-Za-z0-9])Q([1-4])[_-](\d{4})(?![0-9])", re.IGNORECASE), 2),
)


def _name_period(doc: str) -> tuple[tuple[str, str], str, tuple[str, tuple[int, int, int]]] | None:
    """Splits a document path into the family it belongs to, its stem and the period it names.

    `Monthly_Finance_Pack_2025_09.pdf` gives the family every monthly pack shares, the stem
    `Monthly_Finance_Pack` and the month 2025-09, so the four packs differ only in their month.
    """
    for grain, pattern, year_group in _PERIOD_IN_NAME:
        match = pattern.search(doc)
        if not match:
            continue
        year = int(match.group(year_group))
        second = int(match.group(2 if year_group == 1 else 1))
        before = doc[: match.start()]
        family = (before, doc[match.end() :])
        return family, _file_name(before).rstrip("_-. "), (grain, (year, second, 0))
    return None


def _document_series(sections: list[dict]) -> list[dict]:
    """One record per family of documents whose names share a stem and step by one period."""
    by_doc = _by_document(sections)
    families: dict[tuple[str, str], tuple[str, list[tuple[tuple, str]]]] = {}
    for doc in by_doc:
        split = _name_period(doc)
        if split:
            family, stem, period = split
            families.setdefault(family, (stem, []))[1].append((period, doc))

    records = []
    for _family, (surface, members) in sorted(families.items()):
        if len(members) < 2:
            continue
        members.sort()
        step = _step_of([period for period, _ in members])
        if step not in _STEPS:
            continue
        docs = [doc for _, doc in members]
        records.append(
            _record(
                "series",
                surface,
                {"step": step, "form": "documents", "members": docs},
                None,
                docs,
                [by_doc[doc][0]["anchor"] for doc in docs],
                f"{len(docs)} {step} documents from {_period_text(members[0][0])} "
                f"to {_period_text(members[-1][0])}",
            )
        )
    return records


_SHEET_CELL = re.compile(r"^([A-Z]+)(\d+)$")
_CSV_CELL = re.compile(r"^r\d+c(\d+)$")
_TABLE_CELL = re.compile(r"^t\d+r\d+c(\d+)$")


def _table_of(section: dict) -> str | None:
    """The table a row section belongs to: a sheet, a CSV file or one table on one PDF page."""
    anchor = parse_anchor(section["anchor"])
    if anchor.kind == "sheet-cell":
        return anchor.sheet
    if anchor.kind == "row":
        return ""
    if anchor.kind == "page-table-row":
        return f"p{anchor.page}t{anchor.table}"
    return None


def _column_of(ref: str) -> str | None:
    """The column a cell sits in: its letters in a workbook, its number in a CSV or a table."""
    match = _SHEET_CELL.match(ref)
    if match:
        return match.group(1)
    match = _CSV_CELL.match(ref) or _TABLE_CELL.match(ref)
    return f"c{match.group(1)}" if match else None


def _header_above(rows: list[dict], first: int, column: str) -> tuple[str, str] | None:
    """The text and anchor of the cell one row above the first member, in the same column."""
    if first == 0:
        return None
    above = rows[first - 1]
    for cell in above["cells"]:
        if _column_of(cell["ref"]) == column and str(cell["value"]).strip():
            return str(cell["value"]).strip(), above["anchor"]
    return None


def _row_series(sections: list[dict]) -> list[dict]:
    """One record per table column whose cells run through consecutive periods.

    The record is anchored to the row above the first member, which is the column's header
    where the table has one, and its members are the anchors of the rows themselves.
    """
    tables: dict[tuple[str, str], list[dict]] = {}
    for section in sections:
        if section["kind"] != "row":
            continue
        table = _table_of(section)
        if table is not None:
            tables.setdefault((section["doc"], table), []).append(section)

    records = []
    for (doc, _table), rows in sorted(tables.items()):
        columns: dict[str, list[tuple[int, tuple]]] = {}
        for at, row in enumerate(rows):
            for cell in row["cells"]:
                column = _column_of(cell["ref"])
                period = _period(cell["value"])
                if column and period:
                    columns.setdefault(column, []).append((at, period))
        for column, found in sorted(columns.items()):
            if len(found) < 3:
                continue
            step = _step_of([period for _, period in found])
            if step not in _STEPS:
                continue
            members = [rows[at]["anchor"] for at, _ in found]
            header = _header_above(rows, found[0][0], column)
            surface, anchor = header if header else (column, members[0])
            records.append(
                _record(
                    "series",
                    surface,
                    {"step": step, "form": "rows", "members": members},
                    None,
                    [doc],
                    [anchor],
                    f"{len(members)} {step} rows from {_period_text(found[0][1])} "
                    f"to {_period_text(found[-1][1])}",
                )
            )
    return records


def _series_records(sections: list[dict]) -> list[dict]:
    """The document series and the row series of one sample."""
    return _document_series(sections) + _row_series(sections)



# The builders build_index runs, one per kind.
BUILDERS = (
    _dates,
    _amounts,
    _names,
    _identifiers,
    _status_records,
    _version_pair_records,
    _series_records,
)


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