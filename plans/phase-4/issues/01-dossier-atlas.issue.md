# feat(phase-4): dossier.md on sample 1: the fourteen AURORA documents in the matter's set with no decoy, timeline, names, figures and the models blind to it [slice 01]

**Issue:** #63 · **Spec:** PLAN.md#4-phases, row "4 Dossier" · **Plan:** plans/phase-4/01-dossier-atlas.md
**Depends on:** none
**Labels:** phase-4

## Deliverable

`runs/atlas/dossier.md` exists, written by `python -m rlm.dossier samples/atlas runs/atlas`
from the map, the index, the sections and the pinned notes with no model call. Its first
matter's document set holds all fourteen required documents and none of the five decoys, and
every required document is ranked above every decoy. It carries the matter's timeline, the
names each function gave it, its figures with sources, and the models blind to it, every row
with one anchor that resolves. Two runs are byte-identical. The map's one-per-matter cap on
consequences is lifted and its cluster cut is brought in (founder's approval, 2026-09-07);
sample 1's cluster is expected near fourteen, and phase 3's digests are repinned.

## Mechanism

Survey in order. No skill, plugin or MCP fits; no new dependency; no model call. In
`src/rlm/map.py`, `series_break` and `model_after` keep every consequence that meets the rule
instead of one per kind, and `CLUSTER_SHARE` becomes the fixed rule that holds the fourteen
with no decoy, stated in its docstring. `src/rlm/dossier.py` reads `map.json`, `index.jsonl`,
`sections.jsonl` and `notes/` and writes `dossier.md` with a `main(argv)`: sections
`Documents`, `Timeline`, `Names`, `Figures`, `Models blind to it`, and empty `Comparisons` and
`Lesser matters` for slice 02. Row grammar fixed for the phase: `- <date or figure> | <doc> |
<quote> | <anchor>`; a `Documents` line is `- <rank>. <doc> | <title> | <folder> | <date> |
<status>`. Quotes are the notes' quotes verbatim. `tests/test_phase4.py` follows
`tests/test_phase3.py`: a module-level fixture that runs the dossier twice, per-sample tests
parametrised through `tests/conftest.py`, a `readout(terminalreporter)`, skip when inputs are
absent. Tests are committed red first.

## Acceptance criterion

Given `runs/atlas/index.jsonl`, `runs/atlas/sections.jsonl` and pinned `runs/atlas/notes/`
matching `tests/phase2-digests.json`,
when `python -m rlm.map samples/atlas runs/atlas` runs, then `python -m rlm.dossier
samples/atlas runs/atlas` runs twice (the second time into a temporary directory) and then
`pytest -q tests/test_phase3.py tests/test_phase4.py` runs,
then `dossier.md` exists with one trailing newline and the two runs are byte-identical; the
first matter's `Documents` section lists every id in the key's `matter-documents` fact and no
id in the key's `decoys`; every `matter-documents` id is ranked above every decoy in the
dossier's document list; every phase 1 and phase 2 fact has a row whose quote or figure
carries the fact's value after straightening and whose anchor parses, belongs to one of the
fact's documents and is a section anchor of that document; the `Names` section lists every
name the key's `workstream`, `programme` and `ticket` facts give the matter, each with a
document and an anchor; `Models blind to it` carries two series breaks (DR-048 and DR-050,
both at 2025-10-20) and two models after (DR-096 and DR-005), each with its anchor, and the
map's first matter carries the same four consequences; `tests/phase3-digests.json` is
repinned to the new `map.json` and every phase 3 test passes; the readout prints, for the
sample, document set size, planted recall as a percentage, decoys in the set, rows, names,
consequences, and seconds; no line of code reads the key's facts except the tests; and all
phase 0, 1 and 2 tests still pass.

## Files

```aeo-independence
slice: 01-dossier-atlas
edits: src/rlm/map.py
edits: tests/test_phase3.py
edits: tests/phase3-digests.json
creates: src/rlm/dossier.py
creates: tests/test_phase4.py
```

## Out of scope

Comparison rows and lesser matters (slice 02). Samples 2 and 3 (slice 03). Digests, the
status row and the founder's reading (slice 04). A required document outside the set or a
decoy inside it is not acceptable; it is reported with the document's map score and the
edges that carry it, and the map's scoring is revised, not the test loosened.
