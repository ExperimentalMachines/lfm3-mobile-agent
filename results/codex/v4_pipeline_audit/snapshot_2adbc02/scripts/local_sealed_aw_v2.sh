#!/bin/bash
# Run one SEALED AndroidWorld arm on a held-out seed (docs/PREREG_v4.md): results go to results/androidworld_sealed/,
# per-task outcome lines are dropped from the log so nobody reads results before every arm on the seed has finished.
# Usage: bash scripts/local_sealed_aw_v2.sh <arm> <seed> <console_port> <grpc_port> <server_port> [resume_run_dir]
#   arm = v1 | v3 | v4 | guiowl
set -u
cd /Users/alpha/lfm3-android
ARM=$1; SEED=$2; CP=$3; GP=$4; PORT=$5; RESUME=${6:-}
NAME=${ARM}_seed${SEED}
OUT=results/androidworld_sealed/$NAME
LOG=logs/aw_sealed_$NAME.log
mkdir -p "$OUT"
# outcome lines (suite_utils prints "Task Successful/Failed") and android_env fork noise are not written to the log
FILTER="Task Successful\|Task Failed\|_os_env_vars\|FD from fork\|fork_posix"
case "$ARM" in
  v1) SRV=(-m models/LFM3-VL-2B-AndroidControl-GGUF/LFM3-VL-2B-AndroidControl-Q4_K_M.gguf
           --mmproj models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf -c 8192 --image-max-tokens 1024 --reasoning-format deepseek)
      RUN=(--agent=lfm --enable_thinking=true --agent_label=lfm3vl2b_v1_q4km) ;;
  v3) SRV=(-m models/lfm3vl2b_v3-GGUF/LFM3-VL-2B-AndroidAgent-v3-Q4_K_M.gguf
           --mmproj models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf -c 8192 --image-max-tokens 1024 --reasoning-format deepseek)
      RUN=(--agent=lfm --enable_thinking=true --agent_label=lfm3vl2b_v3_q4km) ;;
  v4) SRV=(-m models/lfm3vl2b_v4-GGUF/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf
           --mmproj models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf -c 8192 --image-max-tokens 1024 --reasoning-format deepseek)
      RUN=(--agent=lfm --enable_thinking=true --prompt_version=v4 --agent_label=lfm3vl2b_v4_q4km) ;;
  guiowl) SRV=(-m models/GUI-Owl-1.5-2B-GGUF/GUI-Owl-1.5-2B-Instruct.Q4_K_M.gguf
               --mmproj models/GUI-Owl-1.5-2B-GGUF/GUI-Owl-1.5-2B-Instruct.mmproj-Q8_0.gguf -c 20480 --image-max-tokens 2600 --jinja)
      RUN=(--agent=guiowl --guiowl_images=1 --guiowl_max_pixels=1048576 --installed_apps=true
           --agent_label=guiowl15_2b_matched1img_apps_q4km) ;;
  *) echo "unknown arm $ARM"; exit 2 ;;
esac
for f in "${SRV[1]}" "${SRV[3]}"; do [ -s "$f" ] || { echo "missing $f"; exit 1; }; done
curl -s 127.0.0.1:$PORT/health | grep -q ok && { echo "port $PORT already serving; refusing"; exit 1; }
nohup llama-server "${SRV[@]}" -np 1 -ngl 99 --port $PORT --host 127.0.0.1 > logs/llama_server_$NAME.log 2>&1 < /dev/null &
until curl -s 127.0.0.1:$PORT/health | grep -q ok; do sleep 3; done
echo "[$(date +%T)] server :$PORT up; starting SEALED $NAME (seed $SEED) on emulator $CP"
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=$CP --grpc_port=$GP --server_url=http://127.0.0.1:$PORT \
  --task_random_seed=$SEED --n_task_combinations=1 --output_path=$OUT ${RESUME:+--checkpoint_dir=$RESUME} "${RUN[@]}" 2>&1 \
  | grep --line-buffered -v "$FILTER" >> "$LOG"
pkill -f "[l]lama-server.*--port $PORT "
echo "[$(date +%T)] SEALED $NAME AndroidWorld finished"
