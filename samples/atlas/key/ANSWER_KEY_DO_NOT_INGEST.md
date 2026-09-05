# PROJECT ATLAS — PRIVATE ANSWER KEY  (DO NOT INGEST INTO THE TEST AGENT)

> This file and everything in `evaluator_private/` must **never** be supplied to
> the diligence agent under test. It exists only to grade the agent's output.
> All entities, people and data are fictional.

---

## 1. The issue in plain English

VistaPort Media has suffered an **undisclosed account-data compromise and
authentication-integrity incident**. Between **18-20 October 2025**,
an attacker performed anomalous bulk reads of a legacy account-profile backup
(`legacy_uap_backup_2021.tar.gz`) held in the Kestrel object store. That backup
contained roughly **912.8m** historical profile records
(~**286m** of them belonging to accounts active in
the last 24 months), including names, usernames, email and recovery-email
addresses, phone numbers, dates of birth, salted password hashes, password-reset
tokens and security-question hashes — and, for **8.4m**
legacy small-business accounts, *improperly encrypted security-question answers*.
The same period shows **forged session-cookie activity**, enabled because a
**VPAuth legacy session-signing key had not been rotated since 2019**.

Security engineering treated this as serious (probable unauthorised bulk export),
but management and legal **softened the language** into a "network-quality"
investigation (**NQ-17**), a "**credential hygiene**" programme and "**Trust Reset**",
and the forensic **executive summary was sanitised** relative to the technical
draft. Management had enough information **before signing** to know the matter
might be material, yet the **seller representation schedule states there have been
no material security incidents in the last 24 months**.

Outside counsel privately estimated combined exposure of **$240m–$465m**;
finance booked only a **$12m** "trust & safety" contingency.
Cyber insurance is likely to respond for little or none of it (late notice past
the 45-day window plus a prior-known-events exclusion). Several major advertiser
contracts contain user-trust / security / notification covenants that create
credit, renegotiation or termination leverage, and the forced resets measurably
depressed email WAU, mobile MAU, ad impressions and ad yield — **the very metrics
the synergy model assumes are unaffected.**

**Net:** the asset is worth materially less than the seller-curated story implies.
A fair buyer response is a **price reduction of ~$400m (range $375m–$525m)** or an
equivalent **special indemnity / escrow** plus specific reps — *not* walking away.

---

## 2. The reasoning chain a good agent should follow

1. **Spot the anomaly in the logs.** SIEM exports (DR-067) and the Kestrel
   object-access log (DR-071) show bulk reads of `legacy_uap_backup_2021.tar.gz`
   on 18-20 October 2025 from unusual principals / foreign ASNs,
   with a large data-egress spike.
2. **Establish the technical root cause.** The backup should not have existed
   (retention policy DR-052 vs backup inventory DR-073 showing it retained beyond
   the 36-month limit with 912.8m records), and the
   VPAuth legacy signing key was unrotated since 2019
   (key-rotation exception log DR-074; vulnerability register DR-065) — enabling
   **cookie forging**.
3. **Read the security narrative, then the management narrative.** The NQ-17
   ticket (DR-068) shows security engineering calling this *probable unauthorised
   bulk access*, then a **management reclassification** to "network quality".
   The IronLake **draft** (DR-069) says "bulk export probable" with
   286m active / 912.8m
   total records; the **final** summary (DR-070) is materially softer. The product
   postmortem (DR-060) reframes everything as benign "login friction".
4. **Find the governance/disclosure contradiction.** Disclosure-committee minutes
   (DR-013), exec-committee action items (DR-014) and the disclosure-controls memo
   (DR-086) show management knew of an open materiality question and chose caution /
   "external comms hold". Yet the **seller rep schedule (DR-087)** represents *no
   material cyber incident in 24 months* and *adequate reserves* — a direct
   contradiction and a likely rep breach.
5. **Quantify exposure and test the reserve.** Outside-counsel memo (DR-088) =
   **$240m–$465m**; finance booked
   **$12m** (DR-029, DR-018). The gap is the core of the price chip.
6. **Check insurance.** The cyber policy (DR-081) has a 45-day notice condition and
   a prior-known-events exclusion; the broker notice (DR-082) was drafted
   11 December 2025 — after the window — and
   hedges on what the matter is called. Recovery is doubtful (DR-030).
