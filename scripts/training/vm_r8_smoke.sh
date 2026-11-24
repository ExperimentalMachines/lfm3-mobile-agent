#!/bin/bash
# Smoke for vm_r8_train.sh (round 8) (Colab): the same command on 200 rows / 4 steps with saves every 2 steps to a separate
# public checkpoint repo; then the local run folder is deleted and the command re-run, which must restore step 4 from
# the Hub (as a new VM or Modal would). The full v4.5 download is cached for the real run.
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
export TOKENIZERS_PARALLELISM=false
log() { echo "[$(date +%T)] r8smoke: $*"; }
cd /content/work
MREV=23387beda43c60310348e83e25f78f33c3140d3a; DREV=${DREV:?set DREV}; VREV=f88a843239b7e0b68ea8fcb6eb0c5539276d64eb
run() {
  python sft_vlm.py --model_id LiquidAI/LFM3-VL-2B --model_revision $MREV \
    --train experimentalmachines/MobileAgent-SFT-v4.6@train#$DREV --val experimentalmachines/MobileAgent-SFT-v1@val#$VREV \
    --out /content/runs/r8smoke --max_steps 4 --max_pixels 774400 --bs 4 --grad_accum 8 --no_gc --max_agent_rows 200 \
    --lora_r 64 --lora_alpha 128 --modules_to_save --save_steps 2 --eval_steps 1000 --workers 10 \
    --hub_repo experimentalmachines/LFM3-VL-2B-MobileAgent-v4.6-smoke-ckpt --hub_public
}
log "fresh start: delete the smoke checkpoint repo, run folder and eval files"
python -c "from huggingface_hub import HfApi; HfApi().delete_repo('experimentalmachines/LFM3-VL-2B-MobileAgent-v4.6-smoke-ckpt', missing_ok=True)"
rm -rf /content/runs/r8smoke /content/eval/smoke8_*
log "pass 1: train 4 steps, push checkpoints"
run > /content/runs/r8smoke_1.log 2>&1 || { log "PASS 1 FAILED"; tail -20 /content/runs/r8smoke_1.log; exit 1; }
log "pass 1 ok: $(grep -o '"peak_gpu_mem_gb": [0-9.]*' /content/runs/r8smoke/logs/train_summary.json)"
rm -rf /content/runs/r8smoke
log "pass 2: local folder deleted; must restore from the Hub"
run > /content/runs/r8smoke_2.log 2>&1 || { log "PASS 2 FAILED"; tail -20 /content/runs/r8smoke_2.log; exit 1; }
grep -q "restored /content/runs/r8smoke/checkpoint-[0-9]* from hub" /content/runs/r8smoke_2.log && log "hub restore ok ($(grep -o 'checkpoint-[0-9]* from hub' /content/runs/r8smoke_2.log)); identity: $(grep -c 'different run configuration\|no run_config' /content/runs/r8smoke_2.log) warnings" || { log "SMOKE FAILED: no hub restore"; grep -iE "restore|resum|checkpoint" /content/runs/r8smoke_2.log | tail -5; exit 1; }
log "evals, scorers and gate on 16 rows per split"
MODEL=/content/runs/r8smoke/merged NAME=smoke8 LIMIT=16 bash vm_r8_eval.sh && log "SMOKE OK" || { log "SMOKE FAILED: evals"; exit 1; }
