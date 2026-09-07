"""Writes one note per document from one gateway call, verified and anchored by code.

The model sees the document's section text in ordinal order and nothing else: no anchors, no
key, no other document. It answers with one JSON object holding what the document is, its
flags, its figures, its cross references and what it conceals, quoting the document verbatim.

Code then verifies every item against the document's own sections. An item must carry every
required key of its field as a string: a flag has flag, quote and consequence, a figure has
surface and quote, a cross reference has kind, value and quote, and a concealed item has claim
and quote. An item that answers with the model's own key names instead fails. A quote passes
when its text, with whitespace collapsed, curly quotes and apostrophes straightened, and
markdown emphasis marks dropped, is a substring of one section's text treated the same way, or
of two adjacent sections joined by one space. Case is not folded. The anchor written into the
note is the anchor of the section where the quote starts, and the model's own anchor, if it
writes one, is discarded. A figure passes
when its quote passes and its surface string is inside that quote. Two items of one field that
match on every key are kept once.

Code then harvests the figures the model did not write. Every unit of the document that carries
a currency amount or a percentage becomes a figure of the note: a unit is one sentence of a text
section, whitespace collapsed so a sentence that runs over the page's line ends is one quote, or
one cell of a table row. A plain count or magnitude with no sign, 24 months or 912.8m, is left
to the model. The harvested items go through the same verification as the model's, they carry
the anchor of the section they were read from, and one that matches a model figure on every key
is kept once. The model's items lead the field and the harvested ones follow in document order.

A document whose items fail is asked again once, with its first reply and, for each failed
item, its field, its quote and the reason it failed. The note is then the union, field by
field, of what verified on the first reply and what verifies on the second, so a second reply
that answers with fewer items loses nothing; an item both replies write is kept once. What
fails on the second reply is dropped and written to notes-verify.jsonl. A reply that is not one
JSON object, or that has no what or none of the four lists, is asked again with the exact key
names, and a second reply that fails the same way drops the note whole. There is no third call.
A document the key names but sections.jsonl does not carry is dropped without a call.

Every reply text is written verbatim to runs/<sample>/notes-raw/<document>.<attempt>.txt, so a
pass can be read back without calling the model again.

The documents run eight at a time inside one ledger batch, so a pass is one line of LEDGER.md
and one runs/<sample>/notes-summary.json. A pass over every document of the key writes that
summary from what this call did. A pass over --only documents merges into it instead: the
counts are read back from what is on disk afterward, and the usage of the documents just
replaced is swapped for their new usage in the previous totals.

The bake-off of 2026-09-06 chose z-ai/glm-5.3-flash, DEFAULT_MODEL below, as the model this
phase runs on when --model is left off.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
import time
from pathlib import Path

from rlm.amounts import AMOUNT
from rlm.gateway import Batch, Completion, Gateway, Ledger, estimate_tokens, price
from rlm.key import load_key

PHASE = 2

# The bake-off's winner, the cheapest row whose pass a carried every phase 2 fact of every
# sample (PLAN.md section 5).
DEFAULT_MODEL = "z-ai/glm-5.3-flash"

# Documents in flight at once, as the winning run's leaf did.
WORKERS = 8

NOTE_KEYS = frozenset(
    {"doc", "model", "pass", "what", "flags", "figures", "cross_references", "concealed", "usage"}
)

# The four fields whose items carry a quote and get an anchor.
QUOTED_FIELDS = ("flags", "figures", "cross_references", "concealed")

CROSS_REFERENCE_KINDS = frozenset({"code", "name", "person", "document", "regulator", "ticket"})

# The keys code keeps from each item of a quoted field, beside the anchor it writes. Every one
# of them must be a string in the reply or the item does not verify.
FIELD_KEYS: dict[str, tuple[str, ...]] = {
    "flags": ("flag", "quote", "consequence"),
    "figures": ("surface", "quote"),
    "cross_references": ("kind", "value", "quote"),
    "concealed": ("claim", "quote"),
}

# The keys that name an item inside its field, written to the verify log as detail.
DETAIL_KEYS: dict[str, tuple[str, ...]] = {
    "flags": ("flag",),
    "figures": ("surface",),
    "cross_references": ("kind", "value"),
    "concealed": ("claim",),
}

# The keys of one line of notes-verify.jsonl.
LOG_KEYS = frozenset({"doc", "field", "item", "quote", "detail", "outcome", "attempt"})

# The keys a parsed reply must carry: what, and at least one of the four lists.
REPLY_LISTS = QUOTED_FIELDS

# The hard output cap of one note, and the estimate of its cost before the call.
MAX_OUTPUT_TOKENS = 6000

_WHITESPACE = re.compile(r"\s+")
_CURLY = {"“": '"', "”": '"', "‘": "'", "’": "'"}
# A * or _ used as a markdown emphasis mark: a lone * between spaces, and a _ between two word
# characters, are left alone, since those are not emphasis.
_EMPHASIS_STAR = re.compile(r"(?<!\s)\*|\*(?!\s)")
_EMPHASIS_UNDERSCORE = re.compile(r"(?<!\w)_|_(?!\w)")
# The end of a sentence: a full stop, question mark or exclamation mark, then whitespace.
_SENTENCE_END = re.compile(r"(?<=[.?!])\s+")
# How ingest joins the cells of a table row into the row's text.
_CELL_JOIN = " | "

SYSTEM_PROMPT = """You read one document of a diligence data room and write one note about it.

