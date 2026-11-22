import collections
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


