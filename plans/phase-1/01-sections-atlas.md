# 01: Sections and anchors on sample 1, all seven formats

Issue: [#14](https://github.com/Muhanad-husn/RLM/issues/14)

## Goal

`runs/atlas/sections.jsonl` exists, built by `src/rlm/ingest.py` from
`samples/atlas/data_room/` alone, with every one of the key's 100 documents sectioned and every
section carrying an anchor that resolves back to its file.

## Acceptance criterion

Given `samples/atlas/key.json` and the data room exist,
when `pytest -q tests/test_phase1.py -k sections` runs,
then ingest builds `runs/atlas/sections.jsonl` and `runs/atlas-b/sections.jsonl` from a second
run, the two files are byte identical, every document in `key.documents` has at least one
section, every section's anchor parses and resolves to a page, line, cell or row that exists in
its file, every fact of kind `quote` or `identifier` has its value present in the `text` of a
section of one of its own documents after whitespace normalisation, and the run prints one
coverage line: documents read, sections written, engine disagreements, empty extractions.
Samples `northwind` and `northstar-dental` are skipped with the reason "ingest not enabled for
this sample yet".

## Mechanism

- No skill, plugin or MCP fits. This is a parser, and the parser choice was measured in the
  first build over all 61 PDFs; those numbers are adopted here rather than re-measured.
- PDF text: `pdftext`, pinned to an exact version in `pyproject.toml`. It is the only library
  measured that both maps the bullet glyph to U+2022 and keeps the metadata block's label and
  value on one line, at 2.7 seconds for the corpus.
- PDF cross-check: `pypdf`, a new dependency. The two engines are independent, the check costs
  2.3 seconds for the corpus, and it is what caught `pdfplumber` corrupting the bullet 267
  times in the first build. A disagreeing page is written with a `warning` and counted, never
  repaired.
- PDF tables: `pdfplumber`, a new dependency. 95 ruled tables across 52 of the 61 PDFs, and the
  `Action | Owner | Timing` table in `Disclosure_Committee_Minutes_2025_10_29.pdf` carries
  planted facts in structured form. Flattening it to prose here and asking phase 4 to rebuild
  the row and column relation would pay at query time for structure the file already has.
- XLSX: `openpyxl`, already a dependency, `data_only=True`. One section per row, one cell entry
  per non-empty cell, the cell reference kept. No header inference: measured across 38 sheets in
  the first build, the header is in row 1 in 11 of them and absent in 16, so any rule would be a
  heuristic tuned to this corpus.
- CSV: the standard library `csv`, sniffing nothing. One section per row.
- TXT and MD: read as UTF-8, split on blank lines, line numbers kept.
- EML and MBOX: the standard library `email` and `mailbox`. Headers become the section heading,
  the body is split like text, and an mbox message carries its ordinal in the anchor.
- No model call, no gateway call, no network.

## The section shape

```json
{"doc": "data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf",
 "ordinal": 7,
 "kind": "text",
 "anchor": "data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf#p2l14",
 "heading": "3. Scope of exposure",
 "text": "The legacy backup object legacy_uap_backup_2021.tar.gz holds 912.8m records.",
 "warning": null}
```

```json
{"doc": "data_room/05_Security_IT_and_Infrastructure/Backup_Retention_Inventory.xlsx",
 "ordinal": 12,
 "kind": "row",
 "anchor": "data_room/05_Security_IT_and_Infrastructure/Backup_Retention_Inventory.xlsx#Inventory!A14",
 "heading": "Inventory",
 "cells": [{"ref": "A14", "value": "legacy_uap_backup_2021.tar.gz"}, {"ref": "B14", "value": "2021-07-31"}],
 "text": "legacy_uap_backup_2021.tar.gz | 2021-07-31",
 "warning": null}
```

`kind` is `text` or `row`. Records are written sorted by `doc` then `ordinal`, with sorted JSON
keys and no trailing whitespace, which is what makes two runs byte identical.

## Files

```aeo-independence
slice: 01-sections-atlas
creates: src/rlm/ingest.py
creates: src/rlm/sections.py
creates: tests/test_phase1.py
edits: pyproject.toml
```

## Out of scope

The index. Status words, version pairs and series. Samples 2 and 3. Any note, cluster or
report. A section boundary tuned to make one fact land inside one section: the boundary rule is
the format's own, and a fact that straddles two sections is a finding for slice 02 to carry in
the index, not a reason to move the boundary.
