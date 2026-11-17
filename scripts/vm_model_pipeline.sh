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
export HF_TOKEN=$(cat /content/.hf_token)
export TOKENIZERS_PARALLELISM=false
export EVAL_PUSH_REPO=$FINAL_REPO   # generate.py checkpoints partial predictions here
GT=/content/work/meta/androidcontrol_test_gt.jsonl
GPX=${GENERAL_MAX_PIXELS:-${MAX_PIXELS:-774400}}   # identical general-eval image budget for base and FT
cd /content/work
R=experimentalmachines/AndroidControl-screen-agent-sft
OUT=/content/runs/$RUN
mkdir -p /content/eval $OUT/logs /content/data
log() { echo "[$(date +%T)] $RUN: $*"; }
receipt_ok() { MAX_STEPS=${MAX_STEPS:-} EPOCHS=${EPOCHS:-} MAX_AGENT_ROWS=${MAX_AGENT_ROWS:-} LR=${LR:-} LORA_R=${LORA_R:-} BS=${BS:-} GA=${GA:-} python - "$1" "$MODEL" "$OUT" <<'PY'
import json, os, sys
try:
    r = json.load(open(sys.argv[1])); a = r["args"]
    w = r.get("weights") or {}
    want = {"max_steps": int(os.environ.get("MAX_STEPS") or -1), "epochs": float(os.environ.get("EPOCHS") or 1),
            "max_agent_rows": int(os.environ.get("MAX_AGENT_ROWS") or 0), "lr": float(os.environ.get("LR") or 2e-4),
            "lora_r": int(os.environ.get("LORA_R") or 64), "bs": int(os.environ.get("BS") or 8),
            "grad_accum": int(os.environ.get("GA") or 4)}
    same_cfg = all(type(v)(a.get(k)) == v for k, v in want.items())
    ok = (same_cfg and a.get("model_id") == sys.argv[2] and a.get("out") == sys.argv[3] and w
          and all(v > 0 and os.path.getsize(os.path.join(sys.argv[3], "merged", k)) == v for k, v in w.items())
          and r.get("max_steps", 0) > 0 and r.get("global_step", 0) >= r["max_steps"])
except Exception:
    ok = False
sys.exit(0 if ok else 1)
PY
}
general_ok() { python -c "import json,sys;d=json.load(open('$1'));sys.exit(0 if d['mmstar']['n']>0 and d['mmlu']['n']>0 else 1)" 2>/dev/null; }
metrics_ok() {  # $1 metrics json, $2 predictions jsonl, $3 expected model
  [ -f "$1" ] && [ -f "$2" ] && python - "$1" "$3" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))["integrity"]
ok = m.get("complete") and not m.get("problems") and (m.get("manifest") or {}).get("model") == sys.argv[2]
sys.exit(0 if ok else 1)
PY
}
push_evals() {  # durable copy of every eval artifact after each step ("save frequently")
python - <<PY || fail "upload"
import os, glob
from huggingface_hub import HfApi
api = HfApi(); repo = "$FINAL_REPO"
api.create_repo(repo, private=True, exist_ok=True)
for f in glob.glob("/content/eval/*"):
    if os.path.isfile(f) and os.path.getsize(f) < 500_000_000:
        api.upload_file(path_or_fileobj=f, path_in_repo=f"eval/{os.path.basename(f)}", repo_id=repo)
if os.path.isdir("$OUT/logs"):
    api.upload_folder(folder_path="$OUT/logs", path_in_repo="training_logs", repo_id=repo)
PY
}

if [ -n "${EXTRA_PIP:-}" ]; then  # e.g. flash-linear-attention: Qwen3.5 Gated-DeltaNet fast kernels (math-identical)
  TV=$(python -c "import torch;print(torch.__version__)")
  log "pip install $EXTRA_PIP (torch pinned at $TV)"
  pip install -q $EXTRA_PIP "torch==${TV%%+*}" || fail "extra pip"
  python -c "import torch,sys; sys.exit(0 if torch.__version__=='$TV' else 1)" || { fail "torch changed by EXTRA_PIP"; exit 1; }
  python - <<'PY'
import importlib.metadata as md
for p in ("flash-linear-attention", "fla-core", "causal-conv1d", "triton"):
    try: print("extra-pip version", p, md.version(p), flush=True)
    except Exception: pass
try:
    from transformers.utils import import_utils as iu
    print("transformers sees fla:", [f() for n, f in vars(iu).items() if n.startswith("is_flash_linear") and callable(f)], flush=True)
except Exception as e:
    print("fla check skipped:", e, flush=True)
PY
fi

