"""Summarise the v4.1 follow-up MobileWorld run (run 3: the variant selected by docs/preregistrations/mobileworld-followup-waitrelabel.md, 105 English GUI-only
tasks) from results/mobileworld/traj_r3/ (pulled by scripts/mobileworld/mw_pull_r3.sh) and compare it with run 2.
Same outcome rule as run 2 (analysis/mw_summarize_r2.py, whose classify / mcnemar_exact / traj_steps are reused): score =
the final folder's result.txt; a task without one counts as a failure.
Primary (PREREG_v41): selected variant vs v4 (6/105), paired, exact two-sided McNemar. Secondary (descriptive): vs GUI-Owl
(22/105) and MAI-UI (11/105) from run 2; loop metrics (wait under non-wait intents, repeated intents, 50-step tasks).
Writes results/mobileworld/<run>_gui_en_r3_summary.json and results/mobileworld/mw_r3_comparison.{json,md}.
Usage: python analysis/mw_summarize_r3.py v42
"""
import collections
import glob
import json
import os
import re
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else "v42"
NAMES = {"v42": "LFM3-VL-2B-AndroidAgent-v4.2 (no guards, MobileWorld-native typing)"}
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mw_summarize_r2.py")).read().split("summ = {}")[0]
exec(src)                                       # imports, TASKS, classify, mcnemar_exact, traj_steps (run-2 rule)
R3 = "results/mobileworld/traj_r3"
TASKS = [t if isinstance(t, str) else t.get("task_name", t.get("name")) for t in TASKS]
WAITY = re.compile(r"\b(wait|waiting|load|loading|loads|loaded)\b", re.I)


def intent(p):
    m = re.search(r"<think>(.*?)</think>", p or "", re.S)
    if m:
        return m.group(1).strip().splitlines()[0][:150] if m.group(1).strip() else ""
    m = re.search(r"Action:\s*(.*)", p or "")
    return m.group(1).strip()[:150] if m else ""


def atype(s):
    a = s.get("action") or {}
    return a.get("action_type") if isinstance(a, dict) else str(a)


def loops(root):
    n = waits = wait_nw = same = cap = 0
    for t in TASKS:
        st = traj_steps(os.path.join(root, t))
        if not st:
            continue
        ty = [atype(s) for s in st]
        it = [intent(s.get("prediction")) for s in st]
        n += len(st)
        waits += ty.count("wait")
        wait_nw += sum(1 for a, i in zip(ty, it) if a == "wait" and not WAITY.search(i))
        same += sum(1 for k in range(1, len(it)) if it[k] and it[k] == it[k - 1])
        cap += len(st) >= 50
    return {"steps": n, "wait_steps": waits, "wait_under_non_wait_intent": wait_nw,
            "wait_share": round(waits / n, 3) if n else None,
            "repeated_intent_share": round(same / n, 3) if n else None, "tasks_at_50_steps": cap}


root = os.path.join(R3, f"{RUN}_gui_en_r3")
tasks = {}
for t in TASKS:
    d = os.path.join(root, t)
    kind, val = classify(d) if os.path.isdir(d) else ("error", "never_started")
    backups = sorted(glob.glob(d + "_backup_*"))
    tasks[t] = {"score": val if kind == "result" else 0.0, "has_result": kind == "result",
                "final_category": None if kind == "result" else val, "steps": len(traj_steps(d)),
                "earlier_folders": [classify(b)[1] for b in backups]}
succ = {t for t, v in tasks.items() if v["score"] > 0}
summ = {"model": NAMES.get(RUN, RUN), "run": RUN, "complete": os.path.exists(os.path.join(R3, f"{RUN}_complete")),
        "n_tasks": len(TASKS), "with_result": sum(v["has_result"] for v in tasks.values()), "successes": len(succ),
        "no_result_counted_as_failure": {t: v["final_category"] for t, v in tasks.items() if not v["has_result"]},
        "loop_metrics": loops(root), "tasks": tasks}
json.dump(summ, open(f"results/mobileworld/{RUN}_gui_en_r3_summary.json", "w"), indent=1)

base = {}
for k in ("v4", "guiowl", "maiui"):
    s = json.load(open(f"results/mobileworld/{k}_gui_en_r2_summary.json"))
    base[k] = {t for t, v in s["tasks"].items() if v["score"] and v["score"] > 0}
label = {"v4": "v4", "guiowl": "GUI-Owl-1.5-2B", "maiui": "MAI-UI-2B"}
cmp_ = {"run": RUN, "successes": len(succ), "complete": summ["complete"], "pairs": {}}
for k, B in base.items():
    b, c = len(succ - B), len(B - succ)
    cmp_["pairs"][k] = {"baseline_successes": len(B), "both": len(succ & B), f"{RUN}_only": sorted(succ - B),
                        f"{k}_only": sorted(B - succ), "difference_pp": round(100 * (b - c) / len(TASKS), 1),
                        "mcnemar_exact_p": round(mcnemar_exact(b, c), 4)}
cmp_["loop_metrics"] = {RUN: summ["loop_metrics"], "v4": loops(os.path.join(R, "v4_gui_en_r2"))}
json.dump(cmp_, open("results/mobileworld/mw_r3_comparison.json", "w"), indent=1)

L = [f"# MobileWorld run 3: {NAMES.get(RUN, RUN)} (105 English GUI-only tasks)", "",
     "Post-hoc follow-up ([docs/preregistrations/mobileworld-followup-waitrelabel.md](../../docs/preregistrations/mobileworld-followup-waitrelabel.md)): designed after reading v4's MobileWorld trajectories, so "
     "MobileWorld is a development benchmark for this run. v4's 6/105 stays the held-out MobileWorld number.", "",
     "| Model | Successes / 105 | Both | This run only | Baseline only | Difference | Exact McNemar p |", "|---|---|---|---|---|---|---|"]
for k, p in cmp_["pairs"].items():
    L.append(f"| {label[k]} (run 2) | {p['baseline_successes']} | {p['both']} | {len(p[RUN + '_only'])} | {len(p[k + '_only'])} | "
             f"{p['difference_pp']:+.1f} pp | {p['mcnemar_exact_p']} |")
L += ["", f"**{RUN}: {len(succ)}/105**; tasks with a result {summ['with_result']}; no result (failure): "
      + (", ".join(f"{t} ({c})" for t, c in summ["no_result_counted_as_failure"].items()) or "none") + ".", "",
      f"- {RUN} solved: {', '.join(sorted(succ))}",
      f"- Gained vs v4: {', '.join(cmp_['pairs']['v4'][RUN + '_only']) or 'none'}; lost vs v4: "
      f"{', '.join(cmp_['pairs']['v4']['v4_only']) or 'none'}", "",
      "| Loop metric | v4 (run 2) | " + RUN + " |", "|---|---|---|"]
a, b = cmp_["loop_metrics"]["v4"], cmp_["loop_metrics"][RUN]
for key, nm in (("steps", "Steps"), ("wait_share", "Share of steps that are `wait`"),
                ("wait_under_non_wait_intent", "`wait` under a non-wait intent"),
                ("repeated_intent_share", "Steps repeating the previous intent"), ("tasks_at_50_steps", "Tasks ending at the 50-step limit")):
    L.append(f"| {nm} | {a[key]} | {b[key]} |")
L += ["", "Single run per model at temperature 0. v4 ran with synthetic Enters after typing; this run uses MobileWorld-native "
      "typing, so step counts are not strictly comparable."]
open("results/mobileworld/mw_r3_comparison.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
