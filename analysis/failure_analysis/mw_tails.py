import os; HERE = os.path.dirname(os.path.abspath(__file__))
import json, os, re, sys, collections
sys.argv = ["x"]
src = open(HERE + "/mw_compare.py").read().split("stats = {}")[0]
exec(src)
for run in ["v4_gui_en_r2", "guiowl_gui_en_r2"]:
    c = collections.Counter(); first_stuck = []
    for t in TASKS:
        steps, res = load(run, t)
        if not steps or res is None or res[0] is None or res[0] >= 1: continue
        it = [intent(s.get("prediction")) for s in steps]; ty = [atype(s) for s in steps]
        if len(steps) >= 50:
            tail_i = it[-10:]; tail_t = ty[-10:]
            if len(set(tail_i)) == 1: cat = "same_intent_last10"
            elif all(x == "wait" for x in tail_t): cat = "all_wait_last10"
            elif len(set(tail_i)) <= 2: cat = "two_intents_last10"
            else: cat = "varied"
            c["budget:" + cat] += 1
            # first step from which intent never changes
            j = len(it) - 1
            while j > 0 and it[j - 1] == it[-1]: j -= 1
            first_stuck.append(j)
        else:
            c["self_ended:" + ty[-1]] += 1
    print(run, dict(c.most_common()))
    if first_stuck:
        fs = sorted(first_stuck); print("   budget episodes: step at which final intent loop starts, median", fs[len(fs)//2], "p25", fs[len(fs)//4], "p75", fs[3*len(fs)//4], "; steps wasted in final loop (median)", 50 - fs[len(fs)//2])
