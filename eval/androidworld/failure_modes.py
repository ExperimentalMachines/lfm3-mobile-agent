"""Classify AndroidWorld episodes into failure modes from the raw episode pickles (written locally by android_world).

usage: python eval/androidworld/failure_modes.py <run_dir> [--out file.json]
Each episode gets the first matching label (priority order below); every episode also gets a set of flags.
"""
import argparse
import collections
import glob
import gzip
import json
import os
import pickle

from android_world.env import adb_utils


def act_key(a):
    if not isinstance(a, dict):
        return None
    t = a.get("action_type")
    p = a.get("point_2d")
    if isinstance(p, (list, tuple)) and len(p) == 2:
        p = (round(p[0] / 25), round(p[1] / 25))  # 2.5% grid tolerance
    return (t, p, a.get("text"), a.get("direction"), a.get("app_name"), a.get("goal_status"))


def max_run(xs):
    best, cur, prev = 0, 0, object()
    for x in xs:
        cur = cur + 1 if x == prev and x is not None else 1
        best, prev = max(best, cur), x
    return best


def classify(ep):
    ed = ep["episode_data"] if isinstance(ep.get("episode_data"), dict) else {}  # NaN when the episode raised
    acts = ed.get("parsed_action") or []
    types = [a.get("action_type") if isinstance(a, dict) else None for a in acts]
    flags = set()
    bad_apps = [a.get("app_name") for a in acts if isinstance(a, dict) and a.get("action_type") == "open_app"
                and adb_utils.get_adb_activity(str(a.get("app_name") or "")) is None]
    if bad_apps:
        flags.add("unknown_app_name")
    if max_run(types) >= 3 and "wait" in [t for t in types]:
        if max_run([t if t == "wait" else None for t in types]) >= 3:
            flags.add("wait_loop")
    if max_run([act_key(a) for a in acts if isinstance(a, dict) and a.get("action_type") != "wait"]) >= 3:
        flags.add("repeated_action_loop")
    if any(a is None for a in acts):
        flags.add("unparseable_step")
    last = types[-1] if types else None
    terminated = last in ("status", "answer")
    if ep.get("exception_info") or not ed:
        label = "exception"
    elif (ep["is_successful"] or 0) > 0:
        label = "success"
    elif last == "status" and (acts[-1] or {}).get("goal_status") == "infeasible":
        label = "declared_infeasible"
    elif last == "status":
        label = "premature_or_wrong_complete"
    elif last == "answer":
        label = "wrong_answer"
    elif "unknown_app_name" in flags and len(acts) and types[0] == "open_app" and bad_apps and bad_apps[0] == acts[0].get("app_name"):
        label = "stuck_after_unknown_app"
    elif flags & {"wait_loop", "repeated_action_loop"}:
        label = "loop_until_step_limit"
    else:
        label = "step_limit_no_termination" if not terminated else "other"
    return label, sorted(flags), bad_apps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = []
    for f in sorted(glob.glob(os.path.join(a.run_dir, "*.pkl.gz"))):
        ep = pickle.load(gzip.open(f))  # trusted: written by our own local android_world run
        ep = ep[0] if isinstance(ep, list) else ep
        label, flags, bad_apps = classify(ep)
        rows.append({"task": ep["task_template"], "label": label, "flags": flags, "unknown_apps": bad_apps,
                     "steps": ep["episode_length"]})
    lab = collections.Counter(r["label"] for r in rows)
    flg = collections.Counter(f for r in rows if r["label"] != "success" for f in r["flags"])
    apps = collections.Counter(x for r in rows for x in r["unknown_apps"])
    out = {"n": len(rows), "labels": dict(lab.most_common()), "flags_among_failures": dict(flg.most_common()),
           "unknown_app_names": dict(apps.most_common(25)), "episodes": rows}
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "episodes"}, indent=1))


if __name__ == "__main__":
    main()
