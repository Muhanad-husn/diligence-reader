# 05: Phase 0 gate

Issue: [#5](https://github.com/Muhanad-husn/RLM/issues/5)

## Goal

The phase 0 tests pass on all three samples in one run, the grader's two-run spread on sample
1's perfect report is printed, and `PLAN.md`'s status row for phase 0 carries the numbers.

## Acceptance criterion

Given slices 01 to 04 are merged,
when `pytest -q tests/test_phase0.py` runs with the skip for missing keys removed from
`tests/conftest.py`,
then every test passes on `atlas`, `northwind` and `northstar-dental`, the grader run twice on
`samples/atlas/fixtures/report-perfect.md` prints both rubric scores and their difference, and
`PLAN.md` section 4a's phase 0 row reads state `done`, score `100 / 100 / 100`, dollars `0`,
spread as printed, closed with the date; `README.md`'s status line says phase 0 done.

## Mechanism

- `pytest -q`, the grader from slice 02, and two hand edits to prose. No model call beyond the
  grader's subscription subagent, run twice.

## Files

```aeo-independence
slice: 05-gate
edits: tests/conftest.py
edits: PLAN.md
edits: README.md
depends-on: 04-reports-northwind-northstar
```

## Out of scope

Any phase 1 issue. A spread above 5 points on the perfect report is reported in the status
row and the pull request body, not fixed here; the founder decides whether the grader is
re-prompted in a new phase 0 issue.
