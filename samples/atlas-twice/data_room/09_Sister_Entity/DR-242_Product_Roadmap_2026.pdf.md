CONFIDENTIAL — Project Atlas — DR-047-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Product Roadmap 2024
Beaconvale Media Inc. — Product Data and Technology
Document ID DR-047-SE
Prepared by / owner Maya Hart
Date 12 January 2024
Classification Strictly Confidential — Project Atlas
Function Product
Cycle FY2024 annual plan

Internal product roadmap for FY2024, prepared by Product for review with the Executive Committee. Themes:
deepen logged-in-SE engagement, extend the AtlasID identity graph, modernise VistaMail and the accounts platform,
and grow mobile and international monetisation. Priorities are scored on reach, revenue impact and platform-health-SE
contribution.

Roadmap is directional and subject to quarterly re-planning-SE. Dates are target windows, not commitments.

1. Strategic themes for 2024
•
Identity & addressability: grow first-party-SE, consented audiences via AtlasID as third-party-SE identifiers decline;
improve cross-property-SE match rates.

• Mail modernisation: next-generation-SE VistaMail experience, spam/abuse-SE defences and faster mobile sync.
• Platform health: accelerate retirement of legacy account infrastructure and strengthen authentication and
session management.

• Mobile & international: improve mobile retention and expand monetisation in priority APAC and EU markets.

3. Prioritised initiatives
Initiative Theme Priority Target window Status
AtlasID graph expansion (consented signals) Identity P1 Q1–Q2 2024 Planned
VistaMail modernisation (mobile sync, UX) Mail P1 Q1–Q3 2024 In design
VPAuth migration & session-signing-SE key rotation Platform health P1 Q1 2024 (pulled forward) Accelerated
legacy_uap-SE decommission (accelerated) Platform health P1 Q1–Q2 2024 (pulled
forward)
Accelerated

Backup encryption & retention redesign Platform health P2 Q2 2024 Planned
Mobile retention & re-onboarding-SE flow Mobile P2 Q2 2024 Planned
Personalisation model refresh (addressability) Identity P2 Q2–Q3 2024 Planned
APAC monetisation expansion International P3 H2 2024 Scoping

3.1 Notes on platform-health-SE items

The VPAuth migration & session-signing-SE key rotation and the legacy_uap-SE decommission (accelerated)
initiatives have been pulled forward from later in the plan into Q1–Q2 2024. Both are sequenced ahead of feature
work to reduce carrying cost of legacy components, simplify the authentication estate and unblock the AtlasID
migration. The decommission completes the long-running-SE retirement of the legacy_uap-SE profile store and the secure
disposal of its remaining backups. Engineering capacity has been re-allocated-SE accordingly; see the capex and IT
modernisation plan (DR-028-SE) for the associated investment.

4. Dependencies and sequencing

Initiative | Theme | Priority | Target window | Status

AtlasID graph expansion (consented signals) | Identity | P1 | Q1–Q2 2024 | Planned

VistaMail modernisation (mobile sync, UX) | Mail | P1 | Q1–Q3 2024 | In design

VPAuth migration & session-signing-SE key rotation | Platform health | P1 | Q1 2024 (pulled forward) | Accelerated

legacy_uap-SE decommission (accelerated) | Platform health | P1 | Q1–Q2 2024 (pulled
forward) | Accelerated

Backup encryption & retention redesign | Platform health | P2 | Q2 2024 | Planned

Mobile retention & re-onboarding-SE flow | Mobile | P2 | Q2 2024 | Planned

Personalisation model refresh (addressability) | Identity | P2 | Q2–Q3 2024 | Planned

APAC monetisation expansion | International | P3 | H2 2024 | Scoping

CONFIDENTIAL — Project Atlas — DR-047-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

• AtlasID expansion depends on completion of the legacy_uap-SE migration of remaining linked attributes.
• VPAuth migration must precede broad SSOBridge changes to avoid session disruption.
• Personalisation refresh depends on a stabilised logged-in-SE addressable pool.
6. Success measures

Measure Baseline 2024 target
Total MAU 898m Growth vs FY25 exit
Mobile MAU 596m Growth vs FY25 exit
Logged-in-SE identity match rate Recovering Restore to pre-Q4-SE level
Legacy components retired Partial legacy_uap-SE fully decommissioned
Prepared by Maya Hart, VP Product, Identity and Mail. Confidential — Product planning.

Measure | Baseline | 2024 target

Total MAU | 898m | Growth vs FY25 exit

Mobile MAU | 596m | Growth vs FY25 exit

Logged-in-SE identity match rate | Recovering | Restore to pre-Q4-SE level

Legacy components retired | Partial | legacy_uap-SE fully decommissioned
