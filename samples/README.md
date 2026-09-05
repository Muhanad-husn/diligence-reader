# Samples

Four corpora. The first three are the gate: every phase passes on all three before the next
phase starts. The fourth is run once at the end. Phase 0 turns each raw key below into one
`key.json` of the same shape (facts, each with its documents, its number or quote, and the
phase that must carry it) and writes each sample a brief in the shape of sample 1's.

## 1. `atlas` (Project Atlas, VistaPort and Northstar)

- Documents: `atlas/data_room/`, 100 files in eight folders (61 PDF, 29 XLSX, 7 CSV, TXT, EML,
  MBOX) plus the brief `atlas/data_room/README.md`, which is the task in five deliverables.
- Raw key: `atlas/key/expected_findings.json` (required documents, numbers, decoys),
  `atlas/key/ANSWER_KEY_DO_NOT_INGEST.md` (the reasoning chain and the price bridge),
  `atlas/key/scoring_rubric.md` (nine criteria, 100 points).
- Planted matter: an undisclosed account-data incident on 18 to 20 October 2025 against a
  legacy backup (912.8m records, 286m active, 8.4m small-business), renamed across functions
  (AURORA, NQ-17, Trust Reset, login friction, credential hygiene), a forensic draft softened
  in its final, counsel's exposure $240m to $465m against a $12m reserve, a 45-day insurance
  notice missed, advertiser covenants, engagement metrics down while the synergy model assumes
  them flat. Right answer: reprice by about $400m (range $375m to $525m) or an equivalent
  escrow and indemnity. Fourteen required documents; five decoys.
- Winner: `atlas/winner/` holds the 98.5-point RLM report, its three intermediate files, its
  nine-step trail with stdout, and the evaluator's verdict on the three baseline runs.
- Upstream: brainqub3/synthetic-dataRoom at fe26a96a, MIT. `atlas/fetch.sh` is the first
  build's sparse fetch of `data_room/` alone; the key and winner files were copied from the same
  clone on 2026-09-05.

## 2. `northwind` (Northwind Logistics Software, acquirer Summit Industrial)

- Documents: `northwind/sample_data_room/Northwind_Logistics/`, 11 markdown renderings of
  PDFs and one workbook, plus `_reference/buyer_overview.pdf.md`. Brief to be written in phase
  0 from `northwind/upstream-README.md` and `deal-config.json`.
- Raw key: the table in `northwind/upstream-README.md`. By construction:
  - Hero: `msa_meridian_freight.pdf.md` section 12.3(c), termination effective immediately on a
    change of control, no cure, no wind-down; `arr_schedule.xlsx.md` puts Meridian at
    $12,400,000, 30.1% of $41,200,000 ARR; `cap_table_summary.pdf.md` confirms the deal is a
    change of control; `board_deck_excerpt.pdf.md` says no change-of-control items are flagged
    and calls the concentration well mitigated. Right answer: a $12.4m revenue cliff at close,
    ranked first.
  - Control: `msa_granite_manufacturing.pdf.md` has a benign consent-based clause and must not
    be flagged as the hero.
  - Secondary: Harbor Foods termination for convenience on 30 days (16.5% of ARR); Cobalt
    $28.8m 36-month prepaid order (revenue recognition); a sub-processor with no transfer
    clauses (`dpa_tidewater`, `subprocessor_register`); a contractor who built core IP with no
    assignment (`contractor_agreement_route_engine` against `employment_ip_agreement`).
- Upstream: zoharbabin/due-diligence-agents at 50592659, Apache-2.0.

## 3. `northstar-dental` (Northstar Dental Group)

- Documents: `northstar-dental/`, 13 markdown and xlsx files. Brief to be written in phase 0.
- Raw key: `northstar-dental/metadata/contradictions.json` (C-001: CIM claims 18.0% growth,
  workbook shows $22.2m to $24.8m, 11.7%), `metadata/ground_truth_qa.yaml` (five questions:
  2025 revenue, growth, the contradiction, the highest vendor dependency, payor concentration),
  `metadata/entities.json`.
- Upstream: The-Life/synthetic-dataroom-generator at 6949cf84, MIT, preset `northstar-dental`,
  deterministic. Regenerate with the generator's CLI at that commit; the output here is the
  generator's own.

## 4. `yahoo` (Verizon and Yahoo, 2016 to 2017)

Final check only, phase 7. Public SEC filings, public domain, fetched by a script written in
phase 7 and kept out of git. See `yahoo/README.md` for the document list and the key from the
public record.
