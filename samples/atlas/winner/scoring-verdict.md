# Project Atlas Agent Scoring Verdict

Evaluator: Codex
Date: 2026-06-22

Primary artifacts graded:

- `synthetic_vdr_project_atlas/data_room_no_rlm/Diligence_Findings_Report.md`
- `synthetic_vdr_project_atlas/data_room_rlm_run2/data_room/Diligence_Findings_Report.md`
- `synthetic_vdr_project_atlas/data_room_rlm_sonnet/data_room/Diligence_Findings_Report.md`

Supporting RLM audit artifacts reviewed:

- `synthetic_vdr_project_atlas/data_room_rlm_run2/crux_facts.json`
- `synthetic_vdr_project_atlas/data_room_rlm_run2/findings_crit_high.txt`
- `synthetic_vdr_project_atlas/data_room_rlm_run2/findings_compact.txt`
- `synthetic_vdr_project_atlas/data_room_rlm_run2/findings_pass1.json`
- `synthetic_vdr_project_atlas/data_room_rlm_sonnet/incident_synthesis.md`
- `synthetic_vdr_project_atlas/data_room_rlm_sonnet/findings_inventory.md`
- `synthetic_vdr_project_atlas/data_room_rlm_sonnet/lesser_issues.md`
- `synthetic_vdr_project_atlas/data_room_rlm_sonnet/.claude/rlm_runs/20260622_205649_6324/manifest.json`

Reference materials used:

- `synthetic_vdr_project_atlas/evaluator_private/scoring_rubric.md`
- `synthetic_vdr_project_atlas/evaluator_private/expected_findings.json`
- `synthetic_vdr_project_atlas/evaluator_private/ANSWER_KEY_DO_NOT_INGEST.md`

The first RLM run is intentionally excluded from this re-score.

## Run Conditions

| Run | Model | Prompt and mode | Elapsed time | Notes |
|---|---|---|---:|---|
| Non-RLM workflow | Opus 4.8 | Same due-diligence task prompt, Claude Code ultra code mode | **28 minutes 32 seconds** | Baseline non-RLM comparison run. |
| RLM run2 | Haiku 4.5 leaf | Same due-diligence task prompt with the RLM Skill, Claude Code `xhigh` mode | **8 minutes 45 seconds** | Second RLM run used persisted REPL/audit artifacts and removed prior hooks that appeared to block reads. |
| RLM Sonnet leaf | Sonnet 4.6 leaf | Same due-diligence task prompt and run2 setup, but with Sonnet as the RLM leaf model | **36 minutes 32 seconds** | Fourth experiment: same RLM approach as run2, using a more capable leaf model. |

## Executive Verdict

All three evaluated deliverables found the intended hidden issue: an undisclosed AURORA / NQ-17 / Trust Reset account-data and authentication-integrity incident involving the `legacy_uap_backup_2021.tar.gz` backup, roughly 912.8m total records, roughly 286m active records, anomalous October 2025 bulk reads, VPAuth cookie-forging risk, under-reserving, weak insurance recovery, advertiser/customer contract consequences, and a need to reprice or ring-fence the liability.

Final scores:

| Agent | Model | Score | Band | Verdict |
|---|---|---:|---|---|
| RLM Sonnet leaf agent | Sonnet 4.6 leaf | **98.5 / 100** | Excellent | Winner |
| Non-RLM agent | Opus 4.8 | **97 / 100** | Excellent | Runner-up |
| RLM run2 agent | Haiku 4.5 leaf | **91 / 100** | Excellent | Strong issue discovery, weaker calibration |

The RLM Sonnet leaf report is now the strongest final diligence answer. It keeps the central issue framed as a probable, unresolved, deliberately minimized data-security event; it connects the technical, legal, financial, insurance, customer, and valuation workstreams cleanly; and it mostly preserves decoy discipline. Its main imperfection is deal-action framing: the explicit headline price reduction is only ~$210m, while the answer-key-sized protection comes through a $350m-$465m ring-fenced escrow and uncapped special indemnity.

The non-RLM report remains a strong runner-up. It is still very close to the answer key because it recommends a deal adjustment near the expected ~$400m / $375m-$525m range and is disciplined about treating advertiser-contract and decoy risks as contingent or secondary. It loses to the Sonnet run mainly because the Sonnet report is more structured, more explicit about the cross-functional suppression pattern, and somewhat cleaner in preserving the "probable" rather than "confirmed" exfiltration nuance.

RLM run2 is highly effective at finding the issue, and the saved `crux_facts.json` / `findings_*` files make its working trail much easier to audit. That change is valuable operationally. The final report itself loses points because it repeatedly treats probable exfiltration as established, overstates some contract and regulatory predicates, recommends only a ~$200m headline price cut despite calculating a much larger value bridge, and elevates several decoys or secondary issues above the rubric's intended materiality.

