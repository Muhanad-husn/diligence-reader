"""Runs the candidate models over the samples and writes the table that names the winner.

A model earns its two full passes by clearing a probe first: the few documents of a sample that
carry the facts a note pass must not miss, noted once, checked against the key. A model that
misses one probe fact anywhere is failed there and runs no full pass, so a model that cannot do
the work costs a cent instead of a dollar. The probe of every probed sample still runs, so the
row says what the model misses everywhere.

A model that clears every probe runs pass a and pass b over every document of every sample of
the run, through rlm.notes, into runs/<sample>/bakeoff/<model slug>/<pass>/. Recall is measured
against the sample's key: a planted fact is recalled when its words are inside one verified
quote of a note of one of its own documents, both sides folded the same way. The row carries
the probe, whether the model passes, the dollars and seconds of everything it ran, the
agreement between the two passes and the recall of each.

Models run cheapest first inside a tier, the flash tier before the pro tier. The pro tier is
skipped when a flash model passes everywhere, and stops at the first pro model that passes.
The table is written after each model, so a run that dies part way leaves a readable artefact,
and it is written to runs/<sample>/bakeoff.json for every sample of the run, the same bytes in
each. The winner is the passing row with the lowest measured dollars.

Every pass calls rlm.notes.main, which opens its own ledger batch, so LEDGER.md gains one line
per probe and per pass per sample per model. Nothing here writes LEDGER.md.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

from rlm import notes
from rlm.gateway import PRICES, Gateway, Ledger, estimate_tokens, price
from rlm.key import Key, load_key

PHASE = notes.PHASE

# What a field of a row says before it is measured.
NOT_RUN = "not run"

# The three gate samples, in the order a run takes them.
SAMPLES = ("atlas", "northwind", "northstar-dental")

# One full note pass on sample 1, as PLAN.md section 5 sizes it: the yardstick a tier is
# ordered by.
PASS_TOKENS = (90_000, 60_000)

# The measured fields of a row, in the order the printed table takes them.
MEASURED = ("probe", "passes", "dollars", "agreement", "recall", "seconds")


def _ordered(*models: str) -> tuple[str, ...]:
    """One tier, cheapest first at the cost of a full pass."""
    return tuple(sorted(models, key=lambda model: price(model, *PASS_TOKENS)))


TIERS: dict[str, tuple[str, ...]] = {
    "flash": _ordered(
        "deepseek/deepseek-v4-flash-0731",
        "z-ai/glm-5.3-flash",
        "openai/gpt-5.6-luna",
    ),
    "pro": _ordered("deepseek/deepseek-v4-pro", "z-ai/glm-5.3"),
}

# The documents a model notes before it earns two full passes, by sample. A name is a document
# id or its path in the key; rlm.notes takes either.
PROBE: dict[str, tuple[str, ...]] = {
    "atlas": ("DR-081", "DR-082", "DR-074", "DR-035", "DR-029", "DR-088"),
    "northwind": ("sample_data_room/Northwind_Logistics/cap_table_summary.pdf.md",),
}


def slug(model: str) -> str:
    """The part of a model id after the last slash, used as its directory name."""
    return model.rsplit("/", 1)[-1]


def fold(text: str) -> str:
    """The fold both sides of the recall check take: whitespace, quotes, marks, then case."""
    return notes.straighten(text).casefold()


def phase_facts(key: Key) -> list:
    """The planted facts of a key that this phase's artefact answers for."""
    return [fact for fact in key.facts if fact.phase == PHASE]


def probe_facts(sample: str, key: Key) -> set[str]:
    """The phase facts of a sample whose documents are all inside its probe set.

    A fact whose evidence sits partly outside the probe cannot be judged by the probe, so it is
    left out. The empty set for a sample with no probe.
    """
    chosen = PROBE.get(sample)
    if not chosen:
        return set()
    ids_by_path = {path: doc_id for doc_id, path in key.documents.items()}
    inside = {ids_by_path.get(name, name) for name in chosen}
    return {fact.id for fact in phase_facts(key) if set(fact.documents) <= inside}


def recall(notes_dir: Path, key: Key, fact_ids: set[str] | None = None) -> dict[str, bool]:
    """Says, per planted fact, whether a note of one of its own documents quotes it.

    Reads every note under notes_dir. A fact is recalled when its folded value is inside the
    folded quote of one item of one of the four quoted fields. Restricted to fact_ids when
    given, otherwise every phase fact of the key, recalled or not.
    """
    quotes_by_doc: dict[str, list[str]] = {}
    for path in sorted(Path(notes_dir).glob("*.json")):
        note = json.loads(path.read_text(encoding="utf-8"))
        found = quotes_by_doc.setdefault(note["doc"], [])
        for field in notes.QUOTED_FIELDS:
            for item in note.get(field) or []:
                found.append(fold(item["quote"]))
    hits: dict[str, bool] = {}
    for fact in phase_facts(key):
        if fact_ids is not None and fact.id not in fact_ids:
            continue
        wanted = fold(fact.value)
        paths = [key.documents[doc_id] for doc_id in fact.documents]
        hits[fact.id] = any(
            wanted in quote for path in paths for quote in quotes_by_doc.get(path, [])
        )
    return hits


