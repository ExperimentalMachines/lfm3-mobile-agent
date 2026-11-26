#!/bin/bash
# Export a merged HF model to the phone-format GGUF (language model) used in AndroidWorld.
# The vision tower/projector are untouched by our LoRA (language-model-only), so the base model's
# mmproj GGUF is reused unchanged.
# Usage: scripts/publish/local_export_gguf.sh <hf_repo_or_dir> <out_dir> [quant=Q4_K_M]
set -euo pipefail
SRC=$1; OUT=$2; Q=${3:-Q4_K_M}
cd "$(dirname "$0")/../.."
mkdir -p "$OUT"
NAME=$(basename "$SRC")
if [ -d "$SRC" ]; then M="$SRC"; else
  M="$OUT/$NAME"; uvx --from huggingface_hub hf download "$SRC" --local-dir "$M" --exclude "lora_adapter/*" --exclude "eval/*" --exclude "training_logs/*" > /dev/null
fi
[ -d .venv-convert ] || { uv venv -q -p 3.12 .venv-convert && uv pip install -q -p .venv-convert/bin/python -r tools/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt; }
.venv-convert/bin/python tools/llama.cpp/convert_hf_to_gguf.py "$M" --outtype f16 --outfile "$OUT/$NAME-F16.gguf" 2>&1 | tail -2
llama-quantize "$OUT/$NAME-F16.gguf" "$OUT/$NAME-$Q.gguf" "$Q" 2>&1 | tail -1
rm -f "$OUT/$NAME-F16.gguf"
[ -d "$SRC" ] || rm -rf "$M"   # keep disk lean
ls -la "$OUT"/*.gguf
