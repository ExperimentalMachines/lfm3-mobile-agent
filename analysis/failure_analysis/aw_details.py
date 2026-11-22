import os; HERE = os.path.dirname(os.path.abspath(__file__))
import json, sys, collections, re
R = json.load(open(sys.argv[1]))
exec(open(HERE + "/aw_taxonomy_lib.py").read())
D = {k: v["episodes"] for k, v in R["dev"].items()}
mode = sys.argv[2]

if mode == "fc":  # false completes and wrong answers
    for k in ["lfm3vl2b_v4", "lfm3vl2b_v42"]:
        print("=====", k)
        for t, e in sorted(D[k].items()):
            p = primary(e)
            if p in ("false_complete", "wrong_answer", "answer_task_completed_without_answer"):
                opt = int(e["optimal_steps"]) if e["optimal_steps"] else None
                tail = list(zip(e["intents"][-3:], e["types"][-3:]))
                print(f"{p:14s} {t:42s} steps={e['steps']:2d} opt={opt} waits={e['n_wait']} sameint={e['max_same_intent_run']} ans={e['answer_texts'][:1]}")
                print("      goal:", e["goal"][:150])
                print("      tail:", tail)

if mode == "fcstats":
    rows = []
    for grp, runs in [("dev", ["lfm3vl2b_ft", "lfm3vl2b_v3", "lfm3vl2b_v4", "lfm3vl2b_v41", "lfm3vl2b_v42", "lfm3vl2b_v4_guards", "lfm3vl2b_v41_guards", "lfm3vl2b_v42_guards", "guiowl15_2b_matched"]), ("sealed", None)]:
        if grp == "sealed":
            for arm in ["v4", "guiowl", "v1"]:
                eps = [e for s in [7, 1234, 2026] for e in R["sealed"][f"{arm}_s{s}"]["episodes"].values()]
                rows.append((f"sealed:{arm}", eps))
        else:
            for k in runs:
                rows.append((k, list(D[k].values())))
    for name, eps in rows:
        term = [e for e in eps if e["last_type"] in ("status", "answer") and e["label"] != "exception"]
        good = [e for e in term if e["success"]]
        fc = [e for e in eps if e["label"] == "complete_but_failed"]
        prem = [e for e in fc if e["optimal_steps"] and e["steps"] < int(e["optimal_steps"])]
        after_loop = [e for e in fc if e["max_same_intent_run"] >= 3 or e["max_wait_run"] >= 2]
        compl = [e for e in eps if e["last_type"] == "status" and e["last_status"] == "complete" and e["label"] != "exception"]
        ans = [e for e in eps if e["last_type"] == "answer" and e["label"] != "exception"]
        print(f"{name:26s} terminated={len(term):3d} precision={len(good)}/{len(term)}={len(good)/max(1,len(term)):.2f}  "
              f"complete: {sum(e['success'] for e in compl)}/{len(compl)}  answer: {sum(e['success'] for e in ans)}/{len(ans)}  "
              f"false_complete={len(fc)} (steps<optimal {len(prem)}, after wait/intent loop {len(after_loop)})")

if mode == "fresh":  # no-effect rate of clicks that are not repeats of the previous action, success vs failure
    def fresh_stats(eps):
        c = collections.Counter()
        for e in eps:
            if e["label"] == "exception":
                continue
            # rebuild per-step no-change from counts is impossible; approximate with first click after open_app etc.
        return c
    print("needs per-step diffs; see aw_features2")

if mode == "exc":
    for grp in ["dev", "sealed"]:
        for k, v in R[grp].items():
            c = collections.Counter()
            for t, e in v["episodes"].items():
                if e["label"] == "exception":
                    x = e["exception"] or ""
                    cat = ("a11y_tree" if "a11y" in x.lower() or "accessibility" in x.lower() else
                           "grpc/adb_parse" if any(s in x for s in ["grpc", "gRPC", "fork", "ValueError", "invalid literal"]) else
                           "app_data_reset" if any(s in x.lower() for s in ["clear", "reset", "pm clear", "app data"]) else x[:70])
                    c[cat] += 1
            if c:
                print(grp, k, dict(c))
