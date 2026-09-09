# Phase 5: Report

Milestone `Phase 5`. Spec: `PLAN.md` section 4, row "5 Report". Cap $8. The second phase that
calls a model and writes `LEDGER.md`. The grader runs on the Claude Code subscription and
writes no ledger line.

The outcome: `runs/<sample>/report.md`, `verify.json` and `grade.json` exist for all three
gate samples. The report is the five-section findings report the brief asks for, written by
one model call from the dossier and nothing else, every sentence cited to one dossier anchor,
quotes and certainty words copied. The verifier is code: every citation resolves, every number
exists in its source, no certainty word is raised, the decoys rank below the main matter; its
failures go back to the writer once as a list. The grade is planted-fact recall by code and,
on sample 1, the rubric score by a Claude subagent reading the key. Two writes are run and
the spread is printed. Five models are tried, cheapest first, and the cheapest that passes on
all three samples is pinned as the phase 5 model.

## The bar

Planted-fact recall 100 on every sample, over every fact of the key, measured by
`rlm.grade.measure_recall`. Rubric 85 on sample 1, the rubric's own floor for "excellent",
`PLAN.md` section 10's proposal, set by the founder with this plan's approval. Samples 2 and 3
have no rubric: their bar is recall and the verifier. The kill line of `RULES.md` gate 5 is
watched at slice 03: sample 1 under 70 after $25 spent means the method is wrong. $1.51 of
the $50 is spent as this plan is written.

A number behind the bar: the first build's 98.5-point RLM report measures 32.08 on the same
recall, because it paraphrases where the key wants the room's own words. The dossier carries every planted fact verbatim, so the writer is told to quote, not
to summarise. If sample 1's recall is under 100 after slice 01's two attempts, the founder
sets the bar under `RULES.md` gate 3; the test is not loosened by the builder.

## The shape decisions this phase fixes

- **The writer reads the brief and the dossier, nothing else.** The brief is the task
  (`samples/<sample>/brief.md`); the dossier is the evidence. No section text, no notes, no
  map, no key. One call, temperature 0, seed 0, reasoning as the gateway gives the model, a
  hard output cap of 8000 tokens. Markdown out; the gateway's JSON mode is switched off for
  this call by a flag on `Gateway.complete`, the only change to the gateway.
- **Every sentence cites, in one grammar.** A citation is `[<doc> | <anchor>]`, the second
  and fourth columns of a dossier row, copied. A sentence with no citation is allowed only
  on the executive summary's recommendation line and on a `Calculation:` line. This is what
  the verifier and the phase 5 tests parse; the report's prose is for the reader.
- **Numbers exist in their source or are computed on a labelled line.** Every number in a
  cited sentence, normalised as `rlm.grade.normalise` does, exists in the text of a cited
  section. A number that exists in no source (the price reduction) sits on a line beginning
  `Calculation:` that names its operands, each of which exists in a section cited on that
  line.
- **Certainty words are a ladder in code, and the report may not climb it.** Three rungs:
  possible (`may`, `might`, `could`, `possible`, `potential`), probable (`likely`,
  `probable`, `indicative`, `expected`, `approximately`, `estimated`), certain (`confirmed`,
  `certain`, `conclusive`, `definitive`, `established`). The highest rung in a cited
  sentence may not be above the highest rung in the sections it cites. The ladder is a
  module constant of `src/rlm/verify.py`, the same for every sample.
- **Decoys rank below the main matter, read from the dossier and not from the key.** The
  first finding of section 2 cites at least one document of the dossier's first matter's
  document set, and no finding that cites only lesser-matter documents comes before a finding
  that cites the set. The phase 5 test then reads the key's decoys against the report's
  finding order; the verifier never reads the key.
- **Fail, return once, stop.** The verifier's failures go back to the model as a list in one
  second call carrying the first reply, with the instruction to fix each line and change
  nothing else. `verify.json` records both rounds. `report.md` is the second reply when a
  second call was made. What still fails after the second call fails the phase test. No third
  call.
- **Two writes, same request.** Pass a is `report.md`, `verify.json`, `grade.json`; pass b is
  the same three files under `runs/<sample>/b/`. The spread is the rubric score of a against b
  on sample 1 and recall a against b on samples 2 and 3, printed in the readout and written
  into the grade files. Nothing votes between the passes.
- **The grader is the phase 0 grader.** `rlm.grade` as calibrated in phase 0 (perfect 100,
  wrong under 40 on all three samples), unchanged except for the spread it writes. One
  `claude -p` call per rubric grade, on the subscription, never through the gateway.
