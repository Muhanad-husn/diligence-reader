# chore(phase-6): Phase 6 gate, the variants' reports pinned on the five knobs, the status row in PLAN.md [slice 06]

**Issue:** #101 · **Spec:** PLAN.md#4a-status · **Plan:** plans/phase-6/06-gate.md
**Depends on:** #97, #98, #99, #100
**Labels:** phase-6

## Deliverable

`pytest -q` passes every phase 0 to 6 test on the three gate samples and the five variants in one run.
The five variants' digest files match `tests/phase6-<knob>-digests.json` for each knob. `PLAN.md`
section 4a's phase 6 row carries state, score (recall per knob and rubric on sample 1's variants),
dollars, spread per knob and the date. `PLAN.md` section 4's phase 6 row records, per knob, `holds`
or the phase that dropped a fact and the issue that fixed it. `PLAN.md` section 10 decision 2 is
written as made (the generator). `README.md`'s status line says phase 6 done and the spend so far.
The pull request body carries the five readout lines.

## Mechanism

`pytest -q` and hand edits to prose. No model call, no ledger line. A knob whose harness still fails
at the gate is written into the row with the failing phase and is not fixed here: under RULES.md
gate 3 the founder decides.

## Acceptance criterion

Given slices 01 to 05 are merged,
when `pytest -q` runs,
then every phase 0 to 6 test passes on `atlas`, `northwind` and `northstar-dental`; the five
variants' digest files match `tests/phase6-<knob>-digests.json` for each knob; `PLAN.md` section
4a's phase 6 row reads state `done`, recall per knob (control, names, unnamed, second, twice),
rubric on sample 1's variants, the phase's dollars from `LEDGER.md`, spread per knob, and the
date; `PLAN.md` section 4's phase 6 row records, per knob, `holds` or the phase that dropped a
fact and the issue that fixed it; `PLAN.md` section 10 decision 2 is written as made; `README.md`'s
status line says phase 6 done and the spend so far; the pull request body carries the five readout lines.

## Files

```aeo-independence
slice: 06-gate
edits: PLAN.md
edits: README.md
depends-on: 02-names
depends-on: 03-unnamed
depends-on: 04-second
depends-on: 05-twice
```

## Out of scope

Any phase 7 issue.
