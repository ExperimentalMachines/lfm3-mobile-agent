#!/bin/bash
# LFM3-VL-2B v2 + force_think (inference-only ablation), emulator 1 after the plain v2 run; server :8102 (same GGUF).
cd "$(dirname "$0")/../.." || exit 1
until grep -q "AndroidWorld finished" logs/local_lfm3v2_to_aw.log 2>/dev/null && ! pgrep -f "[r]un_aw.py.*console_port=5556" >/dev/null; do sleep 60; done
until curl -s 127.0.0.1:8102/health | grep -q ok; do
  nohup llama-server -m models/lfm3vl2b_v2-GGUF/LFM3-VL-2B-AndroidAgent-v2-Q4_K_M.gguf --mmproj models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf \
    -c 8192 -np 1 -ngl 99 --image-max-tokens 1024 --reasoning-format deepseek --port 8102 --host 127.0.0.1 > logs/llama_server_lfm3v2_test.log 2>&1 &
  sleep 20
done
echo "[$(date +%T)] starting LFM3 v2 + force_think AndroidWorld on emulator 1"
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=5556 --grpc_port=8556 --server_url=http://127.0.0.1:8102 \
  --agent_label=lfm3vl2b_v2_q4km_forcethink --enable_thinking=true --force_think=true \
  --output_path=results/androidworld/lfm3vl2b_v2_forcethink 2>&1 | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" > logs/aw_run_lfm3v2_forcethink.log
pkill -f "[l]lama-server.*--port 8102 "
echo "[$(date +%T)] force_think AndroidWorld finished"
