"""Writes a variant of a sample as a markdown data room with a key by construction.

`python -m rlm.widen <knob> <source sample dir> <target sample dir>` reads the source sample's
pinned `sections.jsonl`, checks its sha256 against `tests/phase1-digests.json`, and hands the
sections to the module `rlm.widen.<knob>`, which returns the variant to write. The knob is
found by import, so a new knob is a new module and nothing here changes.

The variant is one markdown file per document under
`<target>/data_room/<same folder>/<same name>.<ext>.md`, holding one section per block or
table row in ingest's order with a blank line between them, so that ingest reads each section
back as its own section. `key.json` carries the source's ids, required documents, decoys,
answer, rubric and bar, with the `documents` map pointing at the new paths and the facts the
knob returned; a fact the knob drops is listed in `README.md`. `brief.md` is the source's
brief, with one paragraph added only where a knob adds documents.

The run is deterministic: seed 0, no model call, no clock, no socket. Regenerating a variant
into another directory writes the same bytes.

Where the runs live. `--runs` names the directory holding `<source sample>/sections.jsonl` and
defaults to `runs` relative to the working directory. Runs are never copied into a worktree,
so a run from a worktree passes the main checkout's path, `--runs D:/RLM/runs`.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import shutil
import sys
import textwrap
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

# The room every variant writes its documents under, whatever the source sample calls its own.
ROOM = "data_room"

# The pinned artefact a variant is written from, and the file its sha256 is checked against.
SECTIONS = "sections.jsonl"
DIGESTS = "phase1-digests.json"

# The line ending every file of a variant is written with. A variant is committed and read
# back byte for byte, and .gitattributes checks it out this way on any platform.
NEWLINE = "\r\n"

# The column the README's prose wraps at, the width the repository writes its prose in.
WIDTH = 96


@dataclass(frozen=True)
class Source:
    """The sample a variant is written from: its key, its brief and its pinned sections."""

    name: str
    directory: Path
    key: dict
    brief: str
    sections: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class Document:
    """One document of a variant: its key id, its path in the variant and its section texts."""

    id: str
    path: str
    texts: tuple[str, ...]


@dataclass(frozen=True)
class Drop:
    """A fact a knob takes out of the key, and why."""

    id: str
    why: str


@dataclass(frozen=True)
class Variant:
    """What a knob returns: the documents, the facts, the facts it dropped, the brief and the
    section the knob writes about itself in the variant's README.

    `key_fields` are the key's own fields a knob rewrites, merged into the key after the
    documents and the facts, so that a knob that renames the matter can rewrite the rubric.
    """

    knob: str
    documents: tuple[Document, ...]
    facts: tuple[dict, ...]
    drops: tuple[Drop, ...]
    brief: str
    notes: str = ""
    key_fields: dict = field(default_factory=dict)


def render(text: str) -> str:
    """The text of one section as a variant writes it.

    Carriage returns become newlines and every blank line is dropped, because a blank line is
    what separates two sections in a markdown file. Every other character is left alone, so
    markdown emphasis marks in the source stay text and ingest reads them back as they are.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line for line in lines if line.strip())


def document_markdown(texts) -> str:
    """One markdown document: the section texts in order, a blank line between them."""
    return "\n\n".join(texts) + "\n"


def markdown_path(doc: str) -> str:
    """The path a source document takes in a variant: the same folder and name under the room,
    with `.md` on the end."""
    parts = PurePosixPath(doc).parts
    tail = parts[1:] if len(parts) > 1 else parts
    return PurePosixPath(ROOM, *tail).as_posix() + ".md"


def digests_path() -> Path:
    """tests/phase1-digests.json at the repository root."""
    return Path(__file__).resolve().parents[3] / "tests" / DIGESTS


def read_sections(runs_root: Path, sample: str, digests: Path) -> dict[str, tuple[str, ...]]:
    """The rendered text of every section of a sample's pinned run, by document, in order.

    Raises ValueError when the file is absent or its sha256 is not the pinned one, so that a
    variant is never written from a run the tests do not hold.
    """
    path = runs_root / sample / SECTIONS
    if not path.exists():
        raise ValueError(f"no {SECTIONS} at {path}")
    pinned = json.loads(digests.read_text(encoding="utf-8")).get(sample, {}).get(SECTIONS)
    if pinned is None:
        raise ValueError(f"{digests} pins no {SECTIONS} for {sample}")
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if got != pinned:
        raise ValueError(f"{path} is {got}, not the pinned {pinned}")

    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    records.sort(key=lambda record: (record["doc"], record["ordinal"]))
    found: dict[str, list[str]] = {}
    for record in records:
        text = render(record["text"])
        if text:
            found.setdefault(record["doc"], []).append(text)
    return {doc: tuple(texts) for doc, texts in found.items()}


def read_source(sample_dir: Path, runs_root: Path, digests: Path) -> Source:
    """Reads the source sample's key, brief and pinned sections."""
    key = json.loads((sample_dir / "key.json").read_text(encoding="utf-8"))
    brief = (sample_dir / key["brief"]).read_text(encoding="utf-8")
    return Source(
        name=sample_dir.name,
        directory=sample_dir,
        key=key,
        brief=brief,
        sections=read_sections(runs_root, sample_dir.name, digests),
    )


