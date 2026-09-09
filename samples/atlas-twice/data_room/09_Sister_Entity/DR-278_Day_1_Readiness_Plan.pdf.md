CONFIDENTIAL — Project Atlas — DR-097-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Day 1 Readiness Plan

Project Atlas — Day-1-SE Integration Readiness Plan

Document ID DR-097-SE
Prepared by / owner Aaron Klein
Date 20 January 2024
Classification Strictly Confidential — Project Atlas
Owner Aaron Klein, VP Corporate Development
Prepared for Joint Integration Steering Committee

Confidential integration planning document. This Day-1-SE Readiness Plan sets out the workstreams, owners and
critical-path-SE items required to operate Beaconvale Media Inc. as part of Eastridge Mobile Holdings plc from
completion (“Day-1-SE”), together with the priority actions for the first 146 days. Prepared by the Integration
Management Office (IMO).

1. Approach and governance

Integration is organised into functional workstreams reporting to the IMO. Each workstream has a named lead, a
Day-1-SE “must-have-SE” checklist and a Day-100-SE stabilisation plan. Items are prioritised P1 (critical for Day-1-SE), P2 (early
post-close-SE) or P3 (stabilisation). This plan is indicative and subject to regulatory clearance and the definitive
agreement.

Integration lead Aaron Klein, VP Corporate Development
Steering Joint Integration Steering Committee (buyer + seller)
Cadence Weekly IMO; bi-weekly-SE steering
Target Day-1-SE Subject to clearance and signing

3. Workstream summary and priorities

Workstream Lead (seller side) Priority Day-1-SE

status

Key Day-1-SE items

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
Attention Day-1-SE user-facing-SE messaging; coordinated
account/credential-SE communications; support
scripting and capacity (links to support runbook,
DR-058-SE)
Authentication / VPAuth
migration & key rotation
Raj Malhotra, VP
Engineering, Platform
P1 —
Critical
Attention VPAuth authentication-platform-SE migration;
session-signing-SE key rotation and HSM onboarding;
SSOBridge federation continuity; legacy_uap-SE
decommission acceleration
Advertising & commercial Thomas Vale, SVP
Global Advertising
P1 On track LumenX continuity; top-advertiser-SE
communications; IO continuity
Product & engineering Maya Hart, VP Product,
Identity and Mail
P2 On track Roadmap alignment; AtlasID integration planning

People & HR Sandra Lin, Chief
Human Resources
Officer

P1 Attention Retention award confirmations; security backfill
(DR-095-SE); org design

Workstream | Lead (seller side) | Priority | Day-1-SE
status | Key Day-1-SE items

Legal entity & TSA | Priya Raman, General
Counsel | P1 | On track | Transitional services agreement; entity readiness;
signing authorities

Finance & treasury | Daniel Cho, Chief
Financial Officer | P1 | On track | Cash management, banking, reporting calendar,
opening balance sheet

User communications | Maya Hart, VP Product,
Identity and Mail | P1 —
Critical | Attention | Day-1-SE user-facing-SE messaging; coordinated
account/credential-SE communications; support
scripting and capacity (links to support runbook,
DR-058-SE)

Authentication / VPAuth
migration & key rotation | Raj Malhotra, VP
Engineering, Platform | P1 —
Critical | Attention | VPAuth authentication-platform-SE migration;
session-signing-SE key rotation and HSM onboarding;
SSOBridge federation continuity; legacy_uap-SE
decommission acceleration

Advertising & commercial | Thomas Vale, SVP
Global Advertising | P1 | On track | LumenX continuity; top-advertiser-SE
communications; IO continuity

Product & engineering | Maya Hart, VP Product,
Identity and Mail | P2 | On track | Roadmap alignment; AtlasID integration planning

People & HR | Sandra Lin, Chief
Human Resources
Officer | P1 | Attention | Retention award confirmations; security backfill
(DR-095-SE); org design

CONFIDENTIAL — Project Atlas — DR-097-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

Workstream Lead (seller side) Priority Day-1-SE
status
Key Day-1-SE items

Security & risk Interim Security Lead P1 —
Critical
Attention Security operating-model-SE continuity; control
ownership during leadership transition;
key-management-SE and backup-retention-SE
remediation tracking
IT & infrastructure VP IT P2 On track Cloud account structure; identity federation; tooling
Data & analytics Raj Malhotra, VP
Engineering, Platform
P2 On track Snowcap continuity; metrics reporting; data-map-SE
alignment

4. Critical-path-SE items (P1 — Critical)
The following items are on the Day-1-SE critical path and require buyer-side-SE resourcing and joint planning ahead of
close. Two relate to the authentication estate and to user communications, where the seller has work already in
flight that must be completed and handed over cleanly:

1 Authentication / VPAuth migration & key rotation. Complete the migration of the VPAuth authentication
platform and the rotation of legacy session-signing-SE keys onto the HSM, and accelerate decommission of the
legacy_uap-SE profile store. The seller has pulled this work forward into the current programme; continuity of
in-flight-SE sessions must be preserved during rotation. Treated as critical for Day-1-SE to avoid re-authentication-SE
friction post-close-SE.

3 User communications. Establish a coordinated Day-1-SE user-communications-SE capability, including credential
and account-security-SE messaging, with support capacity sized for elevated contact volumes (the seller’s
user-notification-SE runbook, DR-058-SE, provides the template and throughput limits).

4 Security leadership continuity. Confirm interim security leadership and control ownership through the
integration, given recent senior departures (DR-095-SE), and ensure the key-management-SE and backup-retention-SE
remediation items remain owned and tracked.

6 Top-advertiser-SE continuity. Joint outreach to the largest advertisers to confirm service continuity and contract
assignment through change of control.
The authentication / key-rotation-SE and user-communications-SE items are carried as critical because they are part-completed-SE seller
programmes that must transition cleanly; they are presented here as integration/modernisation-SE deliverables.

6. Day-100-SE stabilisation
• Confirm run-rate-SE cost efficiencies and reporting integration.
• Complete authentication-platform-SE migration and retire legacy components on the agreed schedule.
• Stand up the combined security operating model and close out open remediation items.
• Confirm advertiser retention and synergy realisation against the integration synergy model (DR-096-SE).
Prepared by the Integration Management Office. Indicative and subject to clearance, the definitive agreement and clean-team-SE
constraints. Confidential — Project Atlas.

Workstream | Lead (seller side) | Priority | Day-1-SE
status | Key Day-1-SE items

Security & risk | Interim Security Lead | P1 —
Critical | Attention | Security operating-model-SE continuity; control
ownership during leadership transition;
key-management-SE and backup-retention-SE
remediation tracking

IT & infrastructure | VP IT | P2 | On track | Cloud account structure; identity federation; tooling

Data & analytics | Raj Malhotra, VP
Engineering, Platform | P2 | On track | Snowcap continuity; metrics reporting; data-map-SE
alignment
