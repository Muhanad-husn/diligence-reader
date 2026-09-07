# 04: Phase 4 gate

Issue: [#66](https://github.com/Muhanad-husn/RLM/issues/66)

## Goal

The phase 4 tests pass on all three samples in one run with no code change between them,
`dossier.md` is pinned by digest per sample in `tests/phase4-digests.json`, the founder has
read sample 1's dossier once as a reader, and `PLAN.md` section 4a's phase 4 row carries the
numbers.

## Acceptance criterion

Given slices 01 to 03 are merged,
when `pytest -q` runs,
then every phase 0, 1, 2, 3 and 4 test passes on `atlas`, `northwind` and `northstar-dental`;
`tests/phase4-digests.json` holds the sha256 of each sample's `dossier.md` and a test asserts
the file on disk matches it; `python -m rlm.pin --dossiers` writes that file from the
dossiers on disk and refuses a sample with no dossier; `LEDGER.md` gained no phase 4 line;
`PLAN.md` section 4a's phase 4 row reads state `done`, the three planted recall scores (phase
1 to 4 facts found in the dossier, as a percentage), dollars 0, spread 0 (two runs
byte-identical, by the slice 01 test), and the date; `README.md`'s status line says phase 4
done and the spend so far; and the pull request body carries the three numbers, the sha256 of
the three dossiers, and `runs/atlas/dossier.md` in full for the founder to read once as a
reader before merging.

## Mechanism

`pytest -q`, a `--dossiers` mode in `src/rlm/pin.py` beside `--maps` that writes
`tests/phase4-digests.json` from the dossiers on disk, and two hand edits to prose. No model
call.

## Files

```aeo-independence
slice: 04-gate
creates: tests/phase4-digests.json
edits: src/rlm/pin.py
edits: tests/test_phase4.py
edits: PLAN.md
edits: README.md
depends-on: 03-dossier-northwind-northstar
```

## Out of scope

Any phase 5 issue. A recall below 100 or a decoy in a set on any sample is written into the
status row and traced to the slice that owns it, which is a new phase 4 issue, not a relaxed
bar. What the founder's reading finds wrong in the dossier as prose is a new phase 4 issue
too.
