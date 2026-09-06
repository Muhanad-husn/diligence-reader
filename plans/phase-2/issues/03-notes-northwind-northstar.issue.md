# feat(phase-2): notes on samples 2 and 3 [slice 03]

**Issue:** #39 · **Spec:** PLAN.md#4-phases, row "2 Notes" · **Plan:** plans/phase-2/03-notes-northwind-northstar.md
**Depends on:** #38
**Labels:** phase-2

## Deliverable

`runs/northwind/notes/` and `runs/northstar-dental/notes/` exist with the same code as sample 1. The
five phase 2 facts of sample 2 and the two of sample 3 are inside verified quotes of notes of their
own documents. Sample 1's notes are not rerun in this slice.

## Mechanism

The same modules as slices 01 and 02. The only work expected is in the prompt, if a markdown
contract needs the instruction to quote a clause whole, and in the test's enabled set.

## Acceptance criterion

Given slice 02 is merged and `runs/northwind/sections.jsonl` and
`runs/northstar-dental/sections.jsonl` exist from phase 1,
when `python -m rlm.notes samples/northwind runs/northwind --model deepseek/deepseek-v4-flash-0731
--pass a` and the same for `northstar-dental` run and then `pytest -q tests/test_phase2.py` runs,
then every phase 2 test passes on all three samples with no code change to the note shape or the
verification rule; the long Meridian change-of-control clause is inside one verified quote of the
note of `msa_meridian_freight.pdf.md`; `LEDGER.md` gained one line per sample; and the readout
prints the same lines for the two samples as for sample 1.

## Files

```aeo-independence
slice: 03-notes-northwind-northstar
edits: src/rlm/notes.py
edits: tests/test_phase2.py
edits: LEDGER.md
depends-on: 02-notes-atlas
```

## Out of scope

The second pass, the bake-off, any other model, any change to phase 1 artefacts.
