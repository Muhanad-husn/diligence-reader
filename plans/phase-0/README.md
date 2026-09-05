# Phase 0: Fixtures

Milestone `Phase 0`. Spec: `PLAN.md` section 4, row "0 Fixtures". Cap $0 through the gateway.

The outcome: every one of the three gate samples has a `key.json` of one shape, a brief in the
shape of sample 1's, and two hand-written reports, one perfect and one wrong. A grader in
`src/rlm/grade.py` gives the perfect report 100 and the wrong one under 40 on all three
samples, and that calibration is recorded in `PLAN.md`'s status table before any run artefact
is graded.

## The shape decisions this phase fixes

- **One key shape.** `key.json` carries `documents` (id to path inside the sample), `facts`
  (each with its documents, its value or quote, its kind, and the first phase whose artefact
  must carry it), `decoys`, `answer` (the number the report must land on), and `rubric`
  (the criteria table where the sample has one, empty where it does not). The loader in
  `src/rlm/key.py` is the definition; the test enforces it.
- **The score.** Planted-fact recall is code: a fact is recalled when its value appears in the
  report and one of its documents is cited. The rubric score is a Claude subagent run from
  code with `claude -p`, on the subscription, never through the gateway. Where the key has a
  rubric the score is the rubric score; where it has none the score is recall. `LEDGER.md`
  does not move in this phase.
- **Samples not yet keyed are skipped, not failed.** `tests/conftest.py` skips a sample whose
  `key.json` does not exist, so the suite is green on `main` between slices. The gate removes
  the skip.

## Slices

| NN | Slice | Plan | Issue | Depends on |
|---|---|---|---|---|
| 01 | The key shape, and sample 1's key and brief | [01-key-atlas.md](01-key-atlas.md) | #1 | none |
| 02 | The grader, calibrated on sample 1's perfect and wrong reports | [02-grade-atlas.md](02-grade-atlas.md) | #2 | 01 |
| 03 | Keys and briefs for samples 2 and 3 | [03-keys-northwind-northstar.md](03-keys-northwind-northstar.md) | #3 | 01 |
| 04 | Perfect and wrong reports for samples 2 and 3, graded with no code change | [04-reports-northwind-northstar.md](04-reports-northwind-northstar.md) | #4 | 02, 03 |
| 05 | Phase 0 gate | [05-gate.md](05-gate.md) | #5 | 04 |

Order of work: 01, then 02 and 03 in either order, then 04, then 05.
