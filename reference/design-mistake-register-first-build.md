# Design mistake register: RLM-Challenge, 2026-08-21 to 2026-09-05

Purpose: the complete list of design and process mistakes made in this project, in one grid,
so a rebuild does not repeat any of them. Written by the model that made them. Each row has
what was done, what the concept required, the evidence, what it cost, and the rule for the
rebuild. Numbers are from the repository, the run directories and GitHub.

**Audited 2026-09-05, same day, against git, GitHub, the run directories and the sealed clone.**
The first draft of this file got its own dates and counts wrong (it said eleven days and 60
pull requests; git says sixteen days from the first commit on 2026-08-21, and GitHub says 122
pull requests) and misread the one piece of evidence its root rule rests on, the winner's
trail. Rows corrected by the audit say so in place. Rows the audit added are 1.6, 2.9, 4.4 to
4.6, 5.6 to 5.8 and 6.7 to 6.8, and the rebuild paragraph in section 8 is rewritten. Section 9
lists the numbers in this file that no artefact backs, so nothing rests on them until one does.

Read the first section first. It is the root of most of the rest.

## 0. The root mistake: the map was made up, not read off the document

| | |
|---|---|
| **What was done** | Seven query shapes, five canonical types and a typing schema were designed from the PRD and from general knowledge of data rooms before anyone read this room. Then every section of every document was typed blind against them. |
| **What the concept required** | The map comes from the document. The room hands it over on page one: the index (100 titles, owners, folders, dates), the buyer's own Q&A log, the in-room brief, the cross-references between documents, the words DRAFT, Final, Redacted, Privileged in titles. Read the map, decide what this room is about, then read what the map points to, then extract and check with purpose. |
| **Evidence** | The winning 98.5 run chose 25 documents at step 6 of 9 in its trail, and the audit below (row 0a) says how. A corpus-only selection was tried on 2026-09-05 and the first draft of this row reported "38 documents holding 21 of those 25 and 11 of the answer key's 14 required documents" from a script that was never saved; that figure is unbacked (section 9). Reproduced from `runs/report-7/room.txt` the same day with two of the three rules, identifiers recurring across folders and trouble words in titles: 11 of the 14 required documents at 25, 38 or 50 documents selected, and the same three missed every time, DR-048 (user metrics), DR-050 (VistaMail KPIs) and DR-096 (synergy model). Those three carry rubric criteria 5 and 6 and half of the answer key's price bridge. Nothing in sixteen days used the index, the Q&A or the titles. |
| **Cost** | The whole pipeline design, sixteen days, $20.58. |
| **Rule for the rebuild** | The map is built from the room before anything else and shown to the founder as a list of documents and the identifiers that link them. No type, schema or query exists until that list does. **Corrected by the audit:** the map is a selection step, not a reading gate. A cheap pass over every document comes first, as row 0a's trail shows; the map chooses what the expensive call reads, and it is graded against the 14 required ids before anything is built on it, because the corpus-only version misses three of them. |

## 0a. The second root mistake: the 98.5 answer was in the folder and was never studied

