#!/usr/bin/env python3
"""Round 12 / E-V offline gate (docs/preregistrations/round-12-done-check.md). Inputs: the candidate's round-8 gate result (sm_r8_gate.py,
<eval>/<name>_offline_gate.json) and E's and the candidate's outputs on the four probes
(<eval>/{e,<name>}_probe_{M_done,M_notdone,V_done,V_notdone}.jsonl; the V probes are the M screens asked the done question).
  * round 11's first 10 checks: E's round-8 bars, with early status <= 3.80% and C1 <= 22%
  * M_done `status` >= 50%; M_notdone `status` <= 35%
  * V_done answers yes >= 75%; V_notdone answers no >= 75%
  * model + check: M_notdone rows where the model says `status` AND the check (same screen) does not say no <= 15%;
    M_done rows where the model says `status` and the check does not say no >= 50%
    (the harness accepts a `complete` unless the check answers no: an unparseable answer counts as yes)
Prints one R12 GATE line, writes <out>."""
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


def rows(who, p):
    out = {}
    for l in open(os.path.join(a.eval, f"{who}_probe_{p}.jsonl")):
        j = json.loads(l)
        out[(str(j["episode_id"]), int(j["step_idx"]))] = j["output"].split("</think>")[-1].strip()
    return out


def says_status(txt):
    x = af.parse_action(txt)
    return bool(x and x["action_type"] == "status")


def answer(txt):
    t = txt.strip().strip(".").lower()
    return "yes" if t.startswith("yes") else "no" if t.startswith("no") else "unparsed"


def probe_stats(who):
    s = {}
    for kind in ("done", "notdone"):
        m, v = rows(who, f"M_{kind}"), rows(who, f"V_{kind}")
        assert set(m) == set(v) and m, (who, kind, len(m), len(v))
        n = len(m)
        st = {k: says_status(t) for k, t in m.items()}
        an = {k: answer(t) for k, t in v.items()}
        s[kind] = {"n": n, "status": round(sum(st.values()) / n, 4),
                   "check_yes": round(sum(x == "yes" for x in an.values()) / n, 4),
                   "check_no": round(sum(x == "no" for x in an.values()) / n, 4),
                   "check_unparsed": round(sum(x == "unparsed" for x in an.values()) / n, 4),
                   "status_and_not_blocked": round(sum(st[k] and an[k] != "no" for k in m) / n, 4)}
    return s


g = json.load(open(os.path.join(a.eval, f"{a.name}_offline_gate.json")))
c, cand = g["checks"], g["candidate"]
c["ac_early_status_2plus"] = cand["ac_early_status_2plus"] <= 0.0380
c["probe_C1_hist_done"] = cand["probes"]["C1_hist_done"] <= 0.22
pe, pc = probe_stats("e"), probe_stats(a.name)
c["M_done"] = pc["done"]["status"] >= 0.50
c["M_notdone"] = pc["notdone"]["status"] <= 0.35
c["V_done"] = pc["done"]["check_yes"] >= 0.75
c["V_notdone"] = pc["notdone"]["check_no"] >= 0.75
c["system_M_notdone"] = pc["notdone"]["status_and_not_blocked"] <= 0.15
c["system_M_done"] = pc["done"]["status_and_not_blocked"] >= 0.50
out = {"name": a.name, "candidate": cand, "probes": {"e": pe, a.name: pc}, "checks": c, "pass": all(c.values())}
json.dump(out, open(a.out, "w"), indent=1)
print("R12 GATE", a.name, json.dumps(out), flush=True)
