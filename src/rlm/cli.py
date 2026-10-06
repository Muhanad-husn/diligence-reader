"""`diligence-reader run <room> --out <run_dir>`: one command from a data room to a verified report.

The command runs the stages in order, each through its own module with that module's
DEFAULT_MODEL: ingest, notes, map, dossier, write (one pass, which verifies its report and asks
the model once more where it fails), then export to Word, PDF and CSV. Where the room carries
key.json, recall is graded in code over the key's facts and written to grade.json; no rubric is
scored and no subagent runs.

`--rank llm` or `--rank jev` runs the pick stage of rlm.pick in place of the map and the dossier:
the stages are ingest, notes, pick, write and export, the room is ranked against the acquisition
checklist for the deal `--deal` names, share by default, and the writer reads the chosen
documents' notes whole. pick is done when pick.json is there. Without `--rank` the run is the
one above and `--deal` changes nothing.

`--write tree` runs rlm.tree in place of the map and the dossier: the stages are ingest, notes,
tree, write and export, the room's notes are read in groups by a model that keeps the findings
a deal committee must see, and the writer reads those findings. tree is done when tree.json is
there. It does not go with `--rank`. `--write both` runs the map, the dossier and the tree,
and the writer reads the dossier digest followed by the tree's kept findings whose quote the
dossier digest does not hold. `--middle-model` names the group calls' model and
`--writer-model` the writer's, each defaulting to its module's DEFAULT_MODEL; either may be a
Claude Code model on the founder's subscription.

Before the first model call the command prints what the calls ahead will cost: the input tokens
counted by the gateway's counter and the dollars, then asks y/N. `--yes` answers for the user.
Anything but y stops the run as declined with nothing sent. The notes are priced on the counted
input of every note request the pass would send, scaled by the ratios sample 1's own note passes
billed (NOTES_BILLED_IN, NOTES_BILLED_OUT); the report is priced at its digest cap, the request
a full DIGEST_ROWS digest with the brief and the instructions would carry, and MAX_OUTPUT_TOKENS
back.

A stage whose artefact is already in the run folder is skipped, so a run started again after a
failure picks up at the stage that stopped and pays nothing twice for what it already has:
ingest is done when sections.jsonl and index.jsonl are there, notes when notes-summary.json is
there and noted a document, map when map.json is, dossier when dossier.md is, write when
verify.json reads passes true, and export when report.docx, report.pdf and evidence.csv are.
A report that failed the verifier is a stopped stage; running again writes it again, and pays.

run.json in the run folder is written at every stage boundary: the stage, the status (running,
done or failed), the error code (null when there is none), the documents noted, the dollars
spent, the version, the estimate and, where the room has a key, the recall. The dollars are
everything this run's own calls cost, carried across every start of it by run.json. Notes
copied in from an earlier run are not this run's spend.

Every failure exits non-zero and writes one code to run.json, from ERROR_CODES. The message
printed with it is the exception's, which names a status, a file or a model and never the key.

Money: a user's run spends the user's credits and books nothing. Without `--phase` no stage
reads or writes LEDGER.md and no cap applies; the dollars are counted by a Meter for run.json
alone. `--phase N` is for this build's own gate runs: the calls are booked to LEDGER.md under
phase N and refused past its cap, as every other phase's are.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx

from rlm import __version__
from rlm import dossier as dossier_stage
from rlm import export as export_stage
from rlm import ingest as ingest_stage
from rlm import map as map_stage
from rlm import notes as notes_stage
from rlm import pick as pick_stage
from rlm import tree as tree_stage
from rlm import write as write_stage
from rlm.gateway import (
    CLAUDE_CODE_MODELS,
    PHASE_CAPS,
    PRICES,
    Gateway,
    Ledger,
    Meter,
    NoReply,
    estimate_tokens,
    price,
)
from rlm.grade import measure_recall
from rlm.key import has_key, load_key, room_documents

# The stages in the order they run.
STAGES = ("ingest", "notes", "map", "dossier", "write", "export")

# The stages of a run given a ranker: pick stands where the map and the dossier stood.
PICK_STAGES = ("ingest", "notes", "pick", "write", "export")

# The stages of a run given the tree writer: tree stands where the map and the dossier stood.
TREE_STAGES = ("ingest", "notes", "tree", "write", "export")

# The stages of a run given both writers: the tree stands after the dossier.
BOTH_STAGES = ("ingest", "notes", "map", "dossier", "tree", "write", "export")

# The codes a failed run ends on, one per failure, each with its fix in the README.
ERROR_CODES = (
    "key-refused",
    "no-credits",
    "rate-limited",
    "empty-reply",
    "unreadable-file",
    "verify-failed",
    "declined",
    "unexpected",
)

# The gateway statuses each code stands for. A 429 reaches here only after the gateway's own
# waits are spent.
STATUS_CODES = {401: "key-refused", 403: "key-refused", 402: "no-credits", 429: "rate-limited"}

# What one note request bills against what the gateway's counter counts for it. Sample 1's
# counted input is 202453 tokens over its 100 note requests, as notes.request_tokens counts them
# on the pinned sections.jsonl, and its three newest phase 2 rows of z-ai/glm-5.3-flash in
# LEDGER.md, from 2026-09-08 and the pass that re-asks, billed 576648, 560781 and 525705 tokens
# in and 430656, 413668 and 374396 tokens out: 554378 in and 406240 out on average. Billed input
# runs well above the counted input because a re-ask sends the document and the first reply
# again.
NOTES_BILLED_IN = 2.74
NOTES_BILLED_OUT = 2.01

# The tokens one digest row carries, by the gateway's counter: sample 1's pinned digest.md is
# 15611 tokens over its 193 rows.
DIGEST_ROW_TOKENS = 81

# The file the run's state is written to, in the run folder.
RUN_FILE = "run.json"


class Stopped(Exception):
    """A run that stops on one of ERROR_CODES, with the message printed beside the code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Estimate:
    """What the model calls ahead are expected to cost: counted input tokens and dollars."""

    notes_tokens: int
    write_tokens: int
    dollars: float

    @property
    def tokens(self) -> int:
        return self.notes_tokens + self.write_tokens


