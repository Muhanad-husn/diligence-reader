# 04: Perfect and wrong reports for samples 2 and 3, graded with no code change

Issue: [#4](https://github.com/Muhanad-husn/RLM/issues/4)

## Goal

The grader from slice 02, unchanged, gives each of samples 2 and 3 a perfect report 100 and a
wrong report under 40.

## Acceptance criterion

Given the four fixture reports exist,
when `pytest -q tests/test_phase0.py` runs,
then the key and grade tests pass on all three samples, the diff of the pull request touches
nothing under `src/` or `tests/`, and `runs/northwind/` and `runs/northstar-dental/` hold
`grade-perfect.json` and `grade-wrong.json` with recall 100% and under 40% respectively.

## Mechanism

- Hand-written data, in the brief's five sections, citing documents by the ids in each key.
- Northwind perfect: the $12.4m revenue cliff at close ranked first, the Granite clause named
  as benign, the four secondary gaps, the deck's misstatement, a recommendation with the
  number. Northwind wrong: Granite's consent clause elevated as the change-of-control risk,
  Meridian named only as a concentration, no cliff number, "confirm in Q&A".
- Northstar perfect: $24.8M, $22.2M, 11.7% against the CIM's 18.0%, CloudDent, the two payors
  at $10.0M. Northstar wrong: accepts 18.0%, names SmileSupply as the top vendor risk, no
  payor number.
- No model call: samples 2 and 3 have no rubric, so the grader's subscription subagent is not
  invoked for them.

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

Any change to the grader. A wrong report that scores 40 or above is a grader gap and goes back
to slice 02's file in a new issue, not a rewrite of the wrong report to score lower.
