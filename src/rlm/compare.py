"""Puts the RLM skill's answer on sample 1 beside ours.

Two subcommands.

`prepare <sample_dir> <out_dir>` builds `<out_dir>/corpus.txt` out of the pinned run's
`sections.jsonl`, one header per document naming the DR id the key gives it and the path it
was read from, then every section text of that document in ingest's order. The corpus is the
same bytes every time it is built from the same sections. `prepare` also copies
`reference/rlm-skill/skill/` into `<checkout>/.claude/skills/rlm/`, where the checkout is the
repository the running code sits in, so that `/rlm` finds the skill.

`grade <sample_dir> <ours_run_dir> <rlm_run_dir>` grades the two reports the session saved,
`report.md` and `b/report.md`, with `rlm.grade.grade`, and writes `compare.json`,
`manifest.json` and `tests/phase7-rlm-digests.json`.

Nothing here opens a socket, reads OPENROUTER_API_KEY or writes LEDGER.md. `rlm.grade` calls a
Claude subagent on the subscription, the same call phase 5 grades with, and books nothing.

How the numbers are read.

- The RLM's score a and score b are the two grades of the two reports; its spread is the
  distance between them; its recall a is the first report's planted-fact recall; its dollars
  are zero, because the skill runs on the Claude Code subscription.
- Ours are read from the pinned run: `grade.json` carries score, score b, spread and recall.
  Our dollars are the sum of every phase 5 row of `LEDGER.md` for the sample.
- Our seconds are the wall time of the whole chain: `ingest`, `map` and `dossier` are timed
  once here in a temporary directory, and the notes and write stages contribute the seconds
  their own summaries recorded, because rerunning them would call the gateway. The pinned
  notes are copied into the temporary directory so that map and dossier have what they read;
  the copy is not timed.

The manifest contract.

`manifest.json` names the sample, the skill commit, the sha256 of the corpus, the root model,
the leaf model and the two audit run ids. The root is the session that ran `/rlm`; the leaf is
the skill's own `claude -p`. Code cannot see either from inside, so they are read in this
order:

1. `<rlm_run_dir>/session.json`, if the session left one. Whatever it names is taken as
   written: `root_model`, `leaf_model`, `audit_runs` (the two run ids, pass a first) and
   `seconds`.
2. Otherwise the models come from the environment variables `RLM_ROOT_MODEL` and
   `RLM_SUB_MODEL`, and then from DEFAULT_ROOT_MODEL and DEFAULT_LEAF_MODEL.
3. Otherwise the audit run ids and the RLM's seconds come from the skill's own manifests under
   `<checkout>/.claude/rlm_runs/*/manifest.json`. A manifest is one of ours when its
   `context_file_sha256` is the corpus's. They are ordered oldest first by `initialized_at`,
   and the first two are pass a and pass b. Each run's seconds are its `updated_at` less its
   `initialized_at`, which is the time from loading the context to the last REPL step.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from rlm import dossier as dossierer
from rlm import grade as grader
from rlm import ingest as ingester
from rlm import map as mapper
from rlm.gateway import Ledger
from rlm.key import load_key

# The upstream commit the skill is pinned at, and where it sits in this repository.
SKILL_COMMIT = "0039c005c990daeffef818e5e090279b7ac20874"

# The phase this slice belongs to and the phase whose ledger rows are our dollars.
PHASE = 7
OURS_PHASE = 5

# The mark a corpus header opens with, and the header itself.
HEADER_MARK = "=== "
HEADER = HEADER_MARK + "{doc} | {path} ==="

# The root ran the session; the leaf is the skill's claude -p, the leaf tier of the winner's run.
DEFAULT_ROOT_MODEL = "claude-opus-5[1m]"
DEFAULT_LEAF_MODEL = "claude-sonnet-5"

# Where the skill's audit replay packages land, under the checkout the skill was run from.
AUDIT_RUNS = ".claude/rlm_runs"

# The four files the digests pin, and where the digests are written.
GRADED_FILES = ("report.md", "grade.json", "b/report.md", "b/grade.json")
DIGESTS_NAME = "phase7-rlm-digests.json"


def checkout() -> Path:
    """The repository root of the running code, the directory holding src/rlm."""
    return Path(__file__).resolve().parents[2]


SKILL_SOURCE = checkout() / "reference" / "rlm-skill" / "skill"


def skill_target() -> Path:
    """Where prepare installs the skill so that the session's /rlm finds it."""
    return checkout() / ".claude" / "skills" / "rlm"


