    #!/usr/bin/env python3
    # Auto-generated RLM audit replay step 0006.

    import sys
    from pathlib import Path

    _rlm_run_dir = Path(__file__).resolve().parents[1]
    _rlm_runtime_dir = _rlm_run_dir / "runtime"
    sys.path.insert(0, str(_rlm_runtime_dir))

    from rlm_audit_runtime import load_env, save_env

    globals().update(load_env(_rlm_run_dir, step_index=6))
    try:
        incident_ids = ["DR-008","DR-009","DR-010","DR-011","DR-012","DR-013","DR-014","DR-015",
                "DR-029","DR-059","DR-060","DR-068","DR-069","DR-070","DR-071","DR-075",
                "DR-076","DR-080","DR-082","DR-086","DR-088","DR-089","DR-095","DR-100","DR-087"]
tot = sum(docs[d]['chars'] for d in incident_ids)
print("cluster docs:", len(incident_ids), "total chars:", tot, "~tokens:", tot//4)
for d in incident_ids:
    print(d, docs[d]['chars'], docs[d]['title'][:55])
globals()['incident_ids']=incident_ids
    finally:
        save_env(_rlm_run_dir, step_index=6, namespace=globals())
