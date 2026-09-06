# feat(phase-2): bake-off [slice 04]

**Issue:** #40 · **Spec:** PLAN.md#4-phases, row "2 Notes" · **Plan:** plans/phase-2/04-bakeoff.md
**Depends on:** #39
**Labels:** phase-2

## Deliverable

`runs/<sample>/bakeoff/<model-slug>/<pass>/` holds two passes for every model tried on every sample.
`runs/<sample>/bakeoff.json` holds the table with one row per model carrying `passes` (true when
every planted phase 2 fact is recalled on every sample in both passes), `dollars` (both passes,
three samples), `agreement` (planted facts recalled in both passes over planted facts, per sample),
`seconds`, or `"not run"`. The row named `winner` is the cheapest passing row. `PLAN.md` section 5's
bake-off table is filled from `bakeoff.json` and prices are reread from the gateway's model list on
the day and rewritten if they moved, with the date. The winning model's id is written to
`src/rlm/notes.py` as the default `--model`.

## Mechanism

`src/rlm/bakeoff.py`: loops models in price order, runs `notes.main` twice per sample into the pass
directories, measures recall against the key with the same fold as the test, writes `bakeoff.json`
and prints the table. Stops escalating to the Pro tier when a cheaper model passes everywhere.
Prices: one GET of the gateway's model list, matched on id; if a price differs from `PLAN.md`, the
table in section 5 is rewritten by hand in this pull request with the new date, as section 5 says.

## Acceptance criterion

Given slice 03 is merged,
when `python -m rlm.bakeoff samples runs` runs detached, reading the five model ids and prices from
`PLAN.md` section 5, trying DeepSeek V4 Flash, GLM 5.3 Flash and Luna first and the two Pro models
only if all three fail on some sample, two passes per model per sample, and then `pytest -q
tests/test_phase2.py` runs,
then each pass directory has notes and a verify log of the slice 02 shape; `bakeoff.json` has one
row per model with `passes`, `dollars`, `agreement` and `seconds`, or `"not run"`; the test asserts
that the row named `winner` is the cheapest passing row; `PLAN.md` section 5's prices are reread
from the gateway's model list on the day and rewritten if they moved, with the date; `PLAN.md`
section 5's bake-off table is filled from `bakeoff.json`; and `LEDGER.md` gained one line per pass
per sample per model.

## Files

```aeo-independence
slice: 04-bakeoff
creates: src/rlm/bakeoff.py
edits: src/rlm/notes.py
edits: tests/test_phase2.py
edits: PLAN.md
edits: LEDGER.md
depends-on: 03-notes-northwind-northstar
```

## Out of scope

Pinning (the gate), any sixth model, any pair judge, any change to the note shape, majority voting
between passes.
