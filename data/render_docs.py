"""Fill templates/*.md with tables from data/runs.json and data/table_*.md -> top-level docs. Run after build_runs_registry.py."""
import json, os, time
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
reg = json.load(open(os.path.join(R, "data", "runs.json")))
T = lambda k: open(os.path.join(R, "data", f"table_{k}.md")).read()
aw = {r["id"]: r for r in reg["androidworld_seed30"]}
head = "| model | successes /116 | answer tasks /25 | action tasks /91 | median s/step (M5) |\n|---|---|---|---|---|\n"
for k in ["lfm3vl2b_v4", "guiowl15_2b_matched", "qwen35_2b_ft", "lfm3vl2b_ft", "lfm3vl2b_v3", "lfm3vl2b_v2", "qwen35_08b_ft", "lfm25vl450m_ft"]:
    if k in aw:
        r = aw[k]; b = "**" if k == "lfm3vl2b_v4" else ""
        head += f"| {b}{r['label']}{b} | {b}{r['successes']}{b} | {r['answer_task_successes']} | {r['action_task_successes']} | {r['median_step_latency_s']} |\n"
tr = {r["id"]: r for r in reg["training"]}
rl = tr.get("lfm3vl2b-v4rl", {})
rl_details = (f"* data: {rl.get('train_data')}\n* steps: {rl.get('steps')}, wall {rl.get('wall_h')} h on a Colab A100, peak GPU {rl.get('peak_gpu_gb')} GB\n"
              f"* mean reward first 20 steps {rl.get('reward_first20')} → last 20 steps {rl.get('reward_last20')}\n* {rl.get('notes')}\n")
g = reg.get("v4rl_promotion_offline") or {}
gate_txt = open(os.path.join(R, "results", "v4_gate_seed30.txt")).read()
gate = ("v4 gate (from `results/v4_gate_seed30.txt`):\n\n```json\n" + gate_txt.strip() + "\n```\n\n"
        "v4-RL offline promotion (from `results/v4rl_promotion_offline.json`): criteria "
        + ", ".join(f"`{k}` = {v}" for k, v in (g.get("criteria") or {}).items()) + " → **not promoted**.\n")
mw = reg.get("mobileworld_snapshot") or {}
mwt = f"Status {mw.get('snapshot_time', '?')}; suite: {mw.get('suite', '')}.\n\n| run | host | agent | finished | successes | status |\n|---|---|---|---|---|---|\n"
for k, v in (mw.get("runs") or {}).items():
    fin = f"{v['finished']}/105" if v.get("finished") is not None else "–"
    suc = v["successes"] if v.get("successes") is not None else "–"
    mwt += f"| {k} | {v['host']} | {v['agent']} | {fin} | {suc} | {v.get('status', '')} |\n"
ps = mw.get("paired_so_far")
if ps:
    mwt += f"\nPaired so far (tasks both valid runs have finished): {ps['tasks_finished_by_both']} tasks, v4 {ps['v4_successes']} vs GUI-Owl {ps['guiowl_successes']} successes.\n"
mwt += "\nOnly complete, valid runs are comparable. Per-task results of finished runs are in the working repo (`results/mobileworld/`).\n"
sizes_d = reg["gguf_sizes_gb"]
sp = reg.get("speed_cpu_t8") or []
lab = {"LFM3 v4 (ours)": "**v4 (ours)**", "GUI-Owl-1.5-2B": "GUI-Owl-1.5-2B", "MAI-UI-2B": "MAI-UI-2B"}
fsz = {"LFM3 v4 (ours)": sizes_d.get("LFM3 v4"), "GUI-Owl-1.5-2B": sizes_d.get("GUI-Owl-1.5-2B"), "MAI-UI-2B": sizes_d.get("MAI-UI-2B")}
cpu = ("| Model | Seconds per step (median) | Prompt tokens | Prompt time | Prompt tokens/s | Output tokens | Output tokens/s | Model files |\n"
       "|---|---|---|---|---|---|---|---|\n")
for o in sp:
    b = "**" if "v4" in o["model"] else ""
    cpu += (f"| {lab.get(o['model'], o['model'])} | {b}{o['latency_median_s']:.1f}{b} ({o['latency_min_max_s'][0]:.1f}–{o['latency_min_max_s'][1]:.1f}) | "
            f"{o['prompt_tokens_median']:,} | {o['prompt_s_median']:.1f} s | {o['prompt_tok_per_s']:.0f} | {o['gen_tokens_median']} | "
            f"{o['gen_tok_per_s']:.0f} | {fsz.get(o['model'], 0):.2f} GB |\n")
