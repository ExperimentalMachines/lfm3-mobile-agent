#!/bin/bash
# Runs ON the GPU VM under nohup. Offline AndroidControl test generation + scoring.
# Usage: MODEL=... NAME=... THINK=0|1 bash vm_eval.sh
set -euo pipefail
export HF_TOKEN=$(cat /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/generation_failed/content/.hf_token)
cd /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/generation_failed/content/work
DATA=${DATA:-experimentalmachines/AndroidControl-screen-agent-sft@test}
mkdir -p /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/generation_failed/content/eval
python generate.py --model "$MODEL" --data "$DATA" --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/generation_failed/content/eval/${NAME}.jsonl \
  --enable_thinking ${THINK:-1} --bs ${BS:-64} --max_new_tokens ${MAXNEW:-256} ${EXTRA:-}
python score.py /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/generation_failed/content/eval/${NAME}.jsonl --out /Users/alpha/lfm3-android/results/codex/pass3/shell_km_rkvl1/generation_failed/content/eval/${NAME}.metrics.json > /dev/null
echo "EVAL DONE ${NAME}"
