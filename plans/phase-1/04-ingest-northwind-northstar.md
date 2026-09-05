# 04: Sections and index on samples 2 and 3, sample 1's digest unmoved

Issue: [#17](https://github.com/Muhanad-husn/RLM/issues/17)

## Goal

The ingest built for sample 1 reads samples 2 and 3, and sample 1's two artefacts come out byte
for byte as they were.

## Acceptance criterion

Given slices 02 and 03 are merged,
when `pytest -q tests/test_phase1.py` runs with the enabled-sample tuple emptied so all three
samples run,
then every phase 1 test passes on `atlas`, `northwind` and `northstar-dental`;
`runs/northwind/` and `runs/northstar-dental/` each hold `sections.jsonl` and `index.jsonl`;
the seven phase 1 facts of northwind and the eight of northstar-dental are each in the index
against one of their own documents; `$12,400,000` in `arr_schedule.xlsx.md` and `$12.4m` in the
key normalise to the same amount; `11.7%` is read from `revenue_summary.xlsx`, which no
markdown rendering carries; the two samples produce no version pair and no false series; and the
sha256 of sample 1's `sections.jsonl` and `index.jsonl` still equal the values slice 03 wrote
into `tests/phase1-digests.json`.

## Mechanism

- No skill, plugin or MCP fits.
- Sample 2 is twelve markdown files, one of them a rendering of a workbook, read by the markdown
  reader from slice 01. Sample 3 is eleven markdown files and two real workbooks, read by the
  markdown and `openpyxl` readers from slice 01.
- Any change to `src/rlm/` in this slice must be a reader or an extractor that samples 2 and 3
  exercise and sample 1 does not. The unmoved digest is what proves it: a change that alters
  sample 1's output is a gap in slices 01 to 03 and goes back there as a new issue in this phase,
  not a widening of this one.
- Sample 3's `metadata/` directory holds the raw key and is not a document. Ingest reads the
  sample's documents as `key.documents` names them and nothing else, so nothing under
  `metadata/`, `fixtures/` or `key/` is ever sectioned.
- No model call, no gateway call.

## Files

```aeo-independence
slice: 04-ingest-northwind-northstar
edits: tests/test_phase1.py
edits: tests/phase1-digests.json
depends-on: 02-index-atlas
depends-on: 03-index-status-versions-series-atlas
```

## Out of scope

Sample 4, which is phase 7. Any tuning of a section boundary or an extractor to make one of
these two samples pass where the same change moves sample 1: that is the gap this slice exists
to expose, and it is reported, not absorbed.
