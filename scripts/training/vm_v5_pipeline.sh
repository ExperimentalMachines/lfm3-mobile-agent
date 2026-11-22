#!/bin/bash
# Round 5 (docs/PREREG_v41.md, 2026-11-22 17:00). Runs ON a Colab A100 (colab-b) inside the blocking cell.
# Every stage is skipped when its output exists, so the job can be relaunched after a VM loss.
#  1. v4.2's merged weights from its public repo; v4.2's training data rebuilt without any generation
#     (v4 data @ REV -> data/v41_build_parquet.py -> data/v42_selfhist.py --no_generate from results/v42/selfhist_state)
#     and checked against v4.2's recorded build statistics.
#  2. P: pairs from v4.2's own greedy mistakes (data/v5_pairs.py) -> DPO smoke test -> DPO (train/dpo_vlm.py)
#     -> offline gate evals (AndroidControl test high-level incl. terminal rows, dev_answer, dev_complete).
#  3. S (only if CANDIDATES contains S): v4.2 + 800 SFT steps on v4.2's own mix (train/sft_vlm.py --scheduler wsd)
#     -> the same evals.
# Exports (GGUF F16) and public uploads run as separate jobs that wait for each run's train_receipt.json.
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
export TOKENIZERS_PARALLELISM=false
SRC=alpharomercoma/AndroidAgent-SFT-v4; REV=337553984ee970a767dceb21adc6343f3d613602
V42_REPO=alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.2
M42=/content/models/v42
D41=/content/data/v41_train_disk; D42=/content/data/v42_train_disk; W42=/content/data/v42work
PAIRS=/content/data/v5_pairs; PW=/content/data/v5work
R=experimentalmachines/AndroidControl-screen-agent-sft
GT=/content/work/meta/androidcontrol_test_gt.jsonl
POOL=/content/work/meta/app_pool.json
DEV_REPO=alpharomercoma/AndroidAgent-SFT-v4
CANDIDATES=${CANDIDATES:-P S}
log() { echo "[$(date +%T)] v5: $*"; }
cd /content/work
mkdir -p /content/eval /content/runs /content/models /content/data

# ---- 1. v4.2 weights and data
if [ ! -f $M42/.done ]; then
  log "download v4.2 merged weights ($V42_REPO)"
  python -c "from huggingface_hub import snapshot_download as s; s('$V42_REPO', local_dir='$M42', ignore_patterns=['lora_adapter/*','training_logs/*','eval/*','*.gguf'])" \
    && touch $M42/.done || { log "V4.2 DOWNLOAD FAILED"; exit 1; }
fi
if [ ! -f $D41/.done ]; then
  [ "$(ls /content/data/v4src/data/train-*.parquet 2>/dev/null | wc -l)" = 16 ] || {
    log "download $SRC @ $REV (train shards)"
    python -c "from huggingface_hub import snapshot_download as s; s('$SRC', repo_type='dataset', revision='$REV', local_dir='/content/data/v4src', allow_patterns=['data/train-*'])" \
      || { log "DOWNLOAD FAILED"; exit 1; }; }
  log "build v4.1 data"
  rm -rf /content/data/v41
  python v41_build_parquet.py --src /content/data/v4src --out /content/data/v41 || { log "V4.1 BUILD FAILED"; exit 1; }
  python - <<PY || { log "V4.1 SAVE FAILED"; exit 1; }
import glob
from datasets import load_dataset
fs = sorted(glob.glob("/content/data/v41/data/train-*.parquet")); assert len(fs) == 16, fs
ds = load_dataset("parquet", data_files={"train": fs}, split="train"); assert len(ds) == 92229, len(ds)
ds.save_to_disk("$D41")
PY
  touch $D41/.done
fi
if [ ! -f $D42/.done ]; then
  mkdir -p $W42 && gunzip -c /content/work/meta/selfhist_state.json.gz > $W42/selfhist_state.json || { log "STATE MISSING"; exit 1; }
  log "rebuild v4.2 data from the saved self-history state (no generation)"
  python v42_selfhist.py --v41_disk $D41 --v4_glob "/content/data/v4src/data/train-*.parquet" --model $M42 --work $W42 \
    --save_disk $D42 --rate 0.4 --no_generate || { log "V4.2 REBUILD FAILED"; exit 1; }
  python - <<PY || { log "V4.2 REBUILD DIFFERS FROM THE RECORDED BUILD"; exit 1; }
import json
got = json.load(open("$W42/v42_stats.json")); want = json.load(open("/content/work/meta/selfhist_stats.json"))
keys = ("episodes", "rows_in_episodes", "rows_with_new_history", "rows_own_wait_mistake", "generated", "model_steps_kept")
bad = {k: (got[k], want[k]) for k in keys if got[k] != want[k]}
assert not bad, bad
print("v4.2 rebuild matches the recorded statistics:", {k: got[k] for k in keys})
PY
  touch $D42/.done
fi

