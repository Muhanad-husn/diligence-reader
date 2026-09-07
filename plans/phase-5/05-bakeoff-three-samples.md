# 05: Bake-off on the three samples, five models, table, winner pinned

Issue: [#83](https://github.com/Muhanad-husn/RLM/issues/83)

## Goal

`runs/<sample>/write-bakeoff.json` names the cheapest model whose pass a on every sample has
recall 100, a passing verifier and, on sample 1, a rubric score at or above 85; that model's
pass a is copied to `runs/<sample>/report.md`, `verify.json`, `grade.json` on the three
samples and pinned by digest in `tests/phase5-digests.json`. Samples 2 and 3 pass the phase
5 tests for the first time here.

## Acceptance criterion

Given slice 04 is merged and the three dossiers match `tests/phase4-digests.json`,
when `python -m rlm.writebakeoff samples runs` runs and then `python -m rlm.pin --reports`
and `pytest -q tests/test_phase5.py` run,
then the table holds one row per model of the price table with, per model: passes, dollars,
seconds, and per sample recall a and b, verifier a and b, and on `atlas` rubric a, rubric b
and spread; models ran cheapest first inside the flash tier and the pro tier ran only when
every flash model failed on some sample; the table was written after each model so a run
that dies leaves an artefact; the winner is the passing row with the lowest measured
dollars; `python -m rlm.pin --reports` copies the winner's pass a into place and writes
`tests/phase5-digests.json` with the sha256 of `report.md`, `verify.json` and `grade.json`
per sample, refusing a sample with no winner; every phase 5 test passes on `atlas`,
`northwind` and `northstar-dental` with no code change between them; `LEDGER.md` gained one
phase 5 line per pass per sample per model; `src/rlm/gateway.py`'s `PRICES` reads what the
gateway's model list said on the day and `PAST_PRICES` keeps the old table; the pull request
body carries the table and the three samples' recall, verifier, spread and dollars.

## Mechanism

Survey in order. No skill, plugin or MCP fits; no new dependency. A new module
`src/rlm/writebakeoff.py` shaped on `rlm.bakeoff`: tiers, cheapest first, two passes per
model per sample through `rlm.write.main` into `runs/<sample>/write-bakeoff/<slug>/<pass>/`,
`--recount` rebuilding rows from disk, `--dry-run` printing the estimate. No probe: a write
is one call and costs what a probe would. `rlm.pin` gains `--reports` beside `--dossiers`.
The phase 5 test file gains a digest test in the shape of the phase 4 one. `PLAN.md`
section 5's price table and the phase 5 bake-off table are written in slice 06 from this
slice's `write-bakeoff.json`.

## Files

```aeo-independence
slice: 05-bakeoff-three-samples
creates: src/rlm/writebakeoff.py
creates: tests/phase5-digests.json
edits: src/rlm/pin.py
edits: src/rlm/gateway.py
edits: tests/test_phase5.py
depends-on: 04-map-rescoring-measured
```

## Out of scope

The status row and the tables in `PLAN.md` (slice 06). A model that fails on `northwind` or
`northstar-dental` and passes on `atlas` is a failing row, not a per-sample winner; if no row
passes everywhere, the pull request reports the nearest row and the phase's second attempt
is a new issue against the writer's prompt on the sample that failed.
