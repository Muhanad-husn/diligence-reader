# chore(phase-5): Phase 5 gate, the winner's reports pinned on the three samples, the status row and the bake-off table in PLAN.md [slice 06]

**Issue:** #84 · **Spec:** PLAN.md#4a-status · **Plan:** plans/phase-5/06-gate.md
**Depends on:** #83
**Labels:** phase-5

## Deliverable

`pytest -q` passes every phase 0 to 5 test on the three samples in one run. `PLAN.md`
section 4a's phase 5 row carries state, score (recall on the three samples and the rubric
score on sample 1), dollars, spread and the date; section 5 carries the phase 5 bake-off
table, the winner as the default `--model` of `python -m rlm.write`, and the price table as
reread on the bake-off's day; the phase 3 row records slice 04's outcome; `README.md`'s status
line says phase 5 done and the spend so far. The pull request body carries the three numbers,
the sha256 of the nine pinned files, and `runs/atlas/report.md` in full for the founder to
read once as a reader before merging.

## Mechanism

`pytest -q` and hand edits to prose. No model call, no ledger line.

## Acceptance criterion

Given slices 01 to 05 are merged,
when `pytest -q` runs,
then every phase 0 to 5 test passes on `atlas`, `northwind` and `northstar-dental`; the
three samples' `report.md`, `verify.json` and `grade.json` match `tests/phase5-digests.json`;
`PLAN.md` section 4a's phase 5 row reads state `done`, recall on the three samples and the
rubric score on sample 1, the phase's dollars from `LEDGER.md`, the spread per sample and the
date; `PLAN.md` section 5 carries the phase 5 bake-off table, one row per model, the winner
named as the default `--model` of `python -m rlm.write`, and the price table as reread;
`README.md`'s status line says phase 5 done and the spend so far; the Phase 5 milestone's
note on the map rescoring is closed by slice 04's outcome written into `PLAN.md` section 4's
phase 3 row; and the pull request body carries the three numbers, the sha256 of the nine
pinned files, and `runs/atlas/report.md` in full.

## Files

```aeo-independence
slice: 06-gate
edits: PLAN.md
edits: README.md
depends-on: 05-bakeoff-three-samples
```

## Out of scope

Any phase 6 issue. A recall below 100, a failing verifier or a rubric under 85 on any sample
is written into the status row and traced to the slice that owns it, which is a new phase 5
issue, not a relaxed bar. What the founder's reading finds wrong in the report as prose is a
new phase 5 issue too.
