# feat(phase-4): the seven comparisons and the lesser matters ranked by money on sample 1 [slice 02]

**Issue:** #64 · **Spec:** PLAN.md#4-phases, row "4 Dossier" · **Plan:** plans/phase-4/02-comparisons-atlas.md
**Depends on:** #63
**Labels:** phase-4

## Deliverable

`runs/atlas/dossier.md`'s first matter carries the seven comparisons the key plants for phase
4 (reserve against exposure, draft against final, rep against committee, notice against
window, backup against policy, model against metrics, covenant against incident), each as
one row quoting both sides with both anchors, and a `Lesser matters` section that ranks every
flagged document outside the set by its largest money figure, with the five decoys in it and
below the main matter. Two runs are byte-identical. `map.json` is unchanged from slice 01.

## Mechanism

`src/rlm/dossier.py` gains six readers, each a rule over what the map and the notes hold, not
a schema: draft against final from the map's version pair (the two flags sharing the most
words); reserve against estimate from a money figure whose quote has a reserve word against a
quote with a range; deadline against action from a duration figure, the date it counts from
and the dated action in the other document; model against metrics from each `model-after`
consequence against the `series-break` carrying the figure it repeats; covenant against
incident from a flag with a termination word against the seed's flag sharing the most words;
policy against practice from a figure quote with a limit word against the document outside
the set whose figure equals it. A pair row is `- <doc a> | <quote a> | <anchor a> || <doc b> |
<quote b> | <anchor b>`, all pairs a rule finds, sorted by the pair of ids. `Lesser matters`
ranks every document outside the set with a flag by its largest money figure through
`rlm.amounts`, then by id. The key's fact names are not in the code. No new dependency, no
model call. Tests are committed red first.

## Acceptance criterion

Given slice 01 is merged,
when `python -m rlm.dossier samples/atlas runs/atlas` runs twice and `pytest -q
tests/test_phase3.py tests/test_phase4.py` runs,
then every key fact of kind `comparison` and phase 4 has one row in `Comparisons` that names
both of the fact's documents, carries one anchor per document that parses and belongs to that
document, and whose two quotes carry the two sides of the fact's value split on ` against `
(each side's numbers, dates and words present after straightening); `backup-vs-policy`
reaches DR-052 outside the set and `draft-vs-final` reaches DR-070 through the version pair;
`Lesser matters` lists every document not in the set that carries a flag, ranked by largest
money figure descending, each with the figure, a quote and an anchor; every decoy is in
`Lesser matters` and none in the first matter; two runs are byte-identical; the readout adds
comparisons and lesser matters counts; every phase 3 test passes with `map.json` unchanged
from slice 01 (its sha256 in the pull request body); and all phase 0, 1 and 2 tests still
pass.

## Files

```aeo-independence
slice: 02-comparisons-atlas
edits: src/rlm/dossier.py
edits: tests/test_phase4.py
depends-on: 01-dossier-atlas
```

## Out of scope

Samples 2 and 3. Digests. The phase 5 report. A comparison a rule cannot reach on sample 1
is reported with the two notes' flags and figures and the rule is widened, not the fact
hard-coded.
