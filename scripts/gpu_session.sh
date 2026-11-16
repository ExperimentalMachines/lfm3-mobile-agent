#!/bin/bash
# Local helper: push code to the GPU Colab session and bootstrap it.
# Usage: scripts/gpu_session.sh <session_name>
set -euo pipefail
SESS=${1:-lfm3g4}
cd "$(dirname "$0")/.."
C() { "${COLAB_BIN:-$HOME/.local/bin/colab}" ${COLAB_CONFIG:+--config "$COLAB_CONFIG"} "$@" 2> >(grep -v "new version\|colab update\|silence this" >&2); }
echo 'import os;[os.makedirs(d,exist_ok=True) for d in ("/content/work","/content/runs","/content/eval")];print("dirs ok")' | C exec -s "$SESS"
for f in train/sft_vlm.py train/agent_format.py train/qwen35_chat_template_gen.jinja scripts/vm_train_eval_push.sh \
         eval/androidcontrol/generate.py eval/androidcontrol/score.py eval/general/eval_general.py data/build_general_replay.py scripts/vm_450m_pipeline.sh scripts/vm_model_pipeline.sh \
         scripts/vm_train.sh scripts/colab_bootstrap.py; do
  [ -f "$f" ] || { echo "skip missing $f"; continue; }
  C upload -s "$SESS" "$f" "/content/work/$(basename "$f")" | tail -1
done
C upload -s "$SESS" "${HF_TOKEN_FILE:-$HOME/.cache/huggingface/token}" /content/.hf_token | tail -1
C exec -s "$SESS" --timeout 900 -f scripts/colab_bootstrap.py
