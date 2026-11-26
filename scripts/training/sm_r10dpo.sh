#!/bin/bash
# Round 10 / E-DPO on an AWS SageMaker training job (ml.g6e.2xlarge, 1x L40S 48 GB). docs/preregistrations/round-10-multi-part-false-completes.md (2026-11-25 14:20).
# Channels: code; e (E's merged weights); cand (candidate rows, mode pairs) or pairs (job A's pairs, mode dpo).
# Everything under /opt/ml/checkpoints is synced to S3 while the job runs; a restarted job resumes (greedy.jsonl, receipt).
#   R10_MODE=pairs : E decodes greedily on the candidates -> balanced early/missed-stop pairs in $CK/pairs
#                    (data/stopdpo_pairs.py); then a 2-step DPO smoke on 16 pairs (memory, rendering, end tokens)
#   R10_MODE=dpo   : DPO on the pairs (one pass, train/dpo_vlm.py), merge, then E's round-8 gate (vm_r8_eval.sh)
set -uo pipefail
C=/opt/ml/input/data/code; CK=/opt/ml/checkpoints; ME=/opt/ml/input/data/e
mkdir -p $CK/runs $CK/eval /content/data /opt/ml/model
ln -sfn $CK/runs /content/runs; ln -sfn $CK/eval /content/eval
rm -rf /content/work && mkdir -p /content/work/meta && cp $C/*.py $C/*.sh $C/*.json /content/work/ && cp $C/meta/* /content/work/meta/
cd /content/work || exit 1
log() { echo "[$(date -u +%T)] r10dpo: $*" | tee -a $CK/r10dpo.log; }
MODE=${R10_MODE:-pairs}; BS=${R10_BS:-4}; GA=${R10_GA:-8}
export TOKENIZERS_PARALLELISM=false HF_HUB_DISABLE_TELEMETRY=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HF_HOME=/opt/ml/input/hf
log "mode $MODE; gpu $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader); E files: $(ls $ME | wc -l)"
if [ ! -f $CK/.pip_ok ] || ! python -c "import trl" 2>/dev/null; then
  pip install -q "torch==2.14.1" "torchvision==0.29.1" "torchao==0.18.0" "trl==1.16.0" "transformers==5.20.2" "peft==0.21.2" \
    "accelerate==1.15.0" "datasets==5.1.0" "huggingface-hub==2.3.0" "tokenizers==0.23.3" "safetensors==0.8.0" tensorboard pillow pyarrow numpy hf_xet \
    > $CK/pip.log 2>&1 || { log "PIP FAILED"; tail -5 $CK/pip.log; exit 1; }
  touch $CK/.pip_ok
fi
DPO="--beta 0.1 --sft_weight 1.0 --lr 1e-5 --bs $BS --grad_accum $GA"
if [ "$MODE" = pairs ]; then
  [ -f $CK/pairs/dataset_info.json ] || python stopdpo_pairs.py --cand /opt/ml/input/data/cand --model $ME --out $CK/pairs --bs 48 --max_new_tokens 96 \
      --work $CK/gen ${R10_LIMIT:+--limit $R10_LIMIT} > $CK/pairs.log 2>&1 || { log "PAIRS FAILED"; tail -20 $CK/pairs.log | tee -a $CK/r10dpo.log; exit 1; }
  log "$(grep R10_PAIRS_DONE $CK/pairs.log | cut -c1-900)"
  python dpo_vlm.py --model $ME --pairs $CK/pairs --out /content/runs/dposmoke --smoke 16 $DPO > $CK/dposmoke.log 2>&1 \
    && log "DPO SMOKE OK: $(grep -o '"peak_gpu_mem_gb": [0-9.]*' /content/runs/dposmoke/logs/train_summary.json)" \
    || { log "DPO SMOKE FAILED"; tail -20 $CK/dposmoke.log | tee -a $CK/r10dpo.log; exit 1; }
  exit 0
fi
[ -f /content/runs/edpo/train_receipt.json ] || python dpo_vlm.py --model $ME --pairs /opt/ml/input/data/pairs --out /content/runs/edpo $DPO \
  > $CK/edpo.log 2>&1 || { log "DPO FAILED"; tail -20 $CK/edpo.log | tee -a $CK/r10dpo.log; exit 1; }
log "trained: $(cat /content/runs/edpo/logs/train_summary.json | tr -d '\n' | cut -c1-400)"
MODEL=/content/runs/edpo/merged NAME=r10edpo LIMIT=0 DREV=0ace5559e6c0b808a5ddf4e4ce9831d1d3614471 bash vm_r8_eval.sh 2>&1 | tee -a $CK/r10dpo.log
cp $CK/eval/r10edpo_offline_gate.json /opt/ml/model/ 2>/dev/null
log "R10 E-DPO DONE"
