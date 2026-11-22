import json, os
os.chdir("/Users/alpha/lfm3-android/results")
F = {"v1": "androidcontrol/lfm3vl2b-ac-lora_ft.metrics.json", "v2": "androidcontrol/lfm3vl2b-v2mix-lora_ft.metrics.json",
     "v3": "androidcontrol/lfm3vl2b-v3mix-lora_ft.metrics.json", "v4": "v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft.metrics.json",
     "v41": "v41_dev/lfm3vl2b-v41-lora_ft.metrics.json", "v42": "v42_dev/lfm3vl2b-v42-lora_ft.metrics.json",
     "base": "androidcontrol/lfm3vl2b-ac-lora_base.metrics.json"}
for k, f in F.items():
    if not os.path.exists(f): print(k, "missing", f); continue
    d = json.load(open(f))
    h = d.get("high", {}).get("overall", {}); l = d.get("low", {}).get("overall", {})
    pt = h.get("per_type", {})
    other = {kk: vv for kk, vv in d.items() if kk not in ("high", "low")}
    term = {kk: (json.dumps(vv)[:250]) for kk, vv in other.items()}
    print(k, "high step_sr", round(h.get("step_sr", -1), 3), "ep_sr", round(h.get("episode_sr", -1), 3), "type_match", round(h.get("type_match", -1), 3),
          "low step_sr", round(l.get("step_sr", -1), 3))
    print("   per-type step_sr:", {t: (v["n"], round(v["step_sr"], 3)) for t, v in pt.items()})
    print("   app_unseen:", round(d["high"].get("by_subsplit", {}).get("app_unseen", {}).get("step_sr", -1), 3), "IDD:", round(d["high"].get("by_subsplit", {}).get("IDD", {}).get("step_sr", -1), 3))
    print("   other keys:", term)
for v, dd in [("v4", "v4_dev/hub/eval/lfm3_v4_dev_%s.metrics.json"), ("v41", "v41_dev/lfm3_v41_dev_%s.metrics.json"), ("v42", "v42_dev/lfm3_v42_dev_%s.metrics.json")]:
    out = {}
    for s in ["answer", "complete", "screenqa", "odyssey", "amex"]:
        f = dd % s
        if os.path.exists(f):
            m = json.load(open(f))
            o = m.get("overall", m.get("high", {}).get("overall", m))
            out[s] = {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in o.items() if kk in ("n_steps", "step_sr", "type_match")}
            if s in ("odyssey", "amex", "complete"):
                out[s]["per_type"] = {t: (x["n"], round(x["step_sr"], 3)) for t, x in o.get("per_type", {}).items()}
    print(v, json.dumps(out))
