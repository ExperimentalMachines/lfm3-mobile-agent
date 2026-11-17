"""Score generate.py output on a v2 dev split (gt_action is stored on every row; no external GT file needed).

usage: python score_dev.py preds.jsonl --expect_n N --out metrics.json
Uses score.match / score.score_rows unchanged (click within 0.14 of the GT point; text/answer: normalized exact or
token-F1 >= 0.5; scroll/status exact). Also reports mean token-F1 for `answer` rows (ScreenQA-style).
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score  # noqa: E402
import agent_format as af  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("preds")
ap.add_argument("--expect_n", type=int, required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
rows = [json.loads(l) for l in open(a.preds)]
seen = {(r["episode_id"], r["step_idx"]) for r in rows}
complete = len(seen) == a.expect_n == len(rows)
m = score.score_rows(rows)
f1 = [score._f1((af.parse_action(r["output"]) or {}).get("text") if (af.parse_action(r["output"]) or {}).get("action_type") == "answer" else "",
                json.loads(r["gt_action"])["text"]) for r in rows if json.loads(r["gt_action"])["action_type"] == "answer"]
m["answer_mean_f1"] = sum(f1) / len(f1) if f1 else None
m["integrity"] = {"complete": complete, "n_rows": len(rows), "expected": a.expect_n, "model": rows[0].get("model") if rows else None}
json.dump(m, open(a.out, "w"), indent=1)
print(json.dumps({k: m[k] for k in ("n_steps", "parse_rate", "type_match", "step_sr", "answer_mean_f1")}))
sys.exit(0 if complete else 1)