7. **Trace the commercial consequences.** Advertiser contracts (DR-035, DR-046,
   DR-085) carry user-trust/security/notification covenants; retention/churn notes
   (DR-033, DR-039), customer-success readout (DR-042), Helios IO pause (DR-036)
   and brand-safety feedback (DR-043) show clients already reacting.
8. **Connect metrics to valuation.** Engagement metrics (DR-048, DR-049, DR-050,
   DR-055, DR-099) show real declines after 18 October 2025; the
   QoE (DR-023) and EBITDA bridge (DR-025) treat incident costs as non-recurring;
   the **synergy model (DR-096)** assumes 615m MAU / 408m mobile MAU / normalised
   yield and **its own sensitivity tabs** show hundreds of $m of NPV at risk if
   those assumptions are corrected.
9. **Synthesise a price-chip / escrow recommendation** with a number and a
   structure — not a vague concern, and not "walk away".

---

## 3. Minimum document set needed to support the conclusion

- **DR-069** — AURORA — Phase 1 Technical Findings (DRAFT, Privileged)
- **DR-073** — Backup Retention Inventory
- **DR-074** — Key Rotation Exception Log
- **DR-068** — Network Quality Ticket NQ-17 (Redacted)
- **DR-013** — Disclosure Committee Minutes — 29 October 2025
- **DR-087** — Seller Representation Schedule (Draft)
- **DR-088** — Outside Counsel Privacy Risk Memo (Redacted, Privileged)
- **DR-029** — Contingency Reserve Memo — Trust & Safety Matters
- **DR-081** — Cyber Insurance Policy — 2025/26
- **DR-082** — Draft Cyber-Insurance Notice to Broker
- **DR-096** — Integration Synergy Model
- **DR-035** — Master Services Agreement — Meridian Media Agency (Redacted)
- **DR-050** — VistaMail Weekly KPIs — Q4 2025
- **DR-048** — User Metrics Dashboard — Q3/Q4 2025

A strong answer can be built from these ~14 documents; the others corroborate.

---

## 4. Best supporting documents by category

### 1. SIEM / authentication logs & backup inventories

- **DR-067** — SIEM Alert Exports — Oct–Nov 2025
- **DR-071** — Kestrel Object-Store Access Log Extract
- **DR-073** — Backup Retention Inventory
- **DR-074** — Key Rotation Exception Log
- **DR-065** — Vulnerability Register — Q4 2025
- **DR-066** — IAM Privileged Access Review — Q4 2025
- **DR-061** — Snowcap Data Warehouse — Table Catalogue

### 2. Security ticket & forensic draft language

- **DR-068** — Network Quality Ticket NQ-17 (Redacted)
- **DR-069** — AURORA — Phase 1 Technical Findings (DRAFT, Privileged)
- **DR-070** — AURORA — Executive Summary (Final)
- **DR-060** — Product Incident Postmortem — November 2025 Login Friction
- **DR-063** — Penetration Test 2025 — Executive Summary
- **DR-064** — SOC 2 Type II Report — 2025 (Summary)

### 3. Legal / regulatory correspondence

- **DR-079** — Regulatory Correspondence Log
- **DR-080** — Draft Response to the Irish Data Protection Commission
- **DR-086** — Disclosure Controls & Procedures Memo
- **DR-088** — Outside Counsel Privacy Risk Memo (Redacted, Privileged)
- **DR-089** — Class Action Monitoring Memo — Sector Privacy Litigation
- **DR-084** — Data Processing Agreements Schedule

### 4. Seller representations & disclosure-committee materials

- **DR-013** — Disclosure Committee Minutes — 29 October 2025
- **DR-014** — Executive Committee — Action Items, 5 November 2025
- **DR-087** — Seller Representation Schedule (Draft)
- **DR-012** — Board Minutes — Q4 2025
- **DR-015** — Strategic Alternatives — Board Deck (January 2026)
- **DR-004** — Diligence Q&A Log

### 5. Insurance policy & notice timing

- **DR-081** — Cyber Insurance Policy — 2025/26
- **DR-082** — Draft Cyber-Insurance Notice to Broker
- **DR-030** — Insurance Claims & Recoveries Schedule

