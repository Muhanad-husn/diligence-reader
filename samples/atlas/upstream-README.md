# Synthetic M&A Data Room — Project Atlas

A **fully synthetic** M&A virtual data room built as test data for an AI
diligence agent. It models the *structure* of a large ad-tech/portal acquisition
and embeds a single **material, multi-document hidden issue** that a competent
diligence agent should surface and use to recommend a price reduction.

> ⚠️ **Everything here is fictional.** All companies, people, customers, vendors,
> contracts, logs and financials are invented. Any resemblance to real entities
> is coincidental. Inspired *structurally* by the public Verizon/Yahoo
> transaction pattern; it contains no real Yahoo/Verizon/AOL/Oath/Altaba data.

## The scenario

- **Buyer:** Northstar Mobile Holdings plc — telecoms/broadband operator expanding into digital media.
- **Target:** VistaPort Media Inc. — legacy internet portal & ad-tech company.
- **Deal:** *Project Atlas* — an indicative **$4.83bn** offer.

The seller materials make the asset look attractive (≈1.1bn
registered accounts, 615m MAU, 408m mobile MAU,
$5.15bn revenue, $775m adj. EBITDA,
$410m synergy NPV). The hidden issue is **not stated in any
single document** — it must be reconstructed across security, legal, commercial,
product, financial and board materials.

## The agent's task

The brief handed to the agent under test lives at **`data_room/README.md`** — it is the
agent's instructions, not one of the 100 documents. It asks the agent, as
Northstar's buy-side diligence lead, to produce a **diligence findings
report**: rank issues by materiality with document citations (`DR-###`), quantify the most
material one, and recommend a specific deal action (proceed / proceed-with-conditions /
reprice / escrow–indemnity / withdraw). The brief is deliberately neutral and does **not**
hint at any particular finding. See *"Three difficulty settings"* below to make it harder or
more guided.

## Repository layout

```
synthetic_vdr_project_atlas/
  data_room/                 <-- GIVE THIS (only) TO THE TEST AGENT
    README.md                (the agent's TASK BRIEF — instructions, not one of the 100 documents)
    00_Index_and_Process/    (the 100 diligence documents live in the 8 folders below)
    01_Corporate_and_Board/
    02_Financials_and_Tax/
    03_Commercial_and_Advertising/
    04_Product_Data_and_Technology/
    05_Security_IT_and_Infrastructure/
    06_Legal_Regulatory_and_Compliance/
    07_HR_Operations_and_Integration/
  evaluator_private/         <-- DO NOT GIVE TO THE TEST AGENT
    ANSWER_KEY_DO_NOT_INGEST.md
    expected_findings.json
    scoring_rubric.md
  generator/                 <-- generation + validation tooling (not part of the room)
    create_data_room.py
    atlas/                   (canon, rendering lib, section builders, evaluator content)
    manifest.json
    validation_report.txt
    research_notes.md
  README.md
```

## ⚠️ Evaluator materials

`evaluator_private/` contains the answer key, the structured expected findings and
the scoring rubric. **Never** supply `evaluator_private/` (or `generator/`) to the
agent under test — only `data_room/`.

## How to regenerate

```bash
cd synthetic_vdr_project_atlas/generator
python -m pip install reportlab openpyxl pypdf      # one-time
python create_data_room.py
```

The generator is **deterministic** (fixed seed = 20251018); regenerating produces
the same content. It safely deletes and recreates `data_room/` and
`evaluator_private/`, regenerates the evaluator files, writes `manifest.json` and
`research_notes.md`, then runs validation and writes `validation_report.txt`.

## How to validate the 100-document count

```bash
# from the repo root — count diligence documents only (exclude the task brief)
find synthetic_vdr_project_atlas/data_room -type f -not -name README.md | wc -l   # -> 100
# or rely on the generator's own report:
cat synthetic_vdr_project_atlas/generator/validation_report.txt
```

The validator also confirms: no answer-key strings leak into `data_room/` (including
`data_room/README.md`), every file has substantive content, all spreadsheets open with
openpyxl, CSVs have headers and enough rows, `expected_findings.json` is valid JSON, and the
key linkage terms (AURORA, NQ-17, Trust Reset, legacy_uap, IronLake, 18 October 2025, 286m,
912.8m) appear across multiple documents.

## Three difficulty settings for the agent's task

`data_room/README.md` is the **standard** brief. To recalibrate the test, adjust it:

- **Hard (most realistic):** replace the deliverables with a single instruction — *"Identify
  the single most material issue affecting price and recommend a specific deal action, with
  quantification."* Tests whether the agent finds the needle unaided.
- **Standard (shipped):** the brief as written — ranked findings, quantification, recommended
  deal action, decoys, confidence. Good for general benchmarking and partial-credit grading.
- **Diagnostic:** add *"Review across all of: security/IT, legal & regulatory, commercial
  contracts, financials, product/user metrics, support, board/disclosure, insurance, and HR."*
  Pinpoints which workstream the agent is weak at.

Grade the agent's output against `evaluator_private/scoring_rubric.md` (100 points) and check
its findings/IDs against `evaluator_private/expected_findings.json`.
