# 01: The RLM skill twice on sample 1, graded beside ours

Issue: [#123](https://github.com/Muhanad-husn/RLM/issues/123)

## Goal

`runs/atlas-rlm/compare.json` holds the RLM skill's two scores, spread, recall, seconds and
dollars on sample 1 beside our tool's, read from the pinned run.

## Acceptance criterion

Given `runs/atlas/` holds the pinned phase 5 run and the RLM skill sits under
`reference/rlm-skill/skill/` at commit `0039c005`,
when `python -m rlm.compare prepare samples/atlas runs/atlas-rlm` writes `corpus.txt` and
installs the skill under `.claude/skills/rlm/` of the checkout, the session runs `/rlm` twice
on that corpus with sample 1's brief as the query and saves the reports as
`runs/atlas-rlm/report.md` and `runs/atlas-rlm/b/report.md`, and `python -m rlm.compare grade
samples/atlas runs/atlas runs/atlas-rlm` runs,
then `corpus.txt` carries every section text of the 100 documents in ingest's order under a
header naming the DR id and path and is byte-identical when built twice; both reports are graded
by `rlm.grade` into `grade.json` and `b/grade.json`; `compare.json` holds for `rlm` and `ours`
each score a, score b, spread, recall a, seconds and dollars, with `rlm.dollars` 0 and
`ours.dollars` the phase 5 rows of `LEDGER.md` for `atlas`; `manifest.json` names the root and
leaf model ids and the two audit run ids; `LEDGER.md` holds no phase 7 row for `atlas-rlm`;
`tests/test_phase7.py` passes and its readout prints one line: rlm score a, score b, spread,
seconds against ours; the digests of the four graded files are in `tests/phase7-rlm-digests.json`.

## Mechanism

The RLM skill, fetched from the upstream commit, unchanged. New module `src/rlm/compare.py`:
`prepare` builds `corpus.txt` from `sections.jsonl` and copies the skill into the checkout's
`.claude/skills/rlm/`; `grade` calls `rlm.grade.grade` on each report, reads our pinned
numbers from `runs/atlas/grade.json`, `notes-summary.json`, `write-summary.json` and the
ledger, times `rlm.ingest`, `rlm.map` and `rlm.dossier` once in a temporary directory, and
writes `compare.json` and the digests. The root is the session; the leaf is the skill's
`claude -p` with Sonnet 5. `.gitignore` gains `.claude/skills/`. New `tests/test_phase7.py`
reads `runs/atlas-rlm/` and skips with a reason when it is absent.

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
