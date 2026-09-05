    #!/usr/bin/env python3
    # Auto-generated RLM audit replay step 0007.

    import sys
    from pathlib import Path

    _rlm_run_dir = Path(__file__).resolve().parents[1]
    _rlm_runtime_dir = _rlm_run_dir / "runtime"
    sys.path.insert(0, str(_rlm_runtime_dir))

    from rlm_audit_runtime import load_env, save_env

    globals().update(load_env(_rlm_run_dir, step_index=7))
    try:
        blob = []
for d in incident_ids:
    blob.append(f"\n\n===== {d} | {docs[d]['title']} | {docs[d]['file']} =====\n{docs[d]['text']}")
blob = "".join(blob)

prompt = (
"You are the buy-side M&A diligence lead for Northstar (acquiring VistaPort Media, EV US$4.83bn).\n"
"Below are 25 full documents from the data room that appear to relate to a single underlying security/privacy incident, "
"described differently by different functions (security/forensics, product, finance, legal, HR, board).\n"
"Your job: CONNECT THE THREADS and expose what actually happened and what is being under-disclosed.\n\n"
"Produce:\n"
"1. MASTER TIMELINE: every relevant event in chronological order with EXACT date and the DR-### source. Include first detection, internal escalations, forensic findings, the 'Trust Reset'/password-reset/login-friction events, regulator contact, insurer notice, board/disclosure-committee discussions, and security-team departures.\n"
"2. WHAT ACTUALLY HAPPENED: the most likely true narrative (scope of data exfiltrated, # records/users, data types, root cause), citing DR-### and quoting key figures verbatim.\n"
"3. DIVERGENT FRAMING: a table of how the SAME incident is characterised in each function's document vs. the forensic reality â€” quote the euphemism and name the DR-### (e.g. 'login friction' DR-060 vs forensic 'exfiltration' DR-069). Flag every instance where the public/management framing appears to understate the forensic finding.\n"
"4. WHO KNEW WHAT, WHEN: evidence of knowledge at exec/board/disclosure-committee level and any indications of deliberate non-disclosure to the buyer or regulators, with DR-### and quotes.\n"
"5. DISCLOSURE/REP RISK: how this interacts with the seller representations (DR-087) and disclosure controls (DR-086) â€” is the buyer being asked to rep around a known breach? Quote relevant rep language.\n"
"6. ALL DOLLAR FIGURES & COUNTS relevant to sizing the exposure (records, active accounts, GB egressed, reserve amounts, insurance limits/sublimits/retentions, any cost estimates), each with DR-### and verbatim figure.\n"
"Be exhaustive, precise, cite DR-### on every claim, and quote verbatim. Do not soften the language the way the documents do.\n\n"
"----- DOCUMENTS -----\n" + blob
)
print("prompt chars:", len(prompt))
incident_synthesis = llm_query(prompt, timeout=600)
globals()['incident_synthesis'] = incident_synthesis
print("output chars:", len(incident_synthesis))
with open(r"C:\Users\johna\OneDrive\Documents\DATA ROOM TEST SONNET\incident_synthesis.md","w",encoding="utf-8") as fh:
    fh.write(incident_synthesis)
print("saved incident_synthesis.md")
    finally:
        save_env(_rlm_run_dir, step_index=7, namespace=globals())
