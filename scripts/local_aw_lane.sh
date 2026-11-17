#!/bin/bash
# Resume one emulator "lane" of the AndroidWorld queue after a host reboot (all local processes die on reboot).
# lane1 (5556): GUI-Owl matched reference (resume).  lane2 (5558): 450M base (resume) -> LFM3 FT + runtime_feedback ablation.
# Qwen hand-offs (local_qwen_to_aw.sh) wait on "^bash scripts/local_aw_lane.sh <lane>" + the emulator being free.
# Usage: bash scripts/local_aw_lane.sh lane1|lane2
set -u
cd /Users/alpha/lfm3-android
export ANDROID_SDK_ROOT=/opt/homebrew/share/android-commandlinetools ANDROID_HOME=/opt/homebrew/share/android-commandlinetools \
       JAVA_HOME=/opt/homebrew/opt/openjdk@17
EMU=$ANDROID_SDK_ROOT/emulator/emulator
FILTER="_os_env_vars\|FD from fork\|fork_posix"
boot() {  # avd console grpc log [extra args]
  adb devices | grep -q "emulator-$2" || nohup $EMU -avd "$1" -port "$2" -grpc "$3" -no-snapshot -no-window -no-audio \
      -no-boot-anim -gpu swiftshader_indirect ${5:-} > "$4" 2>&1 < /dev/null &
  until [ "$(adb -s emulator-$2 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]; do sleep 5; done
  sleep 20; echo "[$(date +%T)] emulator-$2 booted"
}
serve() {  # port log args...
  local port=$1 log=$2; shift 2
  curl -s 127.0.0.1:$port/health | grep -q ok || nohup llama-server "$@" --port $port --host 127.0.0.1 > "$log" 2>&1 < /dev/null &
  until curl -s 127.0.0.1:$port/health | grep -q ok; do sleep 3; done; echo "[$(date +%T)] server :$port up"
}
stop_server() { pkill -f "[l]lama-server.*--port $1 " ; true; }
case "$1" in
lane1)
  boot AndroidWorldAvd 5556 8556 logs/emulator_aw.log "-partition-size 3072"
  serve 8092 logs/llama_server_guiowl.log -m models/GUI-Owl-1.5-2B-GGUF/GUI-Owl-1.5-2B-Instruct.Q4_K_M.gguf \
    --mmproj models/GUI-Owl-1.5-2B-GGUF/GUI-Owl-1.5-2B-Instruct.mmproj-Q8_0.gguf -c 20480 -np 1 -ngl 99 --image-max-tokens 2600 --jinja
  echo "[$(date +%T)] resuming GUI-Owl matched reference"
  .venv-aw/bin/python eval/androidworld/run_aw.py --agent=guiowl --guiowl_images=1 --guiowl_max_pixels=1048576 --console_port=5556 \
    --grpc_port=8556 --server_url=http://127.0.0.1:8092 --agent_label=guiowl15_2b_matched1img_q4km \
    --checkpoint_dir=results/androidworld/guiowl15_2b_matched/run_20261116T231457945810 2>&1 \
    | grep --line-buffered -v "$FILTER" >> logs/aw_run_guiowl_matched.log
  stop_server 8092; echo "[$(date +%T)] GUI-Owl reference run finished" ;;
lane2)
  boot AndroidWorldAvd2 5558 8558 logs/emulator_aw2.log
  serve 8095 logs/llama_server_450m_base.log -m models/LFM2.5-VL-450M-GGUF/LFM2.5-VL-450M-Q4_K_M.gguf \
    --mmproj models/LFM2.5-VL-450M-GGUF/mmproj-LFM2.5-VL-450m-Q8_0.gguf -c 8192 -np 1 -ngl 99 --image-max-tokens 2048 --reasoning-format deepseek
  echo "[$(date +%T)] resuming 450M base"
  .venv-aw/bin/python eval/androidworld/run_aw.py --console_port=5558 --grpc_port=8558 --server_url=http://127.0.0.1:8095 \
    --agent_label=lfm25vl450m_base_q4km --enable_thinking=false \
    --checkpoint_dir=results/androidworld/lfm25vl450m_base/run_20261117T062246232259 2>&1 \
    | grep --line-buffered -v "$FILTER" >> logs/aw_run_450m_base.log
  stop_server 8095; echo "[$(date +%T)] 450M base finished; starting runtime-feedback ablation"
  bash scripts/local_runtime_ablation_aw.sh >> logs/local_runtime_ablation.log 2>&1
  stop_server 8096; echo "[$(date +%T)] lane2 done" ;;
esac
