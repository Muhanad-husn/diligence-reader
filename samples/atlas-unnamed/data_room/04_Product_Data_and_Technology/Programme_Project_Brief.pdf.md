CONFIDENTIAL — Project Atlas — DR-059 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 1

The programme — Project Brief
VistaPort Media Inc. — Product Data and Technology
Document ID DR-059
Prepared by / owner Maya Hart
Date 31 October 2025
Classification Strictly Confidential — Project Atlas
the programme
Type account-security initiative

Internal product brief for the programme: a proactive account-security initiative comprising staged
forced password resets and session invalidation across a large account population. This brief defines scope,
approach, sequencing and success measures. It is an operational programme owned by Product in partnership
with Security.

Confidential — internal product brief. For diligence, the programme is described as a routine account-security and account-integrity
initiative.

1. Objective

Strengthen account hygiene by prompting a large population of users to reset passwords and by invalidating
existing sessions so that users re-authenticate. The programme is positioned as proactive maintenance of
credential and session integrity. It is sequenced to minimise user disruption while completing within the planned
window.

2. Scope and population
Parameter Value
Programme name programme
Type account-security: forced password reset + session invalidation
Population in scope Hundreds of millions of accounts (~286m forced resets planned)
Sessions to invalidate ~511m active sessions
Staged start 3 November 2025
Primary systems VPAuth (authentication/session), the programme console
Notification User Notification System — security/credential notice (DR-058)

3. Approach

1 Configure forced-reset and session-invalidation policy in the programme console, targeting the in-scope
population in staged cohorts.

2 On next sign-in, affected users are required to reset their password; existing sessions are invalidated by
VPAuth so that all clients re-authenticate.

3 Communicate via the security/credential notice template, suppressing users who have already actioned the
reset.

4 Monitor login-success, reset-completion and support volumes; throttle waves to manage load.

4. Sequencing
Wave Window Cohort
Wave 1 Week of 3 November 2025 Initial large cohort

Parameter | Value

Programme name | the programme

Type | account-security: forced password reset + session invalidation

Population in scope | Hundreds of millions of accounts (~286m forced resets planned)

Sessions to invalidate | ~511m active sessions

Staged start | 3 November 2025

Primary systems | VPAuth (authentication/session), the programme console

Notification | User Notification System — security/credential notice (DR-058)

Wave | Window | Cohort

Wave 1 | Week of 3 November 2025 | Initial large cohort

CONFIDENTIAL — Project Atlas — DR-059 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 2

Wave Window Cohort
Wave 2 Week of 10 November 2025 Main population
Reminder waves From 17 November 2025 Non-actioners
Tail / recovery Late November onward Stragglers and edge cases

5. Expected user impact

• Temporary increase in sign-in difficulty and password-reset volume during the reset waves.
• Elevated support contacts for account-lockout and reset assistance.
• Short-term dip in logged-in engagement and addressable pool while users re-authenticate.
6. Success measures
• Reset-completion rate across the in-scope population.
• Return of login-success rate to baseline after the waves complete.
• Recovery of logged-in engagement and addressable audiences.
7. Risks

Risk Mitigation
User confusion / phishing concerns about reset
prompts
Clear, consistent wording approved by Security and Legal; in-product
confirmation
Support overload during peak waves Stagger waves; scale support; self-service flows
Engagement and addressability dip Re-onboarding flows; phased reminders
Owner Maya Hart, VP Product, Identity and Mail, with Security Engineering. Programme tracked under the FY2026 platform-health
theme (DR-047).

Wave | Window | Cohort

Wave 2 | Week of 10 November 2025 | Main population

Reminder waves | From 17 November 2025 | Non-actioners

Tail / recovery | Late November onward | Stragglers and edge cases

Risk | Mitigation

User confusion / phishing concerns about reset
prompts | Clear, consistent wording approved by Security and Legal; in-product
confirmation

Support overload during peak waves | Stagger waves; scale support; self-service flows

Engagement and addressability dip | Re-onboarding flows; phased reminders
