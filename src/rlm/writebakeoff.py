"""Runs the candidate models over the samples and writes the table that names the phase 5 model.

A write is one call of the whole digest and costs what a probe would, so there is no probe
here: every model runs its two passes on every sample of the run, through rlm.write.main with
`--passes 2` into runs/<sample>/write-bakeoff/<slug>/, pass a in that directory and pass b
under its b/. The room each pass reads is still the sample's own run directory, so nothing is
copied.

A row carries, per sample, the recall and the verifier of each pass, and where the sample's
grade file holds rubric rows it carries the rubric score of each pass and the spread between
them. A row passes when pass a on every sample of the run reads recall 100 with a passing
verifier and, where there is a rubric, a rubric score at or above RUBRIC_BAR. Pass b is
measured and reported and does not gate.

Models run cheapest first inside a tier, the flash tier before the pro tier, ordered at the
price of one write. The pro tier is skipped when a flash model passes everywhere, and stops at
the first pro model that passes. The table is written after each model, so a run that dies
part way leaves a readable artefact, and it goes to runs/<sample>/write-bakeoff.json for every
sample of the run, the same bytes in each. The winner is the passing row with the lowest
measured dollars.

Every pass calls rlm.write.main, which opens its own ledger batch, so LEDGER.md gains one line
per pass per sample per model. Nothing here writes LEDGER.md, and nothing here reads an answer
key: the recall, the verifier and the rubric are read out of the grade.json, verify.json and
write-summary.json that each pass left on disk.

--recount rebuilds every row from the pass directories already sitting under
runs/<sample>/write-bakeoff/ on disk, with no gateway call and no ledger line. A recount reads
the reports under the verifier of the day: the recall and the rubric come from grade.json, and
the verifier value of each pass comes from running rlm.verify.verify over that pass's
report.md against the sample's sections.jsonl, index.jsonl, dossier.md and map.json, not from
the passes field verify.json stored. The verify.json files are left as they are. A model with
no directory on any sample it is asked about stays a blank row. --dry-run prints one estimate
per model and writes the blank table.

A run named with --samples writes only the samples it names and reads the row from every
sample the kept table already holds, so a rerun of one sample leaves the other samples of the
row and of the table where they were.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from collections.abc import Callable
from pathlib import Path

from rlm import verify, write
from rlm.gateway import PRICES, Gateway, Ledger, estimate_tokens, price

PHASE = write.PHASE

# What a field of a row says before it is measured.
NOT_RUN = "not run"

# The three gate samples, in the order a run takes them.
SAMPLES = ("atlas", "northwind", "northstar-dental")

# One write on sample 1, as PLAN.md section 5 sizes it: the yardstick a tier is ordered by. A
# write is the digest and the brief in and the report out, twice where the verifier sends the
# first reply back.
WRITE_TOKENS = (37_000, 8_000)

# The rubric score pass a reaches on a sample whose key has a rubric, PLAN.md section 10, set
# by the founder. A sample with no rubric is gated on its recall and its verifier alone.
RUBRIC_BAR = 85

# The recall pass a reaches on every sample, over every fact of the key.
RECALL_BAR = 100.0

# The measured fields of a row, in the order the printed table takes them.
MEASURED = ("passes", "dollars", "seconds", "samples")

# The three files one pass leaves that a row is read out of.
PASS_FILES = ("grade.json", "verify.json", "write-summary.json")


def _ordered(*models: str) -> tuple[str, ...]:
    """One tier, cheapest first at the cost of one write."""
    return tuple(sorted(models, key=lambda model: price(model, *WRITE_TOKENS)))


TIERS: dict[str, tuple[str, ...]] = {
    "flash": _ordered(
        "deepseek/deepseek-v4-flash-0731",
        "z-ai/glm-5.3-flash",
        "openai/gpt-5.6-luna",
    ),
    "pro": _ordered("deepseek/deepseek-v4-pro", "z-ai/glm-5.3"),
}


def slug(model: str) -> str:
    """The part of a model id after the last slash, used as its directory name."""
    return model.rsplit("/", 1)[-1]


def pass_dirs(runs_root: Path, sample: str, name: str) -> tuple[Path, Path]:
    """The pass a and pass b directories of one model on one sample."""
    base = runs_root / sample / "write-bakeoff" / name
    return base, base / "b"


def blank_row(model: str, tier: str) -> dict:
    """One row of the table before anything is measured."""
    row = {"model": model, "slug": slug(model), "tier": tier}
    row.update({field: NOT_RUN for field in MEASURED})
    return row


def sample_room(runs_root: Path, sample: str) -> tuple | None:
    """The sections, the index, the dossier and the map one sample's run directory holds.

    None where any of the three files the verifier needs is absent, which is how a pass whose
    room is not on disk keeps the verifier value verify.json stored.
    """
    run_dir = runs_root / sample
    names = ("sections.jsonl", "index.jsonl", "dossier.md")
    if not all((run_dir / name).exists() for name in names):
        return None
    return (
        verify.read_jsonl(run_dir / "sections.jsonl"),
        verify.read_jsonl(run_dir / "index.jsonl"),
        (run_dir / "dossier.md").read_text(encoding="utf-8"),
        verify.read_mapping(run_dir / "map.json"),
    )


def verified_now(out_dir: Path, room: tuple) -> bool:
    """Whether one pass's report.md on disk verifies under the verifier of the day."""
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    sections, index, dossier, mapping = room
    return bool(verify.verify(report, sections, index, dossier, mapping)["passes"])