On runtime, RLM run2 was fastest at **8 minutes 45 seconds**, the non-RLM workflow took **28 minutes 32 seconds**, and the RLM Sonnet leaf run was slowest at **36 minutes 32 seconds**. The scores above remain based on diligence quality and rubric fit rather than elapsed time.

## Rubric Scoring

| Rubric criterion | Points | Non-RLM | RLM run2 | RLM Sonnet | Notes |
|---|---:|---:|---:|---:|---|
| 1. Identifies undisclosed account-data / security incident | 20 | 20 | 19.5 | 20 | All find AURORA / NQ-17 / Trust Reset, the legacy backup, 912.8m total and 286m active records. RLM run2 is slightly dinged because the final report often says "bulk exfiltration" as fact and does not consistently state the 18-20 Oct window in the final deliverable. Sonnet states the 18-20 Oct window and "probable mass data exfiltration" cleanly. |
| 2. Connects technical evidence | 15 | 15 | 15 | 15 | All connect Kestrel/SIEM evidence, over-retained backup, unrotated VPAuth key, cookie-forging risk, and IronLake draft-vs-final softening. |
| 3. Connects legal/regulatory and seller-rep contradiction | 15 | 15 | 15 | 15 | All identify disclosure deferral, buyer-facing/Q&A understatement, draft representation weakness, regulator inquiries, and reserve-rep exposure. Sonnet is especially clear on the Disclosure Schedule gap. |
| 4. Identifies insurance coverage weakness | 10 | 10 | 9 | 10 | Non-RLM and Sonnet correctly frame the 45-day notice issue, prior-known-events risk, and weak recovery. RLM run2 is too categorical in calling recovery impaired or void. |
| 5. Identifies advertiser/customer contract consequences | 10 | 10 | 8 | 9.5 | Non-RLM is strongest on the full advertiser/DPA/customer covenant package. Sonnet strongly captures Meridian, 72-hour notice, early client pauses, LumenX softness, and synergy risk, but is slightly less explicit on the DPA schedule. RLM run2 overstates the predicate as "directly live given an actual breach." |
| 6. Quantifies financial impact | 10 | 9.5 | 9 | 10 | Sonnet gives the cleanest bridge: $240m-$465m counsel range, ~$352m midpoint, $12m reserve, ~$210m EBITDA add-back value, $145m insurance swing, and $154m LumenX revenue sensitivity. RLM run2 loses a point for a less coherent bridge between its ~$336m-$640m value calculation and its final ~$200m price reduction. |
| 7. Recommends price reduction / escrow | 10 | 8.5 | 8.5 | 9.5 | Sonnet recommends a ~$210m price reduction plus $350m-$465m dedicated escrow and uncapped special indemnity. That is close to the answer-key "equivalent escrow/indemnity" path, but the headline price cut itself remains below the expected $375m-$525m range. |
| 8. Distinguishes decoy issues | 5 | 5 | 3 | 4.5 | Non-RLM most cleanly demotes tax nexus, OSS, search concentration, email-gateway noise, and ordinary attrition. Sonnet demotes those issues in a lower-priority section, though it still gives some non-core privacy/consent and contract matters medium-high emphasis. RLM run2 loses more decoy discipline. |
| 9. Cites specific document IDs accurately | 5 | 4 | 4 | 5 | Sonnet cites the core documents accurately and densely. Non-RLM and RLM run2 cite the core documents well, but RLM run2 has several source-stretching statements including confirmed exfiltration, "actual breach" contract triggers, "DPAs already expired," "1.65bn+ records retained 4+ years past policy," and "InfoSec highest attrition." |
| **Total** | **100** | **97** | **91** | **98.5** |  |

## Non-RLM Assessment

Strengths:

- Reconstructs the hidden AURORA / NQ-17 / Trust Reset thesis across security, product, legal, finance, commercial, insurance, and board documents.
- Correctly anchors the conclusion to the key expected documents, including `DR-069`, `DR-071`, `DR-068`, `DR-073`, `DR-074`, `DR-088`, `DR-029`, `DR-081`, `DR-082`, `DR-035`, `DR-048`, `DR-050`, and `DR-096`.
- Best matches the answer-key economics: $240m-$465m exposure, $12m reserve, weak insurance recovery, metric/synergy degradation, and a deal adjustment around the expected ~$400m order of magnitude.
- Handles the key nuance well: the event is a probable, unresolved, deliberately minimized unauthorized bulk-access / likely-exfiltration event, not yet a regulator-confirmed breach.
- Cleanly demotes decoys such as sales/use tax, GPL cleanup, search concentration, ordinary employment matters, and working-capital mechanics.

