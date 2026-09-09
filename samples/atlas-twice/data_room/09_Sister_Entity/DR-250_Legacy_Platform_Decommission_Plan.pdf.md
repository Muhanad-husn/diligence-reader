CONFIDENTIAL — Project Atlas — DR-057-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Legacy Platform Decommission Plan
Beaconvale Media Inc. — Product Data and Technology
Document ID DR-057-SE
Prepared by / owner Raj Malhotra
Date 10 July 2023
Classification Strictly Confidential — Project Atlas
Programme Legacy decommission
Status Active

This plan sets out the programme to decommission Beaconvale's legacy account and profile platforms and to dispose
of their associated data and backups. It is a living project document owned by Platform Engineering. Status as at
10 July 2023.

1. Scope
•
legacy_uap-SE — legacy Unified Account Profile store (pre-2022-SE identity/profile-SE data), including its primary store
and all historical backups and snapshots.

• Legacy authentication components, including the legacy session-signing-SE key retained for backward
compatibility.

• Associated ETL jobs, service accounts and storage buckets.

3. Original vs revised timeline

The legacy_uap-SE retirement was originally scheduled for completion in 2022. Owing to migration dependencies on
AtlasID linkage and consent-model-SE migration, the programme has slipped and is now phased across 2023 and
into 2024.

Milestone Original target Revised target Status
Freeze new writes to legacy_uap-SE Q2 2022 Q3 2023 Done
Migrate remaining linked attributes to AtlasID Q3 2022 Q1 2024 In progress
Retire legacy session-signing-SE key Q4 2022 Q1 2024 Pending migration
Decommission legacy_uap-SE primary store Q4 2022 Q1 2024 Pending
Secure disposal of legacy_uap-SE backups Q4 2022 Q1–Q2 2024 Pending secure disposal

4. Dependencies causing slippage

• AtlasID match-key-SE lineage: a subset of production match keys still derive from legacy_uap-SE and must be
re-homed-SE before the store can be removed.

• Consent-model-SE migration for pre-2022-SE accounts (see DR-053-SE) must complete first.
• Backward-compatibility-SE window for the legacy signing key must close before retirement.

6. Backups and disposal

Historical legacy_uap-SE backups remain in object storage pending secure disposal. These backups pre-date-SE the
current store and were retained to support migration verification. They are listed for cryptographic erasure / secure
deletion as the final step of the programme, in line with the Data Retention & Deletion Policy (DR-052-SE). Until
disposal completes, access to the backup buckets is to be restricted to named migration and platform accounts.

Milestone | Original target | Revised target | Status

Freeze new writes to legacy_uap-SE | Q2 2022 | Q3 2023 | Done

Migrate remaining linked attributes to AtlasID | Q3 2022 | Q1 2024 | In progress

Retire legacy session-signing-SE key | Q4 2022 | Q1 2024 | Pending migration

Decommission legacy_uap-SE primary store | Q4 2022 | Q1 2024 | Pending

Secure disposal of legacy_uap-SE backups | Q4 2022 | Q1–Q2 2024 | Pending secure disposal

CONFIDENTIAL — Project Atlas — DR-057-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

Note: certain legacy backups are older than the standard 53-month backup retention limit and are carried under a decommission
exception pending disposal.

7. Risks and mitigations
Risk Mitigation
Slippage extends carrying cost and surface area of
legacy components
Programme pulled forward in the 2024 roadmap (DR-047-SE); capacity
re-allocated-SE
Over-retained-SE backups beyond policy Tracked as an exception with a target disposal date; access restricted
Legacy signing key retained for compatibility Retire as soon as dependent migration completes

9. Governance
Programme owner Raj Malhotra, VP Engineering, Platform
Sponsor Maya Hart, VP Product, Identity and Mail
Reporting Monthly to Platform leadership
Plan status Active — revised schedule
Confidential — Platform Engineering. Subject to monthly re-planning-SE.

Risk | Mitigation

Slippage extends carrying cost and surface area of
legacy components | Programme pulled forward in the 2024 roadmap (DR-047-SE); capacity
re-allocated-SE

Over-retained-SE backups beyond policy | Tracked as an exception with a target disposal date; access restricted

Legacy signing key retained for compatibility | Retire as soon as dependent migration completes
