# 02: Comparisons and lesser matters on sample 1

Issue: [#64](https://github.com/Muhanad-husn/RLM/issues/64)

## Goal

`runs/atlas/dossier.md`'s first matter carries the seven comparisons the key plants for phase
4, each as one row that quotes both sides with both anchors, and a `Lesser matters` section
that ranks the room's other matters by the money in their notes, with the five decoys in it
and below the main matter.

## Acceptance criterion

Given slice 01 is merged,
when `python -m rlm.dossier samples/atlas runs/atlas` runs twice and `pytest -q
tests/test_phase4.py` runs,
then every key fact of kind `comparison` and phase 4 has one row in the `Comparisons`
section that names both of the fact's documents, carries one anchor per document that parses
and belongs to that document, and whose two quotes carry the two sides of the fact's value
split on ` against ` (each side's numbers, dates and words present after straightening);
the rows are `reserve-vs-exposure` (DR-029 `$12m` against DR-088 `$240m` to `$465m`),
`draft-vs-final` (DR-069 against DR-070, from the map's version pair), `rep-vs-committee`
(DR-087 against DR-013), `notice-vs-window` (DR-082 against DR-081 and DR-068),
`backup-vs-policy` (DR-073 against DR-052, a document outside the set reached by `36
months`), `model-vs-metrics` (DR-096 against DR-048, from the map's consequences),
`covenant-vs-incident` (DR-035 against DR-069); the `Lesser matters` section lists every
document not in the set that carries a flag, ranked by its largest money figure descending,
each with the figure, a quote and an anchor; every decoy is in `Lesser matters` and none is in
the first matter; two runs are byte-identical; the readout adds comparisons and lesser
matters counts; and every phase 3 test still passes with `map.json` unchanged from slice 01
(its sha256 is in the pull request body).

## Mechanism

`src/rlm/dossier.py` gains six readers, each a rule over what the map and the notes already
hold, not a schema:

- **Draft against final**: for each map version pair, the two notes' flags side by side; the
  row quotes the draft's flag and the final's flag that share the most words.
- **Reserve against estimate**: two set documents whose notes carry money figures, one whose
  figure's quote has a reserve word (reserve, provision, accrual, booked) and one whose
  quote has a range (two money figures joined by `to` or a dash); one row per such pair.
- **Deadline against action**: a set document whose note carries a duration figure (`45
  days`) and a dated flag; the row pairs the duration's quote, the date it counts from (the
  earliest dated statement in the same document or one it cross references), and the dated
  action in the other document.
- **Model against metrics**: each map `model-after` consequence against the `series-break`
  whose series carries the figure the model repeats; the row quotes the model's figure and
  the series' turn.
- **Covenant against incident**: a set document whose flag quote carries a termination word
  (terminate, termination) against the seed document's flag with the most shared words.
- **Policy against practice**: a set document whose figure quote carries a limit word (limit,
  maximum, retention) and the document outside the set whose figure equals it.

Every rule reads flags, figures and cross references from the notes and edges from the map.
A pair is written as `- <doc a> | <quote a> | <anchor a> || <doc b> | <quote b> | <anchor
b>`. Where a rule finds more than one pair, all are written, sorted by the pair of ids. The
key's fact names are not in the code.

`Lesser matters`: every document not in the first matter's set whose note carries at least
one flag, ranked by its largest money figure (parsed by `rlm.amounts`), then by id; one line
per document with the figure, the flag's quote and anchor.

No new dependency, no model call.

## Files

```aeo-independence
slice: 02-comparisons-atlas
edits: src/rlm/dossier.py
edits: tests/test_phase4.py
depends-on: 01-dossier-atlas
```

## Out of scope

Samples 2 and 3. Digests. The phase 5 report. A comparison that a rule cannot reach on
sample 1 is reported with the two notes' flags and figures, and the rule is widened, not the
fact hard-coded.
