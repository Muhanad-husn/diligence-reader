# 00: fix(phase-2): the pinned notes are rerun and repinned under the main checkout

Issue: [#52](https://github.com/Muhanad-husn/RLM/issues/52)

## Goal

`D:\RLM\runs\<sample>\notes\`, `notes-verify.jsonl` and `notes-summary.json` exist for the
three gate samples from one fresh pass a of `python -m rlm.notes samples/<sample>
runs/<sample>` (default model `z-ai/glm-5.3-flash`). `tests/phase2-digests.json` is rewritten
to the new files. `pytest -q tests/test_phase2.py` passes on all three samples with planted
recall 15 of 15, 5 of 5 and 2 of 2.

## Acceptance criterion

Given `runs/<sample>/sections.jsonl` exists for the three samples (from `python -m rlm.ingest`,
free and digest-checked) and `OPENROUTER_API_KEY` is set,
when the three passes run detached and `python -m rlm.pin runs --from-notes` (a new mode that
digests what is in `runs/<sample>/notes/` without a bake-off winner) runs and then `pytest -q
tests/test_phase2.py` runs,
then the three passes add three lines to `LEDGER.md` summing to under $0.20; every phase 2
test passes on the three samples; `tests/phase2-digests.json` matches the files on disk; the
test that pins the notes to the bake-off winner's pass a (`test_gate_pinned_notes_are_the_winners_pass_a`)
skips with a reason naming the absent bake-off directory rather than failing; and the pull
request body reports recall per sample and dollars.

## Mechanism

No skill or MCP fits; no new dependency. `src/rlm/notes.py` unchanged. `src/rlm/pin.py` gains
`--from-notes`. `tests/test_phase2.py` gains the skip. Cost: the bake-off's GLM 5.3 Flash row
was $0.18 for a probe and two passes on three samples, so one pass on three samples is about
$0.08.

The risk to name: a fresh pass a can miss a fact the bake-off's pass a carried (the bake-off's
pass b missed `tidewater-subprocessor-gap` on `northwind`). A miss is a phase 2 recall below
100 and is reported in the pull request with the note's quotes beside it. The pass is rerun
once at most (about $0.08 more). The test is not loosened.

## Files

```aeo-independence
slice: 00-repin-notes
edits: src/rlm/pin.py
edits: tests/test_phase2.py
edits: tests/phase2-digests.json
edits: LEDGER.md
```

## Out of scope

Any phase 3 code. Any change to the note shape or prompt. The bake-off table.
