# feat(phase-3): map.json on sample 1: document graph, and the fourteen AURORA documents in one cluster with no decoy [slice 01]

**Issue:** #53 · **Spec:** PLAN.md#4-phases, row "3 Map" · **Plan:** plans/phase-3/01-map-atlas.md
**Depends on:** #52
**Labels:** phase-3

## Deliverable

`runs/atlas/map.json` exists, written by `python -m rlm.map samples/atlas runs/atlas` from
the index, the sections and the pinned notes with no model call. It parses as JSON with sorted
keys and one trailing newline. Every node is a document the key names. Every edge names its
two documents, its kind, the shared value, and one resolving anchor in each document. The
first matter's `cluster` contains all fourteen required documents and no decoy. Two runs are
byte-identical.

## Mechanism

Survey in order. No skill, plugin or MCP fits; no new dependency. No model call. `src/rlm/map.py`
reads the index, sections and pinned notes and writes `map.json` and a `main(argv)`. The
builder opens `tests/test_phase3.py` (following `tests/test_phase1.py`'s pattern with a
module-level fixture that runs the map twice, per-sample parametrised tests, and a
`readout(terminalreporter)`). The design starts with: nodes from the key's `documents` order
with title, folder, first date and status from the index; edges from index identifiers and
cross-references and date proximity (two documents within seven days) and version pairs; weight
falls with the count of documents carrying a value; a matter is seeded from documents whose
notes carry flags or concealed items and share the rarest values; its cluster is documents
whose weighted links to the seed clear a fixed cut. Identifiers and cross-references alone
reach 91 of 100 on sample 1; the challenge is to rank the fourteen above the five decoys. The
test reads nothing from the key except the documents and decoys.

## Acceptance criterion

Given `runs/atlas/index.jsonl`, `runs/atlas/sections.jsonl` and pinned `runs/atlas/notes/`
matching `tests/phase2-digests.json`,
when `python -m rlm.map samples/atlas runs/atlas` runs twice (the second time into a temporary
directory) and then `pytest -q tests/test_phase3.py` runs,
then `map.json` exists and parses with sorted keys and one trailing newline; the two runs are
byte-identical; every document the key's `documents` array names is a node; every edge names
its two documents, its kind (one of `identifier`, `cross-reference`, `date`, `version`), the
shared value, and anchors (for a `date` edge, the two dated sections); the first matter's
`cluster` array contains every id in the key's `matter-documents` array and no id in the
`decoys` array; `ranked` lists every document in the room in descending score; `versions` and
`consequences` are empty (filled in slice 02); the readout prints, for the sample, node count,
edge count by kind, matter count, cluster size, planted recall as a percentage, count of decoys
in the cluster, and seconds; no line of code reads the key's facts except to construct the
test's before-and-after assertion; and all phase 0, 1 and 2 tests still pass.

## Files

```aeo-independence
slice: 01-map-atlas
creates: src/rlm/map.py
creates: tests/test_phase3.py
depends-on: 00-repin-notes
```

## Out of scope

Consequence links, version pairs, lesser matters, samples 2 and 3, digests and the status row.
A cluster recall below 100 or a decoy in the cluster is not acceptable; it is reported with
the document scores and the edges connecting them, and the slice code is revised, not the test
loosened.
