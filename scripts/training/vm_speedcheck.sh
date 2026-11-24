#!/bin/bash
# Round 7 speed check (runs ON a Colab A100 inside the blocking cell; ~25 min).
# Question: is training limited by the GPU or by the CPU data loader? Colab trained v4 at 4.07 rows/s; the same script
# trained v3 on Modal at 9.09 rows/s. Same data shard and model for every config; only throughput settings change.
#   base : the recipe of every run so far (bs 8 x grad_accum 4, gradient checkpointing, 10 loader workers)
#   nogc : base without gradient checkpointing (same maths, more memory)
#   bs16 : nogc with bs 16 x grad_accum 2 (same 32 rows per step)
# Per config: 30 optimizer steps, no eval, no hub push; GPU utilisation (nvidia-smi) and CPU load (vmstat) sampled
# every 5 s. Steady-state speed = (elapsed at step 30 - elapsed at step 10) / 20 steps.
set -uo pipefail
unset HF_TOKEN  # public data and model only: no token in this job's environment
export TOKENIZERS_PARALLELISM=false
OUT=/content/runs/speedcheck; mkdir -p $OUT
log() { echo "[$(date +%T)] speed: $*"; }
cd /content/work
V4D=experimentalmachines/MobileAgent-SFT-v4; V4D_REV=337553984ee970a767dceb21adc6343f3d613602
SUB=/content/data/speed_v4

log "hardware: $(nproc) CPUs, $(free -g | awk '/Mem/{print $2}') GB RAM, $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
nproc > $OUT/nproc.txt; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader > $OUT/gpu.txt
if [ ! -f $SUB/.done ]; then
  log "download 2 of 16 v4 train shards @ $V4D_REV and keep 4,000 rows"
  python - <<PY || { log "DATA FAILED"; exit 1; }
from huggingface_hub import snapshot_download
from datasets import load_dataset
d = snapshot_download("$V4D", repo_type="dataset", revision="$V4D_REV", local_dir="/content/data/in_v4_speed",
                      allow_patterns=["data/train-00000-*", "data/train-00001-*"])
ds = load_dataset("parquet", data_files={"x": [f"{d}/data/train-00000-of-00016.parquet", f"{d}/data/train-00001-of-00016.parquet"]}, split="x")
ds.shuffle(seed=7).select(range(4000)).save_to_disk("$SUB")
print("rows", len(ds))
PY
  touch $SUB/.done
fi

run() {  # name extra-args...
  local N=$1; shift
  local O=$OUT/$N
  [ -f $O/logs/train_log.jsonl ] && grep -q '"step": 30' $O/logs/train_log.jsonl && { log "$N already done"; return 0; }
  rm -rf $O; mkdir -p $O
  nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits -l 5 > $OUT/gpu_$N.csv 2>/dev/null &
  local G=$!
  vmstat -n 5 > $OUT/cpu_$N.txt 2>/dev/null &
  local V=$!
  log "$N: start ($*)"
  python sft_vlm.py --model_id LiquidAI/LFM3-VL-2B --model_revision 23387beda43c60310348e83e25f78f33c3140d3a --train $SUB --out $O --max_steps 30 --max_pixels 774400 \
    --lora_r 64 --lora_alpha 128 --modules_to_save --save_steps 100000 "$@" > $OUT/train_$N.log 2>&1
  local rc=$?
  kill $G $V 2>/dev/null
  log "$N: exit $rc ($(grep -c '"step"' $O/logs/train_log.jsonl 2>/dev/null) log lines)"
  [ $rc != 0 ] && tail -5 $OUT/train_$N.log
  rm -rf $O/merged $O/lora $O/checkpoint-*  # only the logs matter
  return 0
}

run base --bs 8 --grad_accum 4 --workers 10
run nogc --bs 8 --grad_accum 4 --workers 10 --no_gc
run bs16 --bs 16 --grad_accum 2 --workers 10 --no_gc

python - <<'PY'
import json, os, statistics as st
OUT = "/content/runs/speedcheck"; res = {"cpus": open(f"{OUT}/nproc.txt").read().strip(), "gpu": open(f"{OUT}/gpu.txt").read().strip()}
for n in ("base", "nogc", "bs16"):
    r = {}
    try:
        recs = [json.loads(l) for l in open(f"{OUT}/{n}/logs/train_log.jsonl") if l.strip()]
        el = {x["step"]: x["elapsed_s"] for x in recs if "loss" in x}
        r["s_per_step"] = round((el[30] - el[10]) / 20, 2)
        r["rows_per_s"] = round(32 / r["s_per_step"], 2)
        r["peak_gpu_mem_gb"] = max(x.get("gpu_mem_gb", 0) for x in recs)
        r["loss_step30"] = el and [x["loss"] for x in recs if x["step"] == 30 and "loss" in x][0]
    except Exception as e:
        r["error"] = repr(e)[:200]
    try:
        g = [l.split(",") for l in open(f"{OUT}/gpu_{n}.csv") if l.strip()]
        u = [int(a) for a, _ in g]
        busy = u[len(u) // 4:]  # skip model load
        r["gpu_util_mean"] = round(st.mean(busy), 1); r["gpu_util_median"] = st.median(busy)
    except Exception as e:
        r["gpu_error"] = repr(e)[:120]
    try:
        rows = [l.split() for l in open(f"{OUT}/cpu_{n}.txt") if l.split() and l.split()[0].isdigit()]
        idle = [int(x[14]) for x in rows][len(rows) // 4:]
        r["cpu_busy_mean"] = round(100 - st.mean(idle), 1)
    except Exception as e:
        r["cpu_error"] = repr(e)[:120]
    res[n] = r
json.dump(res, open(f"{OUT}/summary.json", "w"), indent=1)
print("SPEEDCHECK", json.dumps(res), flush=True)
PY
log "SPEEDCHECK DONE"
