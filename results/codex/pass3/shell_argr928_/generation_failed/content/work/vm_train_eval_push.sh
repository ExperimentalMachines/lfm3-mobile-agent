#!/bin/bash
# Runs ON the GPU VM (as a job inside vm_blocking_jobs.py): train -> eval fine-tuned -> push to HF.
# Env: RUN, MODEL, TRAIN, VAL, MAX_STEPS/EPOCHS, BS, GA, LR, SAVE_STEPS, EVAL_STEPS, WORKERS, HUB_REPO (ckpt),
#      FINAL_REPO (merged model repo), EVAL_BS, EXTRA
set -uo pipefail
export HF_TOKEN=$(cat /Users/alpha/lfm3-android/results/codex/pass3/shell_argr928_/generation_failed/content/.hf_token)
cd /Users/alpha/lfm3-android/results/codex/pass3/shell_argr928_/generation_failed/content/work
bash vm_train.sh
echo "TRAIN DONE rc=$?"
if [ -f /Users/alpha/lfm3-android/results/codex/pass3/shell_argr928_/generation_failed/content/runs/$RUN/merged/config.json ]; then
  MODEL=/Users/alpha/lfm3-android/results/codex/pass3/shell_argr928_/generation_failed/content/runs/$RUN/merged NAME=${RUN}_ft THINK=1 BS=${EVAL_BS:-64} bash vm_eval.sh
  echo "FT EVAL DONE rc=$?"
fi
python - <<PY
import os, glob
from huggingface_hub import HfApi
api = HfApi()
repo = os.environ["FINAL_REPO"]; run = os.environ["RUN"]
api.create_repo(repo, private=True, exist_ok=True)
base = f"/Users/alpha/lfm3-android/results/codex/pass3/shell_argr928_/generation_failed/content/runs/{run}"
if os.path.isdir(f"{base}/merged"):
    api.upload_folder(folder_path=f"{base}/merged", repo_id=repo, commit_message="merged LoRA -> full weights")
if os.path.isdir(f"{base}/lora"):
    api.upload_folder(folder_path=f"{base}/lora", path_in_repo="lora_adapter", repo_id=repo)
api.upload_folder(folder_path=f"{base}/logs", path_in_repo="training_logs", repo_id=repo)
for f in glob.glob("/Users/alpha/lfm3-android/results/codex/pass3/shell_argr928_/generation_failed/content/eval/*"):
    if os.path.isfile(f):
        api.upload_file(path_or_fileobj=f, path_in_repo=f"eval/{os.path.basename(f)}", repo_id=repo)
print("PUSHED", repo, flush=True)
PY
echo "PIPELINE DONE"
