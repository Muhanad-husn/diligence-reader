"""Writes runs/<sample>/dossier.md from the map, the index, the sections and the notes.

The dossier is the matter read out as rows a person can check. It opens with the matter's
document set, the cluster the map built less the documents that argue against the matter, one
line per document with its rank, its title, its folder, its first date and the status words the
index read off it. A cluster document is out of the set when one of its flag quotes carries the
matter's subject and negates the seed's operative verb, and no other document of the cluster
worries about it by name: a master service agreement whose change-of-control clause says a
change of control gives no party a right to terminate is the opposite of the matter the seed
found, however much of its template it shares with the seed. Then the matter's timeline,
the names the notes gave it, its figures with their sources, and the models that were written
after it and still carry its old numbers. Then the comparisons the room's own words make, and
the lesser matters the room holds outside the set.

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

A comparison is written differently, because it has two sides and each side has to be read
back to the document that says it. A comparison row is two or more `<doc> | <quote> | <anchor>`
parts joined by ` || `. A side of a comparison is one or more parts of one document, so a
document may say its half of a comparison in as many places as it takes, and a comparison whose
window, its start and its action sit in three documents has three sides in one row. Eight rules
write the rows: a draft against its final, a booked reserve against a range of what it could
cost, a deadline against the action taken after it, a model against the series it still
assumes, a termination right against what the seed document found, a limit against the holding
that exceeds it, a warranty that nothing material happened against a committee that has not
decided whether it did, and a document that asks to be read against another against what that
one says back. Each rule reads flags, figures and cross references from the notes, version
pairs and consequences from the map, and the sections where the room asks for the comparison in
its own words. Every pair a rule finds is written, and where two
rules reach the same documents they write one row between them. The rows are sorted by the
documents they name.

Lesser matters is the rest of the room: every document outside the matter's set whose note
carries a flag, ranked by the largest money figure its note holds, largest first, and then by
id, so a document with a flag and no money figure follows the ones with money. Each line
carries that figure, the note's first flag and the place it was written.

Nothing here reads the key's facts, its required documents or its decoys, opens a socket or
calls a model. The key is read for the id and path of each document and for nothing else.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from rlm.amounts import date_matches, normalise_amount
from rlm.key import load_key
from rlm.map import as_day, as_iso, figure_number, read_jsonl, read_notes
from rlm.words import (
    COMMON_WORDS,
    COMPARE_WORDS,
    SUBJECT_WORDS,
    TERMINATION_WORDS,
    closest_section,
    content_words,
    document_of,
    folded_words,
    named_by,
    one_line,
    sections_by_document,
    shared_run,
)

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

# What joins the parts of a comparison row.
JOIN = " || "

# How ingest joins the cells of a table row into the row's text.
CELL_JOIN = " | "

_DAY = re.compile(r"\b([0-9]{1,2} [A-Z][a-z]+ [0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})\b")

# What a clause says where it takes a right away.
NEGATION_WORDS = frozenset({"no", "not", "neither", "nor", "without"})

# What stands in front of a word that is being used as a verb.
VERB_MARKERS = frozenset(
    {"to", "may", "shall", "can", "could", "will", "would", "must", "might"}
)

# How many words a negation may sit in front of the verb it takes away.
CLAUSE_SPAN = 10

# A money figure's quote says the figure is a reserve and not an estimate.
RESERVE_WORDS = re.compile(
    r"\b(reserve|reserves|provision|provisions|accrual|accruals|booked)\b", re.IGNORECASE
)

# Two money figures joined by `to` or a dash: a range, not a point.
MONEY_RANGE = re.compile(
    r"\$\s?[0-9][0-9,.]*\s?(?:mm|bn|tn|[mkb])?\s*(?:to|-|\u2013|\u2014)\s*"
    r"\$\s?[0-9][0-9,.]*\s?(?:mm|bn|tn|[mkb])?",
    re.IGNORECASE,
)

# A duration a document writes as a number of days or of months.
DURATION = re.compile(r"\b([0-9]+)[\s-]?(days?|months?)\b", re.IGNORECASE)

# What a document says beside a figure that is a ceiling rather than a reading.
LIMIT_WORDS = re.compile(r"\b(limit|limits|maximum|retention)\b", re.IGNORECASE)

# What a deadline is written with, and what a record says when it was opened on a day.
WINDOW_WORD = re.compile(r"\bwithin\b", re.IGNORECASE)
OPENING_WORDS = re.compile(r"\b(opened|raised|logged)\b", re.IGNORECASE)
TICKET_WORD = re.compile(r"\bticket\b", re.IGNORECASE)

# A warranty carries a negation beside a materiality word. A reservation carries the
# materiality itself and says it is not settled yet.
NEGATIONS = re.compile(r"\b(no|not|never|nor)\b", re.IGNORECASE)
MATERIAL_WORD = re.compile(r"\bmaterial", re.IGNORECASE)
MATERIALITY_WORD = re.compile(r"\bmateriality\b", re.IGNORECASE)
UNSETTLED_WORDS = re.compile(
    r"\b(determinable|undetermined|premature|deferred|pending)\b", re.IGNORECASE
)


def quoted(text) -> str:
    """A quote as a row writes it: one line, without the pipe a table row closes with.

    The quote is the one field of a row allowed to hold a pipe, so the row's own last pipe has
    to be the one before the anchor. A markdown table row closes with a pipe that separates
    nothing from nothing, and dropping it is what lets the row be read back.
    """
    return one_line(text).rstrip("| ")


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
    return f"- {head} | {doc} | {quoted(quote) or EMPTY} | {anchor}"


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


def verbs_in(words: list[str]) -> set[str]:
    """The words a text uses as verbs: the ones it writes straight after `to` or a modal.

    A word too common to say anything is left out. `to` in `likely to give rise to a claim` is a
    preposition the second time, so `a` is not a verb the clause turns on, and reading it as one
    took DR-081 out of sample 1's set.
    """
    spoken = {words[at] for at in range(1, len(words)) if words[at - 1] in VERB_MARKERS}
    return spoken - COMMON_WORDS


def negated_before(words: list[str], verb: str) -> bool:
    """Whether a negation word sits within CLAUSE_SPAN words in front of the verb."""
    for at, word in enumerate(words):
        if word != verb:
            continue
        if NEGATION_WORDS & set(words[max(0, at - CLAUSE_SPAN) : at]):
            return True
    return False


def is_table_row(quote: str) -> bool:
    """Whether a quote is one row of a table, which ingest writes as its cells joined by pipes."""
    return CELL_JOIN in quote


def unique_title_words(nodes: dict[str, dict]) -> dict[str, set[str]]:
    """The words of each document's title that no other document of the room has in its title.

    `msa` and `agreement` name no one document; `harbor` and `granite` each name one.
    """
    counted: dict[str, int] = {}
    held = {doc: content_words(title_of(node["path"])) for doc, node in nodes.items()}
    for words in held.values():
        for word in words:
            counted[word] = counted.get(word, 0) + 1
    return {doc: {word for word in words if counted[word] == 1} for doc, words in held.items()}


def worried_about(cluster: list[str], nodes: dict[str, dict], notes: dict[str, dict]) -> set[str]:
    """The documents another document of the cluster worries about by name.

    A flag that writes `Harbor Foods refund liability ... is unreserved` names the Harbor MSA,
    and that is the room saying the document belongs to what it is worried about. A flag whose
    quote is a table row names nobody: the customer schedule writes one row per customer, so the
    row that carries Granite Manufacturing names it the way it names every other party in the
    list, and the room is not worried about any of them by writing the list down.
    """
    titled = unique_title_words(nodes)
    found = set()
    for doc in cluster:
        note = notes.get(doc)
        if not note:
            continue
        written = content_words(
            " ".join(
                f"{flag['flag']} {flag['quote']}"
                for flag in note["flags"]
                if not is_table_row(flag["quote"])
            )
        )
        for other in cluster:
            if other != doc and titled.get(other, set()) & written:
                found.add(other)
    return found


def matter_set(matter: dict, nodes: dict[str, dict], notes: dict[str, dict]) -> list[str]:
    """The matter's document set: the map's cluster, less the documents that deny the matter.

    A cluster document is out when one of its flag quotes carries the matter's subject and
    negates the operative verb another document of the cluster writes, and no other document of
    the cluster worries about it by name. The words it is read against are the set's own, not the
    seed's alone: northwind's seed is its cap table and the change-of-control clause the Granite
    MSA argues against is written by the Meridian MSA. The subject is the longest run of words
    the two flags both write, holding two words that say something; the operative verb is a word
    both of them use as a verb, right after `to` or a modal; the negation is a negation word
    within ten words in front of that verb in the cluster document's flag and in front of nothing
    in the other's. A master service agreement whose change-of-control clause says a change of
    control shall not give either party any right to terminate is arguing the opposite of the
    matter, and the map, which links documents by the values they share, cannot tell it from the
    agreement that does terminate: the two share their template. A document the room's own
    worries name by title stays, however its own clause reads, because something else put it in
    the matter.
    """
    cluster = sorted(set(matter["cluster"]))
    seeds = [doc for doc in matter["seed"] if doc in notes]
    if not seeds:
        return cluster
    spoken_by = {
        doc: [folded_words(flag["quote"]) for flag in notes[doc]["flags"]]
        for doc in cluster
        if doc in notes
    }
    named = worried_about(cluster, nodes, notes)
    held = []
    for doc in cluster:
        note = notes.get(doc)
        if doc in seeds or not note or doc in named:
            held.append(doc)
            continue
        others = [said for other, flags in spoken_by.items() if other != doc for said in flags]
        denies = False
        for flag in note["flags"]:
            written = folded_words(flag["quote"])
            spoken = verbs_in(written)
            for said in others:
                for verb in sorted(spoken & verbs_in(said)):
                    if not negated_before(written, verb) or negated_before(said, verb):
                        continue
                    if shared_run(written, said) is not None:
                        denies = True
                        break
                if denies:
                    break
            if denies:
                break
        if not denies:
            held.append(doc)
    return held


def documents_rows(matter: dict, nodes: dict[str, dict], held: list[str]) -> list[str]:
    """One line per document of the matter's set, in the order the map ranked them."""
    inside = set(held)
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


