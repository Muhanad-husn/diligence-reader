# Phase 2: Notes

Milestone `Phase 2`. Spec: `PLAN.md` section 4, row "2 Notes". Cap $8. This is the first phase that
calls a model and the first that writes `LEDGER.md`.

The outcome: `runs/<sample>/notes/<doc>.json` and `runs/<sample>/notes-verify.jsonl` exist for all
three gate samples. One note per document, from one model call per document with a fixed JSON
schema. Every quote and every figure in a note is verified by code against the document's own
sections and carries the anchor of the section it comes from. A note whose quotes fail is re-asked
once; what still fails is dropped and logged. Every planted fact of phase 2 (all of them are quotes:
15 in `atlas`, 5 in `northwind`, 2 in `northstar-dental`) appears in the note of one of its own
documents as a verified quote. Two passes are run and their agreement on the planted facts is
printed. Five models are tried, cheapest first, and the cheapest that passes on all three samples is
pinned as the phase 2 model.

## The shape decisions this phase fixes

- **The model sees section text and nothing else.** The document sent to the model is its sections
  from `runs/<sample>/sections.jsonl`, in ordinal order, one section per line, with no anchors and
  no key. Anchors are not asked of the model; code finds them. This keeps the input about 96k tokens
  on sample 1 and puts the anchor where it can be trusted.
- **A quote is verified by code and located by code.** A quote passes when its text, with whitespace
  collapsed and curly quotes and apostrophes straightened, is a substring of one section's text
  treated the same way, or of the concatenation of two adjacent sections joined by one space for a
  sentence that wraps a line. Case is not folded: a quote is verbatim. The anchor written into the
  note is the anchor of the section where the quote starts. A figure passes when its quote passes
  and the figure's surface string is inside its quote. The model's own anchor, if it writes one, is
  discarded.
- **Fail, re-ask once, drop, log.** After the first call, the failed quotes are listed back to the
  model in one second call for that document, with the instruction to quote verbatim or drop the
  item. What still fails after the second call is dropped from the note and written to
  `notes-verify.jsonl`. A note whose JSON does not parse twice is dropped whole and logged. No third
  call.
- **The gateway is one module and the ledger is written by it.** `src/rlm/gateway.py` is the only
  code that opens a socket to the gateway (OpenRouter, key in `OPENROUTER_API_KEY`). Before a batch
  it prints the estimated input token count (characters divided by four, labelled an estimate) and
  the price at `PLAN.md` section 5's rates, refuses when the estimate would take the phase past its
  cap or the total past $50, and after the batch appends one line to `LEDGER.md` with the gateway's
  own reported token counts. One line per pass per sample per model. Nothing else writes
  `LEDGER.md`.
- **Same request twice.** Temperature 0, a fixed seed where the model accepts one, JSON output mode
  where the model offers one, reasoning turned off or set to its lowest setting where the model
  offers the switch, and a hard output cap per note. Two passes still differ, and that difference is
  what the agreement number measures; nothing votes between them.
- **Eight documents in flight at once.** As the winner's leaf did. Notes are one file per document
  so order does not matter; `notes-verify.jsonl` is sorted by document then item so it is stable.
- **Tests read the artefact; they do not call the model.** A phase 2 test skips with the reason
  "notes not run for this sample yet" when `runs/<sample>/notes/` is absent. The run is launched
  detached, per `CLAUDE.md`, and the tests are run after it. Only the gateway's refusal and ledger
  logic is tested with a fake HTTP transport, and that test never opens a socket.
- **The winner's pass is pinned by digest.** The gate copies the winning model's first pass to
  `runs/<sample>/notes/` and writes the sha256 of every note file into `tests/phase2-digests.json`.
  Phase 3 is deterministic over that pinned set and its tests refuse a moved note. Runs are not
  committed; the digest is.
- **Cheapest first, Pro only on failure.** The bake-off runs DeepSeek V4 Flash, GLM 5.3 Flash and
  Luna on all three samples, two passes each. DeepSeek V4 Pro and GLM 5.3 run only if all three of
  those fail the gate on some sample. The table in `PLAN.md` section 5 carries a row per model
  either way, with "not run" where a row was not needed.

## Slices

| NN | Slice | Plan | Issue | Depends on |
|---|---|---|---|---|
| 01 | One document of sample 1 noted end to end: gateway, ledger, schema, verification | [01-note-one-document-atlas.md](01-note-one-document-atlas.md) | #37 | none |
| 02 | Notes on all of sample 1, re-ask and drop, the fifteen planted quotes | [02-notes-atlas.md](02-notes-atlas.md) | #38 | 01 |
| 03 | Notes on samples 2 and 3 with no code change to the note shape | [03-notes-northwind-northstar.md](03-notes-northwind-northstar.md) | #39 | 02 |
| 04 | Bake-off: five models cheapest first, two passes, agreement, the table in PLAN.md | [04-bakeoff.md](04-bakeoff.md) | #40 | 03 |
| 05 | Phase 2 gate | [05-gate.md](05-gate.md) | #41 | 04 |

Order of work: 01, 02, 03, 04, 05, one after the other. Nothing in this phase runs concurrently
because every slice runs the model on the previous slice's artefact.

## Money

At `PLAN.md` section 5 prices and sample 1's measured size (96k input tokens of section text, about
150k with the prompt, about 80k out): one pass on sample 1 costs about $0.03 on DeepSeek V4 Flash,
$0.03 on GLM 5.3 Flash, $0.13 on Luna, $0.27 on DeepSeek V4 Pro, $0.56 on GLM 5.3. Samples 2 and 3
are under a cent a pass on any model. Slice 01 spends under $0.01. Slice 02 spends about $0.10 over
its development runs. Slice 03 spends under $0.05. Slice 04 spends about $0.40 if a Flash model or
Luna passes, and about $2.10 if the two Pro models have to run. Expected phase total about $0.60;
worst case about $2.50 of the $8 cap.

## What the samples make this phase carry

Sample 1: 100 documents, 2,808 sections, 385k characters; the largest document is 19k characters, so
no document needs splitting. Fifteen phase 2 facts, all quotes, each sitting inside one section of
its document (checked on 2026-09-06 against `runs/atlas/sections.jsonl`). Sample 2: five quotes, one
of them a full contract clause of about sixty words in `msa_meridian_freight.pdf.md` section
12.3(c); a model that quotes half of it fails the fact. Sample 3: two quotes, one in `cim.md`, one
in a vendor agreement.

## A risk to name

If every model quotes the long Meridian clause in part, the fact is not moved to phase 5 and the
test is not loosened. The key belongs to phase 0 and a change to its value is a phase 0 fix issue,
put to the founder with the five models' quotes beside it.
