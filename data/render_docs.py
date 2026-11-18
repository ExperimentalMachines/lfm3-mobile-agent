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
mwt = f"Snapshot {mw.get('snapshot_time', '?')}; suite: {mw.get('suite', '')}.\n\n| model | host | agent | finished | successes |\n|---|---|---|---|---|\n"
for k, v in (mw.get("runs") or {}).items():
    mwt += f"| {k} | {v['host']} | {v['agent']} | {v['finished']}/105 | {v['successes']} |\n"
mwt += "\nPer-task scores and step counts are in `results/snapshot.json`. Runs are still in progress; partial success rates are not comparable until both finish (task order differs).\n"
sp = reg.get("speed_cpu_t8") or []
spt = "| model | calls | median s/step (min–max) | prompt tokens | prompt s | prompt tok/s | output tokens | output s | output tok/s |\n|---|---|---|---|---|---|---|---|---|\n"
for o in sp:
    spt += (f"| {o['model']} | {o['n']} | **{o['latency_median_s']}** ({o['latency_min_max_s'][0]}–{o['latency_min_max_s'][1]}) | {o['prompt_tokens_median']} | "
            f"{o['prompt_s_median']} | {o['prompt_tok_per_s']} | {o['gen_tokens_median']} | {o['gen_s_median']} | {o['gen_tok_per_s']} |\n")
sizes = ", ".join(f"{k} {v} GB" for k, v in reg["gguf_sizes_gb"].items())
sub = {"generated_from": reg["generated_from"], "now": time.strftime("%Y-%m-%d %H:%M"), "headline": head, "rl_details": rl_details,
       "gate": gate, "mobileworld": mwt, "speed_table": spt, "sizes": sizes}
for k in ["training", "ac", "gen", "dev", "aw", "pairs", "sealed"]:
    sub[f"table_{k}"] = T(k)
for f in os.listdir(os.path.join(R, "templates")):
    s = open(os.path.join(R, "templates", f)).read()
    for k, v in sub.items():
        s = s.replace("{{" + k + "}}", v)
    assert "{{" not in s, (f, s[s.index("{{"):s.index("{{") + 40])
    open(os.path.join(R, f), "w").write(s)
print("rendered", sorted(os.listdir(os.path.join(R, "templates"))))