| | |
|---|---|
| **What was done** | The winning run, its report, its intermediate files (per-document notes, incident synthesis, lesser issues) and its nine-step replayable trail sat in the sealed clone from day one. The firewall was read as "never look", and the project designed its own method from scratch and from the internet. |
| **What the concept required** | The task was to challenge that run. The first act is to read how it won: which steps needed a model, which did not, and where its cost is. Then do the model-free steps mechanically and keep the model for the one step that needs it. |
| **Evidence** | Its trail, read step by step on 2026-09-05 from `data_room_rlm_sonnet/.claude/rlm_runs/*/steps`: steps 1 to 3 split `corpus.txt` into 100 documents (mechanical, 43 seconds); step 4 sends every one of the 100 to the Sonnet leaf with one prompt asking for red flags, figures, cross-references and a smell test (542 seconds, 581k characters of notes); step 5 saves the notes; **step 6 is a hard-coded list of 25 document ids typed by the orchestrator after reading those notes, with no selection code at all**; step 7 is one call over the 25 full texts (101k characters in, 39k out); step 8 is one call over the notes of the other 75 (445k characters in, 27k out), told to flag anything that connects back to the incident; step 9 writes. 32 minutes. The three documents the corpus-only map misses, DR-048, DR-050 and DR-096, are not in the 25 either; the winner reached them through step 8. The first draft of this row said step 6 "picks the 25 documents that matter (the map)", which is the same misreading as row 0 in a different sentence: the map came out of a model that had already read everything. |
| **Cost** | Everything the map mistake cost, because the winner's trail would have shown the shape on day one. And one more day: the first draft of this file, written from a twenty-minute reading of the trail, put a rule in row 0 ("no model reads a document the map did not select") that forbids the step the winner's score rests on. |
| **Rule for the rebuild** | Before designing anything, read the winner's trail end to end and write down, per step: model or mechanical, cost, what it decided, and what each step's input and output actually were, from the step files, not from the run's summary. The rebuild replaces steps one at a time and grades after each. The firewall protects the answer key from the pipeline's rules, not from the designer's eyes on the method. |

## 1. Strategy and thesis

