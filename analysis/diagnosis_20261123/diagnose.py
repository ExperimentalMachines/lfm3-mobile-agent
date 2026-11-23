"""Vision vs planning vs sequence (2026-11-23). Reads committed results only.

  python3 -I analysis/diagnosis_20261123/diagnose.py [aw_features.json]
1. AndroidControl test, v4 (results/v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft.jsonl): every non-terminal step is scored
   twice, with the step instruction (low-level) and without (high-level). Right only with the instruction = the model
   can execute but chose the wrong next step (planning); wrong even with it = execution, split into wrong type,
   wrong place (grounding) and wrong text / direction / app.
2. The same file by step index: high-level accuracy and the rate of a wrong `status` (early stop).
3. AndroidWorld held-out (needs aw_features.json from analysis/failure_analysis/aw_features.py, run with the
   AndroidWorld venv): success and false `complete` by the task's optimal step count, v4 vs GUI-Owl.
"""
import collections, json, math, os, statistics as st, sys
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(R, "train")); sys.path.insert(0, os.path.join(R, "eval", "androidcontrol"))
import agent_format as af  # noqa: E402
from score import match  # noqa: E402

rows = [json.loads(l) for l in open(os.path.join(R, "results/v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft.jsonl"))]
by = collections.defaultdict(dict)
idx = collections.defaultdict(lambda: [0, 0, 0])
for r in rows:
    if r["is_terminal"]:
        continue
    gt = json.loads(r["gt_action"]); bb = json.loads(r["gt_bbox"]) if r["gt_bbox"] else None
    p = af.parse_action(r["output"].split("</think>")[-1])
    t_ok, s_ok = match(p, gt, bb)
    d = None
    if p and gt["action_type"] in af.POINT_TYPES and p["action_type"] == gt["action_type"]:
        d = math.hypot((p["point_2d"][0] - gt["point_2d"][0]) / 1000, (p["point_2d"][1] - gt["point_2d"][1]) / 1000)
    by[(r["episode_id"], r["step_idx"])][r["mode"]] = dict(t=t_ok, s=s_ok, gt=gt["action_type"], d=d)
    if r["mode"] == "high":
        k = min(r["step_idx"], 8) // 2 * 2
        idx[k][0] += 1; idx[k][1] += s_ok; idx[k][2] += bool(p and p["action_type"] == "status")
pairs = [v for v in by.values() if "high" in v and "low" in v]
out = {"ac_pairs": len(pairs)}
c = collections.Counter(("H" if v["high"]["s"] else "h") + ("L" if v["low"]["s"] else "l") for v in pairs)
out["both_right"], out["right_only_with_instruction"] = c["HL"], c["hL"]
out["wrong_even_with_instruction"], out["right_only_without"] = c["hl"], c["Hl"]
low_err = collections.Counter()
for v in pairs:
    if not v["low"]["s"]:
        lo = v["low"]
        low_err["wrong_place" if lo["t"] and lo["gt"] in af.POINT_TYPES else ("wrong_content" if lo["t"] else "wrong_type")] += 1
out["low_level_errors"] = dict(low_err)
ds = sorted(v["low"]["d"] for v in pairs if not v["low"]["s"] and v["low"]["t"] and v["low"]["d"] is not None)
out["low_level_miss_distance_median"] = round(ds[len(ds) // 2], 3)
out["high_level_by_step_index"] = {f"{k}-{k + 1 if k < 8 else '+'}": {"n": n, "acc": round(s / n, 3), "early_status": round(e / n, 3)}
                                   for k, (n, s, e) in sorted(idx.items())}
L = collections.Counter(r["episode_id"] for r in rows if r["mode"] == "high")
lens = sorted(L.values())
out["ac_test_episode_steps"] = {"median": st.median(lens), "p90": lens[int(.9 * len(lens))],
                                "share_over_8": round(sum(x > 8 for x in lens) / len(lens), 3)}
if len(sys.argv) > 1:
    d = json.load(open(sys.argv[1]))
    def opt(e):
        try: return int(e["optimal_steps"])
        except Exception: return None
    aw = {}
    for name, arms in (("v4", ["v4_s7", "v4_s1234", "v4_s2026"]), ("guiowl", ["guiowl_s7", "guiowl_s1234", "guiowl_s2026"])):
        b = collections.defaultdict(lambda: [0, 0, 0]); fc_steps = []
        for a in arms:
            for e in d["sealed"][a]["episodes"].values():
                if e["label"] == "exception" or opt(e) is None:
                    continue
                o = opt(e); k = "1-3" if o <= 3 else "4-6" if o <= 6 else "7-10" if o <= 10 else "11+"
                fc = e["label"] == "complete_but_failed" and not e["answer_task"]
                b[k][0] += 1; b[k][1] += e["success"]; b[k][2] += fc
                if fc: fc_steps.append(e["steps"] / o)
        aw[name] = {k: {"n": v[0], "solved": round(v[1] / v[0], 3), "false_complete": round(v[2] / v[0], 3)} for k, v in b.items()}
        aw[name]["false_complete_before_optimal_steps"] = sum(x < 1 for x in fc_steps)
        aw[name]["false_complete_n"] = len(fc_steps)
    out["androidworld_heldout_by_optimal_steps"] = aw
print(json.dumps(out, indent=1))
