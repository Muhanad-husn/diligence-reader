# feat(phase-4): dossier.md on samples 2 and 3, the Granite MSA separated from the Meridian matter by clause content [slice 03]

**Issue:** #65 · **Spec:** PLAN.md#4-phases, row "4 Dossier" · **Plan:** plans/phase-4/03-dossier-northwind-northstar.md
**Depends on:** #64
**Labels:** phase-4

## Deliverable

`runs/northwind/dossier.md` and `runs/northstar-dental/dossier.md` pass the slice 01 and 02
tests with sample 1's dossier and the three maps unchanged. On `northwind` the first matter's
set is the four hero documents, `msa_granite_manufacturing.pdf.md` is outside it and ranked
below all four, and the comparisons carry the board deck against the Meridian MSA's
change-of-control clause and the contractor agreement against the employment IP agreement.
On `northstar-dental` the set is the CIM, the revenue workbook and the Q1 board update, and
the comparison is the CIM's `18.0%` against the workbook's `11.7%`. This slice owns the two
decoy checks moved from phase 3 on 2026-09-07 (#55, PR #61).

## Mechanism

The same module. The set rule: a document is in the matter's set when the map ranks it
inside the cluster and one of its own flag quotes or figures carries a defining value of the
matter, a value shared by the seed's note and at least one other cluster document's note
through figures or cross references (`Meridian Freight Corporation`, `$12,400,000`). The
Granite MSA's note flags termination for cause, insolvency and no termination for
convenience and carries neither value, so it stays out; the map's template values do not
carry it in. The slice 02 covenant rule widens to a flag that shares a word with the other
flag, which reaches the deck's `change-of-control ... flagged` against the MSA's termination
clause and the contractor's `assigning` against the employee's `assigns`. Two percentage
figures whose quotes share the word `growth` in two set documents give the `northstar-dental`
comparison. A fix sample 2 or 3 needs is made once and sample 1 rerun; a fix that moves
sample 1 is reported, not hidden. No key value is read by the code. Tests are committed red
first.

## Acceptance criterion

Given slice 02 is merged and the pinned notes and maps of the three samples match their
digests,
when `python -m rlm.dossier` runs on `northwind` and `northstar-dental` and `pytest -q
tests/test_phase3.py tests/test_phase4.py` runs on all three samples,
then every phase 4 test passes on the three samples: on `northwind` the set is the key's
`hero-documents` fact with no decoy, the decoy ranks below every hero document, and
`Comparisons` carries `deck-vs-msa-coc` and `contractor-vs-employee-ip` with both anchors
each; on `northstar-dental` the set is the key's `matter-documents` fact and `Comparisons`
carries `growth-claimed-vs-actual` with both anchors; every phase 1 and 2 fact of both
samples has a row with its value and a resolving anchor; sample 1's `dossier.md` and the
three `map.json` files are byte-identical to what slice 02 produced (their sha256 in the pull
request body); the readout prints the slice 01 and 02 lines for all three samples; and all
phase 0 to 3 tests still pass.

## Files

```aeo-independence
slice: 03-dossier-northwind-northstar
edits: src/rlm/dossier.py
edits: tests/test_phase4.py
depends-on: 02-comparisons-atlas
```

## Out of scope

Digests, the status row, the founder's reading, sample 4. If no set rule separates Granite
from Meridian without moving sample 1, that is reported with both notes' flags and the map's
edges between them and the founder decides; it is the phase's first attempt, not a relaxed
test.
