CONFIDENTIAL — Project Atlas — DR-055 — VistaPort Media, Inc.. — Subject to NDA & clean-team protocol. Page 1

Personalisation Model — Performance Review
VistaPort Media, Inc.. — Product Data and Technology
Document ID DR-055
Prepared by / owner Maya Hart
Date 22 December 2025
Classification Strictly Confidential — Project Atlas
Function Product / ML
Period Q4 2025 review

Quarterly performance review of the logged-in personalisation and identity-match models. The review covers
model quality metrics, observed degradation and remediation. Figures are derived from production logs in the
Snowcap warehouse.

1. Headline

• A measurable degradation in the logged-in identity match rate and in personalised click-through rate (CTR)
emerged from October 2025, deepening in November before a partial recovery in December.
• The degradation is attributed to addressability headwinds — a reduced logged-in addressable pool — rather
than to model regression. Offline model quality metrics were stable over the period.

2. Metric trend
Month Logged-in identity match rate Personalised CTR Match-rate change vs Aug
Aug 2025 71.4% 0.840% +0.0%
Sep 2025 71.4% 0.839% +0.0%
Oct 2025 69.8% 0.827% -2.2%
Nov 2025 67.0% 0.799% -6.2%
Dec 2025 68.3% 0.813% -4.3%

Index basis: August 2025 = 1.000. Match rate and CTR move with the logged-in addressable pool, not with offline model AUC, which
was flat (±0.3%).

3. Root-cause assessment

The models themselves did not regress. The decline tracks a contraction in the logged-in addressable pool from
late October, coincident with elevated re-authentication and the Trust Reset credential-hygiene activity, which
reduced the volume of resolvable logged-in sessions available to the identity-match layer. Fewer resolvable
sessions mean fewer high-confidence matches, which mechanically lowers personalised CTR even when ranking
quality is unchanged.

4. Correlation with engagement

The match-rate trough aligns with the Q4 low in logged-in engagement (see the user metrics dashboard, DR-048,
and VistaMail KPIs, DR-050). The personalisation yield index bottomed in the week commencing 10 November
2025 and has been recovering since.

5. Remediation

• Rebuild affected logged-in lookalike segments as the addressable pool recovers.
• Re-onboarding and re-consent flows to restore resolvable sessions.

Month | Logged-in identity match rate | Personalised CTR | Match-rate change vs Aug

Aug 2025 | 71.4% | 0.840% | +0.0%

Sep 2025 | 71.4% | 0.839% | +0.0%

Oct 2025 | 69.8% | 0.827% | -2.2%

Nov 2025 | 67.0% | 0.799% | -6.2%

Dec 2025 | 68.3% | 0.813% | -4.3%

CONFIDENTIAL — Project Atlas — DR-055 — VistaPort Media, Inc.. — Subject to NDA & clean-team protocol. Page 2

• Personalisation model refresh scheduled in the 2026 roadmap (DR-047).
6. Outlook
Match rate and CTR are expected to return toward pre-Q4 levels as logged-in engagement normalises and
re-onboarding completes. Recovery has been slower than modelled and remains a watch item for FY2026
monetisation.
Prepared by Personalisation Engineering; owner Maya Hart, VP Product, Identity and Mail.
