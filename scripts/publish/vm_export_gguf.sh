#!/bin/bash
# Runs ON the Colab VM (colab-b), inside the blocking cell. Exports merged weights to the phone GGUF (Q4_K_M) with the
# SAME converter as the Mac: llama.cpp cd959bae9 (convert_hf_to_gguf.py + llama-quantize) and a converter venv pinned
# to the Mac's .venv-convert versions. Why here: the Mac's disk cannot hold merged (3.8 GB) + F16 (3.6 GB) right now,
# and the Hub cannot hold the merged weights (private storage full, 2026-11-21).
#  1. Parity: re-export v4's published merged weights (each file checked against results/v4_local_export_manifest.json)
#     and require the Mac's v4 GGUF SHA-256. Nothing else is exported unless this matches byte for byte.
#  2. For each EXPORT_RUNS entry "run_dir:Name" (waits for the run's train_receipt.json): check_local_merge.py
#     (merged == bf16(base + LoRA)), then export to /content/gguf/<Name>-Q4_K_M.gguf and print its SHA-256.
set -uo pipefail
log() { echo "[$(date +%T)] export: $*"; }
cd /content
export HF_TOKEN=$(cat /content/.hf_token)
V4_GGUF_SHA=5285279249948dc019abf9341f98b65778f679a1f2cbc76e94c57a96af2a35e7
BASE_REV=23387beda43c60310348e83e25f78f33c3140d3a
if [ ! -x llama.cpp/build/bin/llama-quantize ]; then
  rm -rf llama.cpp
  git clone -q --filter=blob:none https://github.com/ggml-org/llama.cpp.git && (cd llama.cpp && git checkout -q cd959bae9 \
    && cmake -B build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF > /dev/null && cmake --build build -j "$(nproc)" --target llama-quantize > build.log 2>&1) \
    || { log "BUILD FAILED"; exit 1; }
fi
(cd llama.cpp && log "llama.cpp $(git log -1 --format=%h)")
if [ ! -x /content/venv-convert/bin/python ]; then
  pip install -q uv && uv venv -q -p 3.12 /content/venv-convert && uv pip install -q -p /content/venv-convert/bin/python \
    --extra-index-url https://download.pytorch.org/whl/cpu torch==2.11.0 transformers==5.20.2 numpy==2.2.6 \
    sentencepiece==0.2.3 protobuf==4.25.9 safetensors==0.8.0 gguf==0.19.0 huggingface-hub==2.4.0 || { log "VENV FAILED"; exit 1; }
fi
PY=/content/venv-convert/bin/python
export_one() {  # merged_dir out_gguf
  $PY llama.cpp/convert_hf_to_gguf.py "$1" --outtype f16 --outfile "$2.F16.gguf" > "$2.convert.log" 2>&1 || return 1
  llama.cpp/build/bin/llama-quantize "$2.F16.gguf" "$2" Q4_K_M > "$2.quant.log" 2>&1 || return 1
  rm -f "$2.F16.gguf"
}
mkdir -p /content/gguf
BASE=$($PY -c "from huggingface_hub import hf_hub_download as d; print(d('LiquidAI/LFM3-VL-2B', 'model.safetensors', revision='$BASE_REV'))") \
  || { log "BASE DOWNLOAD FAILED"; exit 1; }
if [ ! -f /content/gguf/parity_ok ]; then
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
  export_one /content/v4merged /content/gguf/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf || { log "PARITY EXPORT FAILED"; exit 1; }
  h=$(sha256sum /content/gguf/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf | cut -d' ' -f1)
  [ "$h" = "$V4_GGUF_SHA" ] || { log "PARITY MISMATCH: $h (Mac $V4_GGUF_SHA)"; exit 1; }
  touch /content/gguf/parity_ok
  log "parity OK: the Colab export of v4 is byte-identical to the Mac's v4 GGUF"
fi
for spec in ${EXPORT_RUNS:?}; do
  run=${spec%%:*}; name=${spec#*:}; R=/content/runs/$run; G=/content/gguf/$name-Q4_K_M.gguf
  [ -s "$G" ] && { log "$G exists"; continue; }
  until [ -f "$R/train_receipt.json" ]; do sleep 120; done
  $PY /content/work/check_local_merge.py "$R/merged" "$BASE" "$R/lora" || { log "MERGE CHECK FAILED: $run"; exit 1; }
  export_one "$R/merged" "$G" || { log "EXPORT FAILED: $run"; exit 1; }
  log "exported $G sha256 $(sha256sum "$G" | cut -d' ' -f1)"
done
log "all exports done"
