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
[ -d .venv-convert ] || { uv venv -q -p 3.12 .venv-convert && uv pip install -q -p .venv-convert/bin/python -r tools/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt; }
# A Hub repo id is pinned to its current revision before the download, so the receipt can bind the exact weights that were converted.
# A local folder can be converted for tests but gets no receipt and therefore cannot be published with publish_gguf.py.
if [ -d "$SRC" ]; then M="$SRC"; REV=""; else
  REV=$(.venv-convert/bin/python -c "from huggingface_hub import HfApi; print(HfApi().model_info('$SRC').sha)" 2>/dev/null || uvx --from huggingface_hub python -c "from huggingface_hub import HfApi; print(HfApi().model_info('$SRC').sha)")
  M="$OUT/$NAME"; uvx --from huggingface_hub hf download "$SRC" --revision "$REV" --local-dir "$M" --exclude "lora_adapter/*" --exclude "eval/*" --exclude "training_logs/*" > /dev/null
fi
.venv-convert/bin/python tools/llama.cpp/convert_hf_to_gguf.py "$M" --outtype f16 --outfile "$OUT/$NAME-F16.gguf" 2>&1 | tail -2
llama-quantize "$OUT/$NAME-F16.gguf" "$OUT/$NAME-$Q.gguf" "$Q" 2>&1 | tail -1
rm -f "$OUT/$NAME-F16.gguf"
# conversion receipt (checked by publish_gguf.py); written before the downloaded folder is deleted
[ -n "$REV" ] && .venv-convert/bin/python scripts/publish/make_receipt.py "$SRC" "$OUT/$NAME-$Q.gguf" "$Q" --input-dir "$M" --revision "$REV"
[ -d "$SRC" ] || rm -rf "$M"   # keep disk lean
ls -la "$OUT"/*.gguf
