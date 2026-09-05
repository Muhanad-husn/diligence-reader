## VistaPort Media — Ranked Material Diligence Issues (Non-Security-Incident Cluster)

---

### 1. Unaudited FY2025 Financials + Seller-Constructed $163m EBITDA Add-Backs
**Category:** Financial | **Evidence:** DR-018, DR-023, DR-025

**Key figures/dates:** Reported EBITDA $612m; Adjusted EBITDA $775m; add-backs $163m (26.6% uplift): A1 restructuring/severance $48m, A2 legacy legal settlements $22m, A3 Trust Reset/account integrity $34m, A4 SBC $41m, A5 M&A/separation $18m. FY2025 audit "in progress" per Brandt & Mauer LLP; draft statements dated 30 Jan 2026. QoE addendum dated 22 Jan 2026 prepared by Canton Street Capital (sell-side adviser, not independent).

**Consequence:** At 6.2× EV/Adjusted EBITDA, each $10m of improperly characterised add-back equals ~$62m of valuation error. SBC ($41m) is a recurring economic cost; restructuring ($48m) may recur. The $34m Trust Reset add-back assumes non-recurrence of what may be a structural platform cost. Seller-QoE is advocacy, not attestation; FY2025 basis remains unaudited at signing.

**Materiality: HIGH — $163m add-back at 6.2× = ~$1.0bn implied valuation sensitivity if all add-backs are improper; even a 30% disallowance = ~$300m+**

> **Security/incident connection:** The $34m A3 add-back (Trust Reset/account integrity) is the direct cost of the breach remediation. If remediation is ongoing or the underlying cause is unresolved, it is not non-recurring. The Q4 advertising yield suppression (add-back quantum undisclosed in QoE) is a separate additional income adjustment not quantified in the bridge (DR-023, §Q4 memo item).

---

### 2. LumenX Q4 Revenue Collapse and Ongoing Identity Match-Rate Impairment
**Category:** Commercial/Financial | **Evidence:** DR-024, DR-037, DR-055, DR-096

**Key figures/dates:** LumenX Q4 revenue $439m vs. Q3 $497m (sequential decline $58m, −11.7%). eCPM yield index trough 0.930 (week of 10 Nov 2025, −7.0% vs. baseline of 1.003). Identity match rate 67.0% (Nov 2025) vs. 71.4% baseline (Aug 2025); partial recovery to 68.3% (Dec 2025). Synergy model states "several hundred $m of value at risk" if Trust Reset friction persists (DR-096).

**Consequence:** LumenX is 37.1% of total FY2025 revenue ($1,910m). If Q4 run-rate ($439m/quarter, ~$1,756m annualised) persists, structural shortfall vs. FY2025 is ~$154m on the largest single revenue line. Match-rate impairment directly reduces addressable CPMs — the synergy thesis depends on full recovery to pre-October levels, which is asserted but undemonstrated.

**Materiality: HIGH — ~$154m annualised revenue gap; at EV/revenue ~0.94×, implies ~$145m of value erosion even before multiple compression**

> **Security/incident connection:** Both the yield dip and match-rate decline are explicitly attributed to "Trust Reset credential-hygiene session refresh" reducing the logged-in identity signal on impressions (DR-037, DR-055). This is a direct revenue consequence of the security/credential incident, not seasonal softness.

---

### 3. Advertiser Concentration + Meridian MSA Uncapped Termination Right
**Category:** Commercial/Legal | **Evidence:** DR-032, DR-033, DR-035, DR-043

**Key figures/dates:** Meridian Media Agency: $188m FY2025 spend (rank 1), "High" renewal risk, contract ends 30 Jun 2027; Aster Pharma: $39m (rank 10), "High" renewal risk, contract ends 31 May 2026. Combined: $227m, ~13.9% of top-50 measured spend. Top 10 = ~45% of total advertising revenue. Meridian MSA §4.4: immediate termination right if Security Incident unremediated within 30 days of notification, or if §4.5 72-hour notification was missed. Liability cap in §6 does not apply to Section 4 breaches. Service credit: "IIIIIIII% of affected media value" (redacted). Q4 2025: multiple agency accounts paused or queried spend following Trust Reset communications.

