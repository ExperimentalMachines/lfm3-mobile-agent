#!/bin/bash
# Bootstrap the (adopted) G4 session, seed /content/eval with eval outputs already on the Hub, launch Qwen3.5-2B (resumes from hub ckpt).
set -u
cd /Users/alpha/lfm3-android
bash scripts/gpu_session.sh g4 2>&1 | grep -E "versions|HF user|pip rc|mismatch|Error|RTX" | tail -6
cat > /tmp/seed_eval_$$.py <<'PY'
import os
from huggingface_hub import HfApi, hf_hub_download
tok = open("/content/.hf_token").read().strip()
repo = "experimentalmachines/Qwen3.5-2B-AndroidControl"
fs = [f for f in HfApi(token=tok).list_repo_files(repo) if f.startswith("eval/")]
for f in fs:
    hf_hub_download(repo, f, local_dir="/content", token=tok)
print("seeded", sorted(os.listdir("/content/eval")))
PY
colab exec -s g4 -f /tmp/seed_eval_$$.py < /dev/null 2>&1 | grep -E "seeded|Error"; rm -f /tmp/seed_eval_$$.py
bash scripts/launch_on_session.sh g4 scripts/jobs/qwen35_2b_g4.json
