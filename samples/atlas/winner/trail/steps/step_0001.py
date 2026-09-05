    #!/usr/bin/env python3
    # Auto-generated RLM audit replay step 0001.

    import sys
    from pathlib import Path

    _rlm_run_dir = Path(__file__).resolve().parents[1]
    _rlm_runtime_dir = _rlm_run_dir / "runtime"
    sys.path.insert(0, str(_rlm_runtime_dir))

    from rlm_audit_runtime import load_env, save_env

    globals().update(load_env(_rlm_run_dir, step_index=1))
    try:
        import re
# Split into per-document sections using the DR-### header pattern
# Header block: line of '=', then "DR-### | Title", then "folder: ... | file: ...", then line of '='
pattern = re.compile(r'={50,}\n(DR-\d{3}) \| (.+?)\nfolder: (.+?) \| file: (.+?)\n={50,}\n')
matches = list(pattern.finditer(content))
print("num doc headers:", len(matches))

docs = {}  # id -> dict(title, folder, file, text)
for i, m in enumerate(matches):
    did = m.group(1)
    title = m.group(2).strip()
    folder = m.group(3).strip()
    fname = m.group(4).strip()
    start = m.end()
    end = matches[i+1].start() if i+1 < len(matches) else len(content)
    body = content[start:end].strip()
    docs[did] = dict(title=title, folder=folder, file=fname, text=body, chars=len(body))

# size distribution
sizes = sorted([(d, docs[d]['chars']) for d in docs], key=lambda x:-x[1])
print("total docs:", len(docs))
print("largest:", sizes[:5])
print("smallest:", sizes[-5:])
print("total body chars:", sum(docs[d]['chars'] for d in docs))
# persist
globals()['docs'] = docs
    finally:
        save_env(_rlm_run_dir, step_index=1, namespace=globals())
