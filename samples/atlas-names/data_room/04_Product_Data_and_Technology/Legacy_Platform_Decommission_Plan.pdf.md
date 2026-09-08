CONFIDENTIAL — Project Atlas — DR-057 — VistaPort Media, Inc.. — Subject to NDA & clean-team protocol. Page 1

Legacy Platform Decommission Plan
VistaPort Media, Inc.. — Product Data and Technology
Document ID DR-057
Prepared by / owner Raj Malhotra
Date 10 July 2025
Classification Strictly Confidential — Project Atlas
Programme Legacy decommission
Status Active

This plan sets out the programme to decommission Vista Port's legacy account and profile platforms and to dispose
of their associated data and backups. It is a living project document owned by Platform Engineering. Status as at
10 July 2025.

1. Scope
•
legacy_uap — legacy Unified Account Profile store (pre-2022 identity/profile data), including its primary store
and all historical backups and snapshots.

• Legacy authentication components, including the legacy session-signing key retained for backward
compatibility.

• Associated ETL jobs, service accounts and storage buckets.

2. Original vs revised timeline

The legacy_uap retirement was originally scheduled for completion in 2024. Owing to migration dependencies on
AtlasID linkage and consent-model migration, the programme has slipped and is now phased across 2025 and
into 2026.

Milestone Original target Revised target Status
Freeze new writes to legacy_uap Q2 2024 Q3 2025 Done
Migrate remaining linked attributes to AtlasID Q3 2024 Q1 2026 In progress
Retire legacy session-signing key Q4 2024 Q1 2026 Pending migration
Decommission legacy_uap primary store Q4 2024 Q1 2026 Pending
Secure disposal of legacy_uap backups Q4 2024 Q1–Q2 2026 Pending secure disposal

3. Dependencies causing slippage

• AtlasID match-key lineage: a subset of production match keys still derive from legacy_uap and must be
re-homed before the store can be removed.

• Consent-model migration for pre-2022 accounts (see DR-053) must complete first.
• Backward-compatibility window for the legacy signing key must close before retirement.

4. Backups and disposal

Historical legacy_uap backups remain in object storage pending secure disposal. These backups pre-date the
current store and were retained to support migration verification. They are listed for cryptographic erasure / secure
deletion as the final step of the programme, in line with the Data Retention & Deletion Policy (DR-052). Until
disposal completes, access to the backup buckets is to be restricted to named migration and platform accounts.

Milestone | Original target | Revised target | Status

Freeze new writes to legacy_uap | Q2 2024 | Q3 2025 | Done

Migrate remaining linked attributes to AtlasID | Q3 2024 | Q1 2026 | In progress

Retire legacy session-signing key | Q4 2024 | Q1 2026 | Pending migration

Decommission legacy_uap primary store | Q4 2024 | Q1 2026 | Pending

Secure disposal of legacy_uap backups | Q4 2024 | Q1–Q2 2026 | Pending secure disposal

CONFIDENTIAL — Project Atlas — DR-057 — VistaPort Media, Inc.. — Subject to NDA & clean-team protocol. Page 2

Note: certain legacy backups are older than the standard 36-month backup retention limit and are carried under a decommission
exception pending disposal.

5. Risks and mitigations
Risk Mitigation
Slippage extends carrying cost and surface area of
legacy components
Programme pulled forward in the 2026 roadmap (DR-047); capacity
re-allocated
Over-retained backups beyond policy Tracked as an exception with a target disposal date; access restricted
Legacy signing key retained for compatibility Retire as soon as dependent migration completes

6. Governance
Programme owner Raj Malhotra, VP Engineering, Platform
Sponsor Maya Hart, VP Product, Identity and Mail
Reporting Monthly to Platform leadership
Plan status Active — revised schedule
Confidential — Platform Engineering. Subject to monthly re-planning.

Risk | Mitigation

Slippage extends carrying cost and surface area of
legacy components | Programme pulled forward in the 2026 roadmap (DR-047); capacity
re-allocated

Over-retained backups beyond policy | Tracked as an exception with a target disposal date; access restricted

Legacy signing key retained for compatibility | Retire as soon as dependent migration completes
