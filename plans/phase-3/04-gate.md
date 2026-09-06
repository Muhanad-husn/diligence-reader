# 04: Phase 3 gate

Issue: [#56](https://github.com/Muhanad-husn/RLM/issues/56)

## Goal

The phase 3 tests pass on all three samples in one run with no code change between them,
`map.json` is pinned by digest per sample in `tests/phase3-digests.json`, and `PLAN.md`
section 4a's phase 3 row carries the numbers.

## Acceptance criterion

Given slices 00 to 03 are merged,
when `pytest -q` runs,
then every phase 0, 1, 2 and 3 test passes on `atlas`, `northwind` and `northstar-dental`;
`tests/phase3-digests.json` holds the sha256 of each sample's `map.json` and a test asserts
the file on disk matches it; `LEDGER.md` gained no phase 3 line (the phase costs $0); `PLAN.md`
section 4a's phase 3 row reads state `done`, the three planted cluster recall scores, dollars
0, spread 0 (two runs byte-identical, by the slice 01 test), and the date; and `README.md`'s
status line says phase 3 done and the spend so far. The pull request body carries the three
numbers and the sha256 of the three maps.

## Mechanism

`pytest -q`, a `--pin` flag or small addition to `src/rlm/pin.py` that writes
`tests/phase3-digests.json` from the maps on disk, and two hand edits to prose. No model call.

## Files

```aeo-independence
slice: 04-gate
creates: tests/phase3-digests.json
edits: src/rlm/pin.py
edits: tests/test_phase3.py
edits: PLAN.md
edits: README.md
depends-on: 03-map-northwind-northstar
```

## Out of scope

Any phase 4 issue. A cluster recall below 100 or a decoy in a cluster on any sample is written
into the status row and traced to the slice that owns it, which is a new phase 3 issue, not a
relaxed bar.
