"""Writes one note per document from one gateway call, verified and anchored by code.

The model sees the document's section text in ordinal order and nothing else: no anchors, no
key, no other document. It answers with one JSON object holding what the document is, its
flags, its figures, its cross references and what it conceals, quoting the document verbatim.

Code then verifies every quote against the document's own sections. A quote passes when its
text, with whitespace collapsed and curly quotes and apostrophes straightened, is a substring
of one section's text treated the same way, or of two adjacent sections joined by one space.
Case is not folded. The anchor written into the note is the anchor of the section where the
quote starts, and the model's own anchor, if it writes one, is discarded. A figure passes when
its quote passes and its surface string is inside that quote.

A document whose items fail is asked again once, with its first reply and the list of quotes
that were not found, and the second reply becomes the note. What fails again is dropped from
the note and written to notes-verify.jsonl. A reply that is not one JSON object is asked again
the same way, and a second reply that does not parse drops the note whole. There is no third
call. A document the key names but sections.jsonl does not carry is dropped without a call.

The documents run eight at a time inside one ledger batch, so a pass is one line of LEDGER.md
and one runs/<sample>/notes-summary.json.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
import time
from pathlib import Path

from rlm.gateway import Batch, Completion, Gateway, Ledger, estimate_tokens, price
from rlm.key import load_key

PHASE = 2

# Documents in flight at once, as the winning run's leaf did.
WORKERS = 8

NOTE_KEYS = frozenset(
    {"doc", "model", "pass", "what", "flags", "figures", "cross_references", "concealed", "usage"}
)

# The four fields whose items carry a quote and get an anchor.
QUOTED_FIELDS = ("flags", "figures", "cross_references", "concealed")

CROSS_REFERENCE_KINDS = frozenset({"code", "name", "person", "document", "regulator", "ticket"})

# The keys code keeps from each item of a quoted field, beside the anchor it writes.
FIELD_KEYS: dict[str, tuple[str, ...]] = {
    "flags": ("flag", "quote", "consequence"),
    "figures": ("surface", "quote"),
    "cross_references": ("kind", "value", "quote"),
    "concealed": ("claim", "quote"),
}

# The hard output cap of one note, and the estimate of its cost before the call.
MAX_OUTPUT_TOKENS = 6000

_WHITESPACE = re.compile(r"\s+")
_CURLY = {"“": '"', "”": '"', "‘": "'", "’": "'"}

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
                       "value": "the code, name, person, document, regulator or ticket",
                       "quote": "the document's own words carrying it, verbatim"}],
 "concealed": [{"claim": "what the document hedges, omits or softens",
                "quote": "the document's own words, verbatim"}]
}

Rules for every quote:
- Copy the document's characters exactly. Do not paraphrase, correct, shorten inside, or
  reword. A quote that is not verbatim is dropped.
- Keep a quote short: enough words to find it and to carry the point, no more.
- Do not invent a quote. If you cannot quote it, leave the item out.
- A figure's surface string must appear inside its own quote.
- Do not write an anchor, a page, a line or a section number. Those are added later.

A diligence reader is buying this business and needs what the document says against it.
Quote every one of these that the document carries:
- a hedge or a qualifier that weakens a finding, and the sentence that carries it
- a conclusion that is softened, restated or reclassified from something harder
- a warranty, a representation or a covenant, in the words that bind it
- an exclusion, a carve-out or a condition that could deny a claim
- a deadline, a notice period or a clock, and whether it has run
- a policy, a control, a limit or a standard that is breached, blocked or exceeded
- a right to terminate, suspend, withhold or accelerate
- a reserve, a provision or a charge, and the words that size it
- a range of exposure and both of its ends
- a dated turning point: the week, month or date on which a number or a trend moves

Prefer the sentence the document wrote over any summary of it. Many short verbatim quotes are
better than a few long ones. Leave a list empty when the document gives you nothing for it."""

USER_PREFIX = "The document, one section per line, in order:\n\n"

REASK_ITEMS = """These quotes are not in the document as you wrote them:

{quotes}

Return the whole JSON object again, with the same keys. For each quote above, either copy the
document's characters exactly or leave that item out. Keep every other item as it was."""

REASK_JSON = (
    "Your reply was not one JSON object. Answer again with one JSON object and nothing else: "
    "no prose, no code fence, no explanation."
)


def straighten(text: str) -> str:
    """Collapses whitespace and straightens curly quotes and apostrophes. Case is untouched."""
    for curly, straight in _CURLY.items():
        text = text.replace(curly, straight)
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


def _log_record(doc: str, field: str | None, item: int | None, quote: str | None, outcome: str, attempt: int) -> dict:
    return {"doc": doc, "field": field, "item": item, "quote": quote, "outcome": outcome, "attempt": attempt}


