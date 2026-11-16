#!/bin/bash
# Generic per-model pipeline, runs ON a Colab GPU inside the blocking cell. Every step is skipped if its
# output exists, so the job can be relaunched after a VM loss; training resumes from the hub checkpoint.
# Env (required): MODEL RUN FINAL_REPO CKPT_REPO
# Env (optional): MAX_STEPS EPOCHS MAX_AGENT_ROWS REPLAY(0/1) BS GA LR LORA_R LORA_ALPHA MAX_PIXELS
#                 TEMPLATE (path) TARGET_REGEX INLINE_THINK(0/1) FT_THINK(0/1) EVAL_BS SAVE_STEPS
#                 GENERAL_EVAL(0/1) BASE_AC_EVAL(0/1) PRE_GENERAL_MODELS ("model=name ..." extra general evals)
set -uo pipefail
FAILED=0
fail() { echo "[$(date +%T)] $RUN: STAGE FAILED: $*"; FAILED=1; }
export HF_TOKEN=$(cat /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/.hf_token)
export TOKENIZERS_PARALLELISM=false
export EVAL_PUSH_REPO=$FINAL_REPO   # generate.py checkpoints partial predictions here
GT=/Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/work/meta/androidcontrol_test_gt.jsonl
GPX=${GENERAL_MAX_PIXELS:-${MAX_PIXELS:-774400}}   # identical general-eval image budget for base and FT
cd /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/work
R=experimentalmachines/AndroidControl-screen-agent-sft
OUT=/Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/runs/$RUN
mkdir -p /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval $OUT/logs /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/data
log() { echo "[$(date +%T)] $RUN: $*"; }
push_evals() {  # durable copy of every eval artifact after each step ("save frequently")
python - <<PY
import os, glob
from huggingface_hub import HfApi
api = HfApi(); repo = "$FINAL_REPO"
api.create_repo(repo, private=True, exist_ok=True)
for f in glob.glob("/Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/*"):
    if os.path.isfile(f) and os.path.getsize(f) < 500_000_000:
        api.upload_file(path_or_fileobj=f, path_in_repo=f"eval/{os.path.basename(f)}", repo_id=repo)
if os.path.isdir("$OUT/logs"):
    api.upload_folder(folder_path="$OUT/logs", path_in_repo="training_logs", repo_id=repo)
PY
}

