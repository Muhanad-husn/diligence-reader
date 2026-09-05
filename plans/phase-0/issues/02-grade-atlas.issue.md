# feat(phase-0): the grader, calibrated on sample 1's perfect and wrong reports [slice 02]

**Issue:** #2 · **Spec:** PLAN.md#4-phases, row "0 Fixtures" · **Plan:** plans/phase-0/02-grade-atlas.md
**Depends on:** #1
**Labels:** phase-0

## Deliverable

`src/rlm/grade.py`: planted-fact recall by code and a rubric score from a Claude subagent run on the subscription, writing `runs/<sample>/grade-<name>.json` with recall, per-criterion points, the grader model id and elapsed seconds. Two hand-written reports under `samples/atlas/fixtures/`: `report-perfect.md`, built from the answer key's gold-standard answer and price bridge in the brief's five sections citing all fourteen required documents, and `report-wrong.md`, which elevates DR-031 tax nexus, calls the security matter routine credential hygiene, gives no exposure number and recommends "raise in Q&A". The grader gives them 100 and under 40.

## Mechanism

Recall: a fact is recalled when its normalised value (whitespace collapsed, case folded, thousands separators and currency marks dropped, `m` and `million` equal) appears in the report and one of its documents is cited anywhere in the report. Rubric: one `subprocess` call to `claude -p --output-format json` with the rubric rows, the answer key and the report, returning points and a one-line reason per criterion. No SDK, no gateway; `OPENROUTER_API_KEY` is never read and `LEDGER.md` does not move. Score is the rubric total where the key has a rubric, else recall.

## Acceptance criterion

Given sample 1's key from slice 01 and the two fixture reports,
when `pytest -q tests/test_phase0.py -k grade` runs,
then for sample `atlas` the perfect report scores 100 with planted-fact recall 100%, the wrong report scores under 40, `runs/atlas/grade-perfect.json` and `grade-wrong.json` exist with recall, per-criterion rubric points, the grader model id and elapsed seconds, and `LEDGER.md` is unchanged.

## Files

```aeo-independence
slice: 02-grade-atlas
creates: src/rlm/grade.py
creates: samples/atlas/fixtures/report-perfect.md
creates: samples/atlas/fixtures/report-wrong.md
edits: tests/test_phase0.py
depends-on: 01-key-atlas
```

## Out of scope

Two-run spread (the gate). The verifier. Reports for samples 2 and 3. Any grading of a run artefact.
