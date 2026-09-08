CONFIDENTIAL — Project Atlas — DR-097 — Vista Port Media Inc. — Subject to NDA & clean-team protocol. Page 1

Day 1 Readiness Plan

Project Atlas — Day-1 Integration Readiness Plan

Document ID DR-097
Prepared by / owner Aaron Klein
Date 20 January 2026
Classification Strictly Confidential — Project Atlas
Owner Aaron Klein, VP Corporate Development
Prepared for Joint Integration Steering Committee

Confidential integration planning document. This Day-1 Readiness Plan sets out the workstreams, owners and
critical-path items required to operate Vista Port Media Inc. as part of Northstar Mobile Holdings from
completion (“Day-1”), together with the priority actions for the first 100 days. Prepared by the Integration
Management Office (IMO).

1. Approach and governance

Integration is organised into functional workstreams reporting to the IMO. Each workstream has a named lead, a
Day-1 “must-have” checklist and a Day-100 stabilisation plan. Items are prioritised P1 (critical for Day-1), P2 (early
post-close) or P3 (stabilisation). This plan is indicative and subject to regulatory clearance and the definitive
agreement.

Integration lead Aaron Klein, VP Corporate Development
Steering Joint Integration Steering Committee (buyer + seller)
Cadence Weekly IMO; bi-weekly steering
Target Day-1 Subject to clearance and signing

2. Workstream summary and priorities

Workstream Lead (seller side) Priority Day-1

status

Key Day-1 items

Legal entity & TSA PRIYA RAMAN, General
Counsel
P1 On track Transitional services agreement; entity readiness;
signing authorities
Finance & treasury Danile Cho, Chief
Financial Officer
P1 On track Cash management, banking, reporting calendar,
opening balance sheet
User communications Maya Hart, VP Product,
Identity and Mail
P1 —
Critical
Attention Day-1 user-facing messaging; coordinated
account/credential communications; support
scripting and capacity (links to support runbook,
DR-058)
Authentication / VPAuth
migration & key rotation
Raj Malhotra, VP
Engineering, Platform
P1 —
Critical
Attention VPAuth authentication-platform migration;
session-signing key rotation and HSM onboarding;
SSOBridge federation continuity; legacy_uap
decommission acceleration
Advertising & commercial Thomas Vale, SVP
Global Advertising
P1 On track LumenX continuity; top-advertiser
communications; IO continuity
Product & engineering Maya Hart, VP Product,
Identity and Mail
P2 On track Roadmap alignment; AtlasID integration planning

People & HR Sandra Lin, Chief
Human Resources
Officer

P1 Attention Retention award confirmations; security backfill
(DR-095); org design

Workstream | Lead (seller side) | Priority | Day-1
status | Key Day-1 items

Legal entity & TSA | PRIYA RAMAN, General
Counsel | P1 | On track | Transitional services agreement; entity readiness;
signing authorities

Finance & treasury | Danile Cho, Chief
Financial Officer | P1 | On track | Cash management, banking, reporting calendar,
opening balance sheet

User communications | Maya Hart, VP Product,
Identity and Mail | P1 —
Critical | Attention | Day-1 user-facing messaging; coordinated
account/credential communications; support
scripting and capacity (links to support runbook,
DR-058)

Authentication / VPAuth
migration & key rotation | Raj Malhotra, VP
Engineering, Platform | P1 —
Critical | Attention | VPAuth authentication-platform migration;
session-signing key rotation and HSM onboarding;
SSOBridge federation continuity; legacy_uap
decommission acceleration

Advertising & commercial | Thomas Vale, SVP
Global Advertising | P1 | On track | LumenX continuity; top-advertiser
communications; IO continuity

Product & engineering | Maya Hart, VP Product,
Identity and Mail | P2 | On track | Roadmap alignment; AtlasID integration planning

People & HR | Sandra Lin, Chief
Human Resources
Officer | P1 | Attention | Retention award confirmations; security backfill
(DR-095); org design

CONFIDENTIAL — Project Atlas — DR-097 — Vista Port Media Inc. — Subject to NDA & clean-team protocol. Page 2

Workstream Lead (seller side) Priority Day-1
status
Key Day-1 items

Security & risk Interim Security Lead P1 —
Critical
Attention Security operating-model continuity; control
ownership during leadership transition;
key-management and backup-retention
remediation tracking
IT & infrastructure VP IT P2 On track Cloud account structure; identity federation; tooling
Data & analytics Raj Malhotra, VP
Engineering, Platform
P2 On track Snowcap continuity; metrics reporting; data-map
alignment

3. Critical-path items (P1 — Critical)
The following items are on the Day-1 critical path and require buyer-side resourcing and joint planning ahead of
close. Two relate to the authentication estate and to user communications, where the seller has work already in
flight that must be completed and handed over cleanly:

1 Authentication / VPAuth migration & key rotation. Complete the migration of the VPAuth authentication
platform and the rotation of legacy session-signing keys onto the HSM, and accelerate decommission of the
legacy_uap profile store. The seller has pulled this work forward into the current programme; continuity of
in-flight sessions must be preserved during rotation. Treated as critical for Day-1 to avoid re-authentication
friction post-close.

2 User communications. Establish a coordinated Day-1 user-communications capability, including credential
and account-security messaging, with support capacity sized for elevated contact volumes (the seller’s
user-notification runbook, DR-058, provides the template and throughput limits).

3 Security leadership continuity. Confirm interim security leadership and control ownership through the
integration, given recent senior departures (DR-095), and ensure the key-management and backup-retention
remediation items remain owned and tracked.

4 Top-advertiser continuity. Joint outreach to the largest advertisers to confirm service continuity and contract
assignment through change of control.
The authentication / key-rotation and user-communications items are carried as critical because they are part-completed seller
programmes that must transition cleanly; they are presented here as integration/modernisation deliverables.

4. Day-100 stabilisation
• Confirm run-rate cost efficiencies and reporting integration.
• Complete authentication-platform migration and retire legacy components on the agreed schedule.
• Stand up the combined security operating model and close out open remediation items.
• Confirm advertiser retention and synergy realisation against the integration synergy model (DR-096).
Prepared by the Integration Management Office. Indicative and subject to clearance, the definitive agreement and clean-team
constraints. Confidential — Project Atlas.

Workstream | Lead (seller side) | Priority | Day-1
status | Key Day-1 items

Security & risk | Interim Security Lead | P1 —
Critical | Attention | Security operating-model continuity; control
ownership during leadership transition;
key-management and backup-retention
remediation tracking

IT & infrastructure | VP IT | P2 | On track | Cloud account structure; identity federation; tooling

Data & analytics | Raj Malhotra, VP
Engineering, Platform | P2 | On track | Snowcap continuity; metrics reporting; data-map
alignment
