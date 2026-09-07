# Phase 4: Dossier

Milestone `Phase 4`. Spec: `PLAN.md` section 4, row "4 Dossier". Cap $0: every slice is code.

The outcome: `runs/<sample>/dossier.md` exists for all three gate samples, written by
`python -m rlm.dossier samples/<sample> runs/<sample>` from the map, the index, the sections
and the pinned notes, with no model call. The dossier is the only thing the phase 5 writer
reads, so it carries everything the report needs: per matter, a timeline of dated statements,
every name each function gave the matter, figures with their sources, draft against final,
booked reserve against stated estimate, deadlines against actions, models blind to the matter,
and lesser matters ranked by money. Every row cites one anchor that resolves. Two runs are
byte-identical. Every planted fact of phases 1 to 4 is in the dossier with its anchor and its
number. No decoy is in the matter's document set and every planted document is ranked above
every decoy.

## The shape decisions this phase fixes

- **The dossier is markdown with a fixed row grammar.** The phase 5 model reads prose; the
  phase 4 tests and the phase 5 verifier read rows. One file serves both: every fact row is
  `- <date or figure> | <doc> | <quote> | <anchor>` and every comparison row names two
  documents and two anchors. No sidecar JSON. The grammar is the module's, not tuned to a
  sample.
- **The matter's document set is the map's cluster after two map changes made here.** The
  founder approved on 2026-09-07 that phase 4's first sample 1 slice lifts the one-per-matter
  cap on consequences and brings the cluster cut in; sample 1's expected cluster is near 14.
  The cut is tested here against its consumer, the dossier, as `RULES.md` asks, and not
  against a number. Phase 3's digests are repinned in the same pull request because the map
  changed, and the phase 3 tests rerun.
- **Comparisons are pairs the map already links, laid side by side.** Draft against final
  is the map's version pair, the two notes' flags in two columns. Reserve against estimate,
  deadline against action, model against metrics and covenant against incident are two
  documents joined by a shared value or a consequence link, each side quoted from its note
  with its anchor. A comparison may reach a document outside the matter's set when a shared
  value carries it there (the retention policy DR-052 is reached from the backup inventory by
  `36 months`); the set is what the report is about, not the limit of what it may cite.
- **The decoy checks live here.** Moved from phase 3 on 2026-09-07 (#55, PR #61): the map
  cannot tell the Granite MSA from the Meridian MSA because they share a template, and the
  matter's two defining values never sit inside a flag quote. The dossier reads clause content
  out of the notes' flags and figures: a document enters the matter's set only when a flag
  quote or a figure of its own carries one of the matter's defining values. The map's
  attestation rule is not reopened for this.
- **Lesser matters are the rest of the room, ranked by the money in their notes.** The five
  atlas decoys are lesser matters, below the main matter, each with its largest figure. This
  is where the phase 5 report's fourth section comes from.
- **Certainty words are copied.** A dossier row quotes the note's quote. Nothing is
  paraphrased, so the writer inherits the source's words.
- **Two runs are byte-identical.** Rows are sorted by date, then document id, then anchor.
  Ties are broken deterministically.
- **The dossier is pinned by digest at the gate.** `tests/phase4-digests.json` holds the
  sha256 of each sample's `dossier.md`, written by `python -m rlm.pin --dossiers`.

## Slices

| NN | Slice | Plan | Issue | Depends on |
|---|---|---|---|---|
| 01 | Dossier on sample 1: document set, timeline, names, figures, models blind to it | [01-dossier-atlas.md](01-dossier-atlas.md) | #63 | none |
| 02 | Comparisons and lesser matters on sample 1 | [02-comparisons-atlas.md](02-comparisons-atlas.md) | #64 | 01 |
| 03 | Dossier on samples 2 and 3, decoy separated by clause | [03-dossier-northwind-northstar.md](03-dossier-northwind-northstar.md) | #65 | 02 |
| 04 | Phase 4 gate | [04-gate.md](04-gate.md) | #66 | 03 |

Order of work: 01, 02, 03, 04, one after the other. Every slice edits `src/rlm/dossier.py`
and `tests/test_phase4.py`, so nothing runs concurrently.

## Money

$0. No slice calls a model. `LEDGER.md` gains no line.

## What the samples make this phase carry

Sample 1: fourteen required documents, five decoys, seven comparison facts. The cluster is
57 wide on the phase 3 map with the decoys at ranks 73 to 89; the founder's two map changes
bring it in. The comparisons need one document outside the fourteen, DR-052, reached by a
shared value, and DR-070, reached by the version pair. The two consequences the phase 3 cap
discarded, DR-050 (a second series turning at 2025-10-20) and DR-005 (a second model
repeating 615m after the matter), come back when the cap lifts.

Sample 2: four hero documents and one decoy that ranks second on the map. The Meridian MSA's
note flags the change-of-control clause with `effective immediately`; the Granite MSA's note
flags no change-of-control clause at all. The matter's defining values are the customer's
name and its `$12,400,000`, which sit in figures and cross references, never in flag quotes.
The comparisons are the board deck's `No customer-termination, change-of-control, or
contract-portability items are flagged` against the MSA's `effective immediately`, and the
contractor agreement's `contains no provision assigning` against the employment agreement's
`hereby irrevocably assigns`.

Sample 3: three documents, no decoy, one comparison: the CIM's `18.0%` growth claim against
the workbook's `11.7%`. The workbook's own note flags the arithmetic.

## A risk to name

Bringing the cut in on sample 1 could drop a required document that sits low on the phase 3
map (DR-029 at rank 48, DR-050 at 45, DR-081 at 41). Slice 01's test is the fourteen in the
set with no decoy; if the cut alone cannot hold the fourteen, the fix is in how the map scores
a document (a consequence link, a flag attestation), reported in the pull request, not a
hard-coded id and not a relaxed test. A second failure on sample 1 is the phase's second
attempt under `RULES.md` gate 3.
