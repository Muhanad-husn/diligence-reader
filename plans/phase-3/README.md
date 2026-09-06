# Phase 3: Map

Milestone `Phase 3`. Spec: `PLAN.md` section 4, row "3 Map". Cap $0 for map code; slice 00
fixes a phase 2 gap and costs about $0.08.

The outcome: `runs/<sample>/map.json` exists for all three gate samples. One map is built
from the phase 1 index, the phase 1 sections, and the pinned phase 2 notes of each document,
with no model call. A map is a document graph of shared identifiers, cross-references, date
proximity and version pairs; a ranked list of documents per matter; and consequence links
read off the index's series and dates. The map is deterministic: two runs on the same pinned
notes are byte-identical. Every key document of the planted matter is inside the first
matter's cluster; no decoy is.

## The shape decisions this phase fixes

- **The map is a ranking over weighted links, not a reach.** A corpus-only map reaches 91 of
  100 documents on sample 1. The signal that separates the fourteen required documents from
  the five decoys is what the notes say (flags, concealed items and cross references)
  weighed against how common a shared value is across the room.
- **Weight falls with how common a value is.** AURORA is in 16 documents so it weighs less
  than a value in 4 documents. A shared value the notes wrote as a cross reference or inside
  a flag weighs more than one only the index saw.
- **The cut is a fixed rule, not a tuned number.** A matter is seeded from documents whose
  notes carry flags or concealed items and share the rarest values. Its cluster holds
  documents whose weighted links to the seed clear a fixed cut. The same rule applies to all
  three samples with no code change.
- **The notes' flags, concealed items and cross references are the discriminating signal.**
  A shared value the model wrote into a note as a cross reference, or quoted inside a flag,
  is what the document itself said matters; a value only the index saw is background.
- **Consequence links reach what identifiers do not.** A series that breaks at the matter's
  date and a model dated after it add to a document's score, so the two documents the first
  build's corpus-only map missed are ranked inside the cluster by their own link.
- **The room's index and Q&A log are ordinary documents whose notes count.** Their
  cross-references count toward the matter's links like any other document's.
- **Consequence links are read off the index's series and dates, by code.** A
  series-break is an index `series` record whose consecutive periods carry values that turn
  at a period within seven days of the matter's date. A model-after is a document whose note
  says model, forecast, synergy or plan and whose first date is after the matter's date and
  whose figures share a value with a cluster document.
- **Two runs are byte-identical.** The map reads from the key's `documents` order; edges are
  sorted by kind, then by the sorted pair of document ids; the ranked list is sorted by
  score descending. Ties are broken deterministically.
- **Tests read the artefact and refuse notes that do not match the phase 2 digests.** Phase 3
  is deterministic over the pinned notes, so they have to exist. Phase 2's gap (the notes
  were pinned under a worktree and lost) is a slice 00 fix issue. The rule it adds: pinned
  artefacts are written under the main checkout's `runs/`, `D:\RLM\runs`, never under a
  worktree.
- **The map is pinned by digest at the gate.** `tests/phase3-digests.json` holds the sha256
  of each sample's `map.json` and a test asserts the file on disk matches it.

## Slices

| NN | Slice | Plan | Issue | Depends on |
|---|---|---|---|---|
| 00 | fix(phase-2): pinned notes rerun and repinned | [00-repin-notes.md](00-repin-notes.md) | #52 | none |
| 01 | Map on sample 1: document graph, matter cluster | [01-map-atlas.md](01-map-atlas.md) | #53 | 00 |
| 02 | Consequence links and versions on sample 1 | [02-consequences-ranked-atlas.md](02-consequences-ranked-atlas.md) | #54 | 01 |
| 03 | Map on samples 2 and 3 | [03-map-northwind-northstar.md](03-map-northwind-northstar.md) | #55 | 02 |
| 04 | Phase 3 gate | [04-gate.md](04-gate.md) | #56 | 03 |

Order of work: 00, 01, 02, 03, 04, one after the other. Nothing in this phase runs
concurrently because every slice builds on the previous artefact, and slice 00 is a phase 2
fix that must run before phase 3 code.

## Money

Slice 00 costs about $0.08 (one pass a on three samples of `python -m rlm.notes` with GLM 5.3
Flash, the model that passed phase 2). A pass that misses a phase 2 fact reruns once at most,
about $0.08 more, so slice 00 costs up to $0.16 with one rerun. Slices 01 to 04 are code and
cost $0, which is the phase 3 cap in `PLAN.md`. Slice 00's spend is phase 2's and counts
against the $8 phase 2 cap; `LEDGER.md` records it as phase 2.

## What the samples make this phase carry

Sample 1: from the fresh phase 1 index, following shared identifiers and upper-case codes
alone from DR-069 reaches 91 of the 100 documents, all fourteen required and all five decoys.
The discriminators: AURORA is in 16 documents; Trust Reset in 30; Kestrel in 12; IronLake in
10. Sample 2: the four Meridian documents (msa_meridian_freight.pdf.md, arr_schedule.xlsx.md,
cap_table_summary.pdf.md, board_deck_excerpt.pdf.md) form one hero matter linked by the
customer's name and its ARR figures; the Granite MSA shares the phrase Change of Control with
the Meridian MSA and the cap table and is the decoy. Sample 3: the CIM, the revenue workbook
and the board update form one matter linked by growth figures and the 2025 revenue; no decoy.

## A risk to name

The first build's corpus-only map reached eleven of fourteen documents and missed DR-048,
DR-050 and DR-096 (the metrics and synergy documents). Slice 02's consequence links are how
this build reaches them by rule: a series break for DR-048 (its weekly engagement metrics turn
at the incident week), a model-after for DR-096 (a model dated after the incident with figures
in common). If these links do not reach them, the fix is in slice 02, not a hard-coded id.
