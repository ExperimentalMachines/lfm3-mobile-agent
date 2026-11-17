#!/bin/bash
# v2 models: wait for the merged model on the Hub -> Q4_K_M GGUF (+ mmproj) -> llama-server -> AndroidWorld 116 once the
# emulator's previous job has logged its completion marker. The server is stopped afterwards (frees ~2 GB).
# Usage: scripts/local_v2_to_aw.sh <repo> <name> <kind lfm3|qwen> <port> <console_port> <grpc_port> <done_log>:<marker> <label>
set -u
cd /Users/alpha/lfm3-android
REPO=$1; NAME=$2; KIND=$3; PORT=$4; CP=$5; GP=$6; DONE=$7; LABEL=$8
DLOG=${DONE%%:*}; DMARK=${DONE#*:}
OUT=models/$NAME-GGUF
until uvx --from huggingface_hub python -c "
from huggingface_hub import HfApi; import sys
sys.exit(0 if 'config.json' in HfApi().list_repo_files('$REPO') else 1)" 2>/dev/null; do sleep 180; done
echo "[$(date +%T)] merged $REPO on hub; exporting ($KIND)"
if [ "$KIND" = lfm3 ]; then
  bash scripts/local_export_gguf.sh $REPO $OUT || { echo "EXPORT FAILED"; exit 1; }
  GG=$OUT/$(basename $REPO)-Q4_K_M.gguf
  MM=models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf   # LoRA is LM-only: the vision tower is the base model's
else
  mkdir -p $OUT
  uvx --from huggingface_hub hf download $REPO --local-dir $OUT/hf --exclude "lora_adapter/*" --exclude "eval/*" --exclude "training_logs/*" > /dev/null || { echo "DOWNLOAD FAILED"; exit 1; }
  .venv-convert/bin/python tools/llama.cpp/convert_hf_to_gguf.py $OUT/hf --outtype f16 --outfile $OUT/$NAME-F16.gguf 2>&1 | tail -1
  .venv-convert/bin/python tools/llama.cpp/convert_hf_to_gguf.py $OUT/hf --mmproj --outtype f16 --outfile $OUT/mmproj-$NAME-F16.gguf 2>&1 | tail -1
  llama-quantize $OUT/$NAME-F16.gguf $OUT/$NAME-Q4_K_M.gguf Q4_K_M 2>&1 | tail -1
  rm -rf $OUT/hf $OUT/$NAME-F16.gguf
  GG=$OUT/$NAME-Q4_K_M.gguf; MM=$OUT/mmproj-$NAME-F16.gguf
fi
[ -s "$GG" ] && [ -s "$MM" ] || { echo "EXPORT FAILED"; exit 1; }
ls -la $OUT
echo "[$(date +%T)] exported; waiting for emulator $CP ('$DMARK' in $DLOG)"
until grep -q "$DMARK" "$DLOG" 2>/dev/null && ! pgrep -f "[r]un_aw.py.*console_port=$CP" >/dev/null; do sleep 60; done
nohup llama-server -m $GG --mmproj $MM -c 8192 -np 1 -ngl 99 --image-max-tokens 1024 \
  --reasoning-format deepseek --port $PORT --host 127.0.0.1 > logs/llama_server_$NAME.log 2>&1 &
until curl -s 127.0.0.1:$PORT/health | grep -q ok; do sleep 3; done
echo "[$(date +%T)] server :$PORT up; starting $LABEL AndroidWorld on emulator $CP"
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=$CP --grpc_port=$GP --server_url=http://127.0.0.1:$PORT \
  --agent_label=$LABEL --enable_thinking=true --output_path=results/androidworld/$NAME 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" > logs/aw_run_$NAME.log
pkill -f "[l]lama-server.*--port $PORT "
echo "[$(date +%T)] $LABEL AndroidWorld finished"
