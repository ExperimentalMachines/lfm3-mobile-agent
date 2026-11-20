#!/bin/bash
# Local: bootstrap a GPU Colab session and run jobs inside a blocking kernel cell
# (Colab reclaims VMs whose kernel is idle, so nohup'd background jobs get killed).
# Usage: COLAB_CONFIG=<cfg.json|empty> scripts/training/launch_gpu_jobs.sh <session> <jobs.json>
set -euo pipefail
SESS=$1; JOBS=$2
cd "$(dirname "$0")/../.."
C() { "${COLAB_BIN:-$HOME/.local/bin/colab}" ${COLAB_CONFIG:+--config "$COLAB_CONFIG"} "$@" 2> >(grep -v "new version\|colab update\|silence this" >&2); }
COLAB_CONFIG=${COLAB_CONFIG:-} bash scripts/training/gpu_session.sh "$SESS" | tee "logs/${SESS}_bootstrap.log" | grep -E "NVIDIA|pip rc|versions|HF user|mismatch|failed"
grep -q "^versions" "logs/${SESS}_bootstrap.log" || { echo "BOOTSTRAP FAILED"; exit 1; }
C upload -s "$SESS" scripts/training/vm_blocking_jobs.py /content/work/vm_blocking_jobs.py | tail -1
C upload -s "$SESS" scripts/training/vm_eval.sh /content/work/vm_eval.sh | tail -1
C upload -s "$SESS" "$JOBS" /content/work/jobs.json | tail -1
echo 'import os;os.makedirs("/content/work/meta",exist_ok=True)' | C exec -s "$SESS" >/dev/null
C upload -s "$SESS" data/meta/splits.json /content/work/meta/splits.json | tail -1
C upload -s "$SESS" data/meta/androidcontrol_test_gt.jsonl /content/work/meta/androidcontrol_test_gt.jsonl | tail -1
C upload -s "$SESS" data/meta/androidcontrol_test_gt.manifest.json /content/work/meta/androidcontrol_test_gt.manifest.json | tail -1
echo "launching blocking jobs cell on $SESS at $(date +%T)"
nohup "${COLAB_BIN:-$HOME/.local/bin/colab}" ${COLAB_CONFIG:+--config "$COLAB_CONFIG"} exec -s "$SESS" --timeout 200000 -f scripts/training/vm_blocking_jobs.py \
  > "logs/${SESS}_jobs_cell.log" 2>&1 &
PID=$!
sleep 90
if grep -q heartbeat "logs/${SESS}_jobs_cell.log" && kill -0 $PID 2>/dev/null; then echo "cell client pid $PID — heartbeat confirmed"
else echo "LAUNCH NOT CONFIRMED: $(tail -c 300 logs/${SESS}_jobs_cell.log)"; exit 1; fi
