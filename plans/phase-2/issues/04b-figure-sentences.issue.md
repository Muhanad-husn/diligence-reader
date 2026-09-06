**Spec:** PLAN.md#4-phases, row "2 Notes" · **Plan:** plans/phase-2/04b-figure-sentences.md
**Depends on:** #40 (PR #46)
**Labels:** phase-2

## Deliverable

Every sentence of a document that carries an amount or a percentage is in the document's note as a verified figure, whatever the model quoted. `runs/<sample>/bakeoff.json` is rerun on the same five models with this in place, and the cheapest row that passes is the winner and the default `--model` of `python -m rlm.notes`.

## Why

The bake-off in #40 (PR #46) had no passing row. Two sentences decided it, and both carry an amount: DR-029 "explains why management recommends a reserve of $12m at this time" (only DeepSeek V4 Pro quoted it) and `cap_table_summary.pdf.md` 5.2 "more than fifty percent (50%) of the Company's outstanding equity ... constitutes a Change of Control" (only Luna and GLM 5.3 Flash quoted it). A code step that harvests every sentence carrying an amount makes those three models 7 of 7 on the probe at $0. Approved by the founder on 2026-09-06.

## Mechanism

`src/rlm/notes.py`: after the model's items are verified, code walks the document's sections. In a text section, the unit is the sentence, split after a full stop, question mark or exclamation mark followed by whitespace, whitespace collapsed so a sentence that runs over PDF line breaks is one unit. In a table section, the unit is the cell. Every unit in which `rlm.amounts.AMOUNT` finds a currency amount or a percentage is appended to the note's `figures` as `{"surface": <the amount as written>, "quote": <the unit>, "anchor": <the section's anchor>}`, one item per amount, verified by the same `verify_items` path as a model item, so it is verbatim and its surface is inside its quote. An item that matches a model item on every key is kept once. The note shape does not change. Plain counts with no currency or percent sign (`24 months`, `912.8m`) are not harvested; that is what the model is for.

`src/rlm/bakeoff.py`: unchanged. The bake-off is rerun in full (`python -m rlm.bakeoff samples runs`), flash tier first, and the winner's id becomes the default `--model` in `notes.py`. `PLAN.md` section 5's bake-off table is rewritten from the new `bakeoff.json`.

## Acceptance criterion

Given PR #46 is merged,
when `python -m rlm.bakeoff samples runs` runs detached and then `pytest -q tests/test_phase2.py` runs,
then a fake-gateway test shows a reply with no figures yields a note whose figures carry the DR-029 sentence with surface `$12m` and anchor `#p1l23`; a unit test shows a three-line sentence is one quote and a table row yields one item per cell with an amount; `bakeoff.json` has at least one row with `passes` true and `winner` names the cheapest; the winner's pass `a` and `b` directories on all three samples carry every phase 2 planted quote; `notes.py`'s default `--model` is the winner; `PLAN.md` section 5's table is filled from `bakeoff.json`; `LEDGER.md` gained one line per probe and per pass per sample per model; phase 2 spend stays under $8.

## Files

```aeo-independence
slice: 04b-figure-sentences
edits: src/rlm/notes.py
edits: tests/test_phase2.py
edits: PLAN.md
edits: LEDGER.md
creates: plans/phase-2/04b-figure-sentences.md
depends-on: 04-bakeoff
```

## Out of scope

Pinning (the gate), any prompt change, any change to the note shape, harvesting dates, names or plain counts, any model outside the five.
