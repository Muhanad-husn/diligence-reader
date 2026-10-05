# Sealed room pick for #160, by metadata only. index.parquet is the Material Contracts Corpus
# index, https://mcc.law.stanford.edu/index/v=20260806T202425Z/index.parquet (43,897,629 bytes).
# Picked on 2026-10-05: cik 1285550 MRI Interventions (room mri), cik 789851 Sensar Corp (room sensar).
# Room = a company's earliest 100 contracts
# by filing date (the rule the Avid room followed). Filters fixed before any result is seen.
import random, re
import pyarrow.parquet as pq
t = pq.read_table("index.parquet").to_pandas()
t = t[t.cik != "896841"].sort_values(["cik", "date_filed", "doc_key"])
BAD = re.compile(r"TRUST|RECEIVABLES|FUNDING|MORTGAGE|SECURITIZATION|LEASING|CAPITAL I|AUTO|CREDIT CARD|ETF|FUND\b", re.I)
rows = []
for cik, g in t.groupby("cik"):
    if len(g) < 100: continue
    r = g.iloc[:100]
    name = r.company_name.iloc[0]
    if BAD.search(name): continue
    lab = r.label.value_counts()
    if lab.get("employment", 0) > 60: continue
    if lab.get("purchase", 0) < 5: continue
    if (lab >= 5).sum() < 4: continue
    if (r.image_count > 0).sum() > 10: continue
    if not r.content_type.isin(["text/html", "text/plain"]).all(): continue
    if r.size_uncompressed.max() > 2_000_000: continue
    rows.append((cik, name, dict(lab), r.date_filed.min(), r.date_filed.max(), int(r.size_uncompressed.sum())))
print(len(rows), "companies pass")
random.seed(20261005)
for x in random.sample(rows, 2): print(x)