def verify_items(doc: str, field: str, items: object, sections: list[dict]) -> tuple[list[dict], list[dict]]:
    """Verifies one quoted field, returning the items that pass and one record per drop.

    An item whose quote does not locate is dropped, as is a figure whose surface is not inside
    its quote and a cross reference of an unknown kind. The item index in a record is the
    model's own 0-based position.
    """
    kept: list[dict] = []
    dropped: list[dict] = []
    if not isinstance(items, list):
        return kept, dropped
    for index, item in enumerate(items):
        quote = item.get("quote") if isinstance(item, dict) else None
        quote = quote if isinstance(quote, str) else None
        anchor = locate_quote(quote, sections) if quote else None
        if anchor is None:
            dropped.append(_log_record(doc, field, index, quote, "dropped", 1))
            continue
        built = {key: item.get(key, "") for key in FIELD_KEYS[field]}
        if field == "figures" and straighten(str(built["surface"])) not in straighten(quote):
            dropped.append(_log_record(doc, field, index, quote, "dropped", 1))
            continue
        if field == "cross_references" and built["kind"] not in CROSS_REFERENCE_KINDS:
            dropped.append(_log_record(doc, field, index, quote, "dropped", 1))
            continue
        built["anchor"] = anchor
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


def failed_quotes(records: list[dict]) -> str:
    """The failed quotes of one document, one per line, as the re-ask lists them."""
    return "\n".join(f'- "{record["quote"] or ""}"' for record in records)


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


def note_document(doc: str, model: str, pass_name: str, sections: list[dict], call) -> tuple[dict | None, list[dict]]:
    """Notes one document, asking again once when the reply or one of its items fails.

    call sends one list of messages and returns its Completion. The note is None when it is
    dropped whole. The records are this document's lines of the verify log: an item that failed
    on the first call is re-asked, an item that fails on the second is dropped, and a reply that
    does not parse twice is one note-dropped record. usage is left to the caller.
    """
    messages = build_messages(sections)
    first = call(messages)
    parsed = parse_reply(first.text)

    if parsed is None:
        second = call(reask_messages(messages, first.text, REASK_JSON))
        parsed = parse_reply(second.text)
        if parsed is None:
            return None, [_log_record(doc, None, None, None, "note-dropped", 2)]
        note, failures = build_note(doc, model, pass_name, parsed, sections, {})
        return note, [dict(record, outcome="dropped", attempt=2) for record in failures]

    note, failures = build_note(doc, model, pass_name, parsed, sections, {})
    if not failures:
        return note, []

    records = [dict(record, outcome="re-asked", attempt=1) for record in failures]
    asking = REASK_ITEMS.format(quotes=failed_quotes(failures))
    second = call(reask_messages(messages, first.text, asking))
    answered = parse_reply(second.text)
    if answered is None:
        records.extend(dict(record, outcome="dropped", attempt=2) for record in failures)
        return note, records
    note, again = build_note(doc, model, pass_name, answered, sections, {})
    records.extend(dict(record, outcome="dropped", attempt=2) for record in again)
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
    """Notes one document, prices its calls and writes the note. Runs in one pool thread.

    A call that raises drops this document whole so the pool and the batch finish: the
    exception is caught, printed, and logged as note-dropped at attempt 1. A reply that never
    parses is not an exception; it is also printed and logged, so nothing here is silent.
    """
    completions: list[Completion] = []

    def call(messages: list[dict]) -> Completion:
        completion = gateway.complete(model, messages, max_tokens=MAX_OUTPUT_TOKENS)
        batch.record(completion)
        completions.append(completion)
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
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--only",
        default=None,
        help="a document id or its path in the sample; without it every document is noted",
    )
    parser.add_argument("--pass", dest="pass_name", default="a", choices=["a", "b"])
    parser.add_argument("--out", default=None)
    return parser.parse_args(argv)


def main(argv: list[str], gateway: Gateway | None = None, ledger: Ledger | None = None) -> int:
    """Notes the chosen documents of one sample and writes the notes, the log and the summary."""
    args = parse_args(argv)
    sample_dir = Path(args.sample_dir)
    run_dir = Path(args.run_dir)
    out_dir = Path(args.out) if args.out else run_dir

    key = load_key(sample_dir)
    ids_by_path = {path: doc_id for doc_id, path in key.documents.items()}
    if args.only is None:
        chosen = list(key.documents.items())
    elif args.only in key.documents:
        chosen = [(args.only, key.documents[args.only])]
    elif args.only in ids_by_path:
        chosen = [(ids_by_path[args.only], args.only)]
    else:
        print(f"no such document in the key: {args.only}")
        return 2

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
