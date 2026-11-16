#!/bin/bash
# Local helper: push code to the GPU Colab session and bootstrap it.
# Usage: scripts/gpu_session.sh <session_name>
set -euo pipefail
SESS=${1:-lfm3g4}
cd "$(dirname "$0")/.."
C() { "$HOME/.local/bin/colab" ${COLAB_CONFIG:+--config "$COLAB_CONFIG"} "$@" 2> >(grep -v "new version\|colab update\|silence this" >&2); }
echo 'import os;[os.makedirs(d,exist_ok=True) for d in ("/content/work","/content/runs","/content/eval")];print("dirs ok")' | C exec -s "$SESS"
for f in train/sft_vlm.py train/agent_format.py train/qwen35_chat_template_gen.jinja \
         eval/androidcontrol/generate.py eval/androidcontrol/score.py \
         scripts/vm_train.sh scripts/colab_bootstrap.py; do
  C upload -s "$SESS" "$f" "/content/work/$(basename "$f")" | tail -1
done
C upload -s "$SESS" "$HOME/.cache/huggingface/token" /content/.hf_token | tail -1
C exec -s "$SESS" -f scripts/colab_bootstrap.py