def blank_row(model: str, tier: str) -> dict:
    """One row of the table before anything is measured."""
    row = {"model": model, "slug": slug(model), "tier": tier}
    row.update({field: NOT_RUN for field in MEASURED})
    return row


def kept_rows(runs_root: Path, first_sample: str) -> dict[str, dict]:
    """The rows of runs_root/<first_sample>/bakeoff.json, by model, or {} when it is absent."""
    path = runs_root / first_sample / "bakeoff.json"
    if not path.exists():
        return {}
    table = json.loads(path.read_text(encoding="utf-8"))
    return {row["model"]: row for row in table["rows"]}


def pass_estimate(
    sections_by_doc: dict[str, list[dict]], key: Key, only: tuple[str, ...] = ()
) -> tuple[int, int]:
    """The tokens one pass sends and is capped at, counted as rlm.notes counts them."""
    ids_by_path = {path: doc_id for doc_id, path in key.documents.items()}
    if only:
        wanted = {ids_by_path.get(name, name) for name in only}
        paths = [path for doc_id, path in key.documents.items() if doc_id in wanted]
    else:
        paths = list(key.documents.values())
    sections = [sections_by_doc[path] for path in paths if sections_by_doc.get(path)]
    tokens_in = sum(
        estimate_tokens("\n".join(message["content"] for message in notes.build_messages(one)))
        for one in sections
    )
    return tokens_in, notes.MAX_OUTPUT_TOKENS * len(sections)


def sample_estimates(samples: list[str], keys: dict[str, Key], runs_root: Path) -> dict[str, dict]:
    """The tokens of one probe and one full pass per sample, read once."""
    found = {}
    for sample in samples:
        sections_by_doc = notes.read_sections(runs_root / sample)
        entry = {"pass": pass_estimate(sections_by_doc, keys[sample])}
        if sample in PROBE:
            entry["probe"] = pass_estimate(sections_by_doc, keys[sample], PROBE[sample])
        found[sample] = entry
    return found


def model_estimate(estimates: dict[str, dict], model: str) -> float:
    """What one model costs at the table's price if it clears every probe and runs both passes."""
    dollars = 0.0
    for entry in estimates.values():
        if "probe" in entry:
            dollars += price(model, *entry["probe"])
        dollars += 2 * price(model, *entry["pass"])
    return dollars


def run_pass(
    sample_dir: Path,
    run_dir: Path,
    out_dir: Path,
    model: str,
    pass_name: str,
    only: tuple[str, ...],
    gateway: Gateway | None,
    ledger: Ledger | None,
) -> dict:
    """Notes the chosen documents into out_dir and returns that pass's summary."""
    argv = [
        str(sample_dir),
        str(run_dir),
        "--model",
        model,
        "--pass",
        pass_name,
        "--out",
        str(out_dir),
    ]
    for name in only:
        argv.extend(["--only", name])
    code = notes.main(argv, gateway=gateway, ledger=ledger)
    if code != 0:
        raise ValueError(f"the pass on {sample_dir.name} refused with code {code}")
    return json.loads((out_dir / "notes-summary.json").read_text(encoding="utf-8"))


