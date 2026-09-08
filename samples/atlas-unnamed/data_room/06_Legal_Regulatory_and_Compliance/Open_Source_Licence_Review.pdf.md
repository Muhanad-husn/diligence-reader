CONFIDENTIAL — Project Atlas — DR-090 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 1

Open Source Licence Review
Open-Source Software — Licence Compliance Review
Document ID DR-090
Prepared by / owner Hannah Brooks
Date 25 November 2025
Classification Strictly Confidential — Project Atlas

Open-Source Licence Review. This review summarises open-source software usage across the Company's
principal products and identifies a small number of licence-compliance items for remediation. The overall position is
sound; the items below are low-cost and low-effort.
Prepared by Hannah Brooks, Deputy General Counsel
Scope Principal product codebases and build pipelines
Method Automated SCA scan plus manual review of flagged components
Overall assessment Compliant, with minor remediation (see below)

1. Summary of findings
Component Licence Product Issue Remediation
fastcodec GPL-2.0 Media transcoding service Copyleft component
statically linked
Replace with permissive alternative
or isolate via service boundary
gridcache LGPL-3.0 Edge caching layer Dynamic-link obligation;
written-offer notice missing
Add written offer & attribution;
confirm dynamic linking
tinyparse GPL-3.0 Internal tooling only Copyleft in an internal tool
(not distributed)
Confirm non-distribution; document
internal-use position
zlibext Zlib Multiple Attribution notice incomplete Update NOTICE file

2. Risk assessment

• No copyleft obligation has triggered any source-disclosure event affecting proprietary code to date.
• The principal item (fastcodec, GPL-2.0) is confined to one service and is straightforward to remediate by
component replacement or isolation.
• Estimated remediation effort is modest: a few engineering weeks across the items, with no material cost.

3. Remediation plan
1 Replace or isolate the GPL-2.0 component in the transcoding service (target: next quarter).
2 Add the missing LGPL written offer and attribution notices.
3 Refresh NOTICE files and re-run the SCA scan to confirm closure.
4 Add an SCA gate to the build pipeline to prevent regression.
Minor, well-understood compliance items with a clear remediation path and immaterial cost. Maintained by the Office of the General
Counsel.

Component | Licence | Product | Issue | Remediation

fastcodec | GPL-2.0 | Media transcoding service | Copyleft component
statically linked | Replace with permissive alternative
or isolate via service boundary

gridcache | LGPL-3.0 | Edge caching layer | Dynamic-link obligation;
written-offer notice missing | Add written offer & attribution;
confirm dynamic linking

tinyparse | GPL-3.0 | Internal tooling only | Copyleft in an internal tool
(not distributed) | Confirm non-distribution; document
internal-use position

zlibext | Zlib | Multiple | Attribution notice incomplete | Update NOTICE file
