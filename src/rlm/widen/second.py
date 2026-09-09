"""The second knob: sample 1's room with a second matter added to it.

Sample 2's eleven contract documents are written as a ninth folder,
`data_room/08_Northwind_Contracts/`, keeping the file names sample 2 gives them and taking the
ids DR-101 to DR-111 in file name order. The buyer's own overview under sample 2's `_reference`
folder is not a contract of the target and is not added, so the room grows by eleven documents
and not by twelve. Sample 1's hundred documents are written exactly as the control writes them.

The key is built the same way. Sample 1's 53 facts stand first and sample 2's 16 follow in
sample 2's own order, each with its `documents` list written as the new ids; no fact is dropped
and no value, kind, id or phase moves. The required documents are sample 1's 14 then sample 2's
10, and the decoys are sample 1's five then sample 2's Granite MSA. The answer, the rubric and
the bar stay sample 1's, because a 400m repricing outranks a 12.4m cliff.

The brief gains one paragraph naming the folder, the id range and what the eleven documents
are, and the README gains a table of the eleven with what the key calls each one.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from rlm.widen import ROOM, Document, Source, Variant, identity, render, wrap

NAME = "second"

# The folder the second matter's documents are written under, beside sample 1's eight.
FOLDER = "08_Northwind_Contracts"

# The sample the second matter is read out of, and the folder of it that holds the contracts.
SECOND = "northwind"
SECOND_ROOM = "sample_data_room/Northwind_Logistics"

# The id the first added document takes; the rest follow it in file name order.
FIRST_ID = "DR-101"


def root() -> Path:
    """The repository root, the way the pinned digests are found from here."""
    return Path(__file__).resolve().parents[3]


def second_directory() -> Path:
    """The sample directory the second matter is read out of."""
    return root() / "samples" / SECOND


def source_files() -> list[Path]:
    """The markdown files of the second matter, in file name order."""
    return sorted((second_directory() / SECOND_ROOM).glob("*.md"), key=lambda path: path.name)


def next_id(number: int) -> str:
    """The id the added document at this place in file name order takes."""
    head, _, first = FIRST_ID.rpartition("-")
    return f"{head}-{int(first) + number:0{len(first)}d}"


def texts_of(path: Path) -> tuple[str, ...]:
    """The section texts of one added document.

    The file is read as utf-8, its line endings folded to newlines and split on a blank line,
    and each block is rendered the way every other document of a variant is. Nothing else
    changes, so the markdown the variant writes is the source file's own text.
    """
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    return tuple(one for one in (render(block) for block in text.split("\n\n")) if one)


def added() -> tuple[Document, ...]:
    """The eleven documents of the second matter, in file name order."""
    return tuple(
        Document(
            id=next_id(number),
            path=f"{ROOM}/{FOLDER}/{path.name}",
            texts=texts_of(path),
        )
        for number, path in enumerate(source_files())
    )


def second_key() -> dict:
    """Sample 2's key, read as it stands."""
    return json.loads((second_directory() / "key.json").read_text(encoding="utf-8"))


def ids_by_path(documents: tuple[Document, ...]) -> dict[str, str]:
    """Sample 2's document paths mapped to the ids the variant gives them."""
    return {
        f"{SECOND_ROOM}/{document.path.rpartition('/')[2]}": document.id
        for document in documents
    }


def remapped_facts(key: dict, new_id: dict[str, str]) -> tuple[dict, ...]:
    """Sample 2's facts in sample 2's order, with their documents written as the new ids."""
    return tuple(
        {**fact, "documents": [new_id[doc] for doc in fact["documents"]]}
        for fact in key["facts"]
    )


def brief_paragraph(documents: tuple[Document, ...]) -> str:
    """The paragraph the knob adds to sample 1's brief."""
    return wrap(
        f"This room also holds the target's Northwind Logistics contracts and their ARR "
        f"schedule: {len(documents)} documents under `{ROOM}/{FOLDER}/`, with the ids "
        f"{documents[0].id} to {documents[-1].id}. They are a matter of their own, separate "
        f"from the eight workstreams above."
    )


def called(doc_id: str, required: tuple[str, ...], decoys: tuple[str, ...]) -> str:
    """What the key calls one added document: required, a decoy, or neither."""
    if doc_id in required:
        return "required"
    if doc_id in decoys:
        return "decoy"
    return "neither"


def table(
    documents: tuple[Document, ...], required: tuple[str, ...], decoys: tuple[str, ...]
) -> str:
    """The README's table: one row per added document, with what the key calls it."""
    lines = ["| document | file | the key calls it |", "|---|---|---|"]
    for document in documents:
        file_name = document.path.rpartition("/")[2]
        stands = called(document.id, required, decoys)
        lines.append(f"| {document.id} | `{file_name}` | {stands} |")
    return "\n".join(lines)


def notes(
    documents: tuple[Document, ...],
    facts: tuple[dict, ...],
    required: tuple[str, ...],
    decoys: tuple[str, ...],
) -> str:
    """The section the knob adds to the variant's README."""
    brought = f"{len(decoys)} decoy" + ("" if len(decoys) == 1 else "s")
    said = wrap(
        f"The knob adds sample 2's {len(documents)} contract documents as a ninth folder, "
        f"`{ROOM}/{FOLDER}/`, with the ids {documents[0].id} to {documents[-1].id} in file "
        f"name order. Sample 2 brings {len(facts)} facts, {len(required)} required documents "
        f"and {brought}, and the key carries each of them with its documents written as the "
        f"new ids. Sample 1's facts, required documents, decoys, answer, rubric and bar stand "
        f"as they are, because a 400m repricing outranks a 12.4m cliff."
    )
    return f"## The second matter\n\n{said}\n\n{table(documents, required, decoys)}\n"


def build(source: Source) -> Variant:
    """The variant of sample 1 that carries sample 2's contracts as a second matter."""
    documents = added()
    key = second_key()
    new_id = ids_by_path(documents)

    facts = remapped_facts(key, new_id)
    required = tuple(new_id[doc] for doc in key["required_documents"])
    decoys = tuple(
        {"document": new_id[decoy["document"]], "why": decoy["why"]} for decoy in key["decoys"]
    )

    variant = identity(source, NAME, brief_paragraph=brief_paragraph(documents))
    return replace(
        variant,
        documents=variant.documents + documents,
        facts=variant.facts + facts,
        notes=notes(documents, facts, required, tuple(one["document"] for one in decoys)),
        key_fields={
            "required_documents": list(source.key["required_documents"]) + list(required),
            "decoys": list(source.key["decoys"]) + list(decoys),
        },
    )
