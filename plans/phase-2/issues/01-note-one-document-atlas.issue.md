# feat(phase-2): one document of sample 1 noted end to end [slice 01]

**Issue:** #37 · **Spec:** PLAN.md#4-phases, row "2 Notes" · **Plan:** plans/phase-2/01-note-one-document-atlas.md
**Depends on:** none
**Labels:** phase-2

## Deliverable

`runs/atlas/notes/<doc>.json` exists for one document, DR-069, written from one gateway call to
DeepSeek V4 Flash, with every quote verified and anchored by code. `LEDGER.md` carries the line the
call wrote. A note carries `doc`, `model`, `pass`, `what`, `flags`, `figures`, `cross_references`,
`concealed` and `usage`. `cross_references[].kind` is one of `code`, `name`, `person`, `document`,
`regulator`, `ticket`. Every `quote` field carries an `anchor` written by code. The model is asked
for `what`, `flags`, `figures`, `cross_references` and `concealed` only; `doc`, `model`, `pass` and
`usage` are written by code.

## Mechanism

One `httpx` call per document to the OpenRouter chat completions endpoint; `httpx` is already a
dependency. No new dependency. `src/rlm/gateway.py`: `estimate_tokens(text) -> int` (characters
divided by four, rounded up), `price(model, tokens_in, tokens_out) -> float` from a table copied
from `PLAN.md` section 5, `Gateway.complete(model, messages, ...) -> Completion` carrying the text
and the reported usage, `Ledger` that reads the last balance from `LEDGER.md`, refuses past the
phase cap and the $50 total, and appends one line per batch. The transport is injectable so a test
can supply a fake. `src/rlm/notes.py`: builds the document text from sections, holds the one prompt
and the schema, parses the reply, verifies and anchors every quote and figure, writes the note and
the verify log, and has a `main(argv)` with `--model`, `--only <doc id or path>`, `--pass a|b`,
`--out <dir>` (default `runs/<sample>`). `tests/test_phase2.py`: the tests of the acceptance
criterion, parametrised over the three samples through `tests/conftest.py`, skipping a sample whose
notes directory is absent with the reason "notes not run for this sample yet".

## Acceptance criterion

Given `runs/atlas/sections.jsonl` from phase 1 and `OPENROUTER_API_KEY` in the environment,
when `python -m rlm.notes samples/atlas runs/atlas --model deepseek/deepseek-v4-flash-0731 --only
DR-069` runs and then `pytest -q tests/test_phase2.py -k "one_document or gateway"` runs,
then the run prints, before the call, the estimated input tokens and the price in dollars; the note
file exists and parses; every quote in it is found in the document's sections by the rule of
case-exact substring match after whitespace collapse and quote straightening, or of two adjacent
sections joined by one space, and carries a resolving anchor of that document; the planted quote
"bulk export is probable" is inside one verified quote of the note; `LEDGER.md` has one new line
with sample `atlas`, phase `2`, the model id, the gateway's reported tokens in and out, dollars at
the section 5 rate, and a balance equal to the previous balance minus the dollars; and the fake
transport test shows that a batch whose estimate would pass the phase cap of $8 or the $50 total
raises before any request is sent, that nothing is written to `LEDGER.md` in that case, and that a
successful batch writes exactly one line.

## Files

```aeo-independence
slice: 01-note-one-document-atlas
creates: src/rlm/gateway.py
creates: src/rlm/notes.py
creates: tests/test_phase2.py
edits: LEDGER.md
```

## Out of scope

The other 99 documents, the re-ask, concurrency, samples 2 and 3, any model but DeepSeek V4 Flash,
the bake-off, any change to `PLAN.md`.
