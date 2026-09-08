CONFIDENTIAL — Project Atlas — DR-051 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 1

AtlasID — Data Map
VistaPort Media Inc. — Product Data and Technology
Document ID DR-051
Prepared by / owner Grace Okafor
Date 8 December 2025
Classification Strictly Confidential — Project Atlas
Function Privacy Engineering
Scope AtlasID identity graph — production data flows

This data map documents the identity attributes that flow into the AtlasID identity graph, their sources, sensitivity
and downstream consumers. It is maintained by Privacy Engineering and used for records-of-processing and
data-protection impact assessments. It is descriptive of current production data flows.

1. Source systems

• AtlasID — current identity graph and cross-property account linkage and match service.
•
legacy_uap — legacy Unified Account Profile store holding pre-2022 identity/profile data; scheduled for
decommission. Selected attributes from legacy_uap have historically been migrated into, and continue to feed,
AtlasID linkage.

• VPAuth / SSOBridge — authentication and single sign-on, providing the authenticated-user key used to
resolve identities.

2. legacy_uap attribute inventory

The legacy_uap store contains the following account-profile attributes. Several are directly linked into AtlasID for
matching and addressability (see consumer column).
Attribute Sensitivity Feeds AtlasID
matching?
Downstream consumer

Names Personal data Yes AtlasID linkage; ad addressability
Usernames Personal data Yes AtlasID linkage; SSOBridge
Email addresses Personal data Yes AtlasID match key; ad addressability
Recovery email addresses Personal data Yes AtlasID match key (secondary)
Phone numbers Personal data Yes AtlasID match key; ad addressability
Dates of birth Personal data Partial Age-gating; segment eligibility
Salted password hashes Credential (hashed) No Authentication only (VPAuth)
Security-question data Credential / sensitive No Account recovery only

Password hashes and security-question data are credential material used for authentication and recovery only; they are not used for
matching or addressability.

3. Why legacy_uap matters to current value

Although legacy_uap is a legacy store earmarked for decommission, a meaningful share of AtlasID match keys
(email, recovery email and phone) trace their lineage to legacy_uap records. These keys underpin logged-in
addressability and personalisation. The integrity and confidentiality of legacy_uap data therefore remains relevant
to the current identity graph and to ad addressability until the migration and decommission are complete.

4. Downstream consumers of AtlasID

Attribute | Sensitivity | Feeds AtlasID
matching? | Downstream consumer

Names | Personal data | Yes | AtlasID linkage; ad addressability

Usernames | Personal data | Yes | AtlasID linkage; SSOBridge

Email addresses | Personal data | Yes | AtlasID match key; ad addressability

Recovery email addresses | Personal data | Yes | AtlasID match key (secondary)

Phone numbers | Personal data | Yes | AtlasID match key; ad addressability

Dates of birth | Personal data | Partial | Age-gating; segment eligibility

Salted password hashes | Credential (hashed) | No | Authentication only (VPAuth)

Security-question data | Credential / sensitive | No | Account recovery only

CONFIDENTIAL — Project Atlas — DR-051 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 2

• LumenX Ad Exchange — addressable audience resolution and segment eligibility.
• Personalisation models — logged-in identity match and content/ad ranking.
• VistaMail and content properties — cross-property single-view and preferences.
5. Governance

Attribute-level retention, consent and minimisation are governed by the Data Retention & Deletion Policy (DR-052)
and the Consent Management framework (DR-053). Migration of remaining linked attributes out of legacy_uap is
tracked under the decommission plan (DR-057).
Maintained by Grace Okafor, Chief Privacy Officer. Confidential — Privacy Engineering.
