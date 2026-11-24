#!/bin/bash
# Round 7 / v4.5 on an AWS SageMaker training job (ml.g7e.2xlarge: 1x RTX PRO 6000, 96 GB). docs/PREREG_v45.md.
# Channels: code (this script, training/eval code, ground truth, v4 reference numbers) and data (the round-7 mix:
# train, ac_val, gate splits, androidlens/ for the scorer). Everything written under /opt/ml/checkpoints is synced to S3
# while the job runs (checkpoints, merged weights, predictions, metrics, logs), so nothing waits for the job to end and
# a restarted job resumes from its last checkpoint.
#   R7_MODE=smoke : 30 steps each of bs 4 x 8 and bs 8 x 4 (no gradient checkpointing) on 2,000 rows -> speed and
#                   memory; then every eval on 16 rows, every scorer and the gate script (numbers meaningless)
#   R7_MODE=full  : candidate D = LFM3-VL-2B + LoRA (v4 recipe) for one pass over the train split (32 rows per step),
#                   then the five gate evals on all rows, the scorers and the pre-registered offline gate
set -uo pipefail
C=/opt/ml/input/data/code; D=/opt/ml/input/data/data; CK=/opt/ml/checkpoints; W=/opt/work
mkdir -p $W $CK/eval /opt/ml/model
log() { echo "[$(date -u +%T)] r7: $*" | tee -a $CK/r7.log; }
MODE=${R7_MODE:-smoke}; BS=${R7_BS:-4}; GA=${R7_GA:-8}
cp $C/* $W/ && cd $W || exit 1
export TOKENIZERS_PARALLELISM=false HF_HUB_DISABLE_TELEMETRY=1
log "mode $MODE; gpu $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader); $(nproc) CPUs; $(free -g | awk '/Mem/{print $2}') GB RAM"
if [ ! -f $CK/.pip_ok ] || ! python -c "import trl" 2>/dev/null; then
  pip install -q "torch==2.14.1" "torchvision==0.29.1" "torchao==0.18.0" "trl==1.16.0" "transformers==5.20.2" "peft==0.21.2" \
    "accelerate==1.15.0" "datasets==5.1.0" "huggingface-hub==2.3.0" "tokenizers==0.23.3" "safetensors==0.8.0" tensorboard pillow pyarrow \
    > $CK/pip.log 2>&1 || { log "PIP FAILED"; tail -5 $CK/pip.log; exit 1; }
  touch $CK/.pip_ok
fi
log "versions $(python -c 'import torch, transformers, trl; print(torch.__version__, transformers.__version__, trl.__version__, torch.cuda.is_available(), torch.cuda.get_device_capability())')"
N=$(python -c "from datasets import load_from_disk as l; print(len(l('$D/train')))")
log "train rows $N"

train() {  # out steps bs ga extra...
  local O=$1 ST=$2 B=$3 G=$4; shift 4
  [ -f $O/train_receipt.json ] && return 0
  python sft_vlm.py --model_id LiquidAI/LFM3-VL-2B --model_revision 23387beda43c60310348e83e25f78f33c3140d3a --train $D/train --val $D/ac_val --out $O --max_steps $ST --max_pixels 774400 \
    --bs $B --grad_accum $G --no_gc --lora_r 64 --lora_alpha 128 --modules_to_save --workers 6 "$@" > $O.log 2>&1
}

evals() {  # model name limit
  local M=$1 NM=$2 L=$3 LIM="" sp
  [ "$L" != 0 ] && LIM="--limit $L"
  for sp in test_ac_high dev_answer dev_complete dev_androidlens_high dev_memgui; do
    [ -f $CK/eval/${NM}_${sp}.jsonl.done ] && continue
    log "eval $NM $sp"
    python generate.py --model $M --data $D/$sp --out $CK/eval/${NM}_${sp}.jsonl --enable_thinking 1 --bs 32 --max_pixels 774400 $LIM \
      > $CK/eval/${NM}_${sp}.gen.log 2>&1 && touch $CK/eval/${NM}_${sp}.jsonl.done || { log "EVAL FAILED $sp"; tail -5 $CK/eval/${NM}_${sp}.gen.log; return 1; }
  done
  local INC=""; [ "$L" != 0 ] && INC="--allow_incomplete"
  python score.py $CK/eval/${NM}_test_ac_high.jsonl --gt androidcontrol_test_gt.jsonl --modes high --allow_incomplete \
    --out $CK/eval/${NM}_test_ac_high.metrics.json > /dev/null || { log "AC SCORE FAILED"; return 1; }
  for sp in dev_answer dev_complete dev_memgui; do
    local EX=""; [ "$L" = 0 ] && EX="--expect_n $(python -c "from datasets import load_from_disk as l; print(len(l('$D/$sp')))")"
    python score_dev.py $CK/eval/${NM}_${sp}.jsonl $EX --out $CK/eval/${NM}_${sp}.metrics.json > /dev/null || { log "SCORE FAILED $sp"; return 1; }
  done
  python - $CK/eval/${NM}_dev_androidlens_high.jsonl $D/androidlens/dev_androidlens_high.parquet <<'PY' || { log "ANDROIDLENS ADAPT FAILED"; return 1; }
import json, sys, pyarrow.parquet as pq
ids = {(r["episode_id"], int(r["step_idx"])): r["id"] for r in pq.read_table(sys.argv[2], columns=["id", "episode_id", "step_idx"]).to_pylist()}
with open(sys.argv[1].replace(".jsonl", ".ids.jsonl"), "w") as fo:
    for l in open(sys.argv[1]):
        r = json.loads(l); fo.write(json.dumps({"id": ids[(str(r["episode_id"]), int(r["step_idx"]))], "output": r["output"]}) + "\n")
PY
  python score_androidlens.py $CK/eval/${NM}_dev_androidlens_high.ids.jsonl --data $D/androidlens $INC \
    --out $CK/eval/${NM}_dev_androidlens_high.metrics.json > /dev/null || { log "ANDROIDLENS SCORE FAILED"; return 1; }
  python sm_r7_gate.py --name $NM --eval $CK/eval --v4 v4_reference.json --out $CK/eval/${NM}_offline_gate.json | tee -a $CK/r7.log
}

speed() {  # run dir -> "s/step rows/s peak GB"
  python - $1/logs/train_log.jsonl <<'PY'
import json, sys
recs = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
el = {x["step"]: x["elapsed_s"] for x in recs if "loss" in x}
s = (el[30] - el[10]) / 20
print(f"{s:.2f} s/step, {32 / s:.2f} rows/s, peak {max(x.get('gpu_mem_gb', 0) for x in recs)} GB")
PY
}

if [ "$MODE" = smoke ]; then
  for cfg in "4 8" "8 4"; do
    set -- $cfg
    train $CK/smoke_bs$1 30 $1 $2 --max_agent_rows 2000 --save_steps 100000 --eval_steps 100000 || { log "SMOKE TRAIN FAILED bs$1"; tail -5 $CK/smoke_bs$1.log; exit 1; }
    log "SPEED bs $1 x $2: $(speed $CK/smoke_bs$1)"
  done
  evals $CK/smoke_bs8/merged smoke 16 || exit 1
  log "SMOKE OK"
  exit 0
fi

ST=$(( (N + 31) / 32 ))
log "D: one pass = $ST steps x 32 rows (bs $BS x $GA), lr 2e-4 cosine, LoRA r64"
train $CK/run $ST $BS $GA --save_steps 250 --eval_steps 1000 || { log "TRAIN FAILED"; tail -20 $CK/run.log; exit 1; }
log "trained: $(python -c "import json; r=json.load(open('$CK/run/train_receipt.json')); print(r['global_step'], 'steps', round(r['summary'].get('train_runtime', 0) / 3600, 2), 'h')")"
evals $CK/run/merged r7d 0 || exit 1
cp $CK/eval/r7d_offline_gate.json $CK/r7.log /opt/ml/model/ 2>/dev/null
log "R7 DONE"