def code_of(exc: BaseException) -> str:
    """The error code an exception stops a run on."""
    if isinstance(exc, Stopped):
        return exc.code
    if isinstance(exc, httpx.HTTPStatusError):
        return STATUS_CODES.get(exc.response.status_code, "unexpected")
    if isinstance(exc, NoReply):
        return "empty-reply"
    if isinstance(exc, ingest_stage.UnreadableFile):
        return "unreadable-file"
    return "unexpected"


def read_json(path: Path) -> dict | None:
    """A JSON file's object, or None when the file is not there."""
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def stages_for(rank: str | None, write: str | None = None) -> tuple[str, ...]:
    """The stages a run takes: TREE_STAGES with the tree writer, BOTH_STAGES with both writers,
    PICK_STAGES with a ranker, STAGES otherwise."""
    if write == "tree":
        return TREE_STAGES
    if write in ("both", "both-tree-first"):
        return BOTH_STAGES
    return STAGES if rank is None else PICK_STAGES


def done(stage: str, run_dir: Path) -> bool:
    """Says whether a stage's artefact is already in the run folder."""
    if stage == "ingest":
        return (run_dir / "sections.jsonl").exists() and (run_dir / "index.jsonl").exists()
    if stage == "notes":
        summary = read_json(run_dir / "notes-summary.json")
        return bool(summary) and summary.get("noted", 0) > 0
    if stage == "map":
        return (run_dir / "map.json").exists()
    if stage == "dossier":
        return (run_dir / "dossier.md").exists()
    if stage == "pick":
        return (run_dir / pick_stage.PICK_FILE).exists()
    if stage == "tree":
        return (run_dir / tree_stage.TREE_FILE).exists()
    if stage == "write":
        record = read_json(run_dir / "verify.json")
        return bool(record) and record.get("passes") is True
    if stage == "export":
        return all((run_dir / name).exists() for name in ("report.docx", "report.pdf", "evidence.csv"))
    raise ValueError(f"no such stage: {stage}")


