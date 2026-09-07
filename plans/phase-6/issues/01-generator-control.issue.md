# feat(phase-6): generator, control variant and phase 6 harness [slice 01]

**Issue:** #96 · **Spec:** PLAN.md#4-phases, row "6 Widen" · **Plan:** plans/phase-6/01-generator-control.md
**Depends on:** none
**Labels:** phase-6

## Deliverable

`python -m rlm.widen control samples/atlas samples/atlas-control` writes 100 markdown files under
`samples/atlas-control/data_room/<same folder>/<same name>.<ext>.md`, one section per block or
table row in ingest's order, with `key.json` remapped to the new paths and `brief.md` copied.
`rlm.notes` and `rlm.write` gain `--phase` flag defaulting to their own phase constant. The chain
runs on `samples/atlas-control runs/atlas-control` with ledger rows booked to phase 6. `tests/test_phase6.py`
parametrised over every `samples/atlas-*/key.json` present, one test per phase in order, readout
printing recall, dollars from the ledger's phase 6 rows for that sample, spread, and the first phase
whose test failed or `holds`. `tests/phase6-control-digests.json` pinned.

## Mechanism

New package `src/rlm/widen/__init__.py` with `main(argv)` dispatching to `rlm.widen.<knob>` by import.
Reads `runs/atlas/sections.jsonl` checked against `tests/phase1-digests.json`, writes one markdown
file per document under `samples/atlas-<knob>/data_room/`, remaps `key.json` from
`samples/atlas/key.json` with facts carried as rewritten or dropped and listed in README, copies
`brief.md` with one added paragraph only where the knob adds documents. New module `src/rlm/widen/control.py`
as the identity knob. `--phase` flag on `src/rlm/notes.py` and `src/rlm/write.py` defaults to the
stage's own phase constant and books ledger rows to phase 6. `tests/test_phase6.py` imports phase
checks from `rlm.grade` and from phase 1 to 5 test modules' helpers, skip when artefact is absent.

## Acceptance criterion

Given `runs/atlas/sections.jsonl` matches `tests/phase1-digests.json` and `OPENROUTER_API_KEY`
is set,
when `python -m rlm.widen control samples/atlas samples/atlas-control` runs, the chain runs on
`samples/atlas-control runs/atlas-control` (ledger rows booked to phase 6), and `pytest -q
tests/test_phase6.py` runs,
then the variant has exactly 100 documents, each `.md` file's text carries every section text of
its source document in order, regeneration into a temporary directory is byte-identical; `key.json`
loads through `rlm.key.load_key` with 53 facts; every phase 1 to 5 test of the harness passes on
`atlas-control`; the readout line reads recall 100, dollars, spread and `holds`; the pinned
digests are in `tests/phase6-control-digests.json`; `pytest -q` on the three gate samples still
passes with no change to their digests.

## Files

```aeo-independence
slice: 01-generator-control
creates: src/rlm/widen/__init__.py
creates: src/rlm/widen/control.py
creates: tests/test_phase6.py
creates: tests/phase6-control-digests.json
creates: samples/atlas-control/
edits: src/rlm/notes.py
edits: src/rlm/write.py
```

## Out of scope

Any knob. Fixing a phase that drops a fact on the control (that is a new issue on that phase's
milestone under gate 2, and the phase 6 gate waits for it).
