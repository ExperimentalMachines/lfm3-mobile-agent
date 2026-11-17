receipt_ok() { MAX_STEPS=${MAX_STEPS:-} EPOCHS=${EPOCHS:-} MAX_AGENT_ROWS=${MAX_AGENT_ROWS:-} LR=${LR:-} LORA_R=${LORA_R:-} BS=${BS:-} GA=${GA:-} python - "$1" "$MODEL" "$OUT" <<'PY'
import json, os, sys
try:
    r = json.load(open(sys.argv[1])); a = r["args"]
    w = r.get("weights") or {}
    want = {"max_steps": int(os.environ.get("MAX_STEPS") or -1), "epochs": float(os.environ.get("EPOCHS") or 1),
            "max_agent_rows": int(os.environ.get("MAX_AGENT_ROWS") or 0), "lr": float(os.environ.get("LR") or 2e-4),
            "lora_r": int(os.environ.get("LORA_R") or 64), "bs": int(os.environ.get("BS") or 8),
            "grad_accum": int(os.environ.get("GA") or 4)}
    same_cfg = all(type(v)(a.get(k)) == v for k, v in want.items())
    ok = (same_cfg and a.get("model_id") == sys.argv[2] and a.get("out") == sys.argv[3] and w
          and all(v > 0 and os.path.getsize(os.path.join(sys.argv[3], "merged", k)) == v for k, v in w.items())
          and r.get("max_steps", 0) > 0 and r.get("global_step", 0) >= r["max_steps"])
except Exception:
    ok = False
sys.exit(0 if ok else 1)
PY
}

receipt_ok "$OUT/train_receipt.json"