def blind_rows(matter: dict, notes: dict[str, dict], held: list[str]) -> list[str]:
    """The map's consequences, one row each: the period or the date, the document, what kind of
    consequence it is with the series that turned or the figure that outlived the matter, and
    the anchor."""
    inside = set(held)
    lines = []
    for found in matter["consequences"]:
        doc = found["doc"]
        if doc not in inside:
            continue
        if found["kind"] == "series-break":
            when = found["period"]
            what = f"series-break {found['series']}"
        else:
            when = found["date"]
            what = f"model-after {found['figure']}"
        lines.append(row(when, doc, what, found["anchor"]))
    return lines


def worry_words(note: dict) -> set[str]:
    """Every word a note wrote down as a worry: its flags, their quotes and their consequences."""
    parts = []
    for flag in note["flags"]:
        parts += [flag["flag"], flag["quote"], flag["consequence"]]
    return content_words(" ".join(parts))


def figure_statements(note: dict) -> list[dict]:
    """The note's figures and flags together, each as an item with a quote and an anchor."""
    return list(note["figures"]) + list(note["flags"])


def days_named(text) -> set[str]:
    """Every day the text names, as ISO days."""
    return {day for _, _, day in date_matches(one_line(text))}


def money_value(surface) -> float | None:
    """What a money surface is worth, or None where the surface names no money."""
    if "$" not in str(surface):
        return None
    try:
        return normalise_amount(surface)[0]
    except ValueError:
        return None


