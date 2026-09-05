# Parser selection for Stage A1

The PRD says to measure rather than speculate, so before slice 01 of `plans/stage-a1-parse/`
was executed, seven PDF extraction paths and four table paths were run over all 61 PDFs in
`data_room/` and scored on the things that actually matter downstream. This file records the
numbers and the decisions that follow from them. Nothing sealed was read; the whole exercise
ran against `data_room/` and the PRD.

**Measured 2026-08-21**, Windows 11, Python 3.13.11, all 61 PDFs, 118 pages, cold start.

## What was measured, and why those metrics

- **Time** for all 61 files. Not because the corpus is slow — it is 1.4 MB — but because a
  30x difference decides whether re-running ingest during development is free or annoying.
- **Em dash count.** The room uses `—` as its structural separator: `Board Minutes — Q4 2024`,
  `CONFIDENTIAL — Project Atlas — DR-008`. A parser that rewrites it is mutating evidence.
- **Amount count.** `$4,990m` and friends are the Contingency and Assumption signal. A parser
  that splits one across a line break loses it.
- **Label/value pairing.** These PDFs carry a metadata block whose first field is
  `Document ID DR-0NN`, rendered as label and value on one baseline. A parser that emits
  `Document ID\nDR-008` has thrown away the pairing that makes the block readable, and
  slice 02's resolution depends on that pairing. Counted as `paired` (label and value on one
  line) against `broken` (label alone on its line), across three fields in all 61 files, so
  189 is the perfect score in both directions.
- **Bullet glyph.** The room's PDFs use a bullet in list items. It sits at an encoding
  position most extractors cannot map, which turns out to be the sharpest discriminator in
  the set — see below.

## The text extractors

| Extractor | Time (61 files) | chars | em dash | amounts | paired | broken | bullet renders as |
|---|---|---|---|---|---|---|---|
| **pdftext 0.7.1** | **2.74s** | 212679 | 795 | 231 | **189** | **0** | **`•` U+2022** |
| pymupdf-rows | 0.33s | 211733 | 795 | 231 | 189 | 0 | `•` U+2022 |
| pypdf 6.16.1 | 2.33s | 211914 | 795 | 231 | 0 | 189 | `\x7f` |
| pymupdf 1.28.2 | 0.28s | 211851 | 795 | 231 | 0 | 189 | `•` U+2022 |
| pdfplumber 0.11.10 | 10.54s | 213872 | 795 | 231 | 189 | 0 | **`(cid:127)`** |
| pdfplumber `layout=True` | 18.44s | 642154 | 795 | 231 | 189 | 0 | `(cid:127)` |
| poppler `pdftotext -layout` | — | — | — | 231 | 189 | 0 | — |

Two things stand out.

**Every extractor agrees on the substance.** 231 amounts, 795 em dashes, 118 pages, zero
failures, on every path. These are ReportLab-generated PDFs with a clean Type1 text layer,
no scans, no font subsetting and no OCR need. There is no extraction *ambiguity* here to
solve — the differences are all in how the text layer is assembled into lines.

**pdfplumber corrupts the bullet, 267 times across 51 of the 61 files.** It emits the literal
nine-character string `(cid:127)` where the document has a `•`. pypdf and default pymupdf
leave a bare `\x7f`. pdftext and pymupdf's word-level output map it correctly to U+2022. This
matters more than it looks: the corrupted string would travel into every anchored quotation
in the final report, and it is the sort of thing that is invisible until someone reads the
output.

`pdfplumber` with `layout=True` was the plan of record before this measurement. It is the
worst option in the table — 7x the runtime of `pdftext`, three times the characters, all of
the extra being padding whitespace, and no metric it wins. These pages are single-column
ReportLab flows; there are no spaced columns for a layout mode to preserve.

## The ML document-understanding pipelines

Tried because the brief asked for them.

| Tool | Time | em dash | `&amp;` leaks | Notes |
|---|---|---|---|---|
| **docling 2.x** | 8.2–12.9s **per file** | **0** (all destroyed) | yes | Best *structure*: markdown headings, metadata block correctly recognised as a table. Deterministic across two runs. Pulls ~1.3 GB of dependencies including torch and RapidOCR ONNX models. |
| **unstructured (`strategy="fast"`)** | 16.1s for **one** 1-page file | — | — | Types elements (`Title`, `NarrativeText`, `ListItem`, `Footer`), which is genuinely useful but is A2/A4 semantics, not A1. Splits label from value like pypdf does. Drops the bullet silently. |

Both are rejected, and the reason is not that they are bad tools. They are layout-model
pipelines built for the problem this corpus does not have — scanned pages, complex
multi-column layouts, no usable text layer. Against a clean text layer they cost 30 to 40x
the runtime and 1.3 GB of dependencies to arrive at the same words, and docling arrives at
slightly *different* words: it normalises every one of the 795 em dashes to a hyphen and
leaks `&amp;` into the text. For a project whose entire claim rests on anchored, faithful
evidence, a parser that silently rewrites characters is a liability, however good its
structure detection is.

