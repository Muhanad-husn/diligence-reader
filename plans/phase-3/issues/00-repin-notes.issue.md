# fix(phase-2): pinned notes rerun on GLM 5.3 Flash and repinned under the main checkout [slice 00]

**Issue:** #52 · **Spec:** PLAN.md#4-phases, row "2 Notes" · **Plan:** plans/phase-3/00-repin-notes.md
**Depends on:** none
**Labels:** phase-2

## Deliverable

`D:\RLM\runs\<sample>\notes\`, `notes-verify.jsonl` and `notes-summary.json` exist for the
three gate samples from one fresh pass a of `python -m rlm.notes samples/<sample>
runs/<sample>` with the default model `z-ai/glm-5.3-flash`. Every note file matches its
digest in the updated `tests/phase2-digests.json`. Phase 2 tests pass on all three samples
with planted recall 15 of 15, 5 of 5 and 2 of 2.

## Mechanism

No skill or MCP fits; no new dependency. `src/rlm/notes.py` unchanged. `src/rlm/pin.py` gains
`--from-notes` mode that writes `tests/phase2-digests.json` from the notes directory without
requiring a bake-off winner directory. `tests/test_phase2.py` gains a skip condition for the
bake-off pinning test when the bake-off directory is absent. The three passes run detached as
`python -m rlm.notes samples/<sample> runs/<sample>` with the default model. Cost is about
$0.08; a pass that misses any phase 2 fact reruns once (about $0.08 more) and that cost goes
to `LEDGER.md` with a note.

## Acceptance criterion

Given `runs/<sample>/sections.jsonl` exists for the three samples and `OPENROUTER_API_KEY` is
set,
when the three passes run detached and `python -m rlm.pin runs --from-notes` runs and then
`pytest -q tests/test_phase2.py` runs,
then the three passes add three lines to `LEDGER.md` summing to under $0.20; every phase 2
test passes on the three samples; `tests/phase2-digests.json` matches the files on disk; the
test `test_gate_pinned_notes_are_the_winners_pass_a` skips with a reason naming the absent
bake-off directory rather than failing; and the pull request body reports planted recall per
sample and the dollars spent. If any pass misses a phase 2 fact, the rerun cost is reported
with the missed fact's sample and the note's quotes beside it.

## Files

```aeo-independence
slice: 00-repin-notes
edits: src/rlm/pin.py
edits: tests/test_phase2.py
edits: tests/phase2-digests.json
edits: LEDGER.md
```

## Out of scope

Any phase 3 code. Any change to the note shape or prompt. The bake-off table. A phase 2
recall below 100 is not acceptable; it is rerun once and if it still misses, the test is not
loosened.