def part(doc: str, quote, anchor: str) -> tuple[str, str, str]:
    """One `<doc> | <quote> | <anchor>` part of a comparison row."""
    return (doc, quoted(quote), anchor)


def version_pairs_rows(matter: dict, notes: dict[str, dict]) -> list[list[tuple[str, str, str]]]:
    """Draft against final: for each version pair, the two flags that share the most words.

    The map paired the two documents; the row quotes the flag of each that shares the most
    words with a flag of the other, and where two pairs share as many, the earlier anchors win.
    """
    inside = set(matter["cluster"])
    rows = []
    for pair in matter["versions"]:
        first, second = pair["docs"][0], pair["docs"][1]
        if not set(pair["docs"]) <= inside:
            continue
        best = None
        for one in notes.get(first, {}).get("flags", []):
            for other in notes.get(second, {}).get("flags", []):
                shared = len(content_words(one["quote"]) & content_words(other["quote"]))
                mark = (-shared, one["anchor"], other["anchor"])
                if best is None or mark < best[0]:
                    best = (mark, one, other)
        if best is None:
            continue
        _, one, other = best
        rows.append(
            [
                part(first, one["quote"], one["anchor"]),
                part(second, other["quote"], other["anchor"]),
            ]
        )
    return rows


def reserve_rows(cluster: list[str], notes: dict[str, dict]) -> list[list[tuple[str, str, str]]]:
    """Reserve against estimate: a booked amount beside a range of what it could cost.

    A document is a reserve where a money figure of its note is quoted beside a reserve word,
    and an estimate where a money figure is quoted beside two money figures joined by `to` or a
    dash. Each document keeps its largest such figure, and every reserve is written against
    every estimate.
    """
    reserves: dict[str, tuple[float, str, str]] = {}
    estimates: dict[str, tuple[float, str, str]] = {}

    def keep(held: dict[str, tuple[float, str, str]], doc: str, found: tuple[float, str, str]):
        """Keeps the largest figure of a document, and the earliest anchor where two are equal."""
        best = held.get(doc)
        if best is None or (-found[0], found[1]) < (-best[0], best[1]):
            held[doc] = found

    for doc in sorted(set(cluster)):
        note = notes.get(doc)
        if not note:
            continue
        for figure in note["figures"]:
            value = money_value(figure["surface"])
            if value is None:
                continue
            quote = one_line(figure["quote"])
            found = (value, figure["anchor"], quote)
            if RESERVE_WORDS.search(quote):
                keep(reserves, doc, found)
            if MONEY_RANGE.search(quote):
                keep(estimates, doc, found)
    rows = []
    for reserve in sorted(reserves):
        for estimate in sorted(estimates):
            if reserve == estimate:
                continue
            _, anchor, quote = reserves[reserve]
            _, place, other = estimates[estimate]
            rows.append([part(reserve, quote, anchor), part(estimate, other, place)])
    return rows


