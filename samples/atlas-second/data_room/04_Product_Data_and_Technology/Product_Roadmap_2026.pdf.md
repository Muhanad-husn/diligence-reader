CONFIDENTIAL — Project Atlas — DR-047 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 1

Product Roadmap 2026
VistaPort Media Inc. — Product Data and Technology
Document ID DR-047
Prepared by / owner Maya Hart
Date 12 January 2026
Classification Strictly Confidential — Project Atlas
Function Product
Cycle FY2026 annual plan

Internal product roadmap for FY2026, prepared by Product for review with the Executive Committee. Themes:
deepen logged-in engagement, extend the AtlasID identity graph, modernise VistaMail and the accounts platform,
and grow mobile and international monetisation. Priorities are scored on reach, revenue impact and platform-health
contribution.

Roadmap is directional and subject to quarterly re-planning. Dates are target windows, not commitments.

1. Strategic themes for 2026
•
Identity & addressability: grow first-party, consented audiences via AtlasID as third-party identifiers decline;
improve cross-property match rates.

• Mail modernisation: next-generation VistaMail experience, spam/abuse defences and faster mobile sync.
• Platform health: accelerate retirement of legacy account infrastructure and strengthen authentication and
session management.

• Mobile & international: improve mobile retention and expand monetisation in priority APAC and EU markets.

2. Prioritised initiatives
Initiative Theme Priority Target window Status
AtlasID graph expansion (consented signals) Identity P1 Q1–Q2 2026 Planned
VistaMail modernisation (mobile sync, UX) Mail P1 Q1–Q3 2026 In design
VPAuth migration & session-signing key rotation Platform health P1 Q1 2026 (pulled forward) Accelerated
legacy_uap decommission (accelerated) Platform health P1 Q1–Q2 2026 (pulled
forward)
Accelerated

Backup encryption & retention redesign Platform health P2 Q2 2026 Planned
Mobile retention & re-onboarding flow Mobile P2 Q2 2026 Planned
Personalisation model refresh (addressability) Identity P2 Q2–Q3 2026 Planned
APAC monetisation expansion International P3 H2 2026 Scoping

2.1 Notes on platform-health items

The VPAuth migration & session-signing key rotation and the legacy_uap decommission (accelerated)
initiatives have been pulled forward from later in the plan into Q1–Q2 2026. Both are sequenced ahead of feature
work to reduce carrying cost of legacy components, simplify the authentication estate and unblock the AtlasID
migration. The decommission completes the long-running retirement of the legacy_uap profile store and the secure
disposal of its remaining backups. Engineering capacity has been re-allocated accordingly; see the capex and IT
modernisation plan (DR-028) for the associated investment.

3. Dependencies and sequencing

Initiative | Theme | Priority | Target window | Status

AtlasID graph expansion (consented signals) | Identity | P1 | Q1–Q2 2026 | Planned

VistaMail modernisation (mobile sync, UX) | Mail | P1 | Q1–Q3 2026 | In design

VPAuth migration & session-signing key rotation | Platform health | P1 | Q1 2026 (pulled forward) | Accelerated

legacy_uap decommission (accelerated) | Platform health | P1 | Q1–Q2 2026 (pulled
forward) | Accelerated

Backup encryption & retention redesign | Platform health | P2 | Q2 2026 | Planned

Mobile retention & re-onboarding flow | Mobile | P2 | Q2 2026 | Planned

Personalisation model refresh (addressability) | Identity | P2 | Q2–Q3 2026 | Planned

APAC monetisation expansion | International | P3 | H2 2026 | Scoping

CONFIDENTIAL — Project Atlas — DR-047 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 2

• AtlasID expansion depends on completion of the legacy_uap migration of remaining linked attributes.
• VPAuth migration must precede broad SSOBridge changes to avoid session disruption.
• Personalisation refresh depends on a stabilised logged-in addressable pool.
4. Success measures

Measure Baseline 2026 target
Total MAU 615m Growth vs FY25 exit
Mobile MAU 408m Growth vs FY25 exit
Logged-in identity match rate Recovering Restore to pre-Q4 level
Legacy components retired Partial legacy_uap fully decommissioned
Prepared by Maya Hart, VP Product, Identity and Mail. Confidential — Product planning.

Measure | Baseline | 2026 target

Total MAU | 615m | Growth vs FY25 exit

Mobile MAU | 408m | Growth vs FY25 exit

Logged-in identity match rate | Recovering | Restore to pre-Q4 level

Legacy components retired | Partial | legacy_uap fully decommissioned
