CONFIDENTIAL — Project Atlas — DR-056 — VISTAPORT MEDIA INC. — Subject to NDA & clean-team protocol. Page 1

Accounts Service Architecture
VISTAPORT MEDIA INC. — Product Data and Technology
Document ID DR-056
Prepared by / owner Nina Petrov
Date 15 September 2025
Classification Strictly Confidential — Project Atlas
Function Security / Platform Engineering
Doc type Architecture reference

This document describes the architecture of Vistaprot's authentication, session and account services as at the date
of writing. It is an engineering reference for the Platform team and is used for onboarding and change review. It
does not describe any incident.

1. Component overview
Component Responsibility

VPAuth Authentication and session-token service; issues and validates session cookies signed with the active
signing key set.

SSOBridge Single sign-on federation across Vistaprot properties; relies on VPAuth for the authenticated-user
assertion.
AtlasID Identity graph and cross-property account linkage / match service.
legacy_uap Legacy Unified Account Profile store (pre-2022 identity/profile data); feeds remaining linked attributes
into AtlasID; scheduled for decommission.
Snowcap Analytics warehouse holding auth and engagement event tables.

2. Authentication & session flow

1 A user authenticates against VPAuth, which verifies the credential against the account store.
2 VPAuth issues a session cookie signed with the current signing key. Each signed cookie carries a key
identifier (kid) so that validators know which key to use.
3 Properties and SSOBridge validate the session cookie's signature on each request; a valid signature
establishes the authenticated session.

4 Identity resolution for personalisation and addressability is performed by AtlasID using the authenticated-user
key.

3. Session-cookie signing and key management
Session cookies are signed using an HMAC/asymmetric signing key referenced by a key identifier (kid). The
validator trusts any cookie whose signature verifies against a key in the active key set. The active set is intended to
include the current key plus, for backward compatibility during migrations, one or more legacy keys.
Key id (kid) Role Rotation policy Notes
vpauth-current Active signing key Rotate every 12 months Primary key for newly issued cookies
vpauth-legacy-2019 Legacy validation key (NOT
used to sign new cookies)
Overdue — unrotated since 2019 Retained in the active set for backward
compatibility only; pending
rotation/retirement
vpauth-mobile Mobile session key Rotate every 12 months Mobile clients

Component | Responsibility

VPAuth | Authentication and session-token service; issues and validates session cookies signed with the active
signing key set.

SSOBridge | Single sign-on federation across Vistaprot properties; relies on VPAuth for the authenticated-user
assertion.

AtlasID | Identity graph and cross-property account linkage / match service.

legacy_uap | Legacy Unified Account Profile store (pre-2022 identity/profile data); feeds remaining linked attributes
into AtlasID; scheduled for decommission.

Snowcap | Analytics warehouse holding auth and engagement event tables.

Key id (kid) | Role | Rotation policy | Notes

vpauth-current | Active signing key | Rotate every 12 months | Primary key for newly issued cookies

vpauth-legacy-2019 | Legacy validation key (NOT
used to sign new cookies) | Overdue — unrotated since 2019 | Retained in the active set for backward
compatibility only; pending
rotation/retirement

vpauth-mobile | Mobile session key | Rotate every 12 months | Mobile clients

CONFIDENTIAL — Project Atlas — DR-056 — VISTAPORT MEDIA INC. — Subject to NDA & clean-team protocol. Page 2

Rotation policy: signing keys should be rotated on a fixed cadence and any key retained only for backward compatibility should be
retired promptly once the dependent migration completes. Trust in a signed cookie is only as strong as the confidentiality of the
signing key referenced by its kid.
4. legacy_uap and migration

The legacy_uap store predates the current account platform and continues to feed selected attributes into AtlasID
during migration. Decommissioning legacy_uap and retiring the associated legacy signing key (kid
vpauth-legacy-2019) are tracked under the platform-health roadmap (DR-047) and the decommission plan
(DR-057).
5. Dependencies

• SSOBridge depends on VPAuth signature validation; key-set changes must be coordinated.
• AtlasID depends on legacy_uap lineage for a subset of match keys until migration completes.
• Analytics (Snowcap) ingests auth/session events for monitoring and reconciliation.
Prepared by Nina Petrov, Head of Security Engineering. Engineering reference — confidential.
