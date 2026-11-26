#!/usr/bin/env python3
"""Round 13 / E-S offline gate (docs/PREREG_v411.md): no regression on the round-8 evals, and the GUI-Odyssey ending probes.
  * round 11's first 10 checks: E's round-8 bars, with early status <= 3.80% and C1 <= 22%
  * M_done (judged-finished final screens): `status` >= 50%;  M_notdone (judged-unfinished): `status` <= 25%
The multi-step test (eval/androidcontrol/sop.py on the GGUF, Mac) is the second gate and runs after export.
Prints one R13 GATE line, writes <out>."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_format as af  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--eval", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()


def rate(who, p):
    n = s = 0
    for l in open(os.path.join(a.eval, f"{who}_probe_{p}.jsonl")):
        x = af.parse_action(json.loads(l)["output"].split("</think>")[-1])
        n += 1
        s += bool(x and x["action_type"] == "status")
    return round(s / n, 4) if n else None, n


g = json.load(open(os.path.join(a.eval, f"{a.name}_offline_gate.json")))
c, cand = g["checks"], g["candidate"]
c["ac_early_status_2plus"] = cand["ac_early_status_2plus"] <= 0.0380
c["probe_C1_hist_done"] = cand["probes"]["C1_hist_done"] <= 0.22
m = {p: {"e": rate("e", p)[0], "candidate": rate(a.name, p)[0], "n": rate(a.name, p)[1]} for p in ("M_done", "M_notdone")}
c["M_done"] = m["M_done"]["candidate"] >= 0.50
c["M_notdone"] = m["M_notdone"]["candidate"] <= 0.25
out = {"name": a.name, "candidate": cand, "endings": m, "checks": c, "pass": all(c.values())}
json.dump(out, open(a.out, "w"), indent=1)
print("R13 GATE", a.name, json.dumps(out), flush=True)
