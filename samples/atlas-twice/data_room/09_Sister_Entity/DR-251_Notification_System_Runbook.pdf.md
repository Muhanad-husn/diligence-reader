CONFIDENTIAL — Project Atlas — DR-058-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

User Notification System — Runbook
Beaconvale Media Inc. — Product Data and Technology
Document ID DR-058-SE
Prepared by / owner Maya Hart
Date 2 November 2023

Classification Strictly Confidential — Project Atlas
System User Notification System (UNS)
Doc type Operational runbook

Operational runbook for the User Notification System (UNS), which sends large-scale-SE user communications across
email, in-app-SE and push channels. This runbook covers message templates, approval, throughput limits and
capacity planning. It is maintained by Product Operations.

1. Channels and capacity
Channel Sustained throughput Peak (with surge approval) Audience addressable
Transactional email 9m / hour 20m / hour Tens of millions
In-app-SE notice 29m / hour 58m / hour Hundreds of millions
Push notification 12m / hour 26m / hour Mobile MAU
SMS (recovery only) 0.7m / hour 1.8m / hour Verified phone numbers

Capacity planning assumes campaigns can address tens of millions of recipients per wave and that a full-population-SE credential or
security notice may be staged across multiple waves over several days.

3. Message templates
Template Purpose Approvals required
Welcome / onboarding New-account-SE activation Product
Service announcement Feature / policy update Product + Comms
Security / credential notice Prompt users to reset credentials or re-authenticate-SE Product + Security + Legal
Account recovery Password reset and recovery flows Product + Security
Marketing / promotional Opt-in-SE marketing Marketing + Privacy

3.1 Security / credential notice template

The security / credential notice template is used to ask users, at scale, to reset their password and sign in again.
It supports staged delivery to very large populations, suppression of already-actioned-SE users, and reminder waves.
Because of its sensitivity, it requires Security and Legal approval of wording in addition to Product sign-off-SE. It is the
template configured for the Confidence Rebuild programme (see DR-059-SE).

4. Approval workflow

1 Requestor drafts the campaign from an approved template and defines the audience.
3 Required approvers (per the template) sign off wording and audience scope.
4 Operations schedules waves within throughput limits and configures suppression lists.
6 Delivery is monitored; bounce/complaint-SE thresholds trigger automatic throttling.

6. Capacity planning example (full-population-SE staged notice)

Channel | Sustained throughput | Peak (with surge approval) | Audience addressable

Transactional email | 9m / hour | 20m / hour | Tens of millions

In-app-SE notice | 29m / hour | 58m / hour | Hundreds of millions

Push notification | 12m / hour | 26m / hour | Mobile MAU

SMS (recovery only) | 0.7m / hour | 1.8m / hour | Verified phone numbers

Template | Purpose | Approvals required

Welcome / onboarding | New-account-SE activation | Product

Service announcement | Feature / policy update | Product + Comms

Security / credential notice | Prompt users to reset credentials or re-authenticate-SE | Product + Security + Legal

Account recovery | Password reset and recovery flows | Product + Security

Marketing / promotional | Opt-in-SE marketing | Marketing + Privacy

CONFIDENTIAL — Project Atlas — DR-058-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

• Stage a notice to a hundreds-of-millions-SE population across in-app-SE first, then email.
• Plan 6–10 daily waves with reminder waves for non-actioners-SE.
• Reserve recovery-channel-SE (SMS) capacity for users without an accessible email.
• Pre-warm-SE sending infrastructure and coordinate with deliverability partners.
7. Guardrails

• Mandatory suppression of users who have already actioned the request.
• Hard caps on send rate to protect deliverability reputation.
• Legal sign-off-SE required before any security/credential-SE notice is released.
Maintained by Maya Hart, VP Product, Identity and Mail, Product Operations. Confidential.
