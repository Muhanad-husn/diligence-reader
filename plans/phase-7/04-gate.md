# 04: Phase 7 gate

Issue: [#126](https://github.com/Muhanad-husn/RLM/issues/126)

## Goal

`pytest -q` passes every phase 0 to 7 test, and `PLAN.md` carries the phase 7 row and the
comparison table: the RLM against ours on sample 1, and ours on sample 4.

## Acceptance criterion

Given slices 01 and 03 are merged,
when `pytest -q` runs,
then every phase 0 to 7 test passes on the three gate samples, the five variants, `atlas-rlm`
and `yahoo`; `PLAN.md` section 4a's phase 7 row reads state `done`, sample 4's recall, the
phase's dollars from `LEDGER.md`, the RLM's spread beside ours, and the date; `PLAN.md` gains a
section 4b comparison table with one row for the RLM and one for ours on sample 1 (score a,
score b, spread, recall, seconds, dollars) and one row for ours on sample 4; `README.md`'s
status line says phase 7 done and the total spend of the $50; the pull request body carries
the two readout lines and the one recommendation.

## Mechanism

`pytest -q` and hand edits to prose. No model call, no ledger line.

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
