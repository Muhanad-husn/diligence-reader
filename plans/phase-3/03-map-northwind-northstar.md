# 03: Map on samples 2 and 3

Issue: [#55](https://github.com/Muhanad-husn/RLM/issues/55)

## Goal

`runs/northwind/map.json` and `runs/northstar-dental/map.json` pass the slice 01 and 02 tests
with sample 1's map unchanged: on `northwind` the first matter's cluster holds the four hero
documents and not `msa_granite_manufacturing.pdf.md`; on `northstar-dental` it holds
`cim.md`, `revenue_summary.xlsx` and `board_materials/q1-board-update.md`.

## Acceptance criterion

Given slice 02 is merged and the pinned notes of the three samples match their digests,
when `python -m rlm.map` runs on `northwind` and `northstar-dental` and `pytest -q
tests/test_phase3.py` runs on all three samples,
then every phase 3 test passes on the three samples; sample 1's `map.json` is byte-identical
to the one slice 02 produced (its sha256 is in the pull request body); and the readout prints
the slice 01 and 02 lines for all three samples.

## Mechanism

The same module. Two risks the builder names in the pull request rather than tunes around: on
`northwind` the three master service agreements share their boilerplate names and the phrase
`Change of Control`, so a map that weighs a value by the count of documents carrying it must
put `Meridian Freight` (in the MSA, the ARR schedule and the board deck) above `Change of
Control` (in the Meridian MSA, the Granite MSA and the cap table); and on `northstar-dental`
the CIM and the workbook are linked by the growth figures and the board update by the 2025
revenue figure, so the `date` and `cross-reference` edges carry the cluster where identifiers
are few. A fix that sample 2 or 3 needs is made once and sample 1 is rerun; a fix that moves
sample 1's cluster is reported, not hidden. No key value is read by the code.

## Files

```aeo-independence
slice: 03-map-northwind-northstar
edits: src/rlm/map.py
edits: tests/test_phase3.py
depends-on: 02-consequences-ranked-atlas
```

## Out of scope

Digests, the status row, sample 4.