def deadline_rows(
    cluster: list[str], notes: dict[str, dict], sections: list[dict], ids_by_path: dict[str, str]
) -> list[list[tuple[str, str, str]]]:
    """Deadline against action: a window, the day it counts from and the action taken late.

    A window is a figure counted in days quoted beside `within`. Where one document states the
    window and its note names no day beside that window, and another repeats the same window and
    its note does name a day beside it, the second is the document that acted. A day has to sit
    in a quote that writes the window itself, because the cyber policy names its retroactive date
    and its policy year and neither of those is the policy acting on its own 45 days.
    The row carries the window's quote,
    the earliest place in the set where a ticket is opened on a day, and the acting document's
    own part: the first thing it says that shares a word with the window, and, where the
    document has a section that names a day and it is not that same place, the earliest such
    section as well, which is how a mail header's own date reaches the row even where the words
    it shares with the window sit somewhere else in the document.
    """
    windows: dict[str, list[tuple[str, str, str, bool]]] = {}
    for doc in sorted(set(cluster)):
        note = notes.get(doc)
        if not note:
            continue
        written = note["flags"] + note["figures"] + note["concealed"]
        for figure in note["figures"]:
            found = DURATION.search(figure["surface"])
            if not found or not found.group(2).lower().startswith("day"):
                continue
            quote = one_line(figure["quote"])
            if not WINDOW_WORD.search(quote):
                continue
            number = found.group(1)
            counted = re.compile(
                r"\b" + re.escape(number) + r"[\s-]?days?\b", re.IGNORECASE
            )
            dated = any(
                days_named(item["quote"]) and counted.search(one_line(item["quote"]))
                for item in written
            )
            windows.setdefault(number, []).append((doc, quote, figure["anchor"], dated))

    opened = None
    for section in sections:
        doc = document_of(section["anchor"], ids_by_path)
        if doc not in set(cluster):
            continue
        text = one_line(section["text"])
        if not (TICKET_WORD.search(text) and OPENING_WORDS.search(text)):
            continue
        days = days_named(text)
        if not days:
            continue
        mark = (min(days), section["anchor"])
        if opened is None or mark < opened[0]:
            opened = (mark, part(doc, text, section["anchor"]))

    rows = []
    for number in sorted(windows):
        stated = [found for found in windows[number] if not found[3]]
        acted = [found for found in windows[number] if found[3]]
        for doc, quote, anchor, _ in sorted(stated):
            for other, _, _, _ in sorted(acted):
                if other == doc:
                    continue
                first = None
                for section in sections:
                    if document_of(section["anchor"], ids_by_path) != other:
                        continue
                    text = one_line(section["text"])
                    if content_words(text) & content_words(quote):
                        first = part(other, text, section["anchor"])
                        break
                if first is None:
                    continue
                dated = None
                for section in sections:
                    if document_of(section["anchor"], ids_by_path) != other:
                        continue
                    if section["anchor"] == first[2]:
                        continue
                    text = one_line(section["text"])
                    if days_named(text):
                        dated = part(other, text, section["anchor"])
                        break
                found = [part(doc, quote, anchor), first]
                if dated is not None:
                    found.append(dated)
                if opened is not None and opened[1][0] not in (doc, other):
                    found.append(opened[1])
                rows.append(found)
    return rows


