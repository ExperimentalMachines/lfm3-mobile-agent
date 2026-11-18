"""Summarise MobileWorld run 2 (GUI-Owl-1.5-2B vs v4, 105 English GUI-only tasks) from results/mobileworld/traj_r2/
(pulled by scripts/mw_pull_r2.sh). Every attempt folder is classified with the same rule as mw_resume.sh (text after the
runner's last "Error executing task"): MobileWorld's own in-run retries (--auto_retry 3, *_backup_* folders), folders
moved aside by mw_resume.sh (_interrupted/<run>/), and the final folder. Score = the final folder's result.txt; a task
without one counts as a failure (docs/PREREG_v4.md, 2026-11-19 01:55).
Writes results/mobileworld/{guiowl,v4}_gui_en_r2_summary.json and results/mobileworld/mw_r2_comparison.{json,md}.
Usage: python scripts/mw_summarize_r2.py
"""
import glob
import json
import math
import os
import re

R = "results/mobileworld/traj_r2"
TASKS = json.load(open("results/mobileworld/mw_gui_en.json"))
RUNS = {"guiowl": ("guiowl_gui_en_r2", "GUI-Owl-1.5-2B", "MobileWorld official gui_owl_1_5 agent, Q4_K_M, Colab T4 llama.cpp server, --cache-ram 0",
                   "mobile_world_env_0", "go_r2"),
        "v4": ("v4_gui_en_r2", "LFM3-VL-2B-AndroidAgent-v4", "LFM3 adapter (fixed), v4 prompt, Q4_K_M, Colab T4 llama.cpp server",
               "lfmenv_0", "v4_r2")}
ENV = ("setup_failed", "scoring_failed")
MODEL = ("unsupported_action", "invalid_model_output", "ask_user_without_simulator", "other_error")


def classify(d):
    """Outcome of one attempt folder: ('result', score) or ('error', category)."""
    f = os.path.join(d, "result.txt")
    if os.path.isfile(f):
        m = re.search(r"score:\s*([0-9.]+)", open(f).read())
        return "result", float(m.group(1)) if m else 0.0
    txt = "".join(open(x, errors="ignore").read() for x in sorted(glob.glob(d + "/*.log")))
    if "Error executing task" not in txt:
        return "error", "interrupted"
    seg = txt[txt.rindex("Error executing task"):]
    for key, cat in (("Failed to initialize task", "setup_failed"), ("Failed to get task score", "scoring_failed"),
                     ("Unknown action_type", "unsupported_action")):
        if key in seg:
            return "error", cat
    if "error_env" in seg or "Failed to parse tool_call" in seg:
        return "error", "invalid_model_output"
    if "Step action failed" in seg and "API key" in seg:
        return "error", "ask_user_without_simulator"
    return "error", "other_error"


def stamp(name):
    p = os.path.join(R, name)
    return int(open(p).read().split()[0]) if os.path.exists(p) else None


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, p)


summ = {}
for key, (root, model, agent, ctr, st) in RUNS.items():
    base = os.path.join(R, root)
    tasks = {}
    for t in TASKS:
        atts = []
        for d in sorted(glob.glob(os.path.join(base, t + "_backup_*"))):
            atts.append(("mobileworld_auto_retry", os.path.basename(d), *classify(d)))
        for d in sorted(glob.glob(os.path.join(R, "_interrupted", key, t + "_2*"))):
            atts.append(("moved_by_mw_resume", os.path.basename(d), *classify(d)))
        fin = os.path.join(base, t)
        final = classify(fin) if os.path.isdir(fin) else ("error", "never_started")
        atts.append(("final", t, *final))
        tasks[t] = {"score": final[1] if final[0] == "result" else 0.0, "has_result": final[0] == "result",
                    "final_category": None if final[0] == "result" else final[1],
                    "attempts": [{"kind": a, "folder": f, "outcome": o if o == "error" else "result",
                                  "detail": v} for a, f, o, v in atts]}
    succ = [t for t, x in tasks.items() if x["score"] >= 1]
    earlier = [a for x in tasks.values() for a in x["attempts"][:-1]]
    env_errors = sum(a["detail"] in ENV for x in tasks.values() for a in x["attempts"] if a["outcome"] == "error")
    env_tasks = sorted(t for t, x in tasks.items() if any(a["detail"] in ENV for a in x["attempts"] if a["outcome"] == "error"))
    s0, s1 = stamp(st + ".start"), stamp(st + ".end")
    out = {"model": model, "agent": agent, "container": ctr,
           "suite": "MobileWorld a026188, 105 English GUI-only tasks (results/mobileworld/mw_gui_en.json)",
           "settings": "max_round 50, step_wait 3 s, auto_retry 3 (MobileWorld built-in), 1 screenshot; completion rule docs/PREREG_v4.md 2026-11-19 01:55",
           "host": "GCP n2-standard-16 (env containers) + Colab T4 (model server, reverse SSH tunnel)",
           "elapsed_s_original_list": (s1 - s0) if s0 and s1 else None,
           "complete": os.path.exists(os.path.join(R, key + "_complete")),
           "n_tasks": len(TASKS), "with_result": sum(x["has_result"] for x in tasks.values()),
           "successes": len(succ), "success_rate": round(len(succ) / len(TASKS), 4),
           "no_result_counted_as_failure": {t: x["final_category"] for t, x in tasks.items() if not x["has_result"]},
           "tasks_with_more_than_one_attempt": sum(len(x["attempts"]) > 1 for x in tasks.values()),
           "earlier_attempt_outcomes": {c: sum(a["detail"] == c for a in earlier)
                                        for c in sorted({a["detail"] for a in earlier if a["outcome"] == "error"})},
           "environment_errors_all_attempts": env_errors, "tasks_with_an_environment_error": env_tasks,
           "successes_after_an_earlier_failed_attempt": {t: [a["detail"] for a in x["attempts"][:-1]]
                                                         for t, x in tasks.items() if x["score"] >= 1 and len(x["attempts"]) > 1},
           "tasks": tasks}
    json.dump(out, open(f"results/mobileworld/{root}_summary.json", "w"), indent=1)
    summ[key] = out

