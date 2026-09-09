# The RLM Rebuild

*Project report, 10 September 2026*

A recursive language model wrote a strong diligence report on one data room, once, for a
price nobody could state, in a way nobody could repeat. In five days and $18.95 we built a
fixed program that does the same job on that room and three others, scores higher, costs
cents a run, and gives the same answer twice.

| | |
|---|---|
| **100** | Rubric, sample 1, both runs |
| **82 / 84** | RLM skill, same grader |
| **$18.95** | Spent of the $50 ceiling |
| **5 days** | 5 to 9 September 2026 |

## 0. The domain

Due diligence, before an acquisition closes, is a room of documents a buyer's team must read
end to end: contracts, financials, security logs, board minutes, email, spreadsheets, in
whatever format the seller kept them. The material fact is rarely stated once, in one place,
in plain words. It is scattered: a technical finding in one folder, a legal exposure memo in
another, a reserve booked in a third, a forecast that quietly assumes the problem away in a
fourth, each written by a different function under a different name for the same thing. The
task both approaches take on is the same: read the whole room, find the matter that connects
across functions despite the different names, weigh it against what the seller has
disclosed and reserved, and write a findings report a deal team can act on, every claim
traceable back to the page it came from. That is the job. John's RLM and our rebuild are two
different answers to how a language model does it without a human reading all hundred
documents first.

## 1. The challenge

John Adeojo published a synthetic 100-document data room, Project Atlas, with a planted
matter, an answer key and a 100-point rubric, and then ran a recursive language model (RLM)
over it from Claude Code. The RLM is an orchestrating model that writes and runs its own
program at inference time: it reads the room with leaf calls, decides what to read again,
consolidates, and writes. His published run scored 98.5 on his own rubric. It is a real
result and the report it produced is good.

The question we set ourselves was not whether the RLM can do the task. It can. The question
was what the result is worth as a tool, and that turns on three properties the RLM lacks:

- **Reproducible in the middle.** The program is improvised per run. Reading the trail of
  the 98.5 run shows a leaf pass over all 100 documents, then a list of 25 document ids
  typed by the orchestrator from what it read, then two synthesis passes and a write.
  Nothing between the raw files and the report is a fixed function; a second run is a
  different program.
- **Cheap and priced.** The run took 32 minutes and roughly $3 to $5 of leaf tokens on a
  frontier model, with no ledger and no price known before a call was made.
- **Runnable elsewhere.** One run on one room with one key. Nothing showed the method
  transferred to a room with a different shape, a different planted truth, or no planted
  truth at all.

Underneath these sits a fourth point the rubric does not measure: nothing in the RLM
verified a sentence against its source. A report can score 98.5 and still paraphrase, round,
and raise a "probable" to a "confirmed". A buyer's counsel cannot use that.

## 2. How we challenged it

We kept the shape of the winning run and replaced every improvised step with a fixed one,
keeping a model only where a model is the only thing that works. Seven stages, two of them
model calls, the rest code that is byte-identical across runs.

| Stage | Kind | What it does |
|---|---|---|
| Ingest | code | Raw PDF, XLSX, CSV, TXT, EML, MBOX and markdown into sections with anchors, plus an index of dates, amounts, names, identifiers, status words, version pairs and series. |
| Notes | model | One call per document under a fixed JSON schema. Every quote and figure is checked by code against the source; a failed note is re-asked once, then dropped and logged. |
| Map | code | A document graph over shared identifiers, note cross-references, dates and versions. Clusters the matter; consequence links catch a series that breaks at the matter's date and a model dated after it. |
| Dossier | code | Per matter: timeline, every name each function gave it, figures with sources, draft against final, reserve against estimate, deadlines against actions, models blind to it, lesser matters ranked by money. |
| Write | model | One call from the dossier alone. The five-section report the brief asks for; every sentence cites, certainty words copied and never raised. |
| Verify | code | Every citation resolves, every number exists in its source, no certainty word climbed, decoys ranked below the main matter. Failures go back to the writer once. |
| Grade | code + subagent | Planted-fact recall by code; rubric score by a Claude subagent reading the key; spread between two runs. |

The build discipline mattered as much as the design. Four rules did most of the work:

