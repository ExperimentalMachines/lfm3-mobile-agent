#!/bin/bash
# RL pilot job (uploaded as /content/work/rl_go.sh; started by vm_rl_hook.sh next to the v4 pipeline, no kernel restart).
#   1. smoke: 4 GRPO steps on the BASE model with the real pool -> code path, memory, s/step (no v4 needed yet)
#   2. wait for the v4 pipeline to finish (merged weights + evals; avoids GPU contention / OOM)
#   3. main GRPO from merged v4: steps = min(MAX_STEPS, budget / measured s/step)
#   4. push merged + adapter, then offline evals on the v4 dev splits + AndroidControl test (v4 prompt)
# Env set below by the launcher (sed): RL_DATA DEV_REPO DEV_REV
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token) TOKENIZERS_PARALLELISM=false
cd /content/work
RL_DATA=__RL_DATA__; DEV_REPO=__DEV_REPO__; DEV_REV=__DEV_REV__
MAX_STEPS=${MAX_STEPS:-200}; BUDGET_S=${BUDGET_S:-16200}   # 4.5 h for the main optimisation
V4=/content/runs/lfm3vl2b-v4mix-lora/merged
OUT=/content/runs/v4rl; FINAL=alpharomercoma/LFM3-VL-2B-AndroidAgent-v4-RL
log() { echo "[$(date +%T)] rl: $*"; }
log "smoke on base model"
python grpo_vlm.py --model LiquidAI/LFM3-VL-2B --data $RL_DATA --out /content/runs/rl_smoke --smoke > /content/runs/rl_smoke.log 2>&1
grep -q "RL DONE" /content/runs/rl_smoke.log || { log "SMOKE FAILED"; tail -40 /content/runs/rl_smoke.log; exit 1; }
SPS=$(python - <<'PY'
import json
L = [json.loads(l) for l in open("/content/runs/rl_smoke/rl_log.jsonl")]
L = [x for x in L if x.get("step", 0) >= 1]
print(round((L[-1]["elapsed_s"] - L[0]["elapsed_s"]) / max(1, L[-1]["step"] - L[0]["step"]), 1) if len(L) > 1 else 120)
PY
)
log "smoke ok; ${SPS} s/step"
log "waiting for the v4 pipeline to finish"
until grep -q "PIPELINE DONE\|PIPELINE FINISHED WITH FAILURES" /content/runs/lfm3_v4_pipeline.log 2>/dev/null; do
  grep -q "TRAINING FAILED" /content/runs/lfm3_v4_pipeline.log 2>/dev/null && { log "v4 training failed; no RL"; exit 1; }
  sleep 60
done
[ -f $V4/config.json ] || { log "no merged v4 at $V4"; exit 1; }
STEPS=$(python -c "print(max(10, min($MAX_STEPS, int($BUDGET_S / max(1.0, 1.15 * $SPS)))))")
log "main GRPO from v4: $STEPS steps"
python grpo_vlm.py --model $V4 --data $RL_DATA --out $OUT --max_steps $STEPS --hub_repo ${FINAL}-ckpt > /content/runs/v4rl_train.log 2>&1
grep -q "RL DONE" /content/runs/v4rl_train.log || { log "RL TRAINING FAILED"; tail -40 /content/runs/v4rl_train.log; exit 1; }
python - <<PY || log "upload merged failed"
from huggingface_hub import HfApi
api = HfApi(); api.create_repo("$FINAL", private=True, exist_ok=True)
api.upload_folder(folder_path="$OUT/merged", repo_id="$FINAL", commit_message="v4 + static GRPO (merged)")
api.upload_folder(folder_path="$OUT/lora", path_in_repo="lora_adapter", repo_id="$FINAL")
api.upload_file(path_or_fileobj="$OUT/rl_log.jsonl", path_in_repo="training_logs/rl_log.jsonl", repo_id="$FINAL")
PY
log "offline evals"
for sp in dev_answer dev_complete dev_screenqa dev_odyssey dev_amex; do
  N=$(python -c "from datasets import load_dataset; from huggingface_hub import HfApi; fs=HfApi().list_repo_files('$DEV_REPO', repo_type='dataset', revision='$DEV_REV'); print(len(load_dataset('$DEV_REPO', data_files={'$sp': [f for f in fs if f.startswith('data/$sp-')]}, split='$sp', revision='$DEV_REV')))")
  python generate.py --model $OUT/merged --data "$DEV_REPO@$sp#$DEV_REV" --out /content/eval/lfm3_v4rl_$sp.jsonl --enable_thinking 1 \
    --bs 32 --max_pixels 774400 --prompt_v4_pool /content/work/meta/app_pool.json \
    && python score_dev.py /content/eval/lfm3_v4rl_$sp.jsonl --expect_n $N --out /content/eval/lfm3_v4rl_$sp.metrics.json || log "dev $sp failed"
done
python generate.py --model $OUT/merged --data experimentalmachines/AndroidControl-screen-agent-sft@test --out /content/eval/lfm3vl2b-v4rl_ft.jsonl \
  --enable_thinking 1 --bs 32 --max_pixels 774400 --prompt_v4_pool /content/work/meta/app_pool.json \
  && python score.py /content/eval/lfm3vl2b-v4rl_ft.jsonl --gt /content/work/meta/androidcontrol_test_gt.jsonl \
     --expect model=$OUT/merged,max_pixels=774400,enable_thinking=1 --out /content/eval/lfm3vl2b-v4rl_ft.metrics.json || log "AC test failed"
python - <<PY
import glob, os
from huggingface_hub import HfApi
api = HfApi()
for f in glob.glob("/content/eval/lfm3*v4rl*"):
    api.upload_file(path_or_fileobj=f, path_in_repo=f"eval/{os.path.basename(f)}", repo_id="$FINAL")
PY
log "RL PIPELINE DONE"
