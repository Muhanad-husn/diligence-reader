# 03: Our tool once on sample 4

Issue: [#125](https://github.com/Muhanad-husn/RLM/issues/125)

## Goal

`runs/yahoo/` holds the chain's artefacts and one graded report against the public record key.

## Acceptance criterion

Given slice 02 is merged, the filings are fetched and `OPENROUTER_API_KEY` is set,
when `rlm.ingest`, `rlm.notes --phase 7`, `rlm.map`, `rlm.dossier`, `rlm.write --phase 7`,
`rlm.verify` and `rlm.grade` run once on `samples/yahoo runs/yahoo`,
then every stage writes its artefact; `grade.json` holds recall over the key and no rubric;
`verify.json` passes or its failures are listed in the pull request; the ledger's phase 7 rows
for `yahoo` sum under $2; `tests/test_phase7_yahoo.py`'s run checks pass and its readout
prints recall, dollars, verifier state and the first phase whose check fails or `holds`; the
digests of `report.md`, `verify.json` and `grade.json` are in `tests/phase7-yahoo-digests.json`.

## Mechanism

The chain unchanged, once, on the gateway's phase 7 cap. `tests/test_phase7_yahoo.py` gains the
run checks, importing the phase 1 to 5 helpers as `tests/test_phase6.py` does. A stage that
drops a fact is named, not fixed here; under RULES.md gate 2 the fix belongs to that stage's
phase and the founder decides whether phase 7's $4 buys a rerun.

## Files

```aeo-independence
slice: 03-yahoo-run
creates: tests/phase7-yahoo-digests.json
edits: tests/test_phase7_yahoo.py
depends-on: 02-yahoo-fixture
```

## Out of scope

A second write. Any code change to phases 1 to 5.
