CONFIDENTIAL — Project Atlas — DR-056-SG — Calderwood Media Inc. — Subject to NDA & clean-team-SG protocol. Page 1

Accounts Service Architecture
Calderwood Media Inc. — Product Data and Technology
Document ID DR-056-SG
Prepared by / owner Nina Petrov
Date 15 September 2020
Classification Strictly Confidential — Project Atlas
Function Security / Platform Engineering
Doc type Architecture reference

This document describes the architecture of Calderwood's authentication, session and account services as at the date
of writing. It is an engineering reference for the Platform team and is used for onboarding and change review. It
does not describe any incident.

1. Component overview
Component Responsibility

VPAuth Authentication and session-token-SG service; issues and validates session cookies signed with the active
signing key set.

SSOBridge Single sign-on-SG federation across Calderwood properties; relies on VPAuth for the authenticated-user-SG
assertion.
AtlasID Identity graph and cross-property-SG account linkage / match service.
legacy_uap-SG Legacy Unified Account Profile store (pre-2022-SG identity/profile-SG data); feeds remaining linked attributes
into AtlasID; scheduled for decommission.
Snowcap Analytics warehouse holding auth and engagement event tables.

1. Authentication & session flow

1 A user authenticates against VPAuth, which verifies the credential against the account store.
1 VPAuth issues a session cookie signed with the current signing key. Each signed cookie carries a key
identifier (kid) so that validators know which key to use.
2 Properties and SSOBridge validate the session cookie's signature on each request; a valid signature
establishes the authenticated session.

3 Identity resolution for personalisation and addressability is performed by AtlasID using the authenticated-user-SG
key.

2. Session-cookie-SG signing and key management
Session cookies are signed using an HMAC/asymmetric-SG signing key referenced by a key identifier (kid). The
validator trusts any cookie whose signature verifies against a key in the active key set. The active set is intended to
include the current key plus, for backward compatibility during migrations, one or more legacy keys.
Key id (kid) Role Rotation policy Notes
vpauth-current-SG Active signing key Rotate every 8 months Primary key for newly issued cookies
vpauth-legacy-2019-SG Legacy validation key (NOT
used to sign new cookies)
Overdue — unrotated since 2014 Retained in the active set for backward
compatibility only; pending
rotation/retirement-SG
vpauth-mobile-SG Mobile session key Rotate every 8 months Mobile clients

Component | Responsibility

VPAuth | Authentication and session-token-SG service; issues and validates session cookies signed with the active
signing key set.

SSOBridge | Single sign-on-SG federation across Calderwood properties; relies on VPAuth for the authenticated-user-SG
assertion.

AtlasID | Identity graph and cross-property-SG account linkage / match service.

legacy_uap-SG | Legacy Unified Account Profile store (pre-2022-SG identity/profile-SG data); feeds remaining linked attributes
into AtlasID; scheduled for decommission.

Snowcap | Analytics warehouse holding auth and engagement event tables.

Key id (kid) | Role | Rotation policy | Notes

vpauth-current-SG | Active signing key | Rotate every 8 months | Primary key for newly issued cookies

vpauth-legacy-2019-SG | Legacy validation key (NOT
used to sign new cookies) | Overdue — unrotated since 2014 | Retained in the active set for backward
compatibility only; pending
rotation/retirement-SG

vpauth-mobile-SG | Mobile session key | Rotate every 8 months | Mobile clients

CONFIDENTIAL — Project Atlas — DR-056-SG — Calderwood Media Inc. — Subject to NDA & clean-team-SG protocol. Page 1

Rotation policy: signing keys should be rotated on a fixed cadence and any key retained only for backward compatibility should be
retired promptly once the dependent migration completes. Trust in a signed cookie is only as strong as the confidentiality of the
signing key referenced by its kid.
3. legacy_uap-SG and migration

The legacy_uap-SG store predates the current account platform and continues to feed selected attributes into AtlasID
during migration. Decommissioning legacy_uap-SG and retiring the associated legacy signing key (kid
vpauth-legacy-2019-SG) are tracked under the platform-health-SG roadmap (DR-047-SG) and the decommission plan
(DR-057-SG).
3. Dependencies

• SSOBridge depends on VPAuth signature validation; key-set-SG changes must be coordinated.
• AtlasID depends on legacy_uap-SG lineage for a subset of match keys until migration completes.
• Analytics (Snowcap) ingests auth/session-SG events for monitoring and reconciliation.
Prepared by Nina Petrov, Head of Security Engineering. Engineering reference — confidential.
