"""Chooses what the report reads by models, level by level, each seeing everything below it.

The leaves are the notes, one per document. The middle level splits the room's documents, in
the room's own order, into groups whose notes fit one call: a group's budget is the model's
context window, CONTEXT_WINDOWS, times MARGIN, less the instructions and the reply's
MAX_OUTPUT_TOKENS. A document whose note alone passes the budget is a group of its own.

One call per group to DEFAULT_MODEL. The call is told it is the buy-side diligence lead
reviewing these documents for an acquisition of the company, and is given the room's brief
(its own brief.md, else the package's) and the acquisition checklist as a reminder of what a
buyer looks for. It returns at most group_cap findings, ranked, each with the document's id,
the finding in one or two sentences and the quote copied from that document's note.

check_findings keeps a finding whose document is in the group and whose quote, whitespace
collapsed, stands inside one of that document's flag or figure quotes, and takes the anchor of
the first that holds it; every other finding is dropped with its reason. The kept findings past
the group's cap are dropped too. A group whose reply is unreadable, or keeps nothing, is asked
once more, with its first reply and what was wrong with it; a group is never asked a third time.

tree.json holds the model, the budget, the cap and every group: its documents, its tokens, its
calls, every finding it returned, the ones kept and the ones dropped.

tree_digest writes what the writer reads in place of the dossier digest: the kept findings
grouped by document in the room's order, a row being `- <finding> | <doc> | <quote> |
<anchor>`. The verifier reads the same text as its dossier. tree_evidence writes the schedule
of the kept findings' own quotes under the report.

Money: the group calls are one batch of the ledger it is handed, so the estimate is printed
before anything is sent, the phase cap and the ceiling refuse, and one LEDGER.md row is booked.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from rlm.gateway import PHASE_CAPS, Completion, Gateway, Ledger, NoReply, estimate_tokens
from rlm.key import room_documents
from rlm.notes import reask_messages
from rlm.pick import CHECKLIST, _ITEM, clean, digest_rows, field, flags_of, read_notes, schedule_field, titles
from rlm.write import DIGEST_ROWS, brief_path

PHASE = 8

DEFAULT_MODEL = "z-ai/glm-5.3-flash"

# The context window of each model a group call may use, in tokens, as the gateway's model
# list gave it on 2026-10-05.
CONTEXT_WINDOWS = {"z-ai/glm-5.3-flash": 1_048_575}

# The share of the context window a group call is allowed to fill by the repository's estimate
# of four characters a token. Contract text with numbers and defined terms runs nearer three
# characters a token, so a call at the full estimate could pass the window.
MARGIN = 0.6

# The reply of one group: up to DIGEST_ROWS findings of a few sentences each, and the reasoning
# the GLM endpoints spend before they answer.
MAX_OUTPUT_TOKENS = 32000

# The groups called at once.
WORKERS = 4

TREE_FILE = "tree.json"

TREE_PROMPT = """You are the buy-side diligence lead. You are reviewing these documents of a data
room for an acquisition of the company. The brief below is what the deal committee asked for,
and the checklist after it is a reminder of what a buyer looks for in a contract.

The next message holds {count} documents of the room. Each begins with a line `id: <doc>`, then
what the document is, then the risks a reader flagged in it, each with its quote, its
consequence and what it is about, then its figures, each with its quote.

Return the findings from these documents that a deal committee must see, at most {cap}, the one
that matters most first. Each finding is one document's: its id copied character for character
from its `id: ` line, the finding in one or two sentences with its numbers and names, and the
quote copied character for character from that document's note, the quote of one of its flags
or figures or a part of one.

Answer with one JSON object and nothing else:

{{"findings": [{{"doc": "<id>", "finding": "<one or two sentences>", "quote": "<words copied from the note>"}}]}}

THE BRIEF

{brief}

THE CHECKLIST

{checklist}
"""

REASK = """None of the findings of your reply could be used: {reason}. Each finding needs the
id of a document of this message, copied from its `id: ` line, and a quote copied character for
character from that document's note. Answer again with the one JSON object, at most {cap}
findings."""


def checklist_text() -> str:
    """The checklist's headings and questions, one question a line."""
    lines = []
    for line in CHECKLIST.read_text(encoding="utf-8").splitlines():
        match = _ITEM.match(line.strip())
        if match:
            lines.append(f"- {match.group(3).strip()}")
        elif line.startswith("## "):
            lines += ["", line[3:].strip()]
    return "\n".join(lines).strip()


def instructions(room: Path, count: int, cap: int) -> str:
    """The system message of one group call."""
    brief = brief_path(room).read_text(encoding="utf-8").strip()
    return TREE_PROMPT.format(count=count, cap=cap, brief=brief, checklist=checklist_text())


