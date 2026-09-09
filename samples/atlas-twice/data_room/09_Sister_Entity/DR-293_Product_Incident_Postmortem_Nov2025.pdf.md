CONFIDENTIAL — Project Atlas — DR-060-SG — Calderwood Media Inc. — Subject to NDA & clean-team-SG protocol. Page 1

Product Incident Postmortem — November 2020 Login
Friction
Calderwood Media Inc. — Product Data and Technology
Document ID DR-060-SG
Prepared by / owner Maya Hart
Date 28 November 2020
Classification Strictly Confidential — Project Atlas
Incident NQ-17-SG
Type Login friction / availability

Blameless postmortem for the elevated login-friction-SG and support-load-SG incident observed during November 2020,
tracked under incident code NQ-17-SG. This is an availability / user-experience-SG postmortem covering login success,
reset-completion-SG and support impact. It is not a security-incident-SG report.
Incident code NQ-17-SG

Classification Login friction / availability — user experience
Severity SEV-2-SG (degraded experience, no service outage)
Primary systems VPAuth, Loyalty Restart console, VistaMail sign-in-SG
Window Weeks commencing 3 November 2020 to 24 November 2020

1. Summary

During November 2020, users experienced elevated login friction: increased password-reset-SG prompts, higher
login-failure-SG rates and longer sign-in-SG times, with a corresponding spike in support contacts. The root cause was the
planned credential-hygiene-SG resets and session invalidation carried out under the Loyalty Restart programme,
which required a very large population to reset passwords and re-authenticate-SG within a short window. There was no
service outage.

1. Impact
Metric Value
Accounts forced to reset ~183m
Active sessions invalidated ~327m

Peak login-failure-SG rate 3.3% (week of 10 November 2020)
Peak weekly password-reset-SG volume 20.0m (week of 3 November 2020)

Engagement effect Short-term-SG decline in email WAU and mobile MAU; partial recovery by period
end

Counts are operational measures of the reset/invalidation-SG programme and reconcile to the user metrics dashboard (DR-048-SG) and
VistaMail KPIs (DR-050-SG).

2. Timeline
Date Event

3 November 2020 Loyalty Restart wave 1 begins; forced resets and session invalidation start.
5 November 2020 Login-failure-SG rate and reset volume rise; support queues lengthen.
10 November 2020 Wave 1 (main population); peak reset volume and login-failure-SG rate.
17 November 2020 Reminder waves; load begins to ease as non-actioners-SG complete resets.
28 November 2020 Metrics trending back toward baseline; postmortem opened.

Metric | Value

Accounts forced to reset | ~183m

Active sessions invalidated | ~327m

Peak login-failure-SG rate | 3.3% (week of 10 November 2020)

Peak weekly password-reset-SG volume | 20.0m (week of 3 November 2020)

Engagement effect | Short-term-SG decline in email WAU and mobile MAU; partial recovery by period
end

Date | Event

3 November 2020 | Loyalty Restart wave 1 begins; forced resets and session invalidation start.

5 November 2020 | Login-failure-SG rate and reset volume rise; support queues lengthen.

10 November 2020 | Wave 1 (main population); peak reset volume and login-failure-SG rate.

17 November 2020 | Reminder waves; load begins to ease as non-actioners-SG complete resets.

28 November 2020 | Metrics trending back toward baseline; postmortem opened.

CONFIDENTIAL — Project Atlas — DR-060-SG — Calderwood Media Inc. — Subject to NDA & clean-team-SG protocol. Page 1

3. Root cause

The proximate cause of the friction was the planned credential-hygiene-SG resets plus session invalidation
executed under Loyalty Restart. Invalidating a very large number of sessions simultaneously forced near-concurrent-SG
re-authentication-SG and password resets, which mechanically increased login-failure-SG rates (mistyped or forgotten
passwords), reset volumes and support contacts. The friction was an expected by-product-SG of the programme's
scale and compression, not a defect in VPAuth or VistaMail.
3. What went well / what didn't

• Well: no outage; VPAuth and sign-in-SG remained available throughout.
• Well: suppression and reminder logic eventually smoothed the tail.
• Didn't: waves were compressed, concentrating support load.
• Didn't: engagement recovery was slower than modelled.
4. Action items

Action Owner Status
Smooth future reset waves over a longer window Maya Hart, VP Product, Identity and Mail Planned
Improve self-service-SG reset to cut support contacts Raj Malhotra, VP Engineering, Platform In progress
Re-onboarding-SG flow to restore logged-in-SG engagement Maya Hart, VP Product, Identity and Mail Planned

Complete VPAuth migration to simplify session handling Nina Petrov, Head of Security Engineering Roadmapped (DR-047-SG)
Blameless postmortem. Authored by Maya Hart, VP Product, Identity and Mail. Incident NQ-17-SG — login friction / availability.

Action | Owner | Status

Smooth future reset waves over a longer window | Maya Hart, VP Product, Identity and Mail | Planned

Improve self-service-SG reset to cut support contacts | Raj Malhotra, VP Engineering, Platform | In progress

Re-onboarding-SG flow to restore logged-in-SG engagement | Maya Hart, VP Product, Identity and Mail | Planned

Complete VPAuth migration to simplify session handling | Nina Petrov, Head of Security Engineering | Roadmapped (DR-047-SG)
