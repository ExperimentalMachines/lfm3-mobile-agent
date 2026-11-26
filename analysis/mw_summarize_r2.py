"""Summarise MobileWorld run 2 (GUI-Owl-1.5-2B vs v4, plus MAI-UI-2B as a third arm; 105 English GUI-only tasks) from results/mobileworld/traj_r2/
(pulled by scripts/mobileworld/mw_pull_r2.sh). Every attempt folder is classified with the same rule as mw_resume.sh (text after the
runner's last "Error executing task"): MobileWorld's own in-run retries (--auto_retry 3, *_backup_* folders), folders
moved aside by mw_resume.sh (_interrupted/<run>/), and the final folder. Score = the final folder's result.txt; a task
without one counts as a failure (docs/preregistrations/heldout-main-vs-gui-owl.md, 2026-11-19 01:55).
MAI-UI ran as two halves (maiui_a / maiui_b, alternate split of the same 105 tasks; docs/preregistrations/heldout-main-vs-gui-owl.md 2026-11-19 05:20)
whose folders share traj_logs/maiui_gui_en_r2; it is complete when both halves are.
Writes results/mobileworld/{guiowl,v4,maiui}_gui_en_r2_summary.json and results/mobileworld/mw_r2_comparison.{json,md}.
Usage: python analysis/mw_summarize_r2.py
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
               "lfmenv_0", "v4_r2"),
        "maiui": ("maiui_gui_en_r2", "MAI-UI-2B", "MobileWorld official mai_ui agent with history_n 1 (eval/mobileworld/maiui_mw_agent.py), "
                  "Q8_0, Colab T4 llama.cpp server", "mobile_world_env_0 (half a) + lfmenv_0 (half b)", None)}
MOVED = {"guiowl": ["guiowl"], "v4": ["v4"], "maiui": ["maiui_a", "maiui_b"]}       # _interrupted/<dir>/ per run
DONE = {"guiowl": ["guiowl"], "v4": ["v4"], "maiui": ["maiui_a", "maiui_b"]}        # <x>_complete markers per run
ENV = ("setup_failed", "scoring_failed")
MODEL = ("unsupported_action", "invalid_model_output", "ask_user_without_simulator", "other_error")
# model server (Colab tunnel) unreachable: the official agent's 3 LLM retries failed with a connection error; re-run like an
# interruption (scripts/mobileworld/gcp_mw_resume_vm.sh, docs/preregistrations/heldout-main-vs-gui-owl.md 2026-11-19 10:20). Infrastructure, not a model outcome.
SERVER_DOWN = ("Error calling OpenAI API: Connection error", "Error calling OpenAI API: Request timed out", "Connection refused",
               "Error calling OpenAI API: Error code: 502", "Error calling OpenAI API: Error code: 503",
               "Error calling OpenAI API: Error code: 504")


def classify(d):
    """Outcome of one attempt folder: ('result', score) or ('error', category)."""
    f = os.path.join(d, "result.txt")
    if os.path.isfile(f):
        m = re.search(r"score:\s*([0-9.]+)", open(f).read())
        return "result", float(m.group(1)) if m else 0.0
    # by modification time (rsync keeps it): repeated pulls can leave an older execution's log in a final folder (Codex
    # mw_maiui_audit P3), and filename order would then take the older execution's last error
    txt = "".join(open(x, errors="ignore").read() for x in sorted(glob.glob(d + "/*.log"), key=os.path.getmtime))
    if "Error executing task" not in txt:
        return "error", "interrupted"
    i = txt.rindex("Error executing task")
    seg, pre = txt[i:], txt[max(0, i - 6000):i]
    for key, cat in (("Failed to initialize task", "setup_failed"), ("Failed to get task score", "scoring_failed"),
                     ("Unknown action_type", "unsupported_action")):
        if key in seg:
            return "error", cat
    if "Planner LLM failed" in seg and any(x in pre for x in SERVER_DOWN):
        return "error", "model_server_unreachable"
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


def attempt_events(d):
    """Events inside one attempt folder that do not end it: MobileWorld's device-health re-initialisations (same folder,
    empty traj_backup_*.json), GUI-Owl's parse-failure sentinel being rejected by MW's action validator (MW bug), and
    ask_user calls hitting the missing user simulator."""
    txt = "".join(open(x, errors="ignore").read() for x in sorted(glob.glob(d + "/*.log")))
    return {"device_unhealthy_reinits": txt.count("Device is not healthy, retrying"),
            "env_fail_sentinel_rejected": int("error_env" in txt and "validation error" in txt),
            "ask_user_without_simulator": int("Step action failed" in txt and "API key" in txt)}


def traj_steps(d):
    f = os.path.join(d, "traj.json")
    if not os.path.isfile(f):
        return []
    j = json.load(open(f))
    return (j.get("0") or {}).get("traj", []) if isinstance(j, dict) else []


summ = {}
for key, (root, model, agent, ctr, st) in RUNS.items():
    base = os.path.join(R, root)
    tasks = {}
    for t in TASKS:
        atts = []
        for d in sorted(glob.glob(os.path.join(base, t + "_backup_*"))):
            atts.append(("mobileworld_auto_retry", d))
        for d in sorted(x for m in MOVED[key] for x in glob.glob(os.path.join(R, "_interrupted", m, t + "_2*"))):
            atts.append(("moved_by_mw_resume", d))
        fin = os.path.join(base, t)
        atts.append(("final", fin))
        rows = []
        for kind, d in atts:
            o, v = classify(d) if os.path.isdir(d) else ("error", "never_started")
            rows.append({"kind": kind, "folder": os.path.basename(d), "outcome": o, "detail": v, **attempt_events(d)})
        final = rows[-1]
        steps = traj_steps(fin)
        acts = [x.get("action", {}).get("action_type") for x in steps]
        tasks[t] = {"score": final["detail"] if final["outcome"] == "result" else 0.0, "has_result": final["outcome"] == "result",
                    "final_category": None if final["outcome"] == "result" else final["detail"], "steps": len(steps),
                    "synthetic_enters": sum(str(x.get("prediction", "")).startswith("(adapter) keyboard_enter") for x in steps),
                    "enter_dropped_at_step_budget": bool(steps) and len(steps) >= 50 and acts[-1] == "input_text",
                    "attempts": rows}
    X = tasks.values()
    succ = [t for t, x in tasks.items() if x["score"] >= 1]
    earlier = [a for x in X for a in x["attempts"][:-1]]
    env_tasks = sorted(t for t, x in tasks.items() if any(a["outcome"] == "error" and a["detail"] in ENV for a in x["attempts"]))
    reinit_tasks = sorted(t for t, x in tasks.items() if any(a["device_unhealthy_reinits"] for a in x["attempts"]))
    moved = {t for t in TASKS if any(glob.glob(os.path.join(R, "_interrupted", m, t + "_2*")) for m in MOVED[key])}
    pending = sorted(t for t, x in tasks.items() if not x["has_result"] and x["final_category"] in ENV + ("interrupted", "never_started")
                     and (x["final_category"] not in ENV or t not in moved))
    s0, s1 = (stamp(st + ".start"), stamp(st + ".end")) if st else (None, None)
    out = {"model": model, "agent": agent, "container": ctr,
           "suite": "MobileWorld a026188, 105 English GUI-only tasks (results/mobileworld/mw_gui_en.json)",
           "settings": "max_round 50, step_wait 3 s, auto_retry 3 (MobileWorld built-in), 1 screenshot; completion rule docs/preregistrations/heldout-main-vs-gui-owl.md 2026-11-19 01:55 / 05:20 / 05:45",
           "host": "GCP n2-standard-16 (env containers) + Colab T4 (model server, reverse SSH tunnel)",
           "model_server_unreachable_folders": sum(a["detail"] == "model_server_unreachable" for x in tasks.values() for a in x["attempts"]),
           "elapsed_s_original_list": (s1 - s0) if s0 and s1 else None,
           "complete": all(os.path.exists(os.path.join(R, m + "_complete")) for m in DONE[key]), "pending_eligible_tasks": pending,
           "n_tasks": len(TASKS), "with_result": sum(x["has_result"] for x in X),
           "successes": len(succ), "success_rate": len(succ) / len(TASKS),
           "no_result_counted_as_failure": {t: x["final_category"] for t, x in tasks.items() if not x["has_result"]},
           "task_executions": sum(len(x["attempts"]) + sum(a["device_unhealthy_reinits"] for a in x["attempts"]) for x in X),
           "tasks_with_more_than_one_folder": sum(len(x["attempts"]) > 1 for x in X),
           "device_unhealthy_reinits": sum(a["device_unhealthy_reinits"] for x in X for a in x["attempts"]),
           "tasks_with_device_unhealthy_reinit": reinit_tasks,
           "earlier_folder_outcomes": {c: sum(a["detail"] == c for a in earlier)
                                       for c in sorted({a["detail"] for a in earlier if a["outcome"] == "error"})},
           "folder_level_environment_errors": sum(a["outcome"] == "error" and a["detail"] in ENV for x in X for a in x["attempts"]),
           "tasks_with_folder_level_environment_error": env_tasks,
           "env_fail_sentinel_rejected_executions": sum(a["env_fail_sentinel_rejected"] for x in X for a in x["attempts"]),
           "ask_user_without_simulator_executions": sum(a["ask_user_without_simulator"] for x in X for a in x["attempts"]),
           "synthetic_enters": sum(x["synthetic_enters"] for x in X),
           "tasks_ending_at_step_budget": sum(x["steps"] >= 50 for x in X),
           "tasks_at_step_budget_with_synthetic_enters": sum(x["steps"] >= 50 and x["synthetic_enters"] > 0 for x in X),
           "enter_dropped_at_step_budget": sorted(t for t, x in tasks.items() if x["enter_dropped_at_step_budget"]),
           "successes_after_an_earlier_failed_folder": {t: [a["detail"] for a in x["attempts"][:-1]]
                                                        for t, x in tasks.items() if x["score"] >= 1 and len(x["attempts"]) > 1},
           "successes_after_a_device_reinit": sorted(t for t in succ if t in reinit_tasks),
           "tasks": tasks}
    json.dump(out, open(f"results/mobileworld/{root}_summary.json", "w"), indent=1)
    summ[key] = out

g, v = summ["guiowl"]["tasks"], summ["v4"]["tasks"]
both = sum(g[t]["score"] >= 1 and v[t]["score"] >= 1 for t in TASKS)
v_only = sorted(t for t in TASKS if v[t]["score"] >= 1 and g[t]["score"] < 1)
g_only = sorted(t for t in TASKS if g[t]["score"] >= 1 and v[t]["score"] < 1)
narrow = sorted(set(summ["v4"]["tasks_with_folder_level_environment_error"]) | set(summ["guiowl"]["tasks_with_folder_level_environment_error"]))
broad = sorted(set(narrow) | set(summ["v4"]["tasks_with_device_unhealthy_reinit"]) | set(summ["guiowl"]["tasks_with_device_unhealthy_reinit"]))


def sens(excl):
    keep = [t for t in TASKS if t not in excl]
    return {"n_tasks": len(keep), "v4": sum(v[t]["score"] >= 1 for t in keep), "guiowl": sum(g[t]["score"] >= 1 for t in keep)}


provisional = not (summ["v4"]["complete"] and summ["guiowl"]["complete"])
cmp_ = {"provisional": provisional,
        "complete": {k: summ[k]["complete"] for k in summ}, "pending_eligible_tasks": {k: summ[k]["pending_eligible_tasks"] for k in summ},
        "n_tasks": len(TASKS), "v4_successes": summ["v4"]["successes"], "guiowl_successes": summ["guiowl"]["successes"],
        "difference_pp": 100 * (summ["v4"]["successes"] - summ["guiowl"]["successes"]) / len(TASKS),
        "both": both, "v4_only": v_only, "guiowl_only": g_only,
        "neither": len(TASKS) - both - len(v_only) - len(g_only),
        "mcnemar_exact_p": mcnemar_exact(len(v_only), len(g_only)),
        "sensitivity_narrow": {"rule": "exclude tasks with a folder-level setup/scoring failure in either run", "tasks": narrow, **sens(narrow)},
        "sensitivity_broad": {"rule": "also exclude tasks with a MobileWorld device-health re-initialisation in either run", "tasks": broad, **sens(broad)},
        "note": "Secondary, descriptive benchmark (not preregistered as a primary endpoint); single run per model, temperature 0. "
                "Compares configured agent pipelines (adapter, prompt, image budget, parsing), not model weights alone."}
# third arm: MAI-UI-2B, paired against each of the other two on the same 105 tasks (descriptive, one run per model)
mu = summ["maiui"]["tasks"]
env_m = sorted(set(summ["maiui"]["tasks_with_folder_level_environment_error"]))


def pair(a, b, A, B, excl=()):
    keep = [t for t in TASKS if t not in excl]
    ao = sorted(t for t in keep if A[t]["score"] >= 1 and B[t]["score"] < 1)
    bo = sorted(t for t in keep if B[t]["score"] >= 1 and A[t]["score"] < 1)
    bt = sum(A[t]["score"] >= 1 and B[t]["score"] >= 1 for t in keep)
    return {"n_tasks": len(keep), a: sum(A[t]["score"] >= 1 for t in keep), b: sum(B[t]["score"] >= 1 for t in keep),
            "both": bt, f"{a}_only": ao, f"{b}_only": bo, "difference_pp": 100 * (len(ao) - len(bo)) / len(keep),
            "mcnemar_exact_p": mcnemar_exact(len(ao), len(bo))}


m_no_result_setup = sorted(t for t, x in mu.items() if x["final_category"] == "setup_failed")
HALF_A = set(json.load(open(os.path.join(R, "mw_gui_en_maiui_a.json"))))
cmp_["maiui"] = {"complete": summ["maiui"]["complete"], "successes": summ["maiui"]["successes"],
                 "vs_v4": pair("maiui", "v4", mu, v), "vs_guiowl": pair("maiui", "guiowl", mu, g),
                 "no_result_setup_failed": m_no_result_setup,
                 "sensitivity_exclude_maiui_final_setup_failures": {
                     "rule": "exclude tasks whose final MAI-UI folder ended setup_failed (no result) in the MAI-UI run",
                     "vs_v4": pair("maiui", "v4", mu, v, m_no_result_setup), "vs_guiowl": pair("maiui", "guiowl", mu, g, m_no_result_setup)},
                 # per-task history of those final setup failures (Codex mw_maiui_audit P2: they are mixed, not one dead device)
                 "no_result_setup_failed_history": {t: {
                     "half": "a" if t in HALF_A else "b",
                     "container": "mobile_world_env_0" if t in HALF_A else "lfmenv_0",
                     "executions": len(mu[t]["attempts"]),
                     "executions_with_model_actions": sum(len(traj_steps(os.path.join(R, "maiui_gui_en_r2", a["folder"])) if a["kind"] != "moved_by_mw_resume"
                                                              else traj_steps(next(iter(glob.glob(os.path.join(R, "_interrupted", "maiui_*", a["folder"]))), ""))) > 0
                                                          for a in mu[t]["attempts"]),
                     "earlier_endings": [a["detail"] for a in mu[t]["attempts"][:-1]]} for t in m_no_result_setup},
                 "sensitivity_exclude_maiui_env_events": {
                     "tasks": sorted(set(summ["maiui"]["tasks_with_folder_level_environment_error"]) | set(summ["maiui"]["tasks_with_device_unhealthy_reinit"])),
                     "vs_v4": pair("maiui", "v4", mu, v, set(summ["maiui"]["tasks_with_folder_level_environment_error"]) | set(summ["maiui"]["tasks_with_device_unhealthy_reinit"])),
                     "vs_guiowl": pair("maiui", "guiowl", mu, g, set(summ["maiui"]["tasks_with_folder_level_environment_error"]) | set(summ["maiui"]["tasks_with_device_unhealthy_reinit"]))},
                 "conditional_if_five_final_setup_failures_were_successes": {
                     "tasks": [t for t in m_no_result_setup if t != "ThanksgivingPrepTask"],
                     "vs_v4": pair("maiui", "v4", {t: ({"score": 1.0} if t in m_no_result_setup and t != "ThanksgivingPrepTask" else mu[t]) for t in TASKS}, v),
                     "vs_guiowl": pair("maiui", "guiowl", {t: ({"score": 1.0} if t in m_no_result_setup and t != "ThanksgivingPrepTask" else mu[t]) for t in TASKS}, g),
                     "note": "a fixed what-if for those five tasks only, not a bound on a run with every environment problem repaired"},
                 "note": "Optional third arm started after GUI-Owl and v4 finished, on the same two containers (recreated after spot "
                         "preemptions); Q8_0 because its Q4_K_M output degenerates (results/maiui_quant_check.md)."}
json.dump(cmp_, open("results/mobileworld/mw_r2_comparison.json", "w"), indent=1)


def pct(n):
    return f"{100 * n / len(TASKS):.1f}%"


def fmt_cats(d):
    return ", ".join(f"{k} {n}" for k, n in sorted(d.items(), key=lambda kv: -kv[1])) or "none"


tag = " (PROVISIONAL: " + "; ".join(f"{summ[k]['model']} pending {', '.join(summ[k]['pending_eligible_tasks'])}"
                                    for k in summ if summ[k]["pending_eligible_tasks"]) + ")" if provisional else ""
L = [f"# MobileWorld run 2: v4 vs GUI-Owl-1.5-2B, with MAI-UI-2B as a third arm (105 English GUI-only tasks){tag}", "",
     "| Model | Successes / 105 | Tasks with a result | No result (counted as failure) | Folder-level setup/scoring failures (tasks) | Device-health re-initialisations (tasks) | Task executions |",
     "|---|---|---|---|---|---|---|"]
for key in ("v4", "guiowl", "maiui"):
    s = summ[key]
    nr = s["no_result_counted_as_failure"]
    L.append(f"| {s['model']} | **{s['successes']}** ({pct(s['successes'])}) | {s['with_result']} | "
             f"{len(nr)}: {', '.join(f'{t} ({c})' for t, c in nr.items()) or '-'} | {s['folder_level_environment_errors']} ({len(s['tasks_with_folder_level_environment_error'])}) | "
             f"{s['device_unhealthy_reinits']} ({len(s['tasks_with_device_unhealthy_reinit'])}) | {s['task_executions']} |")
sn, sb = cmp_["sensitivity_narrow"], cmp_["sensitivity_broad"]
L += ["", f"Paired on the same 105 tasks: both solved {both}, v4 only {len(v_only)}, GUI-Owl only {len(g_only)}, neither {cmp_['neither']}; "
      f"difference {cmp_['difference_pp']:+.1f} pp, exact McNemar p = {cmp_['mcnemar_exact_p']:.3g} (conditional on these task pairs; one run per model).", "",
      f"Sensitivity (environment): excluding the {len(narrow)} tasks with a folder-level setup/scoring failure in either run, v4 "
      f"{sn['v4']} vs GUI-Owl {sn['guiowl']} of {sn['n_tasks']}; also excluding tasks with a device-health re-initialisation "
      f"({len(broad)} tasks), v4 {sb['v4']} vs GUI-Owl {sb['guiowl']} of {sb['n_tasks']}. Excluding known errors cannot show that the "
      "remaining tasks were unaffected; GUI-Owl's container had more environment failures than v4's.", ""]
cm = cmp_["maiui"]
for nm, k2 in (("v4", "vs_v4"), ("GUI-Owl", "vs_guiowl")):
    q = cm[k2]; o = "v4" if nm == "v4" else "guiowl"
    L.append(f"MAI-UI-2B vs {nm} (paired, 105 tasks): both {q['both']}, MAI-UI only {len(q['maiui_only'])}, {nm} only "
             f"{len(q[o + '_only'])}; difference {q['difference_pp']:+.1f} pp, exact McNemar p = {q['mcnemar_exact_p']:.3g}.")
se = cm["sensitivity_exclude_maiui_final_setup_failures"]
L += ["", f"MAI-UI's run ended {len(cm['no_result_setup_failed'])} tasks without a result after setup failures "
      f"({', '.join(cm['no_result_setup_failed'])}; GUI-Owl and v4: ThanksgivingPrepTask only). Excluding them: MAI-UI "
      f"{se['vs_v4']['maiui']} vs v4 {se['vs_v4']['v4']} vs GUI-Owl {se['vs_guiowl']['guiowl']} of {se['vs_v4']['n_tasks']}. "
      "MAI-UI ran after the other two, on recreated containers after two spot preemptions, so its environment was not identical.", "",
      "Those final setup failures have mixed histories (per task in mw_r2_comparison.json): "
      + "; ".join(f"{t} (half {h['half']}, {h['executions']} executions, {h['executions_with_model_actions']} with model actions, earlier: "
                  f"{fmt_cats({c: h['earlier_endings'].count(c) for c in set(h['earlier_endings'])})})"
                  for t, h in cm["no_result_setup_failed_history"].items()) + ". "
      "In the ReadQwen3Paper tasks MAI-UI acted and then called ask_user, which fails without a user simulator, before setup later "
      "failed. Half b's emulator (lfmenv_0) lost device health during its last invocation: ReadQwen3PaperTask2 initialised at 11:18 "
      "UTC and ran 50 steps, then initialisations failed from about 11:29 UTC. Half a had separate setup failures around "
      "10:29-10:36 UTC. The containers' own logs (results/mobileworld/container_logs/, saved before the VM was deleted; they start "
      "at the containers' recreation after the second preemption, 06:30 UTC) show the emulator dying with a fatal KVM error "
      "(`kvm_user_backed_ram_map: error registering slot: File exists`) 6 times in mobile_world_env_0 and 11 times in lfmenv_0 "
      "from 07:14 UTC on. The matching logs of the GUI-Owl and v4 runs no longer exist (those containers were deleted by "
      "earlier preemptions), so whether they saw the same crashes is unknown. "
      f"What-if for these five tasks only (not a bound on a run with every environment problem repaired): had they been successes, MAI-UI "
      f"{cm['conditional_if_five_final_setup_failures_were_successes']['vs_guiowl']['maiui']} vs GUI-Owl 22 "
      f"({cm['conditional_if_five_final_setup_failures_were_successes']['vs_guiowl']['difference_pp']:+.1f} pp, McNemar p = "
      f"{cm['conditional_if_five_final_setup_failures_were_successes']['vs_guiowl']['mcnemar_exact_p']:.3g}); GUI-Owl and v4 solved none of them. "
      f"Excluding all {len(cm['sensitivity_exclude_maiui_env_events']['tasks'])} tasks with a folder-level setup/scoring failure or a "
      f"device-health re-initialisation in MAI-UI's run: MAI-UI {cm['sensitivity_exclude_maiui_env_events']['vs_v4']['maiui']} vs v4 "
      f"{cm['sensitivity_exclude_maiui_env_events']['vs_v4']['v4']} vs GUI-Owl {cm['sensitivity_exclude_maiui_env_events']['vs_guiowl']['guiowl']} "
      f"of {cm['sensitivity_exclude_maiui_env_events']['vs_v4']['n_tasks']}.",
      "", 
      "Retries and harness events (no score was changed by them):", ""]
for key in ("v4", "guiowl", "maiui"):
    s = summ[key]
    L.append(f"* {s['model']}: earlier folders ended {fmt_cats(s['earlier_folder_outcomes'])}; successes after an earlier failed folder: "
             + (", ".join(s["successes_after_an_earlier_failed_folder"]) or "none")
             + "; successes after a device-health re-initialisation: " + (", ".join(s["successes_after_a_device_reinit"]) or "none") + ".")
sv, sg = summ["v4"], summ["guiowl"]
L += [f"* GUI-Owl's official agent returns an `error_env` sentinel after 5 unparseable outputs, which MobileWorld's own action "
      f"validator rejects (an upstream bug), so instead of ending and being scored the task was re-executed "
      f"({sg['env_fail_sentinel_rejected_executions']} executions); those tasks still scored 0.",
      f"* `ask_user` needs an LLM-backed user simulator this setup does not have: {sg['ask_user_without_simulator_executions']} GUI-Owl "
      f"executions and {summ['maiui']['ask_user_without_simulator_executions']} MAI-UI executions hit it (v4 has no such action). `double_tap` was rejected by GUI-Owl's official action adapter (not by the runtime).",
      f"* v4's adapter completes v4's trained type-then-Enter action with a synthetic Enter on the next environment step "
      f"({sv['synthetic_enters']} synthetic Enters; they count toward the 50-round budget, so v4 made fewer than 50 decisions in "
      f"{sv['tasks_at_step_budget_with_synthetic_enters']} of the {sv['tasks_ending_at_step_budget']} tasks that reached the budget). When typing was the 50th round the Enter was never sent: "
      f"{', '.join(sv['enter_dropped_at_step_budget']) or 'none'} (all scored 0; not evidence they would have passed).",
      "* ThanksgivingPrepTask's initialisation failed on every attempt in both containers (and on AWS in v4 run 1): a persistent "
      "task-specific initialisation failure; whether from task code or a shared dependency is not identified.", "",
      "| Setting | v4 | GUI-Owl (official agent) | MAI-UI (official agent) |", "|---|---|---|---|",
      "| Image history | current screenshot | current screenshot (`history_n` 1) | current screenshot (`history_n` 1; official default 3) |",
      "| Text history | last 8 intent/action pairs | all previous step conclusions | official agent's own (unchanged) |",
      "| Image budget | client resize to at most 880x880 pixels of area, server cap 1,024 tokens | full screenshot, server cap 2,600 tokens | full screenshot, server cap 2,600 tokens |",
      "| Output cap / parse attempts | 512 tokens / up to 2 | 2,048 tokens / up to 5 | 2,048 tokens / official |",
      "| Quantisation | Q4_K_M | Q4_K_M | Q8_0 (Q4_K_M degenerates) |",
      "| Step budget | 50 environment rounds incl. synthetic Enters | 50 environment rounds | 50 environment rounds |", "",
      "MobileWorld's own `--auto_retry 3` (same flag in every run) re-runs a task whose execution ended without a result, whatever "
      "the reason; mw_resume.sh then applied the pre-declared completion rule (docs/preregistrations/heldout-main-vs-gui-owl.md 2026-11-19 01:55, clarified "
      "05:45: the fresh-container allowance is one more invocation, inside which `--auto_retry 3` allows up to 4 executions, "
      "equally for every model). Single run per model at temperature 0; a secondary, descriptive benchmark comparing agent "
      "pipelines, not model weights alone. Independent recomputation: results/codex/mw_r2_audit/ (VALID WITH CAVEATS)."]
open("results/mobileworld/mw_r2_comparison.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
