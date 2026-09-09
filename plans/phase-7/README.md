# Phase 7: Compare

Milestone `Phase 7`. Spec: `PLAN.md` section 4, row "7 Compare". Cap $4. The last phase. Two
things are measured and written beside each other: the recursive language model (RLM) skill run
on sample 1 from Claude Code, on the subscription, against our tool's pinned run; and our tool
once on sample 4, the Verizon and Yahoo filings, against the key from the public record.

The outcome: `runs/atlas-rlm/` holding two RLM reports, their grades, the spread and the wall
time, with our tool's score, spread, dollars and time beside them in one `compare.json`;
`samples/yahoo/key.json` and `brief.md` in the phase 0 shape, the seven filings fetched by code;
`runs/yahoo/` holding our chain's artefacts and one graded report; `PLAN.md` section 4a's phase
7 row and a comparison table.

## The bar

There is no pass bar for the RLM: its numbers are reported beside ours. Sample 4's bar is the
one samples 2 and 3 carry: planted-fact recall 100 and the verifier passing. Sample 4 is not a
data room and its score is reported with that stated, as `samples/yahoo/README.md` says.

## The shape decisions this phase fixes

- **The RLM run is the skill as shipped, on the subscription.** The skill files are fetched
  from Brainqub3/claude_code_RLM at `0039c005`, the commit `reference/rlm-skill/UPSTREAM_COMMIT`
  names, into `reference/rlm-skill/skill/`, where `README.md` already says the skill lives. The
  root is the Claude Code session that builds the issue; the leaf is the skill's `claude -p`
  call with Sonnet 5, the leaf tier the winning run used. The context is one `corpus.txt` built
  by code from sample 1's pinned `runs/atlas/sections.jsonl`, one header per document carrying
  its DR id and path, so the corpus is byte-identical between the two runs. The query is sample
  1's `brief.md`. No gateway call, no ledger row.
- **Two runs, graded by the same grader.** Each run's report is graded by `rlm.grade` against
  sample 1's key, as our reports are. `compare.json` holds, for the RLM and for ours: score a,
  score b, spread, recall, seconds, dollars. Ours are read from the pinned run's `grade.json`,
  `notes-summary.json`, `write-summary.json` and the phase 5 rows of `LEDGER.md`; the free
  stages are timed in place. The RLM's seconds come from the skill's audit manifest.
- **Sample 4 is fetched and split by code.** `python -m rlm.yahoo fetch samples/yahoo` reads
  the seven filings from SEC EDGAR with the User-Agent EDGAR asks for, into
  `samples/yahoo/documents/` (gitignored), and writes each filing as one folder of markdown
  files, one per top-level item or heading, none longer than 40,000 characters, so that no
  document is more than about twice sample 1's largest and `rlm.notes` reads each in one call.
  The key's documents point at the section files. Ingest gains nothing; the filings reach it as
  markdown, the convention samples 2 and 3 and the phase 6 variants already use.
- **The key is the public record.** `samples/yahoo/key.json` carries the facts
  `samples/yahoo/README.md` names: the $350m cut, the $4,475.8m price, the 500m and 1bn
  account counts, the 50/50 split, the forged cookies, the 2014 contemporaneous knowledge, the
  signing and amendment dates. No rubric; recall and the verifier are the bar. The answer is
  reprice by $350m. The brief is written in sample 1's shape for a buyer reading the filings.
- **Our tool runs once on sample 4.** One notes pass on GLM 5.3 Flash, one write on GLM 5.3,
  the verifier, the grader; ledger rows booked to phase 7 through the `--phase` flag phase 6
  added. No spread, as `PLAN.md` says once.
- **Money.** Sample 4's text is about four times sample 1's. One notes pass on GLM 5.3 Flash
  about $0.30, one write with a re-ask on GLM 5.3 about $0.40. Expected under $1 of the $4
  cap. The RLM run and the grader cost nothing on the ledger.

## Slices

| NN | Slice | Plan | Issue | Depends on |
|---|---|---|---|---|
| 01 | The RLM skill twice on sample 1, graded beside ours | [01-rlm-atlas.md](01-rlm-atlas.md) | #123 | none |
| 02 | Sample 4 fetched, split and keyed | [02-yahoo-fixture.md](02-yahoo-fixture.md) | #124 | none |
| 03 | Our tool once on sample 4 | [03-yahoo-run.md](03-yahoo-run.md) | #125 | 02 |
| 04 | Phase 7 gate | [04-gate.md](04-gate.md) | #126 | 01, 03 |

Order of work: slices 01 and 02 concurrently, each in its own worktree. Slice 03 after 02 is
merged. Slice 04 after 01 and 03 are merged.

## A risk to name

The RLM's root is the session, so its two runs are two sessions of about forty minutes each
and their reports are not reproducible; the spread is the point. Sample 4's filings may carry
a planted value in more than one form (a table cell and a sentence); the key names the form
the fetched text carries, checked by the fixture test before any model reads it.
