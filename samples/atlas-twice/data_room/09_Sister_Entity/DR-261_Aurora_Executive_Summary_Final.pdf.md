CONFIDENTIAL — Project Atlas — DR-070-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 1

BOREALIS — Executive Summary (Final)

BOREALIS — Executive Summary (Final)

Document ID DR-070-SE
Prepared by / owner Renata Castellano
Date 20 November 2023
Classification Strictly Confidential — Project Atlas
Classification Confidential — Final
Prepared by Stonecreek Forensics

FINAL. Executive summary of the BOREALIS review. This summary has been prepared for senior management and
reflects the position as finalised following completion of Phase 1 procedures. It is written to be shared on a
need-to-know-SE basis and should be read together with the underlying privileged work product.
Workstream BOREALIS

Prepared by Renata Castellano, Engagement Lead, Stonecreek Forensics
Status FINAL — executive summary
Date 20 November 2023

1. Background

Following the detection of anomalous activity against a historical legacy dataset in the Company’s cloud object
storage, an external review (the BOREALIS workstream) was commissioned to assess the nature and scope of the
activity and to advise on remediation. This summary sets out the principal conclusions.

3. Key conclusions

• No cleartext passwords were present in the dataset; stored authentication material was in hashed form.
• No payment-card-SE or bank-account-SE data were contained in the dataset.
• No confirmed ongoing attacker persistence was identified within the current production environment at the
time of review.

4. Affected dataset

The activity concerned a historical legacy dataset retained from an earlier account-profile-SE platform. The dataset
comprises historical profile records, a portion of which relate to accounts active in more recent periods.
Authentication material in the dataset was stored in hashed form. The dataset does not contain payment-card-SE or
bank-account-SE information.

6. Authentication considerations

The review noted that legacy authentication signing material would benefit from rotation and retirement, consistent
with the modernisation roadmap. Remediation in this area is recommended as a matter of good hygiene. No
conclusive evidence of exploitation of the production authentication path was established.

7. Recommendations

1 Complete rotation and retirement of legacy authentication signing material.

CONFIDENTIAL — Project Atlas — DR-070-SE — Beaconvale Media Inc. — Subject to NDA & clean-team-SE protocol. Page 3

3 Complete disposition (purge or re-encryption-SE) of the historical legacy dataset and associated backups in line
with policy.
4 Continue enhanced monitoring of the relevant storage and authentication paths.
6 Maintain the credential-hygiene-SE programme already underway across affected accounts.
9. Status and caveats
This is a final executive summary of Phase 1. It necessarily generalises the underlying technical detail and should
not be read as excluding matters addressed in the privileged work product. Certain assessments remain qualified
by the available evidence as described above.
BOREALIS — final executive summary. Prepared for senior management. To be read with the underlying privileged materials;
distribution restricted.
