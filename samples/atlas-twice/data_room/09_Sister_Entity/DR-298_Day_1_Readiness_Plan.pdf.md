CONFIDENTIAL — Project Atlas — DR-097-SG — Calderwood Media Inc. — Subject to NDA & clean-team-SG protocol. Page 1

Day 1 Readiness Plan

Project Atlas — Day-1-SG Integration Readiness Plan

Document ID DR-097-SG
Prepared by / owner Aaron Klein
Date 20 January 2021
Classification Strictly Confidential — Project Atlas
Owner Aaron Klein, VP Corporate Development
Prepared for Joint Integration Steering Committee

Confidential integration planning document. This Day-1-SG Readiness Plan sets out the workstreams, owners and
critical-path-SG items required to operate Calderwood Media Inc. as part of Southgate Mobile Holdings plc from
completion (“Day-1-SG”), together with the priority actions for the first 64 days. Prepared by the Integration
Management Office (IMO).

1. Approach and governance

Integration is organised into functional workstreams reporting to the IMO. Each workstream has a named lead, a
Day-1-SG “must-have-SG” checklist and a Day-100-SG stabilisation plan. Items are prioritised P1 (critical for Day-1-SG), P2 (early
post-close-SG) or P3 (stabilisation). This plan is indicative and subject to regulatory clearance and the definitive
agreement.

Integration lead Aaron Klein, VP Corporate Development
Steering Joint Integration Steering Committee (buyer + seller)
Cadence Weekly IMO; bi-weekly-SG steering
Target Day-1-SG Subject to clearance and signing

1. Workstream summary and priorities

Workstream Lead (seller side) Priority Day-1-SG

status

Key Day-1-SG items

Legal entity & TSA Priya Raman, General
Counsel
P1 On track Transitional services agreement; entity readiness;
signing authorities
Finance & treasury Daniel Cho, Chief
Financial Officer
P1 On track Cash management, banking, reporting calendar,
opening balance sheet
User communications Maya Hart, VP Product,
Identity and Mail
P1 —
Critical
Attention Day-1-SG user-facing-SG messaging; coordinated
account/credential-SG communications; support
scripting and capacity (links to support runbook,
DR-058-SG)
Authentication / VPAuth
migration & key rotation
Raj Malhotra, VP
Engineering, Platform
P1 —
Critical
Attention VPAuth authentication-platform-SG migration;
session-signing-SG key rotation and HSM onboarding;
SSOBridge federation continuity; legacy_uap-SG
decommission acceleration
Advertising & commercial Thomas Vale, SVP
Global Advertising
P1 On track LumenX continuity; top-advertiser-SG
communications; IO continuity
Product & engineering Maya Hart, VP Product,
Identity and Mail
P2 On track Roadmap alignment; AtlasID integration planning

People & HR Sandra Lin, Chief
Human Resources
Officer

P1 Attention Retention award confirmations; security backfill
(DR-095-SG); org design

Workstream | Lead (seller side) | Priority | Day-1-SG
status | Key Day-1-SG items

Legal entity & TSA | Priya Raman, General
Counsel | P1 | On track | Transitional services agreement; entity readiness;
signing authorities

Finance & treasury | Daniel Cho, Chief
Financial Officer | P1 | On track | Cash management, banking, reporting calendar,
opening balance sheet

User communications | Maya Hart, VP Product,
Identity and Mail | P1 —
Critical | Attention | Day-1-SG user-facing-SG messaging; coordinated
account/credential-SG communications; support
scripting and capacity (links to support runbook,
DR-058-SG)

Authentication / VPAuth
migration & key rotation | Raj Malhotra, VP
Engineering, Platform | P1 —
Critical | Attention | VPAuth authentication-platform-SG migration;
session-signing-SG key rotation and HSM onboarding;
SSOBridge federation continuity; legacy_uap-SG
decommission acceleration

Advertising & commercial | Thomas Vale, SVP
Global Advertising | P1 | On track | LumenX continuity; top-advertiser-SG
communications; IO continuity

Product & engineering | Maya Hart, VP Product,
Identity and Mail | P2 | On track | Roadmap alignment; AtlasID integration planning

People & HR | Sandra Lin, Chief
Human Resources
Officer | P1 | Attention | Retention award confirmations; security backfill
(DR-095-SG); org design

CONFIDENTIAL — Project Atlas — DR-097-SG — Calderwood Media Inc. — Subject to NDA & clean-team-SG protocol. Page 1

Workstream Lead (seller side) Priority Day-1-SG
status
Key Day-1-SG items

Security & risk Interim Security Lead P1 —
Critical
Attention Security operating-model-SG continuity; control
ownership during leadership transition;
key-management-SG and backup-retention-SG
remediation tracking
IT & infrastructure VP IT P2 On track Cloud account structure; identity federation; tooling
Data & analytics Raj Malhotra, VP
Engineering, Platform
P2 On track Snowcap continuity; metrics reporting; data-map-SG
alignment

2. Critical-path-SG items (P1 — Critical)
The following items are on the Day-1-SG critical path and require buyer-side-SG resourcing and joint planning ahead of
close. Two relate to the authentication estate and to user communications, where the seller has work already in
flight that must be completed and handed over cleanly:

1 Authentication / VPAuth migration & key rotation. Complete the migration of the VPAuth authentication
platform and the rotation of legacy session-signing-SG keys onto the HSM, and accelerate decommission of the
legacy_uap-SG profile store. The seller has pulled this work forward into the current programme; continuity of
in-flight-SG sessions must be preserved during rotation. Treated as critical for Day-1-SG to avoid re-authentication-SG
friction post-close-SG.

1 User communications. Establish a coordinated Day-1-SG user-communications-SG capability, including credential
and account-security-SG messaging, with support capacity sized for elevated contact volumes (the seller’s
user-notification-SG runbook, DR-058-SG, provides the template and throughput limits).

2 Security leadership continuity. Confirm interim security leadership and control ownership through the
integration, given recent senior departures (DR-095-SG), and ensure the key-management-SG and backup-retention-SG
remediation items remain owned and tracked.

3 Top-advertiser-SG continuity. Joint outreach to the largest advertisers to confirm service continuity and contract
assignment through change of control.
The authentication / key-rotation-SG and user-communications-SG items are carried as critical because they are part-completed-SG seller
programmes that must transition cleanly; they are presented here as integration/modernisation-SG deliverables.

3. Day-100-SG stabilisation
• Confirm run-rate-SG cost efficiencies and reporting integration.
• Complete authentication-platform-SG migration and retire legacy components on the agreed schedule.
• Stand up the combined security operating model and close out open remediation items.
• Confirm advertiser retention and synergy realisation against the integration synergy model (DR-096-SG).
Prepared by the Integration Management Office. Indicative and subject to clearance, the definitive agreement and clean-team-SG
constraints. Confidential — Project Atlas.

Workstream | Lead (seller side) | Priority | Day-1-SG
status | Key Day-1-SG items

Security & risk | Interim Security Lead | P1 —
Critical | Attention | Security operating-model-SG continuity; control
ownership during leadership transition;
key-management-SG and backup-retention-SG
remediation tracking

IT & infrastructure | VP IT | P2 | On track | Cloud account structure; identity federation; tooling

Data & analytics | Raj Malhotra, VP
Engineering, Platform | P2 | On track | Snowcap continuity; metrics reporting; data-map-SG
alignment