Answer with one JSON object and nothing else, with exactly these keys:

{
 "what": "one sentence saying what this document is",
 "flags": [{"flag": "what is wrong or risky",
            "quote": "the document's own words, verbatim",
            "consequence": "why it matters to the deal"}],
 "figures": [{"surface": "the number exactly as the document writes it",
              "quote": "the document's own words around that number, verbatim"}],
 "cross_references": [{"kind": "code|name|person|document|regulator|ticket",
                       "value": "the thing it names",
                       "quote": "the document's own words carrying it, verbatim"}],
 "concealed": [{"claim": "what the document hedges, omits or softens",
                "quote": "the document's own words, verbatim"}]
}

Use exactly these key names; another name drops the item.

Rules for every quote:
- Copy the document's characters exactly: never a paraphrase, correction, shortening or
  description. A quote that is not verbatim is dropped.
- Start a quote at the first word of its sentence, a leading Notwithstanding, Subject to or
  For the avoidance of doubt included, and carry its verb.
- In a table, a row is written with its cells separated by " | ". Quote one cell's text
  exactly. Do not join cells or restate a row.
- Keep a quote to one sentence or one row, except a clause paragraph: a termination,
  change of control, assignment or exclusivity paragraph of two or three sentences is one
  quote from its first word to its last full stop, as one flag. Never split it or start it
  after its first word.
- Do not invent a quote; if you cannot quote it, leave it out.
- A figure's surface is copied from its own quote, verbatim, from nowhere else.
- Do not add an anchor, page, line or section number; those come later.

A diligence reader is buying this business; quote every one that the document carries:
- a hedge or qualifier weakening a finding, and its sentence
- a conclusion softened, restated or reclassified from something harder
- every warranty, representation or covenant, especially that something has not happened,
  does not exist or is not owed
- an exclusion, carve-out or condition that could deny a claim
- a deadline, notice period or clock, and whether it has run
- a policy, control, limit or standard breached, blocked or exceeded, and why
- every clause that gives a party a right to end, suspend, withhold, accelerate or claim,
  quoted whole from the first word of its paragraph to the last full stop of that
  paragraph; these come before figures and cross references
- a reserve, provision or charge, and its sizing words
- a range of exposure and its ends
- a dated turning point: the week, month or date a number or trend moves
- every sentence that says this deal or event constitutes, triggers or qualifies as a
  defined term, the sentence that applies the definition to the deal before the one that
  expects it
- in a document under a page, every prose line, including a note under its own heading: a
  dependency, single point of failure or system of record above all

Which sentence to quote:
- When your flag, claim or what restates a sentence, quote that one, not a neighbor.
- When a sentence calls a term, condition or exclusion material, decisive or at risk,
  quote it and the clause defining it.
- When a number recurs, quote the first sentence giving it and its purpose, and the later
  formal one.
- When a table carries a total or a range, quote the prose sentence stating it, not the
  rows.

