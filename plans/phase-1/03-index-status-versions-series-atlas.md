# 03: The index: status words, version pairs, series, on sample 1

Issue: to be filed

## Goal

The index carries the three things phases 3 and 4 read that are not a number, a date or a name:
what state a document is in, which two documents are the same matter at two moments, and which
things are a series with a step, so that phase 3 can see a series break at a cluster's date.

## Acceptance criterion

Given slice 02 is merged,
when `pytest -q tests/test_phase1.py -k "status or versions or series"` runs,
then `runs/atlas/index.jsonl` also holds records of kind `status`, `version-pair` and `series`,
two runs are byte identical, and on sample 1:

- `Network_Quality_Ticket_NQ17_Redacted.txt` and
  `Outside_Counsel_Privacy_Risk_Memo_Redacted.pdf` carry status `redacted`, the counsel memo also
  carries `privileged`, `Draft_Financials_FY2025.pdf` carries `draft`, and the two audited years
  carry `final`.
- `Aurora_Phase1_Technical_Findings_Draft.pdf` and `Aurora_Executive_Summary_Final.pdf` are one
  `version-pair`, ordered draft 2025-11-12 then final 2025-11-20.
- The four `Monthly_Finance_Pack_2025_*.pdf` files are one document series with step `month` and
  their four members in order.
- `VistaMail_KPI_Weekly_Q4_2025.csv` is one row series with step `week` on the `week_start`
  column, and `User_Metrics_Dashboard_Q3_Q4_2025.xlsx` is a row series on its own period column.
- No document is in more than one version pair, and no false version pair is produced.

`tests/phase1-digests.json` records the sha256 of sample 1's `sections.jsonl` and `index.jsonl`.

## Mechanism

- No skill, plugin or MCP fits. Three rules over the sections and the file names, in
  `src/rlm/index.py`.
- Status: the five words `draft`, `final`, `redacted`, `privileged`, `confidential`, matched in
  the file name and in the document's own first sections, anchored to the line that says it. A
  status is a document-level record with one anchor as its proof.
- **Version pair, and why the obvious rule fails here.** The corpus's one version pair is
  `Aurora_Phase1_Technical_Findings_Draft.pdf` against `Aurora_Executive_Summary_Final.pdf`.
  Their file names do not differ only in a status word; the stems differ entirely. A file-name
  rule would miss the single most important pair in the room. The rule is therefore: two
  documents that share an identifier already in the index from slice 02, carry opposite status
  words, and carry dates that order them. `AURORA` is that identifier here. Two candidates for
  the same identifier is a warning in the coverage line, not a guess. `Draft_Financials_FY2025`
  has no final in the room and correctly produces no pair, which is itself something phase 4
  reads.
- **Series, in two forms, because the corpus has both.** A document series is two or more files
  whose names share a stem and differ in a period token that parses as a month, a quarter or a
  week; the four monthly finance packs are one. A row series is a table, a CSV or a workbook
  sheet, with a column whose cells parse as consecutive periods; `VistaMail_KPI_Weekly_Q4_2025.csv`
  has `week_start` and is one. Both write the same record kind, with `step` and ordered members,
  members being documents in the first form and anchors in the second.
- No model call, no gateway call.

## The three records

```json
{"kind": "status", "surface": "REDACTED", "value": "redacted", "unit": null,
 "docs": ["data_room/06_Legal_Regulatory_and_Compliance/Outside_Counsel_Privacy_Risk_Memo_Redacted.pdf"],
 "anchors": ["data_room/06_Legal_Regulatory_and_Compliance/Outside_Counsel_Privacy_Risk_Memo_Redacted.pdf#p1l3"],
 "context": "PRIVILEGED AND CONFIDENTIAL - REDACTED"}
```

```json
{"kind": "version-pair", "surface": "AURORA", "unit": null,
 "value": {"draft": "...Aurora_Phase1_Technical_Findings_Draft.pdf", "draft_date": "2025-11-12",
           "final": "...Aurora_Executive_Summary_Final.pdf", "final_date": "2025-11-20"},
 "docs": ["...Aurora_Phase1_Technical_Findings_Draft.pdf", "...Aurora_Executive_Summary_Final.pdf"],
 "anchors": ["...Aurora_Phase1_Technical_Findings_Draft.pdf#p1l1", "...Aurora_Executive_Summary_Final.pdf#p1l1"],
 "context": "AURORA, draft 2025-11-12 and final 2025-11-20"}
```

```json
{"kind": "series", "surface": "week_start", "unit": null,
 "value": {"step": "week", "form": "rows",
           "members": ["...VistaMail_KPI_Weekly_Q4_2025.csv#r2", "...VistaMail_KPI_Weekly_Q4_2025.csv#r3"]},
 "docs": ["data_room/04_Product_Data_and_Technology/VistaMail_KPI_Weekly_Q4_2025.csv"],
 "anchors": ["data_room/04_Product_Data_and_Technology/VistaMail_KPI_Weekly_Q4_2025.csv#r1"],
 "context": "Weekly KPI rows from 2025-09-01"}
```

## Files

```aeo-independence
slice: 03-index-status-versions-series-atlas
edits: src/rlm/index.py
edits: tests/test_phase1.py
creates: tests/phase1-digests.json
depends-on: 01-sections-atlas
```

## Out of scope

Samples 2 and 3, which have no version pair and no monthly series and must therefore produce
empty sets without producing a false one. Reading what changed between a draft and its final,
and reading where a series breaks: both are phase 3 and phase 4, and this slice only says the
pair and the series exist.
