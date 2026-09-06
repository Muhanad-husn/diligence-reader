# 02: Consequence links and versions on sample 1

Issue: [#54](https://github.com/Muhanad-husn/RLM/issues/54)

## Goal

`runs/atlas/map.json`'s first matter carries `versions` and `consequences` read off the index
and the notes, and its `ranked` list places every one of the fourteen required documents above
every decoy.

## Acceptance criterion

Given slice 01 is merged,
when `python -m rlm.map samples/atlas runs/atlas` runs and `pytest -q tests/test_phase3.py`
runs,
then the first matter's `versions` holds the pair DR-069 and DR-070 with their two dates and
status words (draft dated 2025-11-12, final 2025-11-20, read from the index's `version-pair`
record); `consequences` holds one `series-break` record naming DR-048, the series broken (the
weekly engagement metrics), the period at which it breaks, within seven days of the matter's
date, and an anchor; and one `model-after` record naming DR-096 with its date, later than the
matter's date, and an anchor; every required document's rank is above every decoy's rank; two
runs are byte-identical; the readout adds the count of versions and consequences. The test
reads the matter's date from the key's `incident-start` fact and the document ids from
`forensic-draft`, `forensic-final`, `step-down` and `synergy-npv` facts, and nothing else.

## Mechanism

`src/rlm/map.py` gains the two readers. A `series-break` is an index `series` record whose
consecutive periods carry values that turn (the index's own series values, no model) at a
period within seven days of the matter's date, in a document not already seeded by
identifiers. A `model-after` is a document whose note's `what` or folder says model, forecast,
synergy or plan and whose first date is after the matter's date and whose figures share a
value with a cluster document (615m MAU is in DR-096 and DR-048). Both kinds of consequence
add to the document's score so that DR-048 and DR-096 rank inside the cluster by their own
link and not by a hard-coded id (the first build's row 0a: the corpus-only map missed exactly
these). No model call, no new dependency.

## Files

```aeo-independence
slice: 02-consequences-ranked-atlas
edits: src/rlm/map.py
edits: tests/test_phase3.py
depends-on: 01-map-atlas
```

## Out of scope

Samples 2 and 3. Digests. The dossier's reading of these links (phase 4).
