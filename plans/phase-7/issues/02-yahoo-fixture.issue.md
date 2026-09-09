# feat(phase-7): sample 4 fetched from EDGAR, split into markdown sections, keyed from the public record [slice 02]

**Issue:** #124 · **Spec:** PLAN.md#3-samples-and-keys, row 4 `yahoo` · **Plan:** plans/phase-7/02-yahoo-fixture.md
**Depends on:** none
**Labels:** phase-7

## Deliverable

`python -m rlm.yahoo fetch samples/yahoo` downloads the seven Yahoo filings `samples/yahoo/README.md`
lists from SEC EDGAR into the gitignored `samples/yahoo/documents/`, one folder per filing, one
markdown file per top-level item or heading, none over 40,000 characters, the same bytes on every
run. `samples/yahoo/key.json` is in the phase 0 shape with the public record's facts, no rubric and
no decoys; `brief.md` is in sample 1's shape. A fixture test checks every fact's value against the
text of every document it names before any model reads the sample.

## Mechanism

New module `src/rlm/yahoo.py`: fetch by accession number with the User-Agent EDGAR requires, HTML
to markdown through the `html2text` library pinned in `pyproject.toml`, split on the filing's
top-level headings (Item N for the 10-K, section headings for the proxy, article headings for the
exhibits) and then at paragraph boundaries past 40,000 characters. The key is written by hand from
the README and the fetched text, in the shape `rlm.key.load_key` reads. New
`tests/test_phase7_yahoo.py` with the fixture checks, skipping with a reason when `documents/` is
absent.

## Acceptance criterion

Given a network connection to sec.gov,
when `python -m rlm.yahoo fetch samples/yahoo` runs twice,
then `samples/yahoo/documents/` holds seven folders, one per filing, each holding one markdown
file per top-level item or heading, none over 40,000 characters, and the second run writes the
same bytes; `samples/yahoo/key.json` loads through `rlm.key.load_key` with at least ten facts of
kinds number, date, quote, identifier and comparison, no rubric, no decoys, and the answer reprice
350 USD millions; every fact's value appears in the text of every document it names; every key
document is a file; `brief.md` exists in sample 1's shape; `samples/yahoo/README.md` names the
seven accession numbers; `tests/test_phase7_yahoo.py` passes.

## Files

```aeo-independence
slice: 02-yahoo-fixture
creates: src/rlm/yahoo.py
creates: samples/yahoo/key.json
creates: samples/yahoo/brief.md
creates: tests/test_phase7_yahoo.py
edits: samples/yahoo/README.md
edits: pyproject.toml
```

## Out of scope

Running the chain. A perfect and a wrong report for sample 4. A rubric.
