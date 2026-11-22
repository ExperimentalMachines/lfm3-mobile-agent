"""Failure taxonomy + step-level behaviour stats from aw_features.json. usage: python3 -I <this> aw_features.json"""
import json, sys, collections, statistics as st

R = json.load(open(sys.argv[1]))
EXPECTED_APP = {"SimpleCalendar": ["calendar"], "Markor": ["markor"], "Expense": ["expense"], "Recipe": ["broccoli"],
                "Files": ["files"], "Contacts": ["contacts"], "Clock": ["clock"], "System": ["settings"],
                "Camera": ["camera"], "AudioRecorder": ["audio recorder"], "OsmAnd": ["osmand"], "Retro": ["retro"],
                "Vlc": ["vlc"], "Tasks": ["tasks"], "Notes": ["joplin"], "SportsTracker": ["opentracks", "open tracks"],
                "SimpleSms": ["sms", "messag"], "SimpleDrawPro": ["draw"], "SimpleGallery": ["gallery"]}


def tail_class(e, k=5):
    ty, it = e["types"][-k:], e["intents"][-k:]
    if len(ty) < k:
        return "short"
    if all(t == "wait" for t in ty):
        return "stuck_wait"
    nonwait = [t for t in ty if t != "wait"]
    # same non-wait action repeated (any wait interleaved) -> repeat loop; use intents as proxy for same target
    if len(set(it)) == 1 and it[0]:
        return "stuck_same_intent"
    if sum(t == "scroll" for t in ty) >= 3:
        return "scroll_heavy"
    if e["max_same_any_run"] >= 3 and e["max_same_any_run"] >= 0.3 * e["steps"]:
        return "repeat_loop"
    return "wandering"


def primary(e):
    if e["success"]:
        return "success"
    L = e["label"]
    if L == "exception":
        return "infra_exception"
    if L == "partial_credit":
        return "partial_credit"
    if L == "complete_but_failed":
        return "answer_task_completed_without_answer" if e["answer_task"] else "false_complete"
    if L == "answer_but_failed":
        return "wrong_answer" if e["answer_task"] else "answer_on_action_task"
    if L == "infeasible_declared":
        return "declared_infeasible"
    return "budget:" + tail_class(e)


def flags(e):
    f = set()
    if e["max_wait_run"] >= 3: f.add("wait_run3")
    if e["wait_nonwait_intent"] >= 1: f.add("wait_under_nonwait_intent")
    if e["max_same_action_run"] >= 3: f.add("same_action_run3")
    if e["max_same_intent_run"] >= 4: f.add("same_intent_run4")
    if e["unmapped_opens"]: f.add("unmapped_open_app")
    if e["typed_not_in_goal"]: f.add("typed_text_not_in_goal")
    if e["nochange"].get("click", 0) >= 3: f.add("noeffect_clicks3")
    if e["answer_task"] and e["n_answer"] == 0: f.add("answer_task_no_answer_action")
    if not e["answer_task"] and e["n_answer"] > 0: f.add("answer_on_action_task")
    if e["unparseable"]: f.add("unparseable_step")
    exp = EXPECTED_APP.get(e["app"])
    if exp and e["opens"] and not any(any(x in str(o).lower() for x in exp) for o in e["opens"]):
        f.add("never_opened_expected_app")
    if exp and not e["opens"]: f.add("no_open_app")
    return f