def estimate(room: Path, run_dir: Path, notes_left: bool, write_left: bool) -> Estimate:
    """Prices the model stages still to run, from what ingest has written.

    The notes are every document of the room that has sections, counted the way the notes pass
    counts its own request, and billed at NOTES_BILLED_IN and NOTES_BILLED_OUT of that count.
    The report is the instructions and the room's brief plus DIGEST_ROWS rows of
    DIGEST_ROW_TOKENS, and MAX_OUTPUT_TOKENS back.
    """
    notes_tokens = 0
    dollars = 0.0
    if notes_left:
        sections = notes_stage.read_sections(run_dir)
        notes_tokens = sum(
            notes_stage.request_tokens(sections[doc])
            for doc in room_documents(room).values()
            if sections.get(doc)
        )
        dollars += price(
            notes_stage.DEFAULT_MODEL,
            round(notes_tokens * NOTES_BILLED_IN),
            round(notes_tokens * NOTES_BILLED_OUT),
        )
    write_tokens = 0
    if write_left:
        brief = write_stage.brief_path(room).read_text(encoding="utf-8")
        write_tokens = (
            estimate_tokens(write_stage.PROMPT + brief)
            + write_stage.DIGEST_ROWS * DIGEST_ROW_TOKENS
        )
        dollars += price(write_stage.DEFAULT_MODEL, write_tokens, write_stage.MAX_OUTPUT_TOKENS)
    return Estimate(notes_tokens=notes_tokens, write_tokens=write_tokens, dollars=dollars)


def confirm(found: Estimate, yes: bool) -> None:
    """Prints the estimate and asks y/N, raising Stopped as declined on anything but y."""
    print(
        f"estimate: {found.tokens} input tokens counted ({found.notes_tokens} for the notes, "
        f"{found.write_tokens} for the report), about ${found.dollars:.2f} "
        f"on {notes_stage.DEFAULT_MODEL} and {write_stage.DEFAULT_MODEL}"
    )
    if yes:
        return
    try:
        answer = input(f"Spend about ${found.dollars:.2f} on this run? [y/N] ")
    except EOFError:
        answer = ""
    if answer.strip().lower() not in ("y", "yes"):
        raise Stopped("declined", "the estimate was not accepted; nothing was sent")


def grade_recall(sample_dir: Path, report_path: Path, run_dir: Path, name: str) -> dict:
    """Grades one report's recall over the key's facts in code and writes it to run_dir / name.

    The result has the shape rlm.grade.grade writes, with no rubric: the score is the recall.
    """
    key = load_key(sample_dir)
    recall, recalled, missed = measure_recall(key, report_path.read_text(encoding="utf-8"))
    result = {
        "sample": key.sample,
        "report": report_path.name,
        "recall": recall,
        "recalled": recalled,
        "missed": missed,
        "rubric": [],
        "score": recall,
        "model": "none",
        "seconds": 0.0,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / name).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


