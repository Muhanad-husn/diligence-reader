    #!/usr/bin/env python3
    # Auto-generated RLM audit replay step 0005.

    import sys
    from pathlib import Path

    _rlm_run_dir = Path(__file__).resolve().parents[1]
    _rlm_runtime_dir = _rlm_run_dir / "runtime"
    sys.path.insert(0, str(_rlm_runtime_dir))

    from rlm_audit_runtime import load_env, save_env

    globals().update(load_env(_rlm_run_dir, step_index=5))
    try:
        import os
out_path = r"C:\Users\johna\OneDrive\Documents\DATA ROOM TEST SONNET\findings_inventory.md"
with open(out_path, "w", encoding="utf-8") as fh:
    fh.write("# Per-Document Findings Inventory (RLM leaf extraction)\n")
    for did in order:
        fh.write("\n\n" + "="*80 + "\n")
        fh.write(findings[did].strip() + "\n")
total = sum(len(findings[d]) for d in order)
print("written:", out_path, "total chars:", total)
# also store as buffer
add_buffer("FINDINGS_INVENTORY saved to findings_inventory.md, total chars %d" % total)
    finally:
        save_env(_rlm_run_dir, step_index=5, namespace=globals())
