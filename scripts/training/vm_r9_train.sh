#!/bin/bash
# Round 9 / v4.7, candidate F (docs/PREREG_v47.md): a new LoRA (r64 a128) on E's merged weights, 1,000 steps x 32 rows
# over MobileAgent-SFT-v4.7's fixed train_f mix, lr 1e-4 cosine. bs 2 x 16 without gradient checkpointing, as E.
# Checkpoints every 100 steps go to a PUBLIC Hub repo, so the run resumes on a new Colab VM or on Modal with the
# identical command. Only run if E passed its round-8 offline gate.
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token)   # needed to push the checkpoints
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
log() { echo "[$(date +%T)] r9f: $*"; }
cd /content/work
EREPO=${EREPO:?set EREPO (E merged weights repo)}; EREV=${EREV:?set EREV (its commit)}
DREV=${DREV:?set DREV (MobileAgent-SFT-v4.7 commit)}
VREV=f88a843239b7e0b68ea8fcb6eb0c5539276d64eb          # MobileAgent-SFT-v1 (AndroidControl val, eval loss only)
log "start (resumes from the Hub checkpoint repo if one exists)"
[ -f /content/runs/r9f/train_receipt.json ] && { log "already trained (receipt present)"; MODEL=/content/runs/r9f/merged NAME=r9f LIMIT=0 bash vm_r9_eval.sh; exit $?; }
python sft_vlm.py --model_id $EREPO --model_revision $EREV \
  --train experimentalmachines/MobileAgent-SFT-v4.7@train_f#$DREV --val experimentalmachines/MobileAgent-SFT-v1@val#$VREV \
  --out /content/runs/r9f --max_steps 1000 --lr 1e-4 --max_pixels 774400 --bs 2 --grad_accum 16 --no_gc \
  --lora_r 64 --lora_alpha 128 --modules_to_save --save_steps 100 --eval_steps 500 --workers 10 \
  --hub_repo experimentalmachines/LFM3-VL-2B-MobileAgent-v4.7-F-ckpt --hub_public \
  && { log "TRAIN DONE"; MODEL=/content/runs/r9f/merged NAME=r9f LIMIT=0 bash vm_r9_eval.sh; } || log "TRAIN STOPPED rc=$?"
