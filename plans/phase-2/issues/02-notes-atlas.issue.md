# feat(phase-2): notes on all of sample 1 [slice 02]

**Issue:** #38 · **Spec:** PLAN.md#4-phases, row "2 Notes" · **Plan:** plans/phase-2/02-notes-atlas.md
**Depends on:** #37
**Labels:** phase-2

## Deliverable

`runs/atlas/notes/` holds a note for every one of the 100 documents the key names, or a logged drop.
Each of the fifteen phase 2 facts of sample 1 is inside a verified quote of a note of one of its own
documents. A note carries `doc`, `model`, `pass`, `what`, `flags`, `figures`, `cross_references`,
`concealed` and `usage`. Keys are sorted and every file ends with one newline. `notes-verify.jsonl`
is sorted by document then field then item, one record per failed item and per dropped note.

## Mechanism

The same modules as slice 01. `notes.py` gains: a pool of eight concurrent document calls
(`concurrent.futures.ThreadPoolExecutor`, no new dependency), the re-ask of failed quotes and the
drop after the second call, a note-level drop when JSON fails to parse twice, the sorted verify log,
a per-pass summary printed at the end and written to `runs/<sample>/notes-summary.json` (documents,
dropped, verified, re-asked, dropped items, tokens, dollars, seconds), and the readout hook in
`tests/test_phase2.py` following the phase 1 `readout(terminalreporter)` pattern. The recall test
applies the same fold to both sides: whitespace collapsed, case folded, curly quotes straightened.
No rule reads a key value. Prompt changes are allowed in this slice and are the expected work: the
fifteen facts are the measure. A fact still missed after the prompt is tuned is reported in the pull
request with the note's actual quotes beside it; the test is not loosened.

## Acceptance criterion

Given slice 01 is merged and `runs/atlas/sections.jsonl` exists,
when `python -m rlm.notes samples/atlas runs/atlas --model deepseek/deepseek-v4-flash-0731 --pass a`
runs detached and then `pytest -q tests/test_phase2.py` runs,
then every document in `samples/atlas/key.json`'s `documents` has a note file or a `note-dropped`
record; every quote and figure in every note verifies and its anchor resolves to a section of the
same document; `notes-verify.jsonl` is sorted by document then field then item and every dropped
item it names is absent from its note; each of the fifteen phase 2 facts has a note of one of its
documents holding a verified quote that contains the fact's value after whitespace is collapsed and
case folded on both sides; `LEDGER.md` gained exactly one line for the pass; and the pytest readout
prints, for the sample, documents noted, notes dropped, quotes verified, quotes re-asked, quotes
dropped, planted recall as a percentage, dollars, and seconds.

## Files

```aeo-independence
slice: 02-notes-atlas
edits: src/rlm/notes.py
edits: tests/test_phase2.py
edits: LEDGER.md
depends-on: 01-note-one-document-atlas
```

## Out of scope

Samples 2 and 3, any model but DeepSeek V4 Flash, the second pass and the agreement number, the
bake-off table, digests.
