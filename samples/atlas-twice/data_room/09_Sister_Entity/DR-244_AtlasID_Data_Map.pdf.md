CONFIDENTIAL — Project Atlas — DR-051-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

AtlasID — Data Map
Beaconvale Media Inc. — Product Data and Technology
Document ID DR-051-SE
Prepared by / owner Grace Okafor
Date 8 December 2023
Classification Strictly Confidential — Project Atlas
Function Privacy Engineering
Scope AtlasID identity graph — production data flows

This data map documents the identity attributes that flow into the AtlasID identity graph, their sources, sensitivity
and downstream consumers. It is maintained by Privacy Engineering and used for records-of-processing-SE and
data-protection-SE impact assessments. It is descriptive of current production data flows.

1. Source systems

• AtlasID — current identity graph and cross-property-SE account linkage and match service.
•
legacy_uap-SE — legacy Unified Account Profile store holding pre-2022-SE identity/profile-SE data; scheduled for
decommission. Selected attributes from legacy_uap-SE have historically been migrated into, and continue to feed,
AtlasID linkage.

• VPAuth / SSOBridge — authentication and single sign-on-SE, providing the authenticated-user-SE key used to
resolve identities.

3. legacy_uap-SE attribute inventory

The legacy_uap-SE store contains the following account-profile-SE attributes. Several are directly linked into AtlasID for
matching and addressability (see consumer column).
Attribute Sensitivity Feeds AtlasID
matching?
Downstream consumer

Names Personal data Yes AtlasID linkage; ad addressability
Usernames Personal data Yes AtlasID linkage; SSOBridge
Email addresses Personal data Yes AtlasID match key; ad addressability
Recovery email addresses Personal data Yes AtlasID match key (secondary)
Phone numbers Personal data Yes AtlasID match key; ad addressability
Dates of birth Personal data Partial Age-gating-SE; segment eligibility
Salted password hashes Credential (hashed) No Authentication only (VPAuth)
Security-question-SE data Credential / sensitive No Account recovery only

Password hashes and security-question-SE data are credential material used for authentication and recovery only; they are not used for
matching or addressability.

4. Why legacy_uap-SE matters to current value

Although legacy_uap-SE is a legacy store earmarked for decommission, a meaningful share of AtlasID match keys
(email, recovery email and phone) trace their lineage to legacy_uap-SE records. These keys underpin logged-in-SE
addressability and personalisation. The integrity and confidentiality of legacy_uap-SE data therefore remains relevant
to the current identity graph and to ad addressability until the migration and decommission are complete.

6. Downstream consumers of AtlasID

Attribute | Sensitivity | Feeds AtlasID
matching? | Downstream consumer

Names | Personal data | Yes | AtlasID linkage; ad addressability

Usernames | Personal data | Yes | AtlasID linkage; SSOBridge

Email addresses | Personal data | Yes | AtlasID match key; ad addressability

Recovery email addresses | Personal data | Yes | AtlasID match key (secondary)

Phone numbers | Personal data | Yes | AtlasID match key; ad addressability

Dates of birth | Personal data | Partial | Age-gating-SE; segment eligibility

Salted password hashes | Credential (hashed) | No | Authentication only (VPAuth)

Security-question-SE data | Credential / sensitive | No | Account recovery only

CONFIDENTIAL — Project Atlas — DR-051-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

• LumenX Ad Exchange — addressable audience resolution and segment eligibility.
• Personalisation models — logged-in-SE identity match and content/ad-SE ranking.
• VistaMail and content properties — cross-property-SE single-view-SE and preferences.
7. Governance

Attribute-level-SE retention, consent and minimisation are governed by the Data Retention & Deletion Policy (DR-052-SE)
and the Consent Management framework (DR-053-SE). Migration of remaining linked attributes out of legacy_uap-SE is
tracked under the decommission plan (DR-057-SE).
Maintained by Grace Okafor, Chief Privacy Officer. Confidential — Privacy Engineering.
