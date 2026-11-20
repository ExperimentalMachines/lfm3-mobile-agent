"""Summarise the device-streaming speed benchmark (one Pixel 9, Android 16; pass 1 = v4, guiowl, maiui x3 timed passes;
pass 2 = maiui, guiowl, v4 x1). Source of truth = the recording proxy logs (requests_<model>.jsonl: phone-side llama.cpp
timings per request); the first request of each model in each pass is the mirrored warm-up and is excluded.
Usage: python analysis/devstream_report.py results/devstream/run_YYYYMMDD_HHMM [--md out.md] [--json out.json]"""
import glob
import json
import os
import statistics as st
import sys

run = sys.argv[1]
md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
js = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
LAB = {"v4": "v4 (ours)", "guiowl": "GUI-Owl-1.5-2B", "maiui": "MAI-UI-2B"}
FILES = {"v4": 1.30, "guiowl": 1.55, "maiui": 1.55}


def rows(path):
    out = [json.loads(l) for l in open(path)] if os.path.exists(path) else []
    out = [r for r in out if r.get("status") == 200 and "timings" in (r.get("response") or {})]
    return out[1:]  # drop the warm-up (mirrored screenshot)


def thermal(passdir, t0, t1):
    pts = [json.loads(l) for l in open(os.path.join(passdir, "thermal.jsonl"))] if os.path.exists(os.path.join(passdir, "thermal.jsonl")) else []
    pts = [p for p in pts if t0 <= p["t"] <= t1]
    temps = [int(p["battery_temp_dC"]) / 10 for p in pts if p.get("battery_temp_dC", "").isdigit()]
    stat = [p["thermal"].split(":")[-1].strip() for p in pts if p.get("thermal")]
    return {"battery_c_median": round(st.median(temps), 1) if temps else None, "battery_c_max": max(temps) if temps else None,
            "thermal_status_max": max(stat) if stat else None}


summary = {"run": run, "device": json.load(open(os.path.join(run, "dev0", "device.json"))) if os.path.exists(os.path.join(run, "dev0", "device.json")) else None,
           "models": {}}
for m in ("v4", "guiowl", "maiui"):
    per = {}
    allr = []
    for pname, d in (("pass1", "dev0"), ("pass2", "dev0_pass2")):
        rr = rows(os.path.join(run, d, f"requests_{m}.jsonl"))
        if not rr:
            continue
        allr += rr
        T = [r["response"]["timings"] for r in rr]
        per[pname] = {"n": len(rr), "latency_median_s": round(st.median(r["latency_s"] for r in rr), 2),
                      "prompt_s_median": round(st.median(t["prompt_ms"] for t in T) / 1000, 2),
                      **thermal(os.path.join(run, d), rr[0]["t_start"], rr[-1]["t_end"])}
    if not allr:
        continue
    T = [r["response"]["timings"] for r in allr]
    lat = [r["latency_s"] for r in allr]
    summary["models"][m] = {
        "label": LAB[m], "n": len(allr), "latency_median_s": round(st.median(lat), 1),
        "latency_min_max_s": [round(min(lat), 1), round(max(lat), 1)],
        "prompt_tokens_median": int(st.median(t["prompt_n"] + t.get("cache_n", 0) for t in T)),
        "prompt_processed_median": int(st.median(t["prompt_n"] for t in T)),
        "prompt_s_median": round(st.median(t["prompt_ms"] for t in T) / 1000, 1),
        "prompt_tok_per_s": round(sum(t["prompt_n"] for t in T) / (sum(t["prompt_ms"] for t in T) / 1000), 1),
        "gen_tokens_median": int(st.median(t["predicted_n"] for t in T)),
        "gen_tok_per_s": round(sum(t["predicted_n"] for t in T) / (sum(t["predicted_ms"] for t in T) / 1000), 1),
        "files_gb": FILES[m], "passes": per}
print(json.dumps(summary["models"], indent=1))
if js:
    json.dump(summary, open(js, "w"), indent=1)
if md:
    with open(md, "w") as f:
        f.write("| Model | Seconds per step (median) | Prompt tokens | Prompt time | Prompt tokens/s | Output tokens | Output tokens/s | Model files |\n"
                "|---|---|---|---|---|---|---|---|\n")
        for m, o in summary["models"].items():
            b = "**" if m == "v4" else ""
            f.write(f"| {b}{o['label']}{b} | {b}{o['latency_median_s']}{b} ({o['latency_min_max_s'][0]}–{o['latency_min_max_s'][1]}) | "
                    f"{o['prompt_tokens_median']:,} | {o['prompt_s_median']} s | {o['prompt_tok_per_s']:.0f} | {o['gen_tokens_median']} | "
                    f"{o['gen_tok_per_s']:.0f} | {o['files_gb']:.2f} GB |\n")
        f.write("\nPer pass (pass 1 = v4 → GUI-Owl → MAI-UI, 3 timed passes; pass 2 = MAI-UI → GUI-Owl → v4, 1 timed pass):\n\n"
                "| Model | Pass | Calls | Seconds per step (median) | Prompt time (median) | Battery °C (median / max) | Max thermal status |\n|---|---|---|---|---|---|---|\n")
        for m, o in summary["models"].items():
            for pname, p in o["passes"].items():
                f.write(f"| {o['label']} | {pname} | {p['n']} | {p['latency_median_s']} | {p['prompt_s_median']} s | "
                        f"{p['battery_c_median']} / {p['battery_c_max']} | {p['thermal_status_max']} |\n")
