CONFIDENTIAL — Project Atlas — DR-058 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 1

User Notification System — Runbook
VistaPort Media Inc. — Product Data and Technology
Document ID DR-058
Prepared by / owner Maya Hart
Date 2 November 2025

Classification Strictly Confidential — Project Atlas
System User Notification System (UNS)
Doc type Operational runbook

Operational runbook for the User Notification System (UNS), which sends large-scale user communications across
email, in-app and push channels. This runbook covers message templates, approval, throughput limits and
capacity planning. It is maintained by Product Operations.

1. Channels and capacity
Channel Sustained throughput Peak (with surge approval) Audience addressable
Transactional email 6m / hour 14m / hour Tens of millions
In-app notice 20m / hour 40m / hour Hundreds of millions
Push notification 8m / hour 18m / hour Mobile MAU
SMS (recovery only) 0.5m / hour 1.2m / hour Verified phone numbers

Capacity planning assumes campaigns can address tens of millions of recipients per wave and that a full-population credential or
security notice may be staged across multiple waves over several days.

2. Message templates
Template Purpose Approvals required
Welcome / onboarding New-account activation Product
Service announcement Feature / policy update Product + Comms
Security / credential notice Prompt users to reset credentials or re-authenticate Product + Security + Legal
Account recovery Password reset and recovery flows Product + Security
Marketing / promotional Opt-in marketing Marketing + Privacy

2.1 Security / credential notice template

The security / credential notice template is used to ask users, at scale, to reset their password and sign in again.
It supports staged delivery to very large populations, suppression of already-actioned users, and reminder waves.
Because of its sensitivity, it requires Security and Legal approval of wording in addition to Product sign-off. It is the
template configured for the programme (see DR-059).

3. Approval workflow

1 Requestor drafts the campaign from an approved template and defines the audience.
2 Required approvers (per the template) sign off wording and audience scope.
3 Operations schedules waves within throughput limits and configures suppression lists.
4 Delivery is monitored; bounce/complaint thresholds trigger automatic throttling.

4. Capacity planning example (full-population staged notice)

Channel | Sustained throughput | Peak (with surge approval) | Audience addressable

Transactional email | 6m / hour | 14m / hour | Tens of millions

In-app notice | 20m / hour | 40m / hour | Hundreds of millions

Push notification | 8m / hour | 18m / hour | Mobile MAU

SMS (recovery only) | 0.5m / hour | 1.2m / hour | Verified phone numbers

Template | Purpose | Approvals required

Welcome / onboarding | New-account activation | Product

Service announcement | Feature / policy update | Product + Comms

Security / credential notice | Prompt users to reset credentials or re-authenticate | Product + Security + Legal

Account recovery | Password reset and recovery flows | Product + Security

Marketing / promotional | Opt-in marketing | Marketing + Privacy

CONFIDENTIAL — Project Atlas — DR-058 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 2

• Stage a notice to a hundreds-of-millions population across in-app first, then email.
• Plan 4–7 daily waves with reminder waves for non-actioners.
• Reserve recovery-channel (SMS) capacity for users without an accessible email.
• Pre-warm sending infrastructure and coordinate with deliverability partners.
5. Guardrails

• Mandatory suppression of users who have already actioned the request.
• Hard caps on send rate to protect deliverability reputation.
• Legal sign-off required before any security/credential notice is released.
Maintained by Maya Hart, VP Product, Identity and Mail, Product Operations. Confidential.
