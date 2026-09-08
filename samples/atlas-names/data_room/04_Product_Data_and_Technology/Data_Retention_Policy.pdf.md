CONFIDENTIAL — Project Atlas — DR-052 — Vista Port Media Inc. — Subject to NDA & clean-team protocol. Page 1

Data Retention & Deletion Policy
Vista Port Media Inc. — Product Data and Technology
Document ID DR-052
Prepared by / owner Okafor, Grace
Date 1 June 2024
Classification Strictly Confidential — Project Atlas
Policy ref DPO-RET-01
Status Approved

This Data Retention & Deletion Policy (the “Policy”) establishes the maximum retention periods for categories of
data held by Vista Port Media Inc. and its subsidiaries, and the controls for secure deletion, tokenisation and
anonymisation. It applies to all production systems, analytics stores and backups.

1. Purpose and scope

The Policy implements data-minimisation and storage-limitation principles. It applies to personal data and
account-profile data across all properties, including primary stores, the Snowcap analytics warehouse and all
backup media.

2. Retention periods
Data category Maximum retention Action on expiry
Active account profile data Life of account + 24 months Delete or anonymise
Account backups & snapshots 36 months from creation Delete, or tokenise / anonymise
Authentication & session logs 13 months Delete
Security-question / recovery data Life of account Delete on closure
Marketing & engagement analytics 25 months Aggregate or delete
Financial & tax records Per statutory requirement Retain then delete

Where deletion is not technically feasible within the period, data must be tokenised or irreversibly anonymised, and an exception
must be logged and approved by the Data Protection Office.

3. Backups and snapshots

Account backups and snapshots must not be retained for more than 36 months from the date of creation.
On reaching the limit, backups must be securely deleted, or where retention is genuinely required, the
personal-data fields must be tokenised or anonymised so that the backup no longer constitutes an identifiable
personal-data store. Backup retention beyond the limit requires a documented, time-bound exception approved by
the Data Protection Office and Security.

4. Secure deletion standard

• Cryptographic erasure (key destruction) is the preferred method for encrypted media.
• Object-store deletions must remove all versions and disable soft-delete recovery.
• Deletion must be evidenced in a disposal record retained for audit.

5. Exceptions and legal hold

Legal hold overrides scheduled deletion for data within the scope of the hold. All exceptions, including
over-retention pending a decommission, must be registered, owned, and given a target disposal date. Exceptions

Data category | Maximum retention | Action on expiry

Active account profile data | Life of account + 24 months | Delete or anonymise

Account backups & snapshots | 36 months from creation | Delete, or tokenise / anonymise

Authentication & session logs | 13 months | Delete

Security-question / recovery data | Life of account | Delete on closure

Marketing & engagement analytics | 25 months | Aggregate or delete

Financial & tax records | Per statutory requirement | Retain then delete

CONFIDENTIAL — Project Atlas — DR-052 — Vista Port Media Inc. — Subject to NDA & clean-team protocol. Page 2

are reviewed quarterly by the Data Protection Office.
6. Roles and review
Policy owner Okafor, Grace, Chief Privacy Officer
Approver P. Raman, General Counsel
Review cycle Annual, or on material change
Effective date 1 June 2024
Confidential — Data Protection Office. Compliance with this Policy is mandatory.
