# Northstar Dental Group Synthetic Dataroom

This dataroom is fictional and generated for AI/RAG evaluation, diligence workflow demos, entity extraction, and context-graph testing.

## Company

- **Name:** Northstar Dental Group
- **Industry:** Dental services organization
- **Headquarters:** Columbus, Ohio
- **Founded:** 2014
- **Locations:** Columbus, OH, Cincinnati, OH, Dayton, OH, Indianapolis, IN, Louisville, KY

## Contents

- `company_profile.md` — company overview
- `cim.md` — confidential information memorandum-style summary
- `revenue_summary.xlsx` — revenue by year/category and annual totals
- `customer_contracts/` — synthetic customer/payor contract summaries
- `vendor_agreements/` — synthetic vendor agreement summaries
- `board_materials/` — synthetic board update
- `hr/employee_roster.xlsx` — executive/management roster
- `risks/risk_register.md` — diligence risks
- `metadata/entities.json` — structured ground-truth entities
- `metadata/contradictions.json` — known contradictions
- `metadata/ground_truth_qa.yaml` — questions and expected answers for evals

## Known benchmark feature

This dataroom intentionally includes a revenue-growth contradiction between `cim.md` and `revenue_summary.xlsx`. AI systems should identify the discrepancy and cite both sources.