def model_rows(
    matter: dict, notes: dict[str, dict], cluster: list[str]
) -> list[list[tuple[str, str, str]]]:
    """Model against metrics: a figure a model still assumes against what the series did.

    Each model the map dated after the matter is written against every series that turned and
    carries the same figure. The model's side is the figure the map cited and every flag of the
    same document that speaks of it. The series' side is the flag that names the period the
    series turned in and the lowest dated reading the document holds.
    """
    inside = set(cluster)
    consequences = [found for found in matter["consequences"] if found["doc"] in inside]
    breaks = [found for found in consequences if found["kind"] == "series-break"]
    models = [found for found in consequences if found["kind"] == "model-after"]
    rows = []
    for model in models:
        note = notes.get(model["doc"])
        if not note:
            continue
        number = model["figure"]
        figures = [
            item
            for item in note["figures"]
            if item["anchor"] == model["anchor"] and figure_number(item["surface"]) == number
        ]
        if not figures:
            continue
        figure = figures[0]
        held = content_words(figure["quote"])
        side = [part(model["doc"], figure["quote"], figure["anchor"])]
        for flag in note["flags"]:
            if content_words(flag["quote"]) & held:
                side.append(part(model["doc"], flag["quote"], flag["anchor"]))
        for found in breaks:
            other = notes.get(found["doc"])
            if not other:
                continue
            if number not in {figure_number(item["surface"]) for item in other["figures"]}:
                continue
            turned = [
                part(found["doc"], flag["quote"], flag["anchor"])
                for flag in other["flags"]
                if found["period"] in days_named(flag["quote"])
            ]
            lowest = None
            for item in other["figures"]:
                reading = figure_number(item["surface"])
                if reading is None or not days_named(item["quote"]):
                    continue
                mark = (float(reading), item["anchor"])
                if lowest is None or mark < lowest[0]:
                    lowest = (mark, part(found["doc"], item["quote"], item["anchor"]))
            if not turned or lowest is None:
                continue
            rows.append(side + turned + [lowest[1]])
    return rows


