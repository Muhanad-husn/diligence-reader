"""Pins a sample's notes, map or sections and writes the sha256 of every pinned file into a
digests file. Four modes.

The default mode reads runs/<sample>/bakeoff.json's winner and copies that winner's pass a byte
for byte from runs/<sample>/bakeoff/<slug>/a/ into runs/<sample>/: notes/ replaces the sample's
notes/ (removed first when present), notes-verify.jsonl and notes-summary.json replace the
sample's copies, and notes-raw/ is copied the same way when the winning pass wrote one. A sample
with no winner is a refusal: the message names the sample and the run stops before anything is
copied or written, on any sample. The digests go to tests/phase2-digests.json by default.

The --from-notes mode does not read a bake-off winner and copies nothing. It requires
runs/<sample>/notes to be a directory and runs/<sample>/notes-verify.jsonl to exist; a sample
missing either is a refusal, printed with the sample name, and the run stops with exit 1 before
a digest is written for any sample. It only reads the notes already on disk and digests them.
The digests also go to tests/phase2-digests.json by default.

The --maps mode does not read a bake-off winner and copies nothing. It requires
runs/<sample>/map.json to exist for every requested sample; a sample missing it is a refusal,
printed with the sample name, and the run stops with exit 1 before a digest is written for any
sample. It only reads each sample's map.json as it sits on disk and digests it. The digests go
to tests/phase3-digests.json by default.

The --sections mode does not read a bake-off winner and copies nothing. It requires
runs/<sample>/sections.jsonl and runs/<sample>/index.jsonl to both exist for every requested
sample; a sample missing either is a refusal, printed with the sample name, and the run stops
with exit 1 before a digest is written for any sample. It only reads each sample's sections.jsonl
and index.jsonl as they sit on disk and digests them. The digests go to tests/phase1-digests.json
by default.

Nothing here calls a model or writes LEDGER.md; in every mode the run is bytes on disk, never a
rerun.

The digest file holds, per sample, the sha256 of every pinned file, sorted keys, matching how
tests/phase1-digests.json is written. For notes that is every note file (keyed "notes/<name>")
and notes-verify.jsonl; for maps that is map.json alone (keyed "map.json").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

from rlm import bakeoff

# The three gate samples, in the order a run takes them.
SAMPLES = ("atlas", "northwind", "northstar-dental")


def default_digests_path(maps: bool = False, sections: bool = False) -> Path:
    """tests/phase2-digests.json at the repo root, or tests/phase3-digests.json when maps is
    true, or tests/phase1-digests.json when sections is true. All three sit in the same tests/
    directory, the parent of the rlm package's src."""
    if sections:
        name = "phase1-digests.json"
    elif maps:
        name = "phase3-digests.json"
    else:
        name = "phase2-digests.json"
    return Path(__file__).resolve().parents[2] / "tests" / name


def winner_of(sample_dir: Path) -> str | None:
    """The winner named by sample_dir/bakeoff.json, or None."""
    table = json.loads((sample_dir / "bakeoff.json").read_text(encoding="utf-8"))
    return table.get("winner")


def copy_pass(pass_dir: Path, sample_dir: Path) -> None:
    """Copies one winning pass a's files into sample_dir, replacing what was there."""
    notes_dir = sample_dir / "notes"
    if notes_dir.exists():
        shutil.rmtree(notes_dir)
    shutil.copytree(pass_dir / "notes", notes_dir)

    shutil.copy2(pass_dir / "notes-verify.jsonl", sample_dir / "notes-verify.jsonl")
    shutil.copy2(pass_dir / "notes-summary.json", sample_dir / "notes-summary.json")

    raw_source = pass_dir / "notes-raw"
    if raw_source.is_dir():
        raw_target = sample_dir / "notes-raw"
        if raw_target.exists():
            shutil.rmtree(raw_target)
        shutil.copytree(raw_source, raw_target)


def note_digests(sample_dir: Path) -> dict[str, str]:
    """The sha256 of every pinned note file and the verify log, keyed as the digest file names
    them."""
    digests: dict[str, str] = {}
    for path in sorted((sample_dir / "notes").glob("*.json")):
        digests[f"notes/{path.name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    digests["notes-verify.jsonl"] = hashlib.sha256(
        (sample_dir / "notes-verify.jsonl").read_bytes()
    ).hexdigest()
    return digests


def pin_sample(runs_root: Path, sample: str, winner: str) -> dict[str, str]:
    """Copies one sample's winning pass a into place and returns its file digests."""
    sample_dir = runs_root / sample
    pass_dir = sample_dir / "bakeoff" / bakeoff.slug(winner) / "a"
    copy_pass(pass_dir, sample_dir)
    return note_digests(sample_dir)