- **The key is the only test.** Every sample carries a machine-readable key. A phase passes
  when its artefact carries every planted fact against that key on samples 1, 2 and 3 with
  no code change between. Nothing is "found" unless a test reads it out of the artefact.
- **One artefact per phase, in order.** Fixtures, ingest, notes, map, dossier, report, widen,
  compare. A fact dropped later is traced to the phase that dropped it and fixed there;
  every later phase reruns.
- **Money is enforced by code.** Before any gateway call the input tokens are counted and
  the price printed. The ledger is written by the code that makes the call. Past a phase cap
  or the $50 total, the call refuses.
- **Cheapest model that passes.** Five candidates, a bake-off per model-calling phase, a
  Flash tier tried first, a Pro tier only when every Flash fails. No preference, only the
  table.

### What happened, phase by phase

| Phase | Artefact | What it took | $ |
|---|---|---|---|
| 0 Fixtures | One key shape for all samples; a grader calibrated so a perfect report scores 100 and a wrong one under 40 | Five issues, one day | 0 |
| 1 Ingest | Sections and index, byte-identical over two runs, seven formats | Six fixes on scale, headers, cell anchors and mail headers, all caught by the key | 0 |
| 2 Notes | One verified note per document; five-model bake-off | GLM 5.3 Flash won at $0.18 for six passes. DeepSeek reasoning eating the output cap, Wafer provider returning null, long documents split at 20,000 characters | 1.80 |
| 3 Map | Deterministic document graph and cluster | A corpus-only map reached 91 of 100 documents; weighting by rarity and by what the notes flagged brought the matter's set to fourteen. Consequence links reached the two documents the earlier attempt always missed | 0 |
| 4 Dossier | Every planted fact with anchor and number; no decoy in the set | Decoy separation moved here from the map: the Granite contract shares its template with the hero contract and only the clause text tells them apart | 0 |
| 5 Report | Written, verified, graded, twice | Both Flash writers failed the verifier; GLM 5.3 was the only passing row at $0.45 for six passes. Rubric 90 at the gate, restated to 100 after the phase 6 map fix | 8.28 |
| 6 Widen | Five generated variants of sample 1, each with its own key | Four knobs broke the map in four ways; each was traced to phase 3 and fixed there. Five known misses stand, every one a knob removing what tied a document to the matter | 7.78 |
| 7 Compare | The RLM skill rerun twice beside ours; our tool once on the real Yahoo filings | No planted facts on sample 4. Recall 72.7 on the first run, 86.4 after the long-document fix | 0.26 |

## 3. The outcome

### Head to head on the room the RLM was built for

We ran the RLM skill as shipped, twice, from Claude Code with Sonnet 5 as the leaf, on a
byte-identical corpus of the same 100 documents, and graded both reports with the same
grader we grade ourselves with.

| | Rubric a | Rubric b | Spread | Seconds | Gateway $ |
|---|---|---|---|---|---|
| RLM skill, Sonnet 5 leaf | 82 | 84 | 2 | 990 | 0 (subscription) |
| Ours, GLM 5.3 Flash + GLM 5.3 | 100 | 100 | 0 | 750 | about 0.30 per run |

The published 98.5 and the 82 to 84 we measured are the same method under two graders and
two days. What we can say from our own measurement is this: under one grader, on one
corpus, our fixed program scores 16 to 18 points higher, with no spread, in three quarters
of the time, on models that cost a fraction of the leaf the RLM used. The RLM's
planted-fact recall under our code grader is 34, ours is 100. That gap is mostly citation
shape, but it is also the point: the RLM paraphrases where the key wants the room's own
words.

### Generality

| Sample | What it tests | Recall | Rubric | Spread |
|---|---|---|---|---|
| 1 atlas | The original room: one matter, six functions, five decoys | 100 | 100 | 0 |
| 2 northwind | Eleven contracts; a change-of-control cliff on a 30.1% customer; a decoy contract on the same template | 100 | none | 0 |
| 3 northstar-dental | A numeric contradiction: the CIM claims 18.0% growth, the workbook shows 11.7% | 100 | none | 0 |
| 1 + names | Fifteen names in three to five spellings each | 100 | 94 | 6 |
| 1 + unnamed | The matter named nowhere, linked only by dates and numbers | 97.9 | 98 | 2 |
| 1 + second | A second, unrelated matter in the same room | 98.5 | 99 | 0 |
| 1 + twice | 200 documents, a sister entity's clones with no planted value | 98.1 | 100 | 1 |
| 4 yahoo | Real SEC filings, Verizon and Yahoo 2016 to 2017, no planted facts; key from the public record | 86.4 | none | one run |

