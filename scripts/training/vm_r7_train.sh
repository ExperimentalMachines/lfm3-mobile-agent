#!/bin/bash
# Round 7 / v4.5, candidate D (docs/PREREG_v45.md) on a Colab A100: one pass over MobileAgent-SFT-v4.5 (5,420 steps x
# 32 rows), bs 4 x 8 without gradient checkpointing (same maths as v4's 8 x 4). Checkpoints every 100 steps are pushed
# to a PUBLIC Hub repo (hub_strategy=checkpoint), so the run resumes on a new Colab VM or on Modal with the identical
# command: every resume-identity field (data id + revision, steps, batch, LoRA, lr) is platform-independent.
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token)   # needed to push the checkpoints
export TOKENIZERS_PARALLELISM=false
log() { echo "[$(date +%T)] r7d: $*"; }
cd /content/work
MREV=23387beda43c60310348e83e25f78f33c3140d3a          # LiquidAI/LFM3-VL-2B, as v4
DREV=45331aaadf0e89db25eb9ab10344a46603670557          # experimentalmachines/MobileAgent-SFT-v4.5
VREV=f88a843239b7e0b68ea8fcb6eb0c5539276d64eb          # MobileAgent-SFT-v1 (AndroidControl val, eval loss only)
log "start (Colab A100; resumes from the Hub checkpoint repo if one exists)"
python sft_vlm.py --model_id LiquidAI/LFM3-VL-2B --model_revision $MREV \
  --train experimentalmachines/MobileAgent-SFT-v4.5@train#$DREV --val experimentalmachines/MobileAgent-SFT-v1@val#$VREV \
  --out /content/runs/r7d --max_steps 5420 --max_pixels 774400 --bs 4 --grad_accum 8 --no_gc \
  --lora_r 64 --lora_alpha 128 --modules_to_save --save_steps 100 --eval_steps 1000 --workers 10 \
  --hub_repo experimentalmachines/LFM3-VL-2B-MobileAgent-v4.5-D-ckpt --hub_public \
  && log "TRAIN DONE" || log "TRAIN STOPPED rc=$?"