| # | Mistake | What was done | What the concept required | Evidence | Cost | Rule for the rebuild |
|---|---|---|---|---|---|---|
| 1.1 | Built to a thesis, never to the deliverable | Sixteen days of pipeline stages measured by specs and byte-identity; Stage C (the report) planned on day fifteen, never started | The deliverable is a graded report. Every stage earns its place by moving the score | First report produced 2026-09-05 by hand from artefacts already on disk | All of it | A report exists on day two, by any means. It is graded. Every later change is justified by the score it moves |
| 1.2 | Rebuilt the RLM in disguise | One frontier call per section (A4, 170 calls a pass) and one per entity pair (A5, thousands a run) | The challenge to the RLM is to read less, on purpose, with a map, and to check mechanically | $17.00 of $20.58 spend is A5 judging | Money, days, and the thesis itself | No model reads a section it was not sent to by the map. No model judges a pair a mechanical rule could decide |
| 1.3 | Fixed the seven query shapes before reading the room | The type table in PRD Section 5 was written on day one, 2026-08-21, and the Q1 to Q7 field contract merged on day three, 2026-08-23 (PR #31), before any document had been parsed; then the room was run and five of seven were empty. The first draft of this row dated the queries 2026-08-29, six days late | The shapes come from what the map says this room is about; general shapes (dates, money, versions, deadlines) are checks, not the story | 2026-08-31 room run: Q1, Q2, Q4, Q5, Q6 found nothing; five days of widening followed | Five days, ~$12 | Query shapes are derived after the map is read, per room, and the generic ones are kept as checks |
| 1.4 | Determinism as the organising principle | Byte-identity across runs made the goal of every stage; specs, tests, three review rounds on a merge command argued about it | Determinism belongs to the checks and the report assembly. The reading is a model and moves; aggregate it and move on | `type merge`: 45 tests, three review rounds, two builder rounds, one day, for a 20-line rule | One day plus the mindset | Determinism is required of checks and rendering only. Never spend a day making a model's output reproducible |
| 1.5 | Entity resolution by LLM judge after the PRD named it the wall | A5 judged party, system, incident, liability and claim pairs with a frontier model | In a synthetic room with consistent names, party and system grouping is string matching; incident and claim linking follows the map (codenames, ticket numbers) | Run 7: party 1986 of 1986 and system 219 of 219 pairs mechanical; claim judge 6,363 pairs, $1.28; union would have been 147,884 pairs | Most of the spend | Group by identifiers the room uses (codenames, ticket ids, object names). A judge only where two identifiers must be equated and the map does not say so |
| 1.6 | The project's own spike diagnosed the root on day seven and was overridden | `docs/a5-resolution-spike.md`, 2026-08-27, read the two-folder prototype as "two of its three legs do not hold": the candidate generator "is a way of paying a model to read most of the room pairwise", string similarity proposed nothing, and two runs over the same 893 pairs disagreed on a fifth of them even at temperature 0. Founder decision #59 shipped one narrowing, the boilerplate drop, and A5 was built as a feature anyway | A spike that says the mechanism should not be built as specified is a reason to change the mechanism, not to narrow it by a third and proceed | The spike's own go-or-no-go section, quoted above; nine more days and about $17 of A5 judging followed it | Most of the spend, again, and the reproducibility criterion that had to be redefined twice to survive | A spike's verdict is binding until a measured counter-argument exists. Building on after a no-go is a founder decision recorded as such, with the number that changed his mind |

## 2. Stage A (parse, type, resolve)

| # | Mistake | What was done | What the concept required | Evidence | Cost | Rule for the rebuild |
|---|---|---|---|---|---|---|
| 2.1 | Typed every section blind | `type candidates` proposed every section with a money or date; `type nodes` sent each to the model | Only sections the map points to need reading; the rest need mechanical extraction at most | 170 calls a pass over 282 sections, three passes today for $0.62 | $0.20 a pass, every iteration | Send a model only what the map selected |
| 2.2 | Rigid schemas that miss the row that matters | The Contingency schema took five component ranges from the counsel memo and skipped the "indicative aggregate" row one line below | A reader sees the total; a schema sees fields | DR-088#p1: $240m to $465m present as an Amount mention, absent from every Contingency node in all passes | The headline number missing from the report | A model that reads a section returns the section's own conclusion, not fields; the fields are checked against the text afterwards |
| 2.3 | Node identity that folds in array position | `node_id` for four types included the entry's ordinal, so reordering changed ids and broke reuse | Identity is content | Run 7 reuse: 23 of 6,363 claim pairs recognised | $2.15 run instead of cents | Ids are content hashes, never positional |
| 2.4 | Majority vote over verbatim claim text | Attestation kept only when a majority of passes produced the same wording | Each pass extracts a different subset of claims; wording is not identity, and voting on it halves recall | 272/274/294 per pass, 155 kept; loosening the key did not recover them | Q6 down from 125 rows to 6 | Do not aggregate model reads by vote. Read once on purpose, then check |
| 2.5 | Mention extraction that calls people and headers "systems" | A3 system mentions included "Maya Hart", "Classification Strictly Confidential", "Project Atlas" | A system is an identifier the room uses (VPAuth, legacy_uap, Kestrel) | Retrieval on system mentions returned 446 excerpts of furniture; on label identifiers, 202 relevant lines | Scope joins on furniture | Identifiers come from labels and codenames; furniture is a stop list built from the room's own header lines |
| 2.6 | A period label read as an as-of date | "Q4 2025" in a model cell became the model's date on 3 of 19 cells, the index date on the other 16 | A model is dated by its document; a quarter label is what it is about | Q5: 4 refusals on precision overlap, same sheet, two dates | Refusal noise, split findings | Document date is the model date unless a day-precision as-of is stated |
| 2.7 | Index-owner names as party scope | Assumption scope for the peg model was the index owner "Victor Osei" | Scope is what the section is about, not who filed it | DR-027 never joined to any incident | Second blind model missed | Owner and classification fields are furniture, never scope |
| 2.8 | Three passes to fight variance instead of reading once well | `type merge` over three A4 passes | Variance in what a model extracts is not fixed by voting; it is fixed by asking for the section's conclusion and checking it | Label 41/16/22 across passes; majority kept 19 | $0.62 and a day | One read per selected section, then mechanical checks; if the read fails a check, re-ask that section |
| 2.9 | The buyer's own Q&A log was used only as a counterexample | DR-004, the diligence Q&A log, appears in six source files, every one a docstring warning that the tax matter it records must not join the breach cluster. No stage reads the buyer's questions to decide what to retrieve | The Q&A log is the buyer's own list of what it already suspects, in the room, on page one; the winner's step 4 prompt asks every document for cross-references and the report cites Q-007's evasive answer as evidence | `grep DR-004 src/` on 2026-09-05: six hits, all in docstrings of `contingency.py`, `edge.py`, `cluster.py` | The seller's evasion, a rubric criterion 3 item, absent from the pipeline's output | The index, the Q&A log and the brief are inputs to the map, read before any other document |

## 3. Stage B (queries)

| # | Mistake | What was done | What the concept required | Evidence | Cost | Rule for the rebuild |
|---|---|---|---|---|---|---|
| 3.1 | One row per cell, per pair, per document instance | Q5 one row per assumption cell; Q1 one row per reserve document; Q3 one row per lost figure | A finding is one matter | Q5: 19 rows for one model; Q1: 9 rows for 5 comparisons; 107 rows for about 12 findings | Unreadable output, hidden for a week | The unit of output is the matter. Group before writing |
| 3.2 | Refusal rows in the findings file | "Could not compare" rows written beside findings | A refusal is a pipeline log line, not a finding | 62 of 107 rows in run 7 | A report generator would print them | Refusals never enter the deliverable path |
| 3.3 | Scope join that cannot reach what it needs | Q5 required a shared system or party cluster between a model and an incident | The map already links the model to the incident (same folder, same period, the Q&A) | DR-027 missed; DR-096 found only via "MAU" and "VistaMail" | Half the finding | Joins use the map's own links first; cluster overlap is a secondary signal |
| 3.4 | The planted-row gate as definition of done | `tests/stage_b/test_planted_findings.py`, 11 checks, "11 of 11" cited in every status | A gate that checks eleven known rows measures recall of known rows, not the report | 11 of 11 held on runs 4 through 7 while the pipeline's own dossier reads near 50 by hand grading (section 9: not yet measured) | False confidence for a week | Done is a graded report. Planted checks are regression tests, never the bar |
| 3.5 | Output read by count, never by eye | Every measurement doc reported rows per query and refusal reasons | Read the rows as the buyer would | `docs/extraction-rerun.md` reports "Q5 26 rows" four times; nobody saw they were one finding | The founder's trust, and money spent on runs described by count | Every measurement message carries the rows themselves, digested by subject |

## 4. Stage C (the report)

| # | Mistake | What was done | What the concept required | Evidence | Cost | Rule for the rebuild |
|---|---|---|---|---|---|---|
| 4.1 | Report deferred until the pipeline was "ready" | PRD revision 2026-08-31: "Stage C is not the next thing to build" | The report is the first thing to build, badly, then improved | No report until 2026-09-05 | Eleven days without a score | Report on day two |
| 4.2 | Report designed as a schema of findings, not a document | Stage C plan: `synthesis.json` with six fields per finding, a validator, arms M0 to M4 | The grader reads prose with citations, a number and a structure | The winning baseline is a 4,400-word narrative with tables | Six issues planned, none needed | The report is a document. Validation checks its citations and numbers against the room |
| 4.3 | Today's writer step read the whole room with a big model | Dispatched an Opus agent over all 100 documents | That is the RLM. The writer reads the dossier and the sections the map selected | The first draft of this row said "stopped by the founder". The artefact says it ran to completion: `runs/report-7/Diligence_Findings_Report.md`, 4,684 words, written 11:41, recommending a $300m reduction in a $200m to $410m range, which is below the rubric's $375m to $525m band. So even the RLM in disguise would lose points on criterion 7 | An hour, and one more unmeasured number in this file | The writer never sees the whole room |
| 4.4 | The in-room brief was the public rubric and was never the output contract | `data_room/README.md` lists five deliverables in order: executive summary with a recommendation, findings ranked by materiality with document ids, quantification of the most material issue with a specific deal action, lesser issues, confidence and open items. PRD line 37 quotes it. No spec, stage or test reads it. `runs/report-7/report.md` opens with a summary list, has no recommendation first, no confidence section, and its sections follow the seven queries rather than the five deliverables | The brief is the deliverable's specification, readable from day one, and the rubric's nine criteria are its five deliverables scored. The winner's report has exactly the brief's five sections | Citation counts in `report.md`: DR-087 (seller reps) 0, DR-004 (Q&A) 0, DR-035 and DR-085 (contracts) 0, DR-048 and DR-050 (metrics) 0, the phrase "45-day" 0 | Read as a grader, the pipeline's own dossier lands near 50 of 100, the rubric's partial band | The report template is the brief's five deliverables, written on day one, and every stage is judged by which of the five it fills |
| 4.5 | Four rubric criteria had no query at all | Q1 to Q7 cover, at most and partially, criteria 1, 2, 4 and 6. Nothing asks whether the seller's representations contradict what management knew (criterion 3), what the customer contracts say (criterion 5), what the deal action should be (criterion 7), or which matters are decoys (criterion 8) | The brief names all four in plain words; a query set derived from it would have had a row for each | The rubric, opened 2026-09-05, against the query table in PRD Section 5 | Up to 40 of 100 points unreachable by any Stage B output, before extraction quality is considered | Every deliverable in the brief has at least one retrieval or check behind it before a query is written for anything else |
| 4.6 | The dossier written today still carries the row-level defects rows 3.1 and 3.5 name | `runs/report-7/report.md` section 3 heads two bullets with the same DR-031 tax sentence paired against two different denials; "Other matters the room raises" lists only litigation-schedule rows, so the tax, open-source and search-concentration decoys the rubric's criterion 8 scores are absent | One matter, one entry; decoys named and ranked below | The file, read on 2026-09-05 | Criterion 8 and part of 9 lost in a document built to fix exactly that | The renderer groups by matter and the decoy section is a check on the whole room's liabilities, not on the anomaly rows |

## 5. Measurement and money

| # | Mistake | What was done | What the concept required | Evidence | Cost | Rule for the rebuild |
|---|---|---|---|---|---|---|
| 5.1 | Room re-run as the unit of iteration | Every rule change verified by re-resolving the room | Verify on the artefacts already on disk; re-run only what a change touches, and only after the deterministic check says it is worth it | Runs graph-3 $3.9, graph-4 $3.9, room-graph $5.8, graph-6 $1.2, graph-7 $2.2 | $17 | No priced run before a free check has said what it will change |
| 5.2 | Recommendation without the downstream number | Union for Attestation recommended off node counts; the pair count was free and not run | Compute every number a recommendation rests on before writing it | 644 attestations, 147,884 pairs, about $40; found by a reviewer, not by me | An issue filed and a builder dispatched on a wrong premise | No recommendation carries a spend without the count behind it |
| 5.3 | Spend estimates from precedent, not from the input | "About $1.25 by run 6's precedent" for run 7 | Estimate from the actual pair count of the actual input | Run 7 cost $2.15 | $0.90 and trust | Estimates come from counting the input |
| 5.4 | Grading deferred behind the firewall | Sealed folder kept closed for sixteen days on principle | Grade early with a bad report; the score steers | First grade attempt 2026-09-05; baselines 98.5, 97, 91; ours unmeasured, near 50 by hand (section 9) | No steering signal for sixteen days | Grade on day two and every few days after; label post hoc honestly |
| 5.5 | Documentation of failure instead of correction | Measurement docs recorded that five queries were empty, that passes disagreed, that reuse missed, each as a finding | A finding that the method is off is a reason to change the method, not a paragraph | `docs/extraction-gaps.md`, `docs/extraction-rerun.md`, `docs/a5-resolution-spike.md` | Days of prose | A measured failure changes the next step or it is not written down |
| 5.6 | The cost thesis was unmeasurable on day one and nobody checked | PRD Section 11's headline criterion was "under 20% of R0 token cost". The source transcript says in its own words "the token counts in this experiment were not recorded reliably", and its claim for the RLM was "13% better at comparable cost", never a saving. The clause was withdrawn on 2026-08-31 as unmeasurable, ten days after it was written | Read the source for the number the thesis compares against before writing the thesis. If there is none, the thesis is different | `rlm_challenge.md`, PRD Section 1 and Section 11's revision note. And the comparison that was available: the winner's own step files put its leaf pass at roughly 97k tokens in and 150k out, and its two syntheses at 136k in and 17k out, on the order of $3 to $5 at Sonnet list; this pipeline spent $20.58 and produced no gradable report | The headline was lost on cost, the axis chosen to win on, before quality was measured | Every success criterion is checked against an existing number before it is written, and the baseline's own cost is estimated from its artefacts on day one |
| 5.7 | The steering numbers in this file's first draft were never measured | "Ours about 65" has no `GRADE.md` behind it; the grader brief asked for one and none was written. "38 documents holding 21 of those 25 and 11 of the 14" came from a script that was not saved. The winner's trail was summarised from twenty minutes of reading and the summary was wrong (row 0a) | A number a decision rests on is produced by a script or a file on disk, or it is labelled an estimate | This file, 2026-09-05, first draft against the audit the same afternoon | The rebuild's first rule was written on a misreading | Rows 5.2 and 5.3 apply to this register too. Section 9 lists what is still unbacked |
| 5.8 | Decision points were written down and never revisited | `docs/path-forward.md`, 2026-08-31, named the stop criterion: if, after the first two gaps close, "the queries still return almost nothing, then the honest reading is that this corpus's anomalies are not the shape the seven queries look for". Nineteen slices later the queries returned 107 rows for about twelve findings, and the criterion was never evaluated. PRD Section 10's phasing put the report in week 2 and grading in week 4; neither date was checked against | A recorded decision point is a date on which the decision is made, with the number it was waiting for | The file's "What would make stopping the right call" section, and nothing after it referring back | Five days of widening that the criterion existed to bound | Every written decision point gets a date and an owner, and the status document reports it as met, missed or withdrawn |

## 6. Process

| # | Mistake | What was done | What the concept required | Evidence | Cost | Rule for the rebuild |
|---|---|---|---|---|---|---|
| 6.1 | Review machinery ten times the change | Builder, reviewer, verifier, evidence packets, fix rounds on every PR | Review proportional to risk to the deliverable | 122 PRs in 16 days (117 merged, 4 closed unmerged); PR #177 11.7 hours, 20 commits and 13 comment rounds; a 20-line merge took 3 review rounds. The first draft of this row said 60 PRs in 11 days | Hours per change | One reader on a change that touches the report; none on plumbing |
| 6.2 | One PR per 20 lines | Every slice a branch, worktree, PR, CI run, evidence commit | Batch work into what a reader can judge | 122 PRs, median lifetime 18 minutes from open to merge, 143,750 lines added | CI minutes, context, hours | A PR is a working increment of the report |
| 6.3 | Specs as design history | 2,400-line spec files, superseded passages kept with pointers, docstrings citing fix rounds | A spec states the rule; history lives in git | `specs/stage-a4-canonical.md` | Every change re-read paragraphs | Specs state rules in the present tense, one page each |
| 6.4 | Handbook grown from review findings | Each review defect became a "known pitfall", each pitfall more review | Fix the class in code once | CLAUDE.md pitfalls section | More process per slice | A pitfall becomes a test or a lint rule, never a paragraph |
| 6.5 | Literal instruction-following | "One row per Assumption" obeyed for a week; "Stage C not next" obeyed; "reviewer on every PR" obeyed | Ask what the sentence is for | This whole register | This whole register | Every instruction is read for its purpose. When the letter and the purpose disagree, say so and follow the purpose |
| 6.6 | Founder's questions answered with options instead of answers | Three-option lists on Attestation, on Q5, on next steps | The founder asked for a working product; the work was mine to do | This session's transcript | The founder's patience | One recommendation with the number behind it, then do it |
| 6.7 | The process ran at a scale nothing measured | 682 subagent transcripts (556 MB) against 81 main sessions (120 MB); 1,756 test functions, 51,256 lines of tests over 26,683 of source; 15,786 lines of spec and doc prose; 75 issues; commits between midnight and 06:00 on 11 of the 15 working days | The size of the machinery is a cost like any other, reported beside the spend | Session directory and `wc` over the tree, 2026-09-05 | Sixteen days of agent time for a report that would score in the partial band | Agent-hours and review rounds are counted per slice and reported with the dollars |
| 6.8 | This register condemns work the repository still carries, and says nothing about disposing of it | PR #197 (Attestation by union) awaits founder approval while row 5.2 calls its premise wrong; issues #190 to #195 are open while row 4.2 says none were needed; branch `feat/stage-c/report` holds two unmerged commits and PR #198 was closed without them; the firewall change to `.claude/settings.json` is uncommitted | A finding that work was a mistake carries the action on that work: close, revert, or keep with a reason | `gh pr list`, `gh issue list`, `git status`, 2026-09-05 | Open work that the next session will pick up as if it were wanted | Every row that names a PR, issue or branch names what happens to it |

## 7. What was right and is worth keeping

- The parse: every document to sections with anchors, mechanical, free (`records.jsonl`,
  `documents.jsonl`).
- Mention extraction for dates, money, parties: mechanical, free, mostly correct.
- Document genre from titles: free, correct enough.
- Mechanical checks: a claim cites a section that says it; a number appears in its source; a
  certainty word is the source's own. These are the checks on a reader.
- The report skeleton and the checked narrative from today: the shape of the deliverable.
- The rubric and answer key, now open: grade on day one of the rebuild.

## 8. The rebuild in one paragraph, following the concept

**Rewritten by the audit.** The first version ended "No model reads a document the map did not
select", which row 0a's trail shows is not how the winner won.

Read the winner's trail first, from its step files, and mark each step model or mechanical with
its input and output sizes. Take the brief's five deliverables as the report template on day one
and the rubric as its test. Run one cheap pass over every document, mechanical where it can be
(index row, dates, money, names, versions, identifiers, series, trouble words) and one small
model call per document where it cannot, asking for red flags, figures, cross-references and
what looks concealed; that pass is the cost floor and it is a few dollars. Build the map from
the index, the brief, the Q&A log and those notes: the cluster of documents the cross-references
tie together, and the metrics and model documents the incident's consequences land in, graded
against the 14 required ids before anything is built on it. Make one synthesis call over the
cluster's full text asking for the timeline, what happened, how each function framed it, who
knew when, and every figure with its source; make one over the notes of the rest, told to
connect anything back to the incident and to rank the lesser issues. Assemble the dossier by
matter. Write the report to the five deliverables, every sentence cited, and check every
citation, number and certainty word against the source mechanically. Grade on day one and after
every change; never re-run the room to test an idea, test it on what is on disk. The expensive
model reads only what the map selected; the cheap pass reads everything once.

## 9. Numbers in this file no artefact backs

Listed so nothing rests on them until an artefact exists.

- "Ours about 65" (row 5.4). No `GRADE.md` was written for any report. The pipeline's own
  dossier reads near 50 by the audit's hand grading and the agent-written report higher, but
  neither is a measurement. Producing `runs/report-7/GRADE.md` for both is the first task of
  any next step.
- "38 documents holding 21 of those 25 and 11 of the 14" (row 0). The script was not saved.
  The reproduced figure, 11 of 14 with DR-048, DR-050 and DR-096 missed, came from a script run
  against `runs/report-7/room.txt` and not saved either; the rule and the three missed ids are
  what stand, the document count does not.
- "$17.00 of $20.58 is A5 judging" (row 1.2). The token ledgers carry tokens and no dollars; the
  manifests of the graph runs sum to about $17 and the total came from the OpenRouter balance.
  Plausible, not reproduced from the tree.
- The winner's token counts in row 5.6 are characters divided by four from its saved files, not
  a ledger. The order of magnitude is what the row rests on.
