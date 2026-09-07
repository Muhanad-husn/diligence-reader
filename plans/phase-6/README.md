# Phase 6: Widen

Milestone `Phase 6`. Spec: `PLAN.md` section 4, row "6 Widen". Cap $15. The phase that holds
phases 1 to 5 when knobs are turned on the fixture. Each knob is a generated variant of sample 1
with its own key: names spelled inconsistently, the matter named nowhere and linked only by dates
and numbers, a second matter, twice the documents.

The outcome: five variants under `samples/atlas-<knob>/` (control, names, unnamed, second, twice)
and five test digest files under `tests/phase6-<knob>-digests.json`. The chain runs unchanged
on each: `rlm.ingest`, `rlm.notes` (two passes, GLM 5.3 Flash), `rlm.map`, `rlm.dossier`,
`rlm.write` (two passes, GLM 5.3), `rlm.verify`, `rlm.grade`. A stage that drops a fact on a knob
is a gap in that stage's phase; under RULES.md gate 2 it is fixed in that phase by a new issue on
that phase's milestone, and every later phase reruns. A phase 6 slice does not fix it. The test
reads the key's words and the dossier's facts and names the phase that drops each.

## The bar

Planted-fact recall 100 on every knob, over every fact of its key, measured by
`rlm.grade.measure_recall`. Rubric at or above 85 on sample 1's variants, verifier passing.
Phases 1 to 5 hold on every knob or the readout names the first phase that fails.

## The shape decisions this phase fixes

- **The variant is a markdown data room, not rewritten PDFs.** `python -m rlm.widen <knob>
  samples/atlas samples/atlas-<knob>` reads sample 1's pinned `runs/atlas/sections.jsonl`
  (checked against `tests/phase1-digests.json`) and writes one markdown file per document under
  `samples/atlas-<knob>/data_room/<same folder>/<same name>.<ext>.md`, the convention sample 2
  already uses, one section per block or table row in ingest's order. The same DR ids are kept;
  `key.json`'s `documents` map points at the new paths. Reason: ingest already reads markdown,
  rewriting PDF and XLSX bytes deterministically is not something this repository does, and the
  key's anchors are then line anchors the phase 1 test resolves as it does for sample 2.
- **The key is by construction.** The generator writes `samples/atlas-<knob>/key.json` from
  `samples/atlas/key.json`: same facts, same required documents, decoys, answer, rubric and bar,
  except where the knob rewrites a fact's text, in which case the fact carries the rewritten text
  as it stands in the fact's first document, or removes a fact, in which case the fact is dropped
  and the drop is listed in `samples/atlas-<knob>/README.md`. The brief is sample 1's
  `brief.md` copied, with one added paragraph only where the knob adds documents.
- **The generator is deterministic.** Seed 0, no model call, no clock, no socket. A test
  regenerates the variant into a temporary directory and compares every file byte for byte with
  the committed one. Variants are committed under `samples/atlas-<knob>/` like every other sample;
  runs go under `runs/atlas-<knob>/` and are never committed, pinned by digest under
  `tests/phase6-<knob>-digests.json` through `python -m rlm.pin runs --samples atlas-<knob>
  --digests tests/phase6-<knob>-digests.json` (pin already takes `--samples` and `--digests`).
- **The chain runs unchanged.** Every stage takes `samples/atlas-<knob> runs/atlas-<knob>`:
  `rlm.ingest`, `rlm.notes` (two passes, GLM 5.3 Flash), `rlm.map`, `rlm.dossier`, `rlm.write`
  (two passes, GLM 5.3), `rlm.verify`, `rlm.grade`. No code of phases 1 to 5 changes in a phase 6
  slice except one flag: `rlm.notes` and `rlm.write` gain `--phase` (default their own phase
  constant) so a knob run books its ledger rows to phase 6 and its $15 cap. A stage that drops a
  fact on a knob is a gap in that stage's phase; under RULES.md gate 2 it is fixed in that phase
  by a new issue on that phase's milestone, and every later phase reruns.
- **The phase 6 test names the phase.** `tests/test_phase6.py` is parametrised over every
  `samples/atlas-*/key.json` present and runs, per knob, one test per phase in order: phase 1,
  every planted fact's value in a section of one of its own documents and every anchor resolving;
  phase 2, every planted fact in the note of its own document with a verified quote; phase 3,
  every required document in the matter's set; phase 4, every fact in the dossier with its anchor,
  no decoy in the set; phase 5, `rlm.grade.measure_recall` 100, the verifier passing, the rubric
  at or above 85, the spread printed. Each test skips with a reason when its artefact is absent.
  The readout prints one line per knob: recall, dollars from the ledger's phase 6 rows for that
  sample, spread, and the first phase whose test failed, or `holds`. The phase checks are imported
  from `rlm.grade` and from the phase 1 to 5 test modules' helpers, not rewritten.
- **Knob-specific checks live in their own file.** `tests/test_phase6_<knob>.py` so that the four
  knob slices touch no common file.
- **Money.** Phase 5 measured one pass of notes on sample 1 at about $0.07 on GLM 5.3 Flash and
  one write on GLM 5.3 at about $0.11 plus a re-ask of about the same. One knob is two notes
  passes and two writes with re-asks, about $0.60; the twice knob is about $1.20. Five variants
  (control plus four knobs) about $3.60, expected under $5 of the $15 cap. The rubric grader runs
  on the subscription at $0.

## Slices

| NN | Slice | Plan | Issue | Depends on |
|---|---|---|---|---|
| 01 | Generator, control variant and phase 6 harness | [01-generator-control.md](01-generator-control.md) | #96 | none |
| 02 | Names spelled inconsistently | [02-names.md](02-names.md) | #97 | 01 |
| 03 | The matter named nowhere, linked only by dates and numbers | [03-unnamed.md](03-unnamed.md) | #98 | 01 |
| 04 | A second matter | [04-second.md](04-second.md) | #99 | 01 |
| 05 | Twice the documents | [05-twice.md](05-twice.md) | #100 | 01 |
| 06 | Phase 6 gate | [06-gate.md](06-gate.md) | #101 | 02, 03, 04, 05 |

Order of work: slice 01 alone. Slices 02 to 05 run concurrently, each in its own worktree, at
most four at a time. Slice 06 runs after all are merged.

## What the knobs make this phase carry

Control: the walking skeleton and the baseline. Everything built in phases 1 to 5, running on
the markdown rendition of sample 1, separates what the markdown rendition costs from what a knob
costs.

Names: at least ten distinct names respelled, every respelled name appearing in at least three
spellings across the room. The names knob is where PLAN.md section 8 expects grouping by
identifier to fail. The price of a fix is put to the founder, not built.

Unnamed: the matter's names removed and its documents linked only by dates and numbers. Every
identifier fact for the removed names is dropped and listed in the README.

Second: sample 2's eleven documents as a ninth folder, ids DR-101 to DR-111, its 16 facts and
10 required documents added to the key, its ARR schedule in the Northwind Logistics contracts.
Decoys are sample 1's five plus the Granite MSA. The answer stays sample 1's.

Twice: 81 non-required, non-decoy documents of sample 1 cloned into a sister entity's room under
`data_room/09_Sister_Entity/`, ids starting DR-201, and the 19 largest cloned a second time with
different factors, so the room holds exactly 200 documents. No planted value of the key appears
in any clone.

## A risk to name

The markdown rendition itself may drop a fact in phase 1, which the control variant catches
before any knob is read. The names knob is where PLAN.md section 8 expects grouping by
identifier to fail; the price of a fix is put to the founder, not built here.
