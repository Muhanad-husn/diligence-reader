CONFIDENTIAL — Project Atlas — DR-064 — VistaPort Media, Inc.. — Subject to NDA & clean-team protocol. Page 1

SOC 2 Type II Report — 2025 (Summary)
SOC 2 Type II — 2025 (Management Summary)

Document ID DR-064
Prepared by / owner owen bell
Date 5 October 2025
Classification Strictly Confidential — Project Atlas
Examination period 1 Oct 2024 – 30 Sep 2025
Opinion Unqualified (in-scope)

Summary of the independent SOC 2 Type II examination of VistaPort Media, Inc..’s in-scope services for the period
1 October 2024 to 30 September 2025. The examination addressed the Trust Services Criteria for Security,
Availability and Confidentiality. This is a management summary; the full service auditor’s report is available under
NDA.

1. Opinion

The service auditor issued an unqualified (clean) opinion that, in all material respects, controls over the in-scope
systems were suitably designed and operating effectively to meet the applicable Trust Services Criteria throughout
the examination period. No exceptions requiring qualification were noted for the in-scope system boundary.

2. System boundary and scope

The examination scope comprises the current production identity, advertising and communications services and
their supporting cloud infrastructure. The scope is defined by the system description prepared by management and
agreed with the service auditor.

In scope Basis
AtlasID identity graph (current) Core production identity service
VPAuth (current signing/validation path) Current authentication service
LumenX Ad Exchange Production advertising platform
VistaMail Production communications service
Kestrel-hosted production estate (current) Supporting cloud infrastructure

3. Carve-outs and scope exclusions

Consistent with the agreed system description, certain legacy components in active decommission were excluded
(carved out) from the examination boundary. The clean opinion above does not extend to the carved-out
components. Excluded items are managed under the modernisation roadmap and assured through separate
internal review.

Carved-out component Reason for exclusion
legacy_uap (legacy Unified Account Profile store and its
backups)
Legacy data store in active decommission; outside current production
boundary.
Legacy authentication path (legacy VPAuth session-signing
key set)
Superseded signing material pending rotation/retirement under
modernisation.
Legacy SSO connectors (pre-2022) Deprecated federation endpoints scheduled for removal.

4. Complementary controls and reliance

In scope | Basis

AtlasID identity graph (current) | Core production identity service

VPAuth (current signing/validation path) | Current authentication service

LumenX Ad Exchange | Production advertising platform

VistaMail | Production communications service

Kestrel-hosted production estate (current) | Supporting cloud infrastructure

Carved-out component | Reason for exclusion

legacy_uap (legacy Unified Account Profile store and its
backups) | Legacy data store in active decommission; outside current production
boundary.

Legacy authentication path (legacy VPAuth session-signing
key set) | Superseded signing material pending rotation/retirement under
modernisation.

Legacy SSO connectors (pre-2022) | Deprecated federation endpoints scheduled for removal.

CONFIDENTIAL — Project Atlas — DR-064 — VistaPort Media, Inc.. — Subject to NDA & clean-team protocol. Page 2

Users of this report should note that the unqualified opinion applies only to the in-scope system boundary
described above. Reliance on this report for the carved-out legacy components is not appropriate; those
components are addressed separately. Subservice organisations are presented using the carve-out method.
Management summary prepared by the Office of the CISO. The full SOC 2 Type II report, including the complete system description
and list of carved-out components, is available to approved reviewers under NDA.
