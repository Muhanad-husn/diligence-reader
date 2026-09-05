    #!/usr/bin/env python3
    # Auto-generated RLM audit replay step 0003.

    import sys
    from pathlib import Path

    _rlm_run_dir = Path(__file__).resolve().parents[1]
    _rlm_runtime_dir = _rlm_run_dir / "runtime"
    sys.path.insert(0, str(_rlm_runtime_dir))

    from rlm_audit_runtime import load_env, save_env

    globals().update(load_env(_rlm_run_dir, step_index=3))
    try:
        import re
pattern = re.compile(r'={50,}\r?\n(DR-\d{3}) \| (.+?)\r?\nfolder: (.+?) \| file: (.+?)\r?\n={50,}\r?\n')
matches = list(pattern.finditer(content))
print("num doc headers:", len(matches))
docs = {}
order = []
for i, m in enumerate(matches):
    did = m.group(1)
    start = m.end()
    end = matches[i+1].start() if i+1 < len(matches) else len(content)
    body = content[start:end].strip()
    docs[did] = dict(title=m.group(2).strip(), folder=m.group(3).strip(), file=m.group(4).strip(), text=body, chars=len(body))
    order.append(did)
globals()['docs'] = docs
globals()['order'] = order
sizes = sorted([(d, docs[d]['chars']) for d in docs], key=lambda x:-x[1])
print("total docs:", len(docs), "| total body chars:", sum(docs[d]['chars'] for d in docs))
print("largest:", sizes[:6])
print("smallest:", sizes[-6:])
    finally:
        save_env(_rlm_run_dir, step_index=3, namespace=globals())