A few pages yield twenty to forty quotes; longer ones yield more, one per clause that binds,
ends or excludes. When unsure, quote it; leave a list empty only when nothing applies."""

USER_PREFIX = "The document, one section per line, in order:\n\n"

REASK_ITEMS = """These items of your reply did not verify. Each line is the field, the reason,
then the quote as you wrote it:

{items}

Return the whole JSON object again, with exactly these keys: what, flags, figures,
cross_references, concealed. Each flag has flag, quote and consequence; each figure has surface
and quote; each cross reference has kind, value and quote; each concealed item has claim and
quote. Fix every item listed above or leave it out, and keep every other item as it was."""

REASK_JSON = (
    "Your reply was not one JSON object with the keys asked for. Answer again with one JSON "
    "object and nothing else, no prose and no code fence, using exactly these key names: what, "
    "flags, figures, cross_references, concealed. Each flag has flag, quote and consequence; "
    "each figure has surface and quote; each cross reference has kind, value and quote; each "
    "concealed item has claim and quote. Do not rename a key."
)


def straighten(text: str) -> str:
    """Collapses whitespace, straightens curly quotes and apostrophes, and drops markdown
    emphasis marks (**, __, backticks, and a * or _ used to emphasize a word). Case is untouched.
    """
    for curly, straight in _CURLY.items():
        text = text.replace(curly, straight)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = _EMPHASIS_STAR.sub("", text)
    text = _EMPHASIS_UNDERSCORE.sub("", text)
    return _WHITESPACE.sub(" ", text).strip()


def locate_quote(quote: str, sections: list[dict]) -> str | None:
    """Returns the anchor of the section a quote starts in, or None when it is not there.

    The sections are one document's records in ordinal order. The quote is looked for in each
    section first, then across each adjacent pair joined by one space. The first match in
    ordinal order wins.
    """
    needle = straighten(quote)
    if not needle:
        return None
    straightened = [(section["anchor"], straighten(section["text"])) for section in sections]
    for anchor, text in straightened:
        if needle in text:
            return anchor
    for (anchor, text), (_, following) in zip(straightened, straightened[1:]):
        if needle in f"{text} {following}":
            return anchor
    return None


def section_units(section: dict) -> list[str]:
    """The units of one section, each with its whitespace collapsed.

    A table row is one unit per cell, so a figure quotes the cell and not the whole row. Every
    other section is one unit per sentence, split after a full stop, question mark or exclamation
    mark followed by whitespace, so a sentence that runs over the page's line ends is one unit.
    """
    if section.get("cells") is not None:
        pieces = [straighten(str(cell["value"])) for cell in section["cells"]]
    elif section.get("kind") == "row":
        pieces = straighten(section["text"]).split(_CELL_JOIN)
    else:
        pieces = _SENTENCE_END.split(straighten(section["text"]))
    return [unit for unit in (piece.strip() for piece in pieces) if unit]


def amount_surfaces(unit: str) -> list[str]:
    """Every currency amount and percentage a unit writes, as the unit writes it.

    A number with no dollar sign and no percent sign is a plain count or magnitude and is left
    to the model. A percentage the unit puts in brackets is read without its opening bracket,
    since the match ends at the percent sign and the closing bracket is outside it.
    """
    found: list[str] = []
    for match in AMOUNT.finditer(unit):
        if not (match.group("currency") or match.group("percent")):
            continue
        surface = match.group(0).strip()
        if surface.startswith("(") and ")" not in surface:
            surface = surface[1:].strip()
        if surface:
            found.append(surface)
    return found


def harvest_figures(sections: list[dict]) -> list[dict]:
    """Every unit of one document carrying an amount, as figure items in document order.

    A unit with two amounts gives two items sharing one quote. The anchor is the anchor of the
    section the unit was read from.
    """
    return [
        {"surface": surface, "quote": unit, "anchor": section["anchor"]}
        for section in sections
        for unit in section_units(section)
        for surface in amount_surfaces(unit)
    ]


def note_name(doc_id: str) -> str:
    """The file name of one document's note."""
    return doc_id.replace("/", "__") + ".json"


