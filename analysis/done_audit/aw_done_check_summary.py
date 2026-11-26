"""What the round-12 done check did in AndroidWorld runs (docs/PREREG_v410.md, "Reported"): checks asked, answers,
blocks, blocks in episodes that still ended in success, episodes that hit the block cap, and false completes the check
let through (definition of analysis/aw_false_complete.py). Read-only.
Usage: .venv-aw/bin/python -I analysis/done_audit/aw_done_check_summary.py results/androidworld/<run> [...]
"""
import collections
import glob
import gzip
import json
import os
import pickle
import sys

ANS = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"])

for d in sys.argv[1:]:
    c = collections.Counter()
    blocked_eps = []
    for f in sorted(glob.glob(os.path.join(d, "run_*", "*.pkl.gz"))):
        e = pickle.load(gzip.open(f)); e = e[0] if isinstance(e, list) else e  # trusted: our own runs
        dd = e.get("episode_data") if isinstance(e.get("episode_data"), dict) else {}
        c["episodes"] += 1
        if e.get("exception_info") is not None or not dd:
            c["exceptions"] += 1
            continue
        v = e.get("is_successful")
        ok = v is not None and v == v and v >= 1
        checks = [x for x in (dd.get("done_check") or []) if x]
        nb = sum(bool(x.get("blocked")) for x in checks)
        for x in checks:
            if x.get("asked"):
                c["checks_asked"] += 1
                c["answer_" + x["answer"]] += 1
            else:
                c["checks_skipped_cap"] += 1
        c["blocks"] += nb
        acts = dd.get("parsed_action") or []
        last = acts[-1] if acts else None
        ended_complete = isinstance(last, dict) and last.get("action_type") == "status" and last.get("goal_status", "complete") == "complete"
        fc = ended_complete and not ok and not ((v or 0) > 0) and e["task_template"] not in ANS
        c["successes"] += ok
        c["false_completes"] += fc
        if nb:
            c["episodes_with_blocks"] += 1
            c["blocked_then_success"] += ok
            c["blocked_then_false_complete"] += fc
            c["blocked_then_other_failure"] += (not ok and not fc)
            blocked_eps.append({"task": e["task_template"], "blocks": nb, "success": ok, "false_complete": fc,
                                "steps": len(acts), "reasons": [x.get("reason", "")[:120] for x in checks if x.get("blocked")]})
        if fc and checks and checks[-1].get("asked") and checks[-1].get("answer") != "no":
            c["false_completes_check_said_yes"] += 1
        if fc and checks and not checks[-1].get("asked"):
            c["false_completes_after_cap"] += 1
    print(json.dumps({"run": os.path.basename(d.rstrip("/")), **c}))
    for b in blocked_eps:
        print("  ", json.dumps(b)[:400])