def read_pass(out_dir: Path, room: tuple | None = None) -> dict | None:
    """What one pass on disk says about itself, or None where it did not finish.

    The recall and the rubric come from grade.json, the dollars and the seconds from
    write-summary.json. The rubric is the grade's score where the grade holds rubric rows, and
    None where it holds none, which is how a sample whose key has no rubric is told from one
    whose key has one. The verifier value comes from verify.json's passes field, and where a
    room is given it comes instead from reading report.md again with the verifier of the day.
    No key is read.
    """
    if not all((out_dir / name).exists() for name in PASS_FILES):
        return None
    grade = json.loads((out_dir / "grade.json").read_text(encoding="utf-8"))
    verified = json.loads((out_dir / "verify.json").read_text(encoding="utf-8"))
    summary = json.loads((out_dir / "write-summary.json").read_text(encoding="utf-8"))
    passes = bool(verified["passes"])
    if room is not None and (out_dir / "report.md").exists():
        passes = verified_now(out_dir, room)
    return {
        "recall": grade["recall"],
        "verifier": passes,
        "rubric": grade["score"] if grade.get("rubric") else None,
        "dollars": summary["dollars"],
        "seconds": summary["seconds"],
    }


def sample_entry(first: dict, second: dict) -> dict:
    """One sample's part of a row: the recall and the verifier of each pass, and the rubric."""
    entry = {
        "recall_a": first["recall"],
        "recall_b": second["recall"],
        "verifier_a": first["verifier"],
        "verifier_b": second["verifier"],
    }
    if first["rubric"] is not None and second["rubric"] is not None:
        entry["rubric_a"] = first["rubric"]
        entry["rubric_b"] = second["rubric"]
        entry["spread"] = abs(first["rubric"] - second["rubric"])
    return entry


def sample_passes(entry: dict) -> bool:
    """Says whether pass a on one sample clears the bar the phase sets for it."""
    if entry["recall_a"] < RECALL_BAR or not entry["verifier_a"]:
        return False
    return entry.get("rubric_a", RUBRIC_BAR) >= RUBRIC_BAR


def passes_rule(entries: dict[str, dict], samples: list[str]) -> bool:
    """A row passes when every sample of the run was measured and every one of them cleared."""
    if set(entries) != set(samples):
        return False
    return all(sample_passes(entry) for entry in entries.values())


def run_write(
    sample_dir: Path,
    run_dir: Path,
    out_dir: Path,
    model: str,
    gateway: Gateway | None,
    ledger: Ledger | None,
    grader: Callable[[Path, Path, Path, str], dict] | None,
) -> None:
    """Writes two passes of one model on one sample into out_dir."""
    argv = [
        str(sample_dir),
        str(run_dir),
        "--model",
        model,
        "--passes",
        "2",
        "--out-dir",
        str(out_dir),
    ]
    code = write.main(argv, gateway=gateway, ledger=ledger, grader=grader)
    if code != 0:
        raise ValueError(f"the write on {sample_dir.name} refused with code {code}")


def sample_estimate(samples_root: Path, runs_root: Path, sample: str) -> tuple[int, int]:
    """The tokens one pass sends and is capped at, counted as rlm.write counts them.

    A pass is at most two calls: the digest and the brief, then the re-ask carrying the first
    reply back, so the input is counted twice with one reply added to it.
    """
    dossier = (runs_root / sample / "dossier.md").read_text(encoding="utf-8")
    brief = (samples_root / sample / "brief.md").read_text(encoding="utf-8")
    messages = write.build_messages(brief, write.digest_markdown(dossier))
    tokens = estimate_tokens("\n".join(message["content"] for message in messages))
    return 2 * tokens + write.MAX_OUTPUT_TOKENS, 2 * write.MAX_OUTPUT_TOKENS


