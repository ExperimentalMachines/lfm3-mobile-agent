"""v4 development gate (docs/PREREG_v4.md), computed from raw AndroidWorld episodes + offline dev metrics.

Gate (all must hold to freeze v4 and run it on sealed held-out seeds):
  (1) dev_answer: "clearly above 0" := strict typed answer match (v4_answer_check.same_answer) >= 0.20, and `answer`
      emitted on >= 50% of rows;
  (2) dev_complete: `answer` on <= 3% of action-goal final rows;
  (3) AndroidWorld seed 30: >= 3 answer-task successes AND action-task successes >= v3's - 3.
usage: python scripts/v4_gate.py --v4 results/androidworld/lfm3vl2b_v4 --v3 results/androidworld/lfm3vl2b_v3 \
         --dev_answer <metrics.json+jsonl prefix> --dev_complete <...>
"""
import argparse
import glob
import gzip
import json
import math
import os
import pickle
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
p.add_argument("--n_answer", type=int, required=True, help="rows in the v4 dataset's dev_answer split")
p.add_argument("--n_complete", type=int, required=True, help="rows in the v4 dataset's dev_complete split")
a = p.parse_args()
ANSWER_TASKS = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"])


def aw(run_root):
    runs = glob.glob(os.path.join(run_root, "run_*"))
    if len(runs) != 1:
        raise SystemExit(f"GATE INPUT ERROR: {run_root} must contain exactly one run dir, found {len(runs)}")
    out = {}
    for f in glob.glob(os.path.join(runs[0], "*.pkl.gz")):
        ep = pickle.load(gzip.open(f))  # trusted: written by our own local AndroidWorld runs
        ep = ep[0] if isinstance(ep, list) else ep
        r = ep.get("is_successful")
        ok = isinstance(r, (int, float)) and not math.isnan(r) and r >= 1 and not ep.get("exception_info")
        out[os.path.basename(f).rsplit("_", 1)[0]] = ok
    return out


def preds(path, expect_n):
    rows = [json.loads(l) for l in open(path)]
    if len(rows) != expect_n or len({(r["episode_id"], r["step_idx"]) for r in rows}) != expect_n:
        raise SystemExit(f"GATE INPUT ERROR: {path} has {len(rows)} rows, expected {expect_n} unique")
    acts = [af.parse_action(r["output"]) for r in rows]
    return rows, acts


v4, v3 = aw(a.v4), aw(a.v3)
ALL_TASKS = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"]) | set(v3)
if len(v4) != 116 or len(v3) != 116 or set(v4) != set(v3):
    raise SystemExit(f"GATE INPUT ERROR: need the same 116 tasks in both runs (v4 {len(v4)}, v3 {len(v3)})")
ans4 = sum(v for t, v in v4.items() if t in ANSWER_TASKS)
act4 = sum(v for t, v in v4.items() if t not in ANSWER_TASKS)
act3 = sum(v for t, v in v3.items() if t not in ANSWER_TASKS)
rows, acts = preds(a.dev_answer, a.n_answer)
emitted = sum(1 for x in acts if x and x["action_type"] == "answer") / max(1, len(acts))
correct = sum(1 for r, x in zip(rows, acts) if x and x["action_type"] == "answer"
              and same_answer(x["text"], json.loads(r["gt_action"])["text"])) / max(1, len(rows))
rows_c, acts_c = preds(a.dev_complete, a.n_complete)
false_ans = sum(1 for x in acts_c if x and x["action_type"] == "answer") / max(1, len(acts_c))
complete = sum(1 for x in acts_c if x and x["action_type"] == "status") / max(1, len(acts_c))
g = {"aw_episodes_v4": len(v4), "aw_answer_task_successes_v4": ans4, "aw_action_task_successes_v4": act4,
     "aw_action_task_successes_v3": act3, "dev_answer_emitted": round(emitted, 3), "dev_answer_exact": round(correct, 3),
     "dev_complete_false_answer": round(false_ans, 3), "dev_complete_status": round(complete, 3)}
g["gate"] = {"1_answers": emitted >= 0.5 and correct >= 0.20, "2_no_false_answers": false_ans <= 0.03,
             "3_aw": len(v4) == 116 and ans4 >= 3 and act4 >= act3 - 3}
g["PASS"] = all(g["gate"].values())
print(json.dumps(g, indent=1))
sys.exit(0 if g["PASS"] else 3)
