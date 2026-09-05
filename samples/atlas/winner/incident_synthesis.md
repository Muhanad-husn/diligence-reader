# PROJECT ATLAS — BUY-SIDE DILIGENCE: CONNECTED-THREAD ANALYSIS
## VistaPort Media Inc. — Security Incident (AURORA / NQ-17 / Trust Reset)
*Prepared for: Northstar M&A Diligence — Strictly Confidential*

---

## 1. MASTER TIMELINE

| Date | Event | Source |
|------|-------|--------|
| **2019-02-11** | `vpauth-legacy-2019` session-signing key last rotated. Standing exception applied; annually renewed 2023, 2024, 2025 by CISO O. Bell. Rotation "blocked by legacy session compatibility." | DR-071 |
| **2021-07-31** | `legacy_uap_backup_2021.tar.gz` created; `legacy-uap-backup-key` last rotated. Exception for key retained "pending decommission of legacy_uap"; annually renewed 2024, 2025 by N. Petrov. | DR-071 |
| **14 Nov 2024** | Board Q4 2024: "information-security assurance programme was operating as expected." "No new material risks were reported." | DR-008 |
| **20 Feb 2025** | Board Q1 2025: "privacy programme and information-security assurance were reported as operating effectively. No material matters were raised." | DR-009 |
| **15 May 2025** | Board Q2 2025 approves Canton Street Capital engagement; data-room preparation authorised. Board: "emphasised the importance of accuracy and completeness of diligence materials." | DR-010 |
| **14 Aug 2025** | Board Q3 2025: legacy_uap decommission re-phased to 2026. "Privacy programme and information-security assurance were reported as operating effectively. No material matters were raised at this meeting." | DR-011 |
| **~18 Oct 2025** | **FIRST DETECTION.** Earliest anomalous bulk reads of `legacy_uap_backup_2021.tar.gz` from foreign ASNs not in any restore schedule. | DR-013, DR-068, DR-069 |
| **18–20 Oct 2025** | 5 distinct bulk-read events. Cumulative egress on legacy backup prefix: **~1,840 GB**. Source IPs resolve to **3 foreign autonomous systems**. Abnormal VPAuth token validation on the legacy signing key. ~41,500 suspected forged/replayed session events observed. | DR-069 |
| **20 Oct 2025** | Anomalous activity ceases. Session-validation patterns noted for review. | DR-013 |
| **21 Oct 2025 09:42** | Nina Petrov (Head of Security Engineering) opens internal ticket. Explicit characterisation: *"this does not look like a network problem. The signature is unauthorised BULK ACCESS to the legacy_uap backup, not latency...This is BULK ACCESS, full stop."* Recommends treating as suspected security incident and engaging forensics. | DR-068 |
| **21 Oct 2025 10:05** | Petrov confirms object-store logs show "repeated GET/READ on legacy_uap_backup_2021.tar.gz across 18-20 Oct with egress far above baseline." | DR-068 |
| **21 Oct 2025 14:18** | SOC Tier 2 analyst concurs: "Correlated SIEM alerts (objstore.bulk_read.anomaly, egress.spike) cluster on 18, 19 and 20 October. Also abnormal VPAuth token validation on the legacy signing key." | DR-068 |
| **21 Oct 2025** | Internal investigation opened by Security Engineering. | DR-013 |
| **22 Oct 2025 11:30** | CISO Owen Bell acknowledges and escalates to GC/Legal: *"Escalating to GC/Legal for handling. Pending counsel, keep characterisation factual and avoid conclusions in the ticket text."* | DR-068 |
| **23 Oct 2025 09:10** | **Management/Programme Office reclassifies ticket.** NQ-17 assigned as "network-quality / performance matter." Order issued: *"Bulk-access and breach terminology is to be removed from the summary field pending forensic confirmation. Reassigning to Network Operations. Security findings to continue under a separate privileged workstream."* | DR-068 |
| **23 Oct 2025 09:34** | Petrov logs formal disagreement on record: *"Logging my disagreement with the reclassification. Renaming this to network quality does not change what the legacy_uap_backup_2021.tar.gz logs show for the 18 October 2025 window. Noting for the record."* | DR-068 |
| **23 Oct 2025** | Network Operations reviews: finds "No customer-facing latency SLO breach." | DR-068 |
| **27 Oct 2025** | IronLake Forensics engaged on expedited basis under privileged workstream AURORA. | DR-013, DR-068 |
| **29 Oct 2025** | **Disclosure Committee convenes.** Notes anomalous activity 18–20 Oct. Concludes: "materiality...is not yet determinable." Directs all functions to *"avoid speculative or conclusory terminology (including characterising the matter as a confirmed breach or exfiltration) in internal and external communications."* Defers disclosure decision. | DR-013 |
| **29 Oct 2025 12:15** | NQ-17 ticket closed as "Closed — reclassified." Summary field updated to remove prior characterisation. | DR-068 |
| **31 Oct 2025** | Trust Reset project brief published. Scope: **~286m forced resets** planned; **~511m active sessions** to invalidate. Describes programme as "proactive maintenance of credential and session integrity." | DR-059 |
| **3 Nov 2025** | Trust Reset Wave 1 begins. | DR-059, DR-060 |
| **5 Nov 2025** | Executive Committee action items (AI-01 through AI-08): communications hold on AURORA maintained; ban on "breach or exfiltration terminology in writing"; forensic liaison with IronLake ongoing; insurance and regulatory engagement options in preparation. | DR-014 |
| **5 Nov 2025** | Login-failure rates and reset volumes rise; support queues lengthen. | DR-060 |
| **10 Nov 2025** | Trust Reset Wave 2 (main population). Peak weekly password-reset volume: **31.2m**. Peak login-failure rate: **5.1%**. | DR-060 |
| **10 Nov 2025** | Disclosure Controls & Procedures Memo (DR-086): AURORA listed as "OPEN — escalation question unresolved." | DR-086 |
| **12 Nov 2025** | **IronLake Phase 1 draft technical findings.** Finds: ~912.8m total historical profile records; ~286m active-within-24m; ~1,840 GB egress; 5 bulk-read events; 3 foreign ASNs; ~41,500 suspected forged/replayed session events; legacy signing key unrotated since 2019. Conclusion: *"a bulk export is probable."* | DR-069 |
| **14 Nov 2025** | Irish DPC informal inquiry received re user reset notifications and account access questions. | DR-080 |
| **17 Nov 2025** | Trust Reset reminder waves; load easing. | DR-060 |
| **20 Nov 2025** | **IronLake AURORA final executive summary.** Conclusions deliberately softened from draft: *"the scope of any data acquisition has not been definitively established; the available evidence does not permit a conclusive determination of what, if anything, was removed."* | DR-070 |
| **24 Nov 2025** | Draft DPC response (v0.3): characterises Trust Reset as "proactive account-security measure"; asserts *"the Company has not established that personal data was exfiltrated."* Tracked deletion removes prior language *"the Company is confident no data left its environment"* — outside counsel: *"we cannot say this; the forensic position is not settled."* | DR-080 |
| **28 Nov 2025** | Product postmortem characterises entire matter as "login friction / availability — SEV-2 (degraded experience, no service outage)." States: *"It is not a security-incident report."* | DR-060 |
| **4 Dec 2025** | Karl Webb (Treasury) emails Priya Raman: *"If awareness is measured from the 21 October internal ticket, the 45-day window runs to around 5 December — i.e. essentially now."* Recommends holding notice to Redbridge. | DR-100 |
| **5 Dec 2025** | Priya Raman responds: *"The Phase 1 material is a privileged draft and is more definitive than I think is warranted; the final executive summary is softer. I would rather the notice reflect the final. Let us treat awareness as a question for counsel — receipt of the final summary is a defensible reference point. Please hold the formal notice until we have agreed wording."* | DR-100 |
| **8 Dec 2025** | Outside counsel Juniper & Rowe preliminary exposure memo: indicative aggregate **$240m–$465m**. | DR-088 |
| **11 Dec 2025** | Board Q4 2025: GC introduces "account integrity workstream" and "Trust Reset...staged credential-hygiene measures...intended to maintain account hygiene...described as operational matters." AURORA referenced; "materiality of the matter is not yet determined." Board told engagement metric softness attributed to "seasonality and short-term operational factors." | DR-012 |
| **11 Dec 2025** | Karl Webb emails broker draft insurance notice (DR-082): *"I am genuinely unsure whether, for notice purposes, we describe the circumstance as AURORA (the forensic review of the October activity) or simply as the Trust Reset credential-hygiene programme."* Acknowledges: *"I am conscious we are past the date that the more conservative reading of the 45-day clock would imply."* | DR-082 |
| **11 Dec 2025** | Webb to broker Delacroix: *"Counsel would prefer the notice describe the Trust Reset programme and an associated review rather than lead with a breach characterisation."* | DR-100 |
| **12 Dec 2025** | Broker Delacroix warns: *"describing the matter solely as a 'Trust Reset' programme, when the internal review (AURORA) examines unauthorised access, could be read as under-notification."* Also flags that framing awareness from final summary "is a position they may test." | DR-100 |
| **12 Dec 2025** | Priya Raman to Renata Castellano (IronLake): confirms IronLake *"generalised some of the draft's quantitative language in the final per counsel's direction."* | DR-100 |
| **15 Dec 2025** | Security Steering Committee: CISO Bell records formal dissent on characterisation and notification pace. Security Engineering (Petrov) advocates "broader user notification and earlier, proactive regulator engagement." Legal urges restraint. Commercial flags advertiser sensitivities. Finance notes reserve implications. Insurance notice position flagged as requiring "prompt resolution." | DR-075 |
| **Dec 2025** | CISO Owen Bell resigns. Principal Security Engineer (Authentication) and Staff Security Engineer (Key Management) give notice. | DR-095 |
| **18 Dec 2025** | Class-action monitoring memo notes sector analogues for large-scale credential/profile breaches imply aggregate settlement reserves "in the tens to low hundreds of millions of dollars." | DR-089 |
| **29 Dec 2025** | Owen Bell emails Daniel Cho: *"I cannot reconcile a $12m reserve with the technical picture. The legacy backup at the centre of this covers ~912.8m historical profiles, of which ~286m are active within 24 months, and the signing-key issue makes session forging feasible. Outside counsel's working range is materially higher than $12m once notification, regulatory and litigation heads are included."* | DR-100 |
| **30 Dec 2025** | Daniel Cho responds: *"accounting requires a reliably estimable amount, and we do not have a confirmed reportable event or an agreed quantum. On that basis a proportionate $12m trust-and-safety contingency is what I can support today."* CFO reserve memo filed: **$12m** (DR-029). | DR-029, DR-100 |
| **Jan 2026** | Senior Security Engineer (Detection & Response) gives notice. | DR-095 |
| **6 Jan 2026** | HR attrition memo: CISO + 3 senior security engineers departed; exit interviews cite *"how the October account-integrity event was characterised internally, and about the degree of cross-functional alignment between Security, Legal and Finance on the response."* | DR-095 |
| **8 Jan 2026** | Strategic Alternatives Board Deck for Northstar: *"One open workstream (account integrity) is being managed by management and counsel; it is kept under review and is not expected, on current information, to be quantified at this stage."* | DR-015 |
| **25 Jan 2026** | Seller Representation Schedule (draft): Disclosure Schedule entries against Rep 7.1 describe only "routine credential-hygiene programme" and "legacy systems pending decommissioning." No specific incident disclosed. | DR-087 |

