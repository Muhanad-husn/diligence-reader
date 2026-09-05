# feat(phase-0): the key shape, and sample 1's key and brief [slice 01]

**Issue:** #1 · **Spec:** PLAN.md#4-phases, row "0 Fixtures" · **Plan:** plans/phase-0/01-key-atlas.md
**Depends on:** none
**Labels:** phase-0

## Deliverable

`samples/atlas/key.json` in the shape every sample will share, loaded by `src/rlm/key.py`, with `samples/atlas/brief.md` beside it. The key pins the `DR-###` to file map, the fourteen required documents, the five decoys, every planted fact with its documents and the first phase that must carry it, the answer (400, range 375 to 525, USD millions), and the nine rubric rows. `tests/test_phase0.py` checks the key against the sample; `tests/conftest.py` skips a sample whose key does not exist yet.

## Mechanism

Hand-written data from `samples/atlas/key/expected_findings.json` and `ANSWER_KEY_DO_NOT_INGEST.md`. The id to file map is derived once at authoring time from `Data_Room_Index.xlsx` with `openpyxl`, title tokens against file names as the winner's `extract_corpus.py` did, then pinned into the key. No model call. The shape is in the plan file.

## Acceptance criterion

Given `samples/atlas/key.json` and `samples/atlas/brief.md` exist,
when `pytest -q tests/test_phase0.py -k key` runs,
then for sample `atlas` the key loads, every fact's documents resolve to existing files, every fact names a phase from 1 to 5, the fourteen required documents and the five decoys are disjoint, the answer carries the number 400 with range 375 to 525, and the brief exists. Samples `northwind` and `northstar-dental` are skipped with the reason "no key.json yet".

## Files

```aeo-independence
slice: 01-key-atlas
creates: samples/atlas/key.json
creates: samples/atlas/brief.md
creates: src/rlm/key.py
creates: tests/test_phase0.py
edits: tests/conftest.py
```

## Out of scope

The grader, the perfect and wrong reports, and the keys of samples 2 and 3. The phase 1 check that every planted number is in the index.
