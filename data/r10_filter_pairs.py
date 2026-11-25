#!/usr/bin/env python3
"""Round 10 / E-DPO (docs/PREREG_v48.md 2026-11-25 16:06): keep the E-DPO pairs whose premise the Claude judge confirms
under the owner's definition of done, then balance 1:1 (seed 49) as registered at 14:20.
  early_stop   kept if the judge says NOT_COMPLETE (stopping there really was premature)
  missed_stop  kept if the judge says COMPLETE (the goal really was met, so E should have stopped)
Usage: python r10_filter_pairs.py PAIRS_DISK VERDICTS_JSONL OUT_DISK
"""
import json
import random
import sys
from collections import Counter

from datasets import load_from_disk

pairs_dir, verdicts, out = sys.argv[1:4]
d = load_from_disk(pairs_dir)
kinds = d["kind"]
v = {}
for l in open(verdicts):
    r = json.loads(l)
    if r["verdict"] != "ERROR":
        v[r["row"]] = r["verdict"]
assert len(v) == len(d), f"verdicts for {len(v)} of {len(d)} pairs"
keep = {"early_stop": [i for i in range(len(d)) if kinds[i] == "early_stop" and v[i] == "NOT_COMPLETE"],
        "missed_stop": [i for i in range(len(d)) if kinds[i] == "missed_stop" and v[i] == "COMPLETE"]}
n = min(len(keep["early_stop"]), len(keep["missed_stop"]))
rnd = random.Random(49)
rows = sorted(rnd.sample(keep["early_stop"], n) + rnd.sample(keep["missed_stop"], n))
d.select(rows).save_to_disk(out)
stats = {"pairs_in": len(d), "verdicts": {f"{k}:{x}": c for (k, x), c in Counter((kinds[i], v[i]) for i in range(len(d))).items()},
         "kept_early": len(keep["early_stop"]), "kept_missed": len(keep["missed_stop"]), "each_after_balance": n,
         "pairs_out": len(rows)}
json.dump(stats, open(out.rstrip("/") + "_stats.json", "w"), indent=1)
print("R10_FILTER_DONE", json.dumps(stats))
