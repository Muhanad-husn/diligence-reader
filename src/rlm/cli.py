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
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from rlm import __version__
from rlm import dossier as dossier_stage
from rlm import export as export_stage
from rlm import ingest as ingest_stage
from rlm import map as map_stage
from rlm import settings
from rlm import notes as notes_stage
from rlm import pick as pick_stage
from rlm import tree as tree_stage
from rlm import write as write_stage
from rlm.gateway import (
    PHASE_CAPS,
    Gateway,
    Ledger,
    Meter,
    NoReply,
    estimate_tokens,
    price,
    register_listing,
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
    "unknown-model",
    "bad-settings",
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


# What the group step reads and writes, as shares of what the estimate already counts. The notes
# of a room come to about this share of its documents' tokens, which is what the group calls
# read; a finding is about this many tokens of reply. Both are assumptions until a priced run of
# the sample rooms replaces them; the estimate is a ceiling to confirm, and what a run costs is
# counted from its own calls.
GROUP_BILLED_IN = 0.6
TOKENS_PER_FINDING = 120

# The calls a writer in full makes: the first sections and the lesser issues, each reading the digest.
FULL_WRITER_CALLS = 3


@dataclass(frozen=True)
class Estimate:
    """What the model calls ahead are expected to cost: counted input tokens and dollars, in all
    and for each task that is still to run, with the model each is priced at."""

    notes_tokens: int
    write_tokens: int
    dollars: float
    group_tokens: int = 0
    tasks: dict = field(default_factory=dict)

    @property
    def tokens(self) -> int:
        return self.notes_tokens + self.group_tokens + self.write_tokens


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


def estimate(
    room: Path,
    run_dir: Path,
    notes_left: bool,
    write_left: bool,
    chosen: settings.Settings | None = None,
) -> Estimate:
    """Prices the model stages still to run, each at its own model, from what ingest has written.

    The notes are every document of the room that has sections, counted the way the notes pass
    counts its own request, and billed at NOTES_BILLED_IN and NOTES_BILLED_OUT of that count. The
    group step, where the report is built on the tree, reads GROUP_BILLED_IN of the documents'
    tokens in groups the model's window allows and writes the findings it keeps. The report is the instructions and the room's brief plus the digest's
    rows of DIGEST_ROW_TOKENS, and the writer's reply cap back, as often as the writer calls:
    once, or FULL_WRITER_CALLS times for a writer in full. An OpenRouter model outside PRICES is
    priced at its listed rate and a Claude Code model at zero. chosen is the settings, else the
    saved ones.
    """
    chosen = chosen if chosen is not None else settings.current()
    sections = notes_stage.read_sections(run_dir)
    room_tokens = sum(
        notes_stage.request_tokens(sections[doc])
        for doc in room_documents(room).values()
        if sections.get(doc)
    )
    tasks: dict[str, dict] = {}
    notes_tokens = 0
    if notes_left:
        notes_tokens = room_tokens
        tasks["notes"] = {
            "model": chosen.notes,
            "dollars": price(
                chosen.notes,
                round(notes_tokens * NOTES_BILLED_IN),
                round(notes_tokens * NOTES_BILLED_OUT),
            ),
        }
    group_tokens = 0
    findings = 0
    if chosen.write in settings.TREE_MODES:
        findings = tree_stage.FINDING_ROWS.get(chosen.group, write_stage.DIGEST_ROWS)
        if not done("tree", run_dir):
            system = tree_stage.instructions(room, len(room_documents(room)), findings)
            reads = round(room_tokens * GROUP_BILLED_IN)
            groups = max(1, math.ceil(reads / max(1, tree_stage.group_budget(chosen.group, system))))
            group_tokens = reads + groups * estimate_tokens(system)
            tasks["group"] = {
                "model": chosen.group,
                "dollars": price(
                    chosen.group,
                    group_tokens,
                    min(findings * TOKENS_PER_FINDING, groups * tree_stage.MAX_OUTPUT_TOKENS),
                ),
            }
    write_tokens = 0
    if write_left:
        brief = write_stage.brief_path(room).read_text(encoding="utf-8")
        rows = write_stage.DIGEST_ROWS if chosen.write != "tree" else 0
        rows += findings
        write_tokens = estimate_tokens(write_stage.PROMPT + brief) + rows * DIGEST_ROW_TOKENS
        calls = FULL_WRITER_CALLS if write_stage.writes_in_full(chosen.writer) else 1
        tasks["writer"] = {
            "model": chosen.writer,
            "dollars": price(
                chosen.writer, write_tokens * calls, write_stage.reply_cap(chosen.writer)
            ),
        }
    return Estimate(
        notes_tokens=notes_tokens,
        write_tokens=write_tokens,
        dollars=sum(task["dollars"] for task in tasks.values()),
        group_tokens=group_tokens,
        tasks=tasks,
    )


def confirm(found: Estimate, yes: bool) -> None:
    """Prints the estimate and asks y/N, raising Stopped as declined on anything but y."""
    counted = [f"{found.notes_tokens} for the notes"]
    if "group" in found.tasks:
        counted.append(f"{found.group_tokens} for the group step")
    counted.append(f"{found.write_tokens} for the report")
    priced = "; ".join(
        f"{settings.TASK_NAMES[task]} {info['model']} ${info['dollars']:.2f}" for task, info in found.tasks.items()
    )
    print(
        f"estimate: {found.tokens} input tokens counted ({', '.join(counted)}), "
        f"about ${found.dollars:.2f} on {priced}"
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
        self.models = before.get("models")
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
            "models": self.models,
            "version": __version__,
        }
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / RUN_FILE).write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def resolve_settings(args: argparse.Namespace) -> settings.Settings:
    """The models and the build of this run, from the first of these that names each field: a
    flag, the run's own settings file, the settings saved on this machine, the defaults. A
    ranker's run builds no tree, so the saved way of writing does not carry over to it."""
    found = settings.current()
    if args.settings:
        found = settings.from_dict(json.loads(Path(args.settings).read_text(encoding="utf-8")), found)
    flags = {
        "notes": args.notes_model,
        "group": args.middle_model,
        "writer": args.writer_model,
        "write": args.write,
    }
    flags = {name: value for name, value in flags.items() if value is not None}
    if args.rank is not None and "write" not in flags:
        flags["write"] = ""
    if flags:
        found = settings.from_dict(flags, found)
    return found


