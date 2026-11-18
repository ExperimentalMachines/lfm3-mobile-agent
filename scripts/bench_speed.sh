#!/bin/bash
# Runs ON a benchmark host (GCP VM): for each model, start llama-server with the same flags as its evaluations
# (CPU, -t THREADS, -np 1), run eval/mobileworld/bench_speed.py, then parse that server's per-request timings and RSS.
# One model at a time on an otherwise idle machine. Usage: THREADS=8 bash bench_speed.sh > bench.log 2>&1
set -u
cd ~
T=${THREADS:-8}; OUT=~/bench/results_t$T; mkdir -p "$OUT"
S=llama.cpp/build/bin/llama-server
run() {  # name agent port server-args...
  local name=$1 agent=$2 port=$3; shift 3
  $S "$@" -np 1 -t "$T" --port "$port" --host 127.0.0.1 > "$OUT/server_$name.log" 2>&1 &
  local pid=$!
  until curl -s --max-time 5 127.0.0.1:$port/health | grep -q ok; do sleep 2; done
  (cd MobileWorld && .venv/bin/python ~/lfm3/bench_speed.py --agent "$agent" --url "http://127.0.0.1:$port/v1" \
      --shots ~/bench/shots --reps "${REPS:-3}" --out "$OUT/$name.json") > "$OUT/client_$name.log" 2>&1
  echo "$name rss_mb $(( $(ps -o rss= -p $pid) / 1024 ))" >> "$OUT/rss.txt"
  kill $pid; wait $pid 2>/dev/null
}
run v4 lfm3 8114 -m models/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf --mmproj models/mmproj-LFM3-VL-2B-Q8_0.gguf \
  -c 8192 --image-max-tokens 1024 --reasoning-format deepseek
run guiowl guiowl 8092 -m models/GUI-Owl-1.5-2B-Instruct.Q4_K_M.gguf --mmproj models/GUI-Owl-1.5-2B-Instruct.mmproj-Q8_0.gguf \
  -c 20480 --image-max-tokens 2600 --jinja
run maiui maiui 8093 -m models/MAI-UI-2B-Q4_K_M.gguf --mmproj models/mmproj-MAI-UI-2B-Q8_0.gguf \
  -c 20480 --image-max-tokens 2600 --jinja
echo BENCH_DONE