---

## 2. WHAT ACTUALLY HAPPENED: THE MOST LIKELY TRUE NARRATIVE

### Root Cause

VistaPort retained a 2021-era backup of its legacy Unified Account Profile store (`legacy_uap_backup_2021.tar.gz`) in its Kestrel cloud object store. Two compounding security failures created the exposure:

1. **The backup itself**: The `legacy-uap-backup-key` had not been rotated since 2021, with a risk-accepted exception renewed annually (DR-071). The backup had not been purged despite the legacy_uap decommission being re-phased to 2026 (DR-011).

2. **The session-signing key**: The VPAuth legacy session-signing key `kid=vpauth-legacy-2019` had not been rotated since **2019**, with CISO Bell renewing the exception in 2023, 2024, and 2025 on grounds that rotation *"would invalidate long-lived sessions on deprecated clients"* (DR-071).

### The Exfiltration

On **18 October 2025**, source IP addresses resolving to **3 foreign autonomous systems** not present in any documented restore schedule conducted **5 distinct anomalous bulk-read events** against `legacy_uap_backup_2021.tar.gz` over three days (18–20 October). Cumulative egress on the legacy backup prefix reached approximately **1,840 GB** (DR-069). IronLake's Phase 1 draft, the operative technical conclusion, stated unambiguously: *"a bulk export is probable; the read volume and egress are consistent with retrieval of the object in substantial part"* (DR-069).

