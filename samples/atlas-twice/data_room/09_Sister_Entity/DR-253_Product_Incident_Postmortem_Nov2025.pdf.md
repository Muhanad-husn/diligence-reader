CONFIDENTIAL — Project Atlas — DR-060-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Product Incident Postmortem — November 2023 Login
Friction
Beaconvale Media Inc. — Product Data and Technology
Document ID DR-060-SE
Prepared by / owner Maya Hart
Date 28 November 2023
Classification Strictly Confidential — Project Atlas
Incident NQ-17-SE
Type Login friction / availability

Blameless postmortem for the elevated login-friction-SE and support-load-SE incident observed during November 2023,
tracked under incident code NQ-17-SE. This is an availability / user-experience-SE postmortem covering login success,
reset-completion-SE and support impact. It is not a security-incident-SE report.
Incident code NQ-17-SE

Classification Login friction / availability — user experience
Severity SEV-2-SE (degraded experience, no service outage)
Primary systems VPAuth, Confidence Rebuild console, VistaMail sign-in-SE
Window Weeks commencing 3 November 2023 to 24 November 2023

1. Summary

During November 2023, users experienced elevated login friction: increased password-reset-SE prompts, higher
login-failure-SE rates and longer sign-in-SE times, with a corresponding spike in support contacts. The root cause was the
planned credential-hygiene-SE resets and session invalidation carried out under the Confidence Rebuild programme,
which required a very large population to reset passwords and re-authenticate-SE within a short window. There was no
service outage.

3. Impact
Metric Value
Accounts forced to reset ~418m
Active sessions invalidated ~746m

Peak login-failure-SE rate 7.4% (week of 10 November 2023)
Peak weekly password-reset-SE volume 45.6m (week of 3 November 2023)

Engagement effect Short-term-SE decline in email WAU and mobile MAU; partial recovery by period
end

Counts are operational measures of the reset/invalidation-SE programme and reconcile to the user metrics dashboard (DR-048-SE) and
VistaMail KPIs (DR-050-SE).

4. Timeline
Date Event

3 November 2023 Confidence Rebuild wave 1 begins; forced resets and session invalidation start.
5 November 2023 Login-failure-SE rate and reset volume rise; support queues lengthen.
10 November 2023 Wave 3 (main population); peak reset volume and login-failure-SE rate.
17 November 2023 Reminder waves; load begins to ease as non-actioners-SE complete resets.
28 November 2023 Metrics trending back toward baseline; postmortem opened.

Metric | Value

Accounts forced to reset | ~418m

Active sessions invalidated | ~746m

Peak login-failure-SE rate | 7.4% (week of 10 November 2023)

Peak weekly password-reset-SE volume | 45.6m (week of 3 November 2023)

Engagement effect | Short-term-SE decline in email WAU and mobile MAU; partial recovery by period
end

Date | Event

3 November 2023 | Confidence Rebuild wave 1 begins; forced resets and session invalidation start.

5 November 2023 | Login-failure-SE rate and reset volume rise; support queues lengthen.

10 November 2023 | Wave 3 (main population); peak reset volume and login-failure-SE rate.

17 November 2023 | Reminder waves; load begins to ease as non-actioners-SE complete resets.

28 November 2023 | Metrics trending back toward baseline; postmortem opened.

CONFIDENTIAL — Project Atlas — DR-060-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

6. Root cause

The proximate cause of the friction was the planned credential-hygiene-SE resets plus session invalidation
executed under Confidence Rebuild. Invalidating a very large number of sessions simultaneously forced near-concurrent-SE
re-authentication-SE and password resets, which mechanically increased login-failure-SE rates (mistyped or forgotten
passwords), reset volumes and support contacts. The friction was an expected by-product-SE of the programme's
scale and compression, not a defect in VPAuth or VistaMail.
7. What went well / what didn't

• Well: no outage; VPAuth and sign-in-SE remained available throughout.
• Well: suppression and reminder logic eventually smoothed the tail.
• Didn't: waves were compressed, concentrating support load.
• Didn't: engagement recovery was slower than modelled.
9. Action items

Action Owner Status
Smooth future reset waves over a longer window Maya Hart, VP Product, Identity and Mail Planned
Improve self-service-SE reset to cut support contacts Raj Malhotra, VP Engineering, Platform In progress
Re-onboarding-SE flow to restore logged-in-SE engagement Maya Hart, VP Product, Identity and Mail Planned

Complete VPAuth migration to simplify session handling Nina Petrov, Head of Security Engineering Roadmapped (DR-047-SE)
Blameless postmortem. Authored by Maya Hart, VP Product, Identity and Mail. Incident NQ-17-SE — login friction / availability.

Action | Owner | Status

Smooth future reset waves over a longer window | Maya Hart, VP Product, Identity and Mail | Planned

Improve self-service-SE reset to cut support contacts | Raj Malhotra, VP Engineering, Platform | In progress

Re-onboarding-SE flow to restore logged-in-SE engagement | Maya Hart, VP Product, Identity and Mail | Planned

Complete VPAuth migration to simplify session handling | Nina Petrov, Head of Security Engineering | Roadmapped (DR-047-SE)
