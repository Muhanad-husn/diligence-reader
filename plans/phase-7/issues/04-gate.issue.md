# chore(phase-7): Phase 7 gate, the comparison table and the status row written, the spend closed [slice 04]

**Issue:** #126 · **Spec:** PLAN.md#4a-status · **Plan:** plans/phase-7/04-gate.md
**Depends on:** #125
**Labels:** phase-7

## Deliverable

`pytest -q` passes every phase 0 to 7 test in one run. `PLAN.md` section 4a's phase 7 row carries
state, sample 4's recall, the phase's dollars and the date. A new section 4b holds the table:
ours on sample 4 (recall, seconds, dollars). `README.md`'s status line says phase 7 done and the
total spend of the $50. The pull request body carries the readout line and the one
recommendation.

## Mechanism

`pytest -q` and hand edits to prose. No model call, no ledger line.

## Acceptance criterion

Given slice 03 is merged,
when `pytest -q` runs,
then every phase 0 to 7 test passes on the three gate samples, the five variants and `yahoo`;
`PLAN.md` section 4a's phase 7 row reads state `done`, sample 4's recall, the phase's dollars
from `LEDGER.md` and the date; `PLAN.md` gains a section 4b table with one row for ours on
sample 4; `README.md`'s status line says phase 7 done and the total spend of the $50; the pull
request body carries the readout line and the one recommendation.

## Files

```aeo-independence
slice: 04-gate
edits: PLAN.md
edits: README.md
depends-on: 03-yahoo-run
```

## Out of scope

Any issue after phase 7.
