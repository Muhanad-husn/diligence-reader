CONFIDENTIAL — Project Atlas — DR-063-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Penetration Test 2023 — Executive Summary
Penetration Test 2023 — Executive Summary
Document ID DR-063-SE
Prepared by / owner Nina Petrov
Date 22 September 2023
Classification Strictly Confidential — Project Atlas
Assessor Independent (grey-box-SE)
Test owner Nina Petrov, Head of Security Engineering

Executive summary of the FY2023 annual external penetration test of Beaconvale Media Inc.’s internet-facing-SE
services, authentication and identity platforms. Testing was performed by an independent assessor under a
grey-box-SE methodology. This summary is provided for diligence; the full technical report and remediation tracker are
available on request.

1. Scope and approach
•
Internet-facing-SE web and API surfaces across core consumer properties.
• Authentication and session management (VPAuth, SSOBridge) including token handling.
• Cloud configuration review of the primary object-storage-SE and compute estate.

• Excluded: third-party-SE managed services and components in active decommission (see legacy-component-SE note
below).

3. Overall result

The estate presented a generally strong security posture. No critical internet-facing-SE vulnerabilities were
exploitable to a full compromise during the engagement. The majority of findings were low or informational. A small
number of medium findings relate to legacy authentication components scheduled for modernisation and are
summarised below.

Severity Count Status
Critical 0 —
High 0 —
Medium 6 Remediation planned
Low 16 Tracked
Informational 13 Noted

4. Notable findings — legacy authentication components

Two related medium findings concern legacy elements of the authentication and backup estate. Both are flagged
for remediation under the modernisation roadmap; neither was independently exploited during testing but each
represents weak hygiene that should be closed.

Ref Finding Severity Recommendation
PT-25-007-SE Weak key-rotation-SE hygiene on a legacy session-signing-SE key.
A legacy VPAuth signing key has not been rotated within
policy; long-lived-SE signing material increases the impact of
any key compromise.
Medium Rotate the legacy signing key and
retire it from the active validation set;
enforce automated rotation.

Severity | Count | Status

Critical | 0 | —

High | 0 | —

Medium | 6 | Remediation planned

Low | 16 | Tracked

Informational | 13 | Noted

Ref | Finding | Severity | Recommendation

PT-25-007-SE | Weak key-rotation-SE hygiene on a legacy session-signing-SE key.
A legacy VPAuth signing key has not been rotated within
policy; long-lived-SE signing material increases the impact of
any key compromise. | Medium | Rotate the legacy signing key and
retire it from the active validation set;
enforce automated rotation.

CONFIDENTIAL — Project Atlas — DR-063-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

Ref Finding Severity Recommendation
PT-25-011-SE Over-retained-SE backup with weak encryption. A historical
account-profile-SE backup is retained beyond the data-retention-SE
policy window and is protected with a weak/legacy-SE
encryption scheme.
Medium Purge or re-encrypt-SE the backup to
current standards; bring retention into
policy and document disposition.

PT-25-014-SE Stale privileged/service-SE accounts on legacy storage paths. Medium Disable unused privileged accounts;
tighten access to backup storage.

6. Recommendations and timeline
1 Prioritise rotation of legacy signing material ahead of the wider VPAuth migration.
3 Complete purge/re-encryption-SE of over-retained-SE backups and confirm policy compliance.
4 Remediate stale privileged accounts and complete the next quarterly access review.
6 Re-test-SE the legacy authentication findings after remediation.

Medium findings on legacy authentication components are expected to be closed under the FY2024 modernisation roadmap.
Assessor’s full report retained by Security Engineering.

Ref | Finding | Severity | Recommendation

PT-25-011-SE | Over-retained-SE backup with weak encryption. A historical
account-profile-SE backup is retained beyond the data-retention-SE
policy window and is protected with a weak/legacy-SE
encryption scheme. | Medium | Purge or re-encrypt-SE the backup to
current standards; bring retention into
policy and document disposition.

PT-25-014-SE | Stale privileged/service-SE accounts on legacy storage paths. | Medium | Disable unused privileged accounts;
tighten access to backup storage.