### Data at Risk

The backup contained:

> *"approximately 912.8m historical profile records, of which approximately 286m correspond to accounts active within the preceding 24 months"* (DR-069)

Record fields: *"names, usernames, email addresses, recovery email addresses, phone numbers, dates of birth, salted password hashes, password-reset tokens, security-question hashes"* (DR-069).

Special category: *"~8.4m legacy small-business accounts with improperly encrypted security-question answers"* (DR-069).

No raw payment card or bank account data were in the backup (DR-069, DR-070).

### Authentication Exploitation

The unrotated `vpauth-legacy-2019` signing key created a session-cookie forging vector. IronLake observed *"on the order of 41,500 suspected forged/replayed session events"* during the window — *"consistent with — though not, on present evidence, conclusive of — session forging"* (DR-069). Owen Bell described this explicitly in his 29 December email: *"the signing-key issue makes session forging feasible"* (DR-100).

### The Suppression of the Finding

Security Engineering's characterisation — "BULK ACCESS, full stop" — was overridden within 48 hours by management reclassification. The privileged forensic draft concluded "bulk export is probable." The GC then directed IronLake to soften the final for external use: IronLake confirmed it *"generalised some of the draft's quantitative language in the final per counsel's direction"* (DR-100). The final executive summary (DR-070) replaced "probable" with "has not been definitively established."

