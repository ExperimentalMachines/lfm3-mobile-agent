#!/bin/bash
# Runs ON a CPU Colab VM: process files [START:END) of smolagents/android-control and push parquet.
set -euo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
cd /content/work
echo "[$(date +%T)] slice $START:$END tag=$TAG"
python - <<PY
from huggingface_hub import HfApi, snapshot_download
files = sorted(f for f in HfApi().list_repo_files("smolagents/android-control", repo_type="dataset") if f.startswith("data/") and f.endswith(".parquet"))
sl = files[$START:$END]
print(len(files), "total;", len(sl), "in slice", sl[0], sl[-1], flush=True)
snapshot_download("smolagents/android-control", repo_type="dataset", local_dir="/content/raw", allow_patterns=sl, max_workers=16)
PY
echo "[$(date +%T)] downloaded"; du -sh /content/raw
python build_androidcontrol.py --raw /content/raw --meta /content/work/meta --out /content/data --workers ${WORKERS:-2} --delete_raw --push_parquet experimentalmachines/AndroidControl-screen-agent-sft --tag $TAG
echo "[$(date +%T)] SLICE DONE"
