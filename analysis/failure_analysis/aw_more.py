import os; HERE = os.path.dirname(os.path.abspath(__file__))
import json, sys, collections
R = json.load(open(sys.argv[1]))
exec(open(HERE + "/aw_taxonomy_lib.py").read())
D = {k: v["episodes"] for k, v in R["dev"].items()}
print("ANSWER TASKS (25): answer-action episodes / answer successes / complete-instead / budget")
for k in ["lfm3vl2b_ft", "lfm3vl2b_v3", "lfm3vl2b_v4", "lfm3vl2b_v4_guards", "lfm3vl2b_v41", "lfm3vl2b_v41_guards", "lfm3vl2b_v42", "lfm3vl2b_v42_guards", "guiowl15_2b_matched"]:
    A = [e for e in D[k].values() if e["answer_task"]]
    print(f"  {k}: answered {sum(e['n_answer']>0 for e in A)}, correct {sum(e['success'] for e in A)}, completed-without-answer {sum(e['label']=='complete_but_failed' for e in A)}, budget {sum(e['label']=='step_budget_exhausted' for e in A)}, exception {sum(e['label']=='exception' for e in A)}; answered at step<=optimal: {sum(1 for e in A if e['n_answer']>0 and e['optimal_steps'] and e['steps']<=int(e['optimal_steps']))}")
S = R["sealed"]
for arm in ["v4", "guiowl"]:
    A = [e for s in [7, 1234, 2026] for e in S[f"{arm}_s{s}"]["episodes"].values() if e["answer_task"]]
    print(f"  sealed {arm}: answered {sum(e['n_answer']>0 for e in A)}/75, correct {sum(e['success'] for e in A)}, completed-without-answer {sum(e['label']=='complete_but_failed' for e in A)}, budget {sum(e['label']=='step_budget_exhausted' for e in A)}")

print("\nFORM TASKS: typed text vs goal (v4, v42)")
for k in ["lfm3vl2b_v4", "lfm3vl2b_v42"]:
    for t, e in sorted(D[k].items()):
        if any(t.startswith(p) for p in ["ExpenseAdd", "RecipeAdd", "ContactsAdd", "ContactsNew", "SimpleCalendarAdd", "MarkorCreate", "MarkorEdit", "MarkorAdd", "SimpleSmsSend", "SimpleSmsReply", "ClockTimer", "AudioRecorderRecordAudioWith"]) and not e["success"] and e["label"] != "exception":
            print(f"  [{k[-3:]}] {t} {primary(e)} steps={e['steps']} opt={e['optimal_steps']} typed={e['typed'][:6]} not_in_goal={e['typed_not_in_goal'][:4]}")
            print(f"       goal: {e['goal'][:230]!r}")

print("\nSTUCK-INTENT TAILS (v4, v42)")
for k in ["lfm3vl2b_v4", "lfm3vl2b_v42"]:
    c = collections.Counter()
    for t, e in sorted(D[k].items()):
        if primary(e) in ("budget:stuck_same_intent", "budget:stuck_wait", "budget:repeat_loop"):
            tail_t = e["types"][-6:]; tail_d = e["diffs"][-6:]
            verb = (e["intents"][-1].split() or ["?"])[0]
            c[(verb, tuple(sorted(set(tail_t))))] += 1
            print(f"  [{k[-3:]}] {t}: '{e['intents'][-1][:70]}' tail={tail_t} diffs={tail_d}")
    print(k, "tail (intent verb, action types):", c.most_common())