**Consequence:** Loss of Meridian = $188m revenue. Uncapped MSA liability for Section 4 breaches means Northstar could inherit a claim of unknown size. If VistaPort became aware of a qualifying Security Incident and did not give 72-hour notice to Meridian, the termination right is already crystallised at close.

**Materiality: HIGH — $188m revenue at risk; uncapped contractual liability; legal opinion deferred to "a matter for Legal" (DR-035 §4.6 footnote)**

> **Security/incident connection:** The Trust Reset is explicitly named in the §4.6 footnote as an "operational initiative" where Legal has not yet concluded whether a "reportable event" under §4.2 has occurred. The November 2025 spend pauses (DR-043) and account team Legal-approved talking points (DR-042) indicate this risk is live.

---

### 4. Active Multi-Regulator Privacy/Security Investigation
**Category:** Regulatory | **Evidence:** DR-079, DR-080

**Key figures/dates:** Irish DPC: inbound inquiry 14 Nov 2025; "further questions reserved" 8 Dec 2025 — inquiry still open at 10 Jan 2026 log cutoff. UK ICO: "large-scale password resets" inquiry 19 Nov 2025; "AURORA workstream under review" 10 Dec 2025. California AG Privacy Unit: inbound 2 Dec 2025; "investigation ongoing" at 16 Dec response. New York AG Bureau of Internet & Tech: inbound 4 Dec 2025. All four remain open at log cutoff. Privileged regulatory strategy "held separately by counsel" (not produced).

**Consequence:** Irish DPC as EU lead supervisory authority: GDPR Art. 83(5) fine up to 4% of global annual turnover = up to ~$206m (on $5.15bn FY2025 revenue). UK ICO: up to £17.5m or 4% of global turnover. CA AG: $100–$750 per consumer per incident under CCPA. Four concurrent regulators sharing the same factual basis signals coordinated enforcement risk, not isolated inquiries.

**Materiality: HIGH — GDPR exposure alone up to ~$206m; multi-regulator coordination amplifies timeline and remediation cost**

> **Security/incident connection:** All four regulatory inquiries concern "user reset notifications and account access" — i.e., the Trust Reset/credential incident. "AURORA" is named explicitly in the ICO entry.

---

### 5. Legacy Backup Retention Policy Breach: ~1.65 Billion Records, Weak Encryption
**Category:** Regulatory/Legal | **Evidence:** DR-073, DR-061, DR-057

**Key figures/dates:** `legacy_uap_backup_2021.tar.gz`: 912.8m records, 3.1 TB, "Legacy scheme (weak)" encryption, status "RETAINED — exceeds 36-month policy," disposition "Pending — disposition outstanding." Created 31 Jul 2021; policy breach since ~Jul 2024. `legacy_uap_profile_snapshot_2022.tar.gz`: 740m records, 2.8 TB, weak encryption, "RETAINED — exceeds 36-month policy." Created 31 Mar 2022; policy breach since ~Mar 2025. `legacy_sso_connector_dump_2021.tar.gz`: 45 GB, weak encryption, policy breach since ~Nov 2024. Combined ~1.65bn records held beyond stated policy; no purge deadline, no owner, no escalation ticket.

**Consequence:** GDPR Art. 5(1)(e) storage limitation violation for 1.65bn+ personal data records. GDPR Art. 32 violation (inadequate encryption on large PII dataset). DPC or ICO enforcement action on this standalone basis could reach 4% global turnover (~$206m) independent of the breach liability. The over-retained backup is also the file implicated in the ~1.84 TB exfiltration event (DR-066/DR-067).

**Materiality: HIGH — ~$200m+ regulatory fine exposure; also directly implicated in the exfiltration event**

