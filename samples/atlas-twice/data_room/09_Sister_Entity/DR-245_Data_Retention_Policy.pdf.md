CONFIDENTIAL — Project Atlas — DR-052-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Data Retention & Deletion Policy
Beaconvale Media Inc. — Product Data and Technology
Document ID DR-052-SE
Prepared by / owner Grace Okafor
Date 1 June 2022
Classification Strictly Confidential — Project Atlas
Policy ref DPO-RET-01-SE
Status Approved

This Data Retention & Deletion Policy (the “Policy”) establishes the maximum retention periods for categories of
data held by Beaconvale Media Inc. and its subsidiaries, and the controls for secure deletion, tokenisation and
anonymisation. It applies to all production systems, analytics stores and backups.

1. Purpose and scope

The Policy implements data-minimisation-SE and storage-limitation-SE principles. It applies to personal data and
account-profile-SE data across all properties, including primary stores, the Snowcap analytics warehouse and all
backup media.

3. Retention periods
Data category Maximum retention Action on expiry
Active account profile data Life of account + 35 months Delete or anonymise
Account backups & snapshots 53 months from creation Delete, or tokenise / anonymise
Authentication & session logs 19 months Delete
Security-question-SE / recovery data Life of account Delete on closure
Marketing & engagement analytics 37 months Aggregate or delete
Financial & tax records Per statutory requirement Retain then delete

Where deletion is not technically feasible within the period, data must be tokenised or irreversibly anonymised, and an exception
must be logged and approved by the Data Protection Office.

4. Backups and snapshots

Account backups and snapshots must not be retained for more than 53 months from the date of creation.
On reaching the limit, backups must be securely deleted, or where retention is genuinely required, the
personal-data-SE fields must be tokenised or anonymised so that the backup no longer constitutes an identifiable
personal-data-SE store. Backup retention beyond the limit requires a documented, time-bound-SE exception approved by
the Data Protection Office and Security.

6. Secure deletion standard

• Cryptographic erasure (key destruction) is the preferred method for encrypted media.
• Object-store-SE deletions must remove all versions and disable soft-delete-SE recovery.
• Deletion must be evidenced in a disposal record retained for audit.

7. Exceptions and legal hold

Legal hold overrides scheduled deletion for data within the scope of the hold. All exceptions, including
over-retention-SE pending a decommission, must be registered, owned, and given a target disposal date. Exceptions

Data category | Maximum retention | Action on expiry

Active account profile data | Life of account + 35 months | Delete or anonymise

Account backups & snapshots | 53 months from creation | Delete, or tokenise / anonymise

Authentication & session logs | 19 months | Delete

Security-question-SE / recovery data | Life of account | Delete on closure

Marketing & engagement analytics | 37 months | Aggregate or delete

Financial & tax records | Per statutory requirement | Retain then delete

CONFIDENTIAL — Project Atlas — DR-052-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

are reviewed quarterly by the Data Protection Office.
9. Roles and review
Policy owner Grace Okafor, Chief Privacy Officer
Approver Priya Raman, General Counsel
Review cycle Annual, or on material change
Effective date 1 June 2022
Confidential — Data Protection Office. Compliance with this Policy is mandatory.
