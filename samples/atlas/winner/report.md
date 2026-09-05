# Project Atlas — Buy-Side Diligence Findings Report

**Prepared for:** Northstar Mobile Holdings plc — Deal Committee
**Prepared by:** Buy-side Diligence Lead
**Target:** VistaPort Media Inc. ("VistaPort" / the "Company")
**Indicative enterprise value:** US$4.83bn (~6.2× FY2025 adjusted EBITDA of $775m; ~7.9× reported EBITDA of $612m) (DR-015, DR-018, DR-025)
**Status:** Confidential — subject to NDA and clean-team protocol (DR-003)

> All figures in US$ unless stated. Every conclusion is cited to data-room document IDs (`DR-###`). Where the record is incomplete I say so and state what I would request.

---

## 1. Executive summary

**Recommendation: DO NOT proceed on current price or terms. Proceed only on a *restructured and repriced* basis, conditional on specific incident disclosure.**

The data room evidences a **probable mass data exfiltration** of a legacy user-profile backup containing **~912.8m historical profile records, of which ~286m are active accounts** (DR-069), that VistaPort has **systematically re-characterised across every function** as routine "credential-hygiene," "login friction," "network quality," and an unquantified "open workstream." The Company's own forensic provider concluded **"a bulk export is probable"** (DR-069); its own outside counsel put indicative exposure at **$240m–$465m** (DR-088); yet management has booked a **$12m** reserve (DR-029), answered a direct buyer question by denying any confirmed material incident (DR-004 Q-007), and is offering seller representations whose disclosure schedule does **not** disclose the incident (DR-087).

This is not merely a liability to be priced — it is a **disclosure-integrity and representation problem** that contaminates the reliability of the seller's entire diligence presentation. The same matter also (a) drives the Q4 advertising softness the seller attributes to "seasonality" (DR-012, DR-024, DR-037); (b) is being **added back to adjusted EBITDA** as a $34m "non-recurring" item, inflating the valuation base (DR-025); (c) has triggered **four concurrent regulator inquiries** (Irish DPC, UK ICO, California AG, New York AG) (DR-079); (d) has likely **blown the 45-day notice condition on the $150m cyber tower** (DR-081, DR-082, DR-100); and (e) has caused the **CISO and three senior security engineers to resign**, citing the handling of the matter (DR-095).

