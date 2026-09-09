# chore(phase-7): the RLM skill run twice on sample 1 from Claude Code, graded and timed beside ours [slice 01]

**Issue:** #123 · **Spec:** PLAN.md#4-phases, row "7 Compare" · **Plan:** plans/phase-7/01-rlm-atlas.md
**Depends on:** none
**Labels:** phase-7

## Deliverable

`runs/atlas-rlm/` holds two reports written by the recursive language model skill, as shipped at
upstream commit `0039c005`, run from this Claude Code session on the subscription with sample 1's
brief as the query and a code-built `corpus.txt` as the context. Both reports are graded by
`rlm.grade` against sample 1's key. `compare.json` puts the RLM's score a, score b, spread, recall,
seconds and dollars beside our tool's, read from the pinned `runs/atlas/`. No gateway call, no
ledger row.

## Mechanism

The skill files are fetched into `reference/rlm-skill/skill/`. New module `src/rlm/compare.py`:
`prepare` builds `corpus.txt` from `runs/atlas/sections.jsonl`, one header per document with its
DR id and path, and copies the skill into the checkout's `.claude/skills/rlm/`; `grade` grades
each report with `rlm.grade.grade`, reads our numbers from `runs/atlas/grade.json`,
`notes-summary.json`, `write-summary.json` and the phase 5 rows of `LEDGER.md`, times the free
stages once in a temporary directory, and writes `compare.json`, `manifest.json` and
`tests/phase7-rlm-digests.json`. The root is the session; the leaf is the skill's `claude -p`
with Sonnet 5, the leaf tier of the winning run. `.gitignore` gains `.claude/skills/`.

## Acceptance criterion

Given `runs/atlas/` holds the pinned phase 5 run and the RLM skill sits under
`reference/rlm-skill/skill/` at commit `0039c005`,
when `python -m rlm.compare prepare samples/atlas runs/atlas-rlm` writes `corpus.txt` and
installs the skill, the session runs `/rlm` twice on that corpus with sample 1's brief as the
query and saves the reports as `runs/atlas-rlm/report.md` and `runs/atlas-rlm/b/report.md`, and
`python -m rlm.compare grade samples/atlas runs/atlas runs/atlas-rlm` runs,
then `corpus.txt` carries every section text of the 100 documents in ingest's order under a
header naming the DR id and path and is byte-identical when built twice; both reports are graded
into `grade.json` and `b/grade.json`; `compare.json` holds for `rlm` and `ours` each score a,
score b, spread, recall a, seconds and dollars, with `rlm.dollars` 0 and `ours.dollars` the
phase 5 rows of `LEDGER.md` for `atlas`; `manifest.json` names the root and leaf model ids and
the two audit run ids; `LEDGER.md` holds no phase 7 row for `atlas-rlm`; `tests/test_phase7.py`
passes and its readout prints one line, the RLM's score a, score b, spread and seconds against
ours; the digests of the four graded files are in `tests/phase7-rlm-digests.json`.

## Files

```aeo-independence
slice: 01-rlm-atlas
creates: reference/rlm-skill/skill/
creates: src/rlm/compare.py
creates: tests/test_phase7.py
creates: tests/phase7-rlm-digests.json
edits: .gitignore
edits: reference/rlm-skill/README.md
```

## Out of scope

Any change to the skill. A third run. Sample 4.