The Trust Reset — forced mass password resets for **~286m accounts** and invalidation of **~511m sessions** — was VistaPort's operational remediation of the breach, repackaged as *"proactive maintenance of credential and session integrity"* (DR-059).

---

## 3. DIVERGENT FRAMING TABLE

| Function / Document | Characterisation Used | DR-### | Forensic Reality (DR-069 / DR-068) | Understatement? |
|---|---|---|---|---|
| **Security Engineering — NQ-17 ticket (Petrov, 21 Oct)** | *"unauthorised BULK ACCESS...This is BULK ACCESS, full stop"* | DR-068 | Consistent | **No gap — most accurate framing in the data room** |
| **Management / Programme Office — NQ-17 reclassification (23 Oct)** | *"network-quality / performance matter"*; orders removal of *"bulk-access and breach terminology"* | DR-068 | Unauthorized bulk reads; probable exfiltration of ~1,840 GB | **YES — direct suppression of accurate characterisation by management within 48 hours** |
| **Product postmortem (Hart, 28 Nov)** | *"login friction / availability...SEV-2 (degraded experience, no service outage)...It is not a security-incident report"* | DR-060 | Security breach; bulk export probable | **YES — treats breach response (Trust Reset) as standalone operational event; incident code NQ-17 reused for the cover narrative** |
| **Trust Reset project brief (Hart, 31 Oct)** | *"proactive credential-hygiene initiative...proactive maintenance of credential and session integrity"*; *"for diligence, Trust Reset is described as a routine credential-hygiene and account-integrity initiative"* | DR-059 | Reactive forced mass reset in direct response to the 18 Oct bulk access | **YES — explicitly notes the diligence framing; describes a reactive breach response as proactive hygiene** |
| **AURORA final executive summary (IronLake, 20 Nov)** | *"scope of any data acquisition has not been definitively established; the available evidence does not permit a conclusive determination of what, if anything, was removed"* | DR-070 | Phase 1 draft: *"a bulk export is probable; the read volume and egress are consistent with retrieval of the object in substantial part"* | **YES — final deliberately softened from draft "per counsel's direction" (DR-100); shifts from "probable" to "not definitively established"** |
| **Disclosure Committee (Raman, 29 Oct)** | *"materiality...is not yet determinable"*; directs avoidance of *"confirmed breach or exfiltration"* language | DR-013 | IronLake Phase 1 draft (12 Nov, retroactively): bulk export probable; 1,840 GB egress | **YES — framing precedes full forensics but the suppression directive remained operative after Phase 1 findings were received** |
| **Board Q4 2025 (11 Dec)** | *"account integrity workstream...Trust Reset programme of staged credential-hygiene measures...intended to maintain account hygiene...described as operational matters"*; *"materiality of the matter is not yet determined"* | DR-012 | Phase 1 draft already in hand (12 Nov): probable exfiltration of 912.8m-record backup; $240-$465m exposure estimate from outside counsel (8 Dec) | **YES — board told "operational matters" and unquantified; outside counsel's exposure range existed before board met but was not shared** |
| **Draft DPC response (Okafor, 24 Nov)** | *"the Company has not established that personal data was exfiltrated"*; *"the Company has not at this stage concluded that a notifiable personal-data breach has occurred"* | DR-080 | Phase 1 draft (12 Nov, 12 days earlier): *"bulk export is probable"*; 1,840 GB egress from foreign IPs | **YES — regulator told no established exfiltration; forensics say probable exfiltration; tracked deletion removes even stronger denial** |
| **Contingency reserve memo (Cho, 30 Dec)** | *"trust-and-safety contingency of $12m...management's best estimate of the obligation that is both probable and reliably measurable"* | DR-029 | Outside counsel (8 Dec): $240m–$465m indicative aggregate | **YES — $12m booked; $240-$465m range exists in privileged memo; CISO's email (29 Dec, DR-100) calls it unreconcilable** |
| **Strategic Alternatives Board Deck (Klein, 8 Jan 2026)** | *"One open workstream (account integrity)...not expected, on current information, to be quantified at this stage"* | DR-015 | Outside counsel exposure memo ($240-$465m) dated 8 Dec 2025 — a month before this deck | **YES — deck prepared for Northstar discussions omits quantified exposure range that existed in company files** |
| **Seller Rep Schedule disclosure entries (25 Jan 2026)** | DS-7.1(a): *"Routine security operations, including an ongoing credential-hygiene programme and associated user communications, are conducted in the ordinary course."* DS-7.1(b): *"The Group operates certain legacy systems pending decommissioning."* | DR-087 | Probable breach; 912.8m records; 1,840 GB egress; Irish DPC inquiry (14 Nov); CISO resigned; $240-$465m potential exposure | **YES — no specific incident disclosed; generic language covering a probable major breach; buyer being asked to rep against this disclosure** |