g, v = summ["guiowl"]["tasks"], summ["v4"]["tasks"]
both = sum(g[t]["score"] >= 1 and v[t]["score"] >= 1 for t in TASKS)
v_only = sorted(t for t in TASKS if v[t]["score"] >= 1 and g[t]["score"] < 1)
g_only = sorted(t for t in TASKS if g[t]["score"] >= 1 and v[t]["score"] < 1)
envhit = sorted(t for t in TASKS if any(a["detail"] in ENV for a in g[t]["attempts"] + v[t]["attempts"] if a["outcome"] == "error"))
clean = [t for t in TASKS if t not in envhit]
sens = {"n_tasks": len(clean), "v4": sum(v[t]["score"] >= 1 for t in clean), "guiowl": sum(g[t]["score"] >= 1 for t in clean)}
cmp_ = {"n_tasks": len(TASKS), "v4_successes": summ["v4"]["successes"], "guiowl_successes": summ["guiowl"]["successes"],
        "difference_pp": round(100 * (summ["v4"]["successes"] - summ["guiowl"]["successes"]) / len(TASKS), 1),
        "both": both, "v4_only": v_only, "guiowl_only": g_only,
        "neither": len(TASKS) - both - len(v_only) - len(g_only),
        "mcnemar_exact_p": float(f"{mcnemar_exact(len(v_only), len(g_only)):.3g}"),
        "tasks_with_an_environment_error_in_either_run": envhit,
        "sensitivity_excluding_those_tasks": sens,
        "note": "Secondary, descriptive benchmark (not preregistered as a primary endpoint); single run per model, temperature 0."}
json.dump(cmp_, open("results/mobileworld/mw_r2_comparison.json", "w"), indent=1)


def fmt_cats(d):
    return ", ".join(f"{k} {n}" for k, n in sorted(d.items(), key=lambda kv: -kv[1])) or "none"


L = ["# MobileWorld run 2: v4 vs GUI-Owl-1.5-2B (105 English GUI-only tasks)", "",
     "| Model | Successes / 105 | Tasks with a result | No result (counted as failure) | Setup/scoring errors over all attempts (tasks) | Tasks attempted more than once |",
     "|---|---|---|---|---|---|"]
for key in ("v4", "guiowl"):
    s = summ[key]
    nr = s["no_result_counted_as_failure"]
    L.append(f"| {s['model']} | **{s['successes']}** ({100 * s['success_rate']:.1f}%) | {s['with_result']} | "
             f"{len(nr)}: {', '.join(f'{t} ({c})' for t, c in nr.items()) or '-'} | {s['environment_errors_all_attempts']} ({len(s['tasks_with_an_environment_error'])}) | "
             f"{s['tasks_with_more_than_one_attempt']} |")
L += ["", f"Paired on the same 105 tasks: both solved {both}, v4 only {len(v_only)}, GUI-Owl only {len(g_only)}, neither {cmp_['neither']}; "
      f"difference {cmp_['difference_pp']:+.1f} pp, exact McNemar p = {cmp_['mcnemar_exact_p']}.", "",
      f"Sensitivity: excluding the {len(envhit)} tasks that hit a setup or scoring error in either run, v4 {sens['v4']} vs GUI-Owl "
      f"{sens['guiowl']} of {sens['n_tasks']}.", "",
      "Earlier (replaced) attempts, by how they ended:", ""]
for key in ("v4", "guiowl"):
    s = summ[key]
    L.append(f"* {s['model']}: {fmt_cats(s['earlier_attempt_outcomes'])}; successes that came after an earlier failed attempt: "
             + (", ".join(f"{t} (after {', '.join(c)})" for t, c in s["successes_after_an_earlier_failed_attempt"].items()) or "none") + ".")
L += ["", "MobileWorld's own `--auto_retry 3` (same flag for both runs) re-runs a task whose attempt ended without a result, "
      "whatever the reason, including the model's own crashes; mw_resume.sh then applied the pre-declared completion rule "
      "(docs/PREREG_v4.md, 2026-11-19 01:55). Single run per model at temperature 0; a secondary, descriptive benchmark."]
open("results/mobileworld/mw_r2_comparison.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