- **The map's scoring is redesigned inside this phase, and measured.** The founder approved
  on 2026-09-07 (PR #67) a redesign that brings sample 1's document set down from 68 towards
  fourteen, parked on this milestone. It runs as slice 04, after the writer, verifier and
  grader exist on the 68-document dossier, so its effect on score, dollars and spread is a
  measured delta and not an assumption. It stays if a number moves, as `RULES.md` gate 1
  asks; it is deleted if none does.
- **The bake-off is one run over three samples.** `python -m rlm.writebakeoff` mirrors
  `rlm.bakeoff`: flash tier first, pro tier only when every flash model fails, two passes per
  model per sample, the table written after each model. A row passes when pass a on every
  sample has recall 100 and a passing verifier, and on sample 1 a rubric score at or above
  the bar. Cheapest passing row wins and is pinned by digest. Prices are reread from the
  gateway on the day and rewritten in `PLAN.md` section 5: on 2026-09-07 DeepSeek V4 Flash
  reads 0.14 in and 0.28 out and DeepSeek V4 Pro reads 0.955 and 1.911, both up from the
  table.
- **Tests read the artefact; they do not call the model.** A phase 5 test skips with the
  reason "report not written for this sample yet" when `runs/<sample>/report.md` is absent.
  The write is launched detached, the tests run after it.

## Slices

| NN | Slice | Plan | Issue | Depends on |
|---|---|---|---|---|
| 01 | Report on sample 1: one call from the dossier, cited, recall 100 by code | [01-write-atlas.md](01-write-atlas.md) | #79 | none |
| 02 | Verifier on sample 1: four checks, failures returned once | [02-verify-atlas.md](02-verify-atlas.md) | #80 | 01 |
| 03 | Grade and spread on sample 1: two writes, rubric at or above 85, kill line read | [03-grade-spread-atlas.md](03-grade-spread-atlas.md) | #81 | 02 |
| 04 | Map rescoring, measured: the set from 68 towards fourteen, kept by its delta | [04-map-rescoring-measured.md](04-map-rescoring-measured.md) | #82 | 03 |
| 05 | Bake-off on the three samples: five models, table, winner pinned | [05-bakeoff-three-samples.md](05-bakeoff-three-samples.md) | #83 | 04 |
| 06 | Phase 5 gate | [06-gate.md](06-gate.md) | #84 | 05 |

Order of work: 01 to 06, one after the other. Every slice edits `src/rlm/write.py` or
`tests/test_phase5.py` or runs the model on the previous slice's artefact, so nothing runs
concurrently.

## Money

Sample 1's dossier is 156k estimated tokens today; a write is one call of that size plus one
re-ask of about the same, about 6k tokens out each. At the gateway's prices read on
2026-09-07, one pass on sample 1 costs about $0.03 on GLM 5.3 Flash, $0.05 on DeepSeek V4
Flash, $0.08 on Luna, $0.33 on DeepSeek V4 Pro, $0.50 on GLM 5.3. Samples 2 and 3 together
are about a third of that. Slices 01 to 03 spend about $0.30 over their development writes on
GLM 5.3 Flash. Slice 04 spends about $0.10 rerunning the chain. Slice 05 spends about $0.45 if
a flash model or Luna passes and about $2.60 if the pro tier runs, a quarter of that if slice
04 brings the dossier to a quarter of its size. Expected phase total under $1; worst case
about $3.20 of the $8 cap. The grader costs $0 on the subscription.

## What the samples make this phase carry

Sample 1: 53 facts across phases 1 to 5, seven of them comparisons whose two sides must both
appear in the report's words, and the price reduction of $400m, which no document states and
the report must compute on a labelled line from the counsel's $240m to $465m, the $12m reserve
and the synergy model. Nine rubric rows, 100 points, bar 85. A dossier of 68 documents and
2,700 rows until slice 04.

Sample 2: 16 facts, two comparisons, the $12.4m revenue cliff as the answer. The decoy is the
Granite MSA, a lesser matter in the dossier; the report must rank it below Meridian.

Sample 3: 13 facts, one comparison, the restated growth of 11.7% as the answer. No decoy.

## A risk to name

The recall measure wants the key's words. Numbers, dates and identifiers are exact strings the
dossier carries; the fifteen phase 2 quotes are the notes' quotes, copied into the dossier; the
seven comparisons are two quoted halves each. A writer that quotes the dossier's rows can hit
every one of them; a writer that summarises will land near the winner's 32. Slice 01's prompt
asks for quotes and its test is 100 on sample 1. Its second failure is the phase's second
attempt under `RULES.md` gate 3, and the founder decides the bar then.
