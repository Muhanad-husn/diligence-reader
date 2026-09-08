CONFIDENTIAL — Project Atlas — DR-077 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 1

Business Continuity & DR Test Report
Business Continuity & DR — Test Report
Document ID DR-077
Prepared by / owner Owen Bell
Date 18 November 2025
Classification Strictly Confidential — Project Atlas
Test type Annual BC/DR exercise
Result Satisfactory

Report on the annual business-continuity and disaster-recovery (BC/DR) test of VistaPort Media Inc. conducted in
November 2025. The exercise validated recovery procedures for core production services against documented
recovery objectives. Results were satisfactory with minor action items.

1. Scope and objectives

• Validate failover of core production services across availability zones.
• Confirm recovery of identity, advertising and communications services within objectives.
• Test backup restoration integrity for in-scope production datasets.
• Exercise the crisis-management and communications runbooks.

2. Test scenarios and results
Scenario RTO target RTO actual RPO target Result
Primary region failover (compute) 2h 1h 41m 15m Pass
Identity service (AtlasID) recovery 1h 52m 5m Pass
Advertising platform (LumenX) recovery 2h 1h 58m 15m Pass
Email service (VistaMail) recovery 3h 2h 24m 30m Pass
Warehouse (Snowcap) restore 4h 3h 36m 1h Pass
Backup integrity restore test n/a n/a n/a Pass (sampled)

3. Observations

All in-scope services recovered within their recovery-time and recovery-point objectives. Backup restoration tests
for in-scope production datasets completed successfully on a sampled basis. The crisis-management bridge was
established within the target window and runbooks were followed.

4. Action items
Item Owner Priority Due
Update one stale DNS failover record identified during the test Infra Low 15 January 2026
Refresh the contact tree for two on-call rotations IT Ops Low 10 January 2026
Automate one manual restore-validation step Infra Medium 1 February 2026

5. Conclusion

The Company met its recovery objectives for all tested scenarios. The BC/DR programme is assessed as effective.
Action items are minor and tracked to closure.
Prepared by the Office of the CISO. Next scheduled BC/DR test: Q4 2026.

Scenario | RTO target | RTO actual | RPO target | Result

Primary region failover (compute) | 2h | 1h 41m | 15m | Pass

Identity service (AtlasID) recovery | 1h | 52m | 5m | Pass

Advertising platform (LumenX) recovery | 2h | 1h 58m | 15m | Pass

Email service (VistaMail) recovery | 3h | 2h 24m | 30m | Pass

Warehouse (Snowcap) restore | 4h | 3h 36m | 1h | Pass

Backup integrity restore test | n/a | n/a | n/a | Pass (sampled)

Item | Owner | Priority | Due

Update one stale DNS failover record identified during the test | Infra | Low | 15 January 2026

Refresh the contact tree for two on-call rotations | IT Ops | Low | 10 January 2026

Automate one manual restore-validation step | Infra | Medium | 1 February 2026
