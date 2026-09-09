CONFIDENTIAL — Project Atlas — DR-059-SG — Calderwood Media Inc. — Subject to NDA & clean-team-SG protocol. Page 1

Loyalty Restart — Project Brief
Calderwood Media Inc. — Product Data and Technology
Document ID DR-059-SG
Prepared by / owner Maya Hart
Date 31 October 2020
Classification Strictly Confidential — Project Atlas
Programme Loyalty Restart
Type Credential-hygiene-SG initiative

Internal product brief for the Loyalty Restart programme: a proactive credential-hygiene-SG initiative comprising staged
forced password resets and session invalidation across a large account population. This brief defines scope,
approach, sequencing and success measures. It is an operational programme owned by Product in partnership
with Security.

Confidential — internal product brief. For diligence, Loyalty Restart is described as a routine credential-hygiene-SG and account-integrity-SG
initiative.

1. Objective

Strengthen account hygiene by prompting a large population of users to reset passwords and by invalidating
existing sessions so that users re-authenticate-SG. The programme is positioned as proactive maintenance of
credential and session integrity. It is sequenced to minimise user disruption while completing within the planned
window.

1. Scope and population
Parameter Value
Programme name Loyalty Restart
Type Credential-hygiene-SG: forced password reset + session invalidation
Population in scope Hundreds of millions of accounts (~183m forced resets planned)
Sessions to invalidate ~327m active sessions
Staged start 3 November 2020
Primary systems VPAuth (authentication/session-SG), Loyalty Restart console
Notification User Notification System — security/credential-SG notice (DR-058-SG)

2. Approach

1 Configure forced-reset-SG and session-invalidation-SG policy in the Loyalty Restart console, targeting the in-scope-SG
population in staged cohorts.

1 On next sign-in-SG, affected users are required to reset their password; existing sessions are invalidated by
VPAuth so that all clients re-authenticate-SG.

2 Communicate via the security/credential-SG notice template, suppressing users who have already actioned the
reset.

3 Monitor login-success-SG, reset-completion-SG and support volumes; throttle waves to manage load.

3. Sequencing
Wave Window Cohort
Wave 1 Week of 3 November 2020 Initial large cohort

Parameter | Value

Programme name | Loyalty Restart

Type | Credential-hygiene-SG: forced password reset + session invalidation

Population in scope | Hundreds of millions of accounts (~183m forced resets planned)

Sessions to invalidate | ~327m active sessions

Staged start | 3 November 2020

Primary systems | VPAuth (authentication/session-SG), Loyalty Restart console

Notification | User Notification System — security/credential-SG notice (DR-058-SG)

Wave | Window | Cohort

Wave 1 | Week of 3 November 2020 | Initial large cohort

CONFIDENTIAL — Project Atlas — DR-059-SG — Calderwood Media Inc. — Subject to NDA & clean-team-SG protocol. Page 1

Wave Window Cohort
Wave 1 Week of 10 November 2020 Main population
Reminder waves From 17 November 2020 Non-actioners-SG
Tail / recovery Late November onward Stragglers and edge cases

3. Expected user impact

• Temporary increase in login friction and password-reset-SG volume during the reset waves.
• Elevated support contacts for account-lockout-SG and reset assistance.
• Short-term-SG dip in logged-in-SG engagement and addressable pool while users re-authenticate-SG.
4. Success measures
• Reset-completion-SG rate across the in-scope-SG population.
• Return of login-success-SG rate to baseline after the waves complete.
• Recovery of logged-in-SG engagement and addressable audiences.
4. Risks

Risk Mitigation
User confusion / phishing concerns about reset
prompts
Clear, consistent wording approved by Security and Legal; in-product-SG
confirmation
Support overload during peak waves Stagger waves; scale support; self-service-SG flows
Engagement and addressability dip Re-onboarding-SG flows; phased reminders
Owner Maya Hart, VP Product, Identity and Mail, with Security Engineering. Programme tracked under the FY2021 platform-health-SG
theme (DR-047-SG).

Wave | Window | Cohort

Wave 1 | Week of 10 November 2020 | Main population

Reminder waves | From 17 November 2020 | Non-actioners-SG

Tail / recovery | Late November onward | Stragglers and edge cases

Risk | Mitigation

User confusion / phishing concerns about reset
prompts | Clear, consistent wording approved by Security and Legal; in-product-SG
confirmation

Support overload during peak waves | Stagger waves; scale support; self-service-SG flows

Engagement and addressability dip | Re-onboarding-SG flows; phased reminders
