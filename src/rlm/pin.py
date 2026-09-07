"""Pins a sample's notes, map, sections, dossier or report and writes the sha256 of every
pinned file into a digests file. Six modes.

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

The --dossiers mode does not read a bake-off winner and copies nothing. It requires
runs/<sample>/dossier.md to exist for every requested sample; a sample missing it is a refusal,
printed with the sample name, and the run stops with exit 1 before a digest is written for any
sample. It only reads each sample's dossier.md as it sits on disk and digests it. The digests go
to tests/phase4-digests.json by default.

The --reports mode reads runs/<sample>/write-bakeoff.json's winner and copies that winner's two
passes into place: pass a's report.md, verify.json and grade.json into runs/<sample>/, with
digest.md, write-summary.json and any report-raw*.txt beside them where the pass wrote them,
and pass b's report.md, verify.json and grade.json into runs/<sample>/b/. A sample whose table
names no winner, or that has no table at all, is a refusal: the message names the sample and
the run stops before anything is copied or written, on any sample. The digests go to
tests/phase5-digests.json by default and hold report.md, verify.json and grade.json.

Nothing here calls a model or writes LEDGER.md; in every mode the run is bytes on disk, never a
rerun.

The digest file holds, per sample, the sha256 of every pinned file, sorted keys, matching how
tests/phase1-digests.json is written. For notes that is every note file (keyed "notes/<name>")
and notes-verify.jsonl; for maps that is map.json alone (keyed "map.json"); for sections that
is sections.jsonl and index.jsonl; for dossiers that is dossier.md alone (keyed "dossier.md");
for reports that is report.md, verify.json and grade.json, keyed by those three names.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

from rlm import bakeoff, writebakeoff

# The three gate samples, in the order a run takes them.
SAMPLES = ("atlas", "northwind", "northstar-dental")

# The files of a winning write pass a and pass b are pinned and digested by.
REPORT_FILES = ("report.md", "verify.json", "grade.json")

# What a winning pass a also carries into place where it wrote them: the digest the model was
# sent, the pass's own summary, and the replies as they came back.
REPORT_EXTRAS = ("digest.md", "write-summary.json")


def default_digests_path(
    maps: bool = False,
    sections: bool = False,
    dossiers: bool = False,
    reports: bool = False,
) -> Path:
    """tests/phase2-digests.json at the repo root, tests/phase3-digests.json when maps is true,
    tests/phase1-digests.json when sections is true, tests/phase4-digests.json when dossiers is
    true, or tests/phase5-digests.json when reports is true. All five sit in the same tests/
    directory, the parent of the rlm package's src."""
    if reports:
        name = "phase5-digests.json"
    elif dossiers:
        name = "phase4-digests.json"
    elif sections:
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


def pin_dossiers(runs_root: Path, samples: list[str], digests_path: Path) -> int:
    """Digests each sample's dossier.md as it already sits on disk. Nothing is copied or removed
    and no bake-off winner is read. A sample missing runs/<sample>/dossier.md is a refusal,
    printed with the sample name, before a digest is written for any sample."""
    for sample in samples:
        if not (runs_root / sample / "dossier.md").exists():
            print(f"{sample}: runs/{sample}/dossier.md missing, nothing digested")
            return 1

    all_digests: dict[str, dict[str, str]] = {}
    for sample in samples:
        dossier_path = runs_root / sample / "dossier.md"
        digest = hashlib.sha256(dossier_path.read_bytes()).hexdigest()
        all_digests[sample] = {"dossier.md": digest}
        print(f"{sample}: dossier.md digested")

    write_digests(digests_path, all_digests)
    return 0


def report_winner_of(sample_dir: Path) -> str | None:
    """The winner named by sample_dir/write-bakeoff.json, or None where there is no table."""
    path = sample_dir / "write-bakeoff.json"
    if not path.exists():
        return None
    table = json.loads(path.read_text(encoding="utf-8"))
    return table.get("winner")


def copy_report_pass(pass_dir: Path, target: Path) -> None:
    """Copies one winning pass's report, verifier record and grade into target.

    The digest, the summary and the raw replies come too where the pass wrote them; pass b
    writes them as well, and copying them is how the second draw stays readable beside the
    first.
    """
    target.mkdir(parents=True, exist_ok=True)
    for name in REPORT_FILES:
        shutil.copy2(pass_dir / name, target / name)
    for name in REPORT_EXTRAS:
        if (pass_dir / name).exists():
            shutil.copy2(pass_dir / name, target / name)
    for path in sorted(pass_dir.glob("report-raw*.txt")):
        shutil.copy2(path, target / path.name)


def report_digests(sample_dir: Path) -> dict[str, str]:
    """The sha256 of the three pinned files, keyed as the digest file names them."""
    return {
        name: hashlib.sha256((sample_dir / name).read_bytes()).hexdigest()
        for name in REPORT_FILES
    }


def pin_reports(runs_root: Path, samples: list[str], digests_path: Path) -> int:
    """Copies each sample's winning write pass a into its run directory and pass b under b/,
    then digests the three pinned files of pass a. A sample whose write-bakeoff.json names no
    winner, or that has no table, is a refusal, printed with the sample name, before anything
    is copied or digested for any sample."""
    winners: dict[str, str] = {}
    for sample in samples:
        winner = report_winner_of(runs_root / sample)
        if not winner:
            print(f"{sample}: write-bakeoff.json names no winner, nothing pinned")
            return 1
        winners[sample] = winner

    all_digests: dict[str, dict[str, str]] = {}
    for sample in samples:
        sample_dir = runs_root / sample
        winner = winners[sample]
        pass_a = sample_dir / "write-bakeoff" / writebakeoff.slug(winner)
        copy_report_pass(pass_a, sample_dir)
        copy_report_pass(pass_a / "b", sample_dir / "b")
        digests = report_digests(sample_dir)
        all_digests[sample] = digests
        print(f"{sample}: winner {winner}, {len(digests)} files pinned")

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
    parser.add_argument("--dossiers", action="store_true")
    parser.add_argument("--reports", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Pins each sample's bake-off winner and writes tests/phase2-digests.json. With
    --from-notes, digests the notes already on disk instead, without a bake-off winner. With
    --maps, digests each sample's map.json already on disk instead, into
    tests/phase3-digests.json by default. With --sections, digests each sample's sections.jsonl
    and index.jsonl already on disk instead, into tests/phase1-digests.json by default. With
    --dossiers, digests each sample's dossier.md already on disk instead, into
    tests/phase4-digests.json by default. With --reports, copies each sample's winning write
    bake-off pass a into the run directory and pass b under b/, and digests the three pinned
    files into tests/phase5-digests.json by default."""
    args = parse_args(argv)
    runs_root = Path(args.runs_root)

    if args.reports:
        digests_path = (
            Path(args.digests) if args.digests else default_digests_path(reports=True)
        )
        return pin_reports(runs_root, args.samples, digests_path)

    if args.dossiers:
        digests_path = (
            Path(args.digests) if args.digests else default_digests_path(dossiers=True)
        )
        return pin_dossiers(runs_root, args.samples, digests_path)

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
