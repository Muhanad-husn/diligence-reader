# RLM: the rebuild plan

Written 2026-09-05. This is the plan of record. It replaces everything in the first build; that
build's lessons are not repeated here except where they became a rule.

## 1. What is being built

A tool that does what the recursive language model (RLM) did on the Project Atlas data room,
with the same shape and three properties the RLM lacks: reproducible in the middle, cheap, and
runnable on other document sets. The RLM's own winning run is the specification of the shape;
this plan replaces its improvised parts with fixed ones and keeps the model where the model is
the only thing that works.

**The final deliverable of the method** is one document: a findings report in the five sections
the task brief asks for (recommendation with a number, findings ranked by materiality with
citations, the most material issue quantified with a specific deal action, lesser issues, open
items), produced from raw documents with no human step, with three numbers printed beside it:
its score against the sample's key, the dollars it cost, and the spread between two runs.

Phase 8 turns the tool into a product a user installs and runs on their own machine, from one
command or a web page served on that machine. The seven stages run unchanged, on the user's own
OpenRouter key. Section 4c describes it.

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
| 3 Map | `runs/<sample>/map.json` | Every key document of the planted matter in its cluster. Deterministic over pinned notes. The decoy count in the cluster is printed, not gated: moved to phase 4 on 2026-09-07, see the phase 4 row. Rescored under phase 5 on 2026-09-07 (slice 04, PR #88): a named-link set replaces the score cut, sample 1's set fell from 68 documents to 44, rubric 89 and 87, spread 2 | none | $0 |
| 4 Dossier | `runs/<sample>/dossier.md` | Every planted fact present with the right anchor and number. No decoy in the matter's document set, and every planted document ranked above every decoy. Read by the founder once as a reader. Byte-identical | none | $0 |
| 5 Report | `runs/<sample>/report.md`, `verify.json`, `grade.json` | Verifier passes. Score at or above the bar. Two writes, spread printed. Bake-off over the five models. A room holding a second matter writes it under a heading of its own, above the lesser issues, since #121 | bake-off | $9, $8 plus $1 borrowed from the reserve on 2026-09-09 to rewrite the three gate samples' reports, lost with #119's worktree; the reason is at the head of `LEDGER.md` |
| 6 Widen | same artefacts under `runs/<sample>-<knob>/` | Phases 1 to 5 hold when a knob is turned on the fixture: names spelled inconsistently, the matter named nowhere and linked only by dates and numbers, a second matter, twice the documents. Each knob is one generated variant of sample 1 with its own key. A failure names the phase that dropped the fact. Closed 2026-09-09: `control` holds; `names` was dropped by phase 3, whose map linked documents by the surface of a name, fixed by #113; `unnamed`, `second` and `twice` were dropped by phase 3, whose map read the room from one seed and returned one matter, fixed by #115. Five known misses stand, each a knob taking away what tied a document to the matter | as chosen in 2 and 5 | $15 |
| 7 Compare | `runs/yahoo/` | Our tool once on sample 4, an open corpus with no planted facts, against the public record | as chosen | $4 |
| 8 Product | `runs/<sample>/` written by a run started from the web interface, with `report.docx`, `report.pdf`, `evidence.csv` beside `report.md` | A run started from the web interface on samples 1, 2 and 3 gives the same planted-fact recall as the command line, 100 / 100 / 100, and every planted fact reads out of the docx, the PDF and the CSV. Spread over two runs printed | as chosen in 2 and 5 | $9, $3 from the reserve on 2026-10-04 and $6 on 2026-10-05 for #160 |

Reserve: $5 of the $50, $15 less the $1 phase 5 borrowed on 2026-09-09, the $3 phase 8
borrowed on 2026-10-04 and the $6 phase 8 borrowed on 2026-10-05 for #160. Nothing borrows from
it without the reason written in `LEDGER.md` first.

**The bar for phase 5.** Planted-fact recall 100% (the key is by construction). Rubric score: 85
on sample 1, the rubric's own floor for "excellent", proposed here and set by the founder.
Samples 2 and 3 have no rubric; their bar is recall and the verifier.

**Kill line.** If phase 5 on sample 1 is under 70 after $25 of the $50 is spent, the method is
wrong, not a phase. Stop, write what the phase tests showed, and redesign before another dollar.

## 4a. Status

One row per phase, written by the phase's closing pull request. Score is planted-fact recall
on the three gate samples and, from phase 5, the rubric score on sample 1. The phase 6 row reads
its five knobs in one order, `control`, `names`, `unnamed`, `second`, `twice`, and its recall and
rubric are on sample 1's variants; its dollars are every phase 6 row of `LEDGER.md`.

| Phase | Milestone | State | Score | Dollars | Spread | Closed |
|---|---|---|---|---|---|---|
| 0 Fixtures | Phase 0 | done | 100 / 100 / 100 | 0 | 0 | 2026-09-05 |
| 1 Ingest | Phase 1 | done | 100 / 100 / 100 | 0 | 0 | 2026-09-06 |
| 2 Notes | Phase 2 | done | 100 / 100 / 100 | 1.80 | 0 / 20 / 0 | 2026-09-09 |
| 3 Map | Phase 3 | done | 100 / 100 / 100 | 0 | 0 / 0 / 0 | 2026-09-07 |
| 4 Dossier | Phase 4 | done | 100 / 100 / 100 | 0 | 0 / 0 / 0 | 2026-09-07 |
| 5 Report | Phase 5 | done | 100 / 100 / 100, rubric 100 | 8.28 | 0 / 0 / 0 | 2026-09-08 |
| 6 Widen | Phase 6 | done | recall 100 / 100 / 97.9 / 98.5 / 98.1, rubric 100 / 94 / 98 / 99 / 100 | 7.78 | 0 / 6 / 2 / 1 / 1 | 2026-09-09 |
| 7 Compare | Phase 7 | done | sample 4 recall 86.4 | 0.26 | one run | 2026-09-09 |
| 8 Product | Phase 8 | done | 100 / 87.5 / 100 | 2.51 | 1.9 / 6.3 / 0 | 2026-10-04 |
| 8 #160 new room | Phase 8 | done | sensar 74, mri 81, avid 84 (Claude) | 8.30 | one run | 2026-10-06 |

Phase 5's row was restated on 2026-09-09 by the phase 6 gate, which rewrote the three gate
samples' reports after PR #119 changed the map under them: rubric 90 to 100, spread 4 / 0 / 0
to 0 / 0 / 0, and dollars 1.78 to every phase 5 row of `LEDGER.md`. The date it closed stands.

Phase 8's score is planted-fact recall on the first of two runs per sample, each started from the web
page in the Docker image. Northwind's 87.5 carries two known misses, both the map's on fresh notes:
`tidewater-subprocessor-gap`, named since #144, and `captable-coc-confirmation`, found by the gate,
where the map seeds at the Tidewater DPA and leaves the cap table out; the two rules tried that keep it
moved six to eight pinned atlas maps. Its second run read 93.75, equal to the command line. Atlas's
second run missed `price-reduction`, a figure the writer computes. The gate also left GMICloud out of
the routing, after it twice spent a note's whole budget on reasoning and returned nothing, which cost a
first atlas run one fact; its $0.40 is in the dollars.

Phase 7's score is recall on sample 4 alone: its key has no rubric. Sample 4 ran once, so its
spread column reads one run.

## 4b. Sample 4

Our tool once on sample 4, the open corpus, against the public record. Sample 4 has no rubric,
so its score is recall, 19 of 22 facts; the three misses are phase 4's, named in PR #129.
Its seconds are blank: the notes ran in two passes and the run kept no one wall time.
Restated 2026-09-09 with #131: phase 2 notes a document over 20,000 characters in pieces, and
the chain reran from the notes on; the rerun cost $0.29, booked to phase 2. The row read
recall 72.7, 16 of 22, before it.

**Sample 4 stops at 86.4, founder's decision 2026-09-09.** The three facts the report does not
carry are the commission file number and the employer identification number on the 10-K cover
page, and the fifty percent share in the reorganization amendment. The first two are lookup
identifiers; no reader of the report acts on them. The third is the liability split, which the
report states from the stock purchase agreement and the press release, so the fact is in the
answer by another document. Every fact that bears on the answer is in the report. Closing the
three would take a phase 4 issue and a rerun of samples 1 to 4, about $1, to move the number
and change no conclusion, so no issue is filed for them and the row stands.

| Sample | Recall | Seconds | Dollars |
|---|---|---|---|
| 4 `yahoo` | 86.4 | | 0.26 |

**How a phase becomes issues.** The founder types `/aeo:sprint-plan` for the phase. The plan is
sliced into three to six issues, each a vertical piece that leaves an artefact a test checks
against the key on at least one sample, in this order: the artefact on sample 1, the same
artefact on samples 2 and 3, then the closing issue `Phase N gate` that runs all phase tests on
all three samples and fills the row above. Each issue is one session and one pull request. No
issue of the next phase exists before the gate issue closes.

## 4c. Phase 8, the product

The same seven stages, unchanged in `src/rlm/`, run from one command and from a web page served
on the user's own machine. The user's documents never leave the machine except as the model
calls the tool already makes, through the user's own OpenRouter key. No accounts, no login, no
database, no payments: each run is a folder under `runs/`, and the folder is the state.

| Layer | What it is |
|---|---|
| Engine | `src/rlm/`, the seven stages, unchanged |
| Command | `diligence-reader run <room>`, replacing the five `python -m` steps, with a price estimate shown before the first model call and confirmed by the user, and a retry that resumes from the stage that stopped, since every stage already writes its own artefact |
| Runner | a run takes minutes and does not fit in one web request: a background process on the machine, or a Kubernetes Job, one interface and two implementations |
| API | FastAPI: start a run, stream its progress, fetch the report, export it |
| Progress stream | AG-UI events over server-sent events: run started, step started and finished per stage, state updates for documents noted and dollars spent, run error with its code. No chat and no CopilotKit |
| Web page | upload a room, connect the OpenRouter key, see the estimate and confirm it, watch progress, read the report, export, see an error card |
| Export | Markdown as written, Word and PDF built from the same Markdown, Word with pandoc and PDF with pandoc and Typst, and the Evidence section alone as CSV, saved so Excel opens it cleanly. No Excel file: the report body is prose, and the Evidence section is one flat list, about 1,870 rows on sample 1, that a CSV carries whole |
| Packaging | one Docker image for `docker run`, `pipx install diligence-reader` for the command alone, a build on every merge that publishes the image to GitHub's container registry, and a Helm chart for a firm that runs it on its own Kubernetes cluster |

Kubernetes: the chart is tested on kind, a Kubernetes cluster on one machine, at no cost. No
managed cluster is paid for. Each run is one Kubernetes Job.

The key: the user connects with OpenRouter's sign-in, which issues a key the user can cap and
revoke, or pastes one. The key stays in the browser, goes with each run, is held in the runner's
memory, and is never logged or written to disk.

Money: a user's run spends the user's credits, and the tool sets no cap on them. The limit is the
one the user puts on the key at OpenRouter. The tool shows the estimate before the first model
call and the dollars spent after the run. The repository's `LEDGER.md`, the phase caps and the
$50 ceiling apply to this build's own calls only, which are the gate runs on the three samples; a
user's run neither writes `LEDGER.md` nor is refused by those caps.

When a run fails: every failure carries a code from a short list, each with its fix on the error
card: a refused key, no credits left with a link to top up, rate limited, a model that returned
nothing, a file that could not be read, the verifier failing twice. The card offers a retry from
the stage that stopped. Anything not on the list gets a "Report a problem" button that opens a
GitHub issue filled in with the run id, the version, the stage, the error code and the dollars
spent, never document text and never the key, labelled `user-report`. No server and no GitHub
token are needed for it.

A citation in the report viewer opens the source page with the cited line marked.

The gate: the closing issue `Phase 8 gate` runs the three gate samples through the Docker image
from the web interface, checks recall against the command line's 100 / 100 / 100 and every
planted fact out of the three export files, and writes the row in 4a.

### 4d. Issue #160, a new room

Why: the first blind room (Avid, 100 contracts from the Stanford Material Contracts Corpus)
held 22 of 25 key facts in its notes but the report carried 7. The map, set and dossier rules
that choose what the writer reads were tuned on the three samples.

Two sealed rooms were picked by metadata with a fixed seed: MRI Interventions (mri) and Sensar
Corp (sensar), each a company's earliest 100 contracts. A separate agent built their keys
(26 and 27 facts) and stored them outside the repository.

Tried and failed: ranking the room against a fixed acquisition checklist (src/rlm/checklists/
acquisition.md, 34 questions) with a model or with Jev. Neither held the samples (atlas 7.55
and 20.75). The open-model tree writer (GLM 5.3 Flash picks findings by group, GLM 5.3 writes,
frozen at tag 160-frozen) held the samples at 100 / 100 / 100 but failed both sealed rooms:
mri 4 of 26 and sensar 0 of 27 in the written analysis.

What works: the same tree with Sonnet 5.5 through Claude Code for the group step and the
writer (`--write both-tree-first --middle-model claude-code/claude-sonnet-5-5 --writer-model
claude-code/claude-sonnet-5-5`, frozen at tag 160-claude-frozen). Notes stay on GLM 5.3 Flash.

| Room | Before | Open models | Claude |
|---|---|---|---|
| Avid (practice) | 2/25 | 11/25 | 21/25 |
| MRI (practice for Claude) | not run | 4/26 | 21/26 |
| Sensar (sealed) | not run | 0/27 | 20/27 (74%) |
| Samples | 100 / 87.5 / 100 | 100 / 100 / 100 | 100 / 100 / 100 |

Scores count key facts in the written analysis, before the Evidence section.

Caveat: only sensar was sealed for the Claude version; mri was used while building it, after
the open-model run had read its score. The issue's rule asked for two.

Money: the issue spent its 6 dollars from the reserve plus 2.50 more, raised to fit the credits
left on OpenRouter with no top-up; the Sonnet steps ran at 0 dollars on the founder's
subscription. Notes cost about 2.30 to 2.70 per 100-document room on GLM 5.3 Flash.

What follows: the writer keeps its default until the model configuration issue (#161) lands, since the
Docker image has no Claude Code; the founder will open a separate experiment on more general
questions.

## 5. Models

Five candidates, chosen per task by the bake-off tables in phases 2 and 5, never by preference.
Prices reread from the gateway on 2026-10-04, when the weekly model check found GLM 5.3 Flash
doubled, per million tokens, prompt then completion. The table of 2026-09-08, the day of the
phase 5 bake-off, is kept in `PAST_PRICES` in `src/rlm/gateway.py`.

| Model | Id | In | Out |
|---|---|---|---|
| Luna | `openai/gpt-5.6-luna` | 0.200 | 1.200 |
| DeepSeek V4 Flash | `deepseek/deepseek-v4-flash-0731` | 0.0152 | 1.280 |
| DeepSeek V4 Pro | `deepseek/deepseek-v4-pro` | 0.2088 | 0.4176 |
| GLM 5.3 | `z-ai/glm-5.3` | 1.400 | 4.400 |
| GLM 5.3 Flash | `z-ai/glm-5.3-flash` | 0.150 | 0.500 |

No Gemini. No model from outside this table without the founder's word. Prices are reread and
rewritten here the day a bake-off runs, and the day the weekly model check finds a task model's
price moved, since the estimate a user confirms is built from this table. A bake-off's winner
stands at the prices of its day.

What one full note pass on sample 1 cost at the prices of 2026-09-06 (about 90k tokens in, about
60k out
with a tight schema): DeepSeek Flash $0.01, GLM Flash $0.02, Luna $0.09, DeepSeek Pro $0.14,
GLM 5.3 $0.39. A five-model bake-off on sample 1 is under $1. Samples 2 and 3 are under a cent
each on any model. At the prices of 2026-10-04 the same pass costs GLM Flash $0.04, DeepSeek Pro
$0.04, DeepSeek Flash $0.08, Luna $0.09, GLM 5.3 $0.39.

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
way. The rerun cost $0.98; phase 2 had spent $1.51 of its $8, and $1.80 after #131's
sample 4 rerun on 2026-09-09.

**Phase 5 bake-off, run 2026-09-07 and 2026-09-08** (`runs/<sample>/write-bakeoff.json`,
issues #83, #90 and #92). Every model wrote each sample twice from the pinned dossier; the
verifier read each report and returned its failures to the writer once. A row passes when its
pass a reads planted-fact recall 100 with a passing verifier on all three samples and a rubric
at or above 85 on sample 1. Recall and the verifier read pass a then pass b; the rubric is
sample 1 only, pass a, pass b, spread. Dollars are the six passes at the prices above.

| Model | Passes | Dollars | Seconds | Recall atlas | Recall northwind | Recall northstar-dental | Verifier atlas | Verifier northwind | Verifier northstar-dental | Rubric atlas |
|---|---|---|---|---|---|---|---|---|---|---|
| GLM 5.3 Flash | no | 0.0255 | 466 | 98.11 / 100 | 100 / 100 | 100 / 100 | no / no | yes / no | no / no | 92 / 89 / 3 |
| DeepSeek V4 Flash | no | 0.0527 | 2113 | 98.11 / 98.11 | 100 / 100 | 100 / 100 | no / yes | no / no | no / no | 73 / 51 / 22 |
| Luna | no | 0.0860 | 247 | 100 / 100 | 100 / 100 | 100 / 100 | no / no | no / no | no / no | 86 / 76 / 10 |
| DeepSeek V4 Pro | no | 0.3365 | 673 | 98.11 / 98.11 | 100 / 100 | 100 / 100 | no / no | no / no | no / no | 85 / 92 / 7 |
| GLM 5.3 | yes | 0.4538 | 365 | 100 / 100 | 100 / 100 | 100 / 100 | yes / yes | yes / yes | yes / yes | 90 / 94 / 4 |

**Winner: GLM 5.3**, the only passing row, and the default `--model` of `python -m rlm.write`.
Both Flash rows were tried first and both fail the verifier on sample 1 and sample 3; the Pro
tier ran because every Flash failed, as section 5 asks. The pinned reports are the winner's
pass a under `runs/<sample>/` and pass b under `runs/<sample>/b/`, digests in
`tests/phase5-digests.json`. Phase 5 spent $1.78 of its $8: $0.95 on the five-model bake-off,
$0.31 on the two northwind
reruns of 2026-09-08, $0.52 on slices 01 to 04. The repository has spent $3.50 of the $50.

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
- No hosted service, public demo, accounts, database, payments, chat, or Excel export. The
  product runs on the user's machine only, founder's decision 2026-10-04, because a data room
  sits under a confidentiality agreement and its owner does not upload it to a site run by
  someone else.

## 9. Repository layout

```
PLAN.md          this file
RULES.md         one page: the gates, and the two rules that stop the loop
LEDGER.md        dollars, written by code
CLAUDE.md        what a session in this folder must know
samples/         the four samples, their keys, their briefs
src/rlm/         the tool; one module per stage
tests/           one test file per phase, parametrised over the three samples
runs/            artefacts, never committed
app/             the API and the runner
web/             the web page
deploy/          the Dockerfile and the Helm chart
```

## 10. Decisions the founder has made, and one he has not

Made: $50 ceiling; five models; no Gemini; three-sample gate; phase order; samples 1 to 4;
local-only product as phase 8 (2026-10-04); fresh repository, no lanes.

**Decision 2, where phase 6's knobs come from. Made on 2026-09-08 with the phase 6 sprint plan,
as proposed: the generator.** `python -m rlm.widen <knob> samples/atlas samples/atlas-<knob>`
writes a variant of sample 1 whose key holds by construction, and the five variants are
`control`, `names`, `unnamed`, `second` and `twice`. A knob is a controlled change and an open
sample is not, so open samples stay as the transfer test, which is phase 7's sample 4.

Open, with this plan's proposal:

1. The phase 5 bar on sample 1. Proposed: 85.