m5 = "| Model | Quantization | Steps | Seconds per step, median (10th–90th percentile) | Prompt tokens | Output tokens |\n|---|---|---|---|---|---|\n"
for o in reg.get("speed_m5_in_run") or []:
    b = "**" if "v4" in o["model"] else ""
    part = f" (run in progress: {o['episodes']} of 116 episodes)" if o["episodes"] < 116 else ""
    m5 += (f"| {b}{o['model']}{b}{part} | {o['quant']} | {o['steps']:,} | {b}{o['median_s']:.2f}{b} ({o['p10_s']:.1f}–{o['p90_s']:.1f}) | "
           f"{o['prompt_tokens_median']:,} | {o['output_tokens_median']} |\n")
spt = "| model | calls | median s/step (min–max) | prompt tokens | prompt s | prompt tok/s | output tokens | output s | output tok/s |\n|---|---|---|---|---|---|---|---|---|\n"
for o in sp:
    spt += (f"| {o['model']} | {o['n']} | **{o['latency_median_s']}** ({o['latency_min_max_s'][0]}–{o['latency_min_max_s'][1]}) | {o['prompt_tokens_median']} | "
            f"{o['prompt_s_median']} | {o['prompt_tok_per_s']} | {o['gen_tokens_median']} | {o['gen_s_median']} | {o['gen_tok_per_s']} |\n")
sizes = ", ".join(f"{k} {v} GB" for k, v in reg["gguf_sizes_gb"].items())
def phone_section(ph, title_note):
    if not ph or not ph.get("models"):
        return None
    dv = ph.get("device") or {}
    t = (f"Device: {dv.get('ro.product.model', '?')} ({dv.get('ro.soc.model', '?')}), Android SDK {dv.get('ro.build.version.sdk', '?')}, "
         f"{dv.get('mem', '').replace('MemTotal:', '').strip()} RAM, CPU max kHz {dv.get('cpus', '').strip()}. {title_note}\n\n")
    t += ("| Model | Seconds per step (median, end-to-end) | Prompt tokens | Prompt time (phone) | Prompt tokens/s | Output tokens | Output tokens/s | Model files |\n"
          "|---|---|---|---|---|---|---|---|\n")
    for m, o in ph["models"].items():
        b = "**" if m == "v4" else ""
        t += (f"| {b}{o['label']}{b} | {b}{o['latency_median_s']}{b} ({o['latency_min_max_s'][0]}–{o['latency_min_max_s'][1]}) | "
              f"{o['prompt_tokens_median']:,} | {o['prompt_s_median']} s | {o['prompt_tok_per_s']:.0f} | {o['gen_tokens_median']} | "
              f"{o['gen_tok_per_s']:.0f} | {o['files_gb']:.2f} GB |\n")
    t += "\n| Model | Pass | Calls | Seconds per step (median) | Prompt time (median) | Battery °C (median / max) | Max thermal status |\n|---|---|---|---|---|---|---|\n"
    for m, o in ph["models"].items():
        for pn, pp in o["passes"].items():
            t += f"| {o['label']} | {pn} | {pp['n']} | {pp['latency_median_s']} | {pp['prompt_s_median']} s | {pp['battery_c_median']} / {pp['battery_c_max']} | {pp['thermal_status_max']} |\n"
    return t


phs = reg.get("speed_phones") or {}
qdc = phone_section(phs.get("qdc_sm8975"), "Pass 1 = v4 → GUI-Owl → MAI-UI, pass 2 reversed, 3 timed passes each.")
fb = phs.get("firebase_pixel9_partial") or {}
fbv4 = (fb.get("models") or {}).get("v4")
qdc_txt = (phs.get("qdc_v6_md") or qdc or "_Run in progress._\n") + (
    f"\nEarlier attempt on a Pixel 9 (Tensor G4, Android 16) through Firebase Android Device Streaming, stopped after v4 when we "
    f"switched to Qualcomm Device Cloud: v4 median {fbv4['latency_median_s']} s/step over {fbv4['n']} calls, rising from "
    f"{fbv4['latency_min_max_s'][0]} to {fbv4['latency_min_max_s'][1]} s (not monotonically; the last call took 66.7 s). From the 5th request "
    f"(4th timed call) the sampled frequencies of the three performance cores (CPU 4–6, max 2.6 GHz) fell to ~1.8 GHz and the prime core "
    f"(CPU 7, max 3.1 GHz) slowed and varied (down to 1.4 GHz and lower), while the battery warmed from 27 to ~36 °C and prompt speed fell from "
    f"~26 to ~15 tok/s; Android's thermal status still read 0. These are sampled current frequencies, not recorded caps "
    f"(raw data and thermal log in the working repo, `results/devstream/`).\n" if fbv4 else "")
