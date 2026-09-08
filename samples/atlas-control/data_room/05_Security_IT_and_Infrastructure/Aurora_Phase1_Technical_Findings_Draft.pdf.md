CONFIDENTIAL — Project Atlas — DR-069 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 1

AURORA — Phase 1 Technical Findings (DRAFT, Privileged)
AURORA — Phase 1 Technical Findings (DRAFT)

Document ID DR-069
Prepared by / owner Renata Castellano
Date 12 November 2025
Classification Strictly Confidential — Project Atlas
Classification DRAFT — Privileged & Confidential
Prepared by IronLake Forensics

DRAFT — PRIVILEGED & CONFIDENTIAL — PREPARED AT THE DIRECTION OF COUNSEL — ATTORNEY
WORK PRODUCT. This memorandum records preliminary, work-in-progress technical findings of the AURORA
workstream. It is a draft prepared for the purpose of obtaining legal advice and is not a final conclusion. Findings
are subject to revision as the investigation continues.
Workstream AURORA (Phase 1 technical findings)
Prepared by Renata Castellano, Engagement Lead, IronLake Forensics
For Priya Raman, General Counsel (counsel)
Status DRAFT — privileged — not for distribution
Period under review October–November 2025

1. Summary of preliminary findings

Forensic review of Kestrel object-store access logs identified anomalous bulk reads of the object
legacy_uap_backup_2021.tar.gz during the period 18-20 October 2025 (earliest activity in the 18 October 2025
window). The access pattern is inconsistent with any scheduled restore or analytics job. On the present evidence,
a bulk export is probable; the read volume and egress are consistent with retrieval of the object in substantial
part.

• 5 distinct anomalous bulk-read events across the window.

• Peak/cumulative egress on the legacy backup prefix of approximately 1,840 GB flagged by detection content.
• Source IPs resolve to 3 foreign autonomous systems (ASNs) not associated with any known restore operation.
• Reads originated from principals/accounts not present in the documented restore schedule.

2. Contents of the affected object

The object legacy_uap_backup_2021.tar.gz is a 2021-era backup of the legacy Unified Account Profile store
(legacy_uap). Based on inventory metadata and sampling, the backup contained approximately 912.8m historical
profile records, of which approximately 286m correspond to accounts active within the preceding 24 months.
Attribute Preliminary assessment
Total historical profile records ~912.8m (912,800,000)
Active within 24 months ~286m (286,000,000)

Record fields present names, usernames, email addresses, recovery email addresses, phone numbers, dates
of birth, salted password hashes, password-reset tokens, security-question hashes

Legacy SMB accounts (special concern) ~8.4m legacy small-business accounts with improperly encrypted security-question
answers (legacy small-business accounts)
Payment / bank data No raw payment card numbers or bank account data were contained in the backup.

3. Authentication exposure — cookie-forging feasibility

Attribute | Preliminary assessment

Total historical profile records | ~912.8m (912,800,000)

Active within 24 months | ~286m (286,000,000)

Record fields present | names, usernames, email addresses, recovery email addresses, phone numbers, dates
of birth, salted password hashes, password-reset tokens, security-question hashes

Legacy SMB accounts (special concern) | ~8.4m legacy small-business accounts with improperly encrypted security-question
answers (legacy small-business accounts)

Payment / bank data | No raw payment card numbers or bank account data were contained in the backup.

CONFIDENTIAL — Project Atlas — DR-069 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 2

The VPAuth legacy session-signing key (kid=vpauth-legacy-2019) has not been rotated since 2019. Because this
long-lived key remains in the legacy validation path, an actor in possession of the key (or of material sufficient to
derive valid signatures) could forge session cookies accepted by the legacy VPAuth path. Abnormal
token-validation patterns observed during the window are consistent with — though not, on present evidence,
conclusive of — session forging. We observed on the order of 41,500 suspected forged/replayed session events.
4. Data categories and sensitivity
•
Identifiers and contact data: names, usernames, email and recovery-email addresses, phone numbers, dates
of birth.

• Authentication material: salted password hashes and password-reset tokens.
• Knowledge-based recovery: security-question hashes; and, for the legacy SMB cohort, ~8.4m records whose
security-question answers were improperly encrypted.
• No raw payment-card numbers or bank-account data were contained in the backup.
5. Preliminary conclusions (draft — subject to revision)
1 Anomalous bulk reads of the legacy_uap backup occurred during 18–20 October 2025.
2 On the present evidence, bulk export is probable; scope of any onward use is not yet established.
3 The unrotated legacy signing key materially increases authentication risk and should be rotated and retired as
a priority.

4 Further work is required before any of the above can be stated as a definitive finding.
DRAFT. Privileged and confidential. Prepared at the direction of counsel as attorney work product. Not a final report; figures and
conclusions are preliminary and subject to change. IronLake Forensics — AURORA workstream.
