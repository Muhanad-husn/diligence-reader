# chore(phase-0): Phase 0 gate [slice 05]

**Issue:** #5 · **Spec:** PLAN.md#4-phases, row "0 Fixtures" and section 4a · **Plan:** plans/phase-0/05-gate.md
**Depends on:** #4
**Labels:** phase-0

## Deliverable

The phase 0 tests pass on all three samples in one run with the missing-key skip removed from `tests/conftest.py`. The grader runs twice on sample 1's perfect report and the two rubric scores and their difference are printed. `PLAN.md` section 4a's phase 0 row reads state `done`, score `100 / 100 / 100`, dollars `0`, the spread, and the closing date. `README.md`'s status line says phase 0 done. No phase 1 issue exists before this closes.

## Mechanism

`pytest -q tests/test_phase0.py`, the grader from slice 02 run twice by hand, two prose edits. No model call beyond the grader's subscription subagent.

## Acceptance criterion

Given slices 01 to 04 are merged,
when `pytest -q tests/test_phase0.py` runs with the skip removed,
then every test passes on `atlas`, `northwind` and `northstar-dental`, the two grader runs on `samples/atlas/fixtures/report-perfect.md` both print a rubric score and their difference is written as the spread, and the phase 0 row in `PLAN.md` and the status line in `README.md` carry the numbers above.

## Files

```aeo-independence
slice: 05-gate
edits: tests/conftest.py
edits: PLAN.md
edits: README.md
depends-on: 04-reports-northwind-northstar
```

## Out of scope

Any phase 1 issue. A spread above 5 points is reported in the row and the pull request body, not fixed here; the founder decides whether the grader is re-prompted in a new phase 0 issue.
