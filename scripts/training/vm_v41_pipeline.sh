#!/bin/bash
# v4.1 (2026-11-21). Runs ON a Colab GPU (colab-b account) inside the blocking cell, like vm_model_pipeline.sh.
#  1. Rebuilds the v4.1 training set if it is missing: pinned v4 dataset -> data/v41_build_parquet.py (text-only,
#     deterministic) -> save_to_disk on the VM. Not pushed to the Hub (7.7 GB); a manifest with the source revision,
#     builder hash and shard hashes goes to /content/eval/ (pushed with the evals).
#  2. Runs the unchanged v4 pipeline (vm_model_pipeline.sh) with TRAIN_DATA = that folder. Same rows, same order
#     (shuffle depends only on seed and row count), same recipe; only the text edits differ from v4.
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
SRC=alpharomercoma/AndroidAgent-SFT-v4; REV=337553984ee970a767dceb21adc6343f3d613602
D=/content/data/v41; DISK=/content/data/v41_train_disk
log() { echo "[$(date +%T)] v41: $*"; }
cd /content/work
mkdir -p /content/eval /content/runs
if [ ! -f $DISK/.done ]; then
  rm -rf /content/data/v4src $D $DISK
  log "download $SRC @ $REV (train shards)"
  python -c "from huggingface_hub import snapshot_download as s; s('$SRC', repo_type='dataset', revision='$REV', local_dir='/content/data/v4src', allow_patterns=['data/train-*'])" \
    || { log "DOWNLOAD FAILED"; exit 1; }
  log "build v4.1"
  python v41_build_parquet.py --src /content/data/v4src --out $D || { log "BUILD FAILED"; exit 1; }
  python - <<PY || { log "SAVE FAILED"; exit 1; }
import glob, hashlib, json
from datasets import load_dataset
fs = sorted(glob.glob("$D/data/train-*.parquet"))
src = sorted(glob.glob("/content/data/v4src/data/train-*.parquet"))
assert [f.split("/")[-1] for f in fs] == [f.split("/")[-1] for f in src] and len(fs) == 16, (fs, src)
ds = load_dataset("parquet", data_files={"train": fs}, split="train")
ds.save_to_disk("$DISK")
h = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()
man = {"source": "$SRC@$REV", "builder_sha256": h("v41_build_parquet.py"), "rows": len(ds),
       "source_shards": {f.split("/")[-1]: h(f) for f in src}, "v41_shards": {f.split("/")[-1]: h(f) for f in fs},
       "stats": json.load(open("$D/v41_stats.json"))}
json.dump(man, open("/content/eval/v41_data_manifest.json", "w"), indent=1)
print(json.dumps({k: man[k] for k in ("rows", "builder_sha256", "stats")}))
PY
  rm -rf /content/data/v4src
  touch $DISK/.done
  log "v4.1 data ready: $DISK"
fi
export TRAIN_DATA=$DISK
exec bash /content/work/vm_model_pipeline.sh
