"""Full outcome accounting for AndroidWorld runs (round 14 step 3, docs/preregistrations/round-14-own-history-vs-control.md; external review M3 and M10).
Every episode gets exactly one outcome:
  success              is_successful >= 1 (the checker) and no exception
  claim_unfinished     ended with `status complete` but not fully met (partial credit INCLUDED; answer tasks included)
  wrong_answer         ended with `answer` and not fully met
  claim_infeasible     ended with `status infeasible` and not fully met
  budget_exhausted     no terminal action (step limit or the agent never ended)
  exception            harness exception (counted separately; re-runs are the analysis's business)
Also: false_complete_legacy (analysis/aw_false_complete.py's narrower definition, kept for comparability).
With --paired WITH_CHECK WITHOUT_CHECK (same seed): done-check yield per task: blocked then success (recovered),
success without the check but not with it (lost), blocked then wrong answer / budget exhausted, and every block's outcome.
Usage: .venv-aw/bin/python -I analysis/aw_outcomes.py results/androidworld/<run> [...] [--paired RUN_CHECK RUN_NOCHECK]
"""
import argparse
import collections
import glob
import gzip
import json
import os
import pickle

ANS = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"])


def episodes(d):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "run_*", "*.pkl.gz"))):
        e = pickle.load(gzip.open(f)); e = e[0] if isinstance(e, list) else e  # trusted: our own runs
        out[e["task_template"]] = e
    return out


def outcome(e):
    dd = e.get("episode_data") if isinstance(e.get("episode_data"), dict) else {}
    if e.get("exception_info") is not None or not dd:
        return "exception", False
    v = e.get("is_successful")
    ok = v is not None and v == v and v >= 1
    acts = dd.get("parsed_action") or []
    last = acts[-1] if acts else None
    t = last.get("action_type") if isinstance(last, dict) else None
    legacy_fc = (t == "status" and last.get("goal_status", "complete") == "complete" and not ok and not ((v or 0) > 0)
                 and e["task_template"] not in ANS)
    if ok:
        return "success", legacy_fc
    if t == "status" and last.get("goal_status", "complete") == "complete":
        return "claim_unfinished", legacy_fc
    if t == "status":
        return "claim_infeasible", legacy_fc
    if t == "answer":
        return "wrong_answer", legacy_fc
    return "budget_exhausted", legacy_fc


def blocks(e):
    dd = e.get("episode_data") if isinstance(e.get("episode_data"), dict) else {}
    return sum(bool(x and x.get("blocked")) for x in (dd.get("done_check") or []))


def summary(d):
    eps = episodes(d)
    c = collections.Counter()
    for e in eps.values():
        o, fc = outcome(e)
        c[o] += 1
        c["false_complete_legacy"] += fc
    return {"run": os.path.basename(d.rstrip("/")), "episodes": len(eps), **{k: c[k] for k in (
        "success", "claim_unfinished", "wrong_answer", "claim_infeasible", "budget_exhausted", "exception", "false_complete_legacy")}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="*")
    ap.add_argument("--paired", nargs=2, metavar=("WITH_CHECK", "WITHOUT_CHECK"))
    a = ap.parse_args()
    for d in a.runs:
        print(json.dumps(summary(d)))
    if a.paired:
        w, n = episodes(a.paired[0]), episodes(a.paired[1])
        y = collections.Counter()
        detail = []
        for t in sorted(set(w) & set(n)):
            ow, on = outcome(w[t])[0], outcome(n[t])[0]
            b = blocks(w[t])
            y["tasks"] += 1
            y["with_check_success"] += ow == "success"
            y["without_check_success"] += on == "success"
            if b:
                y["episodes_with_blocks"] += 1
                y["blocks"] += b
                y[f"blocked_then_{ow}"] += 1
                detail.append({"task": t, "blocks": b, "with_check": ow, "without_check": on})
            y["recovered_success"] += bool(b) and ow == "success" and on != "success"
            y["lost_success"] += on == "success" and ow != "success"
            y["gained_success"] += ow == "success" and on != "success"
        print(json.dumps({"paired": [os.path.basename(x.rstrip("/")) for x in a.paired], **y}))
        for x in detail:
            print("  ", json.dumps(x))


if __name__ == "__main__":
    main()