### 6. Product / support metrics (forced resets, engagement decline)

- **DR-048** — User Metrics Dashboard — Q3/Q4 2025
- **DR-049** — Mobile App Retention Cohorts — 2025
- **DR-050** — VistaMail Weekly KPIs — Q4 2025
- **DR-055** — Personalisation Model — Performance Review
- **DR-059** — Trust Reset — Project Brief
- **DR-099** — Customer Support Ticket Taxonomy — Q4 2025
- **DR-043** — Brand Safety & Client Feedback — Q4 2025
- **DR-058** — User Notification System — Runbook

### 7. Customer / advertiser contracts & churn

- **DR-035** — Master Services Agreement — Meridian Media Agency (Redacted)
- **DR-046** — EU Advertiser DPA Terms — Summary
- **DR-085** — Material Contracts — Change of Control & Covenants Summary
- **DR-033** — Advertiser Retention Report — Q4 2025
- **DR-039** — Advertiser Churn & Win/Loss Notes
- **DR-036** — Helios Retail Group — Insertion Orders 2025
- **DR-042** — Customer Success — Weekly Readout, 14 November 2025
- **DR-032** — Top 50 Advertisers — FY2025

### 8. Financial reserves & synergy-model assumptions

- **DR-029** — Contingency Reserve Memo — Trust & Safety Matters
- **DR-023** — Seller Quality of Earnings — Addendum
- **DR-025** — Adjusted EBITDA — Add-Back Schedule
- **DR-018** — Draft Consolidated Financial Statements — FY2025 (Unaudited)
- **DR-096** — Integration Synergy Model
- **DR-028** — Capex Backlog & IT Modernisation Plan
- **DR-021** — Monthly Finance Pack — November 2025
- **DR-022** — Monthly Finance Pack — December 2025

---

## 5. Suggested price reduction and calculation

**Headline: a price chip of approximately $400m, defensible range $375m–$525m**
(equivalently a special indemnity/escrow of ~$400m–$500m plus specific reps).

**Step A — Net unreserved incident exposure.**

| Exposure component | Low | High |
|---|---|---|
| Regulatory fines & penalties (EU/UK/US state) | $60m | $160m |
| User notification, call-centre & credit monitoring | $70m | $120m |
| Security remediation (key rotation, backup redesign, auth migration) | $30m | $45m |
| Advertiser/customer contract credits & renegotiation | $25m | $60m |
| Civil litigation / class settlement reserve | $55m | $80m |
| **Combined (outside counsel, DR-088)** | **$240m** | **$465m** |

- Midpoint exposure ≈ **$352m**.
- Less booked reserve: **−$12m** (DR-029).
- Less expected insurance recovery: **≈ $0–$50m** only. The 45-day notice
  condition (DR-081) appears blown (notice drafted 11 December 2025,
  DR-082) and the prior-known-events exclusion likely applies; sublimits
  (notification $25m / reg-defence
  $20m) are small. Risk-weight ≈ **−$25m**.
- **Net unreserved exposure ≈ $300m–$340m** (probability-weighted to midpoint).

**Step B — Engagement / synergy impairment.**

- Synergy NPV is stated at **$410m** (DR-096) assuming flat
  615m MAU, 408m mobile MAU and yield index 1.00. Realised post-October values
  (DR-048/050) are ~1.5–2.5% lower on MAU and ~3–6% lower on ad-yield index, with
  recovery "slower than modelled" (DR-022). The model's own sensitivity tabs imply
  **~$50m–$120m** of synergy/standalone value at risk. Risk-weight ≈ **$50m–$90m**.

**Step C — Combine (avoiding double counting).**
- Net exposure (A) **$300m–$340m** + synergy/engagement haircut (B) **$50m–$90m**
  ⇒ **~$375m–$430m central**, widening to **$525m** at the high end (worse
  affected-user counts, aggressive regulators, full insurance denial, rep-breach
  litigation) and **$375m** floor at the low end.
- **Best single number: ≈ $400m** (≈ 8% of the $4.83bn offer).

**Structure.** Because timing/quantum are uncertain, the *cleanest* deal outcome
is a hybrid: a modest fixed price reduction **plus** a ring-fenced special
indemnity/escrow (~$400m–$500m) for the AURORA matter with bespoke reps and a
longer survival period. An agent that recommends escrow/indemnity of similar
magnitude instead of a flat cut should receive full credit.

