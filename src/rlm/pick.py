"""Ranks every document of a room against the fixed acquisition checklist and chooses the
documents whose notes the writer reads.

The checklist is checklists/acquisition.md, one line per item, `- <id> [<types>]: <question>`.
load_checklist keeps the items whose types include the deal, share or asset.

Two rankers, called arms. Arm `llm` makes one gateway call to DEFAULT_MODEL carrying the
checklist and, for every document, its note's `what` and the text of each of its flags; the
model answers with every document id in order of how much the document bears on the
checklist. Ids it leaves out follow the rest in the room's own order and ids it invents are
dropped. Arm `jev` asks TypeSafe's Jev, through its own HTTP endpoint, one yes or no question
per checklist item about the document's own text from the room. A document longer than Jev
takes is split into consecutive pieces that fit and scores its best piece. A document's score
on one ask is its highest probability over the items; every document is asked JEV_ASKS times
and the scores averaged, because Jev's answers move between identical calls. Documents are
ranked by score, ties by id. Every raw Jev response is appended to pick-jev-raw.jsonl.

Choosing is the same for both arms: walk the ranked documents and take each document's flags
whole until the next document's flags would take the rows past DIGEST_ROWS. That is the chosen
set and there is no other cut. pick.json holds the arm, the deal, the model, every document
with its score, the chosen documents in rank order and the rows they carry.

pick_digest writes what the writer reads in place of the dossier digest: the chosen documents'
notes whole, flags with their quotes and consequences and then figures, grouped by document in
rank order. The same text is what the verifier reads as the dossier, its Documents list being
the chosen set. pick_evidence writes the schedule of the room's own words under the report.

Money: each arm's calls are one batch of the ledger it is handed, so the estimate is printed
before anything is sent, the phase cap and the ceiling refuse, and one LEDGER.md row is booked.
Jev is priced on input tokens alone at PRICES[JEV_MODEL] and booked with the input tokens each
response reports.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import httpx

from rlm.gateway import PHASE_CAPS, Completion, Gateway, Ledger, estimate_tokens
from rlm.key import room_documents
from rlm.notes import document_text, note_name, read_sections
from rlm.write import DIGEST_ROWS

PHASE = 8

# The model of arm llm: the one a blind rank check of the Avid room used on 2026-10-05.
DEFAULT_MODEL = "z-ai/glm-5.3-flash"

# The ranking reply is one list of ids; this leaves room for a long room's ids and the reasoning
# the GLM endpoints spend before they answer.
RANK_MAX_TOKENS = 16000

ARMS = ("llm", "jev")
DEALS = ("share", "asset")

CHECKLIST = Path(__file__).resolve().parent / "checklists" / "acquisition.md"
_ITEM = re.compile(r"^- ([a-z0-9-]+) \[([a-z, ]+)\]: (.+)$")
_DEAL = re.compile(r"\bAn? (share|asset) deal covers ([^.]+)\.")

# Jev, TypeSafe's decision model, on TypeSafe's own API. JEV_MODEL is the id PRICES knows it by.
JEV_MODEL = "typesafe/jev-1.13.0"
JEV_WIRE_MODEL = "jev-1.13.0"
JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_TOKEN_LIMIT = 32_000
# The share of Jev's limit a request is allowed to fill by the repository's estimate of four
# characters a token. Contract text with numbers and defined terms runs nearer three characters
# a token, so a request at the full estimate could pass the limit.
JEV_MARGIN = 0.6
JEV_ASKS = 2
JEV_WORKERS = 4
JEV_TIMEOUT_SECONDS = 120.0
# The seconds waited before each further try of a request Jev answered with 429 or 529.
JEV_WAITS: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0)
JEV_BUSY = frozenset({429, 529})

PICK_FILE = "pick.json"
JEV_RAW = "pick-jev-raw.jsonl"

RANK_PROMPT = """You rank the documents of one data room by how much each bears on a buy-side
acquisition checklist.

The checklist below is a list of yes or no questions about a single contract, for a {deal} deal.
The next message lists every document of the room by its id, with what the document is and the
risks a reader flagged in it. A document bears more on the checklist the more of its questions
it answers yes and the more those answers matter to a buyer.

Answer with one JSON object and nothing else:

{{"ranked": ["<id>", "<id>", ...]}}

Every document id once, the one that bears most on the checklist first. Copy each id character
for character from the line that begins `id: `.

