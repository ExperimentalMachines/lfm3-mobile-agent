#!/bin/bash
set -euo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
cd /content/work
echo "[$(date +%T)] push start"
python - <<'EOF'
import os, json
from datasets import load_from_disk, DatasetDict
from huggingface_hub import HfApi
repo = "experimentalmachines/AndroidControl-screen-agent-sft"
dd = DatasetDict({k: load_from_disk(f"/content/data/{k}") for k in ("train", "val", "test")})
dd.push_to_hub(repo, private=True, max_shard_size="1GB")
HfApi().upload_file(path_or_fileobj="/content/data/stats.json", path_in_repo="stats.json", repo_id=repo, repo_type="dataset")
print("pushed", repo, flush=True)
EOF
echo "[$(date +%T)] ALL DONE"
