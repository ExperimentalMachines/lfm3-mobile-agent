"""Summarise E's MobileWorld run (docs/PREREG_v46.md 2026-11-25 20:40; descriptive, not gated) from
results/mobileworld/traj_e/ (pulled by scripts/mobileworld/mw_pull_e.sh). Same outcome rule as runs 2 and 3
(analysis/mw_summarize_r2.py: score = the final folder's result.txt; a task without one counts as a failure) and the same
loop metrics as run 3 (analysis/mw_summarize_r3.py: wait share, wait under a non-wait intent, repeated intents, tasks at
the 50-step limit). Compared, paired with exact two-sided McNemar, with v4 (6/105), GUI-Owl (22/105) and MAI-UI (11/105)
from run 2 and v4.2 (8/105) from run 3.
Writes results/mobileworld/e_gui_en_r4_summary.json and results/mobileworld/mw_e_comparison.{json,md}.
Usage: python analysis/mw_summarize_e.py
"""
import os
import sys

sys.argv = [sys.argv[0], "e"]
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mw_summarize_r3.py")).read()
exec(_src.split('root = os.path.join(R3, f"{RUN}_gui_en_r3")')[0])  # run-2 rule + run-3 helpers (intent, atype, loops)
NAMES = {"e": "LFM3-VL-2B-MobileAgent-v4.6-E (24-step history, change notes; no guards, MobileWorld-native typing)"}
RE_ = "results/mobileworld/traj_e"
root = os.path.join(RE_, "e_gui_en_r4")
tasks = {}
for t in TASKS:
    d = os.path.join(root, t)
    kind, val = classify(d) if os.path.isdir(d) else ("error", "never_started")
    backups = sorted(glob.glob(d + "_backup_*"))
    tasks[t] = {"score": val if kind == "result" else 0.0, "has_result": kind == "result",
                "final_category": None if kind == "result" else val, "steps": len(traj_steps(d)),
                "earlier_folders": [classify(b)[1] for b in backups]}
succ = {t for t, v in tasks.items() if v["score"] > 0}
summ = {"model": NAMES["e"], "run": "e", "complete": os.path.exists(os.path.join(RE_, "e_complete")),
        "n_tasks": len(TASKS), "with_result": sum(v["has_result"] for v in tasks.values()), "successes": len(succ),
        "no_result_counted_as_failure": {t: v["final_category"] for t, v in tasks.items() if not v["has_result"]},
        "loop_metrics": loops(root), "tasks": tasks}
json.dump(summ, open("results/mobileworld/e_gui_en_r4_summary.json", "w"), indent=1)

base = {}
for k, f in (("v4", "v4_gui_en_r2_summary.json"), ("v42", "v42_gui_en_r3_summary.json"),
             ("guiowl", "guiowl_gui_en_r2_summary.json"), ("maiui", "maiui_gui_en_r2_summary.json")):
    s = json.load(open(f"results/mobileworld/{f}"))
    base[k] = {t for t, v in s["tasks"].items() if v["score"] and v["score"] > 0}
assert (len(base["v4"]), len(base["v42"]), len(base["guiowl"]), len(base["maiui"])) == (6, 8, 22, 11), {k: len(v) for k, v in base.items()}
label = {"v4": "v4 (run 2)", "v42": "v4.2 (run 3)", "guiowl": "GUI-Owl-1.5-2B (run 2)", "maiui": "MAI-UI-2B (run 2)"}
cmp_ = {"run": "e", "successes": len(succ), "complete": summ["complete"], "pairs": {}}
for k, B in base.items():
    b, c = len(succ - B), len(B - succ)
    cmp_["pairs"][k] = {"baseline_successes": len(B), "both": len(succ & B), "e_only": sorted(succ - B),
                        f"{k}_only": sorted(B - succ), "difference_pp": round(100 * (b - c) / len(TASKS), 1),
                        "mcnemar_exact_p": round(mcnemar_exact(b, c), 4)}
cmp_["loop_metrics"] = {"e": summ["loop_metrics"], "v4": loops(os.path.join(R, "v4_gui_en_r2")),
                        "v42": loops(os.path.join(R3, "v42_gui_en_r3"))}
json.dump(cmp_, open("results/mobileworld/mw_e_comparison.json", "w"), indent=1)

L = [f"# MobileWorld: {NAMES['e']} (105 English GUI-only tasks)", "",
     "Owner decision, descriptive ([PREREG_v46.md](../../docs/PREREG_v46.md), 2026-11-25 20:40). E was developed on "
     "AndroidWorld seed 30 only; MobileWorld's trajectories were read for earlier rounds, so this is not a sealed test.", "",
     "| Model | Successes / 105 | Both | E only | Baseline only | Difference | Exact McNemar p |", "|---|---|---|---|---|---|---|"]
for k, p in cmp_["pairs"].items():
    L.append(f"| {label[k]} | {p['baseline_successes']} | {p['both']} | {len(p['e_only'])} | {len(p[k + '_only'])} | "
             f"{p['difference_pp']:+.1f} pp | {p['mcnemar_exact_p']} |")
L += ["", f"**E: {len(succ)}/105**; tasks with a result {summ['with_result']}; no result (failure): "
      + (", ".join(f"{t} ({c})" for t, c in summ["no_result_counted_as_failure"].items()) or "none") + ".", "",
      f"- E solved: {', '.join(sorted(succ)) or 'none'}",
      f"- Gained vs v4: {', '.join(cmp_['pairs']['v4']['e_only']) or 'none'}; lost vs v4: "
      f"{', '.join(cmp_['pairs']['v4']['v4_only']) or 'none'}", "",
      "| Loop metric | v4 (run 2) | v4.2 (run 3) | E |", "|---|---|---|---|"]
a, m, b = cmp_["loop_metrics"]["v4"], cmp_["loop_metrics"]["v42"], cmp_["loop_metrics"]["e"]
for key, nm in (("steps", "Steps"), ("wait_share", "Share of steps that are `wait`"),
                ("wait_under_non_wait_intent", "`wait` under a non-wait intent"),
                ("repeated_intent_share", "Steps repeating the previous intent"), ("tasks_at_50_steps", "Tasks ending at the 50-step limit")):
    L.append(f"| {nm} | {a[key]} | {m[key]} | {b[key]} |")
L += ["", "Single run per model at temperature 0. v4 ran with synthetic Enters after typing; v4.2 and E use "
      "MobileWorld-native typing, so step counts are not strictly comparable with v4's. E's environment is AWS "
      "c8i.4xlarge with the run-2 image pinned by digest (run 2: GCP)."]
open("results/mobileworld/mw_e_comparison.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