**My best estimate of the deal impact is ~$350m of direct liability (range $240m–$465m, anchored on the Company's own counsel), plus ~$210m of overstated enterprise value from the mischaracterised EBITDA add-back, plus contingent downside from insurance denial (up to ~$145m) and addressability-driven revenue impairment.** The booked reserve understates the central case by a factor of ~29×.

**Recommended deal action (summary; detail in §3):**
1. **Reprice** the enterprise value down by **~$210m** to reverse the $34m Trust Reset add-back from adjusted EBITDA (DR-025), and re-test the multiple against the genuine run-rate.
2. **Ring-fence the incident** with an **uncapped special indemnity for the AURORA matter**, backed by a dedicated **escrow of $350m (central) to $465m (counsel high)** (DR-088), released as the regulatory, litigation and notification outcomes crystallise.
3. **Condition signing** on specific disclosure of the incident in the Disclosure Schedule (DR-087/DR-086), a bring-down of reps 7.1/7.2/8.1/9.1 to the actual facts, confirmation of the cyber-insurance notice/coverage position (DR-081/DR-082), and delivery of the **unredacted** IronLake Phase 1 draft (DR-069) and outside-counsel exposure memo (DR-088).
4. If the seller will not disclose the incident and reset the reps, **withdraw** — the representation package is unsignable as drafted and the post-closing recovery position would be illusory.

---

## 2. Key findings, ranked by materiality

### FINDING 1 (CRITICAL) — Concealed / under-disclosed mass data breach, mis-described across eight workstreams

**The issue.** Between **18–20 October 2025**, source IPs resolving to **three foreign autonomous systems** — not in any restore schedule — executed **five anomalous bulk-read events** against `legacy_uap_backup_2021.tar.gz`, with cumulative egress of **~1,840 GB** (DR-069). The backup contained **~912.8m historical profile records, ~286m active within 24 months** — names, emails, recovery emails, phone numbers, dates of birth, salted password hashes, password-reset tokens and security-question hashes, plus **~8.4m legacy SMB accounts whose security-question answers were "improperly encrypted"** (DR-069). A legacy session-signing key (`kid=vpauth-legacy-2019`), unrotated since **2019** under an annually-renewed exception, created a session-forging vector; forensics observed **~41,500 suspected forged/replayed session events** (DR-069, DR-071).

The magnitude is **independently corroborated** outside the forensic memo: the Backup Retention Inventory lists the same object at "3.1 TB / 912,800,000 records / Legacy scheme (weak) / RETAINED — exceeds 36-month policy / disposition outstanding" (DR-073), and the Snowcap warehouse catalogue lists the same ~912.8m-row snapshot still retained as of December 2025 (DR-061).

**The forensic conclusion was then deliberately softened and re-labelled by every function.** The most accurate characterisation in the entire data room is the front-line security ticket: *"this does not look like a network problem… This is BULK ACCESS, full stop"* (DR-068, 21 Oct). Within 48 hours management reclassified it as a *"network-quality / performance matter"* and ordered *"bulk-access and breach terminology … removed from the summary field"* (DR-068, 23 Oct); the engineer logged a formal written disagreement (DR-068). The chain of re-framing:

| Function / document | How the same event is described | DR-### |
|---|---|---|
| Security engineering (front line) | "unauthorised **BULK ACCESS**… full stop" | DR-068 |
| Management / programme office | "**network-quality / performance** matter"; remove breach terminology | DR-068 |
| Product | "**login friction** / availability — SEV-2… *not a security-incident report*" | DR-060 |
| Product / Trust Reset brief | "**proactive credential-hygiene** initiative"; *"for diligence, Trust Reset is described as a routine credential-hygiene… initiative"* | DR-059 |
| Forensics (final, for external use) | scope *"has not been definitively established"* — softened from the draft's *"bulk export is probable"* **"per counsel's direction"** | DR-069→DR-070, DR-100 |
| Disclosure Committee | *"materiality… not yet determinable"*; avoid "confirmed breach or exfiltration" language | DR-013 |
| Board (11 Dec) | "account integrity workstream… operational matters"; "materiality… not yet determined" | DR-012 |
| Regulator (Irish DPC) | *"the Company has not established that personal data was exfiltrated"* (12 days after "bulk export is probable") | DR-080 |
| Finance | "$12m trust-and-safety contingency… probable and reliably measurable" | DR-029 |
| Board deck **to Northstar** | "one open workstream (account integrity)… not expected… to be quantified at this stage" | DR-015 |
| Seller reps (to Northstar) | disclosure schedule says only "routine… credential-hygiene programme" and "legacy systems pending decommissioning" | DR-087 |

**Knowledge was early, senior and documented.** Security and the CISO knew by 21–22 Oct (DR-068); the GC, CFO, CPO and CEO were engaged through the Disclosure Committee (29 Oct, DR-013) and Executive Committee (5 Nov, DR-014), which issued a standing instruction *"do not use breach or exfiltration terminology in writing"* (DR-014). Outside counsel's **$240m–$465m** exposure memo is dated **8 Dec** (DR-088) — **a month before** the 8 Jan board deck told Northstar the matter was "not expected… to be quantified" (DR-015). Internal dissent is on the record: the CISO emailed the CFO *"I cannot reconcile a $12m reserve with the technical picture"* (DR-100), and recorded formal dissent at the Security Steering Committee (DR-075).

**Consequence.** This is the deal's defining issue. It simultaneously creates (i) a large, real **liability** (regulatory, litigation, notification, remediation — see §3); (ii) a **representation and disclosure failure** that would leave Northstar without contractual recourse if not fixed (Finding 2); (iii) **earnings-quality** contamination (Finding 3); and (iv) **insurance, commercial and people** consequences (Findings 5, 6, 9). The matter is quantified in §3.

---

### FINDING 2 (CRITICAL) — Seller representations are drafted *around* a known breach; the disclosure schedule does not disclose it

**The issue.** Draft Rep 7.1 warrants that, save as fairly disclosed, in the prior 24 months the Group *"has not suffered any material cybersecurity incident, material data breach, or material unauthorised access to or acquisition of personal data… that has required, or that the Seller has determined requires, notification to any regulator or to affected data subjects"* (DR-087). The **only** disclosure-schedule entries against Rep 7.1 are generic: *"Routine security operations, including an ongoing credential-hygiene programme…"* (DS-7.1(a)) and *"legacy systems pending decommissioning"* (DS-7.1(b)) (DR-087). These do **not** name the incident, the dataset, the ~912.8m/286m records, the foreign bulk reads, the AURORA investigation, or the "bulk export is probable" conclusion.

The document **flags its own inadequacy**: DR-087 states the disclosure entries *"describe routine operations and do not, on their face, disclose any specific incident, regulator inquiry or quantified exposure."* The Disclosure Controls memo records that the disclosure question was left **"open"** and the committee would *"reconvene… ahead of any transaction milestone that would require a representation"* (DR-086) — yet the reps were drafted (25 Jan 2026) without that reconvening or specific disclosure.

The seller also answered a **direct buyer question** evasively: asked to *"confirm whether the Company has experienced any material cybersecurity incident, data breach, or unauthorised access to personal data in the last 24 months,"* the GC replied *"the Company has not confirmed any material security incident requiring regulatory or customer notification… Routine security operations, including the credential-hygiene programme…"* (DR-004, Q-007). The same evasion appears at Q-017 (advertiser impact) and Q-015 (CISO departure).

**Consequence.** As drafted, Rep 7.1 (and 7.2 compliance, 8.1 regulatory, 9.1 reserve adequacy) will be **false or misleading** if the October event is a "material" incident — which the forensic record, the record counts, the four live regulator inquiries, the counsel exposure range and the CISO resignations all support. Relying on a post-closing warranty claim against a generic disclosure schedule is a weak position; the better protection is **specific pre-signing disclosure + a special indemnity** (see §3). This finding is *why* the issue cannot simply be "priced and accepted."

---

### FINDING 3 (HIGH) — Adjusted EBITDA is inflated by a $34m breach-remediation add-back; FY2025 is unaudited

**The issue.** The seller bridges reported EBITDA of **$612m** to adjusted EBITDA of **$775m** via **$163m** of add-backs (DR-025). One add-back, **A3, is "Account integrity programme / Trust Reset costs — $34m," labelled "non-recurring operational programme"** (DR-025). Trust Reset is the **breach remediation** (forced reset of ~286m accounts; invalidation of ~511m sessions) (DR-059, DR-060). Treating breach-response cost as a "non-recurring" EBITDA add-back is doubly aggressive: the underlying programme is **ongoing** (capex for auth migration, key rotation and backup redesign has been *accelerated into FY26*, DR-028 C03–C05), and the matter that generated it is unresolved. The seller-prepared QoE addendum (DR-023) is advocacy by the sell-side adviser (Canton Street Capital), not an independent attestation, and **FY2025 remains unaudited** (DR-018); FY2023/FY2024 were unqualified (DR-016, DR-017).

**Consequence.** At the implied **6.23×** multiple, the $34m A3 add-back alone supports **~$210m of enterprise value** that should not survive diligence. The Q4 advertising softness (Finding 6) is a further, separate earnings-quality drag the seller attributes to "seasonality." Quantified in §3 as a repricing item distinct from the liability.

---

### FINDING 4 (HIGH) — Four concurrent regulator inquiries, none specifically disclosed; reserve understated ~29×

**The issue.** The Regulatory Correspondence Log shows **four open inquiries** all tied to the October event and *"being handled together under the account-integrity workstream (AURORA)"*: **Irish DPC** (informal inquiry 14 Nov; acknowledgement/further questions reserved 8 Dec), **UK ICO** (19 Nov; "AURORA under review" 10 Dec), **California AG Privacy Unit** (2 Dec), **New York AG Bureau of Internet & Tech** (4 Dec) (DR-079, corroborated DR-080, DR-088). The draft DPC response declines to treat the matter as a notifiable breach (DR-080). The Irish entity is the EU **lead supervisory authority** (DR-007, DR-079), exposing the Group to GDPR Art. 83 turnover-based penalties (up to 4% of global turnover, i.e. up to ~$206m on $5.15bn revenue) in addition to UK/US state exposure. Outside counsel's regulatory-fine band alone is **$60m–$160m** (DR-088).

**Consequence.** The **$12m** booked reserve (DR-029) is ~29× below counsel's $240m–$465m central exposure; the CFO's own memo concedes *"the eventual cost could be materially higher"* (DR-029) and the CISO called it irreconcilable (DR-100). Rep 8.1 ("no material undisclosed regulatory matters") is impaired by the generic DS-8.1(a) disclosure. Quantified in §3.

---

### FINDING 5 (HIGH) — Cyber tower ($150m) likely forfeited by late / mischaracterised notice

**The issue.** The cyber policy carries a **$150m aggregate limit**, **$5m SIR**, and sublimits of **$25m** (breach notification), **$20m** (regulatory defence & penalties), **$15m** (forensic) and **$30m** (BI) (DR-081). Condition 7.2 requires notice **within 45 days** of a relevant officer becoming aware, and **expressly states awareness "is not deferred until the insured has completed its own investigation or received a final report"** (DR-081). Awareness dates from the 21 Oct security ticket (DR-068) → the 45-day window closed **~5 Dec** (DR-082, DR-100). As of **11 Dec** the broker notice was still a **draft** (DR-082), and internal email shows the GC steering the notice to describe the matter as "Trust Reset" and to date awareness from the **final** (softened) summary — the very deferral the policy disallows; the broker warned this *"could be read as under-notification"* and is a position carriers *"may test"* (DR-082, DR-100). A **prior-known-events exclusion** compounds the risk (DR-081). The insurance schedule itself records INS-01 as *"notice deadline passed / under review"* (DR-030).

**Consequence.** If cover is voided, the entire $150m tower is unavailable for the AURORA matter, and the **net** liability to Northstar rises by up to **~$145m** (tower less SIR). This directly affects the §3 net-exposure calculation.

---

### FINDING 6 (HIGH) — "Seasonal" Q4 advertising softness is breach-driven; it hits the largest revenue line and the synergy thesis

**The issue.** LumenX programmatic (the largest product, **$1,910m / ~37% of FY2025 revenue**) fell to **$439m in Q4** from **$497m in Q3** (–$58m, –11.7%) (DR-024). The seller attributes this to "seasonality / short-term operational factors" to the board (DR-012) and "temporary Q4 yield softness… not… structural" in the QoE (DR-023). The commercial documents tell a different story: the eCPM yield index **dipped to ~0.953** in Q4, explicitly because fewer *"impressions carrying a durable logged-in identity signal"* depressed addressable eCPM following the **Trust Reset** session refresh (DR-037, DR-055). The same mechanism undercuts Northstar's **$410m synergy NPV**, which is explicitly premised on *"higher match rates from combined first-party data"* and growing *"the logged-in, consented audience"* (DR-005, DR-015). Two existing clients have paused **$25.5m** of pipeline pending VistaPort's *"data/privacy posture"* (DR-038), and several top advertisers' notes read "agency reviewing brand-safety/privacy terms ahead of renewal" (DR-032).

**Consequence.** Annualising the Q4 run-rate implies a **~$154m revenue gap** versus the FY2025 base on the largest line (DR-024); whether structural depends on recovery (match rate recovered only partially, ~67%→68.3%, DR-055). At minimum it means the seller's "normalised yield" synergy assumption is unproven and the Q4 softness is mis-attributed. Treated as a downside sensitivity in §3.

---

### FINDING 7 (HIGH) — Key-customer termination right may already be triggered; change-of-control consents unconfirmed

**The issue.** The largest advertiser, **Meridian Media Agency ($188m FY2025 spend, renewal under review)** (DR-032), holds an MSA with a **termination-for-cause right exercisable "with immediate effect" on a "Security Incident or material event affecting user trust,"** with "Security Incident" defined broadly as *"any actual or reasonably suspected unauthorised access"* (DR-035 §4.2–§4.4); the liability cap does not apply to these Section 4 breaches, and a 72-hour customer-notification duty applies (DR-035). Legal has not concluded whether a "reportable event" occurred (DR-035 §4.6). Separately, **change-of-control consent** (not just notice) is required from at least five named material counterparties — Meridian, Helios, Northwind, Aster, Pinnacle (with a competitor clause) — plus the search-syndication partner, and consent tracking is "to be progressed post-signing" (DR-085).

**Consequence.** If VistaPort became aware of a qualifying Security Incident and did not give 72-hour notice, Meridian's termination right may **already be crystallised** at close ($188m revenue at risk, plus uncapped contractual exposure). Post-signing consent processes hand counterparties renegotiation leverage on a committed $4.83bn buyer.

---

### FINDING 8 (MEDIUM-HIGH) — Standalone data-protection failures independent of the breach

**The issue.** Even setting aside the exfiltration: ~1.65bn personal-data records across three legacy backups are **retained beyond the 36-month policy with "weak" encryption and no disposition owner** (DR-073, DR-061); pre-2022 accounts feeding the live **AtlasID** identity graph rest on *"inferred consent"* (not valid consent under GDPR Art. 7 / CPRA), with identity-graph disclosures added to the privacy policy only in v4.6 (Dec 2024) (DR-051, DR-053, DR-083). These are GDPR Art. 5(1)(e) (storage limitation), Art. 32 (security) and Art. 7/13–14 (consent/transparency) exposures in their own right and **aggravate** the breach severity for the regulators already engaged (DR-079, DR-088).

**Consequence.** Independent regulatory exposure and impairment of the AtlasID asset that underpins the addressability synergy thesis (DR-015). Quantification requires the count of affected pre-2022 accounts (withheld).

---

### FINDING 9 (MEDIUM) — Security-leadership exodus during diligence

**The issue.** The **CISO resigned in December 2025**, with the **Principal Security Engineer (Authentication)**, **Staff Security Engineer (Key Management)** and a **Senior Security Engineer (Detection & Response)** also departing; exit interviews cite *"how the October account-integrity event was characterised internally, and… cross-functional alignment between Security, Legal and Finance"* (DR-095). The Head of Security Engineering is flagged "High" flight risk and a retention priority (DR-094). The retention plan was still in draft / not Compensation-Committee-approved (DR-094).

**Consequence.** Loss of the institutional knowledge of the incident at the most sensitive integration moment; corroborates that the matter is serious (people leave over how a "routine" item is handled); raises Rep 7.3 (reasonable controls) questions.

> Findings 1–9 are connected: a single underlying breach manifests as a forensic finding (1), a representation failure (2), an EBITDA adjustment (3), regulatory inquiries (4), an insurance problem (5), revenue softness and a synergy risk (6), a customer-termination risk (7), standalone privacy failures (8) and attrition (9).

---

## 3. Most material issue — quantification (the concealed breach)

**The most material issue is Finding 1 (the concealed/under-disclosed breach), together with its representation, earnings-quality and insurance consequences.** I quantify it in four layers and convert each into a specific deal action.

### Layer A — Direct incident liability (the core number)

I anchor on **VistaPort's own privileged outside-counsel memo (DR-088)**, the most authoritative estimate in the record:

| Component (DR-088) | Low | High |
|---|---|---|
| Regulatory fines & penalties (EU/UK/US state) | $60m | $160m |
| User notification, call-centre & credit monitoring | $70m | $120m |
| Security remediation (key rotation, backup redesign, auth migration) | $30m | $45m |
| Advertiser / customer contract credits & renegotiation | $25m | $60m |
| Civil litigation / class settlement reserve | $55m | $80m |
| **Indicative aggregate** | **$240m** | **$465m** |

**Central case (midpoint): ~$352m.** Cross-check, bottom-up: applying the **lowest** sector class-action analogue ($0.20–$0.40/record, DR-089) to the **286m active** accounts implies **$57m–$114m** of civil exposure alone (to the full 912.8m, $183m–$365m), consistent with counsel's $55m–$80m litigation line being conservative and the aggregate being credible-to-light. I therefore treat **$352m as the central estimate and $240m–$465m as the working range.**

**Versus the booked reserve of $12m (DR-029), the central case is an under-reserve of ~$340m** — consistent with the CISO's own statement that $12m *"cannot be reconciled with the technical picture"* (DR-100).

### Layer B — Earnings-quality / valuation correction (separate from the liability)

The **$34m A3 "Trust Reset" add-back** (DR-025) is breach remediation mischaracterised as non-recurring. Reversing it at the implied **6.23×** multiple removes **~$210m of enterprise value** that diligence does not support. (Reversing *all* $163m of add-backs would be ~$1.0bn; I am only challenging the breach-related A3 here, and flagging SBC ($41m) and restructuring ($48m) for separate scrutiny.)

### Layer C — Insurance offset at risk (swing factor on the net number)

Counsel's $240m–$465m is a gross legal/financial exposure. If the **$150m cyber tower** responds, it could offset up to **~$145m** (limit less $5m SIR), subject to sublimits ($25m/$20m/$15m). But the tower is **at serious risk of denial** for late/mischaracterised notice and the prior-known-events exclusion (Finding 5; DR-081, DR-082, DR-100). **Net exposure to Northstar therefore swings by up to ~$145m depending on coverage** — i.e. roughly $200m–$320m net if cover holds, $352m+ net if it does not. Until the notice/coverage position is confirmed, I assume **no reliable recovery** and price the gross figure.

### Layer D — Revenue / synergy impairment (downside sensitivity, not in the central case)

If the addressability impairment proves structural, the LumenX Q4 run-rate implies a **~$154m revenue gap** (DR-024) and undermines the **$410m synergy NPV** (DR-015). At ~40% incremental margin and 6.23×, a sustained $150m revenue loss would be **~$370m of EV**. I hold this **outside** the central case (match rates were partially recovering, DR-055) but flag it as the principal thesis risk and a reason not to credit "normalised yield."

### Best estimate and recommended deal action

> **Best estimate of deal impact: ~$350m of direct liability (range $240m–$465m), plus ~$210m of overstated EV from the A3 add-back, with up to ~$145m of additional downside if cyber cover is denied and material further downside if the addressability/synergy impairment is structural. Headline: the booked $12m reserve understates the central liability by ~$340m.**

**Specific actions for the deal committee:**

1. **Price reduction — ~$210m:** reverse the $34m Trust Reset add-back from adjusted EBITDA and re-strike EV on the corrected base (DR-025). Re-examine SBC and restructuring add-backs separately.
2. **Special indemnity + escrow — $350m central, sized to $465m:** an **uncapped, specifically-defined special indemnity for the AURORA matter** (regulatory fines, notification, litigation, remediation, customer credits), backed by a **ring-fenced escrow of $350m (release-as-resolved), with a $465m cap on the escrow sizing** per counsel's high case (DR-088). Do **not** rely on the general rep cap.
3. **Reserve top-up condition:** require the FY2025 accounts to carry a reserve reconciled to counsel's range, or a corresponding completion-accounts / locked-box adjustment (DR-029, DR-088).
4. **Disclosure & rep reset (condition precedent):** specific incident disclosure in the Disclosure Schedule and a bring-down of reps 7.1/7.2/8.1/9.1 to the true facts, plus a stand-alone rep on the cyber-insurance notice status (DR-087, DR-086, DR-081).
5. **Insurance condition:** written confirmation from broker/carrier of the notice position and any reservation of rights before signing (DR-081, DR-082).
6. **Information condition:** delivery of the **unredacted** IronLake Phase 1 draft (DR-069), the unredacted counsel exposure memo and its redacted annexes (DR-088), and the privileged regulatory-strategy file (DR-079).

If the seller refuses specific disclosure and a rep reset, the representation package is unsignable and post-closing recourse is illusory — in that case, **withdraw**.

---

## 4. Lesser / lower-priority issues

These are real but smaller, or contingent, and would not on their own move the price materially.

| # | Issue | Evidence | Why lower priority |
|---|---|---|---|
| L1 | **Deferred-revenue purchase-accounting haircut** ~$350m closing balance written down to fair value under ASC 805/IFRS 3; $264m single-year surge in prepaid advertising additions worth an earnings-quality look | DR-026, DR-018 | Mechanical accounting effect, partly anticipated in any deal model; not a hidden liability |
| L2 | **Working-capital peg** computed ~ –$120m with summary cells blank; $28m/yr operating leases treated "off-peg"; carve-out for "matters not yet quantified" | DR-027 | Negotiable in completion mechanics; quantifiable once peg cells are produced |
| L3 | **Sales/use-tax nexus** $6–9m acknowledged historical exposure; nexus study completes Q1 2026 (after the bid deadline); no provision | DR-031, DR-004 | Bounded and modest; address via specific tax indemnity |
| L4 | **Transfer pricing / Irish IP holdco** AtlasID Technologies Ltd (70 staff) shows $0 revenue allocation; entity revenue sums ($7,060m) exceed consolidated ($5,150m) with eliminations not shown | DR-007 | Needs TP documentation to size; structural, not acute — but request TP file |
| L5 | **Search-syndication concentration** ~$326m revenue; counterparty redacted; convenience termination after initial term; CoC consent "self-certified" in a seller summary of an unproduced contract | DR-034, DR-085 | Renewal risk is March 2027; manage via consent process and request executed contract |
| L6 | **Capex backlog $265m** with ~$59m of identity/key/backup remediation accelerated into FY26 | DR-028 | Real incremental cash cost but overlaps with the §3 remediation line; avoid double-count |
| L7 | **GPL-2.0 static linkage** in the revenue-generating media transcoding service; remediation incomplete; in-house self-certification only | DR-090 | Contingent on whether binaries were distributed; obtain IP-counsel opinion and a specific indemnity |
| L8 | **Publisher supply re-openers / related-party** Harbor (Feb 2026) and "Vista Owned & Operated" (intercompany SSP, 68% rev-share) re-openers; intercompany economics need elimination | DR-041 | Margin effect only; quantify with per-publisher volumes |
| L9 | **Employment / other litigation** ordinary-course employment matters; no consumer class action filed yet (a *future* risk already captured in §3 litigation line) | DR-078, DR-091 | Below materiality individually |

---

## 5. Confidence and open items

**Confidence.** High that a serious, under-disclosed security incident occurred and is being re-characterised: the forensic conclusion (*"bulk export is probable,"* DR-069) is corroborated by independent inventories (DR-073, DR-061), the four-regulator log (DR-079), the insurer notice file (DR-082), the CISO's own emails and resignation (DR-100, DR-095), and the candid self-flag in the rep schedule (DR-087). High confidence in the $240m–$465m liability range because it is **the Company's own counsel's number** (DR-088). Medium confidence in the *net* figure, which depends on insurance recovery (Finding 5) and whether the revenue impairment is structural (Finding 6).

**Open items that could move the conclusion:**

1. **Unredacted IronLake Phase 1 (DR-069) and outside-counsel memo + annexes (DR-088).** Final forensic *scope* (what was confirmed removed) is the single biggest swing on liability; the counsel memo's redacted Annex B drives the per-record methodology. *Could move exposure up or down materially.*
2. **Cyber-insurance coverage position (DR-081/DR-082/DR-030).** Written carrier/broker confirmation of the notice date accepted and any reservation of rights. *Swings net exposure by up to ~$145m.*
3. **Notifiability determinations per jurisdiction and regulator posture (DR-079/DR-080).** Whether Art. 33/34 (and US state) notification was/should have been made, and the DPC/ICO/AG stances. *Drives the fine band and the rep 7.2/8.1 breach question.*
4. **Whether Meridian (and other key customers) were given contractual incident notice (DR-035).** Determines if a termination/credit right is already live. *Up to $188m revenue plus uncapped contract exposure.*
5. **Recovery curve of LumenX yield / identity match rate into Q1 2026 (DR-037, DR-055, DR-024).** Confirms whether the Q4 drop is "seasonal" or structural. *Drives the synergy thesis and any revenue-quality repricing.*
6. **Count of pre-2022 "inferred-consent" accounts feeding AtlasID (DR-051/DR-053).** Sizes the standalone consent/storage exposure and the asset impairment.
7. **Board awareness trail vs. the 8 Jan deck (DR-012/DR-015/DR-088).** Whether directors were given the $240–465m range before representing to Northstar — relevant to fraud/recission posture and indemnity negotiation leverage.

**Bottom line for the committee:** the asset's scale and ad-tech are real, but the price and representations were set on a presentation that does not disclose a probable ~$240m–$465m breach liability and that adds ~$210m of unsupported EBITDA value. Reprice, ring-fence with a special indemnity and escrow, and condition signing on specific disclosure — or withdraw.

---

*Prepared from the 100 documents in the Project Atlas data room (DR-001–DR-100). Every figure is sourced to the cited document ID. Quantification is anchored on the Company's own forensic (DR-069) and outside-counsel (DR-088) work product; ranges reflect the open items in §5.*
