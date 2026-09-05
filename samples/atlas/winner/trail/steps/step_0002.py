    #!/usr/bin/env python3
    # Auto-generated RLM audit replay step 0002.

    import sys
    from pathlib import Path

    _rlm_run_dir = Path(__file__).resolve().parents[1]
    _rlm_runtime_dir = _rlm_run_dir / "runtime"
    sys.path.insert(0, str(_rlm_runtime_dir))

    from rlm_audit_runtime import load_env, save_env

    globals().update(load_env(_rlm_run_dir, step_index=2))
    try:
        import re
# show raw repr of a header region
idx = content.find("DR-002")
print(repr(content[idx-120:idx+160]))
print("----- count of 'DR-0' headers via simpler search -----")
print(len(re.findall(r'\nDR-\d{3} \| ', content)))
print("----- eq lines -----")
eqs = [l for l in content.splitlines() if set(l.strip())=={'='} and len(l.strip())>10]
print("num '=' lines:", len(eqs), "sample len:", len(eqs[0]) if eqs else None)
    finally:
        save_env(_rlm_run_dir, step_index=2, namespace=globals())
