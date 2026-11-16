#!/bin/bash
# Runs ON a Colab L4 (account <account-B>, launched from state-dashboard-v4:~/vl) inside the blocking cell.
# LFM2.5-VL-450M agent SFT designed to PRESERVE general knowledge:
#   LoRA r=16 (LM only, vision+projector frozen), LR 1e-4, ~1 pass over 48k agent rows + 20% general replay,
#   general-knowledge eval (MMStar + MMLU) before and after, AndroidControl test eval base + FT, push to HF.
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
export TOKENIZERS_PARALLELISM=false
cd /content/work
MODEL=LiquidAI/LFM2.5-VL-450M
RUN=lfm25vl450m-ac-lora
R=experimentalmachines/AndroidControl-screen-agent-sft
FINAL_REPO=experimentalmachines/LFM2.5-VL-450M-AndroidControl
mkdir -p /content/eval /content/runs/$RUN/logs /content/data

echo "[$(date +%T)] 1) general eval BASE"
[ -f /content/eval/lfm25vl450m_base_general.summary.json ] || \
  python eval_general.py --model $MODEL --out /content/eval/lfm25vl450m_base_general --bs 32

echo "[$(date +%T)] 2) build replay"
[ -d /content/data/replay ] || python build_general_replay.py --out /content/data/replay --n 12000

echo "[$(date +%T)] 3) train"
[ -f /content/runs/$RUN/merged/config.json ] || python sft_vlm.py --model_id $MODEL \
  --train $R@train --val $R@val --replay /content/data/replay --max_agent_rows 48000 \
  --out /content/runs/$RUN --max_pixels 0 --inline_think \
  --epochs 1 --bs 16 --grad_accum 2 --lr 1e-4 --lora_r 16 --lora_alpha 32 --modules_to_save \
  --save_steps 200 --eval_steps 400 --workers 10 \
  --hub_repo experimentalmachines/LFM2.5-VL-450M-AndroidControl-LoRA-ckpt

echo "[$(date +%T)] 4) general eval FT"
python eval_general.py --model /content/runs/$RUN/merged --out /content/eval/lfm25vl450m_ft_general --bs 32

echo "[$(date +%T)] 5) AndroidControl test eval (FT, think inline) + BASE (no-think)"
python generate.py --model /content/runs/$RUN/merged --data $R@test --out /content/eval/${RUN}_ft.jsonl \
  --enable_thinking 0 --bs 48 --max_pixels 0 && python score.py /content/eval/${RUN}_ft.jsonl --out /content/eval/${RUN}_ft.metrics.json > /dev/null
python generate.py --model $MODEL --data $R@test --out /content/eval/lfm25vl450m_base.jsonl \
  --enable_thinking 0 --bs 48 --max_pixels 0 && python score.py /content/eval/lfm25vl450m_base.jsonl --out /content/eval/lfm25vl450m_base.metrics.json > /dev/null

echo "[$(date +%T)] 6) push"
python - <<PY
import os, glob
from huggingface_hub import HfApi
api = HfApi(); repo = "$FINAL_REPO"; base = "/content/runs/$RUN"
api.create_repo(repo, private=True, exist_ok=True)
if os.path.isdir(f"{base}/merged"): api.upload_folder(folder_path=f"{base}/merged", repo_id=repo)
if os.path.isdir(f"{base}/lora"): api.upload_folder(folder_path=f"{base}/lora", path_in_repo="lora_adapter", repo_id=repo)
api.upload_folder(folder_path=f"{base}/logs", path_in_repo="training_logs", repo_id=repo)
for f in glob.glob("/content/eval/*"):
    if os.path.isfile(f): api.upload_file(path_or_fileobj=f, path_in_repo=f"eval/{os.path.basename(f)}", repo_id=repo)
print("PUSHED", repo, flush=True)
PY
echo "[$(date +%T)] PIPELINE DONE"