def note_block(doc: str, note: dict | None) -> str:
    """One document as a group call carries it: its id, what it is, its flags and its figures."""
    note = note or {}
    lines = [f"id: {doc}", f"what: {clean(note.get('what'))}"]
    for flag in flags_of(note):
        lines.append(f"flag: {clean(flag.get('flag'))}")
        lines.append(f"quote: {clean(flag.get('quote'))}")
        lines.append(f"consequence: {clean(flag.get('consequence'))}")
        about = "; ".join(clean(item) for item in flag.get("about") or [])
        if about:
            lines.append(f"about: {about}")
    for figure in note.get("figures") or []:
        lines.append(f"figure: {clean(figure.get('surface'))}")
        lines.append(f"quote: {clean(figure.get('quote'))}")
    return "\n".join(lines)


def group_budget(model: str, system: str) -> int:
    """The note tokens one group call may carry: MARGIN of the model's window, less the
    instructions and the reply."""
    return int(CONTEXT_WINDOWS[model] * MARGIN) - estimate_tokens(system) - MAX_OUTPUT_TOKENS


def make_groups(sizes: dict[str, int], budget: int) -> list[list[str]]:
    """The documents in their order, cut into consecutive groups whose sizes sum within budget.

    A document past the budget alone is a group of its own.
    """
    groups: list[list[str]] = []
    current: list[str] = []
    used = 0
    for doc, size in sizes.items():
        if current and used + size > budget:
            groups.append(current)
            current, used = [], 0
        current.append(doc)
        used += size
    if current:
        groups.append(current)
    return groups


def group_cap(count: int) -> int:
    """The findings one group keeps: the digest's rows shared over the groups, rounded up."""
    return math.ceil(DIGEST_ROWS / count)


def collapse(text: object) -> str:
    """Text with every run of whitespace one space and no quotation marks around it."""
    return " ".join(str(text or "").split()).strip("\"'“”‘’ ")


def check_findings(findings: list, docs: list[str], notes: dict[str, dict | None]) -> tuple[list[dict], list[dict]]:
    """The findings whose quote stands in their own document's note, each with the anchor of the
    flag or figure that holds it, and the rest, each with the reason it was dropped."""
    kept: list[dict] = []
    dropped: list[dict] = []
    members = set(docs)
    for item in findings:
        if not isinstance(item, dict):
            dropped.append({"finding": item, "reason": "not a finding"})
            continue
        doc = str(item.get("doc") or "").strip()
        quote = collapse(item.get("quote"))
        found = {"doc": doc, "finding": clean(item.get("finding")), "quote": clean(item.get("quote"))}
        if doc not in members:
            dropped.append({**found, "reason": "no such document in the group"})
            continue
        if not quote:
            dropped.append({**found, "reason": "no quote"})
            continue
        note = notes.get(doc) or {}
        anchor = None
        for source in [*flags_of(note), *(note.get("figures") or [])]:
            if quote in collapse(source.get("quote")):
                anchor = source.get("anchor", "")
                break
        if anchor is None:
            dropped.append({**found, "reason": "the quote is not in the document's note"})
            continue
        kept.append({**found, "quote": quote, "anchor": anchor})
    return kept, dropped


def parse_findings(text: str) -> list:
    """The list of findings a reply carries, as a JSON object's findings or a bare list."""
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("findings", [])
    if not isinstance(data, list):
        raise ValueError("the reply holds no list of findings")
    return data


def ask_group(docs, notes, system, cap, gateway, batch, model) -> dict:
    """One group's call, and its one further call where the first keeps nothing."""
    user = "\n\n".join(note_block(doc, notes.get(doc)) for doc in docs) + "\n"
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    returned: list = []
    dropped: list[dict] = []
    kept: list[dict] = []
    calls = 0
    sending = messages
    for _ in range(2):
        calls += 1
        try:
            completion = batch.record(gateway.complete(model, sending, max_tokens=MAX_OUTPUT_TOKENS))
        except NoReply as exc:
            batch.record(Completion("", exc.tokens_in, exc.tokens_out, exc.seconds, model))
            sending = messages
            continue
        try:
            findings = parse_findings(completion.text)
        except ValueError as exc:
            reason = f"the reply could not be read as JSON ({exc})"
        else:
            returned += findings
            kept, lost = check_findings(findings, docs, notes)
            dropped += lost
            if kept:
                break
            reason = "no finding named a document of the group with a quote from its note"
        sending = reask_messages(messages, completion.text, REASK.format(reason=reason, cap=cap))
    for item in kept[cap:]:
        dropped.append({**item, "reason": f"past the cap of {cap}"})
    return {"docs": docs, "calls": calls, "returned": returned, "findings": kept[:cap], "dropped": dropped}


