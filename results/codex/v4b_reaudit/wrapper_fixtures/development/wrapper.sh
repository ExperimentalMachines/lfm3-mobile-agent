#!/bin/bash
# v4 hand-off: wait for merged v4 weights on the hub -> phone GGUF -> pause the sealed v1 seed-7 arm on emulator 2
# -> AndroidWorld seed-30 DEVELOPMENT pass with the v4 prompt (not sealed; gate in docs/PREREG_v4.md).
# Usage: bash scripts/local_v4_to_aw.sh <final_repo>
set -u
cd /Users/alpha/lfm3-android/results/codex/v4b_reaudit/wrapper_fixtures/development
REPO=$1; OUT=models/lfm3vl2b_v4-GGUF; NAME=lfm3vl2b_v4; PORT=8114; CP=5558; GP=8558
GG=$OUT/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf; MM=models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf
echo "[$(date +%T)] waiting for merged weights in $REPO"
until .venv-convert/bin/python - "$REPO" <<'PY'
import sys
from huggingface_hub import HfApi
try:
    fs = {s.rfilename for s in HfApi().model_info(sys.argv[1]).siblings}
except Exception:
    sys.exit(1)
sys.exit(0 if "config.json" in fs and any(f.endswith(".safetensors") for f in fs) and any(f.startswith("lora_adapter/") for f in fs) else 1)
PY
do sleep 120; done
echo "[$(date +%T)] merged weights on hub; exporting"
bash scripts/local_export_gguf.sh "$REPO" "$OUT" || { echo "EXPORT FAILED"; exit 1; }
[ -s "$GG" ] && [ -s "$MM" ] || { echo "EXPORT FAILED (missing $GG)"; exit 1; }
echo "[$(date +%T)] exported; pausing the sealed v1 seed-7 arm on emulator $CP (resumed afterwards from its checkpoint)"
RESUME_V1=""
if ! grep -q "SEALED v1_seed7 AndroidWorld finished$" logs/local_sealed_v1_seed7.log 2>/dev/null; then
  bash scripts/pause_sealed_arm.sh v1 7 8111
  RESUME_V1=$(ls -d results/androidworld_sealed/v1_seed7/run_* | tail -1)
fi
until ! pgrep -f "[r]un_aw.py.*console_port=$CP" >/dev/null; do sleep 10; done
nohup llama-server -m $GG --mmproj $MM -c 8192 -np 1 -ngl 99 --image-max-tokens 1024 \
  --reasoning-format deepseek --port $PORT --host 127.0.0.1 > logs/llama_server_$NAME.log 2>&1 < /dev/null &
until curl -s 127.0.0.1:$PORT/health | grep -q ok; do sleep 3; done
echo "[$(date +%T)] server :$PORT up; starting v4 seed-30 development pass on emulator $CP"
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=$CP --grpc_port=$GP --server_url=http://127.0.0.1:$PORT \
  --agent_label=lfm3vl2b_v4_q4km --enable_thinking=true --prompt_version=v4 --output_path=results/androidworld/$NAME 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" > logs/aw_run_$NAME.log
pkill -f "[l]lama-server.*--port $PORT "
echo "[$(date +%T)] v4 AndroidWorld seed-30 finished"
if [ -n "$RESUME_V1" ]; then
  echo "[$(date +%T)] resuming sealed v1 seed-7 from $RESUME_V1"
  bash scripts/local_sealed_aw_v2.sh v1 7 $CP $GP 8111 "$RESUME_V1" >> logs/local_sealed_v1_seed7.log 2>&1
fi
