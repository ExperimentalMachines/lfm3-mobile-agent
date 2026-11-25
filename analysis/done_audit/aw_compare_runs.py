"""Compare AndroidWorld seed-30 runs on the same tasks (round 8: E vs D vs v4). Per run: successes, false completes
(`status complete` but the task failed), useless waits (next screen unchanged, train/screen_change.py on the run's
thumbnails), repeated taps (the same click three or more times in a row), harness errors; for false completes, whether
the action right before `complete` changed the screen. Paired exact McNemar test of each run against the first.
Diagnosis only: nothing from AndroidWorld runs is trained on.
Usage: python aw_compare_runs.py <run name> <run name> ... [--out results.json]
"""
import argparse
import glob
import gzip
import json
import math
import os
import pickle
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "train"))
import screen_change as sc  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("runs", nargs="+")
ap.add_argument("--out", default="")
a = ap.parse_args()


def load(name):
    # The .pkl.gz episode files are written by our own local AndroidWorld harness (run_aw.py) under results/; they are
    # trusted local outputs, which is why pickle (AndroidWorld's own checkpoint format) is acceptable here.
    R = sorted(glob.glob(f"results/androidworld/{name}/run_*"))[-1]
    out = {}
    for f in glob.glob(R + "/*.pkl.gz"):
        d = pickle.load(gzip.open(f))[0]
        e = d["episode_data"] if isinstance(d["episode_data"], dict) else {}
        acts = [x if isinstance(x, dict) else {} for x in e.get("parsed_action") or []]
        th = e.get("screenshot_thumb_jpg") or []
        types = [x.get("action_type") for x in acts]
        waits = useless = rep = 0
        run = 1
        for i, t in enumerate(types):
            if t == "wait":
                waits += 1
                if i + 1 < len(th) and th[i] is not None and th[i + 1] is not None and not sc.changed(sc.prep(th[i]), sc.prep(th[i + 1])):
                    useless += 1
            if i and t == "click" and acts[i] == acts[i - 1]:
                run += 1
                rep += run == 3
            else:
                run = 1
        last = acts[-1] if acts else {}
        fc = d["is_successful"] != 1 and last.get("action_type") == "status" and last.get("goal_status") == "complete"
        before_changed = None
        if fc and len(types) >= 2 and len(th) >= len(types):
            i = len(types) - 2  # the action before `complete`: its screen vs the screen at `complete`
            before_changed = bool(sc.changed(sc.prep(th[i]), sc.prep(th[i + 1])))
        out[os.path.basename(f).replace("_0.pkl.gz", "")] = {
            "success": d["is_successful"] == 1, "false_complete": fc, "steps": len(types), "waits": waits,
            "useless_waits": useless, "repeat_tap_runs": rep, "error": d.get("exception_info") is not None,
            "fc_prev_action": types[-2] if fc and len(types) >= 2 else None, "fc_prev_changed_screen": before_changed}
    return out


def mcnemar(b, c):  # exact two-sided binomial test on the discordant pairs
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


runs = {r: load(r) for r in a.runs}
tasks = sorted(set.intersection(*(set(v) for v in runs.values())))
base = a.runs[0]
summary = {"tasks": len(tasks)}
for r, v in runs.items():
    S = [v[t] for t in tasks]
    steps = sum(x["steps"] for x in S)
    fcs = [x for x in S if x["false_complete"]]
    s = {"successes": sum(x["success"] for x in S), "false_completes": len(fcs), "steps": steps,
         "wait_share": round(sum(x["waits"] for x in S) / max(steps, 1), 4),
         "useless_wait_share": round(sum(x["useless_waits"] for x in S) / max(steps, 1), 4),
         "repeat_tap_runs": sum(x["repeat_tap_runs"] for x in S), "harness_errors": sum(x["error"] for x in S),
         "false_complete_after_no_change": sum(x["fc_prev_changed_screen"] is False for x in fcs)}
    if r != base:
        b = sum(v[t]["success"] and not runs[base][t]["success"] for t in tasks)
        c = sum(runs[base][t]["success"] and not v[t]["success"] for t in tasks)
        s[f"vs_{base}"] = {"wins": b, "losses": c, "mcnemar_p": round(mcnemar(b, c), 3)}
    summary[r] = s
print(json.dumps(summary, indent=1))
if a.out:
    json.dump({"summary": summary, "per_task": runs}, open(a.out, "w"), indent=1)
