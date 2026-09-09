# feat(phase-1): sections and anchors on sample 1, all seven formats [slice 01]

**Issue:** #14 · **Spec:** PLAN.md#4-phases, row "1 Ingest" · **Plan:** plans/phase-1/01-sections-atlas.md
**Depends on:** none
**Labels:** phase-1

## Deliverable

`runs/atlas/sections.jsonl`, built by `src/rlm/ingest.py` from `samples/atlas/data_room/` alone, with all 100 documents of the key sectioned across the six formats the room uses: 61 PDF, 29 XLSX, 7 CSV, 1 TXT, 1 EML, 1 MBOX. A section is text or a table row and carries `doc`, `ordinal`, `kind`, `anchor`, `heading`, `text` and `warning`; a row also carries `cells` with their cell references. The anchor is one string and it is what phase 5 cites: `<doc>#p2l14`, `<doc>#l14`, `<doc>#m3l14`, `<doc>#Sheet1!A14`, `<doc>#r14`. Ingest never reads a key: a document is its path relative to the sample root, and the test maps `DR-069` to that path through `key.documents`.

## Mechanism

Parsers as measured in the first build, adopted rather than re-measured. `pdftext` pinned to an exact version for PDF text; `pypdf` as an independent cross-check that writes a `warning` and a count on a disagreeing page and never repairs it; `pdfplumber` for the 95 ruled tables across 52 of the 61 PDFs, one of which is the `Action | Owner | Timing` table in the disclosure committee minutes; `openpyxl` with `data_only=True` for workbooks, one section per row, no header inference; the standard library for CSV, text, markdown, EML and MBOX. Records sorted by `doc` then `ordinal`, JSON keys sorted, which is what makes two runs byte identical. No model call, no gateway call, no network. Shapes are in the plan file.

## Acceptance criterion

Given `samples/atlas/key.json` and the data room exist,
when `pytest -q tests/test_phase1.py -k sections` runs,
then ingest builds `runs/atlas/sections.jsonl` and a second run into `runs/atlas-b/`, the two are byte identical, every document in `key.documents` has at least one section, every anchor parses and resolves to a page, line, cell or row that exists in its file, every fact of kind `quote` or `identifier` has its value in the `text` of a section of one of its own documents after whitespace normalisation, and the run prints one coverage line: documents read, sections written, engine disagreements, empty extractions. Samples `northwind` and `northstar-dental` are skipped with the reason "ingest not enabled for this sample yet".

## Files

```aeo-independence
slice: 01-sections-atlas
creates: src/rlm/ingest.py
creates: src/rlm/sections.py
creates: tests/test_phase1.py
edits: pyproject.toml
```

## Out of scope

The index. Status words, version pairs and series. Samples 2 and 3. A section boundary tuned so that one fact lands inside one section: the boundary rule is the format's own.