# ---- offline gate evals (same generator/scorer as every earlier version)
evals() {  # merged_dir name
  local M=$1 N=$2
  if ! python score.py /content/eval/${N}_ac_high.jsonl --gt $GT --modes high --expect model=$M,max_pixels=774400,enable_thinking=1 \
       --out /content/eval/${N}_ac_high.metrics.json > /dev/null 2>&1; then
    log "AndroidControl test, high-level (+ terminal rows): $N"
    python generate.py --model $M --data $R@test --out /content/eval/${N}_ac_high.jsonl --enable_thinking 1 --filter_mode high \
      --bs 32 --max_pixels 774400 --prompt_v4_pool $POOL \
      && python score.py /content/eval/${N}_ac_high.jsonl --gt $GT --modes high --expect model=$M,max_pixels=774400,enable_thinking=1 \
      --out /content/eval/${N}_ac_high.metrics.json > /dev/null || { log "AC EVAL FAILED: $N"; return 1; }
  fi
  for sp in dev_answer dev_complete; do
    if [ ! -s /content/eval/${N}_${sp}.metrics.json ]; then
      log "dev eval $N $sp"
      python generate.py --model $M --data "$DEV_REPO@$sp#$REV" --out /content/eval/${N}_${sp}.jsonl --enable_thinking 1 \
        --bs 32 --max_pixels 774400 --prompt_v4_pool $POOL \
        && python score_dev.py /content/eval/${N}_${sp}.jsonl --expect_n $([ $sp = dev_answer ] && echo 136 || echo 80) \
        --out /content/eval/${N}_${sp}.metrics.json || { log "DEV EVAL FAILED: $N $sp"; return 1; }
    fi
  done
  python - "$N" <<'PY'
import json, sys
n = sys.argv[1]
ac = json.load(open(f"/content/eval/{n}_ac_high.metrics.json"))
hi, term = ac["high"]["overall"], ac["terminal_complete"]
da = json.load(open(f"/content/eval/{n}_dev_answer.metrics.json"))
g = {"parse_rate": hi.get("parse_rate"), "ac_high_step_sr": hi.get("step_sr"), "terminal_complete": term.get("step_sr"),
     "dev_answer": da.get("step_sr"),
     "dev_complete": json.load(open(f"/content/eval/{n}_dev_complete.metrics.json")).get("step_sr")}
g["pass"] = bool((g["parse_rate"] or 0) >= 0.99 and (g["ac_high_step_sr"] or 0) >= 0.712
                 and (g["terminal_complete"] or 0) >= 0.70 and (g["dev_answer"] or 0) >= 0.848)
json.dump(g, open(f"/content/eval/{n}_offline_gate.json", "w"), indent=1)
print("OFFLINE GATE", n, json.dumps(g), flush=True)
PY
}

# ---- 2. P: step-DPO on v4.2's own mistakes
if [[ " $CANDIDATES " == *" P "* ]]; then
  OUTP=/content/runs/lfm3vl2b-v43dpo
  if [ ! -f $PAIRS/.done ]; then
    log "pairs from v4.2's own greedy mistakes"
    python v5_pairs.py --data $D42 --model $M42 --out $PAIRS --work $PW --splits /content/work/meta/splits.json \
      --n_rows ${PAIR_ROWS:-16000} && cp $PW/pairs_stats.json /content/eval/v43dpo_pairs_stats.json && touch $PAIRS/.done \
      || { log "PAIRS FAILED"; exit 1; }
  fi
  if [ ! -f /content/runs/v43dpo_smoke.ok ]; then
    log "DPO smoke test (16 pairs, 2 steps)"
    python dpo_vlm.py --model $M42 --pairs $PAIRS --out /content/runs/v43dpo_smoke --smoke 16 \
      && touch /content/runs/v43dpo_smoke.ok || { log "DPO SMOKE FAILED"; exit 1; }
  fi
  if [ ! -f $OUTP/train_receipt.json ]; then
    log "DPO training"
    python dpo_vlm.py --model $M42 --pairs $PAIRS --out $OUTP || { log "DPO TRAINING FAILED"; exit 1; }
  fi
  evals $OUTP/merged lfm3_v43dpo || log "P evals incomplete"
fi

# ---- 2b. P2 (post-hoc, PREREG 2026-11-22 20:15): stop/copy pairs only, balanced, stronger anchor, lower lr
if [[ " $CANDIDATES " == *" P2 "* ]]; then
  OUTP2=/content/runs/lfm3vl2b-v43dpo2
  [ -f $PAIRS/.done ] || { log "P2 needs P's pairs"; exit 1; }
  if [ ! -f $OUTP2/train_receipt.json ]; then
    log "P2 DPO training (early_stop + missed_stop<=356 + copied_intent; sft 1.0; lr 1e-5)"
    python dpo_vlm.py --model $M42 --pairs $PAIRS --out $OUTP2 --kinds early_stop,missed_stop,copied_intent \
      --cap_per_kind missed_stop=356 --sft_weight 1.0 --lr 1e-5 || { log "P2 DPO TRAINING FAILED"; exit 1; }
  fi
  evals $OUTP2/merged lfm3_v43dpo2 || log "P2 evals incomplete"
fi

# ---- 3. S: more SFT on v4.2's own mix
if [[ " $CANDIDATES " == *" S "* ]]; then
  OUTS=/content/runs/lfm3vl2b-v43sft
  if [ ! -f $OUTS/train_receipt.json ]; then
    log "S: 800 more SFT steps on v4.2's mix (WSD, lr ${S_LR:-1e-4}, sampler seed 5)"
    python sft_vlm.py --model_id $M42 --train $D42 --val $R@val --out $OUTS --max_steps 800 --scheduler wsd --decay_frac 0.15 \
      --lr ${S_LR:-1e-4} --seed 5 --max_pixels 774400 --bs 8 --grad_accum 4 --lora_r 64 --lora_alpha 128 \
      --modules_to_save --save_steps 400 --eval_steps 400 --workers 10 || { log "S TRAINING FAILED"; exit 1; }
  fi
  evals $OUTS/merged lfm3_v43sft || log "S evals incomplete"
fi
log "PIPELINE DONE"
