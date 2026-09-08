CONFIDENTIAL — Project Atlas — DR-060 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 1

Product Incident Postmortem — November 2025 Login
Friction
VistaPort Media Inc. — Product Data and Technology
Document ID DR-060
Prepared by / owner Maya Hart
Date 28 November 2025
Classification Strictly Confidential — Project Atlas
the ticket
Type sign-in difficulty / availability

Blameless postmortem for the elevated sign-in difficulty and support-load incident observed during November 2025,
tracked under the ticket. This is an availability / user-experience postmortem covering login success,
reset-completion and support impact. It is not a security-incident report.
The ticket

Classification sign-in difficulty / availability — user experience
Severity SEV-2 (degraded experience, no service outage)
Primary systems VPAuth, the programme console, VistaMail sign-in
Window Weeks commencing 3 November 2025 to 24 November 2025

1. Summary

During November 2025, users experienced elevated sign-in difficulty: increased password-reset prompts, higher
login-failure rates and longer sign-in times, with a corresponding spike in support contacts. The root cause was the
planned account-security resets and session invalidation carried out under the programme,
which required a very large population to reset passwords and re-authenticate within a short window. There was no
service outage.

2. Impact
Metric Value
Accounts forced to reset ~286m
Active sessions invalidated ~511m

Peak login-failure rate 5.1% (week of 10 November 2025)
Peak weekly password-reset volume 31.2m (week of 3 November 2025)

Engagement effect Short-term decline in email WAU and mobile MAU; partial recovery by period
end

Counts are operational measures of the reset/invalidation programme and reconcile to the user metrics dashboard (DR-048) and
VistaMail KPIs (DR-050).

3. Timeline
Date Event

3 November 2025 programme wave 1 begins; forced resets and session invalidation start.
5 November 2025 Login-failure rate and reset volume rise; support queues lengthen.
10 November 2025 Wave 2 (main population); peak reset volume and login-failure rate.
17 November 2025 Reminder waves; load begins to ease as non-actioners complete resets.
28 November 2025 Metrics trending back toward baseline; postmortem opened.

Metric | Value

Accounts forced to reset | ~286m

Active sessions invalidated | ~511m

Peak login-failure rate | 5.1% (week of 10 November 2025)

Peak weekly password-reset volume | 31.2m (week of 3 November 2025)

Engagement effect | Short-term decline in email WAU and mobile MAU; partial recovery by period
end

Date | Event

3 November 2025 | the programme wave 1 begins; forced resets and session invalidation start.

5 November 2025 | Login-failure rate and reset volume rise; support queues lengthen.

10 November 2025 | Wave 2 (main population); peak reset volume and login-failure rate.

17 November 2025 | Reminder waves; load begins to ease as non-actioners complete resets.

28 November 2025 | Metrics trending back toward baseline; postmortem opened.

CONFIDENTIAL — Project Atlas — DR-060 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 2

4. Root cause

The proximate cause of the friction was the planned account-security resets plus session invalidation
executed under the programme. Invalidating a very large number of sessions simultaneously forced near-concurrent
re-authentication and password resets, which mechanically increased login-failure rates (mistyped or forgotten
passwords), reset volumes and support contacts. The friction was an expected by-product of the programme's
scale and compression, not a defect in VPAuth or VistaMail.
5. What went well / what didn't

• Well: no outage; VPAuth and sign-in remained available throughout.
• Well: suppression and reminder logic eventually smoothed the tail.
• Didn't: waves were compressed, concentrating support load.
• Didn't: engagement recovery was slower than modelled.
6. Action items

Action Owner Status
Smooth future reset waves over a longer window Maya Hart, VP Product, Identity and Mail Planned
Improve self-service reset to cut support contacts Raj Malhotra, VP Engineering, Platform In progress
Re-onboarding flow to restore logged-in engagement Maya Hart, VP Product, Identity and Mail Planned

Complete VPAuth migration to simplify session handling Nina Petrov, Head of Security Engineering Roadmapped (DR-047)
Blameless postmortem. Authored by Maya Hart, VP Product, Identity and Mail. The ticket — sign-in difficulty / availability.

Action | Owner | Status

Smooth future reset waves over a longer window | Maya Hart, VP Product, Identity and Mail | Planned

Improve self-service reset to cut support contacts | Raj Malhotra, VP Engineering, Platform | In progress

Re-onboarding flow to restore logged-in engagement | Maya Hart, VP Product, Identity and Mail | Planned

Complete VPAuth migration to simplify session handling | Nina Petrov, Head of Security Engineering | Roadmapped (DR-047)
