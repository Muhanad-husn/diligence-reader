CONFIDENTIAL — Project Atlas — DR-053 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 1

Consent Management — Overview
VistaPort Media Inc. — Product Data and Technology
Document ID DR-053
Prepared by / owner Grace Okafor
Date 20 November 2025
Classification Strictly Confidential — Project Atlas
Function Privacy
Status Overview

This overview describes how consent and preference signals are captured, stored and honoured across VistaPort
properties, and the principal areas of complexity. It is intended as orientation for diligence and not as a legal
opinion.
1. Consent architecture

• A central preference and consent service records user choices for advertising, personalisation, analytics and
communications.

• Consent strings are propagated to LumenX, AtlasID and personalisation at request time.
• Withdrawal of consent is honoured across properties via the central service.
2. Consent categories

Category Basis Withdrawal mechanism
Advertising personalisation Consent / legitimate interest (region-dependent) Privacy dashboard; ad settings
Cross-property identity (AtlasID) Consent Privacy dashboard
Analytics & measurement Consent / legitimate interest Cookie & privacy controls
Marketing communications Consent Unsubscribe; preference centre

3. Legacy and pre-2022 accounts

A known area of complexity concerns legacy and pre-2022 accounts. Some of these accounts, whose profile data
originated in the legacy account platform, lack a modern, granular consent record because they pre-date the
current consent service. For these accounts, consent is inferred from historical settings and, where required,
refreshed through re-consent prompts. The migration of remaining legacy accounts onto the modern consent
model is in progress as part of platform modernisation.
4. Data-subject requests

Access, deletion and objection requests are handled through a central intake with service-level targets aligned to
applicable law. Requests touching legacy data may require additional lookup across the legacy store and its
remaining backups during the migration period.
5. Open items

• Complete consent-model migration for remaining pre-2022 accounts.
• Retire historical inference logic once migration completes.
• Align retention of consent evidence with the Data Retention Policy (DR-052).
Prepared by Grace Okafor, Chief Privacy Officer. For diligence orientation only.

Category | Basis | Withdrawal mechanism

Advertising personalisation | Consent / legitimate interest (region-dependent) | Privacy dashboard; ad settings

Cross-property identity (AtlasID) | Consent | Privacy dashboard

Analytics & measurement | Consent / legitimate interest | Cookie & privacy controls

Marketing communications | Consent | Unsubscribe; preference centre