> **Security/incident connection:** `legacy_uap_backup_2021.tar.gz` is the exact object accessed during the 18–20 Oct 2025 three-night exfiltration window (DR-066, DR-067). Retaining this file beyond policy with weak encryption compounded both the breach severity and the regulatory exposure.

---

### 6. Search Syndication Concentration: $326m Revenue, Counterparty Redacted
**Category:** Commercial | **Evidence:** DR-034, DR-040, DR-085

**Key figures/dates:** Partnership contributes ~22% of search revenue and ~6% of total advertising revenue: $326m FY2025, $306m FY2024, $280m FY2023 (growing share). Agreement effective 1 Apr 2022; initial term ends 31 Mar 2027; auto-renews 2 years; "termination for convenience on 180 days' notice after the initial term." Revenue-share tiers "reset at renewal"; "partner has scale leverage." Counterparty identity redacted in this summary. No change-of-control consent stated to be required (self-certified in redacted summary — not verified against executed agreement).

**Consequence:** $326m revenue at renewal risk in March 2027 (~15 months post-close at typical timeline). Adverse renegotiation could reduce this line by an unknown margin. Self-certification of "no CoC consent" in a redacted, seller-prepared summary of an unproduced executed contract is legally unreliable. Counterparty identity redaction prevents assessment of strategic alignment, credit risk, or relationship dynamics.

**Materiality: MEDIUM-HIGH — $326m revenue base; renegotiation compression unquantifiable without counterparty identity and full executed terms**

---

### 7. Change of Control Consents: Five Material Contracts, No Pre-Signing Confirmation
**Category:** Legal | **Evidence:** DR-085, DR-041

