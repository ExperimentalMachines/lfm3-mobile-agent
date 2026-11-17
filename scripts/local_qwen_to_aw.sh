#!/bin/bash
# Wait for a merged Qwen3.5 fine-tune on the Hub -> Q4_K_M GGUF + F16 mmproj (llama.cpp converter, validated on the
# base model 2026-11-17) -> llama-server -> AndroidWorld 116 on the given emulator once its predecessor job is done.
# Usage: scripts/local_qwen_to_aw.sh <repo> <name> <server_port> <console_port> <grpc_port> <done_log>:<done_marker> <label>
# (waits for <done_marker> to appear in <done_log>: pgrep on a predecessor script is unreliable because its background
#  subshells — e.g. the emulator's parent — keep the same argv for as long as the emulator runs)
set -u
cd /Users/alpha/lfm3-android
REPO=$1; NAME=$2; PORT=$3; CP=$4; GP=$5; DONE=$6; LABEL=$7
DLOG=${DONE%%:*}; DMARK=${DONE#*:}
OUT=models/$NAME-GGUF
until uvx --from huggingface_hub python -c "
from huggingface_hub import HfApi; import sys
sys.exit(0 if 'config.json' in HfApi().list_repo_files('$REPO') else 1)" 2>/dev/null; do sleep 300; done
echo "[$(date +%T)] merged $REPO on hub; exporting"
mkdir -p $OUT
uvx --from huggingface_hub hf download $REPO --local-dir $OUT/hf --exclude "lora_adapter/*" --exclude "eval/*" --exclude "training_logs/*" > /dev/null || { echo "DOWNLOAD FAILED"; exit 1; }
.venv-convert/bin/python tools/llama.cpp/convert_hf_to_gguf.py $OUT/hf --outtype f16 --outfile $OUT/$NAME-F16.gguf 2>&1 | tail -1
.venv-convert/bin/python tools/llama.cpp/convert_hf_to_gguf.py $OUT/hf --mmproj --outtype f16 --outfile $OUT/mmproj-$NAME-F16.gguf 2>&1 | tail -1
llama-quantize $OUT/$NAME-F16.gguf $OUT/$NAME-Q4_K_M.gguf Q4_K_M 2>&1 | tail -1
[ -s $OUT/$NAME-Q4_K_M.gguf ] && [ -s $OUT/mmproj-$NAME-F16.gguf ] || { echo "EXPORT FAILED"; exit 1; }
rm -rf $OUT/hf $OUT/$NAME-F16.gguf
ls -la $OUT
nohup llama-server -m $OUT/$NAME-Q4_K_M.gguf --mmproj $OUT/mmproj-$NAME-F16.gguf -c 8192 -np 1 -ngl 99 --image-max-tokens 1024 \
  --reasoning-format deepseek --port $PORT --host 127.0.0.1 > logs/llama_server_$NAME.log 2>&1 &
until curl -s 127.0.0.1:$PORT/health | grep -q ok; do sleep 3; done
echo "[$(date +%T)] server up on :$PORT; waiting for emulator $CP ('$DMARK' in $DLOG)"
until grep -q "$DMARK" "$DLOG" 2>/dev/null && ! pgrep -f "[r]un_aw.py.*console_port=$CP" >/dev/null; do sleep 60; done
echo "[$(date +%T)] starting $LABEL AndroidWorld on emulator $CP"
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=$CP --grpc_port=$GP --server_url=http://127.0.0.1:$PORT \
  --agent_label=$LABEL --enable_thinking=true --output_path=results/androidworld/$NAME 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" > logs/aw_run_$NAME.log
echo "[$(date +%T)] $LABEL AndroidWorld finished"
