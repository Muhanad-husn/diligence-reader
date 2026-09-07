# 03: Dossier on samples 2 and 3, the decoy separated by clause

Issue: [#65](https://github.com/Muhanad-husn/RLM/issues/65)

## Goal

`runs/northwind/dossier.md` and `runs/northstar-dental/dossier.md` pass the slice 01 and 02
tests with sample 1's dossier unchanged. On `northwind` the first matter's document set holds
the four hero documents and not `msa_granite_manufacturing.pdf.md`, which is ranked below all
four; on `northstar-dental` it holds `cim.md`, `revenue_summary.xlsx` and
`board_materials/q1-board-update.md`.

## Acceptance criterion

Given slice 02 is merged and the pinned notes and maps of the three samples match their
digests,
when `python -m rlm.dossier` runs on `northwind` and `northstar-dental` and `pytest -q
tests/test_phase3.py tests/test_phase4.py` runs on all three samples,
then every phase 4 test passes on the three samples: on `northwind` the set is the key's
`hero-documents` fact with no decoy, the decoy ranks below every hero document, and the
`Comparisons` section carries `deck-vs-msa-coc` (the board deck's `No customer-termination,
change-of-control, or contract-portability items are flagged` against the Meridian MSA's
`effective immediately`) and `contractor-vs-employee-ip` (`contains no provision assigning`
against `hereby irrevocably assigns`), each with both anchors; on `northstar-dental` the set
is the key's `matter-documents` fact and the `Comparisons` section carries
`growth-claimed-vs-actual` (`18.0%` against `11.7%`) with both anchors; sample 1's
`dossier.md` and the three `map.json` files are byte-identical to what slice 02 produced
(their sha256 are in the pull request body); and the readout prints the slice 01 and 02
lines for all three samples.

## Mechanism

The same module. The rule that separates Granite from Meridian is the document set rule: a
document is in the matter's set when the map ranks it inside the cluster and one of its own
flag quotes or figures carries a defining value of the matter. A defining value is a value
shared by the seed's note and at least one other cluster document's note through their
figures or cross references (on `northwind`: `Meridian Freight Corporation` and
`$12,400,000`; on `atlas`: the backup object, the signing key, the ticket). The Granite
MSA's note flags termination for cause, insolvency and no termination for convenience; it
carries neither defining value in any flag quote or figure, so the rule leaves it out and the
map's template values do not carry it in. The `Comparisons` rules of slice 02 reach the two
`northwind` pairs as they are: the board deck's flag with the words `change-of-control` and
`flagged` against the MSA's termination flag (the covenant rule, widened to a flag that shares
a word with the other flag), and the contractor agreement's `assigning` against the employment
agreement's `assigns` (the same rule). On `northstar-dental` the CIM's `18.0%` figure against
the workbook's `11.7%` is two percentage figures whose quotes share the word `growth` in two
set documents.

A fix that sample 2 or 3 needs is made once and sample 1 is rerun; a fix that moves sample
1's dossier is reported, not hidden. No key value is read by the code.

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
edges between them, and the founder decides; it is the phase's first attempt, not a relaxed
test.
