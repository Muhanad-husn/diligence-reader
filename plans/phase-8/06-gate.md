# Slice 06: Phase 8 gate

Milestone `Phase 8`. Issue: [#141](https://github.com/Muhanad-husn/diligence-reader/issues/141). Spec: `PLAN.md#4c-phase-8-the-product`. Depends on: slice 04 of this phase, 04-web; slice 05 of this phase, 05-package.

## Deliverable

The image built from main, served by docker run with RLM_PHASE=8; samples 1, 2 and 3 each started twice from the web page by a Playwright test; recall compared with the command line's 100 / 100 / 100; every planted fact read out of each run's docx, PDF and CSV; the spread over the two runs printed; PLAN.md section 4a's phase 8 row written (score, dollars from every phase 8 LEDGER.md row, spread, closed date); README's "Run it" section rewritten for docker run, pipx and Helm (that text written by a Haiku agent and read by hand).

## Mechanism

The tests of slices 01 to 05 reused; one new gate test drives them on all three samples.

## Acceptance criterion

Given the image from main, when the gate test runs, then recall is 100 / 100 / 100 on the first runs, equal to the command line, every planted fact reads out of the docx, the PDF and the CSV on each sample, the spread is printed, and PLAN.md's phase 8 row is filled. A red found here is fixed in this pull request or written as a known miss; no issue is filed from this readout.

## Tests

tests/test_phase8_gate.py, parametrised over samples 1, 2 and 3, each run twice from the web page.

## Money

About $0.80.

## Files

```aeo-independence
slice: 06-gate
creates: tests/test_phase8_gate.py
edits: PLAN.md
edits: README.md
edits: LEDGER.md
depends-on: 04-web
depends-on: 05-package
```

## Out of scope

Sample 4; the rubric; new features.
