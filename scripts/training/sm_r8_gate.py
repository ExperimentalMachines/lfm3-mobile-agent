#!/usr/bin/env python3
"""Round 8 / v4.6 offline gate (docs/PREREG_v46.md): round 7's checks (sm_r7_gate.py) plus the history probes.
Probe value = share of rows where the candidate outputs `status`. Prints one OFFLINE GATE line, writes <out>."""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_format as af  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--eval", required=True)
ap.add_argument("--v4", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
base = a.out.replace(".json", "_r7checks.json")
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sm_r7_gate.py"), "--name", a.name,
                "--eval", a.eval, "--v4", a.v4, "--out", base], check=True, stdout=subprocess.DEVNULL)
g = json.load(open(base))


def rate(p):
    n = s = 0
    for l in open(os.path.join(a.eval, f"{a.name}_probe_{p}.jsonl")):
        r = json.loads(l)
        x = af.parse_action(r["output"].split("</think>")[-1])
        n += 1
        s += bool(x and x["action_type"] == "status")
    return s / n if n else None


probes = {p: rate(p) for p in ("T_term", "C2_hist_cut", "C0_base", "C1_hist_done", "C3_stale", "C3n_stale_note")}
g["candidate"]["probes"] = probes
c = g["checks"]  # ac_high, dev_answer, dev_complete, ac_early_status_2plus, androidlens_step_10plus (v4 bars)
c.update({"probe_C1_hist_done": probes["C1_hist_done"] <= 0.15, "probe_C3n_stale_note": probes["C3n_stale_note"] <= 0.10,
          "probe_C3_stale": probes["C3_stale"] <= 0.20, "probe_T_term": probes["T_term"] >= 0.70,
          "probe_C2_hist_cut": probes["C2_hist_cut"] >= 0.60})
g["pass"] = all(c.values())
json.dump(g, open(a.out, "w"), indent=1)
print("OFFLINE GATE", a.name, json.dumps(g), flush=True)
