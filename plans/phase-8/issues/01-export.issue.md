# feat(phase-8): report.docx, report.pdf and evidence.csv built from report.md, every planted fact read out of each [slice 01]

**Issue:** #136 · **Spec:** PLAN.md#4c-phase-8-the-product · **Plan:** plans/phase-8/01-export.md
**Labels:** phase-8

## Deliverable

`python -m rlm.export <run_dir>` reads report.md and writes report.docx and report.pdf from the same Markdown, and evidence.csv holding the `## Evidence` section's table alone, UTF-8 with a byte order mark and CRLF line ends so Excel opens it cleanly. The same report gives the same CSV bytes and the same docx and PDF text every time. Exposed as a function `export(run_dir)` the command calls in slice 02.

## Mechanism

Library. Word through pandoc, bundled by the `pypandoc-binary` package so a pipx install needs no system pandoc. PDF through pandoc to HTML then WeasyPrint. CSV by the standard `csv` module over the Evidence table rows.

Survey: no skill or MCP builds docx/PDF inside the tool at run time; the docx and pdf skills are for a session, not for shipped code; a model call is pointless for a format conversion.

## Acceptance criterion

Given the pinned report.md of samples 1, 2 and 3 in the main checkout's runs/, when `python -m rlm.export` runs on each twice, then the planted-fact recall that `rlm.grade.measure_recall` reads from the text of report.docx, of report.pdf and of evidence.csv equals its recall from report.md, 100 on each sample; evidence.csv has one row per row of the Evidence table plus the header; the two exports give byte-identical evidence.csv and identical docx and PDF text. If a planted fact is in report.md but not in the Evidence section, the CSV assertion names it and the slice reports it rather than weakening the test.

## Files

```aeo-independence
slice: 01-export
creates: src/rlm/export.py
creates: tests/test_phase8_export.py
edits: pyproject.toml
```

## Out of scope

An Excel workbook; styling beyond a readable default; the command and the web page.
