# feat(phase-3): consequence links and versions on sample 1: DR-048's series breaks at the incident week, DR-096 is a model dated after it, DR-069 and DR-070 are draft and final [slice 02]

**Issue:** #54 · **Spec:** PLAN.md#4-phases, row "3 Map" · **Plan:** plans/phase-3/02-consequences-ranked-atlas.md
**Depends on:** #53
**Labels:** phase-3

## Deliverable

`runs/atlas/map.json`'s first matter carries `versions` and `consequences` read off the index
and the notes. The `ranked` list places every required document above every decoy. Two runs are
byte-identical.

## Mechanism

`src/rlm/map.py` gains two readers. A `series-break` is an index `series` record whose
consecutive periods carry values that turn at a period within seven days of the matter's date,
in a document not seeded by identifiers (the index's own series values, no model call). A
`model-after` is a document whose note says model, forecast, synergy or plan and whose first
date is after the matter's date and whose figures share a value with a cluster document. Both
kinds add to the document's score so DR-048 and DR-096 rank by their own link (the first
build's corpus-only map missed these). The test reads from the key only the incident-start
date and the forensic-draft, forensic-final, step-down and synergy-npv document ids.

## Acceptance criterion

Given slice 01 is merged,
when `python -m rlm.map samples/atlas runs/atlas` runs and `pytest -q tests/test_phase3.py`
runs,
then the first matter's `versions` array holds one pair object with keys `docs` (the two ids),
`dates` (the two dates in order), and `status` (the two status arrays in order); `consequences`
holds one `series-break` object with keys `doc` (DR-048), `series` (the series name), `period`
(the period where it turns), and `anchor` (a section anchor); one `model-after` object with
keys `doc` (DR-096), `date`, and `anchor`; every required document's score is above every
decoy's score (read off `ranked`); two runs are byte-identical; the readout adds version and
consequence counts; all prior tests pass; and no line of code reads the key's facts except to
construct the test's before-and-after assertion.

## Files

```aeo-independence
slice: 02-consequences-ranked-atlas
edits: src/rlm/map.py
edits: tests/test_phase3.py
depends-on: 01-map-atlas
```

## Out of scope

Samples 2 and 3. Digests. The dossier's reading of these links (phase 4). A document not
reaching its target rank is reported with its score and the consequences that raised it; the
code is revised, not the threshold tuned.