Weaknesses:

- The suggested opening at the high case (~$730m) is aggressive relative to the expected $375m-$525m price-chip range.
- The report is longer than needed and includes some second-order issues that do not materially improve the answer.
- A few phrases push beyond the source record, though the report frequently self-corrects in calibration notes.

Score: **97 / 100**.

## RLM Run2 Assessment

Strengths:

- Finds the core hidden issue and ties it across the expected workstreams.
- The saved RLM outputs materially improve auditability. `crux_facts.json` is especially useful because it preserves extracted facts for the critical documents rather than leaving only the polished narrative.
- Strongly identifies the insurance weakness, the reserve gap, the seller-rep/disclosure problem, the Trust Reset relabelling, the EBITDA add-back problem, and the synergy-model dependency.
- Produces a clear deal-protection package: price reduction, special indemnity, escrow, conditions precedent, bespoke reps, and MAC triggers.

Weaknesses:

- The final report often states "bulk exfiltration" or "actual breach" as established, while the answer key and source documents support "probable" bulk export / likely exfiltration with confirmation still open.
- The headline price reduction is only ~$200m, below the answer-key $375m-$525m range, despite the report's own combined AURORA bridge of ~$336m-$640m before synergy haircut.
- The report gives a strong escrow/indemnity structure, but the relationship between price cut, escrow, indemnity cap, insurance recovery, and synergy haircut is less clean than the non-RLM report.
- It overstates some advertiser/customer consequences, especially by treating Meridian and regulated DPA exposure as already triggered by an "actual breach."
- It loses decoy discipline: sales/use tax is ranked as HIGH/MEDIUM, search concentration is included in a HIGH customer-risk finding, and ordinary/security attrition receives more emphasis than the rubric expects.
- Several non-core factual claims are shaky or likely wrong, including "DPAs already expired," "1.65bn+ records retained 4+ years past policy," and "InfoSec highest attrition in the company."

Score: **91 / 100**.

## RLM Sonnet Leaf Assessment

Strengths:

- Best final answer overall: it reconstructs the AURORA / NQ-17 / Trust Reset thesis across security, product, legal, finance, insurance, board, commercial, and HR evidence while preserving the critical "probable" rather than "confirmed" exfiltration nuance.
- Very strong chronology and suppression analysis, including the NQ-17 reclassification, IronLake draft-to-final softening, Disclosure Committee language controls, regulator wording, buyer Q&A answer, and seller-rep schedule gap.
- Cleanest quantification bridge: $240m-$465m gross counsel exposure, ~$352m midpoint, $12m reserve, ~$210m EBITDA add-back value, potential ~$145m cyber-insurance swing, and LumenX / synergy downside held as a sensitivity rather than double-counted.
- Best audit trail of the RLM runs reviewed here. The `incident_synthesis.md`, `findings_inventory.md`, `lesser_issues.md`, and saved RLM manifest make it easier to see how the final answer was built.
- Keeps most decoys in the right place: sales/use tax, OSS/GPL, search-syndication concentration, working-capital mechanics, and ordinary employment litigation are treated as lower-priority or bounded issues.

Weaknesses:

- The headline price reduction is only ~$210m, below the answer-key $375m-$525m price-chip range. The report substantially cures this with a $350m-$465m dedicated escrow and uncapped special indemnity, so the deduction is small.
- The advertiser/customer finding is strong on Meridian and early pauses but less explicit than the best answer on the DPA schedule and broader customer-notification covenant web.
- It gives some medium-high emphasis to standalone privacy/consent and change-of-control issues that are relevant but not as central as the hidden AURORA incident.
- Runtime was the longest of the evaluated runs at **36 minutes 32 seconds**, so the quality gain came with a material latency cost.

Score: **98.5 / 100**.

## Final Ranking

1. **RLM Sonnet leaf agent: 98.5 / 100**
2. **Non-RLM agent: 97 / 100**
3. **RLM run2 agent: 91 / 100**

The Sonnet leaf materially improves the RLM result. Compared with the Haiku-leaf run2, it keeps the auditability benefits while producing a much better calibrated final report: clearer uncertainty handling, cleaner chronology, stronger quantification, and better decoy ranking. Compared with the non-RLM run, it is slightly stronger as a written diligence answer, though slower. The Haiku-leaf run2 remains useful as evidence that the RLM workflow can find the hidden issue quickly, but the final report is less reliable at preserving uncertainty, ranking decoys, and translating its own quantification into the expected ~$400m deal action.
