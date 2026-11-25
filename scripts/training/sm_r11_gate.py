#!/usr/bin/env python3
"""Round 11 / E-T offline gate (docs/PREREG_v49.md). Inputs: the candidate's round-8 gate result (sm_r8_gate.py,
<eval>/<name>_offline_gate.json), E's (results/v46_dev/e_eval/r8e_offline_gate.json, shipped as e_gate.json) and both
models' outputs on the two multi-part probes (<eval>/{e,<name>}_probe_M_{done,notdone}.jsonl).
  * the eight round-8 bars E passes: unchanged
  * the two E fails: no worse than E by more than about one standard error (early status <= 3.80%, C1 <= 22%)
  * M_done (held-out judged-done GUI-Odyssey terminal screens): `status` share >= E's + 10 points and >= 50%
  * M_notdone (judged-not-done GUI-Odyssey terminal screens): `status` share <= E's + 5 points
Probe value = share of rows where the model outputs `status`. Prints one R11 GATE line, writes <out>."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_format as af  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--eval", required=True)
ap.add_argument("--e_gate", required=True)
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
e = json.load(open(a.e_gate))["candidate"]
c, cand = g["checks"], g["candidate"]
c["ac_early_status_2plus"] = cand["ac_early_status_2plus"] <= 0.0380
c["probe_C1_hist_done"] = cand["probes"]["C1_hist_done"] <= 0.22
m = {}
for p in ("M_done", "M_notdone"):
    (ve, ne), (vc, nc) = rate("e", p), rate(a.name, p)
    assert ne == nc and ne > 0, (p, ne, nc)
    m[p] = {"e": ve, "candidate": vc, "n": nc}
c["M_done"] = m["M_done"]["candidate"] >= max(m["M_done"]["e"] + 0.10, 0.50)
c["M_notdone"] = m["M_notdone"]["candidate"] <= m["M_notdone"]["e"] + 0.05
out = {"name": a.name, "candidate": cand, "e": {k: e[k] for k in ("ac_high", "ac_early_status_2plus", "probes") if k in e},
       "multi_part": m, "checks": c, "pass": all(c.values())}
json.dump(out, open(a.out, "w"), indent=1)
print("R11 GATE", a.name, json.dumps(out), flush=True)