THE CHECKLIST

"""


@dataclass(frozen=True)
class Item:
    """One checklist item: its id, the deal types it is asked for and its question."""

    id: str
    types: tuple[str, ...]
    question: str


def load_checklist(deal: str) -> list[Item]:
    """The checklist items whose types include the deal, in the file's order."""
    if deal not in DEALS:
        raise ValueError(f"no such deal type: {deal}; a deal is one of {', '.join(DEALS)}")
    found = []
    for line in CHECKLIST.read_text(encoding="utf-8").splitlines():
        match = _ITEM.match(line.strip())
        if not match:
            continue
        types = tuple(part.strip() for part in match.group(2).split(","))
        if deal in types:
            found.append(Item(match.group(1), types, match.group(3).strip()))
    return found


def deal_line(deal: str) -> str:
    """The one line the report opens with in pick mode, naming the deal type."""
    covers = {m.group(1): m.group(2) for m in _DEAL.finditer(CHECKLIST.read_text(encoding="utf-8"))}
    return (
        f"Deal type: {deal}. A {deal} deal covers {covers[deal]}; the documents were ranked "
        f"against the acquisition checklist for it."
    )


def read_notes(room: Path, run_dir: Path) -> dict[str, dict | None]:
    """Every document of the room in the room's own order, with its note or None."""
    found: dict[str, dict | None] = {}
    for doc in room_documents(room):
        path = Path(run_dir) / "notes" / note_name(doc)
        found[doc] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    return found


def flags_of(note: dict | None) -> list[dict]:
    return list((note or {}).get("flags") or [])


def choose(ranked: list[str], notes: dict[str, dict | None], cap: int = DIGEST_ROWS) -> tuple[list[str], int]:
    """The documents taken whole from the top of the ranking until the next would pass cap
    rows, a row being one flag, and the rows they carry.

    The first document is taken whatever its rows: a room whose top document alone carries more
    than cap flags would otherwise choose nothing and the writer would read an empty digest.
    """
    chosen: list[str] = []
    rows = 0
    for doc in ranked:
        count = len(flags_of(notes.get(doc)))
        if chosen and rows + count > cap:
            break
        chosen.append(doc)
        rows += count
    return chosen, rows


# ---------------------------------------------------------------- arm llm


def order_reply(ids: list[str], reply: list) -> list[str]:
    """The room's ids in the order the reply gives them, invented ids dropped, a repeat kept at
    its first place, and the ids the reply leaves out after the rest in the room's order."""
    known = set(ids)
    ordered: list[str] = []
    for value in reply:
        doc = str(value).strip()
        if doc in known and doc not in ordered:
            ordered.append(doc)
    return ordered + [doc for doc in ids if doc not in ordered]


def rank_messages(items: list[Item], deal: str, notes: dict[str, dict | None]) -> list[dict]:
    """The ranking call: the checklist in the instructions, every document's note below it."""
    checklist = "\n".join(f"- {item.question}" for item in items)
    blocks = []
    for doc, note in notes.items():
        lines = [f"id: {doc}", f"what: {(note or {}).get('what', '')}"]
        lines += [f"- {flag.get('flag', '')}" for flag in flags_of(note)]
        blocks.append("\n".join(lines))
    return [
        {"role": "system", "content": RANK_PROMPT.format(deal=deal) + checklist + "\n"},
        {"role": "user", "content": "\n\n".join(blocks) + "\n"},
    ]


def parse_ranking(text: str) -> list:
    """The list of ids a ranking reply carries, as a JSON object's ranked list or a bare list."""
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("ranked", [])
    if not isinstance(data, list):
        raise ValueError("the ranking reply holds no list of ids")
    return data


def rank_llm(room: Path, deal: str, notes: dict[str, dict | None], gateway: Gateway, ledger, phase: int) -> list[dict]:
    """Every document with a score of its place, the first at 1, from one gateway call."""
    messages = rank_messages(load_checklist(deal), deal, notes)
    estimated = estimate_tokens("\n".join(message["content"] for message in messages))
    with ledger.batch(room.name, phase, DEFAULT_MODEL, estimated, RANK_MAX_TOKENS) as batch:
        completion = batch.record(gateway.complete(DEFAULT_MODEL, messages, max_tokens=RANK_MAX_TOKENS))
    ids = list(notes)
    ordered = order_reply(ids, parse_ranking(completion.text))
    return [{"doc": doc, "score": round(1 - place / len(ids), 6)} for place, doc in enumerate(ordered)]


