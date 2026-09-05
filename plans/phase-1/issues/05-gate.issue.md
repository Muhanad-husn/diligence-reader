# chore(phase-1): Phase 1 gate [slice 05]

**Issue:** to be filed · **Spec:** PLAN.md#4-phases, row "1 Ingest" · **Plan:** plans/phase-1/05-gate.md
**Depends on:** 04-ingest-northwind-northstar
**Labels:** phase-1

## Deliverable

The phase 1 tests pass on all three samples in one run with no code change between them, and `PLAN.md` section 4a's phase 1 row carries the numbers. `README.md`'s status line says phase 1 done.

## Mechanism

`pytest -q`, the ingest from slices 01 to 04, and two hand edits to prose. No model call, no gateway call, so `LEDGER.md` does not move and the phase cost $0 of the $50.

## Acceptance criterion

Given slices 01 to 04 are merged,
when `pytest -q tests/test_phase1.py` runs,
then every test passes on `atlas`, `northwind` and `northstar-dental`; the run prints per sample the documents read, sections written, index records by kind, engine disagreements and empty extractions; planted-fact recall is printed per sample as the share of key facts whose documents are sectioned and whose value resolves in a section or the index; the sha256 of all six artefacts match `tests/phase1-digests.json`; `LEDGER.md` is unchanged; and the phase 1 row reads state `done`, the three recall scores, dollars `0`, spread `0`, closed with the date.

## Files

```aeo-independence
slice: 05-gate
edits: PLAN.md
edits: README.md
depends-on: 04-ingest-northwind-northstar
```

## Out of scope

Any phase 2 issue. A recall below 100 on any sample is written into the status row and traced to the slice that dropped the fact, which is a new issue in phase 1, not a relaxed bar and not a fix in phase 2. A non-zero engine-disagreement count is reported and investigated, never treated as a threshold to relax.
