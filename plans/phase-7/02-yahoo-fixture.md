# 02: Sample 4 fetched, split and keyed

Issue: [#124](https://github.com/Muhanad-husn/RLM/issues/124)

## Goal

`samples/yahoo/` holds a key in the phase 0 shape and a brief, and one command fetches the
seven filings from SEC EDGAR and writes them as markdown sections the chain can read.

## Acceptance criterion

Given a network connection to sec.gov,
when `python -m rlm.yahoo fetch samples/yahoo` runs twice,
then `samples/yahoo/documents/` holds seven folders, one per filing, each holding one markdown
file per top-level item or heading, none over 40,000 characters, and the second run writes the
same bytes; `samples/yahoo/key.json` loads through `rlm.key.load_key` with at least ten facts
of kinds number, date, quote, identifier and comparison, no rubric, no decoys, and the answer
reprice 350 USD millions; every fact's value appears in the text of every document it names;
every key document is a file; `brief.md` exists in sample 1's shape; `samples/yahoo/README.md`
names the seven accession numbers; `tests/test_phase7_yahoo.py` passes and skips with a reason
when `documents/` is absent.

## Mechanism

New module `src/rlm/yahoo.py`: `fetch` downloads each filing's primary document by accession
number with the User-Agent EDGAR requires, converts HTML to markdown with the `html2text`
library pinned in `pyproject.toml`, splits on the filing's top-level headings (Item N for the
10-K, the proxy's section headings, the exhibits' article headings) and then at paragraph
boundaries past 40,000 characters, and writes the files. The key is written by hand from
`samples/yahoo/README.md` and the fetched text. New `tests/test_phase7_yahoo.py` with the
fixture checks above.

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
