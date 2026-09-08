CONFIDENTIAL — Project Atlas — DR-070 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 1

AURORA — Executive Summary (Final)

AURORA — Executive Summary (Final)

Document ID DR-070
Prepared by / owner Renata Castellano
Date 20 November 2025
Classification Strictly Confidential — Project Atlas
Classification Confidential — Final
Prepared by IronLake Forensics

FINAL. Executive summary of the AURORA review. This summary has been prepared for senior management and
reflects the position as finalised following completion of Phase 1 procedures. It is written to be shared on a
need-to-know basis and should be read together with the underlying privileged work product.
Workstream AURORA

Prepared by Renata Castellano, Engagement Lead, IronLake Forensics
Status FINAL — executive summary
Date 20 November 2025

1. Background

Following the detection of anomalous activity against a historical legacy dataset in the Company’s cloud object
storage, an external review (the AURORA workstream) was commissioned to assess the nature and scope of the
activity and to advise on remediation. This summary sets out the principal conclusions.

2. Key conclusions

• No cleartext passwords were present in the dataset; stored authentication material was in hashed form.
• No payment-card or bank-account data were contained in the dataset.
• No confirmed ongoing attacker persistence was identified within the current production environment at the
time of review.

• The scope of any data acquisition has not been definitively established; the available evidence does not
permit a conclusive determination of what, if anything, was removed.

3. Affected dataset

The activity concerned a historical legacy dataset retained from an earlier account-profile platform. The dataset
comprises historical profile records, a portion of which relate to accounts active in more recent periods.
Authentication material in the dataset was stored in hashed form. The dataset does not contain payment-card or
bank-account information.

4. Authentication considerations

The review noted that legacy authentication signing material would benefit from rotation and retirement, consistent
with the modernisation roadmap. Remediation in this area is recommended as a matter of good hygiene. No
conclusive evidence of exploitation of the production authentication path was established.

5. Recommendations

1 Complete rotation and retirement of legacy authentication signing material.

CONFIDENTIAL — Project Atlas — DR-070 — VistaPort Media Inc. — Subject to NDA & clean-team protocol. Page 2

2 Complete disposition (purge or re-encryption) of the historical legacy dataset and associated backups in line
with policy.
3 Continue enhanced monitoring of the relevant storage and authentication paths.
4 Maintain the credential-hygiene programme already underway across affected accounts.
6. Status and caveats
This is a final executive summary of Phase 1. It necessarily generalises the underlying technical detail and should
not be read as excluding matters addressed in the privileged work product. Certain assessments remain qualified
by the available evidence as described above.
AURORA — final executive summary. Prepared for senior management. To be read with the underlying privileged materials;
distribution restricted.
