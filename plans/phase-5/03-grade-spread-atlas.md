# 03: Grade and spread on sample 1, two writes, rubric at or above 85, kill line read

Issue: [#81](https://github.com/Muhanad-husn/RLM/issues/81)

## Goal

`runs/atlas/grade.json` and `runs/atlas/b/report.md`, `verify.json`, `grade.json` exist: two
writes of the same request, each verified and graded, the rubric score of pass a at or
above 85, the spread between the two rubric scores printed.

## Acceptance criterion

Given slice 02 is merged,
when `python -m rlm.write samples/atlas runs/atlas --passes 2` runs and then `pytest -q
tests/test_phase5.py` runs,
then pass a's files sit in `runs/atlas/` and pass b's in `runs/atlas/b/`; each `grade.json`
was written by `rlm.grade.grade` and holds recall, the missed ids, the nine rubric rows with
points and reasons, the score, the grader's model and seconds; pass a's `grade.json` also
holds `spread`, the absolute difference of the two rubric scores, and `score_b`; pass a's
recall is 100, its verifier passes and its rubric score is at or above 85; pass b's recall,
verifier and score are printed in the readout and not gated; `LEDGER.md` gained two phase 5
lines for `atlas` and no line for the grader; the readout prints score a, score b, spread,
dollars of the two passes and seconds; the pull request body carries the rubric rows with
the grader's reasons for both passes and the total phase spend against the kill line
(sample 1 under 70 after $25 spent).

## Mechanism

Survey in order. No skill, plugin or MCP fits; no new dependency. `rlm.write.main` gains
`--passes` (1 or 2) and `--out` for the pass b directory, calls `rlm.grade.grade` after each
verified write, and writes `spread` and `score_b` into pass a's grade file when two passes
ran. `rlm.grade` is unchanged except that `grade()` takes the output file name, so pass a
writes `grade.json` and not `grade-<name>.json`. The grader is one `claude -p` per pass on
the subscription, as phase 0 built it. Tests committed red first: the rubric test asserts 85
and skips when `grade.json` is absent.

## Files

```aeo-independence
slice: 03-grade-spread-atlas
edits: src/rlm/write.py
edits: src/rlm/grade.py
edits: tests/test_phase0.py
edits: tests/test_phase5.py
depends-on: 02-verify-atlas
```

## Out of scope

Samples 2 and 3 and other models (slice 05). The map rescoring (slice 04). A score under 85
is reported row by row with the grader's reasons; the writer's prompt is revised where the
reasons name the report, and the dossier is traced where they name a fact the dossier lacks,
which is a phase 4 issue. A score under 70 stops the phase and goes to the founder.
