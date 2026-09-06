# 02: Notes on all of sample 1

Issue: [#38](https://github.com/Muhanad-husn/RLM/issues/38)

## Goal

`runs/atlas/notes/` holds a note for every one of the 100 documents the key names, or a logged drop,
and each of the fifteen phase 2 facts of sample 1 is inside a verified quote of a note of one of its
own documents.

## Acceptance criterion

Given slice 01 is merged and `runs/atlas/sections.jsonl` exists,
when `python -m rlm.notes samples/atlas runs/atlas --model deepseek/deepseek-v4-flash-0731 --pass a`
runs detached and then `pytest -q tests/test_phase2.py` runs,
then every document in `samples/atlas/key.json`'s `documents` has a note file or a `note-dropped`
record; every quote and figure in every note verifies and its anchor resolves to a section of the
same document; `notes-verify.jsonl` is sorted by document then field then item and every dropped
item it names is absent from its note; each of the fifteen phase 2 facts has a note of one of its
documents holding a verified quote that contains the fact's value after whitespace is collapsed and
case folded on both sides; `LEDGER.md` gained exactly one line for the pass; and the pytest readout
prints, for the sample, documents noted, notes dropped, quotes verified, quotes re-asked, quotes
dropped, planted recall as a percentage, dollars, and seconds.

## Mechanism

- The same modules as slice 01. `notes.py` gains: a pool of eight concurrent document calls
  (`concurrent.futures.ThreadPoolExecutor`, no new dependency), the re-ask of failed quotes and the
  drop after the second call, a note-level drop when JSON fails to parse twice, the sorted verify
  log, a per-pass summary printed at the end and written to `runs/<sample>/notes-summary.json`
  (documents, dropped, verified, re-asked, dropped items, tokens, dollars, seconds), and the readout
  hook in `tests/test_phase2.py` following the phase 1 `readout(terminalreporter)` pattern.
- The recall test applies the same fold to both sides: whitespace collapsed, case folded, curly
  quotes straightened. No rule reads a key value.
- Prompt changes are allowed in this slice and are the expected work: the fifteen facts are the
  measure. A fact still missed after the prompt is tuned is reported in the pull request with the
  note's actual quotes beside it; the test is not loosened.

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

## Files

```aeo-independence
slice: 02-notes-atlas
edits: src/rlm/notes.py
edits: tests/test_phase2.py
edits: LEDGER.md
depends-on: 01-note-one-document-atlas
```

## Out of scope

Samples 2 and 3, any model but DeepSeek V4 Flash, the second pass and the agreement number, the
bake-off table, digests.