# ---------------------------------------------------------------- arm jev


def jev_questions(items: list[Item]) -> dict[str, dict]:
    """Every checklist item as one noul question under its id."""
    return {item.id: {"type": "noul", "instructions": item.question} for item in items}


def request_tokens(state: str, questions: dict) -> int:
    """The estimated tokens of one Jev request: the document's text and the questions."""
    return estimate_tokens(state) + estimate_tokens(json.dumps(questions))


def jev_pieces(text: str, questions: dict) -> list[str]:
    """The text in consecutive pieces each of whose requests fits JEV_MARGIN of Jev's limit.

    A piece is cut at a line end; a line longer than a whole piece is cut inside the line.
    Joining the pieces with a line end gives the text back, the cuts inside a line aside.
    """
    room = int(JEV_TOKEN_LIMIT * JEV_MARGIN) - estimate_tokens(json.dumps(questions))
    limit = room * 4
    if len(text) <= limit:
        return [text]
    lines: list[str] = []
    for line in text.split("\n"):
        while len(line) > limit:
            lines.append(line[:limit])
            line = line[limit:]
        lines.append(line)
    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for line in lines:
        added = len(line) + (1 if current else 0)
        if current and size + added > limit:
            pieces.append("\n".join(current))
            current, size = [], 0
            added = len(line)
        current.append(line)
        size += added
    if current:
        pieces.append("\n".join(current))
    return pieces


def jev_key(env_files: list[Path] | None = None) -> str:
    """TYPESAFE_API_KEY from the environment, else from the first .env file that carries it.

    The files looked at are the current folder's .env and the checkout's own.
    """
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if key:
        return key
    if env_files is None:
        env_files = [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]
    for path in env_files:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "TYPESAFE_API_KEY":
                return value.strip().strip('"').strip("'")
    return ""


class JevClient:
    """Posts one Jev request at a time and waits through 429 and 529. The transport is
    injectable so a test can fake it."""

    def __init__(self, api_key: str, transport: httpx.BaseTransport | None = None,
                 waits: tuple[float, ...] = JEV_WAITS, url: str = JEV_URL):
        self.api_key = api_key
        self.url = url
        self.waits = tuple(waits)
        self._client = httpx.Client(transport=transport, timeout=JEV_TIMEOUT_SECONDS)

    def ask(self, state: str, questions: dict) -> tuple[int, dict | None, int]:
        """One request: the status, the decoded body when there is one, and the tries taken."""
        body = {"model": JEV_WIRE_MODEL, "state": state, "questions": questions}
        tries = 0
        for wait in (*self.waits, None):
            tries += 1
            response = self._client.post(
                self.url, json=body, headers={"Authorization": f"Bearer {self.api_key}"}
            )
            if response.status_code not in JEV_BUSY or wait is None:
                break
            time.sleep(wait)
        try:
            data = response.json()
        except ValueError:
            data = None
        return response.status_code, data, tries


def highest_noul(data: dict | None, questions: dict) -> float:
    """The highest probability of yes over the questions one response answers.

    Raises ValueError when a question has no noul answer.
    """
    answers = (data or {}).get("answers") or {}
    found = []
    for name in questions:
        answer = answers.get(name)
        if not isinstance(answer, dict) or not isinstance(answer.get("noul"), (int, float)):
            raise ValueError(f"no noul answer for {name}")
        found.append(float(answer["noul"]))
    return max(found)


