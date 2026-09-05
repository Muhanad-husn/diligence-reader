# feat(phase-1): sections and index on samples 2 and 3, sample 1's digest unmoved [slice 04]

**Issue:** #17 · **Spec:** PLAN.md#4-phases, row "1 Ingest" · **Plan:** plans/phase-1/04-ingest-northwind-northstar.md
**Depends on:** #15, #16
**Labels:** phase-1

## Deliverable

`runs/northwind/` and `runs/northstar-dental/` each hold `sections.jsonl` and `index.jsonl`, built by the same ingest that built sample 1's, with the enabled-sample tuple in `tests/test_phase1.py` emptied so all three samples run. Sample 1's two artefacts come out byte for byte as slice 03 left them.

## Mechanism

Sample 2 is twelve markdown files, one of them a rendering of a workbook. Sample 3 is eleven markdown files and two real workbooks, so `11.7%` is read from `revenue_summary.xlsx` and from nowhere else. Both are already covered by the readers slice 01 wrote. Any change to `src/rlm/` in this slice must be a reader or an extractor that samples 2 and 3 exercise and sample 1 does not; the unmoved digest in `tests/phase1-digests.json` is what proves it, and a change that moves sample 1's output is a gap in slices 01 to 03 and goes back there as a new issue in this phase. Ingest reads a sample's documents as `key.documents` names them and nothing else, so nothing under `metadata/`, `fixtures/` or `key/` is ever sectioned. No model call, no gateway call.

## Acceptance criterion

Given slices 02 and 03 are merged,
when `pytest -q tests/test_phase1.py` runs with all three samples enabled,
then every phase 1 test passes on `atlas`, `northwind` and `northstar-dental`; the seven phase 1 facts of northwind and the eight of northstar-dental are each in the index against one of their own documents; `$12,400,000` in `arr_schedule.xlsx.md` and `$12.4m` in the key normalise to the same amount; `11.7%` is read from `revenue_summary.xlsx`; the two samples produce no version pair and no false series; and the sha256 of sample 1's two artefacts still equal what slice 03 wrote into `tests/phase1-digests.json`.

## Files

```aeo-independence
slice: 04-ingest-northwind-northstar
edits: tests/test_phase1.py
edits: tests/phase1-digests.json
depends-on: 02-index-atlas
depends-on: 03-index-status-versions-series-atlas
```

## Out of scope

Sample 4, which is phase 7. Any tuning of a section boundary or an extractor to make these two samples pass where the same change moves sample 1: that is the gap this slice exists to expose, and it is reported, not absorbed.
