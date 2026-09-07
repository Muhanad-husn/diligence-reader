# chore(phase-4): Phase 4 gate [slice 04]

**Issue:** #66 · **Spec:** PLAN.md#4-phases, row "4 Dossier" · **Plan:** plans/phase-4/04-gate.md
**Depends on:** #65
**Labels:** phase-4

## Deliverable

The phase 4 tests pass on all three samples in one run with no code change between them. The
three `dossier.md` artefacts are pinned by digest in `tests/phase4-digests.json`. `PLAN.md`
section 4a's phase 4 row carries the planted recall scores, dollars and spread. `README.md`'s
status line says phase 4 done and the spend so far. The pull request body carries sample 1's
dossier in full, which the founder reads once as a reader before merging.

## Mechanism

`pytest -q`, a `--dossiers` mode in `src/rlm/pin.py` beside `--maps` that writes
`tests/phase4-digests.json` from the dossiers on disk, and two hand edits to prose. No model
call.

## Acceptance criterion

Given slices 01 to 03 are merged,
when `pytest -q` runs,
then every phase 0, 1, 2, 3 and 4 test passes on `atlas`, `northwind` and `northstar-dental`;
`tests/phase4-digests.json` holds the sha256 of each sample's `dossier.md` and a test asserts
the files on disk match it; `python -m rlm.pin --dossiers` writes that file from the dossiers
on disk and refuses, naming the sample, when a dossier is missing; `LEDGER.md` has no new
phase 4 line; `PLAN.md` section 4a's phase 4 row reads state `done`, the three planted recall
scores (phase 1 to 4 facts found in the dossier, as a percentage), dollars 0, spread 0 (two
runs byte-identical, by the slice 01 test), and the date; `README.md`'s status line says phase
4 done and the cumulative spend; the pull request body reports the three numbers, the sha256
of each dossier and `runs/atlas/dossier.md` in full; and the three dossiers exist on disk
under `D:\RLM\runs` with no worktree.

## Files

```aeo-independence
slice: 04-gate
creates: tests/phase4-digests.json
edits: src/rlm/pin.py
edits: tests/test_phase4.py
edits: PLAN.md
edits: README.md
depends-on: 03-dossier-northwind-northstar
```

## Out of scope

Any phase 5 issue. A recall below 100 or a decoy in a set on any sample is written into the
status row and traced to the slice that owns it, which becomes a new phase 4 issue, not a
relaxed bar. What the founder's reading finds wrong in the dossier as prose is a new phase 4
issue too.
