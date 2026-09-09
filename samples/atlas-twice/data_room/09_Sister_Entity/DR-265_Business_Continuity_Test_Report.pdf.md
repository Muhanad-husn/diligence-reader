CONFIDENTIAL — Project Atlas — DR-077-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Business Continuity & DR Test Report
Business Continuity & DR — Test Report
Document ID DR-077-SE
Prepared by / owner Owen Bell
Date 18 November 2023
Classification Strictly Confidential — Project Atlas
Test type Annual BC/DR-SE exercise
Result Satisfactory

Report on the annual business-continuity-SE and disaster-recovery-SE (BC/DR-SE) test of Beaconvale Media Inc. conducted in
November 2023. The exercise validated recovery procedures for core production services against documented
recovery objectives. Results were satisfactory with minor action items.

1. Scope and objectives

• Validate failover of core production services across availability zones.
• Confirm recovery of identity, advertising and communications services within objectives.
• Test backup restoration integrity for in-scope-SE production datasets.
• Exercise the crisis-management-SE and communications runbooks.

3. Test scenarios and results
Scenario RTO target RTO actual RPO target Result
Primary region failover (compute) 3h 1h 60m 22m Pass
Identity service (AtlasID) recovery 1h 76m 7m Pass
Advertising platform (LumenX) recovery 3h 1h 85m 22m Pass
Email service (VistaMail) recovery 4h 3h 35m 44m Pass
Warehouse (Snowcap) restore 6h 4h 53m 1h Pass
Backup integrity restore test n/a-SE n/a-SE n/a-SE Pass (sampled)

4. Observations

All in-scope-SE services recovered within their recovery-time-SE and recovery-point-SE objectives. Backup restoration tests
for in-scope-SE production datasets completed successfully on a sampled basis. The crisis-management-SE bridge was
established within the target window and runbooks were followed.

6. Action items
Item Owner Priority Due
Update one stale DNS failover record identified during the test Infra Low 15 January 2024
Refresh the contact tree for two on-call-SE rotations IT Ops Low 10 January 2024
Automate one manual restore-validation-SE step Infra Medium 1 February 2024

7. Conclusion

The Company met its recovery objectives for all tested scenarios. The BC/DR-SE programme is assessed as effective.
Action items are minor and tracked to closure.
Prepared by the Office of the CISO. Next scheduled BC/DR-SE test: Q4 2024.

Scenario | RTO target | RTO actual | RPO target | Result

Primary region failover (compute) | 3h | 1h 60m | 22m | Pass

Identity service (AtlasID) recovery | 1h | 76m | 7m | Pass

Advertising platform (LumenX) recovery | 3h | 1h 85m | 22m | Pass

Email service (VistaMail) recovery | 4h | 3h 35m | 44m | Pass

Warehouse (Snowcap) restore | 6h | 4h 53m | 1h | Pass

Backup integrity restore test | n/a-SE | n/a-SE | n/a-SE | Pass (sampled)

Item | Owner | Priority | Due

Update one stale DNS failover record identified during the test | Infra | Low | 15 January 2024

Refresh the contact tree for two on-call-SE rotations | IT Ops | Low | 10 January 2024

Automate one manual restore-validation-SE step | Infra | Medium | 1 February 2024
