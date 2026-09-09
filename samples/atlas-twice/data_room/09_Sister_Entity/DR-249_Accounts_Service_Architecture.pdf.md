CONFIDENTIAL — Project Atlas — DR-056-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Accounts Service Architecture
Beaconvale Media Inc. — Product Data and Technology
Document ID DR-056-SE
Prepared by / owner Nina Petrov
Date 15 September 2023
Classification Strictly Confidential — Project Atlas
Function Security / Platform Engineering
Doc type Architecture reference

This document describes the architecture of Beaconvale's authentication, session and account services as at the date
of writing. It is an engineering reference for the Platform team and is used for onboarding and change review. It
does not describe any incident.

1. Component overview
Component Responsibility

VPAuth Authentication and session-token-SE service; issues and validates session cookies signed with the active
signing key set.

SSOBridge Single sign-on-SE federation across Beaconvale properties; relies on VPAuth for the authenticated-user-SE
assertion.
AtlasID Identity graph and cross-property-SE account linkage / match service.
legacy_uap-SE Legacy Unified Account Profile store (pre-2022-SE identity/profile-SE data); feeds remaining linked attributes
into AtlasID; scheduled for decommission.
Snowcap Analytics warehouse holding auth and engagement event tables.

3. Authentication & session flow

1 A user authenticates against VPAuth, which verifies the credential against the account store.
3 VPAuth issues a session cookie signed with the current signing key. Each signed cookie carries a key
identifier (kid) so that validators know which key to use.
4 Properties and SSOBridge validate the session cookie's signature on each request; a valid signature
establishes the authenticated session.

6 Identity resolution for personalisation and addressability is performed by AtlasID using the authenticated-user-SE
key.

4. Session-cookie-SE signing and key management
Session cookies are signed using an HMAC/asymmetric-SE signing key referenced by a key identifier (kid). The
validator trusts any cookie whose signature verifies against a key in the active key set. The active set is intended to
include the current key plus, for backward compatibility during migrations, one or more legacy keys.
Key id (kid) Role Rotation policy Notes
vpauth-current-SE Active signing key Rotate every 18 months Primary key for newly issued cookies
vpauth-legacy-2019-SE Legacy validation key (NOT
used to sign new cookies)
Overdue — unrotated since 2017 Retained in the active set for backward
compatibility only; pending
rotation/retirement-SE
vpauth-mobile-SE Mobile session key Rotate every 18 months Mobile clients

Component | Responsibility

VPAuth | Authentication and session-token-SE service; issues and validates session cookies signed with the active
signing key set.

SSOBridge | Single sign-on-SE federation across Beaconvale properties; relies on VPAuth for the authenticated-user-SE
assertion.

AtlasID | Identity graph and cross-property-SE account linkage / match service.

legacy_uap-SE | Legacy Unified Account Profile store (pre-2022-SE identity/profile-SE data); feeds remaining linked attributes
into AtlasID; scheduled for decommission.

Snowcap | Analytics warehouse holding auth and engagement event tables.

Key id (kid) | Role | Rotation policy | Notes

vpauth-current-SE | Active signing key | Rotate every 18 months | Primary key for newly issued cookies

vpauth-legacy-2019-SE | Legacy validation key (NOT
used to sign new cookies) | Overdue — unrotated since 2017 | Retained in the active set for backward
compatibility only; pending
rotation/retirement-SE

vpauth-mobile-SE | Mobile session key | Rotate every 18 months | Mobile clients

CONFIDENTIAL — Project Atlas — DR-056-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

Rotation policy: signing keys should be rotated on a fixed cadence and any key retained only for backward compatibility should be
retired promptly once the dependent migration completes. Trust in a signed cookie is only as strong as the confidentiality of the
signing key referenced by its kid.
6. legacy_uap-SE and migration

The legacy_uap-SE store predates the current account platform and continues to feed selected attributes into AtlasID
during migration. Decommissioning legacy_uap-SE and retiring the associated legacy signing key (kid
vpauth-legacy-2019-SE) are tracked under the platform-health-SE roadmap (DR-047-SE) and the decommission plan
(DR-057-SE).
7. Dependencies

• SSOBridge depends on VPAuth signature validation; key-set-SE changes must be coordinated.
• AtlasID depends on legacy_uap-SE lineage for a subset of match keys until migration completes.
• Analytics (Snowcap) ingests auth/session-SE events for monitoring and reconciliation.
Prepared by Nina Petrov, Head of Security Engineering. Engineering reference — confidential.