def read_jsonl(path: Path) -> list[dict]:
    """Every record of a JSON lines file, in file order."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def read_json(path: Path) -> dict:
    """One JSON object, or an empty dict where the file is not there."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_of(path: Path) -> str:
    """The sha256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spread(score_a: float, score_b: float) -> float:
    """The distance between two scores, without a sign."""
    return abs(float(score_a) - float(score_b))


# ---------------------------------------------------------------- the corpus


def header(doc_id: str, path: str) -> str:
    """The one line a document opens with, naming its DR id and the path it was read from."""
    return HEADER.format(doc=doc_id, path=path)


def body(text: str) -> str:
    """One section's text as the corpus writes it.

    Carriage returns become newlines, because a mail document carries them and the corpus is
    one LF text file, and trailing whitespace is cut.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip()


def build_corpus(documents: dict[str, str], sections: list[dict]) -> str:
    """Returns the corpus text of a room's sections, under one header per document.

    documents maps a DR id to the path the key gives it. The sections are taken in the order
    they arrive in, which is the order ingest wrote them. A section whose document the key does
    not name has no header to sit under and is left out. Each section's text is written by the
    rule of body, one section to a line block, and a blank line separates documents.
    Nothing here reads a clock, a set order or the file system, so the same sections give the
    same string every time.
    """
    ids_by_path = {path: doc_id for doc_id, path in documents.items()}
    parts: list[str] = []
    current: str | None = None
    for section in sections:
        doc_id = ids_by_path.get(section["doc"])
        if doc_id is None:
            continue
        if doc_id != current:
            if current is not None:
                parts.append("\n")
            parts.append(header(doc_id, section["doc"]) + "\n")
            current = doc_id
        parts.append(body(section["text"]) + "\n")
    return "".join(parts)


def write_corpus(sample_dir: Path, ours_run_dir: Path, out_dir: Path) -> Path:
    """Writes out_dir / corpus.txt from the sample's key and the pinned run's sections."""
    key = load_key(sample_dir)
    sections = read_jsonl(ours_run_dir / "sections.jsonl")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "corpus.txt"
    path.write_text(build_corpus(key.documents, sections), encoding="utf-8", newline="\n")
    return path


def install_skill(source: Path, target: Path) -> Path:
    """Copies the skill tree to target, replacing whatever an earlier install left there."""
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    return target


def pinned_run_dir(sample_dir: Path) -> Path:
    """The pinned run of a sample in this checkout, runs/<sample>/."""
    return checkout() / "runs" / load_key(sample_dir).sample


def prepare(
    sample_dir: Path, out_dir: Path, ours_run_dir: Path | None = None
) -> tuple[Path, Path]:
    """Builds the corpus and installs the skill, and returns both paths."""
    if ours_run_dir is None:
        ours_run_dir = pinned_run_dir(sample_dir)
    corpus = write_corpus(sample_dir, ours_run_dir, out_dir)
    installed = install_skill(SKILL_SOURCE, skill_target())
    return corpus, installed


# ---------------------------------------------------------------- what ran, and for how long


def models(note: dict) -> dict[str, str]:
    """The root and leaf model ids: the session note first, then the environment, then the
    defaults."""
    return {
        "root_model": note.get("root_model")
        or os.environ.get("RLM_ROOT_MODEL")
        or DEFAULT_ROOT_MODEL,
        "leaf_model": note.get("leaf_model")
        or os.environ.get("RLM_SUB_MODEL")
        or DEFAULT_LEAF_MODEL,
    }