def runstats(eps):
    eps = list(eps.values())
    steps = sum(e["steps"] for e in eps)
    tc = collections.Counter()
    for e in eps:
        tc.update({k: v for k, v in e["type_counts"].items()})
    waits = sum(e["n_wait"] for e in eps)
    wn = sum(e["wait_nonwait_intent"] for e in eps)
    sp = sum(e["same_intent_prev"] for e in eps)
    nc = collections.Counter(); ms = collections.Counter()
    for e in eps:
        nc.update(e["nochange"]); ms.update(e["measured"])
    prim = collections.Counter(primary(e) for e in eps)
    fl = collections.Counter(x for e in eps if not e["success"] for x in flags(e))
    return {"n": len(eps), "succ": sum(e["success"] for e in eps), "steps": steps,
            "type_share": {k: round(v / steps, 3) for k, v in tc.most_common()},
            "type_counts": dict(tc.most_common()),
            "wait_share": round(waits / steps, 3) if steps else None, "waits": waits, "wait_nonwait_intent": wn,
            "same_intent_as_prev_share": round(sp / max(1, steps - len(eps)), 3),
            "noeffect_rate": {k: (nc[k], ms[k], round(nc[k] / ms[k], 3)) for k in ["click", "input_text", "scroll", "wait", "open_app", "navigate_back", "long_press"] if ms[k]},
            "primary": dict(prim.most_common()), "flags_among_failures": dict(fl.most_common()),
            "answer_tasks_with_answer_action": sum(1 for e in eps if e["answer_task"] and e["n_answer"] > 0),
            "action_tasks_with_answer_action": sum(1 for e in eps if not e["answer_task"] and e["n_answer"] > 0),
            "unparseable_steps": sum(e["unparseable"] for e in eps),
            "guard_fires": sum(e["guard_fires"] for e in eps),
            "guard_rules": dict(sum((collections.Counter(e["guard_rules"]) for e in eps), collections.Counter())),
            "budget_exhausted": sum(e["label"] == "step_budget_exhausted" for e in eps),
            }


out = {}
for grp in ["dev", "sealed"]:
    for name, v in R[grp].items():
        if name == "lfm3vl2b_v4_rerun":
            continue
        out[f"{grp}:{name}"] = runstats(v["episodes"])
# pooled sealed per arm
for arm in ["v4", "guiowl", "v1"]:
    pooled = {}
    for s in [7, 1234, 2026]:
        for t, e in R["sealed"][f"{arm}_s{s}"]["episodes"].items():
            pooled[f"{t}@{s}"] = e
    out[f"sealed_pooled:{arm}"] = runstats(pooled)
json.dump(out, open(sys.argv[1].replace("aw_features.json", "aw_taxonomy.json"), "w"), indent=1)

order = ["dev:lfm3vl2b_ft", "dev:lfm3vl2b_v2", "dev:lfm3vl2b_v3", "dev:lfm3vl2b_v4", "dev:lfm3vl2b_v4_guards",
         "dev:lfm3vl2b_v41", "dev:lfm3vl2b_v41_guards", "dev:lfm3vl2b_v42", "dev:lfm3vl2b_v42_guards",
         "dev:guiowl15_2b_matched", "sealed_pooled:v4", "sealed_pooled:guiowl", "sealed_pooled:v1"]
cats = sorted({c for k in order for c in out[k]["primary"]})
print("PRIMARY", "\t".join(k.split(":")[1] for k in order))
for c in cats:
    print(c, "\t".join(str(out[k]["primary"].get(c, 0)) for k in order))
fl = sorted({c for k in order for c in out[k]["flags_among_failures"]})
print("\nFLAGS among failures")
for c in fl:
    print(c, "\t".join(str(out[k]["flags_among_failures"].get(c, 0)) for k in order))
print("\nSTEP STATS")
for k in order:
    o = out[k]
    print(k, "succ", o["succ"], "steps", o["steps"], "wait_share", o["wait_share"], "waits", o["waits"], "wait_nonwait", o["wait_nonwait_intent"],
          "sameintent", o["same_intent_as_prev_share"], "budget", o["budget_exhausted"], "unparse", o["unparseable_steps"],
          "ans_on_ans", o["answer_tasks_with_answer_action"], "ans_on_act", o["action_tasks_with_answer_action"],
          "guard", o["guard_fires"], o["guard_rules"])
    print("   types", o["type_share"])
    print("   noeffect", o["noeffect_rate"])
