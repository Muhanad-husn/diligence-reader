CONFIDENTIAL — Project Atlas — DR-064-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

SOC 3 Type II Report — 2023 (Summary)
SOC 3 Type II — 2023 (Management Summary)

Document ID DR-064-SE
Prepared by / owner Owen Bell
Date 5 October 2023
Classification Strictly Confidential — Project Atlas
Examination period 1 Oct 2022 – 30 Sep 2023
Opinion Unqualified (in-scope-SE)

Summary of the independent SOC 3 Type II examination of Beaconvale Media Inc.’s in-scope-SE services for the period
1 October 2022 to 30 September 2023. The examination addressed the Trust Services Criteria for Security,
Availability and Confidentiality. This is a management summary; the full service auditor’s report is available under
NDA.

1. Opinion

The service auditor issued an unqualified (clean) opinion that, in all material respects, controls over the in-scope-SE
systems were suitably designed and operating effectively to meet the applicable Trust Services Criteria throughout
the examination period. No exceptions requiring qualification were noted for the in-scope-SE system boundary.

3. System boundary and scope

The examination scope comprises the current production identity, advertising and communications services and
their supporting cloud infrastructure. The scope is defined by the system description prepared by management and
agreed with the service auditor.

In scope Basis
AtlasID identity graph (current) Core production identity service
VPAuth (current signing/validation-SE path) Current authentication service
LumenX Ad Exchange Production advertising platform
VistaMail Production communications service
Osprey-hosted-SE production estate (current) Supporting cloud infrastructure

4. Carve-outs-SE and scope exclusions

Consistent with the agreed system description, certain legacy components in active decommission were excluded
(carved out) from the examination boundary. The clean opinion above does not extend to the carved-out-SE
components. Excluded items are managed under the modernisation roadmap and assured through separate
internal review.

Carved-out-SE component Reason for exclusion
legacy_uap-SE (legacy Unified Account Profile store and its
backups)
Legacy data store in active decommission; outside current production
boundary.
Legacy authentication path (legacy VPAuth session-signing-SE
key set)
Superseded signing material pending rotation/retirement-SE under
modernisation.
Legacy SSO connectors (pre-2022-SE) Deprecated federation endpoints scheduled for removal.

6. Complementary controls and reliance

In scope | Basis

AtlasID identity graph (current) | Core production identity service

VPAuth (current signing/validation-SE path) | Current authentication service

LumenX Ad Exchange | Production advertising platform

VistaMail | Production communications service

Osprey-hosted-SE production estate (current) | Supporting cloud infrastructure

Carved-out-SE component | Reason for exclusion

legacy_uap-SE (legacy Unified Account Profile store and its
backups) | Legacy data store in active decommission; outside current production
boundary.

Legacy authentication path (legacy VPAuth session-signing-SE
key set) | Superseded signing material pending rotation/retirement-SE under
modernisation.

Legacy SSO connectors (pre-2022-SE) | Deprecated federation endpoints scheduled for removal.

CONFIDENTIAL — Project Atlas — DR-064-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

Users of this report should note that the unqualified opinion applies only to the in-scope-SE system boundary
described above. Reliance on this report for the carved-out-SE legacy components is not appropriate; those
components are addressed separately. Subservice organisations are presented using the carve-out-SE method.
Management summary prepared by the Office of the CISO. The full SOC 3 Type II report, including the complete system description
and list of carved-out-SE components, is available to approved reviewers under NDA.
