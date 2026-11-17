#!/bin/bash
# Fresh Colab L4 session -> bootstrap -> launch a pipeline job file (which resumes from its hub checkpoint).
# Usage: [COLAB_BIN=...] [HF_TOKEN_FILE=...] scripts/provision_and_launch.sh <session> <jobs.json>
set -u
SESS=$1; JOBS=$2
cd "$(dirname "$0")/.."
CB=${COLAB_BIN:-$HOME/.local/bin/colab}
for i in 1 2 3 4 5 6; do
  "$CB" new -s "$SESS" --gpu L4 < /dev/null 2>&1 | tail -2
  "$CB" sessions < /dev/null 2>&1 | grep -q "$SESS" && break
  echo "[$(date +%T)] provision attempt $i failed; retrying in 60 s"; sleep 60
done
"$CB" sessions < /dev/null 2>&1 | grep -q "$SESS" || { echo "PROVISION FAILED"; exit 1; }
bash scripts/gpu_session.sh "$SESS" 2>&1 | grep -E "versions|HF user|pip rc|mismatch|Error|L4" | tail -6
bash scripts/launch_on_session.sh "$SESS" "$JOBS"
