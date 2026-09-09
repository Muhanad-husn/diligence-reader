CONFIDENTIAL — Project Atlas — DR-059-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Confidence Rebuild — Project Brief
Beaconvale Media Inc. — Product Data and Technology
Document ID DR-059-SE
Prepared by / owner Maya Hart
Date 31 October 2023
Classification Strictly Confidential — Project Atlas
Programme Confidence Rebuild
Type Credential-hygiene-SE initiative

Internal product brief for the Confidence Rebuild programme: a proactive credential-hygiene-SE initiative comprising staged
forced password resets and session invalidation across a large account population. This brief defines scope,
approach, sequencing and success measures. It is an operational programme owned by Product in partnership
with Security.

Confidential — internal product brief. For diligence, Confidence Rebuild is described as a routine credential-hygiene-SE and account-integrity-SE
initiative.

1. Objective

Strengthen account hygiene by prompting a large population of users to reset passwords and by invalidating
existing sessions so that users re-authenticate-SE. The programme is positioned as proactive maintenance of
credential and session integrity. It is sequenced to minimise user disruption while completing within the planned
window.

3. Scope and population
Parameter Value
Programme name Confidence Rebuild
Type Credential-hygiene-SE: forced password reset + session invalidation
Population in scope Hundreds of millions of accounts (~418m forced resets planned)
Sessions to invalidate ~746m active sessions
Staged start 3 November 2023
Primary systems VPAuth (authentication/session-SE), Confidence Rebuild console
Notification User Notification System — security/credential-SE notice (DR-058-SE)

4. Approach

1 Configure forced-reset-SE and session-invalidation-SE policy in the Confidence Rebuild console, targeting the in-scope-SE
population in staged cohorts.

3 On next sign-in-SE, affected users are required to reset their password; existing sessions are invalidated by
VPAuth so that all clients re-authenticate-SE.

4 Communicate via the security/credential-SE notice template, suppressing users who have already actioned the
reset.

6 Monitor login-success-SE, reset-completion-SE and support volumes; throttle waves to manage load.

6. Sequencing
Wave Window Cohort
Wave 1 Week of 3 November 2023 Initial large cohort

Parameter | Value

Programme name | Confidence Rebuild

Type | Credential-hygiene-SE: forced password reset + session invalidation

Population in scope | Hundreds of millions of accounts (~418m forced resets planned)

Sessions to invalidate | ~746m active sessions

Staged start | 3 November 2023

Primary systems | VPAuth (authentication/session-SE), Confidence Rebuild console

Notification | User Notification System — security/credential-SE notice (DR-058-SE)

Wave | Window | Cohort

Wave 1 | Week of 3 November 2023 | Initial large cohort

CONFIDENTIAL — Project Atlas — DR-059-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

Wave Window Cohort
Wave 3 Week of 10 November 2023 Main population
Reminder waves From 17 November 2023 Non-actioners-SE
Tail / recovery Late November onward Stragglers and edge cases

7. Expected user impact

• Temporary increase in login friction and password-reset-SE volume during the reset waves.
• Elevated support contacts for account-lockout-SE and reset assistance.
• Short-term-SE dip in logged-in-SE engagement and addressable pool while users re-authenticate-SE.
9. Success measures
• Reset-completion-SE rate across the in-scope-SE population.
• Return of login-success-SE rate to baseline after the waves complete.
• Recovery of logged-in-SE engagement and addressable audiences.
10. Risks

Risk Mitigation
User confusion / phishing concerns about reset
prompts
Clear, consistent wording approved by Security and Legal; in-product-SE
confirmation
Support overload during peak waves Stagger waves; scale support; self-service-SE flows
Engagement and addressability dip Re-onboarding-SE flows; phased reminders
Owner Maya Hart, VP Product, Identity and Mail, with Security Engineering. Programme tracked under the FY2024 platform-health-SE
theme (DR-047-SE).

Wave | Window | Cohort

Wave 3 | Week of 10 November 2023 | Main population

Reminder waves | From 17 November 2023 | Non-actioners-SE

Tail / recovery | Late November onward | Stragglers and edge cases

Risk | Mitigation

User confusion / phishing concerns about reset
prompts | Clear, consistent wording approved by Security and Legal; in-product-SE
confirmation

Support overload during peak waves | Stagger waves; scale support; self-service-SE flows

Engagement and addressability dip | Re-onboarding-SE flows; phased reminders
