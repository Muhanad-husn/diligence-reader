# feat(phase-0): perfect and wrong reports for samples 2 and 3, graded with no code change [slice 04]

**Issue:** #4 · **Spec:** PLAN.md#4-phases, row "0 Fixtures" · **Plan:** plans/phase-0/04-reports-northwind-northstar.md
**Depends on:** #2, #3
**Labels:** phase-0

## Deliverable

Four hand-written reports under `samples/northwind/fixtures/` and `samples/northstar-dental/fixtures/`, `report-perfect.md` and `report-wrong.md` each, in the brief's five sections, citing documents by the ids in each key. The grader from slice 02, unchanged, gives each perfect report 100 and each wrong report under 40.

## Mechanism

Hand-written data. Northwind perfect: the $12.4m revenue cliff at close ranked first, the Granite clause named as benign, the four secondary gaps, the deck's misstatement, a recommendation with the number. Northwind wrong: Granite's consent clause elevated as the change-of-control risk, Meridian named only as a concentration, no cliff number, "confirm in Q&A". Northstar perfect: $24.8M, $22.2M, 11.7% against the CIM's 18.0%, CloudDent, the two payors at $10.0M. Northstar wrong: accepts 18.0%, names SmileSupply as the top vendor risk, no payor number. No model call: these keys have no rubric, so the subscription subagent is not invoked.

## Acceptance criterion

Given the four fixture reports exist,
when `pytest -q tests/test_phase0.py` runs,
then the key and grade tests pass on all three samples, the pull request diff touches nothing under `src/` or `tests/`, and `runs/northwind/` and `runs/northstar-dental/` hold `grade-perfect.json` and `grade-wrong.json` with recall 100% and under 40% respectively.

## Files

```aeo-independence
slice: 04-reports-northwind-northstar
creates: samples/northwind/fixtures/report-perfect.md
creates: samples/northwind/fixtures/report-wrong.md
creates: samples/northstar-dental/fixtures/report-perfect.md
creates: samples/northstar-dental/fixtures/report-wrong.md
depends-on: 02-grade-atlas
depends-on: 03-keys-northwind-northstar
```

## Out of scope

Any change to the grader. A wrong report that scores 40 or above is a grader gap filed as a new issue against slice 02's file, not a rewrite of the wrong report to score lower.
