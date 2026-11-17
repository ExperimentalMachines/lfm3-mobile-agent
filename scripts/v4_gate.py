"""v4 development gate (docs/PREREG_v4.md), computed from raw AndroidWorld episodes + offline dev metrics.

Gate (all must hold to freeze v4 and run it on sealed held-out seeds):
  (1) dev_answer: "clearly above 0" := strict typed answer match (v4_answer_check.same_answer) >= 0.20, and `answer`
      emitted on >= 50% of rows;
  (2) dev_complete: `answer` on <= 3% of action-goal final rows;
  (3) AndroidWorld seed 30: >= 3 answer-task successes AND action-task successes >= v3's - 3.
usage: python scripts/v4_gate.py --v4 results/androidworld/lfm3vl2b_v4 --v3 results/androidworld/lfm3vl2b_v3 \
         --v4_agent lfm3vl2b_v4_q4km --dev_answer <lfm3_v4_dev_answer.jsonl> --dev_complete <lfm3_v4_dev_complete.jsonl>
Input integrity: one run dir per arm, the same 116 tasks with identical goal text + instance seed as the v3 seed-30 run,
agent_name checked; dev predictions must cover exactly the pinned dev splits (results/v4_dev_reference.json) from the
expected model.
"""
import argparse
import glob
import gzip
import json
import math
import os
import pickle
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "train"))
import agent_format as af  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from v4_answer_check import same_answer  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--v4", required=True)
p.add_argument("--v3", default="results/androidworld/lfm3vl2b_v3")
p.add_argument("--dev_answer", required=True, help="predictions jsonl of the v4 model on dev_answer")
p.add_argument("--dev_complete", required=True, help="predictions jsonl of the v4 model on dev_complete")
p.add_argument("--v4_agent", required=True, help="agent_name every v4 episode must carry (e.g. lfm3vl2b_v4_q4km)")
p.add_argument("--v3_agent", default="lfm3vl2b_v3_q4km")
p.add_argument("--dev_model", default="/content/runs/lfm3vl2b-v4bmix-lora/merged", help="`model` field of the dev predictions")
p.add_argument("--dev_ref", default="results/v4_dev_reference.json",
               help="(episode_id, step_idx, gt_action) of the v4 dataset's dev splits, read from the hub at the pinned sha")
a = p.parse_args()
REF = json.load(open(a.dev_ref))
ANSWER_TASKS = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"])


def aw(run_root, agent):
    runs = glob.glob(os.path.join(run_root, "run_*"))
    if len(runs) != 1:
        raise SystemExit(f"GATE INPUT ERROR: {run_root} must contain exactly one run dir, found {len(runs)}")
    out, ident = {}, {}
    for f in glob.glob(os.path.join(runs[0], "*.pkl.gz")):
        ep = pickle.load(gzip.open(f))  # trusted: written by our own local AndroidWorld runs
        ep = ep[0] if isinstance(ep, list) else ep
        r = ep.get("is_successful")
        ok = isinstance(r, (int, float)) and not math.isnan(r) and r >= 1 and not ep.get("exception_info")
        if ep.get("agent_name") != agent:
            raise SystemExit(f"GATE INPUT ERROR: {f} agent_name {ep.get('agent_name')!r} != {agent!r}")
        t = os.path.basename(f).rsplit("_", 1)[0]
        if t in out or ep.get("task_template") != t:
            raise SystemExit(f"GATE INPUT ERROR: duplicate or mislabelled episode {f}")
        out[t] = ok
        ident[t] = (re.sub(r"\d{8}_\d{6}", "<run timestamp>", ep.get("goal") or ""), ep.get("seed"))
    return out, ident


def preds(path, split):
    rows = [json.loads(l) for l in open(path)]
    want = sorted((str(e), int(i), g) for e, i, g in REF["splits"][split])
    got = sorted((str(r["episode_id"]), int(r["step_idx"]), r["gt_action"]) for r in rows)
    if got != want or len(set(got)) != len(got):
        raise SystemExit(f"GATE INPUT ERROR: {path}: (episode_id, step_idx, gt_action) != {split} of {REF['repo']}@{REF['revision']}")
    bad = [r for r in rows if r.get("model") != a.dev_model or r.get("split", split) != split]
    if bad:
        raise SystemExit(f"GATE INPUT ERROR: {path}: {len(bad)} rows from another model/split ({bad[0].get('model')})")
    acts = [af.parse_action(r["output"], strict=True) for r in rows]  # same strict parser as the RL reward/metrics
    return rows, acts


(v4, id4), (v3, id3) = aw(a.v4, a.v4_agent), aw(a.v3, a.v3_agent)
ALL_TASKS = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"]) | set(v3)
if len(v4) != 116 or len(v3) != 116 or set(v4) != set(v3):
    raise SystemExit(f"GATE INPUT ERROR: need the same 116 tasks in both runs (v4 {len(v4)}, v3 {len(v3)})")
diff = sorted(t for t in v3 if id4[t][0] != id3[t][0]
              or (id4[t][1] is not None and id3[t][1] is not None and id4[t][1] != id3[t][1]))
if diff:  # same seed (30) => same task instance (goal text + instance seed) as the v3 run
    raise SystemExit(f"GATE INPUT ERROR: {len(diff)} tasks differ in goal/seed from the v3 seed-30 run, e.g. {diff[:3]}")
ans4 = sum(v for t, v in v4.items() if t in ANSWER_TASKS)
act4 = sum(v for t, v in v4.items() if t not in ANSWER_TASKS)
act3 = sum(v for t, v in v3.items() if t not in ANSWER_TASKS)
rows, acts = preds(a.dev_answer, "dev_answer")
emitted = sum(1 for x in acts if x and x["action_type"] == "answer") / max(1, len(acts))
correct = sum(1 for r, x in zip(rows, acts) if x and x["action_type"] == "answer"
              and same_answer(x["text"], json.loads(r["gt_action"])["text"])) / max(1, len(rows))
rows_c, acts_c = preds(a.dev_complete, "dev_complete")
false_ans = sum(1 for x in acts_c if x and x["action_type"] == "answer") / max(1, len(acts_c))
complete = sum(1 for x in acts_c if x and x["action_type"] == "status" and x.get("goal_status") == "complete") / max(1, len(acts_c))
g = {"aw_episodes_v4": len(v4), "aw_answer_task_successes_v4": ans4, "aw_action_task_successes_v4": act4,
     "aw_action_task_successes_v3": act3, "dev_answer_emitted": round(emitted, 3), "dev_answer_exact": round(correct, 3),
     "dev_complete_false_answer": round(false_ans, 3), "dev_complete_status": round(complete, 3)}
g["gate"] = {"1_answers": emitted >= 0.5 and correct >= 0.20, "2_no_false_answers": false_ans <= 0.03,
             "3_aw": len(v4) == 116 and ans4 >= 3 and act4 >= act3 - 3}
g["PASS"] = all(g["gate"].values())
print(json.dumps(g, indent=1))
sys.exit(0 if g["PASS"] else 3)