def rank_jev(room: Path, run_dir: Path, deal: str, client: JevClient, ledger, phase: int, label: str = "") -> list[dict]:
    """Every document with the mean over JEV_ASKS asks of its best piece's highest noul,
    ranked by score and then by id."""
    questions = jev_questions(load_checklist(deal))
    sections = read_sections(run_dir)
    jobs: list[tuple[str, int, int, str]] = []
    for doc, path in room_documents(room).items():
        text = document_text(sections.get(path) or [])
        if not text.strip():
            continue
        for ask in range(1, JEV_ASKS + 1):
            for number, piece in enumerate(jev_pieces(text, questions), start=1):
                jobs.append((doc, ask, number, piece))
    estimated = sum(request_tokens(piece, questions) for _, _, _, piece in jobs)

    lock = threading.Lock()
    best: dict[tuple[str, int], float] = {}
    failed: list[str] = []
    raw_path = Path(run_dir) / JEV_RAW

    with ledger.batch(room.name, phase, JEV_MODEL, estimated, 0) as batch, raw_path.open(
        "a", encoding="utf-8", newline="\n"
    ) as raw:

        def one(job: tuple[str, int, int, str]) -> None:
            doc, ask, number, piece = job
            started = time.monotonic()
            error = None
            try:
                status, data, tries = client.ask(piece, questions)
            except httpx.HTTPError as exc:
                status, data, tries, error = None, None, 0, f"{type(exc).__name__}: {exc}"
            tokens = int(((data or {}).get("usage") or {}).get("input_tokens") or 0) if isinstance(data, dict) else 0
            score = None
            if error is None and status == 200:
                try:
                    score = highest_noul(data, questions)
                except ValueError as exc:
                    error = str(exc)
            elif error is None:
                error = f"status {status}"
            record = {
                "doc": doc, "ask": ask, "piece": number, "pass": label, "status": status,
                "tries": tries, "input_tokens": tokens, "error": error, "response": data,
                "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            }
            with lock:
                raw.write(json.dumps(record, ensure_ascii=False) + "\n")
                raw.flush()
                batch.record(Completion("", tokens, 0, time.monotonic() - started, JEV_MODEL))
                if score is None:
                    failed.append(f"{doc} ask {ask} piece {number}: {error}")
                else:
                    best[(doc, ask)] = max(best.get((doc, ask), 0.0), score)

        with ThreadPoolExecutor(max_workers=JEV_WORKERS) as pool:
            list(pool.map(one, jobs))

    if failed:
        raise RuntimeError(f"Jev answered {len(failed)} requests with no score: " + "; ".join(failed[:5]))
    scores = {}
    for doc in room_documents(room):
        asked = [best[(doc, ask)] for ask in range(1, JEV_ASKS + 1) if (doc, ask) in best]
        scores[doc] = round(sum(asked) / len(asked), 6) if asked else 0.0
    ordered = sorted(scores, key=lambda doc: (-scores[doc], doc))
    return [{"doc": doc, "score": scores[doc]} for doc in ordered]


# ---------------------------------------------------------------- the stage


def pick(
    room: Path,
    run_dir: Path,
    arm: str,
    deal: str,
    gateway: Gateway | None = None,
    ledger=None,
    jev: JevClient | None = None,
    phase: int = PHASE,
    out: str = PICK_FILE,
) -> dict:
    """Ranks the room by one arm, chooses by the rows rule, writes run_dir / out and returns it."""
    room, run_dir = Path(room), Path(run_dir)
    if arm not in ARMS:
        raise ValueError(f"no such ranker: {arm}; a ranker is one of {', '.join(ARMS)}")
    load_checklist(deal)
    if ledger is None:
        ledger = Ledger(Path(__file__).resolve().parents[2] / "LEDGER.md")
    notes = read_notes(room, run_dir)
    if arm == "llm":
        if gateway is None:
            gateway = Gateway()
        ranked = rank_llm(room, deal, notes, gateway, ledger, phase)
        model = DEFAULT_MODEL
    else:
        if jev is None:
            key = jev_key()
            if not key:
                raise RuntimeError("TYPESAFE_API_KEY is not set in the environment or a .env file")
            jev = JevClient(key)
        ranked = rank_jev(room, run_dir, deal, jev, ledger, phase, label=out)
        model = JEV_MODEL
    chosen, rows = choose([row["doc"] for row in ranked], notes)
    picked = {"arm": arm, "deal": deal, "model": model, "ranked": ranked, "chosen": chosen, "rows": rows}
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / out).write_text(json.dumps(picked, indent=2) + "\n", encoding="utf-8")
    print(f"pick {room.name}: {arm} chose {len(chosen)} of {len(ranked)} documents, {rows} rows")
    return picked


# ---------------------------------------------------------------- what the writer reads


def clean(text: object) -> str:
    """A note's text on one line, its words otherwise as the note has them."""
    return " ".join(str(text or "").split())


def field(text: object) -> str:
    """A field of our own words on one line, with no bar that would split the row."""
    return clean(text).replace(" | ", " / ")


def titles(room: Path) -> dict[str, str]:
    """Each document's file name, the title the digest and the schedule give it."""
    return {doc: Path(path).name for doc, path in room_documents(room).items()}