Worth keeping in view rather than discarding: if a second corpus in the generality test has
scanned documents, this is the row of the table to come back to.

## The table extractors

`pdfplumber.extract_tables()` finds **95 ruled tables across 52 of the 61 PDFs**, and the
extraction is clean — correct cells, embedded newlines preserved inside a cell.

```
== Disclosure_Committee_Minutes_2025_10_29.pdf page 2, 5 x 3
   ['Action', 'Owner', 'Timing']
   ['Obtain and review IronLake Phase 1 findings', 'General Counsel / CISO', 'On receipt']
   ['Maintain factual, non-conclusory internal language re NQ-17 / AURORA', 'All functions', 'Immediate']
```

`camelot` in `lattice` mode works on these files too, with comparable quality, and needs no
Ghostscript for them. It is not chosen because pdfplumber is already in the dependency set
for nothing extra and finds the same tables.

## Decisions

1. **PDF text: `pdftext` 0.7.1** (Apache-2.0, on `pypdfium2`). Correct on every metric,
   2.74s for the corpus, and the only library in the set that both maps the bullet correctly
   and groups lines correctly without code written here.

   `pymupdf` matches it and is 8x faster, and is rejected for two reasons. It is
   **AGPL-3.0 or commercial**, which would force this repository's licence, and the variant
   that scores full marks is `pymupdf-rows` — row grouping written here by rounding the
   baseline y-coordinate, which is a hand-tuned constant in a heuristic and the first
   over-engineering tripwire in `CLAUDE.md`. `pdftext` does that grouping as a maintained
   library. Licences of the chosen set are all permissive: pdftext Apache-2.0, pypdf
   BSD-3-Clause, pdfplumber MIT via pdfminer.six.

2. **Cross-check every PDF against `pypdf`.** The two engines are independent — pdfium in C++
   versus a pure-Python parser — and today they produce **identical word multisets on 61 of
   61 files**. The check costs 2.3s for the whole corpus and it is what caught pdfplumber's
   `(cid:127)` corruption in the first place. It runs in the coverage gate and reports a
   disagreeing page rather than silently choosing a winner.

3. **PDF tables are extracted as tables in A1, with `pdfplumber`.** This reverses the earlier
   plan to defer them. 52 of 61 PDFs is not an edge case, and an `Action | Owner | Timing`
   table is the Obligation type from PRD Section 5 sitting in the document in structured
   form. Flattening it to prose in A1 and asking a later stage to reconstruct the row-column
   relation would be paying at query time for structure the corpus already has — which is the
   exact thing this project exists to argue against.

4. **No MCP server is used.** None of the connected servers parses documents. Chrome could
   render a PDF and scrape the text, which is slower by orders of magnitude and not
   deterministic. Google Drive could convert one, which would upload a corpus `docs/corpus.md`
   records as not ours to redistribute to a third-party service. Both are ruled out on policy
   and determinism, not on capability.

5. **No model call in A1, including as a fallback.** The A1 experimental arm in PRD Section 7
   measures a mechanical-only pipeline; a model call inside the parse would make that arm
   measure something else. Where the mechanical path cannot produce text — an empty page, or
   a page the two engines disagree on — the run reports it and the number goes in the
   coverage report. Nothing is quietly repaired.

6. **Spreadsheets get no header inference.** Measured across all 38 sheets: the header is in
   row 1 in only 11 of them, row 4 in 9, rows 5 and 6 in one each, and in 16 sheets the
   obvious detector — first all-string row followed by a row containing a non-string — finds
   nothing at all, because those tables are string-valued throughout. Any header rule would
   be a heuristic tuned against this corpus. A1 emits the cell grid with its anchors and
   leaves the choice to whoever needs it, with the cell reference as proof.

## The fallback ladder, and why it is expected never to fire

Written down because it was asked for, and because a gate with no defined failure branch is
a gate nobody can trust.

1. `pdftext` extracts the page.
2. `pypdf` extracts the same page. Word multisets are compared after normalising whitespace.
3. Agreement: the `pdftext` text is the record.
4. Disagreement, or an empty extraction from either: the record is still written, carrying a
   `warning` naming the disagreement, and the coverage report counts it. It is not repaired,
   not retried with a third parser, and not sent to a model.
5. If the count is ever non-zero, that is a finding to investigate and write up, not a
   threshold to relax.

On today's corpus step 4 fires zero times.

## Reproducing this

Install `pdftext pdfplumber pypdf`, then for each PDF compare `plain_text_output(path)`
against `"\n".join(page.extract_text() for page in pypdf.PdfReader(path).pages)` on the
metrics in the table above. The rejected tools need `docling`, `unstructured[pdf]`
`unstructured_inference`, `camelot-py` and `pymupdf`, which together take the virtual
environment from 669 MB to 2.0 GB — worth knowing before repeating the exercise. None of the
rejected packages is a dependency of this project.