s7 = reg.get("seed7_analysis_md")
seed7_txt = (f"Status: **{reg.get('seed7_status')}**.\n\n" + s7.split("\n", 1)[1]) if s7 else "_Seed 7 not yet unsealed._\n"
latest = []
if s7:
    import re as _re
    m = _re.search(r"\| v4_minus_guiowl \(PRIMARY\) \| ([-0-9.]+) \| \[([-0-9.]+), ([-0-9.]+)\] \| ([0-9.]+)", s7)
    rows = {a: _re.search(rf"\| {_re.escape(lbl)} \(seed 7\) \| (\d+)/116", s7) for a, lbl in
            (("v4", "LFM3 v4 (final)"), ("guiowl", "GUI-Owl-1.5-2B matched"), ("v1", "LFM3 v1 (reference)"))}
    if m and all(rows.values()):
        latest.append(f"* **Held-out AndroidWorld seed 7** ({reg.get('seed7_status')}): v4 **{rows['v4'].group(1)}/116**, GUI-Owl matched "
                      f"{rows['guiowl'].group(1)}/116, v1 {rows['v1'].group(1)}/116; v4 − GUI-Owl = {m.group(1)} points (95% CI {m.group(2)} to "
                      f"{m.group(3)}, p = {m.group(4)}). One seed: preliminary by the preregistration; seeds 1234 and 2026 are still sealed "
                      "([details](EVALUATIONS.md#held-out-seed-7-unsealed-after-all-three-arms-finished)).")
q = phs.get("qdc_v6_md") or ""
hm = __import__("re").search(r"\*\*Headline \(([^)]*)\):\*\* (.*)", q)
if hm:
    latest.append("* **On a real phone** (Snapdragon 8 Elite Extreme Gen 6, CPU, Qualcomm Device Cloud; " + hm.group(1) + "): "
                  + hm.group(2) + " ([SPEED](SPEED.md)).")
latest.append("* **Speed on CPU** (8 threads): one step takes **6.4 s for v4 vs ~58 s for GUI-Owl-1.5-2B and MAI-UI-2B**; Apple M5 GPU "
              "in real AndroidWorld runs: see [SPEED](SPEED.md).")
ps = mw.get("paired_so_far") or {}
runs2 = {k: v for k, v in (mw.get("runs") or {}).items() if "run 2" in k}
if runs2:
    latest.append("* **MobileWorld** (105 English GUI-only tasks; " + "; ".join(f"{k.split(' (')[0]}: {v['successes']}/{v['finished']} finished tasks solved, {v.get('status')}" for k, v in runs2.items())
                  + (f"; on the {ps['tasks_finished_by_both']} tasks both have finished: v4 {ps['v4_successes']} vs GUI-Owl {ps['guiowl_successes']}" if ps else "")
                  + "). v4's first MobileWorld run (5/105) is not counted: its adapter changed v4's scroll and Enter behaviour "
                  "([status](EVALUATIONS.md)).")
sub = {"generated_from": reg["generated_from"], "now": time.strftime("%Y-%m-%d %H:%M"), "headline": head, "rl_details": rl_details,
       "gate": gate, "mobileworld": mwt, "speed_table": spt, "sizes": sizes, "speed_cpu": cpu, "speed_m5": m5, "speed_qdc": qdc_txt, "sealed_seed7": seed7_txt, "latest": "\n".join(latest)}
for k in ["training", "ac", "gen", "dev", "aw", "pairs", "sealed"]:
    sub[f"table_{k}"] = T(k)
for f in os.listdir(os.path.join(R, "templates")):
    s = open(os.path.join(R, "templates", f)).read()
    for k, v in sub.items():
        s = s.replace("{{" + k + "}}", v)
    assert "{{" not in s, (f, s[s.index("{{"):s.index("{{") + 40])
    open(os.path.join(R, f), "w").write(s)
print("rendered", sorted(os.listdir(os.path.join(R, "templates"))))
