#!/bin/bash
# Round 13 / candidate E-S (semi-online RL from E) on an AWS SageMaker training job. docs/preregistrations/round-13-yardstick-own-history.md.
# Channels: code; e (E's merged weights); r13in (ody_term2.parquet, claude_ody_terminal_verdicts.jsonl,
# claude_next_actions.jsonl, claude_ac_complete_verdicts.jsonl, rl_probe_exclude.json). E's training split comes from the
# public Hub (pinned). /opt/ml/checkpoints is synced to S3; a restarted job resumes from the last saved adapter.
#   R13_MODE=smoke : 2 batches (B 2, G 4, 6 steps max) on the full episode build -> s/batch and memory; merge; every
#                    round-8 eval and the round-12 probes on 16 rows (numbers meaningless)
#   R13_MODE=full  : R13_BATCHES batches (B 4, G 4); merge; round-8 evals and the round-12 probes in full; sm_r13_gate.py
set -uo pipefail
C=/opt/ml/input/data/code; CK=/opt/ml/checkpoints; ME=/opt/ml/input/data/e; IN=/opt/ml/input/data/r13in
mkdir -p $CK/runs $CK/eval /content/data /opt/ml/model
ln -sfn $CK/runs /content/runs; ln -sfn $CK/eval /content/eval
rm -rf /content/work && mkdir -p /content/work/meta && cp $C/*.py $C/*.sh $C/*.json /content/work/ && cp $C/meta/* /content/work/meta/
cd /content/work || exit 1
log() { echo "[$(date -u +%T)] r13: $*" | tee -a $CK/r13.log; }
MODE=${R13_MODE:-smoke}; DREV=0ace5559e6c0b808a5ddf4e4ce9831d1d3614471; EV=/content/eval; O=/content/runs/r13es
export TOKENIZERS_PARALLELISM=false HF_HUB_DISABLE_TELEMETRY=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HF_HOME=/opt/ml/input/hf
log "mode $MODE; gpu $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader); $(nproc) CPUs; E files $(ls $ME | wc -l); inputs: $(ls $IN | tr '\n' ' ')"
if [ ! -f $CK/.pip_ok ] || ! python -c "import peft" 2>/dev/null; then
  pip install -q "torch==2.14.1" "torchvision==0.29.1" "torchao==0.18.0" "trl==1.16.0" "transformers==5.20.2" "peft==0.21.2" \
    "accelerate==1.15.0" "datasets==5.1.0" "huggingface-hub==2.3.0" "tokenizers==0.23.3" "safetensors==0.8.0" tensorboard pillow pyarrow numpy hf_xet \
    > $CK/pip.log 2>&1 || { log "PIP FAILED"; tail -5 $CK/pip.log; exit 1; }
  touch $CK/.pip_ok
fi
if [ "$MODE" = smoke ]; then ARGS="--batches 2 --B 2 --G 4 --max_steps 6 --save_every 1"; LIM=16
else ARGS="--batches ${R13_BATCHES:?} --B 4 --G 4 --max_steps 12 --save_every 5"; LIM=0; fi
RES=""; [ -f $O/state.json ] && [ -d $O/adapter ] && RES="--resume $O/adapter"
if ! grep -q '"done": true' $O/state.json 2>/dev/null; then
  log "semi-online RL: $ARGS lr ${R13_LR:-3e-5} $RES"
  python semi_online_rl.py --model_id $ME --out $O --term $IN/ody_term2.parquet --verdicts $IN/claude_ody_terminal_verdicts.jsonl \
    --written $IN/claude_next_actions.jsonl --acv $IN/claude_ac_complete_verdicts.jsonl --probe_ids $IN/rl_probe_exclude.json \
    --lr ${R13_LR:-3e-5} --gamma 0.5 --omega 1.0 --patch 1 --temperature 1.0 --history_steps 24 --notes 1 $ARGS $RES \
    > $O.log 2>&1 || { log "RL FAILED"; grep -v Warning $O.log | tail -15 | tee -a $CK/r13.log; exit 1; }
fi
log "$(grep -m1 'episodes {' $O.log | cut -c1-600)"
log "rl: $(tail -1 $O/rl_log.jsonl)"
[ -f $O/merged/config.json ] || python merge_adapter.py --base $ME --adapter $O/adapter --out $O/merged >> $O.log 2>&1 \
  || { log "MERGE FAILED"; tail -5 $O.log | tee -a $CK/r13.log; exit 1; }
N=$([ "$MODE" = smoke ] && echo smoke13 || echo r13es)
# the round-12 probes (M and V; V is informative only: E-S was not trained on the done question), E and E-S
for who in e $N; do
  M=$ME; [ $who = $N ] && M=$O/merged
  for p in M_done M_notdone; do
    [ -f $EV/${who}_probe_$p.jsonl.done ] && continue
    python generate.py --model $M --data $IN/probes/probe_$p --out $EV/${who}_probe_$p.jsonl --enable_thinking 1 --bs 32 \
      --max_pixels 774400 --limit $LIM > $EV/${who}_probe_$p.gen.log 2>&1 && touch $EV/${who}_probe_$p.jsonl.done \
      || { log "PROBE FAILED $who $p"; tail -5 $EV/${who}_probe_$p.gen.log | tee -a $CK/r13.log; exit 1; }
  done
done
MODEL=$O/merged NAME=$N LIMIT=$LIM DREV=$DREV bash vm_r8_eval.sh 2>&1 | tee -a $CK/r13.log
grep -q "EVAL DONE $N" $CK/r13.log || { log "ROUND-8 EVALS FAILED"; exit 1; }
python sm_r13_gate.py --name $N --eval $EV --out $EV/${N}_r13_gate.json 2>&1 | tee -a $CK/r13.log
cp $EV/${N}_r13_gate.json $CK/r13.log /opt/ml/model/ 2>/dev/null
log "R13 $MODE DONE"
