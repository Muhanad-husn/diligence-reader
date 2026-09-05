    #!/usr/bin/env python3
    # Auto-generated RLM audit replay step 0004.

    import sys
    from pathlib import Path

    _rlm_run_dir = Path(__file__).resolve().parents[1]
    _rlm_runtime_dir = _rlm_run_dir / "runtime"
    sys.path.insert(0, str(_rlm_runtime_dir))

    from rlm_audit_runtime import load_env, save_env

    globals().update(load_env(_rlm_run_dir, step_index=4))
    try:
        # Per-document extraction. One leaf call per doc, in DR order.
def build_prompt(did):
    d = docs[did]
    return (
        "You are a forensic M&A buy-side diligence analyst reviewing one document from a data room.\n"
        "The buyer (Northstar) is acquiring VistaPort Media for an enterprise value of US$4.83bn.\n"
        "Read the document below and extract findings with ZERO fluff. Be precise and quote verbatim.\n\n"
        f"DOCUMENT {did}: {d['title']} (folder: {d['folder']}; file: {d['file']})\n"
        "----- DOCUMENT TEXT -----\n"
        f"{d['text']}\n"
        "----- END DOCUMENT -----\n\n"
        "Return EXACTLY these sections (omit a section only if truly nothing):\n"
        f"### {did} â€” <one-line what this document is>\n"
        "**Red flags / risks:** bullet list. For each: the specific issue, any euphemism/downplaying/inconsistency you notice, and the financial or legal consequence. If none, write 'none material'.\n"
        "**Key figures/dates:** bullet list of every dollar amount, user/record count, percentage, and material date, quoted verbatim with what it refers to.\n"
        "**Cross-references:** anything that points to another matter, codename, project, ticket, person, regulator, or document (e.g. AURORA, Trust Reset, Kestrel, NQ-17, Irish DPC, contingency reserve, escrow, change-of-control). Quote the phrase.\n"
        "**Smell test:** in 1-2 sentences, what (if anything) looks concealed, under-disclosed, euphemistic, timing-suspicious, or contradicted elsewhere.\n"
    )

prompts = [build_prompt(did) for did in order]
print("num prompts:", len(prompts))
outs = llm_query_map(prompts, max_workers=8)
print("num outputs:", len(outs))
# store
findings = {order[i]: outs[i] for i in range(len(order))}
globals()['findings'] = findings
# sanity: any empty/short outputs?
short = [d for d in order if len(findings[d].strip()) < 80]
print("short/empty outputs:", short)
# preview one
print("\n===== SAMPLE DR-069 =====\n", findings.get('DR-069','')[:1500])
    finally:
        save_env(_rlm_run_dir, step_index=4, namespace=globals())
