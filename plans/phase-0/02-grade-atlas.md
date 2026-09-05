# 02: The grader, calibrated on sample 1's perfect and wrong reports

Issue: [#2](https://github.com/Muhanad-husn/RLM/issues/2)

## Goal

`src/rlm/grade.py` gives `samples/atlas/fixtures/report-perfect.md` a score of 100 and
`samples/atlas/fixtures/report-wrong.md` a score under 40, and prints recall, rubric score
and the model that graded.

## Acceptance criterion

Given sample 1's key from slice 01 and the two fixture reports,
when `pytest -q tests/test_phase0.py -k grade` runs,
then for sample `atlas` the perfect report scores 100 with planted-fact recall 100%, the wrong
report scores under 40, and `runs/atlas/grade-perfect.json` and `grade-wrong.json` exist with
recall, per-criterion rubric points, the grader model id and the elapsed seconds.
`LEDGER.md` is unchanged.

## Mechanism

- No skill or plugin fits: the grader is the tool's own stage and lives in `src/rlm/`.
- Recall is code. A fact is recalled when its normalised value (whitespace collapsed, case
  folded, thousands separators and currency marks dropped, `m` and `million` equal) appears in
  the report and at least one of its documents is cited anywhere in the report. Recall is
  recalled facts over all facts, as a percentage.
- The rubric score is one model call, the subscription subagent named in `PLAN.md`: a
  `subprocess` running `claude -p --output-format json` with the rubric rows, the answer key
  and the report, asking for JSON of points and one-line reason per criterion. The
  Anthropic SDK and the gateway are not used; the grader never reads `OPENROUTER_API_KEY`.
  Score is the rubric total where the key has a rubric, else recall.
- The perfect report is written by hand from the answer key's gold-standard answer and price
  bridge, in the brief's five sections, citing all fourteen required documents by id. The
  wrong report elevates DR-031 (tax nexus) as the most material issue, treats the security
  matter as routine credential hygiene, cites no exposure number and recommends "raise in
  Q&A".

## Files

```aeo-independence
slice: 02-grade-atlas
creates: src/rlm/grade.py
creates: samples/atlas/fixtures/report-perfect.md
creates: samples/atlas/fixtures/report-wrong.md
edits: tests/test_phase0.py
depends-on: 01-key-atlas
```

## Out of scope

Two-run spread (the gate). The verifier. Reports for samples 2 and 3. Any grading of a run
artefact.
