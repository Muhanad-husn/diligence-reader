# chore(phase-7): Phase 7 gate, the comparison table and the status row written, the spend closed [slice 04]

**Issue:** #126 · **Spec:** PLAN.md#4a-status · **Plan:** plans/phase-7/04-gate.md
**Depends on:** #123, #125
**Labels:** phase-7

## Deliverable

`pytest -q` passes every phase 0 to 7 test in one run. `PLAN.md` section 4a's phase 7 row carries
state, sample 4's recall, the phase's dollars, the RLM's spread beside ours, and the date. A new
section 4b holds the comparison table: the RLM and ours on sample 1 (score a, score b, spread,
recall, seconds, dollars), and ours on sample 4. `README.md`'s status line says phase 7 done and
the total spend of the $50. The pull request body carries the two readout lines and the one
recommendation.

## Mechanism

`pytest -q` and hand edits to prose. No model call, no ledger line.

## Acceptance criterion

Given slices 01 and 03 are merged,
when `pytest -q` runs,
then every phase 0 to 7 test passes on the three gate samples, the five variants, `atlas-rlm` and
`yahoo`; `PLAN.md` section 4a's phase 7 row reads state `done`, sample 4's recall, the phase's
dollars from `LEDGER.md`, the RLM's spread beside ours, and the date; `PLAN.md` gains a section 4b
comparison table with one row for the RLM and one for ours on sample 1 and one row for ours on
sample 4; `README.md`'s status line says phase 7 done and the total spend of the $50; the pull
request body carries the two readout lines and the one recommendation.

## Files

```aeo-independence
slice: 04-gate
edits: PLAN.md
edits: README.md
depends-on: 01-rlm-atlas
depends-on: 03-yahoo-run
```

## Out of scope

Any issue after phase 7.