for spec in ${PRE_GENERAL_MODELS:-}; do  # e.g. "LiquidAI/LFM3-VL-2B=lfm3vl2b_base /content/runs/x/merged=lfm3vl2b_ft"
  m=${spec%%=*}; n=${spec##*=}
  general_ok /content/eval/${n}_general.summary.json || { log "general eval $n"; python eval_general.py --model $m --out /content/eval/${n}_general --bs ${EVAL_BS:-32} --max_pixels $GPX || fail "general $n"; }
done

if [ "${GENERAL_EVAL:-1}" = 1 ] && ! general_ok /content/eval/${RUN}_base_general.summary.json; then
  log "general eval BASE"; python eval_general.py --model $MODEL --out /content/eval/${RUN}_base_general --bs ${EVAL_BS:-32} --max_pixels $GPX || fail "general base"
fi
push_evals

REPLAY_ARGS=""
if [ "${REPLAY:-0}" = 1 ]; then
  WANT=$(sha256sum build_general_replay.py | cut -d" " -f1)
  if ! grep -q "$WANT" /content/data/replay/replay_receipt.json 2>/dev/null; then
    rm -rf /content/data/replay; log "build replay"
    python build_general_replay.py --out /content/data/replay --n 12000 || { fail "replay"; exit 1; }
  fi
  REPLAY_ARGS="--replay /content/data/replay"
fi
TEMPLATE_ARGS=${TEMPLATE:+--chat_template_path $TEMPLATE}
REGEX_ARGS=${TARGET_REGEX:+--target_regex $TARGET_REGEX}
STEP_ARGS="--epochs ${EPOCHS:-1}"; [ -n "${MAX_STEPS:-}" ] && STEP_ARGS="--max_steps $MAX_STEPS"
ROWS_ARGS=""; [ -n "${MAX_AGENT_ROWS:-}" ] && ROWS_ARGS="--max_agent_rows $MAX_AGENT_ROWS"
INLINE_ARGS=""; [ "${INLINE_THINK:-0}" = 1 ] && INLINE_ARGS="--inline_think"

if ! receipt_ok $OUT/train_receipt.json; then
  rm -rf $OUT/merged $OUT/lora $OUT/train_receipt.json
  rm -f /content/eval/${RUN}_ft.* /content/eval/${RUN}_ft_nothink_high.* /content/eval/${RUN}_ft_general.*  # new weights => stale FT evals
  log "train"
  python sft_vlm.py --model_id $MODEL --train ${TRAIN_DATA:-$R@train} --val $R@val --out $OUT $REPLAY_ARGS $ROWS_ARGS $STEP_ARGS \
    --max_pixels ${MAX_PIXELS:-774400} $INLINE_ARGS $TEMPLATE_ARGS $REGEX_ARGS \
    --bs ${BS:-8} --grad_accum ${GA:-4} --lr ${LR:-2e-4} --lora_r ${LORA_R:-64} --lora_alpha ${LORA_ALPHA:-128} \
    --modules_to_save --save_steps ${SAVE_STEPS:-100} --eval_steps ${EVAL_STEPS:-250} --workers ${WORKERS:-10} \
    --hub_repo $CKPT_REPO
fi
receipt_ok $OUT/train_receipt.json || { log "TRAINING FAILED"; push_evals; exit 1; }
log "push merged + adapter"
python - <<PY || fail "upload merged"
from huggingface_hub import HfApi
api = HfApi(); repo = "$FINAL_REPO"
api.create_repo(repo, private=True, exist_ok=True)
api.upload_folder(folder_path="$OUT/merged", repo_id=repo, commit_message="merged LoRA -> full weights")
api.upload_folder(folder_path="$OUT/lora", path_in_repo="lora_adapter", repo_id=repo)
PY
push_evals

if [ "${GENERAL_EVAL:-1}" = 1 ] && ! general_ok /content/eval/${RUN}_ft_general.summary.json; then
  log "general eval FT"; python eval_general.py --model $OUT/merged --out /content/eval/${RUN}_ft_general --bs ${EVAL_BS:-32} --max_pixels $GPX || fail "general ft"
  push_evals
fi
if ! python score.py /content/eval/${RUN}_ft.jsonl --gt $GT --expect model=$OUT/merged,max_pixels=${MAX_PIXELS:-774400},enable_thinking=${FT_THINK:-1} --out /content/eval/${RUN}_ft.metrics.json > /dev/null 2>&1; then
  log "AndroidControl test FT"
  python generate.py --model $OUT/merged --data $R@test --out /content/eval/${RUN}_ft.jsonl --enable_thinking ${FT_THINK:-1} \
    --bs ${EVAL_BS:-32} --max_pixels ${MAX_PIXELS:-774400} && python score.py /content/eval/${RUN}_ft.jsonl --gt $GT --expect model=$OUT/merged,max_pixels=${MAX_PIXELS:-774400},enable_thinking=${FT_THINK:-1} --out /content/eval/${RUN}_ft.metrics.json > /dev/null || fail "ft AC eval"
  push_evals
fi
if [ "${BASE_AC_EVAL:-1}" = 1 ] && ! python score.py /content/eval/${RUN}_base.jsonl --gt $GT --expect model=$MODEL,max_pixels=${MAX_PIXELS:-774400},enable_thinking=0 --out /content/eval/${RUN}_base.metrics.json > /dev/null 2>&1; then
  log "AndroidControl test BASE (no-think)"
  python generate.py --model $MODEL --data $R@test --out /content/eval/${RUN}_base.jsonl --enable_thinking 0 \
    --bs ${EVAL_BS:-32} --max_pixels ${MAX_PIXELS:-774400} && python score.py /content/eval/${RUN}_base.jsonl --gt $GT --expect model=$MODEL,max_pixels=${MAX_PIXELS:-774400},enable_thinking=0 --out /content/eval/${RUN}_base.metrics.json > /dev/null || fail "base AC eval"
  push_evals
fi

# ---- v2 extras: held-out dev splits for several models + forced-choice general eval of the FT model
# DEV_MODELS="hub_or_FT=name:think ..." (FT = this run's merged weights); DEV_REPO holds dev_odyssey/dev_amex/dev_screenqa
for spec in ${DEV_MODELS:-}; do
  m=${spec%%=*}; rest=${spec##*=}; n=${rest%%:*}; th=${rest##*:}
  [ "$m" = FT ] && m=$OUT/merged
  for sp in ${DEV_SPLITS:-dev_odyssey dev_amex dev_screenqa}; do
    N=$(python - <<PY
from huggingface_hub import HfApi
from datasets import load_dataset
fs = HfApi().list_repo_files("$DEV_REPO", repo_type="dataset")
print(len(load_dataset("$DEV_REPO", data_files={"$sp": [f for f in fs if f.startswith("data/$sp-")]}, split="$sp")))
PY
)
    if ! python score_dev.py /content/eval/${n}_${sp}.jsonl --expect_n $N --out /content/eval/${n}_${sp}.metrics.json > /dev/null 2>&1; then
      log "dev eval $n $sp ($N rows)"
      python generate.py --model $m --data $DEV_REPO@$sp --out /content/eval/${n}_${sp}.jsonl --enable_thinking $th \
        --bs ${EVAL_BS:-32} --max_pixels ${MAX_PIXELS:-774400} \
        && python score_dev.py /content/eval/${n}_${sp}.jsonl --expect_n $N --out /content/eval/${n}_${sp}.metrics.json || fail "dev $n $sp"
      push_evals
    fi
  done
done
if [ "${LOGPROB_FT:-0}" = 1 ] && ! general_ok /content/eval/${RUN}_ft_general_logprob.summary.json; then
  log "general eval FT (forced-choice logprob)"
  python eval_general.py --model $OUT/merged --out /content/eval/${RUN}_ft_general_logprob --mode logprob --bs 16 --max_pixels $GPX || fail "general logprob ft"
  push_evals
fi
if [ "${MATCHED_NOTHINK:-1}" = 1 ] && ! python score.py /content/eval/${RUN}_ft_nothink_high.jsonl --gt $GT --modes high --expect model=$OUT/merged,max_pixels=${MAX_PIXELS:-774400},enable_thinking=0 --out /content/eval/${RUN}_ft_nothink_high.metrics.json > /dev/null 2>&1; then
  log "AndroidControl test FT matched no-think (high-level)"
  python generate.py --model $OUT/merged --data $R@test --out /content/eval/${RUN}_ft_nothink_high.jsonl --enable_thinking 0 \
    --filter_mode high --bs ${EVAL_BS:-32} --max_pixels ${MAX_PIXELS:-774400} \
    && python score.py /content/eval/${RUN}_ft_nothink_high.jsonl --gt $GT --modes high --expect model=$OUT/merged,max_pixels=${MAX_PIXELS:-774400},enable_thinking=0 --out /content/eval/${RUN}_ft_nothink_high.metrics.json > /dev/null \
    && touch /content/eval/${RUN}_ft_nothink_high.jsonl.done || fail "ft nothink eval"
  push_evals
fi
if [ "$FAILED" = 1 ]; then log "PIPELINE FINISHED WITH FAILURES"; exit 1; fi
log "PIPELINE DONE"
