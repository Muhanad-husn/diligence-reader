# feat(phase-3): map.json on samples 2 and 3: the four Meridian documents without Granite, the three Northstar growth documents [slice 03]

**Issue:** #55 · **Spec:** PLAN.md#4-phases, row "3 Map" · **Plan:** plans/phase-3/03-map-northwind-northstar.md
**Depends on:** #54
**Labels:** phase-3

## Deliverable

`runs/northwind/map.json` and `runs/northstar-dental/map.json` exist and pass the slice 01
and 02 tests with sample 1's map unchanged. On `northwind` the first matter's cluster holds
the four hero documents and not the Granite MSA. On `northstar-dental` it holds the CIM, the
revenue workbook and the board update. All phase 3 tests pass on all three samples.

## Mechanism

The same module. The builder names two risks rather than tunes around them: on `northwind` the
three MSAs share boilerplate and the phrase `Change of Control` so the ranking must separate
`Meridian Freight` (three documents) from `Change of Control` (four); on `northstar-dental`
the CIM and workbook are linked by growth figures and the board update by 2025 revenue so
`date` and `cross-reference` edges must carry the cluster where identifiers are few. A fix
that sample 2 or 3 needs is made once and sample 1 is rerun; a fix that moves sample 1's
cluster is reported, not hidden. No key value is read by the code.

## Acceptance criterion

Given slice 02 is merged and the pinned notes for the three samples match their phase 2
digests,
when `python -m rlm.map` runs on `northwind` and `northstar-dental` and then `pytest -q
tests/test_phase3.py` runs on all three samples,
then every phase 3 test passes on `atlas`, `northwind` and `northstar-dental`; sample 1's
`map.json` is byte-identical to the slice 02 output (its sha256 is in the pull request body);
on `northwind` the first matter's cluster contains all ids in the key's `matter-documents`
(the four hero paths) and not the decoy (Granite); on `northstar-dental` the cluster contains
all three key documents and no decoy; the readout prints the slice 01 and 02 metrics for all
three samples; all prior tests pass; and no line of code reads the key's facts except to
construct the test's before-and-after assertion.

## Files

```aeo-independence
slice: 03-map-northwind-northstar
edits: src/rlm/map.py
edits: tests/test_phase3.py
depends-on: 02-consequences-ranked-atlas
```

## Out of scope

Digests, the status row, sample 4. A cluster recall below 100 or a decoy in a cluster on
sample 2 or 3 is not acceptable; the code is revised, not the test loosened.
