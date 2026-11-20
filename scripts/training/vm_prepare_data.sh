#!/bin/bash
# Runs ON the Colab VM (nohup). Downloads AndroidControl screenshots (smolagents mirror),
# rebuilds official splits, and pushes the processed dataset to a private HF repo.
set -euo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
cd /content/work
mkdir -p /content/raw /content/data logs
echo "[$(date +%T)] download start"
python - <<'EOF'
from huggingface_hub import snapshot_download
import time
t=time.time()
p=snapshot_download("smolagents/android-control", repo_type="dataset", local_dir="/content/raw",
                    allow_patterns=["data/*.parquet"], max_workers=16)
print("downloaded in", time.time()-t, "s", flush=True)
EOF
du -sh /content/raw
echo "[$(date +%T)] build start"
python build_androidcontrol.py --raw /content/raw --meta /content/work/meta --out /content/data --workers ${WORKERS:-10} --delete_raw
echo "[$(date +%T)] build done"
rm -rf /content/raw   # free disk once processed
du -sh /content/data/*
echo "[$(date +%T)] PREP DONE"
