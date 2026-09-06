# 01: One document of sample 1 noted end to end

Issue: [#37](https://github.com/Muhanad-husn/RLM/issues/37)

## Goal

`runs/atlas/notes/<doc>.json` exists for one document, DR-069,
`data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf`, written
from one gateway call to DeepSeek V4 Flash, with every quote verified and anchored by code, and
`LEDGER.md` carries the line the call wrote.

## Acceptance criterion

Given `runs/atlas/sections.jsonl` from phase 1 and `OPENROUTER_API_KEY` in the environment,
when `python -m rlm.notes samples/atlas runs/atlas --model deepseek/deepseek-v4-flash-0731 --only
DR-069` runs and then `pytest -q tests/test_phase2.py -k "one_document or gateway"`,
then the run prints, before the call, the estimated input tokens and the price in dollars; the note
file exists and parses; every quote in it is found in the document's sections by the rule in the
README and carries a resolving anchor of that document; the planted quote "bulk export is probable"
is inside one verified quote of the note; `LEDGER.md` has one new line with sample `atlas`, phase
`2`, the model id, the gateway's reported tokens in and out, dollars at the section 5 rate, and a
balance equal to the previous balance minus the dollars; and the fake transport test shows that a
batch whose estimate would pass the phase cap of $8 or the $50 total raises before any request is
sent, that nothing is written to `LEDGER.md` in that case, and that a successful batch writes
exactly one line.

## Mechanism

- No skill, plugin or MCP fits. One `httpx` call per document to the OpenRouter chat completions
  endpoint; `httpx` is already a dependency. No new dependency.
- `src/rlm/gateway.py`: `estimate_tokens(text) -> int` (characters divided by four, rounded up),
  `price(model, tokens_in, tokens_out) -> float` from a table copied from `PLAN.md` section 5,
  `Gateway.complete(model, messages, ...) -> Completion` carrying the text and the reported usage,
  `Ledger` that reads the last balance from `LEDGER.md`, refuses past the phase cap and the $50
  total, and appends one line per batch. The transport is injectable so a test can supply a fake.
- `src/rlm/notes.py`: builds the document text from sections, holds the one prompt and the schema,
  parses the reply, verifies and anchors every quote and figure, writes the note and the verify log,
  and has a `main(argv)` with `--model`, `--only <doc id or path>`, `--pass a|b`, `--out <dir>`
  (default `runs/<sample>`).
- `tests/test_phase2.py`: the tests of the acceptance criterion, parametrised over the three samples
  through `tests/conftest.py`, skipping a sample whose notes directory is absent with the reason
  "notes not run for this sample yet".

## The note shape

```json
{"doc": "data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf",
 "model": "deepseek/deepseek-v4-flash-0731",
 "pass": "a",
 "what": "Draft forensic findings on the October 2025 legacy backup exposure.",
 "flags": [{"flag": "Exfiltration assessed as probable",
            "quote": "bulk export is probable",
            "anchor": "data_room/05_Security_IT_and_Infrastructure/Aurora_Phase1_Technical_Findings_Draft.pdf#p2l14",
            "consequence": "Contradicts the final report's softer wording."}],
 "figures": [{"surface": "912.8m", "quote": "The legacy backup object holds 912.8m records.", "anchor": "...#p2l9"}],
 "cross_references": [{"kind": "code", "value": "AURORA", "quote": "...", "anchor": "..."}],
 "concealed": [{"claim": "The final omits the exfiltration finding.", "quote": "...", "anchor": "..."}],
 "usage": {"tokens_in": 1234, "tokens_out": 456, "dollars": 0.0002, "seconds": 3.1, "calls": 1}}
```

`cross_references[].kind` is one of `code`, `name`, `person`, `document`, `regulator`, `ticket`.
Every `quote` field carries an `anchor` written by code. The model is asked for `what`, `flags`,
`figures`, `cross_references` and `concealed` only; `doc`, `model`, `pass`, `anchor` and `usage` are
written by code. Keys are sorted and the file ends with one newline.

The verify log shape, `notes-verify.jsonl`, one record per failed item and per dropped note:

```json
{"doc": "...", "field": "flags", "item": 2, "quote": "the text the model gave", "outcome": "dropped", "attempt": 2}
```

`outcome` is `re-asked` for a failure after the first call and `dropped` for a failure after the
second; a note dropped whole has `field` null and `outcome` `note-dropped`.

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
