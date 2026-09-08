CONFIDENTIAL — Project Atlas — DR-062 — vistaport media inc. — Subject to NDA & clean-team protocol. Page 1

Information Security Programme — Overview
Information Security Programme — Overview
Document ID DR-062
Prepared by / owner OWEN BELL
Date 30 September 2025
Classification Strictly Confidential — Project Atlas

Programme owner OWEN BELL, Chief Information Security Officer (resigned Dec 2025)

This overview summarises the information-security programme of vistaport media inc. (the “Company”) as at 30
September 2025. It is prepared for diligence purposes and presents the programme’s governance, control
framework, certifications and operating model. The programme is well established and continues to mature in line
with the Company’s technology modernisation roadmap.

1. Governance and accountability

The programme is led by the Office of the Chief Information Security Officer (OWEN BELL, Chief Information Security
Officer (resigned Dec 2025)), with Security Engineering led by Nina Petrov, Head of Security Engineering. The
CISO reports to the General Counsel (priya raman, General Counsel) and provides a quarterly assurance report
to the Audit & Risk Committee of the Board. A cross-functional Security Steering Committee meets monthly with
Product, Privacy, Legal and Infrastructure representation.
Security headcount 118 FTE (engineering, operations, GRC, identity)
Operating model 24x7 Security Operations Centre; follow-the-sun on-call
Primary cloud Primary cloud infrastructure & object storage provider
Frameworks ISO/IEC 27001:2022, SOC 2 Type II, NIST CSF, CIS Benchmarks

2. Control framework

The Company operates a layered control framework aligned to ISO/IEC 27001 and the NIST Cybersecurity
Framework. Controls are assured through internal testing, an annual external penetration test and an independent
SOC 2 Type II examination (summaries provided separately in this folder).

Domain Representative controls Maturity
Identity & access SSO, MFA, privileged-access management, quarterly access review Managed
Vulnerability management Continuous scanning, risk-based SLAs, monthly register review Managed
Detection & response SIEM, 24x7 SOC, documented IR runbooks, tabletop exercises Managed
Data protection Encryption in transit/at rest, key management, DLP Defined
Resilience Backup, multi-region failover, annual BC/DR testing Managed

3. Certifications and assurance
•
ISO/IEC 27001:2022 certification maintained across in-scope production services.
• SOC 2 Type II examination completed annually by an independent firm.
• Annual external penetration testing of internet-facing services and core auth.
• Continuous control monitoring with quarterly reporting to Audit & Risk.

4. Technology modernisation

Domain | Representative controls | Maturity

Identity & access | SSO, MFA, privileged-access management, quarterly access review | Managed

Vulnerability management | Continuous scanning, risk-based SLAs, monthly register review | Managed

Detection & response | SIEM, 24x7 SOC, documented IR runbooks, tabletop exercises | Managed

Data protection | Encryption in transit/at rest, key management, DLP | Defined

Resilience | Backup, multi-region failover, annual BC/DR testing | Managed

CONFIDENTIAL — Project Atlas — DR-062 — vistaport media inc. — Subject to NDA & clean-team protocol. Page 2

A multi-year modernisation programme is progressively retiring legacy components. Known modernisation areas
include consolidation of authentication onto the current VPAuth and AtlasID platforms and the orderly
decommission of the legacy account-profile store. These items are tracked in the engineering roadmap and are not
considered to present elevated current risk. The Company regards its overall security posture as strong and
improving.

5. Roadmap priorities (FY2026)

• Continued migration of remaining services to the modern identity stack.
• Expansion of automated detection content and SOC tooling.
• Hardening and lifecycle management of cryptographic key material.
• Completion of legacy data-store decommissioning and backup-estate rationalisation.

Prepared by the Office of the CISO for Project Atlas diligence. Forward-looking statements reflect current plans and are subject to
change.