class RunState:
    """run.json for one run folder: read once when the run starts, written at every boundary."""

    def __init__(self, run_dir: Path, meter: Meter):
        self.run_dir = run_dir
        self.meter = meter
        before = read_json(run_dir / RUN_FILE) or {}
        self.carried = float(before.get("dollars", 0.0))
        self.estimate = before.get("estimate")
        self.stage = "ingest"

    def write(self, status: str, code: str | None = None) -> None:
        """Writes run.json with this stage, this status and the counts read off the run folder."""
        summary = read_json(self.run_dir / "notes-summary.json") or {}
        grade = read_json(self.run_dir / "grade.json")
        state = {
            "stage": self.stage,
            "status": status,
            "code": code,
            "documents_noted": int(summary.get("noted", 0)),
            "dollars": round(self.carried + self.meter.dollars, 6),
            "estimate": self.estimate,
            "recall": grade["recall"] if grade else None,
            "version": __version__,
        }
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / RUN_FILE).write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def run(args: argparse.Namespace, gateway: Gateway | None, ledger: Ledger | None) -> int:
    """Runs every stage not yet done on one room into one run folder; 0 when the run is done."""
    room = Path(args.room)
    run_dir = Path(args.out) if args.out else Path("runs") / room.name
    if args.phase is not None and args.phase not in PHASE_CAPS:
        print(f"no such phase in the caps: {args.phase}")
        return 2
    if not room.is_dir():
        print(f"no room at {room}")
        return 2
    if args.write is not None and args.rank is not None:
        print(f"--write {args.write} does not go with --rank")
        return 2
    if args.phase is not None and ledger is None:
        ledger = Ledger(Path(__file__).resolve().parents[2] / "LEDGER.md")
    meter = Meter(ledger if args.phase is not None else None)
    # A stage module asks for a phase to book to; without --phase the meter books nothing and
    # caps nothing, so the phase it is handed is only a name.
    phase = str(args.phase if args.phase is not None else 8)
    stage_argv = [str(room), str(run_dir), "--phase", phase]

    state = RunState(run_dir, meter)
    try:
        state.stage = "ingest"
        if not done("ingest", run_dir):
            state.write("running")
            print(ingest_stage.coverage_line(ingest_stage.ingest(room, run_dir)))

        notes_left = not done("notes", run_dir)
        write_left = not done("write", run_dir)
        if notes_left or write_left:
            state.stage = "notes" if notes_left else "write"
            found = estimate(room, run_dir, notes_left, write_left)
            state.estimate = round(found.dollars, 6)
            state.write("running")
            confirm(found, args.yes)
            if gateway is None:
                if not os.environ.get("OPENROUTER_API_KEY"):
                    raise Stopped("key-refused", "OPENROUTER_API_KEY is not set")
                gateway = Gateway()

        state.stage = "notes"
        if notes_left:
            state.write("running")
            if notes_stage.main(stage_argv, gateway=gateway, ledger=meter) != 0:
                raise Stopped("unexpected", "the notes pass did not start")
            if not done("notes", run_dir):
                raise Stopped("empty-reply", "no document of the room was noted")

        if args.write == "tree":
            state.stage = "tree"
            if not done("tree", run_dir):
                state.write("running")
                tree_argv = [str(room), str(run_dir), "--phase", phase, "--model", args.middle_model]
                if tree_stage.main(tree_argv, gateway=gateway, ledger=meter) != 0:
                    raise Stopped("unexpected", "the tree did not run")
        elif args.rank is None:
            state.stage = "map"
            if not done("map", run_dir):
                state.write("running")
                if map_stage.main([str(room), str(run_dir)]) != 0:
                    raise Stopped("unexpected", "the map did not run")

            state.stage = "dossier"
            if not done("dossier", run_dir):
                state.write("running")
                if dossier_stage.main([str(room), str(run_dir)]) != 0:
                    raise Stopped("unexpected", "the dossier did not run")

            if args.write in ("both", "both-tree-first"):
                state.stage = "tree"
                if not done("tree", run_dir):
                    state.write("running")
                    tree_argv = [str(room), str(run_dir), "--phase", phase, "--model", args.middle_model]
                    if tree_stage.main(tree_argv, gateway=gateway, ledger=meter) != 0:
                        raise Stopped("unexpected", "the tree did not run")
        else:
            state.stage = "pick"
            if not done("pick", run_dir):
                state.write("running")
                pick_argv = [str(room), str(run_dir), "--arm", args.rank, "--deal", args.deal, "--phase", phase]
                if pick_stage.main(pick_argv, gateway=gateway, ledger=meter) != 0:
                    raise Stopped("unexpected", "the pick did not run")

        state.stage = "write"
        if write_left:
            state.write("running")
            grader = grade_recall if has_key(room) else None
            write_argv = stage_argv
            if args.write == "tree":
                write_argv = [*stage_argv, "--tree", "--model", args.writer_model]
            elif args.write in ("both", "both-tree-first"):
                write_argv = [*stage_argv, "--both", "--model", args.writer_model]
                if args.write == "both-tree-first":
                    write_argv.append("--tree-first")
            elif args.rank is not None:
                write_argv = [*stage_argv, "--pick"]
            if write_stage.main(write_argv, gateway=gateway, ledger=meter, grader=grader) != 0:
                raise Stopped("unexpected", "the write did not start")
            if not done("write", run_dir):
                raise Stopped("verify-failed", "the report failed the verifier after its one re-ask")

        state.stage = "export"
        if not done("export", run_dir):
            state.write("running")
            for path in export_stage.export(run_dir).values():
                print(path)
    except Exception as exc:
        code = code_of(exc)
        state.write("failed", code)
        detail = f"{type(exc).__name__}: {exc}" if code == "unexpected" else str(exc)
        print(f"error: {code}: {detail}")
        return 1

    state.write("done")
    grade = read_json(run_dir / "grade.json")
    recall = f", recall {grade['recall']:g}" if grade else ""
    print(
        f"done: {run_dir}, ${state.carried + meter.dollars:.4f} spent against an estimate of "
        f"${(state.estimate or 0.0):.4f}{recall}"
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Reads the command line."""
    parser = argparse.ArgumentParser(
        prog="diligence-reader",
        description="Reads a data room and writes a cited, verified findings report.",
    )
    parser.add_argument("--version", action="version", version=f"diligence-reader {__version__}")
    commands = parser.add_subparsers(dest="command")
    runner = commands.add_parser("run", help="run every stage not yet done on one room")
    runner.add_argument("room", help="the folder holding the room's documents")
    runner.add_argument(
        "--out", default=None, help="the run folder, runs/<room> under the current folder by default"
    )
    runner.add_argument("--yes", action="store_true", help="accept the estimate without asking")
    runner.add_argument(
        "--phase",
        type=int,
        default=None,
        help="book the calls to LEDGER.md under this phase and its cap; for this build's own runs",
    )
    runner.add_argument(
        "--rank",
        choices=pick_stage.ARMS,
        default=None,
        help="rank the room against the acquisition checklist with this ranker, in place of the map",
    )
    runner.add_argument(
        "--deal",
        choices=pick_stage.DEALS,
        default="share",
        help="the deal type the checklist is asked for; it matters only with --rank",
    )
    runner.add_argument(
        "--write",
        choices=("tree", "both", "both-tree-first"),
        default=None,
        help="tree: models read the notes in groups and keep what the report reads, in place of the "
        "map; both: the report reads the dossier digest and the tree's findings it lacks; "
        "both-tree-first: the same, the tree's findings first",
    )
    runner.add_argument(
        "--middle-model",
        dest="middle_model",
        choices=sorted(tree_stage.CONTEXT_WINDOWS),
        default=tree_stage.DEFAULT_MODEL,
        help="the model of the group calls with --write tree or both",
    )
    runner.add_argument(
        "--writer-model",
        dest="writer_model",
        choices=sorted({*PRICES, *CLAUDE_CODE_MODELS} - {pick_stage.JEV_MODEL}),
        default=write_stage.DEFAULT_MODEL,
        help="the writer's model with --write tree or both",
    )
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
    return args


def main(
    argv: list[str] | None = None,
    gateway: Gateway | None = None,
    ledger: Ledger | None = None,
) -> int:
    """The console script. A test hands it a gateway on a fake transport and a ledger of its own."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.command is None:
        return 2
    return run(args, gateway, ledger)


if __name__ == "__main__":
    sys.exit(main())
