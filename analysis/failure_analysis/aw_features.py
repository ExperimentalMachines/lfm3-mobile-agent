"""Per-episode features for AndroidWorld runs (read-only; writes only the JSON path given as argv[1]).
usage: from the repo root: .venv-aw/bin/python -I <this> <out.json>
"""
import glob, gzip, io, json, os, pickle, re, sys, collections
import numpy as np
from PIL import Image
from android_world.env import adb_utils

REPO = "/Users/alpha/lfm3-android"
os.chdir(REPO)
ANS = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"])
META = {m["task_name"]: m for m in json.load(open("data/meta/androidworld_task_metadata.json"))}
WAITY = re.compile(r"\b(wait|waiting|load|loading|loads|loaded)\b", re.I)

_GUIOWL = {"click": "click", "long_press": "long_press", "swipe": "scroll", "type": "input_text", "wait": "wait",
           "terminate": "status", "answer": "answer", "open": "open_app"}
_BUTTON = {"back": "navigate_back", "home": "navigate_home", "enter": "keyboard_enter"}


def norm(a):
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
    return (n["type"], p, str(n["arg"]))


def max_run(xs):
    best, cur, prev = 0, 0, object()
    for x in xs:
        cur = cur + 1 if (x is not None and x == prev) else 1
        if x is None:
            cur = 0
        best, prev = max(best, cur), x
    return best


def app_resolves(name):
    name = str(name or "")
    return name in adb_utils._DEFAULT_URIS or adb_utils.get_adb_activity(name) is not None or "." in name


def small(jpg):
    return np.asarray(Image.open(io.BytesIO(jpg)).convert("L").resize((72, 160)), dtype=np.float32)


def app_of(t):
    for p in ["SimpleCalendar", "SimpleSms", "SimpleDrawPro", "Markor", "Expense", "Recipe", "Files", "Contacts", "Clock",
              "System", "Browser", "Camera", "AudioRecorder", "OsmAnd", "Retro", "Vlc", "Tasks", "Notes",
              "SportsTracker", "TurnO", "OpenApp", "SaveCopyOfReceipt"]:
        if t.startswith(p):
            return {"TurnO": "System", "OpenApp": "System", "SaveCopyOfReceipt": "SimpleGallery"}.get(p, p)
    return "other"