def covenant_rows(
    matter: dict, notes: dict[str, dict], cluster: list[str]
) -> list[list[tuple[str, str, str]]]:
    """Covenant against incident: a termination right against what the seed document found.

    A covenant is a flag quoted with a termination word. It is written against the leading
    finding of the matter's seed document, the first flag of its note, which is the finding the
    room's other documents answer to. Picking the seed flag by shared words was measured on the
    #106 notes and landed on the key-rotation flag, whose words the clause repeats, not on the
    export the clause is a right to terminate over.
    """
    seeds = [doc for doc in matter["seed"] if doc in notes]
    rows = []
    for doc in sorted(set(cluster)):
        note = notes.get(doc)
        if not note:
            continue
        worries = worry_words(note)
        for flag in note["flags"]:
            if not TERMINATION_WORDS.search(one_line(flag["quote"])):
                continue
            held = content_words(flag["quote"])
            for seed in seeds:
                if seed == doc:
                    continue
                best = None
                for other in notes[seed]["flags"][:1]:
                    written = content_words(
                        f"{other['flag']} {other['quote']} {other['consequence']}"
                    )
                    shared = len(held & content_words(other["quote"])) + len(worries & written)
                    mark = (-shared, other["anchor"])
                    if best is None or mark < best[0]:
                        best = (mark, other)
                if best is None:
                    continue
                rows.append(
                    [
                        part(doc, flag["quote"], flag["anchor"]),
                        part(seed, best[1]["quote"], best[1]["anchor"]),
                    ]
                )
    return rows


def compare_rows(
    matter: dict,
    nodes: dict[str, dict],
    notes: dict[str, dict],
    sections: list[dict],
    ids_by_path: dict[str, str],
    cluster: list[str],
) -> list[list[tuple[str, str, str]]]:
    """Asked against answered: a document that says to read it against another, and both answers.

    A note names another document of the set by its id or its file name, and the place where it
    names it asks for the comparison in its own words. The row carries that place, the place in
    the named document that shares the most words with it, and the place back in the naming
    document that shares the most words with that one. The row quotes the sections and not the
    note, because it is the room asking: what a workbook answers a memo with is a row of the
    workbook, not a worry someone wrote about it.

    The words of the two documents' own names are not counted on either side. A memo that says
    to read it against `revenue_summary.xlsx` shares the word revenue with every row of that
    workbook, and the row wanted is the one that shares what the memo is asking about.
    """
    inside = set(cluster)
    held = sections_by_document(sections, ids_by_path)
    named = named_by(nodes)
    rows = []
    for doc in sorted(inside):
        note = notes.get(doc)
        if not note:
            continue
        asked = set()
        for reference in note["cross_references"]:
            other = named.get(str(reference["value"]).strip().upper())
            if other is None or other == doc or other not in inside:
                continue
            asked.add((reference["anchor"], other))
        for anchor, other in sorted(asked):
            text = dict(held.get(doc, [])).get(anchor)
            if not text or not COMPARE_WORDS.search(text):
                continue
            without = content_words(
                f"{doc} {nodes[doc]['path']} {other} {nodes[other]['path']}"
            )
            answer = closest_section(held.get(other, []), text, without)
            if answer is None:
                continue
            back = closest_section(held.get(doc, []), answer[1], without)
            found = [part(doc, text, anchor), part(other, answer[1], answer[0])]
            if back is not None:
                found.append(part(doc, back[1], back[0]))
            rows.append(found)
    return rows


