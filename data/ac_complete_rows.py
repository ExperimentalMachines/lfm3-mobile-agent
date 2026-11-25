#!/usr/bin/env python3
"""Every real AndroidControl `status complete` row of E's training split (MobileAgent-SFT-v4.6 @ 0ace5559, train), for
the Claude completion labels (docs/PREREG_v48.md 2026-11-25 16:25). Streams one shard at a time (download, keep the rows,
delete the shard), resumable per shard.
Out: OUT/rows/train-XXXXX.parquet (episode_id, step_idx, user, jpg) and OUT/variants.jsonl (the `#cf_short` variants:
their id and the source row they copy).
Usage: python ac_complete_rows.py OUT
"""
import json
import os
import shutil
import sys

import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import HfApi, hf_hub_download

REPO, REV = "experimentalmachines/MobileAgent-SFT-v4.6", "0ace5559e6c0b808a5ddf4e4ce9831d1d3614471"
out = sys.argv[1]
os.makedirs(f"{out}/rows", exist_ok=True)
shards = sorted(f for f in HfApi().list_repo_files(REPO, repo_type="dataset", revision=REV) if f.startswith("data/train-"))
total = 0
for sh in shards:
    dst = f"{out}/rows/{os.path.basename(sh)}"
    if os.path.exists(dst):
        total += pq.read_metadata(dst).num_rows
        continue
    p = hf_hub_download(REPO, sh, repo_type="dataset", revision=REV, local_dir=f"{out}/dl")
    t = pq.read_table(p, columns=["source", "gt_action", "episode_id", "step_idx", "messages", "images"])
    keep, var = {"episode_id": [], "step_idx": [], "user": [], "jpg": []}, []
    for r in t.to_pylist():
        if r["source"] != "androidcontrol" or json.loads(r["gt_action"]).get("goal_status") != "complete":
            continue
        e = str(r["episode_id"])
        if "#" in e:
            var.append({"variant": e, "step_idx": r["step_idx"], "source_episode": e.split("#", 1)[0]})
            continue
        keep["episode_id"].append(e)
        keep["step_idx"].append(int(r["step_idx"]))
        keep["user"].append(r["messages"][1]["content"])
        keep["jpg"].append(r["images"][0]["bytes"])
    pq.write_table(pa.table(keep), dst + ".tmp")
    os.replace(dst + ".tmp", dst)
    with open(f"{out}/variants.jsonl", "a") as f:
        for v in var:
            f.write(json.dumps(v) + "\n")
    shutil.rmtree(f"{out}/dl", ignore_errors=True)
    total += len(keep["user"])
    print(f"{sh}: {len(keep['user'])} rows, {len(var)} variants; total {total}", flush=True)
print("AC_ROWS_DONE", total)