def identity(
    source: Source,
    knob: str,
    text: Callable[[str, str], str] | None = None,
    fact: Callable[[dict], dict | Drop] | None = None,
    brief_paragraph: str = "",
    path: Callable[[str], str] | None = None,
) -> Variant:
    """The variant a knob builds when it changes nothing but the rendition.

    `text` rewrites one section, taking the source document's path and the section text. `fact`
    returns the fact to keep or a Drop, and every Drop is listed in the variant's README.
    `brief_paragraph` is added to the brief, and a knob adds one only where it adds documents.
    `path` is where a document is written, and a knob passes one only where the source's file
    name carries what the knob removes; the default is markdown_path.
    """
    place = markdown_path if path is None else path
    documents = []
    for doc_id, doc in sorted(source.key["documents"].items()):
        texts = source.sections.get(doc, ())
        if text is not None:
            texts = tuple(text(doc, one) for one in texts)
        documents.append(Document(id=doc_id, path=place(doc), texts=tuple(texts)))

    facts = []
    drops = []
    for one in source.key["facts"]:
        kept = fact(one) if fact is not None else one
        if isinstance(kept, Drop):
            drops.append(kept)
        else:
            facts.append(kept)

    brief = source.brief
    if brief_paragraph:
        brief = brief.rstrip("\n") + "\n\n" + brief_paragraph.strip("\n") + "\n"

    return Variant(
        knob=knob,
        documents=tuple(documents),
        facts=tuple(facts),
        drops=tuple(drops),
        brief=brief,
    )


def variant_key(source: Source, variant: Variant, name: str) -> dict:
    """The variant's key: the source's key with the new name, the new paths, the facts, and the
    fields the knob rewrote."""
    key = dict(source.key)
    key["sample"] = name
    key["documents"] = {document.id: document.path for document in variant.documents}
    key["facts"] = list(variant.facts)
    key.update(variant.key_fields)
    return key


def wrap(text: str) -> str:
    """One paragraph wrapped at the width the repository writes its prose in."""
    return "\n".join(textwrap.wrap(text, width=WIDTH))


def readme(source: Source, variant: Variant, name: str) -> str:
    """The variant's README: the knob, what it was written from, the facts it dropped, and the
    section the knob wrote about itself where it wrote one."""
    dropped = (
        "\n\n" + "\n".join(f"- `{drop.id}`: {drop.why}" for drop in variant.drops)
        if variant.drops
        else " none"
    )
    written = wrap(
        f"Written by `python -m rlm.widen {variant.knob} samples/{source.name} "
        f"samples/{name}`, from `runs/{source.name}/{SECTIONS}` as `tests/{DIGESTS}` pins it."
    )
    room = wrap(
        f"The knob is `{variant.knob}`. The room is {len(variant.documents)} markdown "
        f"documents, one section of the source per block, under `{ROOM}/`. The key keeps the "
        f"source's ids, required documents, decoys, answer, rubric and bar, and points its "
        f"`documents` map at the new paths."
    )
    said = f"\n{variant.notes.strip()}\n" if variant.notes.strip() else ""
    return (
        f"# {name}\n\n{written}\n\n{room}\n\n"
        f"Facts: {len(variant.facts)}.\n\n"
        f"Facts dropped:{dropped}\n{said}"
    )


def write_text(path: Path, text: str) -> None:
    """Writes one file of a variant, creating its folder, with the line ending NEWLINE names."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline=NEWLINE)


def write_variant(source: Source, variant: Variant, target: Path) -> None:
    """Writes the room, the key, the brief and the README of one variant into target.

    The room is removed first, so a document a knob no longer writes does not survive a rerun.
    """
    room = target / ROOM
    if room.exists():
        shutil.rmtree(room)
    for document in variant.documents:
        write_text(target / document.path, document_markdown(document.texts))

    key = variant_key(source, variant, target.name)
    write_text(target / "key.json", json.dumps(key, indent=2, ensure_ascii=False) + "\n")
    write_text(target / source.key["brief"], variant.brief)
    write_text(target / "README.md", readme(source, variant, target.name))


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Reads the command line of one widen run."""
    parser = argparse.ArgumentParser(prog="python -m rlm.widen")
    parser.add_argument("knob")
    parser.add_argument("source")
    parser.add_argument("target")
    parser.add_argument(
        "--runs",
        default="runs",
        help="the directory holding <source sample>/sections.jsonl, relative to the working "
        "directory; a run from a worktree passes the main checkout's path",
    )
    parser.add_argument("--digests", default=None)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Writes one variant of one sample and prints what it wrote."""
    args = parse_args(argv)
    try:
        module = importlib.import_module(f"rlm.widen.{args.knob}")
    except ImportError:
        print(f"no knob module rlm.widen.{args.knob}")
        return 2

    digests = Path(args.digests) if args.digests else digests_path()
    try:
        source = read_source(Path(args.source), Path(args.runs), digests)
    except ValueError as refusal:
        print(f"{refusal}, nothing written")
        return 2

    variant = module.build(source)
    target = Path(args.target)
    write_variant(source, variant, target)
    sections = sum(len(document.texts) for document in variant.documents)
    print(
        f"widen {variant.knob}: {len(variant.documents)} documents, {sections} sections, "
        f"{len(variant.facts)} facts, {len(variant.drops)} dropped, written to {target}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
