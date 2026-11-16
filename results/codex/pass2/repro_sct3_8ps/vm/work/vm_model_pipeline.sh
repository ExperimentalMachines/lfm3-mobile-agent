#!/bin/bash
# Generic per-model pipeline, runs ON a Colab GPU inside the blocking cell. Every step is skipped if its
# output exists, so the job can be relaunched after a VM loss; training resumes from the hub checkpoint.
# Env (required): MODEL RUN FINAL_REPO CKPT_REPO
# Env (optional): MAX_STEPS EPOCHS MAX_AGENT_ROWS REPLAY(0/1) BS GA LR LORA_R LORA_ALPHA MAX_PIXELS
#                 TEMPLATE (path) TARGET_REGEX INLINE_THINK(0/1) FT_THINK(0/1) EVAL_BS SAVE_STEPS
#                 GENERAL_EVAL(0/1) BASE_AC_EVAL(0/1) PRE_GENERAL_MODELS ("model=name ..." extra general evals)
set -uo pipefail
export HF_TOKEN=$(cat /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/.hf_token)
export TOKENIZERS_PARALLELISM=false
cd /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/work
R=experimentalmachines/AndroidControl-screen-agent-sft
OUT=/Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/runs/$RUN
mkdir -p /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval $OUT/logs /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/data
log() { echo "[$(date +%T)] $RUN: $*"; }
push_evals() {  # durable copy of every eval artifact after each step ("save frequently")
python - <<PY
import os, glob
from huggingface_hub import HfApi
api = HfApi(); repo = "$FINAL_REPO"
api.create_repo(repo, private=True, exist_ok=True)
for f in glob.glob("/Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/*"):
    if os.path.isfile(f) and os.path.getsize(f) < 500_000_000:
        api.upload_file(path_or_fileobj=f, path_in_repo=f"eval/{os.path.basename(f)}", repo_id=repo)
if os.path.isdir("$OUT/logs"):
    api.upload_folder(folder_path="$OUT/logs", path_in_repo="training_logs", repo_id=repo)
PY
}

for spec in ${PRE_GENERAL_MODELS:-}; do  # e.g. "LiquidAI/LFM3-VL-2B=lfm3vl2b_base /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/runs/x/merged=lfm3vl2b_ft"
  m=${spec%%=*}; n=${spec##*=}
  [ -f /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${n}_general.summary.json ] || { log "general eval $n"; python eval_general.py --model $m --out /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${n}_general --bs ${EVAL_BS:-32}; }
done

if [ "${GENERAL_EVAL:-1}" = 1 ] && [ ! -f /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_base_general.summary.json ]; then
  log "general eval BASE"; python eval_general.py --model $MODEL --out /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_base_general --bs ${EVAL_BS:-32}
fi
push_evals

REPLAY_ARGS=""
if [ "${REPLAY:-0}" = 1 ]; then
  [ -d /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/data/replay ] || { log "build replay"; python build_general_replay.py --out /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/data/replay --n 12000; }
  REPLAY_ARGS="--replay /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/data/replay"
fi
TEMPLATE_ARGS=${TEMPLATE:+--chat_template_path $TEMPLATE}
REGEX_ARGS=${TARGET_REGEX:+--target_regex $TARGET_REGEX}
STEP_ARGS="--epochs ${EPOCHS:-1}"; [ -n "${MAX_STEPS:-}" ] && STEP_ARGS="--max_steps $MAX_STEPS"
ROWS_ARGS=""; [ -n "${MAX_AGENT_ROWS:-}" ] && ROWS_ARGS="--max_agent_rows $MAX_AGENT_ROWS"
INLINE_ARGS=""; [ "${INLINE_THINK:-0}" = 1 ] && INLINE_ARGS="--inline_think"

if [ ! -f $OUT/merged/config.json ]; then
  log "train"
  python sft_vlm.py --model_id $MODEL --train $R@train --val $R@val --out $OUT $REPLAY_ARGS $ROWS_ARGS $STEP_ARGS \
    --max_pixels ${MAX_PIXELS:-774400} $INLINE_ARGS $TEMPLATE_ARGS $REGEX_ARGS \
    --bs ${BS:-8} --grad_accum ${GA:-4} --lr ${LR:-2e-4} --lora_r ${LORA_R:-64} --lora_alpha ${LORA_ALPHA:-128} \
    --modules_to_save --save_steps ${SAVE_STEPS:-100} --eval_steps ${EVAL_STEPS:-250} --workers ${WORKERS:-10} \
    --hub_repo $CKPT_REPO
fi
[ -f $OUT/merged/config.json ] || { log "TRAINING FAILED"; push_evals; exit 1; }
log "push merged + adapter"
python - <<PY
from huggingface_hub import HfApi
api = HfApi(); repo = "$FINAL_REPO"
api.create_repo(repo, private=True, exist_ok=True)
api.upload_folder(folder_path="$OUT/merged", repo_id=repo, commit_message="merged LoRA -> full weights")
api.upload_folder(folder_path="$OUT/lora", path_in_repo="lora_adapter", repo_id=repo)
PY
push_evals

if [ "${GENERAL_EVAL:-1}" = 1 ] && [ ! -f /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_ft_general.summary.json ]; then
  log "general eval FT"; python eval_general.py --model $OUT/merged --out /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_ft_general --bs ${EVAL_BS:-32}
  push_evals
fi
if [ ! -f /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_ft.metrics.json ]; then
  log "AndroidControl test FT"
  python generate.py --model $OUT/merged --data $R@test --out /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_ft.jsonl --enable_thinking ${FT_THINK:-1} \
    --bs ${EVAL_BS:-32} --max_pixels ${MAX_PIXELS:-774400} && python score.py /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_ft.jsonl --out /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_ft.metrics.json > /dev/null
  push_evals
fi
if [ "${BASE_AC_EVAL:-1}" = 1 ] && [ ! -f /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_base.metrics.json ]; then
  log "AndroidControl test BASE (no-think)"
  python generate.py --model $MODEL --data $R@test --out /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_base.jsonl --enable_thinking 0 \
    --bs ${EVAL_BS:-32} --max_pixels ${MAX_PIXELS:-774400} && python score.py /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_base.jsonl --out /Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/eval/${RUN}_base.metrics.json > /dev/null
  push_evals
fi
log "PIPELINE DONE"
