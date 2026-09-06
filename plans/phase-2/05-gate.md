# 05: Phase 2 gate

Issue: [#41](https://github.com/Muhanad-husn/RLM/issues/41)

## Goal

The phase 2 tests pass on all three samples in one run with no code change between them, the winning
model's first pass is pinned by digest, and `PLAN.md`'s status row for phase 2 carries the numbers.

## Acceptance criterion

Given slices 01 to 04 are merged,
when the winning model's pass `a` is copied from `runs/<sample>/bakeoff/<winner>/a/` to
`runs/<sample>/notes/` and `runs/<sample>/notes-verify.jsonl` for the three samples and `pytest -q
tests/test_phase2.py` runs,
then every test passes on `atlas`, `northwind` and `northstar-dental`; `tests/phase2-digests.json`
holds the sha256 of every pinned note file and verify log and a test asserts the files on disk match
it; the readout prints per sample the lines from slice 02 plus the agreement between the two
bake-off passes; `LEDGER.md`'s phase 2 lines sum to under $8; and `PLAN.md` section 4a's phase 2 row
reads state `done`, the three planted recall scores, the dollars from the ledger, the spread as the
three per-sample values of 100 minus agreement, and the date. `README.md`'s status line says phase 2
done and the spend so far.

## Mechanism

`pytest -q`, a small `python -m rlm.pin` that copies the winning pass into place and writes
`tests/phase2-digests.json`, and two hand edits to prose. No new model call.

## Files

```aeo-independence
slice: 05-gate
creates: tests/phase2-digests.json
edits: tests/test_phase2.py
edits: PLAN.md
edits: README.md
depends-on: 04-bakeoff
```

## Out of scope

Any phase 3 issue. A recall below 100 on any sample is written into the status row and traced to the
slice that dropped the fact, which is a new phase 2 issue, not a relaxed bar. A spread above zero is
reported as measured; nothing votes between passes.
