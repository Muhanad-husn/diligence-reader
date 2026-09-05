"""Builds runs/<sample>/index.jsonl from the section records ingest has already written.

Every record carries the same seven keys: `kind`, `surface`, `value`, `unit`, `docs`,
`anchors` and `context`. `docs` and `anchors` are lists on every kind, so a version pair and a
series have the same shape as an amount. `kind` is one of `date`, `amount`, `name`,
`identifier`, `status`, `version-pair` and `series`.

One private builder per kind reads the sections and returns its records; `build_index`
concatenates what the builders in `_BUILDERS` return. Records are written sorted by kind, then
by their value, then by their first anchor, so two runs of the same sample write the same
bytes. Nothing here reads a key, opens a socket or calls a model.
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

from rlm.sections import parse_anchor


def build_index(sections: list[dict]) -> list[dict]:
    """Runs every builder over the section records and returns the index records."""
    records: list[dict] = []
    for builder in _BUILDERS:
        records.extend(builder(sections))
    return records


def write_index(run_dir: Path, records: list[dict]) -> None:
    """Writes run_dir / "index.jsonl", one sorted JSON object per line."""
    run_dir.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        records,
        key=lambda record: (
            record["kind"],
            json.dumps(record["value"], sort_keys=True),
            record["anchors"][0],
        ),
    )
    (run_dir / "index.jsonl").write_text(
        "".join(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n" for record in ordered),
        encoding="utf-8",
        newline="\n",
    )


def _record(kind: str, surface, value, unit, docs: list[str], anchors: list[str], context: str) -> dict:
    """Builds one index record with the seven keys every kind carries."""
    return {
        "kind": kind,
        "surface": surface,
        "value": value,
        "unit": unit,
        "docs": docs,
        "anchors": anchors,
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


# ---------------------------------------------------------------------------------------------
# Slice 02 adds the date, amount, name and identifier builders above this line.
# ---------------------------------------------------------------------------------------------


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

_STATUS_SURFACES_UPPER = frozenset(word.upper() for word in _STATUS_SURFACES)


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


_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-./&]*")


def _is_identifier(token: str) -> bool:
    """Says whether a token is a name a thing was given rather than a dictionary word.

    An all-capitals token of three or more letters is one, such as AURORA or NDA; so is a token
    carrying a digit, a hyphen or an underscore, such as DR-069 or legacy_uap_backup_2021. A
    status word is a dictionary word however it is written.
    """
    if len(token) < 3 or token.upper() in _STATUS_SURFACES_UPPER:
        return False
    if token.isalpha():
        return token.isupper()
    return any(character.isdigit() or character in "-_" for character in token)


# Slice 02's identifier records replace this helper once both slices are merged: it reads the
# same tokens out of the file name and the front matter that its identifier builder does.
def _shared_identifiers(sections_by_doc: dict[str, list[dict]]) -> dict[str, list[str]]:
    """The identifiers two or more documents share, each with the documents that carry it."""
    carried: dict[str, set[str]] = {}
    for doc, sections in sections_by_doc.items():
        texts = [_name_words(doc)] + [section["text"] for section in _front_matter(sections)]
        for text in texts:
            for match in _TOKEN.finditer(text):
                token = match.group(0).strip("./-")
                if token and _is_identifier(token):
                    carried.setdefault(token.upper(), set()).add(doc)
    return {token: sorted(docs) for token, docs in sorted(carried.items()) if len(docs) > 1}


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

_ISO_DAY = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b")
_MONTH_DAY_YEAR = re.compile(r"\b([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\b")


def _iso_day(year: int, month: int, day: int) -> str | None:
    """The ISO string of a day, or None where those three numbers are not a day."""
    try:
        return datetime.date(year, month, day).isoformat()
    except ValueError:
        return None


def _first_date(sections: list[dict]) -> str | None:
    """The first date the document's front matter states, as an ISO string.

    These documents put `Date 12 November 2025` in the metadata block under the title, so the
    first date of the front matter is the date the document carries.
    """
    for section in _front_matter(sections):
        for line in section["text"].split("\n"):
            match = _ISO_DAY.search(line)
            if match:
                found = _iso_day(*(int(group) for group in match.groups()))
                if found:
                    return found
            match = _DAY_MONTH_YEAR.search(line)
            if match and match.group(2).lower() in _MONTHS:
                found = _iso_day(
                    int(match.group(3)),
                    _MONTHS.index(match.group(2).lower()) + 1,
                    int(match.group(1)),
                )
                if found:
                    return found
            match = _MONTH_DAY_YEAR.search(line)
            if match and match.group(1).lower() in _MONTHS:
                found = _iso_day(
                    int(match.group(3)),
                    _MONTHS.index(match.group(1).lower()) + 1,
                    int(match.group(2)),
                )
                if found:
                    return found
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


def _version_pair_records(sections: list[dict]) -> list[dict]:
    """One record per pair of documents that are the same matter at two moments."""
    by_doc = _by_document(sections)
    dates = {doc: _first_date(own) for doc, own in by_doc.items()}
    return _pairs_from(
        _shared_identifiers(by_doc),
        _statuses(sections),
        {doc: date for doc, date in dates.items() if date},
        {doc: own[0]["anchor"] for doc, own in by_doc.items()},
    )


# A series steps by a week, a month or a quarter. A day is not a step: a column of consecutive
# days is a calendar, not a series a later phase can read a break in.
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


# Slice 02's date, amount, name and identifier builders join this tuple.
_BUILDERS = (_status_records, _version_pair_records, _series_records)
