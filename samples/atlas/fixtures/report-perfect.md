# Diligence Findings Report: Project Atlas

## 1. Executive Summary

**Recommendation: Reprice or restructure via special indemnity.**

VistaPort Media has an undisclosed account-data and authentication-integrity incident that materially reduces the value of this acquisition. The incident began on 2025-10-18 and unfolded through 18-20 October 2025. The company suffered probable unauthorised bulk export of approximately 286m active and 912.8m total records from a legacy backup (legacy_uap_backup_2021.tar.gz). The incident (internally designated AURORA, NQ-17, and "Trust Reset") was flagged by security engineering and discussed by management and disclosure committees, yet the seller representation schedule states that the company has not suffered any material cybersecurity incident in the past twenty-four (24) months.

Outside counsel estimates exposure of approximately $240m to $465m against a booked reserve of only $12m. Cyber insurance will likely provide little or no recovery due to late notice and a prior-known-events exclusion. Advertiser contracts contain security-incident covenants. Forced password and account resets have measurably depressed the metrics used in the synergy model.

The net impact is a price reduction of approximately $400m (defensible range $375m to $525m), or an equivalent special indemnity and escrow with bespoke representations and extended survival.

---

## 2. Key Findings, Ranked by Materiality

### A. Undisclosed account-data and authentication-integrity incident

The core issue centers on VistaPort's AURORA investigation (also referenced as NQ-17 and the "Trust Reset" programme). The incident occurred beginning 2025-10-18 and continuing through 18-20 October 2025. The technical investigation by IronLake indicated that bulk export is probable (DR-069).

The affected data was contained in a backup object, legacy_uap_backup_2021.tar.gz, stored in the company's Kestrel object store. That backup contained approximately 912.8m total profile records, including approximately 286m records belonging to accounts active in the prior 24 months, plus approximately 8.4m legacy small-business accounts.

The forensic draft dated 2025-11-12 (DR-069) concluded bulk export is probable. However, the final summary dated 2025-11-20 (DR-070) stated that available evidence does not permit a conclusive determination of what, if anything, was removed. The comparison is stark: bulk export is probable against no conclusive determination of what was removed.

Evidence exists in SIEM logs (DR-067) and the Kestrel object-access log (DR-071). The ticket was initially classified as a security matter, then RECLASSIFIED as a network-quality / performance matter on 2025-10-23 (DR-068).

### B. Authentication-key vulnerability enabling forged sessions

Forged session-cookie activity occurred during the incident period. This was enabled because the VPAuth legacy session-signing key, vpauth-legacy-2019, had not been rotated since 2019-02-11. The key-rotation exception log indicates: Rotation blocked by legacy session compatibility (DR-074). This vulnerability, combined with access to password-reset tokens in the backup, created account takeover pathways.

### C. Governance and disclosure contradiction

The backup was created on 2021-07-31 and retained in storage. Policy requires a 36 months retention limit. The backup created 2021-07-31 and retained against a 36-month limit represents a retention violation. The backup inventory shows it exceeds 36-month policy (DR-073).

Disclosure committee minutes dated 2025-10-29 note that the materiality of the matter is not yet determinable (DR-013). This represents a stark contrast to the seller representation. The rep-vs-committee comparison is clear: no material cybersecurity incident in 24 months against materiality not yet determinable on 2025-10-29.

A disclosure-controls procedures memo (DR-086) confirms management awareness and engagement. Yet the seller representation schedule (DR-087) represents that the company has not suffered any material cybersecurity incident in the twenty-four (24) month lookback period, a direct contradiction.

Regulatory authorities have taken notice. A regulatory correspondence log (DR-079) and draft response to the Irish Data Protection Commission (DR-080) document ongoing inquiries.

### D. Insurance coverage weakness

VistaPort's cyber insurance policy carries a notice requirement (DR-081). A draft cyber-insurance notice to the broker was prepared on 2025-12-11 (DR-082). This notice timing raises concerns about whether we are past the date that the more conservative reading of the 45-day clock would imply. The notice-vs-window comparison is critical: notice drafted 2025-12-11 against 45 days from the ticket opened 2025-10-21.

The policy contains a prior-known-events exclusion (DR-081, DR-082). The insurance claims and recoveries schedule (DR-030) reflects minimal expected recovery.

Outside counsel has estimated exposure at approximately $240m to $465m (DR-088). Management recommends a reserve of $12m at this time (DR-029). The reserve-vs-exposure comparison is stark: $12m against $240m to $465m.

### E. Commercial covenant consequences