def pick_digest(room: Path, run_dir: Path, picked: dict) -> str:
    """The chosen documents' notes whole, by document in rank order, as the writer reads them.

    A flag row is `- <flag> Consequence: <consequence> | <doc> | <quote> | <anchor>` and a figure
    row `- <figure> | <doc> | <quote> | <anchor>`. The Documents list names the chosen set.
    """
    notes = read_notes(room, run_dir)
    named = titles(room)
    chosen = picked["chosen"]
    lines = [
        "# Digest",
        "",
        f"The documents of the room that bear most on the acquisition checklist for a "
        f"{picked['deal']} deal, in rank order, each with its note whole. A flag row is "
        f"`- <flag> Consequence: <consequence> | <doc> | <words> | <anchor>` and a figure row "
        f"`- <figure> | <doc> | <words> | <anchor>`. There are no comparisons, no timeline and "
        f"no lesser matters.",
        "",
        "### Documents",
        "",
    ]
    lines += [f"- {place}. {doc} | {field(named.get(doc, doc))} | - | - | -" for place, doc in enumerate(chosen, start=1)]
    lines.append("")
    for place, doc in enumerate(chosen, start=1):
        note = notes.get(doc) or {}
        lines += [f"### {place}. {doc} | {field(named.get(doc, doc))}", ""]
        if note.get("what"):
            lines += [field(note["what"]), ""]
        for flag in flags_of(note):
            lines.append(
                f"- {field(flag.get('flag'))} Consequence: {field(flag.get('consequence'))} | {doc} | "
                f"{clean(flag.get('quote'))} | {flag.get('anchor', '')}"
            )
        figures = note.get("figures") or []
        if figures:
            lines += ["", "Figures:", ""]
            for figure in figures:
                lines.append(
                    f"- {field(figure.get('surface'))} | {doc} | {clean(figure.get('quote'))} | "
                    f"{figure.get('anchor', '')}"
                )
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def digest_rows(digest: str) -> list[str]:
    """The rows of a pick digest that carry an anchor, the Documents list left out."""
    return [line for line in digest.splitlines() if line.startswith("- ") and "#" in line.rsplit(" | ", 1)[-1]]


def schedule_field(text: object) -> str:
    """The first field of a schedule line: no bar, quotation mark or bracket inside it."""
    return re.sub(r'[|"\[\]]', "", field(text)).strip()


def pick_evidence(room: Path, run_dir: Path, picked: dict) -> str:
    """The schedule of the chosen documents' own words, one line per flag and per figure, each
    ending in its citation, under a heading per document in rank order."""
    notes = read_notes(room, run_dir)
    named = titles(room)
    lines: list[str] = []
    for doc in picked["chosen"]:
        note = notes.get(doc) or {}
        block: list[str] = []
        items = [(flag.get("flag"), flag) for flag in flags_of(note)]
        items += [(figure.get("surface"), figure) for figure in note.get("figures") or []]
        for first, item in items:
            quote = clean(item.get("quote"))
            line = f'- {schedule_field(first)} | "{quote}" | [{doc} | {item.get("anchor", "")}]'
            if line not in block:
                block.append(line)
        if not block:
            continue
        lines += [f"### {doc} | {field(named.get(doc, doc))}", "", *block, ""]
    return "\n".join(lines).rstrip("\n") + "\n"


def read_pick(run_dir: Path) -> dict:
    return json.loads((Path(run_dir) / PICK_FILE).read_text(encoding="utf-8"))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m rlm.pick")
    parser.add_argument("room")
    parser.add_argument("run_dir")
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--deal", choices=DEALS, default="share")
    parser.add_argument("--phase", type=int, default=PHASE)
    parser.add_argument("--out", default=PICK_FILE, help="the file name under the run folder")
    return parser.parse_args(argv)


def main(argv: list[str], gateway: Gateway | None = None, ledger=None, jev: JevClient | None = None) -> int:
    """Runs the stage from the command line; 0 when pick.json is written."""
    args = parse_args(argv)
    if args.phase not in PHASE_CAPS:
        print(f"no such phase in the caps: {args.phase}")
        return 2
    pick(Path(args.room), Path(args.run_dir), args.arm, args.deal, gateway=gateway, ledger=ledger,
         jev=jev, phase=args.phase, out=args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
