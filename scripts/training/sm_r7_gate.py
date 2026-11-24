#!/usr/bin/env python3
"""Round 7 / v4.5 offline gate (docs/PREREG_v45.md). Reads the candidate's metrics and predictions, compares them with
v4's round-6 reference numbers (v4_reference.json: v4 through the same evaluator on its own 8-step prompt), writes
<out> and prints one OFFLINE GATE line.

Checks (all must hold):
  ac_high                  AndroidControl test high-level step accuracy          >= v4 - 0.02
  dev_answer               v4 dev_answer                                          >= v4 - 0.05
  dev_complete             v4 dev_complete                                        >= v4 - 0.05
  ac_early_status_2plus    AndroidControl test non-terminal rows at least 2 steps before the episode's terminal row:
                           share predicted `status`                               <= v4 + 0.005
  androidlens_step_10plus  AndroidLens English step accuracy at steps >= 10       >= v4
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_format as af  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--eval", required=True)
ap.add_argument("--v4", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
L = lambda key: json.load(open(os.path.join(a.eval, f"{a.name}_{key}.metrics.json")))


def status_rates(path):
  rows = [json.loads(l) for l in open(path)]
  term = {str(r["episode_id"]): int(r["step_idx"]) for r in rows if r.get("is_terminal")}
  out = {"2plus": [0, 0], "1": [0, 0], "late4": [0, 0]}
  for r in rows:
    e = str(r["episode_id"])
    if r.get("mode", "high") != "high" or r.get("is_terminal"):
      continue
    p = af.parse_action(r["output"].split("</think>")[-1])
    st = bool(p and p["action_type"] == "status")
    if int(r["step_idx"]) >= 4:
      out["late4"][0] += 1; out["late4"][1] += st
    if e in term:
      k = "2plus" if term[e] - int(r["step_idx"]) >= 2 else "1"
      out[k][0] += 1; out[k][1] += st
  return {k: (s / n if n else None) for k, (n, s) in out.items()}


ac = L("test_ac_high")
al = L("dev_androidlens_high")["high"]
b = al["by_bucket"]
parts = [b[x] for x in ("10-19", "20+") if x in b]
sr = status_rates(os.path.join(a.eval, f"{a.name}_test_ac_high.jsonl"))
c = {"ac_high": ac["high"]["overall"]["step_sr"], "terminal_complete": ac.get("terminal_complete", {}).get("step_sr"),
     "dev_answer": L("dev_answer")["step_sr"], "dev_complete": L("dev_complete")["step_sr"], "dev_memgui": L("dev_memgui")["step_sr"],
     "ac_early_status_2plus": sr["2plus"], "ac_status_1_before_end": sr["1"], "ac_late_status": sr["late4"],
     "androidlens_step": al["nonterminal"]["step_acc"],
     "androidlens_step_10plus": sum(x["step_acc"] * x["n"] for x in parts) / max(1, sum(x["n"] for x in parts)),
     "androidlens_early_status": al["nonterminal"]["early_status"], "androidlens_terminal": al.get("terminal", {})}
v = json.load(open(a.v4))
checks = {"ac_high": c["ac_high"] >= v["ac_high"] - 0.02,
          "dev_answer": c["dev_answer"] >= v["dev_answer"] - 0.05,
          "dev_complete": c["dev_complete"] >= v["dev_complete"] - 0.05,
          "ac_early_status_2plus": c["ac_early_status_2plus"] is not None and c["ac_early_status_2plus"] <= v["ac_early_status_2plus"] + 0.005,
          "androidlens_step_10plus": c["androidlens_step_10plus"] >= v["androidlens_step_10plus"]}
g = {"candidate": c, "v4": v, "checks": checks, "pass": all(checks.values())}
json.dump(g, open(a.out, "w"), indent=1)
print("OFFLINE GATE", a.name, json.dumps(g), flush=True)