def audit_manifests(corpus: Path, runs_root: Path) -> list[dict]:
    """The skill's audit manifests over this corpus, oldest first.

    A manifest is over this corpus when its context_file_sha256 is the corpus's sha256.
    """
    if not runs_root.is_dir():
        return []
    wanted = sha256_of(corpus)
    found = []
    for path in sorted(runs_root.glob("*/manifest.json")):
        manifest = read_json(path)
        if manifest.get("context_file_sha256") == wanted:
            found.append(manifest)
    return sorted(found, key=lambda manifest: manifest.get("initialized_at", 0.0))


def audit_run_ids(manifests: list[dict], note: dict) -> dict[str, str]:
    """The two audit run ids, pass a first, from the session note or from the manifests."""
    named = list(note.get("audit_runs") or [])
    if not named:
        named = [manifest.get("run_id", "") for manifest in manifests]
    named = (named + ["", ""])[:2]
    return {"a": named[0], "b": named[1]}


def rlm_seconds(manifests: list[dict], note: dict) -> float:
    """The wall time of the two RLM runs, from the session note or from the manifests."""
    if "seconds" in note:
        return float(note["seconds"])
    return sum(
        float(manifest.get("updated_at", 0.0)) - float(manifest.get("initialized_at", 0.0))
        for manifest in manifests
    )


def time_free_stages(sample_dir: Path, ours_run_dir: Path) -> dict[str, float]:
    """Times ingest, map and dossier once in a temporary directory and returns their seconds.

    The pinned notes are copied in between ingest and map, because map and dossier read them
    and rerunning the notes stage would call the gateway. The copy is not timed.
    """
    seconds = {}
    with tempfile.TemporaryDirectory() as scratch:
        run_dir = Path(scratch) / "run"
        started = time.monotonic()
        ingester.ingest(sample_dir, run_dir)
        seconds["ingest"] = time.monotonic() - started

        notes = ours_run_dir / "notes"
        if notes.is_dir():
            shutil.copytree(notes, run_dir / "notes")

        started = time.monotonic()
        mapper.write_map(mapper.build_map(sample_dir, run_dir), run_dir)
        seconds["map"] = time.monotonic() - started

        started = time.monotonic()
        dossierer.write_dossier(dossierer.build_dossier(sample_dir, run_dir), run_dir)
        seconds["dossier"] = time.monotonic() - started
    return seconds


def ledger_dollars(rows: list[dict], sample: str, phase: int) -> float:
    """Sums the dollars of every ledger row of one sample and one phase."""
    return sum(
        row["dollars"] for row in rows if row["sample"] == sample and row["phase"] == str(phase)
    )


# ---------------------------------------------------------------- the two sides


def our_numbers(sample_dir: Path, ours_run_dir: Path, ledger_path: Path) -> dict:
    """The six numbers of our pinned run: two scores, the spread, recall a, seconds and dollars."""
    graded = read_json(ours_run_dir / "grade.json")
    score_a = float(graded.get("score", 0.0))
    score_b = float(graded.get("score_b", score_a))
    stages = time_free_stages(sample_dir, ours_run_dir)
    seconds = sum(stages.values())
    for name in ("notes-summary.json", "write-summary.json"):
        seconds += float(read_json(ours_run_dir / name).get("seconds", 0.0))
    rows = Ledger(ledger_path).rows() if ledger_path.exists() else []
    return {
        "score_a": score_a,
        "score_b": score_b,
        "spread": float(graded.get("spread", spread(score_a, score_b))),
        "recall_a": float(graded.get("recall", 0.0)),
        "seconds": seconds,
        "dollars": ledger_dollars(rows, load_key(sample_dir).sample, OURS_PHASE),
    }


