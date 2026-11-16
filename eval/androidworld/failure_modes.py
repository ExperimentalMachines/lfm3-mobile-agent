"""Describe AndroidWorld episodes from the raw episode pickles (written locally by our own android_world runs).

usage: python eval/androidworld/failure_modes.py <run_dir> [--out file.json]

Outcome label per episode (descriptive, NOT a causal diagnosis):
  success | exception | complete_but_failed (agent signalled completion, judge says failed) | infeasible_declared |
  answer_but_failed | step_budget_exhausted (no terminal action: android_world only ends a non-terminated episode at the
  task's step budget, so a non-terminated, non-exception episode necessarily exhausted it).
Flags (overlapping, observational): unmapped_open_app (android_world's own launch_app would not resolve the name: not a
_DEFAULT_URIS key, no _PATTERN_TO_ACTIVITY match, not package-like), wait_run3 (>=3 consecutive waits),
same_action_run3 (>=3 consecutive identical non-wait actions, coordinates on a 25-unit grid; any other action breaks
the run), unparseable_step. Handles both our JSON schema (action_type/point_2d) and GUI-Owl's (action/coordinate).
"""
import argparse
import collections
import glob
import gzip
import json
import os
import pickle

from android_world.env import adb_utils

_GUIOWL = {"click": "click", "long_press": "long_press", "swipe": "scroll", "type": "input_text", "wait": "wait",
           "terminate": "status", "answer": "answer", "open": "open_app"}
_BUTTON = {"back": "navigate_back", "home": "navigate_home", "enter": "keyboard_enter"}


def norm(a):
    """-> dict(type, point, arg, status) or None."""
    if not isinstance(a, dict):
        return None
    if "action_type" in a:
        t = a.get("action_type")
        return {"type": t, "point": a.get("point_2d"), "status": a.get("goal_status"),
                "arg": a.get("text") or a.get("app_name") or a.get("direction")}
    if "action" in a:
        t = a.get("action")
        t = _BUTTON.get(str(a.get("button", "")).lower(), "system_button") if t == "system_button" else _GUIOWL.get(t, t)
        st = {"success": "complete", "failure": "infeasible"}.get(a.get("status"), a.get("status"))
        return {"type": t, "point": a.get("coordinate"), "status": st,
                "arg": a.get("text") or (tuple(a["coordinate2"]) if a.get("coordinate2") else None)}
    return None


def key(n):
    if n is None:
        return None
    p = n["point"]
    if isinstance(p, (list, tuple)) and len(p) == 2:
        p = (round(p[0] / 25), round(p[1] / 25))
    return (n["type"], p, n["arg"])


def max_run(xs):
    best, cur, prev = 0, 0, object()
    for x in xs:
        cur = cur + 1 if (x is not None and x == prev) else 1
        best, prev = max(best, cur), x
    return best


def app_resolves(name):
    name = str(name or "")
    return name in adb_utils._DEFAULT_URIS or adb_utils.get_adb_activity(name) is not None or "." in name


def classify(ep):
    ed = ep["episode_data"] if isinstance(ep.get("episode_data"), dict) else {}  # NaN when the episode raised
    raw = ed.get("parsed_action") or []
    acts = [norm(a) for a in raw]
    types = [n["type"] if n else None for n in acts]
    flags = set()
    unmapped = [n["arg"] for n in acts if n and n["type"] == "open_app" and not app_resolves(n["arg"])]
    if unmapped:
        flags.add("unmapped_open_app")
    if max_run(["w" if t == "wait" else None for t in types]) >= 3:
        flags.add("wait_run3")
    if max_run([key(n) if n and n["type"] != "wait" else None for n in acts]) >= 3:
        flags.add("same_action_run3")
    if any(n is None for n in acts):
        flags.add("unparseable_step")
    last = acts[-1] if acts else None
    if ep.get("exception_info") or not ed:
        label = "exception"
    elif (ep["is_successful"] or 0) >= 1:
        label = "success"
    elif (ep["is_successful"] or 0) > 0:
        label = "partial_credit"  # composite tasks (e.g. TurnOnWifiAndOpenApp) can return 0.5
    elif last and last["type"] == "status":
        label = "infeasible_declared" if last["status"] == "infeasible" else "complete_but_failed"
    elif last and last["type"] == "answer":
        label = "answer_but_failed"
    else:
        label = "step_budget_exhausted"
    return label, sorted(flags), unmapped, sum(t == "answer" for t in types)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = []
    for f in sorted(glob.glob(os.path.join(a.run_dir, "*.pkl.gz"))):
        ep = pickle.load(gzip.open(f))  # trusted: written by our own local android_world run, never downloaded
        ep = ep[0] if isinstance(ep, list) else ep
        label, flags, unmapped, n_answer = classify(ep)
        rows.append({"task": ep["task_template"], "instance_id": ep.get("instance_id"), "label": label, "flags": flags,
                     "unmapped_apps": unmapped, "answer_actions": n_answer, "steps": ep["episode_length"]})
    fails = [r for r in rows if r["label"] != "success"]
    out = {"n": len(rows), "labels": dict(collections.Counter(r["label"] for r in rows).most_common()),
           "flags_among_failures": dict(collections.Counter(f for r in fails for f in r["flags"]).most_common()),
           "episodes_with_answer_action": sum(r["answer_actions"] > 0 for r in rows),
           "unmapped_app_names": dict(collections.Counter(x for r in rows for x in r["unmapped_apps"]).most_common(25)),
           "note": "labels are outcome descriptions, not causes; flags overlap", "episodes": rows}
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "episodes"}, indent=1))


if __name__ == "__main__":
    main()
