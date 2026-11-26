#!/bin/bash
# Round 14 (docs/PREREG_v412.md): two arms from E on the same 400 episodes (seed 14), each on its own SageMaker job.
#   R14_ARM=rl  : corrected semi-online RL (train/semi_online_rl.py: natural-segment returns, premature terminal ends the
#                 attempt, strict matcher, suffix windows keep endings, no failed-audit labels), 100 batches x B4 x G4
#   R14_ARM=sft : matched control: E's greedy own-history rollouts on the same episodes -> every strict miss labelled with
#                 the human's action (--collect) -> SFT mix with uniform replay (3,200 rows, 100 steps x 32, lr 1e-4)
#   R14_MODE=smoke: 2 batches / 8 episodes, a 30-step SFT, evals on 16 rows (numbers meaningless)
# Then: merge, both ending probes for E and the arm, every round-8 eval, sm_r13_gate.py (the same bars as round 13).
# Channels: code; e (E's merged weights); r14in (ody_term2.parquet, verdicts, written actions, probe exclusions, probes).
set -uo pipefail
C=/opt/ml/input/data/code; CK=/opt/ml/checkpoints; ME=/opt/ml/input/data/e; IN=/opt/ml/input/data/r14in
mkdir -p $CK/runs $CK/eval /content/data /opt/ml/model
ln -sfn $CK/runs /content/runs; ln -sfn $CK/eval /content/eval
rm -rf /content/work && mkdir -p /content/work/meta && cp $C/*.py $C/*.sh $C/*.json /content/work/ && cp $C/meta/* /content/work/meta/
cd /content/work || exit 1
ARM=${R14_ARM:?}; MODE=${R14_MODE:-smoke}
log() { echo "[$(date -u +%T)] r14-$ARM: $*" | tee -a $CK/r14.log; }
DREV=0ace5559e6c0b808a5ddf4e4ce9831d1d3614471; EV=/content/eval; O=/content/runs/r14$ARM
export TOKENIZERS_PARALLELISM=false HF_HUB_DISABLE_TELEMETRY=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True HF_HOME=/opt/ml/input/hf
log "mode $MODE; gpu $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader); E files $(ls $ME | wc -l); inputs: $(ls $IN | tr '\n' ' ')"
if [ ! -f $CK/.pip_ok ] || ! python -c "import peft, trl" 2>/dev/null; then
  pip install -q "torch==2.14.1" "torchvision==0.29.1" "torchao==0.18.0" "trl==1.16.0" "transformers==5.20.2" "peft==0.21.2" \
    "accelerate==1.15.0" "datasets==5.1.0" "huggingface-hub==2.3.0" "tokenizers==0.23.3" "safetensors==0.8.0" tensorboard pillow pyarrow numpy hf_xet \
    > $CK/pip.log 2>&1 || { log "PIP FAILED"; tail -5 $CK/pip.log; exit 1; }
  touch $CK/.pip_ok
fi
COMMON="--model_id $ME --term $IN/ody_term2.parquet --verdicts $IN/claude_ody_terminal_verdicts.jsonl --written $IN/claude_next_actions.jsonl --probe_ids $IN/rl_probe_exclude.json --history_steps 24 --notes 1 --max_steps 12 --seed 14"
if [ "$MODE" = smoke ]; then NB=2; LIM=16; SFT_STEPS=30; else NB=100; LIM=0; SFT_STEPS=100; fi
if [ "$ARM" = rl ]; then
  RES=""; [ -f $O/state.json ] && [ -d $O/adapter ] && RES="--resume $O/adapter"
  if ! grep -q '"done": true' $O/state.json 2>/dev/null; then
    log "RL: $NB batches x B4 x G4, lr 3e-5 $RES"
    python semi_online_rl.py $COMMON --out $O --batches $NB --B 4 --G 4 --lr 3e-5 --gamma 0.5 --omega 1.0 --patch 1 \
      --temperature 1.0 --save_every 5 $RES > $O.log 2>&1 || { log "RL FAILED"; grep -v Warning $O.log | tail -15 | tee -a $CK/r14.log; exit 1; }
  fi
  log "$(grep -m1 'episodes {' $O.log | cut -c1-700)"; log "$(grep -m1 'plan:' $O.log | cut -c1-300)"; log "rl last: $(tail -1 $O/rl_log.jsonl)"
  [ -f $O/merged/config.json ] && [ $O/merged/config.json -nt $O/adapter/adapter_model.safetensors ] || \
    python merge_adapter.py --base $ME --adapter $O/adapter --out $O/merged >> $O.log 2>&1 || { log "MERGE FAILED"; exit 1; }
else
  if [ ! -f $O/div/dataset_info.json ]; then
    log "collect: E greedy, own history, same $NB batches x B4 episodes, every strict miss -> human action"
    python semi_online_rl.py $COMMON --out $O --batches $NB --B 4 --G 4 --collect $O/div > $O.collect.log 2>&1 \
      || { log "COLLECT FAILED"; grep -v Warning $O.collect.log | tail -15 | tee -a $CK/r14.log; exit 1; }
  fi
  log "$(grep -m1 'plan:' $O.collect.log | cut -c1-300)"; log "$(cat $O/collect_stats.json | tr -d '\n' | cut -c1-500)"
  [ -f $O/mix_stats.json ] || python r14_sft_mix.py --div $O/div --out $O/mix --n $((SFT_STEPS * 32)) > $O.mix.log 2>&1 \
    || { log "MIX FAILED"; tail -5 $O.mix.log | tee -a $CK/r14.log; exit 1; }
  log "$(grep -o 'R14_SFT_MIX_DONE.*' $O.mix.log)"
  if [ ! -f $O/sft/train_receipt.json ]; then
    python sft_vlm.py --model_id $ME --train $O/mix --out $O/sft --max_steps $SFT_STEPS --max_pixels 774400 --bs 1 --grad_accum 32 \
      --lr 1e-4 --warmup 0.03 --scheduler cosine --lora_r 64 --lora_alpha 128 --modules_to_save --workers 6 --save_steps 50 \
      --eval_steps 100000 > $O.sft.log 2>&1 || { log "SFT FAILED"; tail -20 $O.sft.log | tee -a $CK/r14.log; exit 1; }
  fi
  ln -sfn $O/sft/merged $O/merged
fi
N=$([ "$MODE" = smoke ] && echo smoke14$ARM || echo r14$ARM)
for who in e $N; do
  M=$ME; [ $who = $N ] && M=$O/merged
  for p in M_done M_notdone; do
    [ -f $EV/${who}_probe_$p.jsonl.done ] && continue
    python generate.py --model $M --data $IN/probes/probe_$p --out $EV/${who}_probe_$p.jsonl --enable_thinking 1 --bs 32 \
      --max_pixels 774400 --limit $LIM > $EV/${who}_probe_$p.gen.log 2>&1 && touch $EV/${who}_probe_$p.jsonl.done \
      || { log "PROBE FAILED $who $p"; tail -5 $EV/${who}_probe_$p.gen.log | tee -a $CK/r14.log; exit 1; }
  done
done
MODEL=$O/merged NAME=$N LIMIT=$LIM DREV=$DREV bash vm_r8_eval.sh 2>&1 | tee -a $CK/r14.log
grep -q "EVAL DONE $N" $CK/r14.log || { log "ROUND-8 EVALS FAILED"; exit 1; }
python sm_r13_gate.py --name $N --eval $EV --out $EV/${N}_r14_gate.json 2>&1 | sed 's/^R13 GATE/R14 GATE/' | tee -a $CK/r14.log
cp $EV/${N}_r14_gate.json $CK/r14.log /opt/ml/model/ 2>/dev/null
log "R14 $ARM $MODE DONE"
