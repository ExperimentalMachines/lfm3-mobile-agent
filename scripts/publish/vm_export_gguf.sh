#!/bin/bash
# Runs ON the Colab VM (colab-b), inside the blocking cell. Converts merged weights to an F16 GGUF with the Mac's
# converter (llama.cpp cd959bae9 convert_hf_to_gguf.py; venv pinned to the Mac's .venv-convert versions), from a folder
# named exactly like the Mac's export folder (the converter takes general.name etc. from it). The 4-bit step
# (llama-quantize Q4_K_M) runs on the Mac: quantizing on this x86 VM changed 0.06% of bytes vs the Mac (2026-11-21
# parity test), so only the F16 step moves here. Why here at all: the Mac's disk cannot hold merged (3.8 GB) + F16
# (3.6 GB), and the Hub cannot hold the merged weights (private storage full).
# EXPORT_RUNS entries "dir_or_run:Name[:base_safetensors]" (round 5: base = v4.2's merged weights; SKIP_V4_PARITY=1 skips
# the v4 parity input, whose Mac marker already exists): v4 (parity, published merged weights checked against
# results/v4_local_export_manifest.json) and each run (waits for its train_receipt.json, then check_local_merge.py).
# Output: /content/gguf/<Name>-F16.gguf (+ .sha256). The Mac quantizes and checks v4's Q4_K_M SHA-256 first.
set -uo pipefail
log() { echo "[$(date +%T)] export: $*"; }
cd /content
export HF_TOKEN=$(cat /content/.hf_token)
BASE_REV=23387beda43c60310348e83e25f78f33c3140d3a
if [ "$(cd llama.cpp 2>/dev/null && git rev-parse --short=9 HEAD)" != cd959bae9 ]; then
  rm -rf llama.cpp
  git clone -q --filter=blob:none https://github.com/ggml-org/llama.cpp.git && (cd llama.cpp && git checkout -q cd959bae9) \
    || { log "CLONE FAILED"; exit 1; }
fi
(cd llama.cpp && log "llama.cpp $(git log -1 --format=%h)")
if [ ! -x /content/venv-convert/bin/python ]; then
  pip install -q uv && uv venv -q -p 3.12 /content/venv-convert && uv pip install -q -p /content/venv-convert/bin/python \
    --extra-index-url https://download.pytorch.org/whl/cpu torch==2.11.0 transformers==5.20.2 numpy==2.2.6 \
    sentencepiece==0.2.3 protobuf==4.25.9 safetensors==0.8.0 gguf==0.19.0 huggingface-hub==2.4.0 || { log "VENV FAILED"; exit 1; }
fi
PY=/content/venv-convert/bin/python
export_f16() {  # merged_dir Name  (converted through /content/named/<Name>, the Mac's folder name)
  mkdir -p /content/named && ln -sfn "$1" "/content/named/$2"
  $PY llama.cpp/convert_hf_to_gguf.py "/content/named/$2" --outtype f16 --outfile "/content/gguf/$2-F16.gguf.part" \
    > "/content/gguf/$2.convert.log" 2>&1 || return 1
  mv "/content/gguf/$2-F16.gguf.part" "/content/gguf/$2-F16.gguf"
  sha256sum "/content/gguf/$2-F16.gguf" | cut -d' ' -f1 > "/content/gguf/$2-F16.gguf.sha256"
}
mkdir -p /content/gguf
BASE=$($PY -c "from huggingface_hub import hf_hub_download as d; print(d('LiquidAI/LFM3-VL-2B', 'model.safetensors', revision='$BASE_REV'))") \
  || { log "BASE DOWNLOAD FAILED"; exit 1; }
if [ "${SKIP_V4_PARITY:-0}" != 1 ] && [ ! -s /content/gguf/LFM3-VL-2B-AndroidAgent-v4-F16.gguf ]; then
  $PY - <<'PY' || { log "PARITY INPUT FAILED"; exit 1; }
import hashlib, json, os
from huggingface_hub import hf_hub_download
man = json.load(open("/content/work/meta/v4_local_export_manifest.json"))["files"]
os.makedirs("/content/v4merged", exist_ok=True)
for f, want in man.items():
    p = hf_hub_download("experimentalmachines/LFM3-VL-2B-AndroidAgent-v4", f, local_dir="/content/v4merged")
    d = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 24), b""): d.update(b)
    assert d.hexdigest() == want, f"{f}: published file differs from the v4 export manifest"
print("v4 merged files match the manifest:", len(man))
PY
  export_f16 /content/v4merged LFM3-VL-2B-AndroidAgent-v4 || { log "PARITY F16 FAILED"; exit 1; }
  log "v4 F16 ready (parity input for the Mac)"
fi
for spec in ${EXPORT_RUNS:?}; do
  run=${spec%%:*}; rest=${spec#*:}; name=${rest%%:*}; base=$BASE; [ "$rest" != "$name" ] && base=${rest#*:}; R=/content/runs/$run
  [ -s "/content/gguf/$name-F16.gguf" ] && { log "$name F16 exists"; continue; }
  until [ -f "$R/train_receipt.json" ]; do sleep 120; done
  $PY /content/work/check_local_merge.py "$R/merged" "$base" "$R/lora" || { log "MERGE CHECK FAILED: $run"; exit 1; }
  export_f16 "$R/merged" "$name" || { log "EXPORT FAILED: $run"; exit 1; }
  log "exported /content/gguf/$name-F16.gguf sha256 $(cat /content/gguf/$name-F16.gguf.sha256)"
done
log "all F16 exports done"
