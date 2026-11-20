#!/bin/bash
# Runs ON the GPU VM: process the smolagents files listed in remaining_files.json, push parquet (tag g4).
set -euo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
cd /content/work
echo "[$(date +%T)] download"
python - <<'PY'
import json
from huggingface_hub import snapshot_download
files = ["data/" + f for f in json.load(open("/content/work/remaining_files.json"))]
snapshot_download("smolagents/android-control", repo_type="dataset", local_dir="/content/raw", allow_patterns=files, max_workers=32)
print("downloaded", len(files), flush=True)
PY
du -sh /content/raw
echo "[$(date +%T)] build"
python build_androidcontrol.py --raw /content/raw --meta /content/work/meta --out /content/data --workers ${WORKERS:-40} --delete_raw --push_parquet experimentalmachines/AndroidControl-screen-agent-sft --tag ${TAG:-g4}
echo "[$(date +%T)] LIST DONE"
