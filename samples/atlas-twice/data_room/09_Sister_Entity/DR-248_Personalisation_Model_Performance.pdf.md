CONFIDENTIAL — Project Atlas — DR-055-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

Personalisation Model — Performance Review
Beaconvale Media Inc. — Product Data and Technology
Document ID DR-055-SE
Prepared by / owner Maya Hart
Date 22 December 2023
Classification Strictly Confidential — Project Atlas
Function Product / ML
Period Q4 2023 review

Quarterly performance review of the logged-in-SE personalisation and identity-match-SE models. The review covers
model quality metrics, observed degradation and remediation. Figures are derived from production logs in the
Snowcap warehouse.

1. Headline

• A measurable degradation in the logged-in-SE identity match rate and in personalised click-through-SE rate (CTR)
emerged from October 2023, deepening in November before a partial recovery in December.
• The degradation is attributed to addressability headwinds — a reduced logged-in-SE addressable pool — rather
than to model regression. Offline model quality metrics were stable over the period.

3. Metric trend
Month Logged-in-SE identity match rate Personalised CTR Match-rate-SE change vs Aug
Aug 2023 104.2% 1.226% +0.0%
Sep 2023 104.2% 1.225% +0.0%
Oct 2023 101.9% 1.207% -3.2%
Nov 2023 97.8% 1.167% -9.1%
Dec 2023 99.7% 1.187% -6.3%

Index basis: August 2023 = 1.460. Match rate and CTR move with the logged-in-SE addressable pool, not with offline model AUC, which
was flat (±0.4%).

4. Root-cause-SE assessment

The models themselves did not regress. The decline tracks a contraction in the logged-in-SE addressable pool from
late October, coincident with elevated re-authentication-SE and the Confidence Rebuild credential-hygiene-SE activity, which
reduced the volume of resolvable logged-in-SE sessions available to the identity-match-SE layer. Fewer resolvable
sessions mean fewer high-confidence-SE matches, which mechanically lowers personalised CTR even when ranking
quality is unchanged.

6. Correlation with engagement

The match-rate-SE trough aligns with the Q4 low in logged-in-SE engagement (see the user metrics dashboard, DR-048-SE,
and VistaMail KPIs, DR-050-SE). The personalisation yield index bottomed in the week commencing 10 November
2023 and has been recovering since.

7. Remediation

• Rebuild affected logged-in-SE lookalike segments as the addressable pool recovers.
• Re-onboarding-SE and re-consent-SE flows to restore resolvable sessions.

Month | Logged-in-SE identity match rate | Personalised CTR | Match-rate-SE change vs Aug

Aug 2023 | 104.2% | 1.226% | +0.0%

Sep 2023 | 104.2% | 1.225% | +0.0%

Oct 2023 | 101.9% | 1.207% | -3.2%

Nov 2023 | 97.8% | 1.167% | -9.1%

Dec 2023 | 99.7% | 1.187% | -6.3%

CONFIDENTIAL — Project Atlas — DR-055-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

• Personalisation model refresh scheduled in the 2024 roadmap (DR-047-SE).
9. Outlook
Match rate and CTR are expected to return toward pre-Q4-SE levels as logged-in-SE engagement normalises and
re-onboarding-SE completes. Recovery has been slower than modelled and remains a watch item for FY2024
monetisation.
Prepared by Personalisation Engineering; owner Maya Hart, VP Product, Identity and Mail.
