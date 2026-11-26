#!/bin/bash
# Round 13 step 1 (docs/PREREG_v411.md): SOP for a list of models on one llama-server port, one after the other.
# Each entry: name:gguf_dir_suffix:history_steps:notes. Usage: bash scripts/eval/run_sop_lane.sh <port> name:dir:hist:notes ...
set -u
cd "$(dirname "$0")/../.." || exit 1
PORT=$1; shift
MM=models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf
mkdir -p results/r13_dev
for spec in "$@"; do
  IFS=: read NAME DIR HIST NOTES <<< "$spec"
  GG=$(ls models/lfm3vl2b_$DIR-GGUF/*Q4_K_M.gguf | head -1)
  [ -s "$GG" ] || { echo "[$(date +%T)] $NAME: model missing"; continue; }
  curl -s -m 3 127.0.0.1:$PORT/health | grep -q ok && { echo "[$(date +%T)] port $PORT busy; stop"; exit 1; }
  nohup llama-server -m "$GG" --mmproj $MM -c 32768 -np 4 -ngl 99 --image-max-tokens 1024 --reasoning-format deepseek \
    --port $PORT --host 127.0.0.1 > logs/llama_server_sop_$NAME.log 2>&1 < /dev/null &
  SP=$!; t0=$(date +%s); ok=1
  until curl -s -m 3 127.0.0.1:$PORT/health | grep -q ok; do
    kill -0 $SP 2>/dev/null || { echo "[$(date +%T)] $NAME: server died"; ok=0; break; }
    [ $(( $(date +%s) - t0 )) -gt 600 ] && { kill $SP; echo "[$(date +%T)] $NAME: server not healthy"; ok=0; break; }
    sleep 3
  done
  [ $ok = 1 ] || continue
  echo "[$(date +%T)] $NAME: $(shasum -a 256 "$GG" | cut -c1-12) up on :$PORT"
  .venv-data/bin/python -I eval/androidcontrol/sop.py --server http://127.0.0.1:$PORT --name $NAME --history_steps $HIST \
    --notes $NOTES --episodes 400 --threads 4 --out results/r13_dev/sop_$NAME.jsonl 2>&1 | grep -v "^  " | tail -2
  kill $SP; sleep 3
done
echo "[$(date +%T)] lane $PORT done"
