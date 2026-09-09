# Phase 7: Compare

Milestone `Phase 7`. Spec: `PLAN.md` section 4, row "7 Compare". Cap $4. The last phase. One
thing is measured: our tool once on sample 4, the Verizon and Yahoo filings, against the key
from the public record.

The outcome: `samples/yahoo/key.json` and `brief.md` in the phase 0 shape, the seven filings
fetched by code; `runs/yahoo/` holding our chain's artefacts and one graded report; `PLAN.md`
section 4a's phase 7 row and section 4b's table.

## The bar

Sample 4's bar is the one samples 2 and 3 carry: planted-fact recall 100 and the verifier
passing. Sample 4 is not a data room and its score is reported with that stated, as
`samples/yahoo/README.md` says.

## The shape decisions this phase fixes

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
  cap. The grader costs nothing on the ledger.

## Slices

| NN | Slice | Plan | Issue | Depends on |
|---|---|---|---|---|
| 02 | Sample 4 fetched, split and keyed | [02-yahoo-fixture.md](02-yahoo-fixture.md) | #124 | none |
| 03 | Our tool once on sample 4 | [03-yahoo-run.md](03-yahoo-run.md) | #125 | 02 |
| 04 | Phase 7 gate | [04-gate.md](04-gate.md) | #126 | 03 |

Order of work: slice 02 first, in its own worktree. Slice 03 after 02 is merged. Slice 04 after
03 is merged.

## A risk to name

Sample 4's filings may carry a planted value in more than one form (a table cell and a
sentence); the key names the form the fetched text carries, checked by the fixture test before
any model reads it.
