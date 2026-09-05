# feat(phase-0): keys and briefs for samples 2 and 3 [slice 03]

**Issue:** #3 · **Spec:** PLAN.md#4-phases, row "0 Fixtures" · **Plan:** plans/phase-0/03-keys-northwind-northstar.md
**Depends on:** #1
**Labels:** phase-0

## Deliverable

`samples/northwind/key.json` and `samples/northstar-dental/key.json` in the shape slice 01 fixed, loaded by the same `src/rlm/key.py` with no change, and a `brief.md` beside each in the shape of sample 1's brief. Document ids are file paths relative to the sample. Northwind's answer is 12.4 (USD millions, the revenue cliff at close); its decoy is the Granite consent clause. Northstar's answer is 11.7 (percent, the true growth against the CIM's 18.0%). Neither has a rubric.

## Mechanism

Hand-written data from `samples/northwind/upstream-README.md` and `samples/northstar-dental/metadata/` (contradictions, ground-truth questions, entities). Briefs copy sample 1's brief structure: the deal and the parties, the five deliverables, the ground rules, the folder table. A brief names the deal and the folders, never a planted fact. No model call.

## Acceptance criterion

Given the two keys and two briefs exist,
when `pytest -q tests/test_phase0.py -k key` runs,
then it passes on all three samples with no change to `src/rlm/key.py` or the test, every document each key names resolves to a file in its sample, and the answer of `northwind` carries 12.4 and of `northstar-dental` carries 11.7.

## Files

```aeo-independence
slice: 03-keys-northwind-northstar
creates: samples/northwind/key.json
creates: samples/northwind/brief.md
creates: samples/northstar-dental/key.json
creates: samples/northstar-dental/brief.md
depends-on: 01-key-atlas
```

## Out of scope

Reports and grading for these samples. If slice 01's shape cannot hold one of these keys, that is `spec-drift` on this issue, fixed in `src/rlm/key.py` here with the reason in the pull request body.
