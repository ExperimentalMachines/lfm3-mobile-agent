#!/usr/bin/env python3
"""Round 14 matched control (docs/preregistrations/round-14-own-history-vs-control.md; external review recommendation 5): SFT mix of E's own-history
divergence rows (train/semi_online_rl.py --collect: every step where E's greedy action failed the strict matcher on the
same 400 episodes / windows as the RL arm, labelled with the human's action) + uniform replay from E's training split,
to N rows (100 steps x 32). Seed 14.
Usage: python ownhistory_sft_mix.py --div DIV_DISK --out OUT [--n 3200]"""
import argparse
import json
import random
from collections import Counter

from datasets import Dataset, concatenate_datasets, load_dataset, load_from_disk
from huggingface_hub import HfApi

REPO, REV = "experimentalmachines/MobileAgent-SFT-Counterfactual", "0ace5559e6c0b808a5ddf4e4ce9831d1d3614471"
ap = argparse.ArgumentParser()
ap.add_argument("--div", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--n", type=int, default=3200)
ap.add_argument("--shards", type=int, default=0)
a = ap.parse_args()
div = load_from_disk(a.div)
files = sorted(f for f in HfApi().list_repo_files(REPO, repo_type="dataset", revision=REV) if f.startswith("data/train-"))
train = load_dataset(REPO, data_files={"train": files[: a.shards or None]}, split="train", revision=REV)
train = train.select_columns(["images", "messages"])
_mf = train.features["messages"]
keys = list((_mf[0] if isinstance(_mf, list) else _mf.feature).keys())  # the replay rows' message fields
rows = []
for r in div:
    msgs = [{k: m.get(k) for k in keys} for m in r["messages"]]
    rows.append({"images": r["images"], "messages": msgs})
dv = Dataset.from_list(rows, features=train.features)
n_rep = max(0, a.n - len(dv))
rep = train.select(sorted(random.Random(14).sample(range(len(train)), n_rep)))
mix = concatenate_datasets([dv, rep]).shuffle(seed=14).flatten_indices()
mix.save_to_disk(a.out)
st = {"divergence_rows": len(dv), "kinds": dict(Counter(div["kind"])), "replay_rows": n_rep, "mix_rows": len(mix)}
json.dump(st, open(a.out + "_stats.json", "w"), indent=1)
print("R14_SFT_MIX_DONE", json.dumps(st), flush=True)
