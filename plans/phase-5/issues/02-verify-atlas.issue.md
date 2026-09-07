# feat(phase-5): verify.json on sample 1: citations resolve, numbers exist in their source, no certainty word raised, decoys below the matter, failures returned to the writer once [slice 02]

**Issue:** #80 · **Spec:** PLAN.md#4-phases, row "5 Report" · **Plan:** plans/phase-5/02-verify-atlas.md
**Depends on:** #79
**Labels:** phase-5

## Deliverable

`runs/atlas/verify.json` exists, written by code from `report.md`, `sections.jsonl`,
`index.jsonl` and `dossier.md`, and reads pass. Four checks: every citation resolves to a
section of the named document; every number in a cited sentence exists in a cited section or
the sentence is a `Calculation:` line whose operands do; no cited sentence's certainty word
sits above the highest rung of its cited sections; the first finding cites the dossier's
first matter's document set and no finding citing only lesser-matter documents comes before
one that cites the set. The writer sends the failures back to the model once as a list with
the first reply; `verify.json` records both rounds and `report.md` is the last reply.

## Mechanism

A new module `src/rlm/verify.py`: `CERTAINTY` ladder constant (possible: may, might, could,
possible, potential; probable: likely, probable, indicative, expected, approximately,
estimated; certain: confirmed, certain, conclusive, definitive, established),
`citations(line)`, `check_citations`, `check_numbers`, `check_certainty`, `check_order`,
`verify(report, sections, index, dossier) -> dict`, `main(argv)`. Numbers are normalised as
`rlm.grade.normalise` does; anchors parse with `rlm.sections.parse_anchor`. `rlm.write.main`
calls `verify` after the first reply and, on failures, builds the second call as
`rlm.notes.reask_messages` does, verifies again, writes `verify.json` with both rounds. The
document set is the `Documents` section of the dossier's first matter; the lesser documents
are its `Lesser matters` rows. The verifier reads no key and makes no model call. Tests are
committed red first.

## Acceptance criterion

Given slice 01 is merged and `runs/atlas/report.md` was written by `python -m rlm.write`,
when `python -m rlm.write samples/atlas runs/atlas` runs (the verifier runs inside it after
each reply) and `python -m rlm.verify samples/atlas runs/atlas` runs on the report on disk,
and then `pytest -q tests/test_phase5.py` runs,
then `verify.json` holds one round per model call made (one or two), each round a list of
failures with the check name, the line, and the reason, and a top-level `passes` that is
true when the last round is empty; every citation of `report.md` parses with
`rlm.sections.parse_anchor`, names a document of `index.jsonl` and an anchor of that
document in `sections.jsonl`; every number in a cited sentence, normalised as
`rlm.grade.normalise` does, is in the normalised text of one of the sentence's cited
sections, or the sentence is a `Calculation:` line whose every other number is; the highest
certainty rung of a cited sentence is not above the highest rung of its cited sections; the
first finding of section 2 cites a document of the dossier's first matter's document set and
no finding citing only lesser-matter documents precedes one that cites the set; when round
one fails, round two was one call carrying the first reply and the failure list, and
`report.md` is the second reply; the phase 5 test reads `verify.json` and fails when `passes`
is false; the phase 5 test also reads the key's decoys and fails when a decoy is cited in a
finding above the first finding that cites a `matter-documents` id; the readout prints the
failures per check per round; the verifier reads no key and makes no model call.

## Files

```aeo-independence
slice: 02-verify-atlas
creates: src/rlm/verify.py
edits: src/rlm/write.py
edits: tests/test_phase5.py
depends-on: 01-write-atlas
```

## Out of scope

The rubric grade and the spread (slice 03). Samples 2 and 3 (slice 05). A report that still
fails after the second call is reported with the failure list; the prompt or a check's
reading of the source is revised, and the check is not dropped.
