# Slice 02: The command

Milestone `Phase 8`. Issue: [#137](https://github.com/Muhanad-husn/diligence-reader/issues/137). Spec: `PLAN.md#4c-phase-8-the-product`. Depends on: slice 01 of this phase, 01-export.

## Deliverable

A console script `diligence-reader` (project version set to 0.8.0, read back as `rlm.__version__` from package metadata). `diligence-reader run <room> --out <run_dir>` runs ingest, notes, map, dossier, write (one pass, which verifies), then export, using each module's own DEFAULT_MODEL. Before the first model call it prints the input tokens counted by the gateway's counter and the estimated dollars (notes priced on the counted input and the output ratio of sample 1's phase 2 ledger rows; write priced at its digest cap) and asks y/N; `--yes` skips the prompt. A stage whose artefact already exists in the run folder is skipped, so running again after a failure starts at the stage that stopped. `run.json` is written at every stage boundary: stage, status, error code, documents noted, dollars spent, version. A room without brief.md uses `src/rlm/brief.md`. Recall is graded by code when the room has key.json; no rubric. Without `--phase` nothing writes LEDGER.md and no cap applies; `--phase 8` books LEDGER.md under `8: 3.0` added to PHASE_CAPS. Every failure exits non-zero with one code from the list in the README, written to run.json. `pipx install .` gives the command.

## Mechanism

argparse in a new src/rlm/cli.py calling each module's main or its functions with an injected gateway; a ledger-free batch in src/rlm/gateway.py that applies no cap, writes nothing and keeps the dollars for run.json; HTTP status mapped to codes (401 and 403 key-refused, 402 no-credits, 429 after the gateway's own retries rate-limited, null content empty-reply).

Survey: no skill or MCP applies; library is argparse plus `[project.scripts]` in pyproject.toml; no model call; the chosen approach is a clean CLI module that each stage can call.

## Acceptance criterion

Given an OpenRouter key and samples 1, 2 and 3, when `diligence-reader run samples/<s> --out runs/<s>-cli --yes --phase 8` runs, then recall is 100 on each, the verifier passes, run.json reads done with the dollars spent, and the printed estimate came before the first call and is within a factor of two of the dollars spent; when a run is stopped after notes and run again, ingest and notes do not run again and no new notes ledger row is written; when run without `--phase`, LEDGER.md is byte-identical before and after; a refused key leaves run.json with `key-refused` and no artefact past ingest; a room with no brief.md runs on the default brief; `pipx install .` puts `diligence-reader` on the path.

## Tests

tests/test_phase8_command.py: end to end on samples 2 and 3, sample 1 once; resume and error mapping with a fake gateway transport at $0.

## Money

About $0.45.

## Risks

The fresh-notes northwind miss named in the README.

## Files

```aeo-independence
slice: 02-command
creates: src/rlm/cli.py
creates: src/rlm/brief.md
creates: tests/test_phase8_command.py
edits: src/rlm/gateway.py
edits: src/rlm/notes.py
edits: src/rlm/write.py
edits: pyproject.toml
depends-on: 01-export
```

## Out of scope

The API, the web page, two write passes (the gate takes its spread from two runs), the rubric.
