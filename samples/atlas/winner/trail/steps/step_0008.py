    #!/usr/bin/env python3
    # Auto-generated RLM audit replay step 0008.

    import sys
    from pathlib import Path

    _rlm_run_dir = Path(__file__).resolve().parents[1]
    _rlm_runtime_dir = _rlm_run_dir / "runtime"
    sys.path.insert(0, str(_rlm_runtime_dir))

    from rlm_audit_runtime import load_env, save_env

    globals().update(load_env(_rlm_run_dir, step_index=8))
    try:
        # Build a digest of NON-incident findings to populate "lesser issues" and catch anything missed.
incident = set(incident_ids)
non_incident = [d for d in order if d not in incident]
blob = []
for d in non_incident:
    blob.append(f"\n\n##### {d} | {docs[d]['title']}\n{findings[d].strip()}")
blob = "".join(blob)
print("non-incident docs:", len(non_incident), "digest chars:", len(blob))

prompt = (
"You are the buy-side M&A diligence lead for Northstar (acquiring VistaPort Media, EV US$4.83bn).\n"
"Below are per-document finding notes for the data-room documents that are NOT part of the main security-incident cluster.\n"
"Identify and rank the DISTINCT, genuinely MATERIAL diligence issues (financial, tax, commercial, legal, IP, HR, regulatory, operational). "
"EXCLUDE generic/no-issue notes. For each issue give: a short title; the specific DR-### evidence; the verbatim key figure(s)/date(s); the financial or legal consequence; and a rough materiality (High/Medium/Low) with a $ estimate where the documents support one.\n"
"ALSO: flag any item here that actually connects back to the security/privacy incident (e.g. Q4 advertising softness, user-metric adjustments, customer termination rights, accelerated capex, attrition, tax/nexus, insurance) â€” note the connection explicitly.\n"
"Be concise but specific. Output a ranked markdown list. Do not invent figures not present in the notes.\n\n"
"----- PER-DOCUMENT NOTES -----\n" + blob
)
lesser = llm_query(prompt, timeout=600)
globals()['lesser']=lesser
with open(r"C:\Users\johna\OneDrive\Documents\DATA ROOM TEST SONNET\lesser_issues.md","w",encoding="utf-8") as fh:
    fh.write(lesser)
print("output chars:", len(lesser))
print(lesser[:200])
    finally:
        save_env(_rlm_run_dir, step_index=8, namespace=globals())