Advertiser contracts, including the Meridian Media Agency master services agreement (DR-035), contain user-trust and security-incident notification covenants. These contracts specify the right to terminate this Agreement, or any affected Insertion Order, with immediate effect. The covenant-vs-incident comparison is direct: termination for a Security Incident against a probable bulk export.

Early churn signals are documented in the advertiser retention report (DR-033) and advertiser churn and win-loss notes (DR-039). The customer success weekly readout dated 2025-11-14 (DR-042) reflects client concern.

### F. Metric and synergy impact

The forced password resets and Trust Reset programme have measurably degraded user engagement and ad yield. A visible step-down begins the week commencing 20 October 2025 (DR-048). The VistaMail metrics document the Trust Reset wave 1 impact (DR-050).

The integration synergy model (DR-096) assumes 615 million monthly active users and 408 million mobile monthly active users. The base case assumes no lasting trust friction. However, the model-vs-metrics comparison reveals: 615m MAU assumed flat against 594m in the week of 2025-11-10.

The account integrity and Trust Reset programme has generated costs of approximately $34m (DR-025).

---

## 3. Most Material Issue: Quantification and Deal Action

### Financial Exposure

Outside counsel at Juniper & Rowe prepared a privacy risk memorandum (DR-088) that assesses total exposure at approximately $240m to $465m.

The company has booked a reserve of $12m (DR-029). The net unreserved exposure is significant. Management recommends a reserve of $12m at this time, and the exposure range is approximately $240m to $465m, meaning the reserve-vs-exposure gap compares $12m against $240m to $465m.

Cyber insurance recovery is unlikely. Notice was drafted well past any reasonable window, and the prior-known-events exclusion applies.

The synergy model projects $410m in synergy NPV but assumes 615m MAU assumed flat. Realised metrics show 594m in the week of 2025-11-10, creating value at risk.

The net unreserved exposure yields a defensible range of $375m to $525m with a central estimate of approximately $400m price reduction.

### Recommended Deal Action

Northstar should reprice the transaction by approximately $400m (range $375m to $525m). Alternatively, structure a special indemnity and escrow with extended-survival representations.

The deal should address:
- The AURORA incident with approximately 286m active and 912.8m total records probably accessed
- The backup retention failure: backup created 2021-07-31 and retained against a 36-month limit
- The unrotated signing key: vpauth-legacy-2019, last rotated 2019-02-11
- The apparent breach of the seller representation

The fourteen required documents of the AURORA matter are: DR-069, DR-073, DR-074, DR-068, DR-013, DR-087, DR-088, DR-029, DR-081, DR-082, DR-096, DR-035, DR-050, DR-048.

The asset remains valuable at a corrected price.

---

## 4. Lesser and Lower-Priority Issues

**Tax nexus** (DR-031). Sales and use tax structure presents exposure of $6m to $9m, an order of magnitude smaller and fully estimable.

**Search partnership concentration** (DR-034). Search revenue dependency represents approximately 22% concentration. This is a genuine risk but not a value-destroying contingency.

**Email gateway security** (DR-076). Email-gateway alerts for phishing and BEC are routine operations and unrelated to the account-data incident.

**Open source licence compliance** (DR-090). Open source and GPL license clean-up poses only low-cost remediation risk.

**Executive and security retention** (DR-094). A key employee retention plan addresses deal-driven attrition.

---

## 5. Confidence and Open Items

**High confidence:** The technical evidence is contemporaneous (SIEM logs DR-067, Kestrel object-access log DR-071, backup inventory DR-073, key-rotation exception log DR-074 showing rotation blocked by legacy session compatibility). The backup exceeds 36-month policy (DR-073) and was created 2021-07-31. The disclosure committee's open materiality question dated 2025-10-29 (DR-013) directly contradicts the seller representation. Outside counsel's approximately $240m to $465m exposure estimate (DR-088) is based on established methodologies.

**Moderate confidence:** The exact volume exfiltrated is bounded by the forensic draft (bulk export is probable, DR-069) versus the final summary (no conclusive determination of what was removed, DR-070). Cyber insurance recovery is doubtful given the notice-vs-window issue (notice drafted 2025-12-11 against a 45-day window from 2025-10-21) and the prior-known-events exclusion.

**Would confirm:** (1) Detailed forensic access to establish affected-user counts; (2) Complete advertiser contract review; (3) Regulatory inquiry status; (4) Insurance counsel assessment; (5) Updated metrics post-Trust Reset.

Northstar's recommendation stands: reprice by approximately $400m (range $375m to $525m) or establish an equivalent special indemnity and escrow mechanism.