def document_text(sections: list[dict]) -> str:
    """The document as the model sees it: section text in ordinal order, one per line."""
    return "\n".join(section["text"] for section in sections)


def build_messages(sections: list[dict]) -> list[dict]:
    """The two messages of one note call: the task and schema, then the document."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PREFIX + document_text(sections)},
    ]


def parse_reply(text: str) -> dict | None:
    """Reads the model's reply as one JSON object, stripping a code fence. None when it fails."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        stripped = stripped.rstrip()
        if stripped.endswith("```"):
            stripped = stripped[: -len("```")]
    try:
        data = json.loads(stripped)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _log_record(
    doc: str,
    field: str | None,
    item: int | None,
    quote: str | None,
    outcome: str,
    attempt: int,
    detail: str | None = None,
) -> dict:
    return {
        "doc": doc,
        "field": field,
        "item": item,
        "quote": quote,
        "detail": detail,
        "outcome": outcome,
        "attempt": attempt,
    }


def item_detail(field: str, item: object) -> str | None:
    """Names one item inside its field: the flag, the surface, kind and value, or the claim.

    None when the item is not an object or one of the naming keys is missing or not a string.
    """
    if not isinstance(item, dict):
        return None
    values = [item.get(key) for key in DETAIL_KEYS[field]]
    if not all(isinstance(value, str) for value in values):
        return None
    return ": ".join(values)


def well_shaped(reply: dict) -> bool:
    """Says whether a parsed reply carries what as a non-empty string and one of the four lists."""
    what = reply.get("what")
    if not isinstance(what, str) or not what.strip():
        return False
    return any(isinstance(reply.get(field), list) for field in REPLY_LISTS)


def _item_reason(field: str, item: object, sections: list[dict]) -> str | None:
    """Why one item of a quoted field does not verify, or None when it does."""
    if not isinstance(item, dict):
        return "missing key quote"
    for key in FIELD_KEYS[field]:
        if not isinstance(item.get(key), str):
            return f"missing key {key}"
    if locate_quote(item["quote"], sections) is None:
        return "quote not found verbatim"
    if field == "figures" and straighten(item["surface"]) not in straighten(item["quote"]):
        return "surface not inside the quote"
    if field == "cross_references" and item["kind"] not in CROSS_REFERENCE_KINDS:
        return "kind not one of " + ", ".join(sorted(CROSS_REFERENCE_KINDS))
    return None


def verify_items(
    doc: str, field: str, items: object, sections: list[dict], keep_anchor: bool = False
) -> tuple[list[dict], list[dict]]:
    """Verifies one quoted field, returning the items that pass and one record per drop.

    An item fails when it does not carry every required key of its field as a string, when its
    quote does not locate in the document, when a figure's surface is not inside its quote, or
    when a cross reference's kind is not one of the six. Each failure record carries the item's
    detail and the reason it failed; the reason is for the re-ask and is not logged. Two items
    that match on every key are kept once. The item index in a record is the model's own 0-based
    position.

    With keep_anchor the item's own anchor is kept instead of the one code locates. The harvest
    passes it, because a unit already names the section it was read from, while a short cell such
    as $0 reads verbatim in an earlier row too.
    """
    kept: list[dict] = []
    dropped: list[dict] = []
    seen: set[tuple[str, ...]] = set()
    if not isinstance(items, list):
        return kept, dropped
    for index, item in enumerate(items):
        quote = item.get("quote") if isinstance(item, dict) else None
        quote = quote if isinstance(quote, str) else None
        reason = _item_reason(field, item, sections)
        if reason is not None:
            record = _log_record(doc, field, index, quote, "dropped", 1, item_detail(field, item))
            dropped.append(dict(record, reason=reason))
            continue
        built = {key: item[key] for key in FIELD_KEYS[field]}
        signature = tuple(built[key] for key in FIELD_KEYS[field])
        if signature in seen:
            continue
        seen.add(signature)
        own = item.get("anchor") if keep_anchor else None
        built["anchor"] = own if isinstance(own, str) else locate_quote(built["quote"], sections)
        kept.append(built)
    return kept, dropped


