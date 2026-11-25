#!/usr/bin/env python3
"""Round 10 / v4.8 offline gate (docs/PREREG_v48.md): round 8's gate (sm_r8_gate.py; every bar unchanged) plus the
multi-part probes against E on the same evaluator and hardware:
  M_mid  (rows 1-3 actions before the end)  share of `status` <= E's - 5 points and <= 10%
  M_done (held-out terminal rows)            share of `status` >= E's + 10 points and >= 50%
Reported, not gated: wait probes W0 / W1 / W2 (share of `wait`) and the share of `wait` on C3n, for the candidate and E.
Prints one OFFLINE GATE line, writes <out>."""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_format as af  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--e_name", default="e")
ap.add_argument("--eval", required=True)
ap.add_argument("--v4", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
base = a.out.replace(".json", "_r8checks.json")
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sm_r8_gate.py"), "--name", a.name,
                "--eval", a.eval, "--v4", a.v4, "--out", base], check=True, stdout=subprocess.DEVNULL)
g = json.load(open(base))


def share(name, probe, typ):
    f = os.path.join(a.eval, f"{name}_probe_{probe}.jsonl")
    if not os.path.exists(f):
        return None
    n = s = 0
    for l in open(f):
        x = af.parse_action(json.loads(l)["output"].split("</think>")[-1])
        n += 1
        s += bool(x and x["action_type"] == typ)
    return s / n if n else None


m = {who: {"M_mid": share(nm, "M_mid", "status"), "M_done": share(nm, "M_done", "status")} for who, nm in (("candidate", a.name), ("e", a.e_name))}
rep = {who: {p: share(nm, p, "wait") for p in ("W0_base", "W1_nwait", "W2_loading", "C3n_stale_note")} for who, nm in (("candidate", a.name), ("e", a.e_name))}
g["candidate"]["multi_part"], g["e_multi_part"] = m["candidate"], m["e"]
g["reported_wait_share"] = rep
c, e = g["checks"], m["e"]
if None in (e["M_mid"], e["M_done"]):
    raise SystemExit("E's multi-part probe outputs are missing: the gate needs them (same evaluator)")
c.update({"probe_M_mid": m["candidate"]["M_mid"] <= min(e["M_mid"] - 0.05, 0.10),
          "probe_M_done": m["candidate"]["M_done"] >= max(e["M_done"] + 0.10, 0.50)})
g["pass"] = all(c.values())
json.dump(g, open(a.out, "w"), indent=1)
print("OFFLINE GATE", a.name, json.dumps(g), flush=True)