for spec in ${PRE_GENERAL_MODELS:-}; do  # e.g. "LiquidAI/LFM3-VL-2B=lfm3vl2b_base /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/runs/x/merged=lfm3vl2b_ft"
  m=${spec%%=*}; n=${spec##*=}
  [ -f /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${n}_general.summary.json ] || { log "general eval $n"; python eval_general.py --model $m --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${n}_general --bs ${EVAL_BS:-32} --max_pixels $GPX || fail "general $n"; }
done

if [ "${GENERAL_EVAL:-1}" = 1 ] && [ ! -f /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_base_general.summary.json ]; then
  log "general eval BASE"; python eval_general.py --model $MODEL --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_base_general --bs ${EVAL_BS:-32} --max_pixels $GPX || fail "general base"
fi
push_evals

REPLAY_ARGS=""
if [ "${REPLAY:-0}" = 1 ]; then
  WANT=$(sha256sum build_general_replay.py | cut -d" " -f1)
  if ! grep -q "$WANT" /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/data/replay/replay_receipt.json 2>/dev/null; then
    rm -rf /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/data/replay; log "build replay"
    python build_general_replay.py --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/data/replay --n 12000 || { fail "replay"; exit 1; }
  fi
  REPLAY_ARGS="--replay /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/data/replay"
fi
TEMPLATE_ARGS=${TEMPLATE:+--chat_template_path $TEMPLATE}
REGEX_ARGS=${TARGET_REGEX:+--target_regex $TARGET_REGEX}
STEP_ARGS="--epochs ${EPOCHS:-1}"; [ -n "${MAX_STEPS:-}" ] && STEP_ARGS="--max_steps $MAX_STEPS"
ROWS_ARGS=""; [ -n "${MAX_AGENT_ROWS:-}" ] && ROWS_ARGS="--max_agent_rows $MAX_AGENT_ROWS"
INLINE_ARGS=""; [ "${INLINE_THINK:-0}" = 1 ] && INLINE_ARGS="--inline_think"

if [ ! -f $OUT/train_receipt.json ]; then
  rm -rf $OUT/merged $OUT/lora
  log "train"
  python sft_vlm.py --model_id $MODEL --train $R@train --val $R@val --out $OUT $REPLAY_ARGS $ROWS_ARGS $STEP_ARGS \
    --max_pixels ${MAX_PIXELS:-774400} $INLINE_ARGS $TEMPLATE_ARGS $REGEX_ARGS \
    --bs ${BS:-8} --grad_accum ${GA:-4} --lr ${LR:-2e-4} --lora_r ${LORA_R:-64} --lora_alpha ${LORA_ALPHA:-128} \
    --modules_to_save --save_steps ${SAVE_STEPS:-100} --eval_steps ${EVAL_STEPS:-250} --workers ${WORKERS:-10} \
    --hub_repo $CKPT_REPO
fi
[ -f $OUT/train_receipt.json ] || { log "TRAINING FAILED"; push_evals; exit 1; }
log "push merged + adapter"
python - <<PY
from huggingface_hub import HfApi
api = HfApi(); repo = "$FINAL_REPO"
api.create_repo(repo, private=True, exist_ok=True)
api.upload_folder(folder_path="$OUT/merged", repo_id=repo, commit_message="merged LoRA -> full weights")
api.upload_folder(folder_path="$OUT/lora", path_in_repo="lora_adapter", repo_id=repo)
PY
push_evals

if [ "${GENERAL_EVAL:-1}" = 1 ] && [ ! -f /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_ft_general.summary.json ]; then
  log "general eval FT"; python eval_general.py --model $OUT/merged --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_ft_general --bs ${EVAL_BS:-32} --max_pixels $GPX || fail "general ft"
  push_evals
fi
if [ ! -f /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_ft.metrics.json ]; then
  log "AndroidControl test FT"
  python generate.py --model $OUT/merged --data $R@test --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_ft.jsonl --enable_thinking ${FT_THINK:-1} \
    --bs ${EVAL_BS:-32} --max_pixels ${MAX_PIXELS:-774400} && python score.py /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_ft.jsonl --gt $GT --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_ft.metrics.json > /dev/null || fail "ft AC eval"
  push_evals
fi
if [ "${BASE_AC_EVAL:-1}" = 1 ] && [ ! -f /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_base.metrics.json ]; then
  log "AndroidControl test BASE (no-think)"
  python generate.py --model $MODEL --data $R@test --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_base.jsonl --enable_thinking 0 \
    --bs ${EVAL_BS:-32} --max_pixels ${MAX_PIXELS:-774400} && python score.py /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_base.jsonl --gt $GT --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_base.metrics.json > /dev/null || fail "base AC eval"
  push_evals
fi
if [ "${MATCHED_NOTHINK:-1}" = 1 ] && [ ! -f /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_ft_nothink_high.jsonl.done ]; then
  log "AndroidControl test FT matched no-think (high-level)"
  python generate.py --model $OUT/merged --data $R@test --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_ft_nothink_high.jsonl --enable_thinking 0 \
    --filter_mode high --bs ${EVAL_BS:-32} --max_pixels ${MAX_PIXELS:-774400} && touch /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/qwen2b_success/content/eval/${RUN}_ft_nothink_high.jsonl.done || fail "ft nothink eval"
  push_evals
fi
if [ "$FAILED" = 1 ]; then log "PIPELINE FINISHED WITH FAILURES"; exit 1; fi
log "PIPELINE DONE"
