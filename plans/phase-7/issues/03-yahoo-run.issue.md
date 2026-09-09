# feat(phase-7): our tool once on sample 4, one graded report against the public record [slice 03]

**Issue:** #125 · **Spec:** PLAN.md#4-phases, row "7 Compare" · **Plan:** plans/phase-7/03-yahoo-run.md
**Depends on:** #124
**Labels:** phase-7

## Deliverable

`runs/yahoo/` holds every stage's artefact from one run of the unchanged chain on sample 4: one
notes pass on GLM 5.3 Flash, one write on GLM 5.3, the verifier and the grader, ledger rows booked
to phase 7. `grade.json` holds recall over the public record key. The phase 7 readout prints
sample 4's recall, dollars, verifier state and the first phase whose check fails or `holds`.

## Mechanism

The chain as it stands, once, under the gateway's $4 phase 7 cap, through the `--phase` flag
phase 6 added to `rlm.notes` and `rlm.write`. `tests/test_phase7_yahoo.py` gains the run checks,
importing the phase 1 to 5 helpers as `tests/test_phase6.py` does. A stage that drops a fact is
named in the pull request, not fixed here; under RULES.md gate 2 the fix belongs to that stage's
phase and the founder decides whether phase 7's cap buys a rerun.

## Acceptance criterion

Given slice 02 is merged, the filings are fetched and `OPENROUTER_API_KEY` is set,
when `rlm.ingest`, `rlm.notes --phase 7`, `rlm.map`, `rlm.dossier`, `rlm.write --phase 7`,
`rlm.verify` and `rlm.grade` run once on `samples/yahoo runs/yahoo`,
then every stage writes its artefact; `grade.json` holds recall over the key and no rubric;
`verify.json` passes or its failures are listed in the pull request; the ledger's phase 7 rows for
`yahoo` sum under $2; `tests/test_phase7_yahoo.py`'s run checks pass and its readout prints
recall, dollars, verifier state and the first phase whose check fails or `holds`; the digests of
`report.md`, `verify.json` and `grade.json` are in `tests/phase7-yahoo-digests.json`.

## Files

```aeo-independence
slice: 03-yahoo-run
creates: tests/phase7-yahoo-digests.json
edits: tests/test_phase7_yahoo.py
depends-on: 02-yahoo-fixture
```

## Out of scope

A second write. Any code change to phases 1 to 5.
