# Sample 4: Verizon and Yahoo

The real case Project Atlas was modelled on. Run once, at the end, as the check on what nobody
here thought to plant. Documents are fetched in phase 7 into `documents/` (gitignored) by
`python -m rlm.yahoo fetch samples/yahoo`, which downloads each document below from the EDGAR
archives, converts it to markdown and splits it into one file per item or section.

## Documents to fetch from SEC EDGAR (Yahoo Inc., CIK 1011006)

Seven filings. The accession number is the folder on EDGAR; the archive URL of any document
below is `https://www.sec.gov/Archives/edgar/data/1011006/<accession without dashes>/<file>`.

1. 8-K of 25 July 2016 with the original stock purchase agreement. Accession
   `0001193125-16-656036`, written to `documents/8-K-2016-07-25-stock-purchase-agreement/`.
   Primary document `d178500d8k.htm`, exhibit 2.1 `d178500dex21.htm`.
2. 8-K of 22 September 2016 announcing the 2014 breach (500m accounts). Accession
   `0001193125-16-717056`, written to `documents/8-K-2016-09-22-2014-security-incident/`.
   Primary document `d260014d8k.htm`, exhibit 99.1 `d260014dex991.htm`.
3. 8-K of 14 December 2016 announcing the 2013 breach (1bn accounts). Accession
   `0001193125-16-793106`, written to `documents/8-K-2016-12-14-2013-security-incident/`.
   Primary document `d305610d8k.htm`, exhibit 99.1 `d305610dex991.htm`.
4. 8-K of 21 February 2017 and its exhibits: the amendment, price reduced by $350m to
   $4,475.8m, liability sharing. Accession `0001193125-17-049548`, written to
   `documents/8-K-2017-02-21-amendment/`. Primary document `d353690d8k.htm`, exhibit 2.1 the
   amendment to the stock purchase agreement `d353690dex21.htm`, exhibit 2.2 the amendment to
   the reorganization agreement `d353690dex22.htm`, exhibit 10.1 the settlement and release
   agreement `d353690dex101.htm`.
   https://www.sec.gov/Archives/edgar/data/1011006/000119312517049548/d353690d8k.htm
5. DEFA14A of February 2017, the press release. Accession `0001193125-17-049549`, written to
   `documents/DEFA14A-2017-02-21-press-release/`. Exhibit 99.1 `d353690dex991.htm`.
   https://www.sec.gov/Archives/edgar/data/0001011006/000119312517049549/d353690dex991.htm
6. Form 10-K for fiscal 2016 (filed 1 March 2017): the independent committee's findings on what
   management knew in 2014. Accession `0001193125-17-065791`, written to
   `documents/10-K-2016/`. Primary document `d293630d10k.htm`.
7. DEFM14A proxy of 24 April 2017: background of the transaction, the renegotiation. Accession
   `0001193125-17-133449`, written to `documents/DEFM14A-2017-04-24/`. Primary document
   `d206374ddefm14a.htm`.
   https://www.sec.gov/Archives/edgar/data/0001011006/000119312517133449/d206374ddefm14a.htm

The accession numbers of filings 1, 2, 3 and 6 were read off the filing index
`https://data.sec.gov/submissions/CIK0001011006.json` on 2026-09-09.

EDGAR asks every caller to name itself. The fetch sends the User-Agent
`RLM rebuild muhanad.a.husn@gmail.com` and waits a quarter of a second between requests, well
under the ten requests a second EDGAR allows. The raw HTML is cached under
`documents/_raw/<accession>/` so a rerun downloads nothing and writes the same bytes.

## Key, from the public record

- Matter: undisclosed historical account-data breaches, including forged-cookie activity,
  known in part to management in 2014 and disclosed to the buyer only after signing.
- Right answer at the time of the filings: reprice, not walk away; the parties cut the price by
  $350m and split post-closing breach liabilities 50/50 for non-SEC investigations and
  third-party litigation, with SEC and shareholder matters staying with Yahoo.
- The 10-K's committee finding that the company's information security team had contemporaneous
  knowledge of the 2014 intrusion is the knew-when fact.

`key.json` writes that record into the phase 0 shape: twenty-two facts of five kinds, each
naming the section files that carry it, no rubric and no decoys, and the answer a reprice of
350 USD millions. `brief.md` is the buy-side task in sample 1's shape.

The corpus here is a set of filings, not a data room, so this sample tests scale, real prose and
real inconsistency of names rather than the data-room shape. Its score is reported beside the
others with that stated.
