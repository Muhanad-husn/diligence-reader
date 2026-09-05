# 03: Keys and briefs for samples 2 and 3

Issue: [#3](https://github.com/Muhanad-husn/RLM/issues/3)

## Goal

`samples/northwind/key.json` and `samples/northstar-dental/key.json` load through the same
`src/rlm/key.py` as sample 1's, with a brief beside each in the shape of sample 1's.

## Acceptance criterion

Given the two keys and two briefs exist,
when `pytest -q tests/test_phase0.py -k key` runs,
then it passes on all three samples with no change to `src/rlm/key.py` or the test, every
document each key names resolves to a file in its sample, and the `answer` of `northwind`
carries 12.4 (USD millions, the revenue cliff) and of `northstar-dental` carries 11.7 (percent,
the true growth).

## Mechanism

- Data written by hand from `samples/northwind/upstream-README.md` and
  `samples/northstar-dental/metadata/`. Document ids are the file paths relative to the sample,
  since neither sample has an index.
- Northwind facts: the 12.3(c) termination on change of control (quote), Meridian $12,400,000
  and 30.1% of $41,200,000 (numbers), the cap table's change-of-control confirmation, the
  deck's "no change-of-control items flagged" (quote, comparison against the MSA), Harbor 30
  days and 16.5%, Cobalt $28.8m and 36 months, the Tidewater sub-processor gap, the contractor
  IP gap. Decoy: `msa_granite_manufacturing.pdf.md`, the benign consent clause. No rubric.
- Northstar facts: 2025 revenue $24.8M, 2024 $22.2M, growth 11.7%, the CIM's 18.0% claim
  (comparison), CloudDent renewal 2025-09-30 as the top vendor dependency, Buckeye and Midwest
  $10.0M together. Decoy: none planted; the other two vendors are listed so the wrong report
  can elevate one. No rubric.
- Briefs: sample 1's brief with the deal, the parties, the folder table and the same five
  deliverables. Northwind names Summit Industrial Group acquiring Northwind Logistics
  Software, about $41.2M ARR. Northstar names a buy-side lead for an unnamed sponsor acquiring
  Northstar Dental Group. A brief names the deal and the folders, never a planted fact.
- No model call.

## Files

```aeo-independence
slice: 03-keys-northwind-northstar
creates: samples/northwind/key.json
creates: samples/northwind/brief.md
creates: samples/northstar-dental/key.json
creates: samples/northstar-dental/brief.md
depends-on: 01-key-atlas
```

## Out of scope

Reports and grading for these samples. If the shape from slice 01 cannot hold one of these
keys, that is a `spec-drift` on this issue, fixed in `src/rlm/key.py` in this slice with the
reason in the pull request body.