---

## 4. WHO KNEW WHAT, WHEN

### Nina Petrov — Head of Security Engineering
Knew by **21 October 2025** (DR-068). First to characterise the event as *"unauthorised BULK ACCESS...full stop."* Formally logged disagreement with reclassification on record on 23 October (DR-068). Advocated at Security Steering Committee (15 Dec) for *"broader user notification and earlier, proactive regulator engagement"* and *"that the evidence already supports treating affected users as notifiable"* (DR-075). Resigned December 2025 (DR-095). Exit interview cited *"how the October account-integrity event was characterised internally, and about the degree of cross-functional alignment between Security, Legal and Finance"* (DR-095).

### Owen Bell — CISO
Knew by **22 October 2025** (DR-068: *"Acknowledged. Escalating to GC/Legal."*) Renewed the exception on `vpauth-legacy-2019` in 2023, 2024, and 2025 (DR-071). Formally recorded dissent at Security Steering Committee 15 December: *"he was uncomfortable with the degree of caution being applied to external steps"* and that *"the technical evidence supported earlier and broader notification than the consensus position"* (DR-075). On 29 December emailed Cho: *"I cannot reconcile a $12m reserve with the technical picture...Outside counsel's working range is materially higher than $12m once notification, regulatory and litigation heads are included"* (DR-100). Resigned December 2025 (DR-095). Exit interview cited internal alignment concerns (DR-095).

### Priya Raman — General Counsel
Knew by **22 October 2025** (escalated to by Bell; DR-068). Chaired Disclosure Committee 29 October — issued directive to *"avoid speculative or conclusory terminology (including characterising the matter as a confirmed breach or exfiltration)"* (DR-013). Chaired Exec Committee 5 November — issued AI-03: *"Do not use breach or exfiltration terminology in writing pending counsel's assessment"* (DR-014). On 5 December explicitly directed delay of insurance notice and argued awareness should be dated from final summary rather than 21 October ticket: *"The Phase 1 material is a privileged draft and is more definitive than I think is warranted; the final executive summary is softer. I would rather the notice reflect the final"* (DR-100). On 12 December directed IronLake that the final summary was the authoritative version and confirmed quantitative language had been *"generalised...per counsel's direction"* (DR-100). Prepared DR-087 seller reps.

### Daniel Cho — CFO
Knew by **29 October 2025** (attended Disclosure Committee; DR-013). Attended Exec Committee 5 November (DR-014). Received Bell's 29 December email explicitly stating $12m was inadequate against the technical picture and outside counsel's range (DR-100). Responded by maintaining $12m: *"accounting requires a reliably estimable amount, and we do not have a confirmed reportable event or an agreed quantum"* (DR-100). Filed reserve memo 30 December recommending $12m (DR-029). Note: Cho simultaneously knew from DR-088 (8 December) that outside counsel's range was $240m–$465m.

### Grace Okafor — Chief Privacy Officer / CPO
Knew by **29 October 2025** (attended Disclosure Committee; DR-013). On Exec Committee 5 November (DR-014). Drafted DPC response 24 November telling the Commission *"the Company has not established that personal data was exfiltrated"* — 12 days after Phase 1 draft found "bulk export is probable" (DR-080). Responsible for AI-05 (privacy-law notification assessment) and AI-02 (customer-facing wording aligned with Legal before issue) (DR-014).

### Elena Marquez — CEO
Present at and chaired Exec Committee 5 November (DR-014) at which all AURORA/Trust Reset action items were discussed, including the external-communications hold and ban on breach terminology.

### Board of Directors
First formally informed on **11 December 2025** (DR-012), but in materially softened terms: *"account integrity workstream...Trust Reset programme...staged credential-hygiene measures...intended to maintain account hygiene...described as operational matters"*; *"materiality of the matter is not yet determined."*