def policy_rows(
    nodes: dict[str, dict], notes: dict[str, dict], cluster: list[str]
) -> list[list[tuple[str, str, str]]]:
    """Policy against practice: a limit a document sets against what another document holds.

    A policy is a duration figure whose own place in the document also carries a flag with a
    limit word. The practice is every other document whose note repeats that duration in a
    quote that carries a figure of its own, which is where a holding is measured against the
    limit rather than the limit restated.
    """
    limits = []
    for doc in sorted(set(cluster)):
        note = notes.get(doc)
        if not note:
            continue
        limiting = [
            flag for flag in note["flags"] if LIMIT_WORDS.search(one_line(flag["quote"]))
        ]
        flagged = {flag["anchor"] for flag in limiting}
        for figure in note["figures"]:
            found = DURATION.fullmatch(figure["surface"].strip())
            if not found or figure["anchor"] not in flagged:
                continue
            side = [part(doc, figure["quote"], figure["anchor"])]
            for flag in limiting:
                if flag["anchor"] == figure["anchor"]:
                    side.append(part(doc, flag["quote"], flag["anchor"]))
            limits.append((doc, found.group(1), found.group(2).lower().rstrip("s"), side))

    rows = []
    for doc, number, unit, side in limits:
        same = re.compile(rf"\b{number}[\s-]?{unit}s?\b", re.IGNORECASE)
        for other in sorted(set(cluster)):
            note = notes.get(other)
            if other == doc or not note:
                continue
            held = []
            for item in figure_statements(note):
                quote = one_line(item["quote"])
                if not same.search(quote):
                    continue
                digits = set(re.findall(r"[0-9]+", quote.replace(",", ""))) - {number}
                if not digits:
                    continue
                found = part(other, quote, item["anchor"])
                if found not in held:
                    held.append(found)
            if held:
                rows.append(side + held)
    return rows


def warranty_rows(cluster: list[str], notes: dict[str, dict]) -> list[list[tuple[str, str, str]]]:
    """Warranty against reservation: nothing material happened against nothing decided yet.

    A warranty is a flag quoted with a negation beside a materiality word. A reservation is a
    flag quoted with the materiality itself and a word that says it is not settled. Every
    warranty is written against every reservation.
    """
    warranties = []
    reservations = []
    for doc in sorted(set(cluster)):
        note = notes.get(doc)
        if not note:
            continue
        for flag in note["flags"]:
            quote = one_line(flag["quote"])
            found = part(doc, quote, flag["anchor"])
            if MATERIALITY_WORD.search(quote) and UNSETTLED_WORDS.search(quote):
                reservations.append(found)
            elif NEGATIONS.search(quote) and MATERIAL_WORD.search(quote):
                warranties.append(found)
    rows = []
    for warranty in warranties:
        for reservation in reservations:
            if warranty[0] != reservation[0]:
                rows.append([warranty, reservation])
    return rows


