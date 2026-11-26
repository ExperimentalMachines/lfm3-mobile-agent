#!/bin/bash
# Round 12 / candidate E-V on an AWS SageMaker training job (ml.g6.2xlarge, 1x L4 24 GB). docs/PREREG_v410.md.
# Channels: code; e (E's merged weights); r12in (ody_term2.parquet = the 1,766 GUI-Odyssey terminal candidates,
# claude_ody_terminal_verdicts.jsonl, claude_next_actions.jsonl, notdone_split.json, r11_mix_stats.json, claude_ac_complete_verdicts.jsonl). E's training split comes from the public Hub
# (pinned revision), so the job needs no token. /opt/ml/checkpoints (runs, evals, logs) is synced to S3 while the job runs;
# a restarted job resumes (checkpoints every 100 steps, finished evals); the mix is rebuilt (deterministic, seed 12).
#   R12_MODE=smoke : mix with 40 terminal rows per class, 2,000 rows (E's full split is read, so the history check is real
#                    for those rows); 30 steps for each micro-batch in R12_CFGS -> s/step and peak memory; then all four
#                    probes for E and the smoke model, every round-8 eval and both gates on 16 rows (numbers meaningless)
#   R12_MODE=full  : the 32,000-row mix; 1,000 steps (R12_BS x R12_GA = 32 rows); merge; E and E-V on the M and V probes; the
#                    round-8 gate evals on the v4.6 splits (vm_r8_eval.sh); sm_r12_gate.py
set -uo pipefail
C=/opt/ml/input/data/code; CK=/opt/ml/checkpoints; ME=/opt/ml/input/data/e; IN=/opt/ml/input/data/r12in
mkdir -p $CK/runs $CK/eval /content/data /opt/ml/model
ln -sfn $CK/runs /content/runs; ln -sfn $CK/eval /content/eval
rm -rf /content/work && mkdir -p /content/work/meta && cp $C/*.py $C/*.sh $C/*.json /content/work/ && cp $C/meta/* /content/work/meta/
cd /content/work || exit 1
log() { echo "[$(date -u +%T)] r12: $*" | tee -a $CK/r12.log; }
MODE=${R12_MODE:-smoke}; DREV=0ace5559e6c0b808a5ddf4e4ce9831d1d3614471; D=/content/data/r12; EV=/content/eval
export TOKENIZERS_PARALLELISM=false HF_HUB_DISABLE_TELEMETRY=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HF_HOME=/opt/ml/input/hf
log "mode $MODE; gpu $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader); $(nproc) CPUs; E files $(ls $ME | wc -l); inputs: $(ls $IN | tr '\n' ' ')"
if [ ! -f $CK/.pip_ok ] || ! python -c "import trl" 2>/dev/null; then
  pip install -q "torch==2.14.1" "torchvision==0.29.1" "torchao==0.18.0" "trl==1.16.0" "transformers==5.20.2" "peft==0.21.2" \
    "accelerate==1.15.0" "datasets==5.1.0" "huggingface-hub==2.3.0" "tokenizers==0.23.3" "safetensors==0.8.0" tensorboard pillow pyarrow numpy hf_xet \
    > $CK/pip.log 2>&1 || { log "PIP FAILED"; tail -5 $CK/pip.log; exit 1; }
  touch $CK/.pip_ok
fi

# ---- 1. the mix and the probes (data/r12_mix.py)
MX=""; [ "$MODE" = smoke ] && MX="--limit 40 --n_mix 2000"
if [ ! -f $D/mix_stats.json ]; then
  python r12_mix.py --term $IN/ody_term2.parquet --verdicts $IN/claude_ody_terminal_verdicts.jsonl --written $IN/claude_next_actions.jsonl --split $IN/notdone_split.json --r11stats $IN/r11_mix_stats.json --acv $IN/claude_ac_complete_verdicts.jsonl --out $D $MX > $CK/mix.log 2>&1 \
    || { log "MIX FAILED"; grep -v Warning $CK/mix.log | tail -5 | tee -a $CK/r12.log; cp $D*_diffs.json $CK/ 2>/dev/null; exit 1; }
fi
cp $D/mix_stats.json $CK/
log "$(grep -o 'R12_MIX_DONE.*' $CK/mix.log | cut -c1-1500)"

train() {  # out steps bs ga extra...
  local O=$1 ST=$2 B=$3 G=$4; shift 4
  [ -f $O/train_receipt.json ] && return 0
  python sft_vlm.py --model_id $ME --train $D/mix --out $O --max_steps $ST --max_pixels 774400 --bs $B --grad_accum $G \
    --lr 1e-4 --warmup 0.03 --scheduler cosine --lora_r 64 --lora_alpha 128 --modules_to_save --workers 6 "$@" > $O.log 2>&1
}

speed() {  # run dir -> "s/step, peak GB"
  python - $1/logs/train_log.jsonl <<'PY'
import json, sys
recs = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
el = {x["step"]: x["elapsed_s"] for x in recs if "loss" in x}
ks = sorted(el); a, b = ks[len(ks) // 3], ks[-1]
print(f"{(el[b] - el[a]) / (b - a):.2f} s/step (steps {a}-{b}), peak {max(x.get('gpu_mem_gb', 0) for x in recs)} GB")
PY
}

probes() {  # name model limit
  for p in M_done M_notdone V_done V_notdone; do
    [ -f $EV/$1_probe_$p.jsonl.done ] && continue
    log "probe $1 $p"
    python generate.py --model $2 --data $D/probe_$p --out $EV/$1_probe_$p.jsonl --enable_thinking 1 --bs 32 --max_pixels 774400 --limit $3 \
      > $EV/$1_probe_$p.gen.log 2>&1 && touch $EV/$1_probe_$p.jsonl.done || { log "PROBE FAILED $1 $p"; tail -5 $EV/$1_probe_$p.gen.log | tee -a $CK/r12.log; return 1; }
  done
}

gate() {  # name limit
  MODEL=$2 NAME=$1 LIMIT=$3 DREV=$DREV bash vm_r8_eval.sh 2>&1 | tee -a $CK/r12.log
  grep -q "EVAL DONE $1" $CK/r12.log || { log "ROUND-8 EVALS FAILED $1"; return 1; }
  python sm_r12_gate.py --name $1 --eval $EV --out $EV/$1_r12_gate.json 2>&1 | tee -a $CK/r12.log
  grep -q "R12 GATE $1" $CK/r12.log
}

if [ "$MODE" = smoke ]; then
  OK=""
  for cfg in ${R12_CFGS:-"2:16:nogc"}; do
    IFS=: read B G GCF <<< "$cfg"; X=""; [ "$GCF" = nogc ] && X="--no_gc"
    O=/content/runs/smoke_${B}x${G}_${GCF}
    if train $O 30 $B $G --save_steps 100000 --eval_steps 100000 $X; then
      log "SPEED bs $B x $G $GCF: $(speed $O)"; OK=${OK:-$O}
    else
      log "bs $B x $G $GCF failed: $(grep -m1 -oE 'OutOfMemoryError|Error[^:]*' $O.log || echo see log)"
    fi
  done
  [ -n "$OK" ] || { log "SMOKE TRAIN FAILED"; exit 1; }
  probes e $ME 16 && probes smoke12 $OK/merged 16 || { log "SMOKE FAILED: probes"; exit 1; }
  gate smoke12 $OK/merged 16 && log "SMOKE OK" || { log "SMOKE FAILED: gate"; exit 1; }
  exit 0
fi

B=${R12_BS:?}; G=${R12_GA:?}; X=""; [ "${R12_GC:-gc}" = nogc ] && X="--no_gc"
log "E-V: 1,000 steps x 32 rows (bs $B x $G, ${R12_GC:-gc}), lr 1e-4 cosine, new LoRA r64 on E; resumes from $CK/runs/r12ev"
probes e $ME 0 || exit 1
train /content/runs/r12ev 1000 $B $G --save_steps 100 --eval_steps 100000 $X || { log "TRAIN FAILED"; tail -20 /content/runs/r12ev.log | tee -a $CK/r12.log; exit 1; }
log "trained: $(python -c "import json; r=json.load(open('/content/runs/r12ev/train_receipt.json')); print(r['global_step'], 'steps', round(r['summary'].get('train_runtime', 0) / 3600, 2), 'h')")"
probes r12ev /content/runs/r12ev/merged 0 || exit 1
gate r12ev /content/runs/r12ev/merged 0 || { log "GATE FAILED TO RUN"; exit 1; }
cp $EV/r12ev_r12_gate.json $EV/r12ev_offline_gate.json $CK/r12.log /opt/ml/model/ 2>/dev/null
log "R12 E-V DONE"