**What the Board was NOT told on 11 December 2025, despite it being in management's possession:**
- IronLake Phase 1 draft (12 Nov): "bulk export is probable"; 912.8m records; 1,840 GB egress (DR-069)
- Outside counsel Juniper & Rowe exposure estimate (8 Dec): $240m–$465m (DR-088)
- CISO's formal dissent recorded at Security Steering Committee (15 Dec, post-board, but the dissent position was known before) (DR-075)
- Irish DPC informal inquiry received 14 November (DR-080)
- Insurance notice timing concern (45-day window arguably already breached; DR-082, DR-100)

The January 2026 board deck presented to Northstar (DR-015) described the matter as *"not expected, on current information, to be quantified at this stage"* — despite outside counsel's $240m–$465m memo being over a month old.

### Evidence of Deliberate Non-Disclosure
1. **Reclassification on 23 October** (DR-068): Management directed removal of breach and bulk-access terminology from the ticket summary — not because the facts were unclear (Security Engineering was explicit) but pending "forensic confirmation." Petrov's logged disagreement sits in the ticket as formal objection.

2. **Directive against breach language** (DR-013, DR-014): The Disclosure Committee and Exec Committee both issued standing directives banning breach/exfiltration terminology in writing across all functions. This directive shaped the DPC response, the Trust Reset project brief, the product postmortem, the board minutes, and the seller reps.

3. **Insurance notice delay and characterisation** (DR-082, DR-100): Raman explicitly directed delay of insurance notice and argued for characterising it as "Trust Reset" rather than AURORA/unauthorised access. Broker Delacroix warned this *"could be read as under-notification."* The likely-breached 45-day condition has not been disclosed to the buyer.

4. **Softening of forensic conclusions** (DR-100): Raman directed IronLake to treat the final executive summary as authoritative; IronLake confirmed it *"generalised some of the draft's quantitative language in the final per counsel's direction."* The final summary (placed in the data room as DR-070) is softer than the underlying Phase 1 draft (DR-069) on the key question of whether exfiltration occurred.

5. **Disclosure schedule entries** (DR-087): The draft Disclosure Schedule against Rep 7.1 discloses only "routine credential-hygiene programme" and "legacy systems pending decommissioning" — both generic, neither incident-specific. DR-086 explicitly records that the disclosure committee would *"reconvene on this item ahead of any transaction milestone that would require a representation"* — meaning the committee knew the reps could not be given cleanly without resolving this item, yet the draft reps were issued without specific disclosure.

---

## 5. DISCLOSURE / REP RISK

### The Representations (DR-087)

**Rep 7.1 — Security incidents:**
> *"Save as fairly disclosed in the Disclosure Schedule, in the twenty-four (24) months prior to the date of this Agreement the Group has not suffered any material cybersecurity incident, material data breach, or material unauthorised access to or acquisition of personal data held by the Group that has required, or that the Seller has determined requires, notification to any regulator or to affected data subjects."*

**Draft Disclosure Schedule entries against 7.1:**
- DS-7.1(a): *"Routine security operations, including an ongoing credential-hygiene programme and associated user communications, are conducted in the ordinary course."*
- DS-7.1(b): *"The Group operates certain legacy systems pending decommissioning under its IT modernisation programme."*

**Analysis:** These entries do not "fairly disclose" the October 2025 event. They do not name the incident, identify the affected dataset (legacy_uap_backup_2021.tar.gz), quantify the records at risk (912.8m / 286m), describe the nature of the access (bulk read from foreign ASNs), reference the forensic investigation (AURORA), or disclose the IronLake conclusion (bulk export probable). A buyer reading DS-7.1(a) would understand it as covering routine security maintenance, not a probable exfiltration of a 912.8m-record backup. If the incident constitutes a "material cybersecurity incident" or "material unauthorised access" — and the forensic and outside counsel record strongly supports that conclusion — Rep 7.1 will be false unless specifically and adequately disclosed.

DR-086 explicitly records that the disclosure committee *"left the disclosure question open"* and would *"reconvene on this item ahead of any transaction milestone that would require a representation."* That reconvening has not been reflected in the draft seller reps as of 25 January 2026.

**Rep 7.2 — Compliance:**
> *"Save as fairly disclosed, the Group has in all material respects complied with applicable data-protection and privacy laws and with its material contractual obligations concerning the security of personal data."*

**Exposure:** A probable exfiltration of 912.8m records almost certainly engaged notification obligations under GDPR Article 33 (72-hour clock) and Article 34 (individual notification). The draft DPC response (DR-080) explicitly declines to notify under Article 33. Outside counsel (DR-088) identified EU/UK regulatory exposure of **$60m–$160m** and noted US states (California and New York) had already made informal contact. If notification obligations were engaged and not discharged in a timely manner, the compliance rep is impaired.

