# 04c: Passing row

Issue: [#49](https://github.com/Muhanad-husn/RLM/issues/49)

## Goal

`runs/<sample>/bakeoff.json` names a winner: the cheapest row whose pass a carries every phase 2 planted fact on every sample. The two-pass agreement stays in the row and is reported as the spread, not gated. The winner's id is the default `--model` of `python -m rlm.notes`, and `PLAN.md` section 5's table names it.

PLAN.md section 4 defines the phase 2 test as every planted fact in the note of its own document with a verified quote, and two passes with their agreement printed. The row rule written in #40 gated on both passes instead, and under it no model passed the rerun in #47: GLM 5.3 Flash and Luna both carry 22 of 22 facts in pass a and 21 of 22 in pass b, losing the same northwind sentence to provider nondeterminism at temperature 0. Under the section 4 rule GLM 5.3 Flash wins at $0.18 against Luna's $0.76 on identical recall. Approved by the founder on 2026-09-06, with the note that the winner matters only for what its pinned pass gives phases 3 to 5: the northwind spread of 20 is carried into the gate row and traced there, not hidden by this rule.

## Acceptance criterion

Given PR #48 is merged, when `python -m rlm.bakeoff samples runs --recount` runs and then `pytest -q` runs, then `bakeoff.json` on all three samples has `passes` true for GLM 5.3 Flash and Luna and `winner` equal to `z-ai/glm-5.3-flash`; a fake-gateway test shows a model with pass a complete and pass b short of one fact passes with agreement below 1.0; the artefact test asserts the winner is the cheapest row whose pass a recall is total on every sample; `python -m rlm.notes samples/atlas runs/atlas --only DR-069 --out <tmp>` with a fake gateway runs on `z-ai/glm-5.3-flash` without `--model`; `LEDGER.md` gains no line; `PLAN.md` section 5 names the winner.

## Mechanism

- `src/rlm/bakeoff.py`: a row `passes` when every phase 2 fact of every sample is recalled in pass a. `agreement` and `recall` are unchanged. A new `--recount` flag rebuilds every row from the pass directories already under `runs/<sample>/bakeoff/` with no gateway call and no ledger line, rewrites `bakeoff.json` and prints the table; rows with no directories stay `"not run"`.
- `src/rlm/notes.py`: `--model` defaults to the winner, `z-ai/glm-5.3-flash`.
- `PLAN.md` section 5: the passes column and the winner sentence rewritten from the recounted `bakeoff.json`.

## Files

```aeo-independence
slice: 04c-passing-row
edits: src/rlm/bakeoff.py
edits: src/rlm/notes.py
edits: tests/test_phase2.py
edits: PLAN.md
creates: plans/phase-2/04c-passing-row.md
depends-on: 04b-figure-sentences
```

## Out of scope

Pinning (the gate, #41), any new model call, any change to the note or the harvest, any voting between passes.
