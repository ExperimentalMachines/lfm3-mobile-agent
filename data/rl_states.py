"""RL state pool for the static-screenshot GRPO pilot (Codex research rank 1), drawn ONLY from the built v4 train split.

2,000 single-screenshot states, prompts exactly as in v4 SFT (system + user messages), gold action as reward metadata:
  700 qa_final    : final rows of navigate-then-answer copies (answer; strict typed match)   [one per episode]
  500 complete    : final rows of original AndroidControl action episodes (status complete)
  300 other       : open_app / input_text / scroll / navigate_* / keyboard_enter / wait
  500 click       : click / long_press (dense distance reward)
No dev episodes (they are not in v4 train), no ScreenQA. Deterministic (seed 4). Pushed as a private dataset.
usage: python data/rl_states.py --v4_out data/v4work/build/out --repo experimentalmachines/MobileAgent-RL [--dry_run]
"""
import argparse
import glob
import json
import os
import random

import pyarrow.parquet as pq
from datasets import Dataset, Features, Image, Sequence, Value

p = argparse.ArgumentParser()
p.add_argument("--v4_out", required=True)
p.add_argument("--repo", default="experimentalmachines/MobileAgent-RL")
p.add_argument("--dry_run", action="store_true")
a = p.parse_args()
QUOTA = {"qa_final": 700, "complete": 500, "other": 300, "click": 500}
rnd = random.Random(4)
buckets = {k: [] for k in QUOTA}
seen_final = set()
for f in sorted(glob.glob(os.path.join(a.v4_out, "data/train-*.parquet"))):
    t = pq.read_table(f, columns=["source", "episode_id", "gt_action", "is_terminal", "img_sha"]).to_pylist()
    for i, r in enumerate(t):
        if r["source"] == "screenqa":
            continue
        g = json.loads(r["gt_action"])
        typ = g["action_type"]
        if r["episode_id"].endswith("#qa") and typ == "answer":
            if r["episode_id"] in seen_final:  # final answer rows are duplicated for SFT weighting; one per episode here
                continue
            seen_final.add(r["episode_id"])
            buckets["qa_final"].append((f, i))
        elif r["episode_id"].endswith("#qa"):
            continue  # prefix rows of question copies duplicate original states
        elif typ == "status":
            buckets["complete"].append((f, i))
        elif typ in ("click", "long_press"):
            buckets["click"].append((f, i))
        elif typ != "answer":
            buckets["other"].append((f, i))
pick = {}
for k, n in QUOTA.items():
    rnd.shuffle(buckets[k])
    for f, i in buckets[k][:n]:
        pick.setdefault(f, []).append((i, k))
    print(k, "available", len(buckets[k]), "picked", min(n, len(buckets[k])), flush=True)
rows = {"image": [], "prompt": [], "gt_action": [], "kind": [], "episode_id": []}
for f, items in pick.items():
    t = pq.read_table(f, columns=["images", "messages", "gt_action", "episode_id"])
    msgs, imgs, gts, eps = (t.column(c).to_pylist() for c in ("messages", "images", "gt_action", "episode_id"))
    for i, k in items:
        m = msgs[i]
        assert m[0]["role"] == "system" and m[1]["role"] == "user" and "\nInstalled apps: " in m[1]["content"]
        rows["image"].append({"bytes": imgs[i][0]["bytes"], "path": None})
        rows["prompt"].append([{"role": "system", "content": m[0]["content"]}, {"role": "user", "content": m[1]["content"]}])
        rows["gt_action"].append(gts[i])
        rows["kind"].append(k)
        rows["episode_id"].append(eps[i])
feat = Features({"image": Image(), "prompt": [{"role": Value("string"), "content": Value("string")}],
                 "gt_action": Value("string"), "kind": Value("string"), "episode_id": Value("string")})
ds = Dataset.from_dict(rows, features=feat).shuffle(seed=4)
print(ds, {k: rows["kind"].count(k) for k in QUOTA}, flush=True)
if a.dry_run:
    raise SystemExit(0)
ds.push_to_hub(a.repo, private=True)
from huggingface_hub import HfApi  # noqa: E402

print("pushed", a.repo, HfApi().dataset_info(a.repo).sha, flush=True)