def tree(
    room: Path,
    run_dir: Path,
    gateway: Gateway | None = None,
    ledger=None,
    phase: int = PHASE,
    model: str = DEFAULT_MODEL,
    budget: int | None = None,
) -> dict:
    """Groups the room, asks every group for its findings, writes run_dir / tree.json and
    returns it."""
    room, run_dir = Path(room), Path(run_dir)
    if ledger is None:
        ledger = Ledger(Path(__file__).resolve().parents[2] / "LEDGER.md")
    if gateway is None:
        gateway = Gateway()
    notes = read_notes(room, run_dir)
    sizes = {doc: estimate_tokens(note_block(doc, note)) for doc, note in notes.items()}
    if budget is None:
        budget = group_budget(model, instructions(room, len(notes), DIGEST_ROWS))
    groups = make_groups(sizes, budget)
    cap = group_cap(len(groups))
    systems = [instructions(room, len(docs), cap) for docs in groups]
    estimated = sum(estimate_tokens(system) + sum(sizes[doc] for doc in docs) for system, docs in zip(systems, groups))

    with ledger.batch(room.name, phase, model, estimated, MAX_OUTPUT_TOKENS * len(groups)) as batch:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            answered = list(pool.map(
                lambda pair: ask_group(pair[1], notes, pair[0], cap, gateway, batch, model),
                zip(systems, groups),
            ))
    for docs, group in zip(groups, answered):
        group["tokens"] = sum(sizes[doc] for doc in docs)
    built = {"model": model, "budget": budget, "cap": cap, "groups": answered}
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / TREE_FILE).write_text(json.dumps(built, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    kept = sum(len(group["findings"]) for group in answered)
    lost = sum(len(group["dropped"]) for group in answered)
    print(f"tree {room.name}: {len(groups)} groups, {kept} findings kept, {lost} dropped")
    return built


# ---------------------------------------------------------------- what the writer reads


def by_document(room: Path, built: dict) -> list[tuple[str, list[dict]]]:
    """The kept findings grouped by document, in the room's order, each document's in the order
    its group ranked them."""
    found: dict[str, list[dict]] = {}
    for group in built["groups"]:
        for item in group["findings"]:
            found.setdefault(item["doc"], []).append(item)
    return [(doc, found[doc]) for doc in room_documents(room) if doc in found]


def tree_digest(room: Path, run_dir: Path, built: dict) -> str:
    """The kept findings by document in the room's order, as the writer reads them."""
    named = titles(room)
    documents = by_document(room, built)
    lines = [
        "# Digest",
        "",
        "The findings a reader chose from every document of the room, grouped by document in the "
        "room's order. A row is `- <finding> | <doc> | <words> | <anchor>`, the words copied from "
        "the document. There are no comparisons, no timeline and no lesser matters.",
        "",
        "### Documents",
        "",
    ]
    lines += [f"- {place}. {doc} | {field(named.get(doc, doc))} | - | - | -" for place, (doc, _) in enumerate(documents, start=1)]
    lines.append("")
    for place, (doc, items) in enumerate(documents, start=1):
        lines += [f"### {place}. {doc} | {field(named.get(doc, doc))}", ""]
        for item in items:
            lines.append(f"- {field(item['finding'])} | {doc} | {clean(item['quote'])} | {item['anchor']}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def tree_evidence(room: Path, run_dir: Path, built: dict) -> str:
    """The schedule of the kept findings' own quotes, one line each ending in its citation,
    under a heading per document in the room's order."""
    named = titles(room)
    lines: list[str] = []
    for doc, items in by_document(room, built):
        block: list[str] = []
        for item in items:
            line = f'- {schedule_field(item["finding"])} | "{clean(item["quote"])}" | [{doc} | {item["anchor"]}]'
            if line not in block:
                block.append(line)
        lines += [f"### {doc} | {field(named.get(doc, doc))}", "", *block, ""]
    return "\n".join(lines).rstrip("\n") + "\n"


def read_tree(run_dir: Path) -> dict:
    return json.loads((Path(run_dir) / TREE_FILE).read_text(encoding="utf-8"))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m rlm.tree")
    parser.add_argument("room")
    parser.add_argument("run_dir")
    parser.add_argument("--phase", type=int, default=PHASE)
    return parser.parse_args(argv)


def main(argv: list[str], gateway: Gateway | None = None, ledger=None) -> int:
    """Runs the stage from the command line; 0 when tree.json is written."""
    args = parse_args(argv)
    if args.phase not in PHASE_CAPS:
        print(f"no such phase in the caps: {args.phase}")
        return 2
    tree(Path(args.room), Path(args.run_dir), gateway=gateway, ledger=ledger, phase=args.phase)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
