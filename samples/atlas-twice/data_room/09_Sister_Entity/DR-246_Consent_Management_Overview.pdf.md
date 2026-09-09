CONFIDENTIAL — Project Atlas — DR-053-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Consent Management — Overview
Beaconvale Media Inc. — Product Data and Technology
Document ID DR-053-SE
Prepared by / owner Grace Okafor
Date 20 November 2023
Classification Strictly Confidential — Project Atlas
Function Privacy
Status Overview

This overview describes how consent and preference signals are captured, stored and honoured across Beaconvale
properties, and the principal areas of complexity. It is intended as orientation for diligence and not as a legal
opinion.
1. Consent architecture

• A central preference and consent service records user choices for advertising, personalisation, analytics and
communications.

• Consent strings are propagated to LumenX, AtlasID and personalisation at request time.
• Withdrawal of consent is honoured across properties via the central service.
3. Consent categories

Category Basis Withdrawal mechanism
Advertising personalisation Consent / legitimate interest (region-dependent-SE) Privacy dashboard; ad settings
Cross-property-SE identity (AtlasID) Consent Privacy dashboard
Analytics & measurement Consent / legitimate interest Cookie & privacy controls
Marketing communications Consent Unsubscribe; preference centre

4. Legacy and pre-2022-SE accounts

A known area of complexity concerns legacy and pre-2022-SE accounts. Some of these accounts, whose profile data
originated in the legacy account platform, lack a modern, granular consent record because they pre-date-SE the
current consent service. For these accounts, consent is inferred from historical settings and, where required,
refreshed through re-consent-SE prompts. The migration of remaining legacy accounts onto the modern consent
model is in progress as part of platform modernisation.
6. Data-subject-SE requests

Access, deletion and objection requests are handled through a central intake with service-level-SE targets aligned to
applicable law. Requests touching legacy data may require additional lookup across the legacy store and its
remaining backups during the migration period.
7. Open items

• Complete consent-model-SE migration for remaining pre-2022-SE accounts.
• Retire historical inference logic once migration completes.
• Align retention of consent evidence with the Data Retention Policy (DR-052-SE).
Prepared by Grace Okafor, Chief Privacy Officer. For diligence orientation only.

Category | Basis | Withdrawal mechanism

Advertising personalisation | Consent / legitimate interest (region-dependent-SE) | Privacy dashboard; ad settings

Cross-property-SE identity (AtlasID) | Consent | Privacy dashboard

Analytics & measurement | Consent / legitimate interest | Cookie & privacy controls

Marketing communications | Consent | Unsubscribe; preference centre
