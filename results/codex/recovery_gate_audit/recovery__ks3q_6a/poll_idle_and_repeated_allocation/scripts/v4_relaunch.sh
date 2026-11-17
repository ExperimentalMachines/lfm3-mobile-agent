#!/bin/bash
# After a Colab VM loss: bootstrap an already-provisioned session, restore the v4 + RL files, and relaunch the v4 job
# (SFT resumes from the hub checkpoint in CKPT_REPO; pipeline steps whose outputs exist are skipped).
# Usage: bash scripts/v4_relaunch.sh <session>
set -u; set -o pipefail
S=$1
cd "$(dirname "$0")/.."
TMP=/Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/poll_idle_and_repeated_allocation/tmp/v4_relaunch_$$; mkdir -p "$TMP"
C() { /Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/poll_idle_and_repeated_allocation/bin/colab "$@" < /dev/null 2>&1 | grep -v "new version\|colab update\|silence"; }
SFT_SHA=337553984ee970a767dceb21adc6343f3d613602
RL_SHA=9ba36d90abe9bdbaa0c578879336472ab054cc2c
echo "[$(date +%T)] bootstrap $S"
bash scripts/gpu_session.sh "$S" 2>&1 | grep -E "NVIDIA|pip rc|versions|HF user|mismatch|failed|Error|dirs ok" | tail -8
echo 'import os;os.makedirs("/content/work/meta",exist_ok=True);print("meta ok")' | /Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/poll_idle_and_repeated_allocation/bin/colab exec -s "$S" 2>/dev/null \
  | grep -q "meta ok" || { echo "RELAUNCH FAILED: kernel unreachable"; exit 1; }
up() { C upload -s "$S" "$1" "$2" | grep -q Uploaded || { echo "RELAUNCH FAILED: upload $1"; exit 1; }; }
up data/v4work/app_pool.json /content/work/meta/app_pool.json
for f in train/rl_reward.py train/grpo_vlm.py data/v4_answer_check.py scripts/vm_rl_hook.sh scripts/strict_dev_metrics.py; do
  up "$f" "/content/work/$(basename "$f")"
done
if [ "${NO_RL:-0}" = 1 ]; then   # e.g. an interim L4: SFT only (no concurrent GRPO smoke on 24 GB); RL can be uploaded later
  echo "[$(date +%T)] NO_RL=1: rl_go.sh / rl_hold not uploaded"
else
echo hold > "$TMP/rl_hold"; up "$TMP/rl_hold" /content/work/rl_hold
sed -e "s#__RL_DATA__#alpharomercoma/AndroidAgent-RL-v4@$RL_SHA#" -e 's#__DEV_REPO__#alpharomercoma/AndroidAgent-SFT-v4#' \
    -e "s#__DEV_REV__#$SFT_SHA#" -e 's#__V4_RUN__#lfm3vl2b-v4bmix-lora#' -e 's#__SKIP_SMOKE__#1#' scripts/vm_rl_go.sh > "$TMP/rl_go.sh"
bash -n "$TMP/rl_go.sh" && ! grep -q "__[A-Z0-9_]*__" "$TMP/rl_go.sh" || { echo "RELAUNCH FAILED: rl_go template"; exit 1; }
up "$TMP/rl_go.sh" /content/work/rl_go.sh
fi
python3 scripts/make_v4_train_job.py $SFT_SHA v4b || { echo "RELAUNCH FAILED: job file"; exit 1; }
bash scripts/launch_on_session.sh "$S" scripts/jobs/lfm3_v4_a100.json