def write_digests(digests_path: Path, all_digests: dict[str, dict[str, str]]) -> None:
    """Writes every sample's digests to digests_path, sorted keys, creating its parent."""
    digests_path.parent.mkdir(parents=True, exist_ok=True)
    digests_path.write_text(
        json.dumps(all_digests, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def pin_from_notes(runs_root: Path, samples: list[str], digests_path: Path) -> int:
    """Digests each sample's notes/ and notes-verify.jsonl as they already sit on disk. Nothing
    is copied or removed. A sample missing notes/ or notes-verify.jsonl is a refusal, printed
    with the sample name, before a digest is written for any sample."""
    for sample in samples:
        sample_dir = runs_root / sample
        has_notes_dir = (sample_dir / "notes").is_dir()
        has_verify = (sample_dir / "notes-verify.jsonl").exists()
        if not has_notes_dir or not has_verify:
            print(f"{sample}: runs/{sample}/notes or notes-verify.jsonl missing, nothing digested")
            return 1

    all_digests: dict[str, dict[str, str]] = {}
    for sample in samples:
        digests = note_digests(runs_root / sample)
        all_digests[sample] = digests
        note_count = len(digests) - 1
        print(f"{sample}: {note_count} notes, {len(digests)} digests")

    write_digests(digests_path, all_digests)
    return 0


def pin_maps(runs_root: Path, samples: list[str], digests_path: Path) -> int:
    """Digests each sample's map.json as it already sits on disk. Nothing is copied or removed
    and no bake-off winner is read. A sample missing runs/<sample>/map.json is a refusal,
    printed with the sample name, before a digest is written for any sample."""
    for sample in samples:
        if not (runs_root / sample / "map.json").exists():
            print(f"{sample}: runs/{sample}/map.json missing, nothing digested")
            return 1

    all_digests: dict[str, dict[str, str]] = {}
    for sample in samples:
        map_path = runs_root / sample / "map.json"
        digest = hashlib.sha256(map_path.read_bytes()).hexdigest()
        all_digests[sample] = {"map.json": digest}
        print(f"{sample}: map.json digested")

    write_digests(digests_path, all_digests)
    return 0


def pin_sections(runs_root: Path, samples: list[str], digests_path: Path) -> int:
    """Digests each sample's sections.jsonl and index.jsonl as they already sit on disk.
    Nothing is copied or removed and no bake-off winner is read. A sample missing either file
    is a refusal, printed with the sample name, before a digest is written for any sample."""
    for sample in samples:
        sample_dir = runs_root / sample
        has_sections = (sample_dir / "sections.jsonl").exists()
        has_index = (sample_dir / "index.jsonl").exists()
        if not has_sections or not has_index:
            print(f"{sample}: runs/{sample}/sections.jsonl or index.jsonl missing, nothing digested")
            return 1

    all_digests: dict[str, dict[str, str]] = {}
    for sample in samples:
        sample_dir = runs_root / sample
        sections_digest = hashlib.sha256((sample_dir / "sections.jsonl").read_bytes()).hexdigest()
        index_digest = hashlib.sha256((sample_dir / "index.jsonl").read_bytes()).hexdigest()
        all_digests[sample] = {"sections.jsonl": sections_digest, "index.jsonl": index_digest}
        print(f"{sample}: sections.jsonl and index.jsonl digested")

    write_digests(digests_path, all_digests)
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Reads the command line of one pin run."""
    parser = argparse.ArgumentParser(prog="python -m rlm.pin")
    parser.add_argument("runs_root")
    parser.add_argument("--samples", nargs="+", default=list(SAMPLES))
    parser.add_argument("--digests", default=None)
    parser.add_argument("--from-notes", action="store_true")
    parser.add_argument("--maps", action="store_true")
    parser.add_argument("--sections", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Pins each sample's bake-off winner and writes tests/phase2-digests.json. With
    --from-notes, digests the notes already on disk instead, without a bake-off winner. With
    --maps, digests each sample's map.json already on disk instead, into
    tests/phase3-digests.json by default. With --sections, digests each sample's sections.jsonl
    and index.jsonl already on disk instead, into tests/phase1-digests.json by default."""
    args = parse_args(argv)
    runs_root = Path(args.runs_root)

    if args.sections:
        digests_path = (
            Path(args.digests) if args.digests else default_digests_path(sections=True)
        )
        return pin_sections(runs_root, args.samples, digests_path)

    if args.maps:
        digests_path = Path(args.digests) if args.digests else default_digests_path(maps=True)
        return pin_maps(runs_root, args.samples, digests_path)

    digests_path = Path(args.digests) if args.digests else default_digests_path()

    if args.from_notes:
        return pin_from_notes(runs_root, args.samples, digests_path)

    winners: dict[str, str] = {}
    for sample in args.samples:
        winner = winner_of(runs_root / sample)
        if not winner:
            print(f"{sample}: bakeoff.json names no winner, nothing pinned")
            return 1
        winners[sample] = winner

    all_digests: dict[str, dict[str, str]] = {}
    for sample in args.samples:
        winner = winners[sample]
        digests = pin_sample(runs_root, sample, winner)
        all_digests[sample] = digests
        notes_copied = len(digests) - 1
        print(f"{sample}: winner {winner}, {notes_copied} notes copied, {len(digests)} digests")

    write_digests(digests_path, all_digests)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
