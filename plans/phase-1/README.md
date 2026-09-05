# Phase 1: Ingest

Milestone `Phase 1`. Spec: `PLAN.md` section 4, row "1 Ingest". Cap $0, no model call, no gateway
call, so `LEDGER.md` does not move in this phase.

The outcome: `runs/<sample>/sections.jsonl` and `runs/<sample>/index.jsonl` exist for all three
gate samples, built by code alone from the raw files. Every document a key names has sections.
Every planted quote and identifier resolves to a section anchor in one of its own documents.
Every planted number and date is in the index against one of its own documents, matched on a
normalised value rather than on the surface string. Two runs of the same sample are byte
identical.

## The shape decisions this phase fixes

- **A document is its path.** Ingest never reads a key. A section's `doc` is the file path
  relative to the sample root, and the test maps a key's `DR-069` to that path through
  `key.documents`. Nothing downstream derives an id map again.
- **One section shape, two flavours.** A section is text or a table row. Both carry `doc`,
  `ordinal`, `kind`, `anchor`, `heading`, `text` and `warning`. A table row also carries `cells`,
  each with its own cell reference. `text` is what a later stage quotes; `cells` is what it
  computes from.
- **The anchor is one string and it is the citation.** `<doc>#p2l14` for a PDF page and line,
  `<doc>#l14` for plain text, markdown and a single mail message, `<doc>#m3l14` for a message
  inside an mbox, `<doc>#Sheet1!A14` for a workbook cell, `<doc>#r14` for a CSV row. The report
  in phase 5 cites this string and the verifier resolves it back to the file.
- **The index normalises, and the test normalises the key the same way.** `$12,400,000` in
  `arr_schedule.xlsx.md` and `$12.4m` in the key are the same amount because
  `src/rlm/amounts.py` maps both to `12400000.0 USD`. The same function is applied to both
  sides, so no rule is tuned against a key value. The same holds for
  `twenty-four (24) months`, `45-day`, `36-month`, `912.8m` and `30.1%`.
- **Seven index kinds and no more:** `date`, `amount`, `name`, `identifier`, `status`,
  `version-pair`, `series`. They are the seven `PLAN.md` section 2 names for this stage. A
  record carries `docs` and `anchors` as lists, so a version pair and a series have the same
  shape as an amount.
- **Nothing is quietly repaired.** Where two PDF engines disagree on a page, the section is
  written with a `warning` naming the disagreement and the run's coverage line counts it. No
  third parser, no retry, no model call.
- **Determinism is pinned, not asserted.** `tests/phase1-digests.json` holds the sha256 of each
  sample's two artefacts. Slice 03 writes sample 1's; slice 04 must not move it while adding
  samples 2 and 3. `pyproject.toml` pins `pdftext` to an exact version so the digest means
  something across machines.
- **A sample whose ingest is not enabled yet is skipped, not failed.** `tests/test_phase1.py`
  carries the tuple of enabled samples and skips the rest with the reason "ingest not enabled
  for this sample yet", the way `tests/conftest.py` skips a sample with no key. Slice 04 empties
  the skip.

## Slices

| NN | Slice | Plan | Issue | Depends on |
|---|---|---|---|---|
| 01 | Sections and anchors on sample 1, all seven formats | [01-sections-atlas.md](01-sections-atlas.md) | #14 | none |
| 02 | The index: dates, amounts, names, identifiers, on sample 1 | [02-index-atlas.md](02-index-atlas.md) | #15 | 01 |
| 03 | The index: status words, version pairs, series, on sample 1 | [03-index-status-versions-series-atlas.md](03-index-status-versions-series-atlas.md) | #16 | 01 |
| 04 | Sections and index on samples 2 and 3, sample 1's digest unmoved | [04-ingest-northwind-northstar.md](04-ingest-northwind-northstar.md) | #17 | 02, 03 |
| 05 | Phase 1 gate | [05-gate.md](05-gate.md) | #18 | 04 |

Order of work: 01, then 02 and 03 concurrently, then 04, then 05.

## What sample 1 makes this phase carry

100 documents in six formats: 61 PDF, 29 XLSX, 7 CSV, 1 TXT, 1 EML, 1 MBOX. Twenty-nine of the
key's fifty-three facts are phase 1 facts, and they sit across every one of those formats: 29
document references into PDFs, 16 into workbooks, 6 into the redacted ticket text, 4 into the
insurance notice email and 3 into CSV exports. There is no format this phase can defer.

Samples 2 and 3 are markdown and one workbook, so slice 04 is small by document count and is
the whole generality claim of the phase.