On the real case the report lands on the right answer: proceed on the amended terms, the
$350m price cut and the 50/50 liability split as the baseline, with the committee's finding
that the security team knew of the 2014 intrusion at the time. The three facts it does not
carry are two cover-page identifiers and a share figure the report states from another
document. No fact that bears on the answer is missing.

### Money

| Item | $ |
|---|---|
| Everything, 5 to 9 September, all bake-offs, reruns and variants | 18.95 |
| Balance of the $50 ceiling | 31.05 |
| One end-to-end run of sample 1 today (notes on GLM 5.3 Flash, write on GLM 5.3) | about 0.30 |
| Sample 4, the seven filings, one run | 0.26 |

## 4. Between the lines

The numbers above are the answer to the question we asked. These are the things we did not
ask and learned anyway.

1. **The model was never the hard part.** Two of seven stages call a model, and the
   cheapest model on the table was good enough for one of them. Every point we gained after
   phase 2 came from code: the map's weighting, the dossier's comparisons, the verifier's
   four checks. Where the RLM spends a frontier model on deciding what to read, we spend a
   graph.
2. **Verification is what bought the score, not the writer.** Both Flash writers reached
   recall 98 to 100 and still failed. The gap between 90 and 100 on the rubric was closed by
   returning the verifier's list to the writer once, and by a map fix, not by a better
   model.
3. **The map is where generality lives.** Every knob in phase 6 broke phase 3 and nothing
   else. A map that links on the surface of a name fails on misspellings; a map that grows
   from one seed returns one matter; a map with a fixed cut loses a document when the room
   doubles. All four were fixed in the map with no change to the notes or the writer.
4. **The RLM's real strength is the leaf pass, and we kept it.** A cheap read of every
   document before selection is the one thing the winning run did that a corpus-only map
   cannot replace. Our notes stage is that pass, under a schema, verified.
5. **Determinism made the debugging possible.** Five stages are byte-identical over two
   runs and pinned by digest. When a fact went missing it was traced to a phase in minutes,
   because every other phase could be ruled out by its hash. The RLM has no equivalent; its
   middle cannot be diffed.
6. **Spread is a number, not a hope.** Every run is written twice and the difference is
   printed beside the score. On the three gate samples it is zero. The RLM's two runs
   differed by two rubric points and by their entire program.
7. **The discipline cost less than the loop it prevented.** The key-first,
   one-phase-at-a-time rule looks slow. It closed eight phases in five days on $18.95, with
   every dollar attributable to a sample, a phase and a model.

## 5. What still stands against us

- **Five known misses on the variants.** Each is a knob taking away the only thing that
  tied one document to the matter. The rule that would reach them is a pairwise model
  judge, which is priced and deliberately not built.
- **Sample 4 at 86.4.** Two lookup identifiers and one duplicated share figure. Closing them
  is a phase 4 issue and a $1 rerun that changes no conclusion.
- **One rubric, one room.** Samples 2, 3 and 4 have no rubric; their bar is recall and the
  verifier. The 100 is measured on the room the RLM was built for, and only there.
- **The writer needs a Pro-tier model.** GLM 5.3 is the only writer that passed the verifier
  on all three samples. The notes run on Flash; the write does not, yet.

---

Repository `Muhanad-husn/RLM`, 134 issues and pull requests, 2026-09-05 to 2026-09-09. Spend
from `LEDGER.md`, scores from `PLAN.md` section 4a and the phase 7 comparison. Source rooms:
brainqub3/synthetic-dataRoom (MIT), zoharbabin/due-diligence-agents (Apache-2.0),
The-Life/synthetic-dataroom-generator (MIT), SEC EDGAR.
