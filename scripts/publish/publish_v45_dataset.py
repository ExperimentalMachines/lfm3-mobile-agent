#!/usr/bin/env python3
"""Publish the round-7 / v4.5 mix (data/v45_build_mix.py output) as experimentalmachines/MobileAgent-SFT-v4.5 (public):
parquet shards (~450 MB) per split under data/, the AndroidLens scorer files under androidlens/, build_stats.json and
the card. Runs on the build instance with HF_TOKEN set; prints the commit sha (the revision to pin).
usage: publish_v45_dataset.py --mix ~/r7mix --androidlens ~/data/mac/androidlens_h24 --card dataset-sft-v4.5.md
"""
import argparse
import math
import os
import shutil

from datasets import load_from_disk
from huggingface_hub import HfApi

ap = argparse.ArgumentParser()
ap.add_argument("--mix", required=True)
ap.add_argument("--androidlens", required=True)
ap.add_argument("--card", required=True)
ap.add_argument("--repo", default="experimentalmachines/MobileAgent-SFT-v4.5")
ap.add_argument("--work", default=os.path.expanduser("~/r7publish"))
ap.add_argument("--extra_splits", default="", help="folder of <split>.parquet files published as data/<split>-00000-of-00001.parquet (round 8 probes)")
a = ap.parse_args()

shutil.rmtree(a.work, ignore_errors=True)
os.makedirs(os.path.join(a.work, "data"))
os.makedirs(os.path.join(a.work, "androidlens"))
splits = sorted(os.listdir(os.path.join(a.mix, "disk")))
for sp in splits:
    ds = load_from_disk(os.path.join(a.mix, "disk", sp))
    n = max(1, math.ceil(ds.data.nbytes / 450e6))
    for i in range(n):
        ds.shard(num_shards=n, index=i, contiguous=True).to_parquet(os.path.join(a.work, "data", f"{sp}-{i:05d}-of-{n:05d}.parquet"))
    print(sp, len(ds), "rows,", n, "shards", flush=True)
if a.extra_splits:
    for f in sorted(os.listdir(a.extra_splits)):
        if f.endswith(".parquet"):
            shutil.copy(os.path.join(a.extra_splits, f), os.path.join(a.work, "data", f[:-8] + "-00000-of-00001.parquet"))
            print("extra split", f[:-8], flush=True)
for f in ("dev_androidlens_high.parquet", "manifest.json"):
    shutil.copy(os.path.join(a.androidlens, f), os.path.join(a.work, "androidlens", f))
shutil.copy(os.path.join(a.mix, "build_stats.json"), os.path.join(a.work, "build_stats.json"))
shutil.copy(a.card, os.path.join(a.work, "README.md"))
api = HfApi()
api.create_repo(a.repo, repo_type="dataset", private=False, exist_ok=True)
c = api.upload_folder(repo_id=a.repo, repo_type="dataset", folder_path=a.work,
                      commit_message=f"{a.repo.split('/')[1]}: training mix and gate splits")
print("PUBLISHED", a.repo, c.oid, flush=True)