**EBITDA-quality cross-check (supporting, not additive):** the $34m "account
integrity / Trust Reset" add-back (DR-025/023) is substantially incident-driven
and probably recurring; removing it (~$741m adj EBITDA) at the implied ~6.2x
EV/EBITDA multiple is ~$210m of value — directionally consistent with, and
already captured within, the exposure-based chip above.

---

## 6. Why this is analogous to the public Verizon/Yahoo repricing

When Verizon agreed to buy Yahoo's operating business (~$4.83bn), Yahoo
subsequently disclosed massive historical data breaches (ultimately ~3bn
accounts, including forged-cookie activity). The parties **amended the deal to cut
the price by ~$350m** (to ~$4.48bn) and to **share certain breach liabilities**,
rather than terminating. Project Atlas mirrors the *pattern*: an attractive
ad-tech/identity asset, a **previously undisclosed account-data/authentication
incident** (including cookie-forging), and the correct buyer response being a
**price reduction / liability-sharing mechanism**, not abandonment. The $4.83bn
headline and the ~$375m–$525m chip are deliberately in the same neighbourhood as
the public precedent. All Project Atlas entities and facts are fictional.

---

## 7. Decoy issues (real but less material)

- **DR-031** — Sales/use tax nexus exposure ($6-9m) — real but an order of magnitude smaller and fully estimable.
- **DR-034** — Search-partner concentration (~22% of search revenue) — a genuine concentration risk, not a value-destroying contingency.
- **DR-076** — Email-gateway phishing/BEC noise — routine security operations, unrelated to the account-data incident.
- **DR-090** — Open-source/GPL licence clean-up — low-cost remediation.
- **DR-094** — Executive/security retention plan — overlaps with attrition but is ordinary deal retention, not the issue itself.

Each is genuine and worth a diligence note, but none is value-destroying at the
scale of the AURORA matter; an agent that elevates a decoy over the incident, or
treats the incident as merely one of several equal items, should lose points.

---

## 8. Gold standard answer (what a top agent should produce)

> VistaPort has an **undisclosed account-data and authentication-integrity
> incident (internally AURORA / NQ-17 / "Trust Reset")**. On
> 18-20 October 2025 a legacy profile backup
> (`legacy_uap_backup_2021.tar.gz`, ~912.8m records,
> ~286m active) was subject to probable
> unauthorised bulk export, with forged session cookies enabled by a VPAuth
> signing key unrotated since 2019. Security
> flagged it; management reclassified and softened it (DR-068/069/070), the
> disclosure committee left materiality open (DR-013/086), yet the seller reps
> deny any material incident (DR-087). Outside counsel pegs exposure at
> $240m–$465m (DR-088) against a
> $12m reserve (DR-029); cyber insurance likely fails
> for late notice / prior-known-events (DR-081/082); advertiser user-trust
> covenants (DR-035/046/085) and measurable engagement decline (DR-048/050/099)
> further impair value and the synergy case (DR-096). **Recommend a price
> reduction of ~$400m (range $375m–$525m) or an equivalent special
> indemnity/escrow with bespoke reps — not termination.**

---

## 9. Acceptable alternative formulations

- Recommending a **special indemnity + escrow of ~$400m–$500m** (with bespoke
  cyber/privacy reps and extended survival) **instead of** a flat price cut.
- A price-chip number anywhere in **$375m–$525m**, provided it is tied to the
  exposure memo, the reserve gap, the insurance weakness and the synergy/metric
  impact.
- Framing the headline as a **rep-and-warranty breach + specific-indemnity**
  problem rather than a pure valuation problem, so long as quantum is in range.
- A **conditional / two-track** recommendation (e.g. confirmatory forensic access
  + interim escrow, converting to a fixed chip once affected-user counts are
  established).
- Emphasis on **regulatory + class-action + contract-credit** stacking as the
  driver, as long as the ~$400m order of magnitude and the "reprice, don't walk"
  conclusion are preserved.

Answers that should **lose** marks: "walk away" with no price/escrow thesis;
"raise it in Q&A" with no quantification; fixating on a decoy (tax, OSS, search
concentration); or asserting a breach with no document citations.
