#!/bin/bash
# Round 8 / v4.6, candidate E (docs/PREREG_v46.md) on a Colab A100: one pass over MobileAgent-SFT-v4.6 ($MAX_STEPS steps x
# 32 rows), bs 4 x 8 without gradient checkpointing (same maths as v4's 8 x 4). Checkpoints every 100 steps are pushed
# to a PUBLIC Hub repo (hub_strategy=checkpoint), so the run resumes on a new Colab VM or on Modal with the identical
# command: every resume-identity field (data id + revision, steps, batch, LoRA, lr) is platform-independent.
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token)   # needed to push the checkpoints
export TOKENIZERS_PARALLELISM=false
# bs 2 x 16 (same 32 rows per step): bs 4 x 8 ran out of memory on a 40 GB A100 with v4.6's 24-step rows (2026-11-25)
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
log() { echo "[$(date +%T)] r8e: $*"; }
cd /content/work
MREV=23387beda43c60310348e83e25f78f33c3140d3a          # LiquidAI/LFM3-VL-2B, as v4
DREV=${DREV:?set DREV}; MAX_STEPS=${MAX_STEPS:?set MAX_STEPS}  # experimentalmachines/MobileAgent-SFT-v4.6
VREV=f88a843239b7e0b68ea8fcb6eb0c5539276d64eb          # MobileAgent-SFT-v1 (AndroidControl val, eval loss only)
log "start (resumes from the Hub checkpoint repo if one exists)"
# a finished run is never resumed: resuming at the last step trains one more step (seen in the round-7 smoke)
[ -f /content/runs/r8e/train_receipt.json ] && { log "already trained (receipt present)"; MODEL=/content/runs/r8e/merged NAME=r8e LIMIT=0 bash vm_r8_eval.sh; exit $?; }
python sft_vlm.py --model_id LiquidAI/LFM3-VL-2B --model_revision $MREV \
  --train experimentalmachines/MobileAgent-SFT-v4.6@train#$DREV --val experimentalmachines/MobileAgent-SFT-v1@val#$VREV \
  --out /content/runs/r8e --max_steps $MAX_STEPS --max_pixels 774400 --bs 2 --grad_accum 16 --no_gc \
  --lora_r 64 --lora_alpha 128 --modules_to_save --save_steps 100 --eval_steps 1000 --workers 10 \
  --hub_repo experimentalmachines/LFM3-VL-2B-MobileAgent-v4.6-E-ckpt --hub_public \
  && { log "TRAIN DONE"; MODEL=/content/runs/r8e/merged NAME=r8e LIMIT=0 bash vm_r8_eval.sh; } || log "TRAIN STOPPED rc=$?"
