"""Audit of the training split's `wait` steps (round 9, "fix the waits"). For each `wait` row of an episode (not the
counterfactual or question copies), using the row's position in its episode (its last history line number):
  noop      the next screen of the episode is unchanged (train/screen_change.py)        -> the wait did nothing
  trailing  the next row is the episode's final `status` row                           -> waited after the task was done
  changed   the next screen changed (loading finished, toast vanished, an ad, ...)
  no_next   the next step's screen is not in the data
Prints counts per source and writes samples per group (keys) for review by eye.
Usage: python wait_audit.py <train parquet dir | datasets save_to_disk dir> <out.json>
"""
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "train"))
import screen_change as sc  # noqa: E402

HB = re.compile(r"\nPrevious steps:\n(.*?)\nWhat is the next action\?$", re.S)
LINE = re.compile(r"^(\d+)\. ")
DISK = os.path.exists(os.path.join(sys.argv[1], "dataset_info.json"))
if DISK:
    from datasets import Image as HFImage, Sequence, load_from_disk
    DS = load_from_disk(sys.argv[1])
    files = ["disk"]
else:
    files = sorted(glob.glob(os.path.join(sys.argv[1], "train-*.parquet")))
eps = defaultdict(dict)  # (source, episode) -> {position: (file, row, action_type)}
for fi, f in enumerate(files):
    t = DS.select_columns(["messages", "source", "episode_id", "gt_action"]).to_list() if DISK else \
        pq.read_table(f, columns=["messages", "source", "episode_id", "gt_action"]).to_pylist()
    for ri, r in enumerate(t):
        e = str(r["episode_id"])
        if "#" in e or r["source"] == "screenqa":
            continue
        nums = [int(m.group(1)) for m in map(LINE.match, HB.search(r["messages"][1]["content"]).group(1).split("\n")) if m]
        pos = nums[-1] if nums else 0
        eps[(r["source"], e)].setdefault(pos, (fi, ri, json.loads(r["gt_action"])["action_type"]))
need = set()
waits = []
for k, d in eps.items():
    for p, (fi, ri, typ) in d.items():
        if typ != "wait":
            continue
        nxt = d.get(p + 1)
        waits.append((k, p, nxt))
        if nxt:
            need.add((fi, ri)); need.add(nxt[:2])
by_file = defaultdict(set)
for fi, ri in need:
    by_file[fi].add(ri)
img = {}
for fi, rows in by_file.items():
    if DISK:
        raw = DS.cast_column("images", Sequence(HFImage(decode=False))).select_columns(["images"])
        for ri in rows:
            img[(fi, ri)] = sc.prep(raw[ri]["images"][0]["bytes"])
        continue
    col = pq.read_table(files[fi], columns=["images"]).column("images").to_pylist()
    for ri in rows:
        img[(fi, ri)] = sc.prep(col[ri][0]["bytes"])
cnt = Counter()
samples = defaultdict(list)
for (src, e), p, nxt in waits:
    if not nxt:
        g = "no_next"
    elif nxt[2] == "status":
        g = "trailing"
    else:
        fi, ri, _ = eps[(src, e)][p]
        g = "changed" if sc.changed(img[(fi, ri)], img[nxt[:2]]) else "noop"
    cnt[(src, g)] += 1
    if len(samples[g]) < 400:
        samples[g].append({"source": src, "episode_id": e, "position": p})
print(json.dumps(sorted(((f"{s}:{g}", n) for (s, g), n in cnt.items()))))
json.dump({"counts": {f"{s}:{g}": n for (s, g), n in cnt.items()}, "samples": samples}, open(sys.argv[2], "w"), indent=0)
