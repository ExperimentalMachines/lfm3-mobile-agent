#!/bin/bash
# Runs ON the GPU VM under nohup. Offline AndroidControl test generation + scoring.
# Usage: MODEL=... NAME=... THINK=0|1 bash vm_eval.sh
set -euo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
cd /content/work
DATA=${DATA:-experimentalmachines/AndroidControl-screen-agent-sft@test}
mkdir -p /content/eval
python generate.py --model "$MODEL" --data "$DATA" --out /content/eval/${NAME}.jsonl \
  --enable_thinking ${THINK:-1} --bs ${BS:-64} --max_new_tokens ${MAXNEW:-256} ${EXTRA:-}
python score.py /content/eval/${NAME}.jsonl --gt /content/work/meta/androidcontrol_test_gt.jsonl --out /content/eval/${NAME}.metrics.json > /dev/null
echo "EVAL DONE ${NAME}"
