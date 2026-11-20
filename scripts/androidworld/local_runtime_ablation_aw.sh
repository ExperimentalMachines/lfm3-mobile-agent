#!/bin/bash
# Ablation (Codex final-audit rec. #1): LFM3-VL-2B FT, same GGUF/server/seed as the main run, plus --runtime_feedback
# (lexical open_app resolution against installed apps + failure / no-visible-change notes in the history).
# Runs on emulator 2 (5558/8558) after the 450M base run there has finished.
cd "$(dirname "$0")/../.." || exit 1
sleep 5
while pgrep -f "local_450m_base_aw.sh" >/dev/null || pgrep -f "agent_label=lfm25vl450m" >/dev/null; do sleep 60; done
until curl -s 127.0.0.1:8096/health | grep -q ok; do
  echo "[$(date +%T)] LFM3 FT server not up; starting it"
  nohup llama-server -m models/LFM3-VL-2B-AndroidControl-GGUF/LFM3-VL-2B-AndroidControl-Q4_K_M.gguf \
    --mmproj models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf -c 8192 -np 1 -ngl 99 --image-max-tokens 1024 \
    --reasoning-format deepseek --port 8096 --host 127.0.0.1 > logs/llama_server_lfm3_ft_ablation.log 2>&1 &
  sleep 30
done
echo "[$(date +%T)] starting LFM3 FT + runtime_feedback AndroidWorld on emulator 2"
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=5558 --grpc_port=8558 --server_url=http://127.0.0.1:8096 \
  --agent_label=lfm3vl2b_ft_q4km_runtimefb --enable_thinking=true --runtime_feedback=true \
  --output_path=results/androidworld/lfm3vl2b_ft_runtimefb 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" > logs/aw_run_lfm3_ft_runtimefb.log
echo "[$(date +%T)] ablation finished"