def check_settings(found: settings.Settings, gateway: Gateway | None) -> None:
    """Refuses settings that cannot run before any model call: a model no provider serves or a
    way of writing that is none.

    An OpenRouter id the five models of PRICES do not vouch for is looked up in OpenRouter's own
    model list, which is free to read and needs no key; the list also gives its price and window.
    """
    listing = None
    if settings.needs_listing(found):
        lister = gateway if gateway is not None else Gateway()
        try:
            listing = lister.models()
        except httpx.HTTPError as exc:
            raise Stopped(
                "unexpected", f"OpenRouter's model list could not be read to check the models: {type(exc).__name__}"
            ) from exc
        register_listing(listing, lister.context_lengths)
    try:
        settings.validate(found, listing)
    except settings.UnknownModel as exc:
        raise Stopped("unknown-model", str(exc)) from exc
    except settings.SettingsError as exc:
        raise Stopped("bad-settings", str(exc)) from exc


def gateway_for(found: settings.Settings, gateway: Gateway | None, ranked: bool = False) -> Gateway:
    """The gateway of this run: the one given, else one on OPENROUTER_API_KEY.

    Raises Stopped as a refused key when a used task runs on OpenRouter, or the run has a ranker,
    whose calls are the pick stage's own on OpenRouter, and the key is not in the environment.
    """
    if gateway is None:
        if (settings.needs_key(found) or ranked) and not os.environ.get("OPENROUTER_API_KEY"):
            raise Stopped("key-refused", "OPENROUTER_API_KEY is not set")
        gateway = Gateway()
    return gateway


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
        try:
            chosen = resolve_settings(args)
        except (settings.SettingsError, OSError, ValueError) as exc:
            raise Stopped("bad-settings", str(exc)) from exc
        state.models = chosen.to_dict()
        state.stage = "ingest"
        check_settings(chosen, gateway)

        if not done("ingest", run_dir):
            state.write("running")
            print(ingest_stage.coverage_line(ingest_stage.ingest(room, run_dir)))

        notes_left = not done("notes", run_dir)
        write_left = not done("write", run_dir)
        if notes_left or write_left:
            state.stage = "notes" if notes_left else "write"
            found = estimate(room, run_dir, notes_left, write_left, chosen)
            state.estimate = round(found.dollars, 6)
            state.write("running")
            confirm(found, args.yes)
            gateway = gateway_for(chosen, gateway, args.rank is not None)

        mode = chosen.write
        state.stage = "notes"
        if notes_left:
            state.write("running")
            notes_argv = [*stage_argv, "--model", chosen.notes]
            if notes_stage.main(notes_argv, gateway=gateway, ledger=meter) != 0:
                raise Stopped("unexpected", "the notes pass did not start")
            if not done("notes", run_dir):
                raise Stopped("empty-reply", "no document of the room was noted")

        if mode == "tree":
            state.stage = "tree"
            if not done("tree", run_dir):
                state.write("running")
                tree_argv = [str(room), str(run_dir), "--phase", phase, "--model", chosen.group]
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

            if mode in ("both", "both-tree-first"):
                state.stage = "tree"
                if not done("tree", run_dir):
                    state.write("running")
                    tree_argv = [str(room), str(run_dir), "--phase", phase, "--model", chosen.group]
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
            write_argv = [
                *stage_argv, "--model", chosen.writer, "--models-line", settings.models_line(chosen)
            ]
            if mode == "tree":
                write_argv.append("--tree")
            elif mode in ("both", "both-tree-first"):
                write_argv.append("--both")
                if mode == "both-tree-first":
                    write_argv.append("--tree-first")
            elif args.rank is not None:
                write_argv.append("--pick")
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
        "--notes-model",
        dest="notes_model",
        default=None,
        help="the model of the notes: an OpenRouter id or claude-code/<model>; the saved or default "
        "model when left off",
    )
    runner.add_argument(
        "--middle-model",
        dest="middle_model",
        default=None,
        help="the model of the group step, which runs with --write tree or both; same choices as --notes-model",
    )
    runner.add_argument(
        "--writer-model",
        dest="writer_model",
        default=None,
        help="the model of the writer; same choices as --notes-model",
    )
    runner.add_argument(
        "--settings",
        default=None,
        help="a JSON file of model settings for this run, laid over the saved settings",
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