def sample_estimates(samples_root: Path, runs_root: Path, samples: list[str]) -> dict[str, tuple[int, int]]:
    """The tokens of one pass per sample, read once."""
    return {sample: sample_estimate(samples_root, runs_root, sample) for sample in samples}


def model_estimate(estimates: dict[str, tuple[int, int]], model: str) -> float:
    """What one model costs at the table's price if it runs both passes on every sample."""
    return sum(2 * price(model, *tokens) for tokens in estimates.values())


def fill_row(
    row: dict,
    samples: list[str],
    runs_root: Path,
    rooms: dict[str, tuple | None],
    required: tuple[str, ...] = (),
) -> None:
    """Fills one row from the pass directories on disk, one entry per sample with both passes.

    A sample of required whose passes are not on disk is a refusal. A row with no pass at all
    is left as it was, which is how a model that never ran stays a blank row.
    """
    dollars = 0.0
    seconds = 0.0
    entries: dict[str, dict] = {}

    for sample in samples:
        a_dir, b_dir = pass_dirs(runs_root, sample, row["slug"])
        room = rooms.get(sample)
        first, second = read_pass(a_dir, room), read_pass(b_dir, room)
        if first is None or second is None:
            if sample in required:
                raise ValueError(f"the write on {sample} left no pass to read")
            continue
        entries[sample] = sample_entry(first, second)
        dollars += first["dollars"] + second["dollars"]
        seconds += first["seconds"] + second["seconds"]

    if not entries:
        return

    row["samples"] = entries
    row["dollars"] = round(dollars, 6)
    row["seconds"] = seconds
    row["passes"] = passes_rule(entries, samples)


def measure(
    row: dict,
    samples: list[str],
    table_samples: list[str],
    samples_root: Path,
    runs_root: Path,
    rooms: dict[str, tuple | None],
    gateway: Gateway | None,
    ledger: Ledger | None,
    grader: Callable[[Path, Path, Path, str], dict] | None,
) -> None:
    """Runs one model's two passes on every sample of samples and fills its row.

    The row is read off disk over table_samples, which is every sample the table covers, so a
    run restricted to one sample keeps the samples it did not write.
    """
    for sample in samples:
        a_dir, _ = pass_dirs(runs_root, sample, row["slug"])
        run_write(
            samples_root / sample,
            runs_root / sample,
            a_dir,
            row["model"],
            gateway,
            ledger,
            grader,
        )
    fill_row(row, table_samples, runs_root, rooms, required=tuple(samples))


def recount_row(
    row: dict, samples: list[str], runs_root: Path, rooms: dict[str, tuple | None]
) -> None:
    """Rebuilds one row from the pass directories already on disk, with no gateway call. A model
    with no pass on any sample stays the blank row it started as."""
    fill_row(row, samples, runs_root, rooms)


def build_table(samples: list[str], rows: dict[str, dict]) -> dict:
    """The whole cross-sample table, one row per model of the price table."""
    ordered = [rows[model] for tier in TIERS for model in TIERS[tier]]
    passing = [row for row in ordered if row["passes"] is True]
    winner = min(passing, key=lambda row: row["dollars"])["model"] if passing else None
    return {
        "date": datetime.date.today().isoformat(),
        "samples": list(samples),
        "prices": {row["model"]: list(PRICES[row["model"]]) for row in ordered},
        "rows": ordered,
        "winner": winner,
    }