def features(ep):
    t = ep["task_template"]
    dd = ep["episode_data"] if isinstance(ep.get("episode_data"), dict) else {}
    raw = dd.get("parsed_action") or []
    acts = [norm(a) for a in raw]
    types = [n["type"] if n else None for n in acts]
    reasons = list(dd.get("model_reasoning") or [""] * len(acts))
    intents = [(r or "").strip().splitlines()[0][:200] if (r or "").strip() else "" for r in reasons]
    exc = ep.get("exception_info")
    succ = exc is None and (lambda v: v is not None and v == v and v >= 1)(ep.get("is_successful"))
    partial = exc is None and not succ and (ep.get("is_successful") or 0) > 0
    last = acts[-1] if acts else None
    if exc is not None or not dd:
        label = "exception"
    elif succ:
        label = "success"
    elif partial:
        label = "partial_credit"
    elif last and last["type"] == "status":
        label = "infeasible_declared" if last["status"] == "infeasible" else "complete_but_failed"
    elif last and last["type"] == "answer":
        label = "answer_but_failed"
    else:
        label = "step_budget_exhausted"
    n = len(acts)
    # screen change after each action (thumbnail i+1 vs i); last step has no successor
    thumbs = dd.get("screenshot_thumb_jpg") or []
    diffs = []
    try:
        sm = [small(j) for j in thumbs]
        diffs = [float(np.abs(sm[i + 1] - sm[i]).mean()) for i in range(len(sm) - 1)]
    except Exception:
        diffs = []
    nochange = collections.Counter(); total_measured = collections.Counter()
    for i, tp in enumerate(types[:len(diffs)]):
        if tp is None:
            continue
        total_measured[tp] += 1
        if diffs[i] < 1.0:
            nochange[tp] += 1
    waits = [i for i, tp in enumerate(types) if tp == "wait"]
    wait_nonwait_intent = sum(1 for i in waits if intents[i] and not WAITY.search(intents[i]))
    same_intent_prev = sum(1 for i in range(1, n) if intents[i] and intents[i] == intents[i - 1])
    opens = [n_["arg"] for n_ in acts if n_ and n_["type"] == "open_app"]
    unmapped = [a for a in opens if not app_resolves(a)]
    typed = [str(n_["arg"]) for n_ in acts if n_ and n_["type"] == "input_text"]
    goal = ep.get("goal") or ""
    typed_not_in_goal = [x for x in typed if x and x.lower() not in goal.lower()]
    guards = [g for g in (dd.get("guard") or []) if g]
    g_rules = collections.Counter(r for g in guards for r in g.get("rules", []))
    timings = [x for x in (dd.get("timings") or []) if isinstance(x, dict)]
    usage = [x for x in (dd.get("usage") or []) if isinstance(x, dict)]
    attempts = dd.get("attempts") or []
    n_calls = sum(len(a) for a in attempts if isinstance(a, list))
    unparse = sum(1 for a in acts if a is None)
    first_bad = sum(1 for x in (dd.get("first_attempt_lenient_ok") or []) if x is False)
    return {
        "task": t, "app": app_of(t), "answer_task": t in ANS, "difficulty": META.get(t, {}).get("difficulty"),
        "optimal_steps": META.get(t, {}).get("optimal_steps"), "goal": goal,
        "success": bool(succ), "label": label, "exception": (str(exc).strip().splitlines()[-1][:200] if exc is not None and str(exc).strip() else (repr(exc)[:100] if exc is not None else None)),
        "diffs": [round(x, 2) for x in diffs],
        "is_successful": ep.get("is_successful") if ep.get("is_successful") == ep.get("is_successful") else None,
        "steps": n, "episode_length": ep.get("episode_length"),
        "types": types, "intents": intents,
        "type_counts": dict(collections.Counter(types)),
        "n_wait": len(waits), "wait_nonwait_intent": wait_nonwait_intent,
        "max_wait_run": max_run(["w" if tp == "wait" else None for tp in types]),
        "max_same_action_run": max_run([key(a) if a and a["type"] != "wait" else None for a in acts]),
        "max_same_any_run": max_run([key(a) for a in acts]),
        "max_same_intent_run": max_run([x if x else None for x in intents]),
        "same_intent_prev": same_intent_prev,
        "max_scroll_run": max_run(["s" if tp == "scroll" else None for tp in types]),
        "opens": opens, "unmapped_opens": unmapped, "first_type": types[0] if types else None,
        "typed": typed, "typed_not_in_goal": typed_not_in_goal,
        "n_answer": types.count("answer"), "answer_texts": [str(a["arg"]) for a in acts if a and a["type"] == "answer"],
        "last_type": last["type"] if last else None, "last_status": last["status"] if last else None,
        "nochange": dict(nochange), "measured": dict(total_measured),
        "guard_fires": len(guards), "guard_rules": dict(g_rules), "guard_ok": sum(1 for g in guards if g.get("ok")),
        "unparseable": unparse, "first_attempt_fail": first_bad, "n_calls": n_calls,
        "latency": [x for x in (dd.get("latency_s") or []) if isinstance(x, (int, float)) and x == x],
        "prompt_ms": [x.get("prompt_ms") for x in timings], "prompt_n": [x.get("prompt_n") for x in timings],
        "cache_n": [x.get("cache_n") for x in timings],
        "pred_ms": [x.get("predicted_ms") for x in timings], "pred_n": [x.get("predicted_n") for x in timings],
        "prompt_tokens": [x.get("prompt_tokens") for x in usage], "completion_tokens": [x.get("completion_tokens") for x in usage],
    }


def load_dir(d):
    runs = sorted(x for x in glob.glob(os.path.join(d, "run_*")) if os.path.isdir(x))
    r = runs[-1]
    out = {}
    for f in sorted(glob.glob(os.path.join(r, "*.pkl.gz"))):
        recs = pickle.loads(gzip.decompress(open(f, "rb").read()))  # trusted: written by this repo's own harness
        ep = recs[0] if isinstance(recs, list) else recs
        out[ep["task_template"]] = features(ep)
    return r, out


DEV = ["lfm3vl2b_ft", "lfm3vl2b_v2", "lfm3vl2b_v3", "lfm3vl2b_v4", "lfm3vl2b_v4_guards", "lfm3vl2b_v41",
       "lfm3vl2b_v41_guards", "lfm3vl2b_v42", "lfm3vl2b_v42_guards", "guiowl15_2b_matched", "lfm3vl2b_v4_rerun"]
res = {"dev": {}, "sealed": {}}
for d in DEV:
    r, eps = load_dir(f"results/androidworld/{d}")
    res["dev"][d] = {"run_dir": r, "episodes": eps}
    print(d, r, len(eps), sum(e["success"] for e in eps.values()), file=sys.stderr)
for arm in ["v4", "guiowl", "v1"]:
    for s in [7, 1234, 2026]:
        r, eps = load_dir(f"results/androidworld_sealed/{arm}_seed{s}")
        rr = f"results/androidworld_sealed/{arm}_seed{s}_rerun"
        subst = []
        if os.path.isdir(rr):
            r2, eps2 = load_dir(rr)
            for t, e2 in eps2.items():
                if t in eps and eps[t]["label"] == "exception":  # preregistered single re-run of setup crashes
                    eps[t] = e2; subst.append(t)
        res["sealed"][f"{arm}_s{s}"] = {"run_dir": r, "episodes": eps, "reruns_substituted": subst}
        print(arm, s, len(eps), sum(e["success"] for e in eps.values()), len(subst), file=sys.stderr)
json.dump(res, open(sys.argv[1], "w"))
