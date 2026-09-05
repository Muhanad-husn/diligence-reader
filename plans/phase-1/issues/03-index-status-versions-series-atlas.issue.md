# feat(phase-1): the index: status words, version pairs, series, on sample 1 [slice 03]

**Issue:** #16 · **Spec:** PLAN.md#4-phases, row "1 Ingest" · **Plan:** plans/phase-1/03-index-status-versions-series-atlas.md
**Depends on:** #14
**Labels:** phase-1

## Deliverable

The three index kinds that are not a number, a date or a name: `status`, `version-pair` and `series`, written into `runs/atlas/index.jsonl` in the same record shape slice 02 fixed. These are what phase 3 reads to see a series break at a cluster's date and what phase 4 reads to set a draft against its final. `tests/phase1-digests.json` is created here, holding the sha256 of sample 1's `sections.jsonl` and `index.jsonl`.

## Mechanism

Three rules over the sections and the file names, in `src/rlm/index.py`. Status is the five words `draft`, `final`, `redacted`, `privileged`, `confidential`, matched in the file name and in the document's first sections and anchored to the line that says it. Version pair is not a file-name rule, and this matters: the room's one pair is `Aurora_Phase1_Technical_Findings_Draft.pdf` against `Aurora_Executive_Summary_Final.pdf`, whose stems differ entirely, so a name rule would miss the most important pair in the corpus. The rule is two documents that share an identifier already in the index from slice 02, carry opposite status words, and carry dates that order them; `AURORA` is that identifier. Series has two forms because the corpus has both: a document series over files whose names share a stem and differ in a period token, which is the four monthly finance packs, and a row series over a table whose column parses as consecutive periods, which is `week_start` in `VistaMail_KPI_Weekly_Q4_2025.csv`. Two candidates for one pair is a warning in the coverage line, not a guess. No model call, no gateway call.

## Acceptance criterion

Given slice 02 is merged,
when `pytest -q tests/test_phase1.py -k "status or versions or series"` runs,
then `runs/atlas/index.jsonl` holds records of the three kinds, two runs are byte identical, and on sample 1: the redacted ticket export and the redacted counsel memo carry `redacted` with the memo also carrying `privileged`; `Draft_Financials_FY2025.pdf` carries `draft` and the two audited years carry `final`; the two Aurora documents are one `version-pair` ordered draft 2025-11-12 then final 2025-11-20; the four `Monthly_Finance_Pack_2025_*.pdf` files are one document series with step `month` in order; `VistaMail_KPI_Weekly_Q4_2025.csv` is a row series with step `week` on `week_start` and `User_Metrics_Dashboard_Q3_Q4_2025.xlsx` is a row series on its own period column; no document is in more than one version pair and no false pair is produced; and `tests/phase1-digests.json` records both digests.

## Files

```aeo-independence
slice: 03-index-status-versions-series-atlas
edits: src/rlm/index.py
edits: tests/test_phase1.py
creates: tests/phase1-digests.json
depends-on: 01-sections-atlas
```

## Out of scope

Samples 2 and 3, which have no version pair and no monthly series and must produce empty sets without producing a false one. Reading what changed between a draft and its final, and reading where a series breaks: those are phases 4 and 3.