def write_table(runs_root: Path, samples: list[str], table: dict) -> list[Path]:
    """Writes the table into every sample's run directory, the same bytes in each."""
    body = json.dumps(table, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    written = []
    for sample in samples:
        path = runs_root / sample / "write-bakeoff.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        written.append(path)
    return written


def _entry_text(sample: str, entry: dict) -> str:
    """One sample's part of a printed row."""
    parts = [
        f"{sample} recall {entry['recall_a']:g}/{entry['recall_b']:g}",
        f"verify {entry['verifier_a']}/{entry['verifier_b']}",
    ]
    if "rubric_a" in entry:
        parts.append(
            f"rubric {entry['rubric_a']:g}/{entry['rubric_b']:g} spread {entry['spread']:g}"
        )
    return " ".join(parts)


def _samples_text(entries) -> str:
    if entries == NOT_RUN:
        return NOT_RUN
    return "; ".join(_entry_text(sample, entry) for sample, entry in entries.items())


def table_line(row: dict) -> str:
    """One printed line of the table: model, tier, passes, dollars, seconds, then the samples."""
    dollars = row["dollars"]
    seconds = row["seconds"]
    return "  ".join(
        [
            row["model"],
            row["tier"],
            str(row["passes"]),
            NOT_RUN if dollars == NOT_RUN else f"${dollars:.4f}",
            NOT_RUN if seconds == NOT_RUN else f"{seconds:.1f}",
            _samples_text(row["samples"]),
        ]
    )


def print_table(table: dict) -> None:
    """Prints one line per row, then the winner."""
    for row in table["rows"]:
        print(table_line(row))
    print(f"winner: {table['winner'] or 'none'}")


def kept_rows(runs_root: Path, first_sample: str) -> dict[str, dict]:
    """The rows of runs_root/<first_sample>/write-bakeoff.json, by model, or {} when absent."""
    path = runs_root / first_sample / "write-bakeoff.json"
    if not path.exists():
        return {}
    table = json.loads(path.read_text(encoding="utf-8"))
    return {row["model"]: row for row in table["rows"]}


def table_samples_of(kept: dict[str, dict], samples: list[str]) -> list[str]:
    """Every sample the written table covers: the run's own and the ones the kept rows hold.

    A run restricted to one sample leaves the other samples' passes on disk, so the table it
    writes still carries them. The order is the order of SAMPLES, and a sample outside that
    tuple comes after them in the order it was met.
    """
    found = list(samples)
    for row in kept.values():
        entries = row.get("samples")
        if not isinstance(entries, dict):
            continue
        for sample in entries:
            if sample not in found:
                found.append(sample)
    known = [sample for sample in SAMPLES if sample in found]
    return known + [sample for sample in found if sample not in known]


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Reads the command line of one bake-off."""
    parser = argparse.ArgumentParser(prog="python -m rlm.writebakeoff")
    parser.add_argument("samples_root")
    parser.add_argument("runs_root")
    parser.add_argument("--samples", nargs="+", default=list(SAMPLES))
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="the model ids to try; without it every model of the price table",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--recount",
        action="store_true",
        help="rebuild every row from the pass directories on disk, with no call and no ledger line",
    )
    return parser.parse_args(argv)


def main(
    argv: list[str],
    gateway: Gateway | None = None,
    ledger: Ledger | None = None,
    grader: Callable[[Path, Path, Path, str], dict] | None = None,
) -> int:
    """Runs the bake-off over the chosen models and samples and writes the table."""
    args = parse_args(argv)
    if args.recount and (args.dry_run or args.models is not None):
        print("--recount takes no --dry-run and no --models")
        return 2

    samples_root = Path(args.samples_root)
    runs_root = Path(args.runs_root)
    samples = list(args.samples)

    if args.recount:
        rooms = {sample: sample_room(runs_root, sample) for sample in samples}
        rows = {model: blank_row(model, tier) for tier in TIERS for model in TIERS[tier]}
        for model in rows:
            recount_row(rows[model], samples, runs_root, rooms)
        table = build_table(samples, rows)
        write_table(runs_root, samples, table)
        print_table(table)
        return 0

    wanted = None
    if args.models is not None:
        wanted = set(args.models)
        unknown = sorted(wanted - set(PRICES))
        if unknown:
            print("no such model in the price table: " + ", ".join(unknown))
            return 2

    kept = kept_rows(runs_root, samples[0]) if wanted is not None else {}
    table_samples = table_samples_of(kept, samples)
    rooms = {sample: sample_room(runs_root, sample) for sample in table_samples}
    rows = {
        model: kept[model]
        if wanted is not None and model not in wanted and model in kept
        else blank_row(model, tier)
        for tier in TIERS
        for model in TIERS[tier]
    }
    chosen = [
        (tier, model)
        for tier in TIERS
        for model in TIERS[tier]
        if wanted is None or model in wanted
    ]

    estimates = sample_estimates(samples_root, runs_root, samples)
    print("model order: " + ", ".join(model for _, model in chosen))
    for _, model in chosen:
        estimate = model_estimate(estimates, model)
        print(f"{model}: two passes on {len(samples)} samples estimate ${estimate:.4f}")

    if args.dry_run:
        table = build_table(table_samples, rows)
        write_table(runs_root, table_samples, table)
        print_table(table)
        return 0

    if gateway is None:
        gateway = Gateway()

    for tier in TIERS:
        if tier != "flash" and any(rows[model]["passes"] is True for model in rows):
            break
        for one_tier, model in chosen:
            if one_tier != tier:
                continue
            measure(
                rows[model],
                samples,
                table_samples,
                samples_root,
                runs_root,
                rooms,
                gateway,
                ledger,
                grader,
            )
            table = build_table(table_samples, rows)
            write_table(runs_root, table_samples, table)
            print_table(table)
            if tier != "flash" and rows[model]["passes"] is True:
                break

    table = build_table(table_samples, rows)
    write_table(runs_root, table_samples, table)
    print_table(table)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
