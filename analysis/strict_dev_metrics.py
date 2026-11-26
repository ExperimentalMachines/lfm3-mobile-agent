"""Strict metrics on v4 dev predictions (generate.py jsonl): dev_answer -> answer emitted / strict typed match
(data/v4_answer_check.same_answer); dev_complete -> false `answer` rate / `status complete` rate.
usage: python strict_dev_metrics.py --answer <dev_answer.jsonl> --complete <dev_complete.jsonl> --out <json>"""
import argparse, json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
for d in (here, os.path.join(here, "..", "train"), os.path.join(here, "..", "data")):
    sys.path.insert(0, d)
import agent_format as af  # noqa: E402
from sft_main_answer_check import exact_answer, same_answer  # noqa: E402
p = argparse.ArgumentParser(); p.add_argument("--answer", required=True); p.add_argument("--complete", required=True)
p.add_argument("--out", required=True); a = p.parse_args()
A = [json.loads(l) for l in open(a.answer)]; C = [json.loads(l) for l in open(a.complete)]
assert A and C, "empty prediction file"
pa = [af.parse_action(r["output"], strict=True) for r in A]; pc = [af.parse_action(r["output"], strict=True) for r in C]
m = {"n_answer": len(A), "n_complete": len(C),
     "answer_emitted": sum(1 for x in pa if x and x["action_type"] == "answer") / max(1, len(A)),
     "answer_exact_strict": sum(1 for r, x in zip(A, pa) if x and x["action_type"] == "answer"
                                and same_answer(x["text"], json.loads(r["gt_action"])["text"])) / max(1, len(A)),
     "complete_false_answer": sum(1 for x in pc if x and x["action_type"] == "answer") / max(1, len(C)),
     "complete_status": sum(1 for x in pc if x and x["action_type"] == "status" and x.get("goal_status") == "complete") / max(1, len(C)),
     "answer_exact_normalised": sum(1 for r, x in zip(A, pa) if x and x["action_type"] == "answer"
                                    and exact_answer(x["text"], json.loads(r["gt_action"])["text"])) / max(1, len(A))}
json.dump(m, open(a.out, "w"), indent=1); print(json.dumps(m))
