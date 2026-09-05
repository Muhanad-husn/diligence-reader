# 05: Phase 1 gate

Issue: [#18](https://github.com/Muhanad-husn/RLM/issues/18)

## Goal

The phase 1 tests pass on all three samples in one run with no code change between them, the
two-run spread is zero because the artefacts are byte identical, and `PLAN.md`'s status row for
phase 1 carries the numbers.

## Acceptance criterion

Given slices 01 to 04 are merged,
when `pytest -q tests/test_phase1.py` runs,
then every test passes on `atlas`, `northwind` and `northstar-dental`; the run prints, per
sample, documents read, sections written, index records by kind, engine disagreements and empty
extractions; planted-fact recall is printed per sample as the share of key facts whose
documents are sectioned and whose value resolves in a section or the index; the sha256 of all
six artefacts match `tests/phase1-digests.json`; `LEDGER.md` is unchanged because no gateway
call was made; and `PLAN.md` section 4a's phase 1 row reads state `done`, the three recall
scores, dollars `0`, spread `0`, closed with the date. `README.md`'s status line says phase 1
done.

## Mechanism

- `pytest -q`, the ingest from slices 01 to 04, and two hand edits to prose. No model call.

## Files

```aeo-independence
slice: 05-gate
edits: PLAN.md
edits: README.md
depends-on: 04-ingest-northwind-northstar
```

## Out of scope

Any phase 2 issue. A recall below 100 on any sample is written into the status row and the pull
request body and traced to the slice that dropped the fact, which is a new issue in phase 1, not
a relaxed bar and not a fix in phase 2. A non-zero engine-disagreement count is reported and
investigated, never treated as a threshold to relax.
