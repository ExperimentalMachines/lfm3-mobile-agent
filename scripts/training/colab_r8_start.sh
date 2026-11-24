#!/bin/bash
# Round 8 / candidate E on Colab (PREREG_v46 log, 2026-11-25): get an A100 or G4, install the pinned packages, launch
# vm_r8_train.sh in a blocking cell (checkpoints every 100 steps to the public Hub repo), start the credit guard.
# The same command resumes E on Modal later from the last Hub checkpoint.
set -u
cd "$(dirname "$0")/../.."
S=r8e; C() { ~/.local/bin/colab "$@" < /dev/null 2>&1 | grep -v -i "new version\|colab update\|silence"; }
have() { C sessions | grep -q "\[$S\]"; }
end=$(( $(date +%s) + ${WAIT_S:-14400} ))
until have; do
  for g in A100 G4; do have && break; C new -s $S --gpu $g | tail -1 | sed "s/^/[$(date +%T)] $g: /" | cut -c1-120; have && break; sleep 20; done
  [ $(date +%s) -gt $end ] && { echo "NO GPU"; exit 1; }
done
echo "[$(date +%T)] session: $(C sessions | grep "\[$S\]" | cut -c1-90)"
C upload -s $S ~/.cache/huggingface/token /content/.hf_token | tail -1
C exec -s $S --timeout 1200 -f scripts/training/colab_bootstrap.py | grep -E "pip rc|versions" | tail -2
EXTRA_FILES="scripts/training/vm_r8_train.sh:/content/work/vm_r8_train.sh scripts/training/vm_r8_eval.sh:/content/work/vm_r8_eval.sh scripts/training/sm_r8_gate.py:/content/work/sm_r8_gate.py scripts/training/sm_r7_gate.py:/content/work/sm_r7_gate.py eval/androidlens/score_androidlens.py:/content/work/score_androidlens.py scripts/training/v4_reference_r7.json:/content/work/v4_reference.json" \
  bash scripts/training/launch_on_session.sh $S scripts/training/jobs/r8e_colab.json 2>&1 | tail -2
nohup bash scripts/training/colab_credit_guard.sh $S 1.5 > logs/colab_credit_guard_r8e.log 2>&1 < /dev/null &
echo "[$(date +%T)] credit guard started (pid $!)"
