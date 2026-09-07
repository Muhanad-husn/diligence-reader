# RLM: the rebuild plan

Written 2026-09-05. This is the plan of record. It replaces everything in the first build; that
build's lessons are in `reference/design-mistake-register-first-build.md` and are not repeated
here except where they became a rule.

## 1. What is being built

A tool that does what the recursive language model (RLM) did on the Project Atlas data room,
with the same shape and three properties the RLM lacks: reproducible in the middle, cheap, and
runnable on other document sets. The RLM's own winning run is the specification of the shape
(`reference/winner-trail.md`); this plan replaces its improvised parts with fixed ones and keeps
the model where the model is the only thing that works.

**The final deliverable of the method** is one document: a findings report in the five sections
the task brief asks for (recommendation with a number, findings ranked by materiality with
citations, the most material issue quantified with a specific deal action, lesser issues, open
items), produced from raw documents with no human step, with three numbers printed beside it:
its score against the sample's key, the dollars it cost, and the spread between two runs.

## 2. The method

Seven stages. Two call a model. Everything else is code and is byte-identical across runs.

| Stage | Kind | Input | Output |
|---|---|---|---|
| Ingest | code | raw files (PDF, XLSX, CSV, TXT, EML, MBOX, MD) | sections with anchors; index of dates, amounts, names, identifiers, status words (draft, final, redacted, privileged), version pairs, series |
| Notes | model, one call per document, fixed schema | one document | JSON: what this is, flags, figures with verbatim quotes, cross-references (codes, names, people, documents), what looks concealed. Every quote and figure verified against the source by code; a failed note is re-asked once, then dropped and logged |
| Map | code | index + notes | document graph (shared identifiers, note cross-references, date proximity, versions); clusters; consequence links (a series that breaks at a cluster's date, a model dated after it); ranked document list per matter |
| Dossier | code | map + index + notes | per matter: timeline of dated statements, every name each function gave it, figures with sources, draft against final, booked reserve against stated estimate, deadlines against actions, models blind to it, lesser matters ranked by money |
| Write | model, one call | dossier only | the five-section report; every sentence cites; certainty words copied, never raised |
| Verify | code | report + sources | every citation resolves, every number exists in its source, no certainty word raised, decoys ranked below the main matter; failures returned to Write once as a list |
| Grade | code + subscription subagent | report + key | planted-fact recall by code; rubric score by a Claude subagent reading the key; two-run spread |

What the RLM did that this does not: improvise the program per run, read the cluster's full
text a second time, read the notes a third time, judge document pairs. What this does that the
RLM did not: verify every model sentence against the source, and run the same program twice.

## 3. Samples and keys

Every phase passes on sample 1, then on samples 2 and 3 with no code change between. Sample 4
runs once, at the end. Keys and briefs are in `samples/README.md`.

| # | Name | Documents | Planted truth | Source |
|---|---|---|---|---|
| 1 | `atlas` | 100, six formats, eight folders | one matter across six functions, five decoys; answer key, expected findings, 100-point rubric | brainqub3/synthetic-dataRoom, MIT |
| 2 | `northwind` | 11 markdown-rendered contracts, schedules, deck | one cross-document finding (a change-of-control clause against a 30.1% customer), a control clause, four secondary gaps, a deck that misstates the exposure | zoharbabin/due-diligence-agents, Apache-2.0 |
| 3 | `northstar-dental` | 15 markdown and xlsx | one numeric contradiction, five ground-truth questions | The-Life/synthetic-dataroom-generator, MIT, seeded |
| 4 | `yahoo` | public SEC filings, 2016 to 2017 | the real case: an undisclosed breach, a $350m price cut, a liability split | SEC EDGAR, public domain; fetched in phase 7 |

## 4. Phases

One artefact per phase. The planted key is checked against that artefact by a test. A phase is
done when its tests pass on samples 1, 2 and 3. Nothing later may compensate for an earlier gap;
the gap is fixed in its own phase and every later phase reruns.

| Phase | Artefact | Test against the key | Model | Cap |
|---|---|---|---|---|
| 0 Fixtures | `samples/*/key.json` in one shape for all three samples; a brief per sample; a hand-written perfect report and a wrong one per sample | Grader gives the perfect report 100 and the wrong one under 40 on all three samples. Calibrated before anything else is graded | subagent | $0 |
| 1 Ingest | `runs/<sample>/sections.jsonl`, `index.jsonl` | Every planted fact's anchor exists. Every planted number, date and identifier is in the index. Two runs byte-identical | none | $0 |
| 2 Notes | `runs/<sample>/notes/<doc>.json`, `notes-verify.jsonl` | Every planted fact appears in the note of its own document, with a verified quote. Two passes: agreement on planted facts printed. Bake-off over the five models, cheapest that passes wins | bake-off | $8 |
| 3 Map | `runs/<sample>/map.json` | Every key document of the planted matter in its cluster. Deterministic over pinned notes. The decoy count in the cluster is printed, not gated: moved to phase 4 on 2026-09-07, see the phase 4 row | none | $0 |
| 4 Dossier | `runs/<sample>/dossier.md` | Every planted fact present with the right anchor and number. No decoy in the matter's document set, and every planted document ranked above every decoy. Read by the founder once as a reader. Byte-identical | none | $0 |
| 5 Report | `runs/<sample>/report.md`, `verify.json`, `grade.json` | Verifier passes. Score at or above the bar. Two writes, spread printed. Bake-off over the five models | bake-off | $8 |
| 6 Widen | same artefacts under `runs/<sample>-<knob>/` | Phases 1 to 5 hold when a knob is turned on the fixture: names spelled inconsistently, the matter named nowhere and linked only by dates and numbers, a second matter, twice the documents. Each knob is one generated variant of sample 1 with its own key. A failure names the phase that dropped the fact | as chosen in 2 and 5 | $15 |
| 7 Compare | `runs/atlas-rlm/`, `runs/yahoo/` | The RLM skill run on sample 1 from Claude Code (subscription, no gateway spend): its score, spread and time beside ours. Then our tool once on sample 4 against the public record | as chosen | $4 |

Reserve: $15 of the $50. Nothing borrows from it without the reason written in `LEDGER.md`
first.

**The bar for phase 5.** Planted-fact recall 100% (the key is by construction). Rubric score: 85
on sample 1, the rubric's own floor for "excellent", proposed here and set by the founder.
Samples 2 and 3 have no rubric; their bar is recall and the verifier.

**Kill line.** If phase 5 on sample 1 is under 70 after $25 of the $50 is spent, the method is
wrong, not a phase. Stop, write what the phase tests showed, and redesign before another dollar.

## 4a. Status

One row per phase, written by the phase's closing pull request. Score is planted-fact recall
on the three gate samples and, from phase 5, the rubric score on sample 1.

| Phase | Milestone | State | Score | Dollars | Spread | Closed |
|---|---|---|---|---|---|---|
| 0 Fixtures | Phase 0 | done | 100 / 100 / 100 | 0 | 0 | 2026-09-05 |
| 1 Ingest | Phase 1 | done | 100 / 100 / 100 | 0 | 0 | 2026-09-06 |
| 2 Notes | Phase 2 | done | 100 / 100 / 100 | 1.51 | 0 / 20 / 0 | 2026-09-06 |
| 3 Map | Phase 3 | done | 100 / 100 / 100 | 0 | 0 / 0 / 0 | 2026-09-07 |
| 4 Dossier | Phase 4 | not started | | | | |
| 5 Report | Phase 5 | not started | | | | |
| 6 Widen | Phase 6 | not started | | | | |
| 7 Compare | Phase 7 | not started | | | | |

**How a phase becomes issues.** The founder types `/aeo:sprint-plan` for the phase. The plan is
sliced into three to six issues, each a vertical piece that leaves an artefact a test checks
against the key on at least one sample, in this order: the artefact on sample 1, the same
artefact on samples 2 and 3, then the closing issue `Phase N gate` that runs all phase tests on
all three samples and fills the row above. Each issue is one session and one pull request. No
issue of the next phase exists before the gate issue closes.

## 5. Models

Five candidates, chosen per task by the bake-off tables in phases 2 and 5, never by preference.
Prices read from the gateway on 2026-09-06, per million tokens, prompt then completion.

| Model | Id | In | Out |
|---|---|---|---|
| Luna | `openai/gpt-5.6-luna` | 0.200 | 1.200 |
| DeepSeek V4 Flash | `deepseek/deepseek-v4-flash-0731` | 0.050 | 0.100 |
| DeepSeek V4 Pro | `deepseek/deepseek-v4-pro` | 0.657 | 1.314 |
| GLM 5.3 | `z-ai/glm-5.3` | 1.400 | 4.400 |
| GLM 5.3 Flash | `z-ai/glm-5.3-flash` | 0.075 | 0.250 |

No Gemini. No model from outside this table without the founder's word. Prices are reread and
rewritten here the day a bake-off runs.

What one full note pass on sample 1 costs at these prices (about 90k tokens in, about 60k out
with a tight schema): DeepSeek Flash $0.01, GLM Flash $0.02, Luna $0.09, DeepSeek Pro $0.14,
GLM 5.3 $0.39. A five-model bake-off on sample 1 is under $1. Samples 2 and 3 are under a cent
each on any model.

**Bake-off table, filled per phase, one row per model:** passes the gate (yes or no), dollars,
two-run agreement on planted facts, seconds. The cheapest row that passes wins. A Flash model
is tried first; a Pro tier is tried only where every Flash fails.

**Phase 2 bake-off, rerun 2026-09-06 with figure sentences harvested by code**
(`runs/<sample>/bakeoff.json`). Before its two full passes a model is probed once on the seven
documents whose planted sentences DeepSeek Flash missed in slices 02 and 03 (six of `atlas`, one
of `northwind`); a model that misses any of the seven probe facts is recorded as failing and runs
no full pass. A row passes when its pass a carries every planted fact on every sample, as the
phase 2 test in section 4 asks; the two-pass agreement is the spread and is reported, not gated
(founder's decision, 2026-09-06, issue #49). Recall is pass a and pass b per sample; agreement is
`atlas`, `northwind`, `northstar-dental`. **Winner: GLM 5.3 Flash**, the cheapest passing row,
and the default `--model` of `python -m rlm.notes`.

| Model | Probe atlas | Probe northwind | Recall | Passes | Dollars | Agreement | Seconds |
|---|---|---|---|---|---|---|---|
| DeepSeek V4 Flash | 5 of 6, missed covenant-termination | 1 of 1 | not run | no | 0.0034 | not run | 130 |
| GLM 5.3 Flash | 6 of 6 | 1 of 1 | atlas 15/15 and 15/15; northwind 5/5 and 4/5; northstar-dental 2/2 and 2/2 | yes | 0.1803 | 1.0, 0.8, 1.0 | 2606 |
| Luna | 6 of 6 | 1 of 1 | atlas 15/15 and 15/15; northwind 5/5 and 4/5; northstar-dental 2/2 and 2/2 | yes | 0.7567 | 1.0, 0.8, 1.0 | 600 |
| DeepSeek V4 Pro | 5 of 6, missed rotation-blocked | 1 of 1 | not run | no | 0.0387 | not run | 97 |
| GLM 5.3 | not run | not run | not run | not run | not run | not run | not run |

GLM 5.3 Flash and Luna both miss the same sentence in pass b only, `tidewater-subprocessor-gap`
of `subprocessor_register.pdf.md`, which both quote in pass a; the raw pass b replies never
contain it. That is the spread of 20 on `northwind` the gate row carries, and the gate traces
it. DeepSeek Pro's probe miss is a reply of `{}` and then one that is not JSON on DR-074.
GLM 5.3 was not run: its probe in the first run of the day lost two of seven documents to the
6000 output token cap with reasoning on, and its two passes would cost about $3 to fail the same
way. The rerun cost $0.98; phase 2 has spent $1.51 of its $8.

## 6. Money

`LEDGER.md` is the running total: one line per gateway call batch, with sample, phase, model,
tokens in and out, dollars from the table above, and the balance left of $50. Written by the
code that makes the call, never by hand. No call runs before its input token count is known
and its price is printed. A pair judge (any model call over two documents to decide whether
they are about the same thing) is not in this plan and needs the founder's word.

## 7. Reporting to the founder

One message per phase, and one per day while a phase is open. It carries three numbers and one
decision: score, dollars, spread, and the one thing recommended next with the number behind it.
No sub-metric, no option list. If the message cannot name the score, nothing else in it counts.

## 8. What is deliberately not built

- No canonical types, schemas or queries before the map exists. The dossier's checks are
  written over what the map found.
- No pairwise judging. Names are grouped by identifier; where that fails in phase 6, the fix is
  priced and put to the founder.
- No majority voting over model output. One read, verified, pinned.
- No fixing one check while the report does not score. The only unit of work is a phase, and
  the only test is the key.
- No review lanes, builder and reviewer and verifier roles, evidence packets, or fix rounds. One
  reader per pull request. A pull request is a phase.
- No specification files. The tests are the specification. Docstrings say what a function does
  in the present tense and cite nothing.

## 9. Repository layout

```
PLAN.md          this file
RULES.md         one page: the gates, and the two rules that stop the loop
LEDGER.md        dollars, written by code
CLAUDE.md        what a session in this folder must know
samples/         the four samples, their keys, their briefs
reference/       the winner's trail, the transcript, the first build's register, the RLM skill
src/rlm/         the tool; one module per stage
tests/           one test file per phase, parametrised over the three samples
runs/            artefacts, never committed
```

## 10. Decisions the founder has made, and two he has not

Made: $50 ceiling; five models; no Gemini; three-sample gate; phase order; samples 1 to 4;
fresh repository, no lanes.

Open, with this plan's proposal:

1. The phase 5 bar on sample 1. Proposed: 85.
2. Whether phase 6's knobs come from a generator we write (variants of sample 1 with keys by
   construction) or from more open samples. Proposed: the generator, because a knob is a
   controlled change and an open sample is not; open samples stay as the transfer test.
