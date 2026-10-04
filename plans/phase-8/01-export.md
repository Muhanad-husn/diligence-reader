# Slice 01: Export

Milestone `Phase 8`. Issue: [#136](https://github.com/Muhanad-husn/diligence-reader/issues/136). Spec: `PLAN.md#4c-phase-8-the-product`. Depends on: none.

## Deliverable

`python -m rlm.export <run_dir>` reads report.md and writes report.docx and report.pdf from the same Markdown, and evidence.csv holding the `## Evidence` section's table alone, UTF-8 with a byte order mark and CRLF line ends so Excel opens it cleanly. The same report gives the same CSV bytes and the same docx and PDF text every time. Exposed as a function `export(run_dir)` the command calls in slice 02.

## Mechanism

Library. Word through pandoc, bundled by the `pypandoc-binary` package so a pipx install needs no system pandoc. PDF through pandoc to Typst source, compiled by the `typst` package, which ships as a wheel with no system libraries needed. WeasyPrint needs Pango and GTK, which pipx does not install on Windows or macOS. CSV by the standard `csv` module over the Evidence section's bullets, one row per bullet.

Survey: no skill or MCP builds docx/PDF inside the tool at run time; the docx and pdf skills are for a session, not for shipped code; a model call is pointless for a format conversion; the chosen approach is the library route, which keeps the run portable and self-contained.

## Acceptance criterion

Given the pinned report.md of samples 1, 2 and 3 in the main checkout's runs/, when `python -m rlm.export` runs on each twice, then the planted-fact recall that `rlm.grade.measure_recall` reads from the text of report.docx, of report.pdf and of evidence.csv equals its recall from report.md, 100 on each sample; evidence.csv has one row per bullet of the Evidence section plus the header; the two exports give byte-identical evidence.csv and identical docx and PDF text. If a planted fact is in report.md but not in the Evidence section, the CSV assertion names it and the slice reports it rather than weakening the test. On atlas, `price-reduction` is the one fact in report.md and not in the Evidence section, and the test names it.

## Tests

tests/test_phase8_export.py, parametrised over atlas, northwind, northstar-dental.

## Money

$0, no model call.

## Risks

A PDF line break or hyphen can split a quoted value; the test reads PDF text with whitespace normalised the way `rlm.grade.normalise` does, and a split that survives that is fixed in the Typst source, not in the test.

## Files

```aeo-independence
slice: 01-export
creates: src/rlm/export.py
creates: tests/test_phase8_export.py
edits: pyproject.toml
```

## Out of scope

An Excel workbook; styling beyond a readable default; the command and the web page.