**Key figures/dates:** Consent required (not just notice) from: Meridian Media Agency, Helios Retail Group, Northwind Financial, Aster Pharma, Pinnacle Telecom, and search syndication partner (unnamed). Pinnacle Telecom: "Consent required (CoC + competitor clause)." LumenX programmatic framework: per-partner consents required. Consent tracking "to be progressed post-signing" (management's preliminary view only). Document date 12 Jan 2026.

**Consequence:** Northstar commits $4.83bn without confirmed counterparty consent from at least five named material commercial relationships plus an unknown number of LumenX programmatic sub-partners. Pinnacle's competitor clause could make consent impossible if any Northstar group entity is deemed a competitor. Post-signing leverage asymmetry: counterparties can demand renegotiation knowing buyer is committed.

**Materiality: MEDIUM-HIGH — aggregate contracted revenue across the five named counterparties is substantial; Pinnacle competitor clause could block consent entirely**

> **Security/incident connection:** Meridian's §4.4 termination right (DR-035) makes its CoC consent doubly risky — it could consent while simultaneously exercising breach termination. Both risks are live concurrently.

---

### 8. Pre-2022 Account Consent Gap + AtlasID Late Disclosure
**Category:** Regulatory/IP | **Evidence:** DR-053, DR-051, DR-083

**Key figures/dates:** Scope of pre-2022 accounts with "inferred" consent: not quantified (zero count or percentage disclosed). Migration "in progress" with no completion date. AtlasID identity-graph disclosures and opt-out controls added to consumer privacy policy only in v4.6, dated 1 Dec 2024. Pre-2022 legacy_uap data feeds live AtlasID match keys: "a meaningful share" (no percentage given). "Remaining legacy accounts" still on old consent model per DR-053.

**Consequence:** "Inferred consent" is not valid consent under GDPR Art. 7 or CPRA. Any advertising targeting of pre-2022 accounts using AtlasID is potentially unlawful processing. If pre-2022 accounts represent a significant portion of the 1.1bn registered base, this impairs the entire AtlasID commercial value proposition to Northstar. The AtlasID identity-graph non-disclosure (pre-Dec 2024) creates backdated GDPR Art. 13/14 liability for any period it was deployed without user notice.

**Materiality: MEDIUM-HIGH — quantification requires the count of affected accounts (withheld); if >30% of registered base, regulatory and commercial impairment is severe**

> **Security/incident connection:** The pre-2022 legacy_uap data that feeds AtlasID is the same data exfiltrated in the Oct 2025 breach (DR-066); the consent gap aggravates the breach severity for the regulatory investigation.

---

### 9. Working Capital Peg: Computed Negative $120m, All Summary Cells Blank, Off-Peg Leases
**Category:** Financial | **Evidence:** DR-027

**Key figures/dates:** Computed 12-month average NWC: ~-$120.25m (receivables avg. $679m − payables avg. $433m − accruals avg. $367m). Monthly range: -$98m (Oct) to -$149m (Jun); intra-year swing $51m. Peg column and all averages blank in produced document. Operating lease commitments $28m/yr described as "off-peg memo item." Disclaimer: "no adjustment is made for matters not yet quantified or recognised."

**Consequence:** Negative peg creates buyer top-up risk: if closing NWC is less negative than the peg, Northstar pays a top-up. Management has every incentive to engineer a more negative closing NWC. The off-peg $28m/yr operating lease (~$200-300m implied PV at deal discount rates) is a debt-like item likely excluded from the EV bridge. The open-ended "matters not yet recognised" carve-out means unbooked liabilities discovered post-signing reduce closing NWC against the peg.

**Materiality: MEDIUM-HIGH — ~$120m NWC anchor; $28m/yr lease obligation likely excluded from debt bridge; swing risk of $51m in seller's favour depending on closing timing**

---

### 10. Deferred Revenue Purchase Accounting Haircut (~$357m)
**Category:** Financial | **Evidence:** DR-026, DR-018

**Key figures/dates:** Estimated closing balance ~$357m ($318m opening + $582m additions − $543m recognised, all by manual computation — closing cells blank in produced document). Prepaid advertising: ~$112m estimated closing (additions $264m = 2.75× opening balance of $96m). Annual subscriptions: ~$154m. Draft FY2025 balance sheet records $350m.

**Consequence:** Under ASC 805/IFRS 3, deferred revenue is written down to fair value at acquisition — often near zero for media subscriptions and advertising prepayments. ~$357m of post-close revenue suppression at deal multiples. The $264m single-year surge in prepaid advertising additions (nearly 3× opening balance) warrants scrutiny as possible pre-sale cash acceleration at distressed rates.

**Materiality: MEDIUM — ~$357m post-close revenue haircut; $264m advertising prepay surge is an earnings quality flag**

---

### 11. Sales/Use Tax Nexus: $6-9m Unregistered, Nexus Study Incomplete at Signing
**Category:** Tax | **Evidence:** DR-031, DR-004, DR-078

**Key figures/dates:** California $1.6m, New York $1.3m (VDA candidate), Texas $1.1m, Illinois $0.7m, Washington $0.6m (VDA candidate), other states $1.0-3.7m; total $6-9m "including estimated tax, interest and potential penalties." Nexus study target completion Q1 2026 (after indicative offer deadline of 13 Feb 2026). No provision in FY2025 accounts as of memo date 30 Nov 2025. VDA availability not confirmed for two states.

**Consequence:** Liability is historical and acknowledged — not merely prospective risk. Ceiling unknown until nexus study completes (which occurs after Northstar submits indicative bid). VDA denial in NY/WA triggers full look-back plus penalties; "other states" range of $1.0-3.7m is a 3.7× spread. Excluded from any current provision.

**Materiality: MEDIUM — $6-9m quantified; ceiling ~$15m+ if VDAs denied and other-states study widens**

---

### 12. Transfer Pricing / Irish IP Holdco: AtlasID Technologies $0 Revenue Allocation
**Category:** Tax | **Evidence:** DR-007

**Key figures/dates:** AtlasID Technologies Ltd (Ireland): 70 employees, $0 FY2025 revenue allocation despite being "intra-group licensor" for "certain identity-graph technology." VistaPort Treasury DAC (Ireland): 8 employees, $0 revenue, group treasury/intercompany financing — no intercompany loan balances, rates, or currency exposures disclosed. Netherlands BV (intermediate EMEA holdco): 4 employees, $0 revenue — ATAD/substance risk. Total group revenue allocation $7,060m ≠ consolidated revenue ($5,150m); "intra-group eliminations not shown."

**Consequence:** A functioning IP licensor generating royalties across a $7bn revenue group should record royalty income. Zero allocation is either structurally inconsistent or transfer-pricing arrangements are not arm's-length. Irish Revenue Commissioner scrutiny is live; BEPS Pillar Two may catch low-substance entities. Intercompany loan quantum unknown (could be material at $4.83bn EV).

**Materiality: MEDIUM — transfer-pricing exposure unquantifiable without TP documentation; Irish IP holdco is a DPC investigation nexus (AtlasID is also the EU data-controller entity)**

---

### 13. Capex Backlog $265m with Security-Critical Projects Pulled Forward
**Category:** Operational | **Evidence:** DR-028

**Key figures/dates:** Total backlog $265m; aggregate FY26 spend $213m; post-FY26 tail $52m. Accelerated from FY27 to FY26: C03 VPAuth auth migration $26m, C04 session-signing key rotation & HSM $14m, C05 backup encryption & retention redesign (legacy_uap) $19m. C07 LumenX exchange capacity $21m FY26/$28m total. Stated rationale: "reduce technical debt ahead of decommissioning" (no incident disclosed as driver).

**Consequence:** $265m committed capex above and beyond the ~$286m annual run-rate (per DR-018). Security-critical items ($59m for C03-C05) represent reactive remediation dressed as forward investment. Buyer inherits partially completed modernisation with $52m tail after FY26, and known vulnerabilities until C03-C05 complete.

**Materiality: MEDIUM — $265m total capex commitment; $59m security remediation items are likely undercosted given current state**

> **Security/incident connection:** C03 (VPAuth migration), C04 (key rotation/HSM), and C05 (backup encryption for legacy_uap) are direct responses to the AURORA-identified vulnerabilities and the 6-year-old unrotated signing key (DR-056, DR-065). The "pull-forward" is remediation, not roadmap.

---

### 14. CISO Departure + Security Team Attrition
**Category:** HR/Operational | **Evidence:** DR-004, DR-006, DR-062, DR-093, DR-094, DR-095

**Key figures/dates:** CISO Owen Bell departed December 2025 (during active diligence). InfoSec SF: 52 FTE (net −6 YoY), 13.8% 12-month attrition, 9 open roles. InfoSec Dublin: 24 FTE (net −3), 18.5% attrition, 4 open roles. Nina Petrov (Head of Security Engineering, Tier 2): "High" flight risk, "flagged as retention priority given recent attrition." Three additional senior security engineers on elevated retention watch (names in appendix only). Retention plan draft status as of 20 Dec 2025 — not yet Compensation Committee approved. CISO role unnamed in retention plan.

**Consequence:** Security leadership vacuum at integration's most sensitive moment. Authentication/key-management knowledge concentrated in Petrov and three named engineers, all at high flight risk. DR-094 labels this "routine retention and backfill" — directly contradicted by the pattern. Institutional knowledge of the AURORA incident scope may leave with departing staff.

**Materiality: MEDIUM — re-hiring cost $5-20m; residual incident risk from knowledge loss is unquantifiable but potentially material to regulatory obligations**

> **Security/incident connection:** Attrition is post-AURORA; the CISO departure one month after the AURORA Final report and contemporaneous with the DPC inquiry is likely incident-driven, not coincidental. DR-093 footnote redirects to DR-095 ("attrition within specific functions") which remains unproduced.

---

### 15. Cyber Insurance: Notice Deadline Lapsed, Coverage for AURORA Potentially Void
**Category:** Insurance/Financial | **Evidence:** DR-030, DR-081, DR-082

**Key figures/dates:** Policy: $150m aggregate; $5m SIR per claim; sublimits: breach notification $25m, regulatory defence/penalties $20m, forensic investigation $15m, BI $30m. Policy year 1 Jul 2025–30 Jun 2026; 45-day notice condition. INS-01 (DR-030): "Notice deadline passed / under review" for "operational security / account-integrity matter (AURORA / NQ-17)"; "carrier notification being finalised with broker." Zero claim or recovery recorded. DR-082: draft broker notification email dated 11 Dec 2025 — "draft" status means it may not have been sent.

**Consequence:** Late or non-delivery of notice is a standard basis for carrier denial of the entire claim. The "prior known events" exclusion in the policy (DR-081) further excludes any matter where an officer "would have expected" a claim. CISO/GC/Director of Treasury & Insurance were clearly aware of AURORA before the notice deadline. If coverage is voided, the $150m tower is unavailable for the AURORA incident, leaving all regulatory, litigation, and remediation costs uninsured at close.

**Materiality: MEDIUM — $150m insurance tower at risk; if voided, Northstar inherits uninsured exposure that the deal pricing may not contemplate**

> **Security/incident connection:** Directly relates to AURORA. The draft notice (DR-082), the passed deadline (DR-030), and the 45-day condition (DR-081) together create a specific coverage denial risk for the primary incident.

---

### 16. GPL-2.0 Static Linkage in Revenue-Generating Media Transcoding Service
**Category:** IP/Legal | **Evidence:** DR-090

**Key figures/dates:** fastcodec (GPL-2.0) statically linked into Media transcoding service. Remediation target: "next quarter" from 25 Nov 2025 (i.e., Q1 2026 — incomplete at diligence). No historical binary distribution audit conducted. Self-certified "no source-disclosure event to date" — no audit trail cited. Review dated 25 Nov 2025; no external IP counsel sign-off.

**Consequence:** Static linkage under GPL-2.0 triggers copyleft obligation: any external distribution of the transcoding service binary requires making full proprietary source code available under GPL-2.0 on request. If VistaPort has distributed executables containing fastcodec (OTT apps, SDK partners, CDN-embedded builds), active compliance obligations already exist and may have been triggered without acknowledgement. Remediation is incomplete at signing.

**Materiality: MEDIUM — legal risk hard to cap; forced open-sourcing of proprietary transcoding code would materially impair this IP asset; in-house counsel self-assessment is insufficient at this deal size**

---

### 17. Q1 2026 Pipeline: $25.5m On Hold for "Data/Privacy Posture"
**Category:** Commercial | **Evidence:** DR-038

**Key figures/dates:** OPP-019 Northwind Financial expansion: $14.5m gross/$8.7m weighted (60% probability — unjustifiably high for an on-hold deal). OPP-020 BlueOrbit Travel expansion: $11m gross/$6.6m weighted. Both coded "on hold — client reviewing data/privacy posture." Combined: $25.5m gross (18.9% of total $134.9m pipeline), $15.3m weighted (16.6%). Both are existing clients (expansion opportunities). Footnote inserts "routine" with no supporting evidence.

**Consequence:** Both existing clients have independently paused expansion pending VistaPort's data/privacy posture resolution — identical language across two unrelated verticals signals systemic, not account-specific, concern. Weighted pipeline overstated by ~$15.3m. Both deals at risk if the underlying privacy/data issue is not resolved pre-close.

**Materiality: LOW-MEDIUM — $25.5m direct revenue at risk; indicative of broader systemic advertiser concern not yet fully visible in closed-won metrics**

> **Security/incident connection:** "Data/privacy posture" queries from existing clients are the commercial-sales manifestation of the Trust Reset/AURORA event. Same language appears in DR-043 and DR-033 in the context of Trust Reset.

---

### 18. Publisher Supply Agreements: Imminent Re-Openers + Vista Owned & Operated Related-Party
**Category:** Commercial | **Evidence:** DR-041

**Key figures/dates:** Harbor Lifestyle: 70% rev-share, renewal 28 Feb 2026 (already elapsed at signing), "near-term renewal; rev-share re-opener expected," risk "Med." Vista Owned & Operated: 68% rev-share, renewal 28 May 2026, "near-term renewal; rev-share re-opener expected," risk "Med" — identified as "Vista Owned & Operated" with no disclosure of intercompany nature, transfer-pricing basis, or consolidation treatment. Rev-share floor risk: Summit Sports Media, Granite Business Wire, Skyline Weather all at 70%.

**Consequence:** Harbor re-opener may already have occurred or be in active negotiation at close; any upward renegotiation compresses LumenX net take-rate on this inventory. Vista O&O appears to be an intercompany publisher-SSP arrangement where VistaPort pays itself; circular economics need to be eliminated in consolidation modelling. No change-of-control clauses disclosed for any of the 14 agreements.

**Materiality: LOW-MEDIUM — margin compression risk quantifiable only with revenue volumes by publisher (not disclosed); Vista O&O intercompany treatment could affect consolidated EBITDA**

---

## Summary Materiality Matrix

| # | Issue | Category | Materiality | $ Estimate | Security Link |
|---|-------|----------|-------------|------------|--------------|
| 1 | Unaudited FY2025 + $163m seller add-backs | Financial | **HIGH** | ~$1bn valuation sensitivity at deal multiples | Yes (A3 = Trust Reset) |
| 2 | LumenX Q4 revenue collapse + match-rate impairment | Commercial | **HIGH** | ~$154m annualised revenue gap | **Yes** |
| 3 | Advertiser concentration + Meridian uncapped termination | Commercial/Legal | **HIGH** | $188-227m revenue; uncapped liability | **Yes** |
| 4 | Four-regulator privacy/security investigation | Regulatory | **HIGH** | Up to ~$206m GDPR fine | **Yes** |
| 5 | 1.65bn-record backup retention violation | Regulatory | **HIGH** | Up to ~$206m GDPR fine | **Yes** |
| 6 | Search syndication concentration ($326m, redacted) | Commercial | **MEDIUM-HIGH** | $326m at March 2027 renewal risk | No |
| 7 | CoC consents not confirmed pre-signing | Legal | **MEDIUM-HIGH** | 5+ contracts, $500m+ combined revenue | Partial (Meridian) |
| 8 | Pre-2022 consent gap + AtlasID late disclosure | Regulatory | **MEDIUM-HIGH** | Unquantified; proportional to pre-2022 cohort size | **Yes** |
| 9 | Working capital peg: negative $120m, blank outputs | Financial | **MEDIUM-HIGH** | ~$120m NWC + off-peg ~$300m lease PV | No |
| 10 | Deferred revenue haircut (~$357m) | Financial | **MEDIUM** | ~$357m post-close revenue suppression | No |
| 11 | Sales/use tax nexus $6-9m, incomplete | Tax | **MEDIUM** | $6-9m; ceiling unknown | Marginal |
| 12 | Transfer pricing / Irish IP holdco $0 revenue | Tax | **MEDIUM** | Unquantified without TP docs | No |
| 13 | $265m capex backlog, security items accelerated | Operational | **MEDIUM** | $265m committed; $59m security remediation | **Yes** |
| 14 | CISO departure + security team attrition | HR | **MEDIUM** | $5-20m rehiring; knowledge loss risk | **Yes** |
| 15 | Cyber insurance notice lapsed, AURORA coverage void | Insurance | **MEDIUM** | $150m tower at risk | **Yes** |
| 16 | GPL-2.0 static linkage in transcoding service | IP | **MEDIUM** | Uncapped if distribution has occurred | No |
| 17 | $25.5m pipeline on hold for "data/privacy posture" | Commercial | **LOW-MEDIUM** | $25.5m gross | **Yes** |
| 18 | Publisher re-openers + Vista O&O related-party | Commercial | **LOW-MEDIUM** | Margin compression; intercompany distortion | No |