def measure(
    row: dict,
    samples: list[str],
    keys: dict[str, Key],
    samples_root: Path,
    runs_root: Path,
    gateway: Gateway | None,
    ledger: Ledger | None,
) -> None:
    """Probes one model, runs its two passes when the probe is clean, and fills its row."""
    model = row["model"]
    dollars = 0.0
    seconds = 0.0
    probe: dict[str, dict] = {}
    clean = True

    for sample in samples:
        if sample not in PROBE:
            continue
        out_dir = runs_root / sample / "bakeoff" / row["slug"] / "probe"
        summary = run_pass(
            samples_root / sample,
            runs_root / sample,
            out_dir,
            model,
            "a",
            PROBE[sample],
            gateway,
            ledger,
        )
        dollars += summary["dollars"]
        seconds += summary["seconds"]
        found = recall(out_dir / "notes", keys[sample], probe_facts(sample, keys[sample]))
        missed = sorted(fact_id for fact_id, hit in found.items() if not hit)
        probe[sample] = {"hits": len(found) - len(missed), "of": len(found), "missed": missed}
        if missed:
            clean = False

    row["probe"] = probe
    row["dollars"] = round(dollars, 6)
    row["seconds"] = seconds
    if not clean:
        row["passes"] = False
        print(f"{model}: the probe missed a fact, so it runs no full pass")
        return

    agreement: dict[str, float] = {}
    counts: dict[str, dict[str, list[int]]] = {}
    passes = True
    for sample in samples:
        key = keys[sample]
        facts = [fact.id for fact in phase_facts(key)]
        found: dict[str, dict[str, bool]] = {}
        for pass_name in ("a", "b"):
            out_dir = runs_root / sample / "bakeoff" / row["slug"] / pass_name
            summary = run_pass(
                samples_root / sample,
                runs_root / sample,
                out_dir,
                model,
                pass_name,
                (),
                gateway,
                ledger,
            )
            dollars += summary["dollars"]
            seconds += summary["seconds"]
            found[pass_name] = recall(out_dir / "notes", key, None)
        counts[sample] = {
            pass_name: [sum(1 for hit in found[pass_name].values() if hit), len(facts)]
            for pass_name in ("a", "b")
        }
        both = sum(1 for fact_id in facts if found["a"][fact_id] and found["b"][fact_id])
        agreement[sample] = round(both / len(facts), 4) if facts else 0.0
        if both != len(facts):
            passes = False

    row["recall"] = counts
    row["agreement"] = agreement
    row["passes"] = passes
    row["dollars"] = round(dollars, 6)
    row["seconds"] = seconds


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
        path = runs_root / sample / "bakeoff.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        written.append(path)
    return written


def _probe_text(probe) -> str:
    if probe == NOT_RUN:
        return NOT_RUN
    if not probe:
        return "none"
    return ", ".join(f"{sample} {seen['hits']}/{seen['of']}" for sample, seen in probe.items())


def _agreement_text(agreement) -> str:
    if agreement == NOT_RUN:
        return NOT_RUN
    return ", ".join(f"{sample} {share:.2f}" for sample, share in agreement.items())


def table_line(row: dict) -> str:
    """One printed line of the table: model, tier, probe, passes, dollars, agreement, seconds."""
    dollars = row["dollars"]
    seconds = row["seconds"]
    return "  ".join(
        [
            row["model"],
            row["tier"],
            _probe_text(row["probe"]),
            str(row["passes"]),
            NOT_RUN if dollars == NOT_RUN else f"${dollars:.4f}",
            _agreement_text(row["agreement"]),
            NOT_RUN if seconds == NOT_RUN else f"{seconds:.1f}",
        ]
    )


def print_table(table: dict) -> None:
    """Prints one line per row, then the winner."""
    for row in table["rows"]:
        print(table_line(row))
    print(f"winner: {table['winner'] or 'none'}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Reads the command line of one bake-off."""
    parser = argparse.ArgumentParser(prog="python -m rlm.bakeoff")
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
    return parser.parse_args(argv)


def main(argv: list[str], gateway: Gateway | None = None, ledger: Ledger | None = None) -> int:
    """Runs the bake-off over the chosen models and samples and writes the table."""
    args = parse_args(argv)
    samples_root = Path(args.samples_root)
    runs_root = Path(args.runs_root)
    samples = list(args.samples)
    keys = {sample: load_key(samples_root / sample) for sample in samples}

    wanted = None
    if args.models is not None:
        wanted = set(args.models)
        unknown = sorted(wanted - set(PRICES))
        if unknown:
            print("no such model in the price table: " + ", ".join(unknown))
            return 2

    kept = kept_rows(runs_root, samples[0]) if wanted is not None else {}
    rows = {
        model: kept[model] if wanted is not None and model not in wanted and model in kept else blank_row(model, tier)
        for tier in TIERS
        for model in TIERS[tier]
    }
    chosen = [
        (tier, model)
        for tier in TIERS
        for model in TIERS[tier]
        if wanted is None or model in wanted
    ]

    estimates = sample_estimates(samples, keys, runs_root)
    print("model order: " + ", ".join(model for _, model in chosen))
    for _, model in chosen:
        estimate = model_estimate(estimates, model)
        print(f"{model}: probe and two passes on {len(samples)} samples estimate ${estimate:.4f}")

    if args.dry_run:
        table = build_table(samples, rows)
        write_table(runs_root, samples, table)
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
            measure(rows[model], samples, keys, samples_root, runs_root, gateway, ledger)
            table = build_table(samples, rows)
            write_table(runs_root, samples, table)
            print_table(table)
            if tier != "flash" and rows[model]["passes"] is True:
                break

    table = build_table(samples, rows)
    write_table(runs_root, samples, table)
    print_table(table)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
