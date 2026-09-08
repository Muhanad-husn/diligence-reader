CONFIDENTIAL — Project Atlas — DR-063 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 1

Penetration Test 2025 — Executive Summary
Penetration Test 2025 — Executive Summary
Document ID DR-063
Prepared by / owner Nina Petrov
Date 22 September 2025
Classification Strictly Confidential — Project Atlas
Assessor Independent (grey-box)
Test owner Nina Petrov, Head of Security Engineering

Executive summary of the FY2025 annual external penetration test of VistaPort Media Inc.’s internet-facing
services, authentication and identity platforms. Testing was performed by an independent assessor under a
grey-box methodology. This summary is provided for diligence; the full technical report and remediation tracker are
available on request.

1. Scope and approach
•
Internet-facing web and API surfaces across core consumer properties.
• Authentication and session management (VPAuth, SSOBridge) including token handling.
• Cloud configuration review of the primary object-storage and compute estate.

• Excluded: third-party managed services and components in active decommission (see legacy-component note
below).

2. Overall result

The estate presented a generally strong security posture. No critical internet-facing vulnerabilities were
exploitable to a full compromise during the engagement. The majority of findings were low or informational. A small
number of medium findings relate to legacy authentication components scheduled for modernisation and are
summarised below.

Severity Count Status
Critical 0 —
High 0 —
Medium 4 Remediation planned
Low 11 Tracked
Informational 9 Noted

3. Notable findings — legacy authentication components

Two related medium findings concern legacy elements of the authentication and backup estate. Both are flagged
for remediation under the modernisation roadmap; neither was independently exploited during testing but each
represents weak hygiene that should be closed.

Ref Finding Severity Recommendation
PT-25-007 Weak key-rotation hygiene on a legacy session-signing key.
A legacy VPAuth signing key has not been rotated within
policy; long-lived signing material increases the impact of
any key compromise.
Medium Rotate the legacy signing key and
retire it from the active validation set;
enforce automated rotation.

Severity | Count | Status

Critical | 0 | —

High | 0 | —

Medium | 4 | Remediation planned

Low | 11 | Tracked

Informational | 9 | Noted

Ref | Finding | Severity | Recommendation

PT-25-007 | Weak key-rotation hygiene on a legacy session-signing key.
A legacy VPAuth signing key has not been rotated within
policy; long-lived signing material increases the impact of
any key compromise. | Medium | Rotate the legacy signing key and
retire it from the active validation set;
enforce automated rotation.

CONFIDENTIAL — Project Atlas — DR-063 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 2

Ref Finding Severity Recommendation
PT-25-011 Over-retained backup with weak encryption. A historical
account-profile backup is retained beyond the data-retention
policy window and is protected with a weak/legacy
encryption scheme.
Medium Purge or re-encrypt the backup to
current standards; bring retention into
policy and document disposition.

PT-25-014 Stale privileged/service accounts on legacy storage paths. Medium Disable unused privileged accounts;
tighten access to backup storage.

4. Recommendations and timeline
1 Prioritise rotation of legacy signing material ahead of the wider VPAuth migration.
2 Complete purge/re-encryption of over-retained backups and confirm policy compliance.
3 Remediate stale privileged accounts and complete the next quarterly access review.
4 Re-test the legacy authentication findings after remediation.

Medium findings on legacy authentication components are expected to be closed under the FY2026 modernisation roadmap.
Assessor’s full report retained by Security Engineering.

Ref | Finding | Severity | Recommendation

PT-25-011 | Over-retained backup with weak encryption. A historical
account-profile backup is retained beyond the data-retention
policy window and is protected with a weak/legacy
encryption scheme. | Medium | Purge or re-encrypt the backup to
current standards; bring retention into
policy and document disposition.

PT-25-014 | Stale privileged/service accounts on legacy storage paths. | Medium | Disable unused privileged accounts;
tighten access to backup storage.
