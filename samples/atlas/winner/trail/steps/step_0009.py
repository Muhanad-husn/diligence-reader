    #!/usr/bin/env python3
    # Auto-generated RLM audit replay step 0009.

    import sys
    from pathlib import Path

    _rlm_run_dir = Path(__file__).resolve().parents[1]
    _rlm_runtime_dir = _rlm_run_dir / "runtime"
    sys.path.insert(0, str(_rlm_runtime_dir))

    from rlm_audit_runtime import load_env, save_env

    globals().update(load_env(_rlm_run_dir, step_index=9))
    try:
        summary = (
"PROJECT ATLAS â€” RLM FINDINGS INVENTORY (100 docs DR-001..DR-100).\n"
"Most material issue: concealed/under-disclosed mass data breach.\n"
"- 18-20 Oct 2025: 5 bulk-read events, ~1,840 GB egress, 3 foreign ASNs against legacy_uap_backup_2021.tar.gz (DR-069; corroborated DR-073, DR-061).\n"
"- ~912.8m historical profile records; ~286m active within 24m; ~8.4m SMB with improperly encrypted security answers; vpauth-legacy-2019 key unrotated since 2019; ~41,500 forged/replayed sessions (DR-069, DR-071).\n"
"- Forensic 'bulk export is probable' (DR-069 draft) softened to 'not definitively established' in final 'per counsel's direction' (DR-070, DR-100).\n"
"- Re-labelled across functions: network-quality (DR-068), login friction SEV-2 (DR-060), proactive credential-hygiene/Trust Reset (DR-059), operational matter to board (DR-012), 'not established' to Irish DPC (DR-080), 'not quantified' to Northstar (DR-015).\n"
"- Reserve $12m (DR-029) vs outside counsel $240m-$465m (DR-088). CISO: 'cannot reconcile $12m with the technical picture' (DR-100).\n"
"- 4 regulators open under AURORA: Irish DPC, UK ICO, CA AG, NY AG (DR-079).\n"
"- Cyber tower $150m at risk: 45-day notice likely blown (aware ~21 Oct; notice draft 11 Dec); policy says awareness not deferred to final report; prior-known-events exclusion (DR-081, DR-082, DR-030, DR-100).\n"
"- EBITDA inflated: $34m Trust Reset add-back A3 as 'non-recurring' (DR-025); at 6.23x ~ $210m EV.\n"
"- Reps drafted around the breach; disclosure schedule generic; buyer Q-007 answered evasively (DR-087, DR-086, DR-004).\n"
"- Revenue: LumenX Q4 $439m vs Q3 $497m, addressability/identity-signal driven, mis-attributed to seasonality (DR-024, DR-037, DR-055); $410m synergy NPV at risk (DR-015).\n"
"- People: CISO + 3 senior security engineers resigned over handling (DR-095).\n"
"Best estimate: ~$350m direct liability (range $240-465m) + ~$210m overstated EV + up to ~$145m insurance swing.\n"
"Recommendation: reprice ~$210m; uncapped AURORA special indemnity + $350m-$465m escrow; specific disclosure + rep reset as conditions; else withdraw.\n"
"Full report: data_room/Diligence_Findings_Report.md. Supporting: incident_synthesis.md, lesser_issues.md, findings_inventory.md."
)
FINAL(summary)
    finally:
        save_env(_rlm_run_dir, step_index=9, namespace=globals())
