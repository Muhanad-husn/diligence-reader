# chore(phase-3): Phase 3 gate [slice 04]

**Issue:** #56 · **Spec:** PLAN.md#4-phases, row "3 Map" · **Plan:** plans/phase-3/04-gate.md
**Depends on:** #55
**Labels:** phase-3

## Deliverable

The phase 3 tests pass on all three samples in one run with no code change between them. The
three `map.json` artefacts are pinned by digest in `tests/phase3-digests.json`. `PLAN.md`
section 4a's phase 3 row carries the planted recall scores, dollars and spread. `README.md`'s
status line says phase 3 done and the spend so far.

## Mechanism

`pytest -q`, a `--pin` flag or small addition to `src/rlm/pin.py` that writes
`tests/phase3-digests.json` from the maps on disk, and two hand edits to prose. No new model
call.

## Acceptance criterion

Given slices 00 to 03 are merged,
when `pytest -q` runs,
then every phase 0, 1, 2 and 3 test passes on `atlas`, `northwind` and `northstar-dental`;
`tests/phase3-digests.json` holds the sha256 of each sample's `map.json` and a test asserts
the files on disk match it; `LEDGER.md` has no new phase 3 lines (the phase costs $0; phase 2
costs were paid in the prior phase); `PLAN.md` section 4a's phase 3 row reads state `done`,
the three planted cluster recall scores, dollars 0, spread 0
(two runs byte-identical, by the slice 01 test), and the date; `README.md`'s status line says
phase 3 done and the cumulative spend so far; the pull request body reports the three planted
recall numbers and the sha256 of each map; and `runs/atlas/map.json`, `runs/northwind/map.json`
and `runs/northstar-dental/map.json` exist on disk with no worktree.

## Files

```aeo-independence
slice: 04-gate
creates: tests/phase3-digests.json
edits: src/rlm/pin.py
edits: tests/test_phase3.py
edits: PLAN.md
edits: README.md
depends-on: 03-map-northwind-northstar
```

## Out of scope

Any phase 4 issue. A cluster recall below 100 or a decoy in a cluster on any sample is written
into the status row and traced to the slice that owns it, which becomes a new phase 3 issue,
not a relaxed bar.
