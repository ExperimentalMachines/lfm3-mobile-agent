#!/bin/bash
# Round 10 / v4.8 on an AWS SageMaker training job (owner's choice: ml.g6e.2xlarge, 1x L40S 48 GB). docs/PREREG_v48.md.
# Channels: code, and e (E's merged weights, for E's baseline on the round-9/10 probes with the same evaluator). Data comes straight from the public Hub dataset (pinned revision), so the job needs
# no data channel and no token; everything under /opt/ml/checkpoints (run folder with checkpoints, merged weights,
# predictions, metrics, logs) is synced to S3 while the job runs, and a restarted job resumes from it.
# Same pinned packages and eval scripts as the Modal / Colab runs (/content layout).
#   R9_MODE=smoke : 30 steps of each micro-batch in R9_CFGS on 2,000 rows -> s/step and peak memory; E's baseline on
#                   the probes (all rows: real numbers); then every eval, scorer and the gate on 16 rows (numbers meaningless)
#   R9_MODE=full  : candidate G = LFM3-VL-2B + LoRA (E's recipe), one pass over v4.8 train (32 rows per step), then the
#                   round-10 gate evals (vm_r10_eval.sh; E's baseline first if not done)
set -uo pipefail
C=/opt/ml/input/data/code; CK=/opt/ml/checkpoints
mkdir -p $CK/runs $CK/eval /content/data /opt/ml/model
ln -sfn $CK/runs /content/runs; ln -sfn $CK/eval /content/eval
rm -rf /content/work && mkdir -p /content/work/meta && cp $C/*.py $C/*.sh $C/*.json /content/work/ && cp $C/meta/* /content/work/meta/
cd /content/work || exit 1
log() { echo "[$(date -u +%T)] r10: $*" | tee -a $CK/r9.log; }
DATA=${R9_DATA:-experimentalmachines/MobileAgent-SFT-v4.8}; export DREPO=$DATA; ME=/opt/ml/input/data/e
MODE=${R9_MODE:-smoke}; DREV=${R9_DREV:?}; export DREV
MREV=23387beda43c60310348e83e25f78f33c3140d3a; VREV=f88a843239b7e0b68ea8fcb6eb0c5539276d64eb
export TOKENIZERS_PARALLELISM=false HF_HUB_DISABLE_TELEMETRY=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HF_HOME=/opt/ml/input/hf
log "mode $MODE; gpu $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader); $(nproc) CPUs; $(free -g | awk '/Mem/{print $2}') GB RAM; disk $(df -h /opt/ml | awk 'NR==2{print $4}') free"
if [ ! -f $CK/.pip_ok ] || ! python -c "import trl" 2>/dev/null; then
  pip install -q "torch==2.14.1" "torchvision==0.29.1" "torchao==0.18.0" "trl==1.16.0" "transformers==5.20.2" "peft==0.21.2" \
    "accelerate==1.15.0" "datasets==5.1.0" "huggingface-hub==2.3.0" "tokenizers==0.23.3" "safetensors==0.8.0" tensorboard pillow pyarrow numpy hf_xet \
    > $CK/pip.log 2>&1 || { log "PIP FAILED"; tail -5 $CK/pip.log; exit 1; }
  touch $CK/.pip_ok
fi
log "versions $(python -c 'import torch, transformers, trl; print(torch.__version__, transformers.__version__, trl.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))')"

train() {  # out steps bs ga extra...
  local O=$1 ST=$2 B=$3 G=$4; shift 4
  [ -f $O/train_receipt.json ] && return 0
  python sft_vlm.py --model_id LiquidAI/LFM3-VL-2B --model_revision $MREV \
    --train $DATA@train#$DREV --val experimentalmachines/MobileAgent-SFT-v1@val#$VREV \
    --out $O --max_steps $ST --max_pixels 774400 --bs $B --grad_accum $G --lora_r 64 --lora_alpha 128 --modules_to_save \
    --workers 6 "$@" > $O.log 2>&1
}

speed() {  # run dir -> "s/step, peak GB"
  python - $1/logs/train_log.jsonl <<'PY'
import json, sys
recs = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
el = {x["step"]: x["elapsed_s"] for x in recs if "loss" in x}
ks = sorted(el); a, b = ks[len(ks) // 3], ks[-1]
s = (el[b] - el[a]) / (b - a)
print(f"{s:.2f} s/step (steps {a}-{b}), peak {max(x.get('gpu_mem_gb', 0) for x in recs)} GB")
PY
}

if [ "$MODE" = smoke ]; then
  OK=""
  for cfg in ${R9_CFGS:-"4:8:nogc" "2:16:nogc"}; do
    IFS=: read B G GCF <<< "$cfg"; X=""; [ "$GCF" = nogc ] && X="--no_gc"
    O=/content/runs/smoke_${B}x${G}_${GCF}
    if train $O 30 $B $G --max_agent_rows 2000 --save_steps 100000 --eval_steps 100000 $X; then
      log "SPEED bs $B x $G $GCF: $(speed $O)"; OK=${OK:-$O}
    else
      log "bs $B x $G $GCF failed: $(grep -m1 -oE 'OutOfMemoryError|Error[^:]*' $O.log || echo see log)"
    fi
  done
  [ -n "$OK" ] || { log "SMOKE TRAIN FAILED"; exit 1; }
  MODEL_E=$ME E_ONLY=1 LIMIT=0 bash vm_r10_eval.sh 2>&1 | tee -a $CK/r9.log   # E's baseline, all probe rows
  grep -q "E BASELINE DONE" $CK/r9.log || { log "SMOKE FAILED: E baseline"; exit 1; }
  MODEL=$OK/merged NAME=smoke10 LIMIT=16 bash vm_r10_eval.sh 2>&1 | tee -a $CK/r9.log
  grep -q "EVAL DONE smoke10" $CK/r9.log && log "SMOKE OK" || { log "SMOKE FAILED: evals"; exit 1; }
  exit 0
fi

B=${R9_BS:?}; G=${R9_GA:?}; X=""; [ "${R9_GC:-gc}" = nogc ] && X="--no_gc"
ST=${R9_MAX_STEPS:?}
log "G: one pass = $ST steps x 32 rows (bs $B x $G, ${R9_GC:-gc}), lr 2e-4 cosine, LoRA r64; resumes from $CK/runs/r9g"
train /content/runs/r10g $ST $B $G --save_steps 100 --eval_steps 1000 $X || { log "TRAIN FAILED"; tail -20 /content/runs/r10g.log | tee -a $CK/r9.log; exit 1; }
log "trained: $(python -c "import json; r=json.load(open('/content/runs/r10g/train_receipt.json')); print(r['global_step'], 'steps', round(r['summary'].get('train_runtime', 0) / 3600, 2), 'h')")"
MODEL=/content/runs/r10g/merged NAME=r10g MODEL_E=$ME LIMIT=0 bash vm_r10_eval.sh 2>&1 | tee -a $CK/r9.log
cp $CK/eval/r10g_offline_gate.json $CK/r9.log /opt/ml/model/ 2>/dev/null
log "R10 G DONE"