def build_note(doc: str, model: str, pass_name: str, reply: dict, sections: list[dict], usage: dict) -> tuple[dict, list[dict]]:
    """Builds one verified note from a parsed reply, with one log record per dropped item."""
    what = reply.get("what")
    note = {
        "doc": doc,
        "model": model,
        "pass": pass_name,
        "what": what if isinstance(what, str) else "",
        "usage": usage,
    }
    dropped: list[dict] = []
    for field in QUOTED_FIELDS:
        kept, failures = verify_items(doc, field, reply.get(field), sections)
        note[field] = kept
        dropped.extend(failures)
    return note, dropped


def write_note(out_dir: Path, doc_id: str, note: dict) -> Path:
    """Writes one note with sorted keys and one trailing newline."""
    notes_dir = out_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    path = notes_dir / note_name(doc_id)
    path.write_text(json.dumps(note, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_raw(out_dir: Path, doc_id: str, attempt: int, text: str) -> Path:
    """Writes one reply's text verbatim under notes-raw, named by document and attempt."""
    raw_dir = out_dir / "notes-raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    stem = note_name(doc_id)[: -len(".json")]
    path = raw_dir / f"{stem}.{attempt}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def _log_order(record: dict) -> tuple[str, str, int, int]:
    return (
        record["doc"],
        record["field"] or "",
        record["item"] if record["item"] is not None else -1,
        record["attempt"],
    )


def write_verify_log(out_dir: Path, records: list[dict], replacing: set[str]) -> Path:
    """Rewrites notes-verify.jsonl, replacing the records of the documents just processed.

    The file is written even when it is empty, sorted by document, field, item then attempt.
    """
    path = out_dir / "notes-verify.jsonl"
    kept = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            existing = json.loads(line)
            if existing["doc"] not in replacing:
                kept.append(existing)
    kept.extend(records)
    kept.sort(key=_log_order)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n" for record in kept)
    path.write_text(body, encoding="utf-8")
    return path


def read_sections(run_dir: Path) -> dict[str, list[dict]]:
    """Reads sections.jsonl into one list per document, each in ordinal order."""
    by_doc: dict[str, list[dict]] = {}
    for line in (run_dir / "sections.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        by_doc.setdefault(record["doc"], []).append(record)
    for records in by_doc.values():
        records.sort(key=lambda record: record["ordinal"])
    return by_doc


def reask_messages(messages: list[dict], first_text: str, asking: str) -> list[dict]:
    """The messages of a second call: the first call, its reply, and what to do again."""
    return [
        *messages,
        {"role": "assistant", "content": first_text},
        {"role": "user", "content": asking},
    ]


def failed_items(records: list[dict]) -> str:
    """The failed items of one document, one line each: the field, the reason, then the quote."""
    return "\n".join(
        f'- {record["field"]}: {record["reason"]}: "{record["quote"] or ""}"' for record in records
    )


def log_record(record: dict) -> dict:
    """One line of notes-verify.jsonl: a failure record without the reason the re-ask carries."""
    return {key: value for key, value in record.items() if key in LOG_KEYS}


def call_usage(model: str, completions: list[Completion]) -> dict:
    """Sums one document's calls into the note's usage block."""
    tokens_in = sum(completion.tokens_in for completion in completions)
    tokens_out = sum(completion.tokens_out for completion in completions)
    return {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "dollars": price(model, tokens_in, tokens_out),
        "seconds": sum(completion.seconds for completion in completions),
        "calls": len(completions),
    }


def merge_items(first: list[dict], second: list[dict]) -> list[dict]:
    """The union of one field's verified items from two attempts, the first attempt's in front.

    An item of the second attempt that matches an item already kept on every key is left out.
    """
    merged = list(first)
    seen = {tuple(sorted(item.items())) for item in merged}
    for item in second:
        signature = tuple(sorted(item.items()))
        if signature in seen:
            continue
        seen.add(signature)
        merged.append(item)
    return merged


def add_harvest(doc: str, note: dict, sections: list[dict]) -> list[dict]:
    """Adds every unit of the document carrying an amount to the note's figures.

    The harvested items are verified the way a model item is and follow the model's own items in
    document order. One that matches a model figure on surface, quote and anchor is left out.
    Returns one log record per harvested item that did not verify, dropped at attempt 1; in
    practice there are none, since a unit is a substring of its own section.
    """
    kept, dropped = verify_items(doc, "figures", harvest_figures(sections), sections, keep_anchor=True)
    note["figures"] = merge_items(note["figures"], kept)
    return [log_record(record) for record in dropped]


def note_document(doc: str, model: str, pass_name: str, sections: list[dict], call) -> tuple[dict | None, list[dict]]:
    """Notes one document from the model, then harvests the figures the model did not write."""
    note, records = model_note(doc, model, pass_name, sections, call)
    if note is None:
        return None, records
    return note, records + add_harvest(doc, note, sections)


def model_note(doc: str, model: str, pass_name: str, sections: list[dict], call) -> tuple[dict | None, list[dict]]:
    """Notes one document from the model alone, asking again once when the reply or an item fails.

    call sends one list of messages and returns its Completion. The note is None when it is
    dropped whole. usage is left to the caller.

    The note's items are the union, per field, of the items that verify on the first reply and
    the items that verify on the second: the first reply's in the order it wrote them, then the
    second reply's new ones in the order it wrote them, an item that matches one already kept on
    every key left out. A second reply that answers with fewer items than the first therefore
    loses nothing. The note's what is the first reply's. When the second reply does not parse or
    is not well shaped the note is the first reply's verified items alone.

    The records are this document's lines of the verify log: an item that failed on the first
    call is re-asked; an item of the second reply that fails is dropped at attempt 2, and when
    the second reply does not parse the first call's failures are what is dropped at attempt 2.
    A reply that twice fails to parse or to carry the keys asked for is one note-dropped record.
    """
    messages = build_messages(sections)
    first = call(messages)
    parsed = parse_reply(first.text)

    if parsed is None or not well_shaped(parsed):
        second = call(reask_messages(messages, first.text, REASK_JSON))
        parsed = parse_reply(second.text)
        if parsed is None or not well_shaped(parsed):
            return None, [_log_record(doc, None, None, None, "note-dropped", 2)]
        note, failures = build_note(doc, model, pass_name, parsed, sections, {})
        return note, [log_record(dict(record, outcome="dropped", attempt=2)) for record in failures]

    note, failures = build_note(doc, model, pass_name, parsed, sections, {})
    if not failures:
        return note, []

    records = [log_record(dict(record, outcome="re-asked", attempt=1)) for record in failures]
    asking = REASK_ITEMS.format(items=failed_items(failures))
    second = call(reask_messages(messages, first.text, asking))
    answered = parse_reply(second.text)
    if answered is None or not well_shaped(answered):
        records.extend(log_record(dict(record, outcome="dropped", attempt=2)) for record in failures)
        return note, records
    second_note, again = build_note(doc, model, pass_name, answered, sections, {})
    for field in QUOTED_FIELDS:
        note[field] = merge_items(note[field], second_note[field])
    records.extend(log_record(dict(record, outcome="dropped", attempt=2)) for record in again)
    return note, records


def note_and_write(
    doc_id: str,
    doc: str,
    sections: list[dict],
    model: str,
    pass_name: str,
    out_dir: Path,
    gateway: Gateway,
    batch: Batch,
) -> tuple[str, dict | None, list[dict]]:
    """Notes one document, prices its calls, keeps each reply and writes the note.

    Runs in one pool thread. Every reply text is written to notes-raw before it is read, so a
    pass can be tuned from what the model actually said. A call that raises drops this document
    whole so the pool and the batch finish: the exception is caught, printed, and logged as
    note-dropped at attempt 1. A reply that never parses is not an exception; it is also printed
    and logged, so nothing here is silent.
    """
    completions: list[Completion] = []

    def call(messages: list[dict]) -> Completion:
        completion = gateway.complete(model, messages, max_tokens=MAX_OUTPUT_TOKENS)
        batch.record(completion)
        completions.append(completion)
        write_raw(out_dir, doc_id, len(completions), completion.text)
        return completion

    try:
        note, records = note_document(doc, model, pass_name, sections, call)
    except Exception as exc:
        print(f"{doc_id}: note dropped, {type(exc).__name__}: {exc}")
        return doc_id, None, [_log_record(doc, None, None, None, "note-dropped", 1)]

    if note is None:
        print(f"{doc_id}: note dropped, the reply did not parse")
    else:
        note["usage"] = call_usage(model, completions)
        write_note(out_dir, doc_id, note)
    return doc_id, note, records


def read_note(out_dir: Path, doc_id: str) -> dict | None:
    """Reads one document's note from disk, or None when it has not been written there."""
    path = out_dir / "notes" / note_name(doc_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def notes_on_disk(out_dir: Path) -> list[dict]:
    """Every note under out_dir/notes, parsed, in no particular order."""
    return [json.loads(path.read_text(encoding="utf-8")) for path in (out_dir / "notes").glob("*.json")]


def counts_from_disk(out_dir: Path, documents: int) -> dict:
    """documents, noted, dropped and verified, counted from the notes actually on disk.

    noted is the number of note files; dropped is documents minus noted; verified is the sum,
    over every note on disk, of its kept quoted items.
    """
    notes = notes_on_disk(out_dir)
    noted = len(notes)
    verified = sum(len(note[field]) for note in notes for field in QUOTED_FIELDS)
    return {"documents": documents, "noted": noted, "dropped": documents - noted, "verified": verified}


def verify_counts_from_disk(out_dir: Path) -> dict:
    """re_asked and dropped_items, counted from the merged notes-verify.jsonl on disk."""
    path = out_dir / "notes-verify.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "re_asked": sum(1 for record in records if record["outcome"] == "re-asked"),
        "dropped_items": sum(1 for record in records if record["outcome"] == "dropped"),
    }


def write_summary(out_dir: Path, summary: dict) -> Path:
    """Writes notes-summary.json with sorted keys and one trailing newline."""
    path = out_dir / "notes-summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def summary_line(summary: dict) -> str:
    """The one line a pass prints when it ends."""
    return (
        f"pass {summary['pass']} on {summary['sample']}: documents {summary['documents']}, "
        f"noted {summary['noted']}, notes dropped {summary['dropped']}, "
        f"quotes verified {summary['verified']}, quotes re-asked {summary['re_asked']}, "
        f"quotes dropped {summary['dropped_items']}, {summary['tokens_in']} tokens in, "
        f"{summary['tokens_out']} tokens out, ${summary['dollars']:.4f}, "
        f"{summary['seconds']:.1f} seconds"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Reads the command line of one note run."""
    parser = argparse.ArgumentParser(prog="python -m rlm.notes")
    parser.add_argument("sample_dir")
    parser.add_argument("run_dir")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        help="a document id or its path in the sample, repeatable; without it every document "
        "is noted",
    )
    parser.add_argument("--pass", dest="pass_name", default="a", choices=["a", "b"])
    parser.add_argument("--out", default=None)
    return parser.parse_args(argv)


def main(argv: list[str], gateway: Gateway | None = None, ledger: Ledger | None = None) -> int:
    """Notes the chosen documents of one sample and writes the notes, the log and the summary.

    Without --only the summary is written from this call alone. With --only it is merged into
    whatever is on disk: the counts are read back from the notes and the verify log after this
    call writes them, and the token totals fold this call's usage into the previous summary's,
    minus the usage the replaced documents carried before.
    """
    args = parse_args(argv)
    sample_dir = Path(args.sample_dir)
    run_dir = Path(args.run_dir)
    out_dir = Path(args.out) if args.out else run_dir

    key = load_key(sample_dir)
    ids_by_path = {path: doc_id for doc_id, path in key.documents.items()}
    if not args.only:
        chosen = list(key.documents.items())
    else:
        wanted = set()
        for only in args.only:
            if only in key.documents:
                wanted.add(only)
            elif only in ids_by_path:
                wanted.add(ids_by_path[only])
            else:
                print(f"no such document in the key: {only}")
                return 2
        chosen = [(doc_id, doc) for doc_id, doc in key.documents.items() if doc_id in wanted]

    sections_by_doc = read_sections(run_dir)
    prompts = [(doc_id, doc) for doc_id, doc in chosen if sections_by_doc.get(doc)]
    missing = [(doc_id, doc) for doc_id, doc in chosen if not sections_by_doc.get(doc)]

    if gateway is None:
        gateway = Gateway()
    if ledger is None:
        ledger = Ledger(Path(__file__).resolve().parents[2] / "LEDGER.md")

    estimated_in = sum(
        estimate_tokens("\n".join(message["content"] for message in build_messages(sections_by_doc[doc])))
        for _, doc in prompts
    )
    estimated_out = MAX_OUTPUT_TOKENS * len(prompts)

    # A partial pass merges into what a prior pass wrote, so the usage of the documents this
    # call is about to replace is read before note_and_write overwrites their note files.
    previous_summary = None
    replaced_tokens_in = replaced_tokens_out = 0
    if args.only:
        summary_path = out_dir / "notes-summary.json"
        if summary_path.exists():
            previous_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        for doc_id, _ in prompts:
            old_note = read_note(out_dir, doc_id)
            if old_note is not None:
                usage = old_note["usage"]
                replaced_tokens_in += usage.get("tokens_in", 0)
                replaced_tokens_out += usage.get("tokens_out", 0)

    records = [_log_record(doc, None, None, None, "note-dropped", 1) for _, doc in missing]
    for doc_id, _ in missing:
        print(f"{doc_id}: note dropped, the document has no sections")

    started = time.monotonic()
    with ledger.batch(
        sample_dir.name, PHASE, args.model, tokens_in=estimated_in, tokens_out=estimated_out
    ) as batch:
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = [
                pool.submit(
                    note_and_write,
                    doc_id,
                    doc,
                    sections_by_doc[doc],
                    args.model,
                    args.pass_name,
                    out_dir,
                    gateway,
                    batch,
                )
                for doc_id, doc in prompts
            ]
            results = [future.result() for future in futures]
    seconds = time.monotonic() - started

    noted = 0
    dropped = len(missing)
    verified = 0
    for doc_id, note, doc_records in results:
        records.extend(doc_records)
        if note is None:
            dropped += 1
            continue
        noted += 1
        kept = sum(len(note[field]) for field in QUOTED_FIELDS)
        verified += kept
        failed = sum(1 for record in doc_records if record["outcome"] == "dropped")
        print(f"{doc_id}: {kept} items kept, {failed} dropped")

    write_verify_log(out_dir, records, {doc for _, doc in chosen})

    if args.only:
        # documents, noted, dropped and verified come from what is on disk now, not from the
        # documents this call asked, the way write_verify_log merges into the log on disk
        # rather than replacing it. tokens_in and tokens_out fold this call's usage into the
        # previous summary's totals, minus the usage of the documents just replaced; with no
        # previous summary there is nothing to fold into, so this call's own totals stand.
        disk_counts = counts_from_disk(out_dir, len(key.documents))
        verify_counts = verify_counts_from_disk(out_dir)
        if previous_summary is None:
            tokens_in, tokens_out = batch.tokens_in, batch.tokens_out
        else:
            tokens_in = previous_summary["tokens_in"] - replaced_tokens_in + batch.tokens_in
            tokens_out = previous_summary["tokens_out"] - replaced_tokens_out + batch.tokens_out
        summary = {
            "documents": disk_counts["documents"],
            "noted": disk_counts["noted"],
            "dropped": disk_counts["dropped"],
            "verified": disk_counts["verified"],
            "re_asked": verify_counts["re_asked"],
            "dropped_items": verify_counts["dropped_items"],
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "dollars": price(args.model, tokens_in, tokens_out),
            "seconds": seconds,
            "model": args.model,
            "pass": args.pass_name,
            "sample": sample_dir.name,
        }
    else:
        summary = {
            "documents": len(chosen),
            "noted": noted,
            "dropped": dropped,
            "verified": verified,
            "re_asked": sum(1 for record in records if record["outcome"] == "re-asked"),
            "dropped_items": sum(1 for record in records if record["outcome"] == "dropped"),
            "tokens_in": batch.tokens_in,
            "tokens_out": batch.tokens_out,
            "dollars": price(args.model, batch.tokens_in, batch.tokens_out),
            "seconds": seconds,
            "model": args.model,
            "pass": args.pass_name,
            "sample": sample_dir.name,
        }
    write_summary(out_dir, summary)
    print(summary_line(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
