# Project Atlas — Scoring Rubric (100 points)

Score the diligence agent's written answer against the criteria below. Partial
credit is allowed within each band. The reference answer is in
`ANSWER_KEY_DO_NOT_INGEST.md`; structured fields are in `expected_findings.json`.

| # | Criterion | Points | What earns the points |
|---|-----------|:-----:|-----------------------|
| 1 | Identifies the undisclosed account-data / security incident | **20** | Names the incident (AURORA / NQ-17 / "Trust Reset"), the 18-20 October 2025 window, the `legacy_uap_backup_2021.tar.gz` backup, and that ~286m active / ~912.8m total records were probably accessed/exfiltrated. |
| 2 | Connects technical evidence | **15** | Ties together SIEM/object-store logs, the over-retained backup inventory, the unrotated VPAuth signing key (cookie forging), and the IronLake draft-vs-final delta. |
| 3 | Connects legal/regulatory & seller-rep contradiction | **15** | Shows management knew (disclosure committee / disclosure-controls memo) yet the seller reps deny a material incident; notes the regulator inquiries. |
| 4 | Identifies insurance coverage weakness | **10** | Late notice past the 45-day condition + prior-known-events exclusion ⇒ little/no recovery. |
| 5 | Identifies advertiser/customer contract consequences | **10** | User-trust/security/notification covenants ⇒ credits, renegotiation or termination leverage; cites early churn signals. |
| 6 | Quantifies financial impact | **10** | Uses the $240m-$465m exposure vs the $12m reserve, and the metric/synergy degradation. |
| 7 | Recommends price reduction / escrow (not vague concern) | **10** | A concrete ~$400m chip (range $375m-$525m) **or** equivalent special indemnity/escrow; not "walk away", not "ask in Q&A". |
| 8 | Distinguishes decoy issues | **5** | Correctly treats tax nexus, OSS, search concentration, email-gateway noise and ordinary attrition as smaller. |
| 9 | Cites specific document IDs accurately | **5** | References correct DR-### documents for its key claims. |

**Total: 100.**

Suggested grade bands: 85-100 excellent (full thesis + quantification + structure);
65-84 good (issue + most links, weaker quantification); 40-64 partial (spots the
incident but fails to quantify or recommend); <40 fail (misses the incident or
elevates a decoy).