**Rep 8.1 — Regulatory:**
> *"Save as fairly disclosed in the Disclosure Schedule, there are no material undisclosed regulatory matters, investigations or enforcement proceedings pending or, so far as the Seller is aware, threatened against any Group company by any data-protection authority or other regulator."*

**Disclosure Schedule against 8.1:**
- DS-8.1(a): *"The Group responds from time to time to routine and informal regulator correspondence in the ordinary course."*

**Analysis:** The Irish DPC issued an informal inquiry on **14 November 2025** specifically concerning *"recent user notifications relating to password resets and questions raised by certain users about access to their accounts"* (DR-080). The draft DPC response (DR-080) is at v0.3. US state offices (California and New York) had made informal contact (DR-088). DS-8.1(a)'s generic characterisation of "routine and informal regulator correspondence" does not fairly disclose specific, live regulatory inquiries tied to the October event.

**Rep 9.1 — Reserves adequate:**
> *"The reserves and provisions reflected in the FY2025 draft financial statements are, in the Seller's view, adequate in all material respects for the liabilities and contingencies that are reasonably estimable as at the date of those statements."*

**Analysis:** The recognised reserve is **$12m** (DR-029). Outside counsel's indicative aggregate exposure is **$240m–$465m** (DR-088). Bell's 29 December email (DR-100) states directly: *"I cannot reconcile a $12m reserve with the technical picture."* The CFO's memo (DR-029) itself acknowledges: *"were certain contingencies to crystallise, the eventual cost could be materially higher."* Cho's defence — *"we do not have a confirmed reportable event or an agreed quantum"* — is itself the disclosure problem: the seller is asking the buyer to inherit an unresolved exposure and to rep that a $12m reserve is adequate.

### The Bottom Line

The buyer is being asked, through Rep 7.1, to effectively give comfort that there has been no material breach — against a Disclosure Schedule that does not specifically disclose the October 2025 event. If the breach is material (and the forensic record, the magnitude of records at risk, the CISO's formal dissent, the outside counsel's $240m–$465m range, and the CISO/engineer departures all point in that direction), the seller reps will be false, the disclosure schedule will be inadequate, and Northstar will have no contractual protection. The seller has, by not resolving DR-086's "open item" ahead of drafting the reps, structured a situation where it is offering representations around a known, probable breach.

---

## 6. ALL DOLLAR FIGURES AND COUNTS

### Records / Users

| Figure | Description | Source |
|--------|-------------|--------|
| **~912.8m (912,800,000)** | *"approximately 912.8m historical profile records"* in `legacy_uap_backup_2021.tar.gz` | DR-069, DR-088 |
| **~286m (286,000,000)** | *"approximately 286m correspond to accounts active within the preceding 24 months"* | DR-069, DR-088 |
| **~8.4m** | *"~8.4m legacy small-business accounts with improperly encrypted security-question answers"* | DR-069 |
| **~286m** | Accounts forced to password reset under Trust Reset | DR-059, DR-060 |
| **~511m** | Active sessions invalidated under Trust Reset | DR-059, DR-060 |
| **~41,500** | *"on the order of 41,500 suspected forged/replayed session events"* during the October window | DR-069 |
| **~615m** | Monthly active users (January 2026 deck) | DR-015 |
| **~408m** | Mobile MAU (January 2026 deck) | DR-015 |
| **~614m** | Monthly active users (Q4 2024) | DR-008 |
| **31.2m** | Peak weekly password-reset volume (week of 3 Nov 2025) | DR-060 |
| **5.1%** | Peak login-failure rate (week of 10 Nov 2025) | DR-060 |

### Data Egressed

| Figure | Description | Source |
|--------|-------------|--------|
| **~1,840 GB** | *"Peak/cumulative egress on the legacy backup prefix of approximately 1,840 GB flagged by detection content"* | DR-069 |
| **5** | Distinct anomalous bulk-read events during 18–20 Oct window | DR-069 |
| **3** | Foreign autonomous systems (ASNs) as source | DR-069 |

### Financial — Deal / Business

| Figure | Description | Source |
|--------|-------------|--------|
| **$4.83bn** | Northstar indicative enterprise value | DR-015 |
| **~$5,150m** | FY2025 group revenue (preliminary) | DR-012, DR-015 |
| **~$775m** | FY2025 adjusted EBITDA | DR-015 |
| **~6.2x** | Implied EV / adjusted EBITDA | DR-015 |
| **~$410m** | Estimated synergy NPV | DR-015 |

