#!/usr/bin/env python3
"""Round 9 candidate F's fixed 32,000-row mix (docs/PREREG_v47.md): every nwait / nwaitload counterfactual row, every
relabelled wait row, and the rest drawn uniformly from the v4.7 train split. Seed 47.
Usage: python v47_cont_mix.py ~/r9mix/disk/train ~/r9mix/relabelled_rows.json ~/r9mix/disk/train_f"""
import json
import random
import sys

from datasets import load_from_disk

N = 32000
ds = load_from_disk(sys.argv[1])
rel = {(x["source"], str(x["episode_id"]), int(x["step_idx"])) for x in json.load(open(sys.argv[2]))}
must, rest = [], []
for i, (s, e, t) in enumerate(zip(ds["source"], ds["episode_id"], ds["step_idx"])):
    e = str(e)
    if "#cf_nwait" in e or ("#" not in e and (s, e, int(t)) in rel):
        must.append(i)
    else:
        rest.append(i)
rnd = random.Random(47)
pick = must + rnd.sample(rest, N - len(must))
rnd.shuffle(pick)
out = ds.select(pick).flatten_indices()
out.save_to_disk(sys.argv[3])
print(json.dumps({"rows": len(out), "counterfactual_and_relabelled": len(must), "replay": N - len(must)}))