def comparison_lines(
    matter: dict,
    nodes: dict[str, dict],
    notes: dict[str, dict],
    sections: list[dict],
    ids_by_path: dict[str, str],
    cluster: list[str],
) -> list[str]:
    """Every comparison the rules find, one row each, sorted by the documents they name.

    A row is two or more `<doc> | <quote> | <anchor>` parts joined by ` || `. A side of a
    comparison is one or more parts of one document, so a document says its half of a
    comparison in as many places as it takes. Two rules that reach the same documents write one
    row between them.
    """
    rows = (
        version_pairs_rows(matter, notes)
        + reserve_rows(cluster, notes)
        + deadline_rows(cluster, notes, sections, ids_by_path)
        + model_rows(matter, notes, cluster)
        + covenant_rows(matter, notes, cluster)
        + policy_rows(nodes, notes, cluster)
        + warranty_rows(cluster, notes)
        + compare_rows(matter, nodes, notes, sections, ids_by_path, cluster)
    )
    merged: dict[tuple[str, ...], list[tuple[str, str, str]]] = {}
    for found in rows:
        named = tuple(sorted({doc for doc, _, _ in found}))
        held = merged.setdefault(named, [])
        for one in found:
            if one not in held:
                held.append(one)
    lines = []
    for named in merged:
        held = sorted(merged[named], key=lambda one: (one[0], one[2], one[1]))
        lines.append(
            (
                tuple(doc for doc, _, _ in held),
                "- "
                + JOIN.join(
                    f"{doc} | {quote or EMPTY} | {anchor}" for doc, quote, anchor in held
                ),
            )
        )
    return [line for _, line in sorted(lines)]


def lesser_lines(
    matter: dict, nodes: dict[str, dict], notes: dict[str, dict], held: list[str]
) -> list[str]:
    """Every flagged document outside the matter's set, ranked by the money its note holds.

    The rank is the largest money figure of the note, largest first, and then the document id,
    so a document with a flag and no money figure follows the ones with money. The line carries
    that figure, the note's first flag and the place it was written.
    """
    inside = set(held)
    found = []
    for doc in sorted(nodes):
        note = notes.get(doc)
        if doc in inside or not note or not note["flags"]:
            continue
        largest, surface = 0.0, EMPTY
        for figure in note["figures"]:
            value = money_value(figure["surface"])
            if value is not None and value > largest:
                largest, surface = value, figure["surface"]
        flag = note["flags"][0]
        found.append((-largest, doc, surface, flag["quote"], flag["anchor"]))
    return [row(surface, doc, quote, anchor) for _, doc, surface, quote, anchor in sorted(found)]


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
        cluster = matter_set(matter, nodes, notes)
        written = {
            "Documents": documents_rows(matter, nodes, cluster),
            "Timeline": timeline_rows(cluster, notes, nodes, records, held, ids_by_path),
            "Names": names_rows(cluster, notes),
            "Figures": figures_rows(cluster, notes),
            "Models blind to it": blind_rows(matter, notes, cluster),
            "Comparisons": comparison_lines(
                matter, nodes, notes, sections, ids_by_path, cluster
            ),
            "Lesser matters": lesser_lines(matter, nodes, notes, cluster),
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


def first_matter(text: str) -> str:
    """The dossier's first matter, from its heading to the next matter's heading or the end."""
    found: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("## Matter "):
            if found:
                break
            found.append(line)
        elif found:
            found.append(line)
    return "".join(found)


def readout_line(sample: str, text: str, seconds: float) -> str:
    """The one line a dossier run prints: the counts per section and the time it took.

    `set` is how many documents the matter's set holds after the clause rule, which is the
    number of Documents rows. `tokens` is what the first matter costs to hand a model, estimated
    at one token per four characters, which is close enough for a line that says whether the
    matter still fits.
    """
    counted = {heading: 0 for heading in SECTIONS}
    heading = None
    for line in text.splitlines():
        if line.startswith("### "):
            heading = line[4:].strip()
        elif heading and line.startswith("- "):
            counted[heading] += 1
    tokens = len(first_matter(text)) // 4
    return (
        f"dossier {sample}: documents {counted['Documents']}, "
        f"timeline {counted['Timeline']}, "
        f"names {counted['Names']}, "
        f"figures {counted['Figures']}, "
        f"consequences {counted['Models blind to it']}, "
        f"comparisons {counted['Comparisons']}, "
        f"lesser matters {counted['Lesser matters']}, "
        f"set {counted['Documents']}, "
        f"tokens ~{tokens}, "
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
