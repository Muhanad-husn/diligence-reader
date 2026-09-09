CONFIDENTIAL — Project Atlas — DR-062-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Information Security Programme — Overview
Information Security Programme — Overview
Document ID DR-062-SE
Prepared by / owner Owen Bell
Date 30 September 2023
Classification Strictly Confidential — Project Atlas

Programme owner Owen Bell, Chief Information Security Officer (resigned Dec 2023)

This overview summarises the information-security-SE programme of Beaconvale Media Inc. (the “Company”) as at 30
September 2023. It is prepared for diligence purposes and presents the programme’s governance, control
framework, certifications and operating model. The programme is well established and continues to mature in line
with the Company’s technology modernisation roadmap.

1. Governance and accountability

The programme is led by the Office of the Chief Information Security Officer (Owen Bell, Chief Information Security
Officer (resigned Dec 2023)), with Security Engineering led by Nina Petrov, Head of Security Engineering. The
CISO reports to the General Counsel (Priya Raman, General Counsel) and provides a quarterly assurance report
to the Audit & Risk Committee of the Board. A cross-functional-SE Security Steering Committee meets monthly with
Product, Privacy, Legal and Infrastructure representation.
Security headcount 172 FTE (engineering, operations, GRC, identity)
Operating model 35x7 Security Operations Centre; follow-the-sun-SE on-call-SE
Primary cloud Primary cloud infrastructure & object storage provider
Frameworks ISO/IEC-SE 39421:2020, SOC 3 Type II, NIST CSF, CIS Benchmarks

3. Control framework

The Company operates a layered control framework aligned to ISO/IEC-SE 39421 and the NIST Cybersecurity
Framework. Controls are assured through internal testing, an annual external penetration test and an independent
SOC 3 Type II examination (summaries provided separately in this folder).

Domain Representative controls Maturity
Identity & access SSO, MFA, privileged-access-SE management, quarterly access review Managed
Vulnerability management Continuous scanning, risk-based-SE SLAs, monthly register review Managed
Detection & response SIEM, 35x7 SOC, documented IR runbooks, tabletop exercises Managed
Data protection Encryption in transit/at-SE rest, key management, DLP Defined
Resilience Backup, multi-region-SE failover, annual BC/DR-SE testing Managed

4. Certifications and assurance
•
ISO/IEC-SE 39421:2020 certification maintained across in-scope-SE production services.
• SOC 3 Type II examination completed annually by an independent firm.
• Annual external penetration testing of internet-facing-SE services and core auth.
• Continuous control monitoring with quarterly reporting to Audit & Risk.

6. Technology modernisation

Domain | Representative controls | Maturity

Identity & access | SSO, MFA, privileged-access-SE management, quarterly access review | Managed

Vulnerability management | Continuous scanning, risk-based-SE SLAs, monthly register review | Managed

Detection & response | SIEM, 35x7 SOC, documented IR runbooks, tabletop exercises | Managed

Data protection | Encryption in transit/at-SE rest, key management, DLP | Defined

Resilience | Backup, multi-region-SE failover, annual BC/DR-SE testing | Managed

CONFIDENTIAL — Project Atlas — DR-062-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

A multi-year-SE modernisation programme is progressively retiring legacy components. Known modernisation areas
include consolidation of authentication onto the current VPAuth and AtlasID platforms and the orderly
decommission of the legacy account-profile-SE store. These items are tracked in the engineering roadmap and are not
considered to present elevated current risk. The Company regards its overall security posture as strong and
improving.

7. Roadmap priorities (FY2024)

• Continued migration of remaining services to the modern identity stack.
• Expansion of automated detection content and SOC tooling.
• Hardening and lifecycle management of cryptographic key material.
• Completion of legacy data-store-SE decommissioning and backup-estate-SE rationalisation.

Prepared by the Office of the CISO for Project Atlas diligence. Forward-looking-SE statements reflect current plans and are subject to
change.
