#!/bin/bash
# Smoke for vm_r7_train.sh (Colab): the same command on 200 rows / 4 steps with saves every 2 steps to a separate
# public checkpoint repo; then the local run folder is deleted and the command re-run, which must restore step 4 from
# the Hub (as a new VM or Modal would). The full v4.5 download is cached for the real run.
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
export TOKENIZERS_PARALLELISM=false
log() { echo "[$(date +%T)] r7smoke: $*"; }
cd /content/work
MREV=23387beda43c60310348e83e25f78f33c3140d3a; DREV=45331aaadf0e89db25eb9ab10344a46603670557; VREV=f88a843239b7e0b68ea8fcb6eb0c5539276d64eb
run() {
  python sft_vlm.py --model_id LiquidAI/LFM3-VL-2B --model_revision $MREV \
    --train experimentalmachines/MobileAgent-SFT-v4.5@train#$DREV --val experimentalmachines/MobileAgent-SFT-v1@val#$VREV \
    --out /content/runs/r7smoke --max_steps 4 --max_pixels 774400 --bs 4 --grad_accum 8 --no_gc --max_agent_rows 200 \
    --lora_r 64 --lora_alpha 128 --modules_to_save --save_steps 2 --eval_steps 1000 --workers 10 \
    --hub_repo experimentalmachines/LFM3-VL-2B-MobileAgent-v4.5-smoke-ckpt --hub_public
}
log "pass 1: train 4 steps, push checkpoints"
run > /content/runs/r7smoke_1.log 2>&1 || { log "PASS 1 FAILED"; tail -20 /content/runs/r7smoke_1.log; exit 1; }
log "pass 1 ok: $(grep -o '"peak_gpu_mem_gb": [0-9.]*' /content/runs/r7smoke/logs/train_summary.json)"
rm -rf /content/runs/r7smoke
log "pass 2: local folder deleted; must restore from the Hub"
run > /content/runs/r7smoke_2.log 2>&1 || { log "PASS 2 FAILED"; tail -20 /content/runs/r7smoke_2.log; exit 1; }
grep -q "restored /content/runs/r7smoke/checkpoint-4 from hub" /content/runs/r7smoke_2.log && log "SMOKE OK (restored step 4 from the Hub)" || { log "SMOKE FAILED: no hub restore"; grep -iE "restore|resum|checkpoint" /content/runs/r7smoke_2.log | tail -5; }