def grade_reports(sample_dir: Path, rlm_run_dir: Path) -> tuple[dict, dict]:
    """Grades report.md and b/report.md into grade.json and b/grade.json, and returns both."""
    first = grader.grade(sample_dir, rlm_run_dir / "report.md", rlm_run_dir, "grade.json")
    second = grader.grade(
        sample_dir, rlm_run_dir / "b" / "report.md", rlm_run_dir / "b", "grade.json"
    )
    return first, second


def rlm_numbers(first: dict, second: dict, seconds: float) -> dict:
    """The six numbers of the RLM's two runs. Its dollars are zero: it ran on the subscription."""
    score_a = float(first["score"])
    score_b = float(second["score"])
    return {
        "score_a": score_a,
        "score_b": score_b,
        "spread": spread(score_a, score_b),
        "recall_a": float(first["recall"]),
        "seconds": seconds,
        "dollars": 0.0,
    }


def digests_of(rlm_run_dir: Path) -> dict[str, str]:
    """The sha256 of the two reports and the two grades."""
    return {name: sha256_of(rlm_run_dir / name) for name in GRADED_FILES}


def write_json(path: Path, record: dict) -> Path:
    """Writes one JSON object, indented, with one trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def grade(sample_dir: Path, ours_run_dir: Path, rlm_run_dir: Path) -> dict:
    """Grades both RLM reports and writes compare.json, manifest.json and the digests."""
    sample = load_key(sample_dir).sample
    note = read_json(rlm_run_dir / "session.json")
    corpus = rlm_run_dir / "corpus.txt"
    manifests = audit_manifests(corpus, checkout() / AUDIT_RUNS)

    first, second = grade_reports(sample_dir, rlm_run_dir)
    record = {
        "sample": sample,
        "rlm": rlm_numbers(first, second, rlm_seconds(manifests, note)),
        "ours": our_numbers(sample_dir, ours_run_dir, checkout() / "LEDGER.md"),
    }
    write_json(rlm_run_dir / "compare.json", record)

    manifest = {
        "sample": sample,
        "skill_commit": SKILL_COMMIT,
        "corpus_sha256": sha256_of(corpus),
        "audit_runs": audit_run_ids(manifests, note),
    }
    manifest.update(models(note))
    write_json(rlm_run_dir / "manifest.json", manifest)

    write_json(checkout() / "tests" / DIGESTS_NAME, {rlm_run_dir.name: digests_of(rlm_run_dir)})
    return record


# ---------------------------------------------------------------- the command line


def readout_line(record: dict) -> str:
    """One line: the RLM's two scores, its spread, its seconds and its dollars, against ours."""
    rlm, ours = record["rlm"], record["ours"]
    return (
        f"rlm {rlm['score_a']:g} / {rlm['score_b']:g}, spread {rlm['spread']:g}, "
        f"seconds {rlm['seconds']:.1f}, ${rlm['dollars']:.4f} against "
        f"ours {ours['score_a']:g} / {ours['score_b']:g}, spread {ours['spread']:g}, "
        f"seconds {ours['seconds']:.1f}, ${ours['dollars']:.4f}"
    )


USAGE = (
    "usage: python -m rlm.compare prepare <sample_dir> <out_dir>\n"
    "       python -m rlm.compare grade <sample_dir> <ours_run_dir> <rlm_run_dir>"
)


def main(argv: list[str]) -> int:
    """Runs one subcommand and prints what it wrote."""
    if len(argv) == 3 and argv[0] == "prepare":
        corpus, installed = prepare(Path(argv[1]), Path(argv[2]))
        text = corpus.read_text(encoding="utf-8")
        print(
            f"corpus {corpus} {corpus.stat().st_size} bytes {len(text)} chars, "
            f"skill installed at {installed}"
        )
        return 0
    if len(argv) == 4 and argv[0] == "grade":
        print(readout_line(grade(Path(argv[1]), Path(argv[2]), Path(argv[3]))))
        return 0
    print(USAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
