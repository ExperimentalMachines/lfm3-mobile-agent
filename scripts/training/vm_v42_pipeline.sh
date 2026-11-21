#!/bin/bash
# v4.2 = fix 4 (2026-11-21, docs/PREREG_v41.md). Runs ON the Colab VM that trained v4.1 (colab-b session v41), in the
# same blocking cell as the resumed v4.1 evaluations (scripts/training/jobs/lfm3_v41_evals_v42_a100.json).
#  1. v4.1's merged weights replay a deterministic SELFHIST_RATE share of training episodes on their recorded screens
#     with their own history (data/v42_selfhist.py); rows of those episodes get the self-generated history.
#  2. The unchanged v4 pipeline trains v4.2 from the base model on that dataset (same recipe, rows and order).
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
SRC=alpharomercoma/AndroidAgent-SFT-v4; REV=337553984ee970a767dceb21adc6343f3d613602
D41=/content/data/v41_train_disk; D42=/content/data/v42_train_disk; W=/content/data/v42work
M41=/content/runs/lfm3vl2b-v41-lora/merged
log() { echo "[$(date +%T)] v42: $*"; }
cd /content/work
mkdir -p /content/eval /content/runs
[ -f $D41/.done ] || { log "v4.1 data missing"; exit 1; }
python - <<PY || { log "v4.1 training receipt missing or incomplete"; exit 1; }
import json; r = json.load(open("/content/runs/lfm3vl2b-v41-lora/train_receipt.json")); assert r["global_step"] >= r["max_steps"] > 0
PY
if [ ! -f $D42/.done ]; then
  [ "$(ls /content/data/v4src/data/train-*.parquet 2>/dev/null | wc -l)" = 16 ] || {
    log "download $SRC @ $REV (train shards, for positions and human steps)"
    python -c "from huggingface_hub import snapshot_download as s; s('$SRC', repo_type='dataset', revision='$REV', local_dir='/content/data/v4src', allow_patterns=['data/train-*'])" \
      || { log "DOWNLOAD FAILED"; exit 1; }; }
  log "self-history with v4.1 (rate ${SELFHIST_RATE:?})"
  python v42_selfhist.py --v41_disk $D41 --v4_glob "/content/data/v4src/data/train-*.parquet" --model $M41 --work $W \
    --save_disk $D42 --rate $SELFHIST_RATE --bs ${SELFHIST_BS:-48} || { log "SELF-HISTORY FAILED"; exit 1; }
  cp $W/v42_stats.json /content/eval/v42_selfhist_stats.json
  python - <<PY
import hashlib, json
h = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()
json.dump({"v41_disk": "$D41", "v4_source": "$SRC@$REV", "model": "$M41",
           "v41_receipt": json.load(open("/content/runs/lfm3vl2b-v41-lora/train_receipt.json")).get("weights"),
           "builder_sha256": h("v42_selfhist.py"), "rate": float("$SELFHIST_RATE")},
          open("/content/eval/v42_data_manifest.json", "w"), indent=1)
PY
  touch $D42/.done
  log "v4.2 data ready: $D42"
fi
export TRAIN_DATA=$D42
exec bash /content/work/vm_model_pipeline.sh
