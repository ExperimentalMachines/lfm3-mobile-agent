#!/bin/bash
# v4.1 follow-up (docs/PREREG_v41.md): phone GGUF of v4.1, exported exactly like v4 (scripts/androidworld/local_v4_to_aw_v2.sh):
#   1. merged weights from the Hub repo at a pinned revision (or a dir copied off the Colab VM if the upload failed);
#   2. scripts/publish/check_local_merge.py: merged == bf16(base + LoRA) tensor by tensor (base pinned as for v4);
#   3. scripts/publish/local_export_gguf.sh: same converter, Q4_K_M, base mmproj reused;
#   4. manifest results/v41_local_export_manifest.json (revisions + sha256 of every file); the merged dir is then removed
#      to keep the Mac's disk lean (it stays on the Hub / Colab).
# Usage: bash scripts/publish/local_export_v41.sh <hub_revision | local_merged_dir> <adapter_dir_or_hub_rev>
set -euo pipefail
cd "$(dirname "$0")/../.."
REPO=alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.1; NAME=LFM3-VL-2B-AndroidAgent-v4.1
SRC=${1:?}; ADREV=${2:?}
OUT=models/lfm3vl2b_v41-GGUF; GG=$OUT/$NAME-Q4_K_M.gguf; MM=models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf
BASE=$HOME/.cache/huggingface/hub/models--LiquidAI--LFM3-VL-2B/snapshots/23387beda43c60310348e83e25f78f33c3140d3a/model.safetensors
[ -e "$GG" ] && { echo "$GG exists; refusing to overwrite"; exit 1; }
[ -s "$BASE" ] || { echo "base weights missing: $BASE"; exit 1; }
M=models/hf_local/$NAME
if [ -d "$SRC" ]; then M=$SRC; MREV="local:$SRC"; else
  rm -rf "$M"; MREV=$SRC
  uvx --from huggingface_hub hf download $REPO --revision "$SRC" --local-dir "$M" --exclude "lora_adapter/*" --exclude "eval/*" --exclude "training_logs/*" > /dev/null
fi
if [ -d "$ADREV" ]; then AD=$ADREV; else
  AD=$(.venv-convert/bin/python -c "
from huggingface_hub import snapshot_download
p = snapshot_download('$REPO', revision='$ADREV', allow_patterns=['lora_adapter/adapter_model.safetensors','lora_adapter/adapter_config.json'])
print(p + '/lora_adapter')")
fi
.venv-convert/bin/python scripts/publish/check_local_merge.py "$M" "$BASE" "$AD"
bash scripts/publish/local_export_gguf.sh "$M" "$OUT"
.venv-convert/bin/python - "$M" "$GG" "$MM" "$MREV" "$ADREV" <<'PY'
import hashlib, json, os, sys
m, gg, mm, mrev, adrev = sys.argv[1:6]
def h(p):
    d = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): d.update(b)
    return d.hexdigest()
man = {"repo": "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.1", "merged_revision": mrev, "adapter_revision": adrev,
       "verified": "scripts/publish/check_local_merge.py: merged == bf16(LiquidAI/LFM3-VL-2B@23387beda4 + LoRA)",
       "merged_files": {f: h(os.path.join(m, f)) for f in sorted(os.listdir(m)) if os.path.isfile(os.path.join(m, f))},
       "gguf": {os.path.basename(gg): h(gg), os.path.basename(mm): h(mm)}}
json.dump(man, open("results/v41_local_export_manifest.json", "w"), indent=1)
print("manifest written:", man["gguf"])
PY
[ -d "$SRC" ] || rm -rf "$M"
echo "exported $GG"