### Reserve / Exposure

| Figure | Description | Source |
|--------|-------------|--------|
| **$12m** | Trust-and-safety contingency recognised in FY2025 draft financial statements | DR-029 |
| **$240m** | Outside counsel indicative aggregate exposure — **low end** | DR-088 |
| **$465m** | Outside counsel indicative aggregate exposure — **high end** | DR-088 |
| **$60m–$160m** | Regulatory fines & penalties (EU/UK/US state) | DR-088 |
| **$70m–$120m** | User notification, call-centre & credit monitoring | DR-088 |
| **$30m–$45m** | Security remediation (key rotation, backup redesign, auth migration) | DR-088 |
| **$25m–$60m** | Advertiser/customer contract credits & renegotiation | DR-088 |
| **$55m–$80m** | Civil litigation / class settlement reserve | DR-088 |

Bell explicitly: *"Outside counsel's working range is materially higher than $12m once notification, regulatory and litigation heads are included"* (DR-100). CFO acknowledged: *"were certain contingencies to crystallise, the eventual cost could be materially higher than the amount recognised"* (DR-029).

### Insurance

| Item | Description | Source |
|------|-------------|--------|
| **45 days** | Policy notice condition (Condition 7.2): notice required within 45 days of a relevant officer becoming aware of a relevant circumstance | DR-082, DR-100 |
| **~5 December 2025** | Date the 45-day window closed if awareness measured from 21 October (date internal ticket opened) | DR-082, DR-100 |
| **Late November 2025** | Alternative "awareness" date argued by Raman (receipt of final summary) — *"a defensible reference point"* | DR-100 |
| **Prior-known-events exclusion** | Identified risk if carriers determine awareness predates notice | DR-082, DR-100 |
| **Redbridge** | Broker name for cyber tower | DR-082 |

Broker Delacroix: *"framing the awareness date around the final summary rather than the October activity is a position they may test"* and describing the matter as Trust Reset only *"could be read as under-notification"* (DR-100).

### Class-Action Settlement Analogues

| Analogue | Affected | Reported settlement | Implied per-record | Source |
|----------|----------|--------------------|--------------------|--------|
| Sector comparator A (credential/profile data) | ~150m | $85m–$120m | $0.60–$0.80/record | DR-089 |
| Sector comparator B (email/identity data) | ~80m | $50m–$90m | $0.60–$1.10/record | DR-089 |
| Sector comparator C (large legacy dataset) | ~500m+ | $100m–$175m | $0.20–$0.40/record | DR-089 |
| Sector comparator D (regulated-data overlay) | ~30m | $40m–$70m | $1.30–$2.30/record | DR-089 |
| Sector comparator E (per-capita basis) | ~200m | $60m–$110m | $0.30–$0.60/record | DR-089 |

Applying even the lowest analogues ($0.20–$0.40/record) to the 286m active-account population implies a civil litigation settlement of approximately **$57m–$114m** — before regulatory fines, notification costs, and remediation. Applied to 912.8m total records, the low-end analogue implies **$183m–$365m** in civil exposure alone.

---

## DILIGENCE SUMMARY FOR NORTHSTAR

The data room presents a coherent but legally fragile narrative in which a probable mass data exfiltration (IronLake Phase 1 draft: *"bulk export is probable"*; ~1,840 GB; 912.8m records) is characterised by management as: (a) a "network quality" ticket, (b) a "proactive credential-hygiene initiative," (c) an "operational matter," (d) a "login friction" SEV-2 incident, and (e) an unquantified "open workstream" in the buyer's board deck. The seller is offering representations under DR-087 that are premised on disclosure entries that do not disclose the specific incident. The reserve ($12m) is separated from the outside counsel exposure estimate ($240m–$465m) by a factor of 20–39x. The CISO who renewed the key exceptions creating the vulnerability, who formally dissented on the reserve and the notification pace, and who objected in writing that the $12m figure was irreconcilable with the technical picture, has resigned. Three additional security engineers from the authentication and key-management teams have resigned, citing the handling of the October event. The cyber insurance notice is arguably out of time. The Irish DPC inquiry is live and not specifically disclosed.

Northstar should require, before signing, specific incident disclosure in the Disclosure Schedule, resolution of the AURORA disclosure question as contemplated by DR-086, reconciliation of the reserve against outside counsel's exposure range, confirmation of the insurance notice status and any prior-known-events exclusion risk, and access to the unredacted IronLake Phase 1 draft (DR-069) and the unredacted outside counsel exposure memo (DR-088). The $4.83bn enterprise value should be repriced or escrowed to reflect a contingency range of at minimum $240m, pending resolution.