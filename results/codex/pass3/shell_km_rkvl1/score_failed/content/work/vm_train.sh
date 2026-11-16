#!/bin/bash
# Runs ON the Colab VM under nohup. Usage: MAX_STEPS=... RUN=... bash vm_train.sh
set -euo pipefail
export HF_TOKEN=$(cat /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/score_failed/content/.hf_token)
export TOKENIZERS_PARALLELISM=false
cd /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/score_failed/content/work
RUN=${RUN:-lfm3vl2b-ac-lora}
MODEL=${MODEL:-LiquidAI/LFM3-VL-2B}
mkdir -p /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/score_failed/content/runs/$RUN/logs
python sft_vlm.py \
  --model_id "$MODEL" \
  --train ${TRAIN:-/Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/score_failed/content/data/train} \
  ${VAL:+--val $VAL} \
  --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/score_failed/content/runs/$RUN \
  --max_steps ${MAX_STEPS:--1} --epochs ${EPOCHS:-1} \
  --bs ${BS:-16} --grad_accum ${GA:-2} --lr ${LR:-2e-4} \
  --lora_r ${LORA_R:-64} --lora_alpha ${LORA_ALPHA:-128} \
  --modules_to_save \
  --save_steps ${SAVE_STEPS:-400} --eval_steps ${EVAL_STEPS:-400} \
  --workers ${WORKERS:-8} \
  ${HUB_REPO:+--hub_repo $HUB_REPO} \
  ${EXTRA:-}
echo "TRAIN EXIT $?"
