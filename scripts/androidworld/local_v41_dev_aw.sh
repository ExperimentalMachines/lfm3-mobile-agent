#!/bin/bash
# v4.1 follow-up (docs/PREREG_v41.md): one AndroidWorld seed-30 development pass for variant A-E.
#   A = v4 + guards, B = v4.1, C = v4.1 + guards, D = v4.2 + guards, E = v4.2,
#   R = v4.2 replicate (identical to E, separate output; measures run-to-run noise),
#   P = v4.3-dpo (round 5: DPO on own mistakes), S = v4.3-sft (round 5: more SFT on the same mix).
# Same harness as v4's seed-30 pass (scripts/androidworld/local_v4_to_aw_v2.sh): run_aw.py defaults (seed 30, one
# instance per task), prompt v4, thinking on, same llama-server flags and mmproj; only the model file and --guards vary.
# Usage: nohup bash scripts/androidworld/local_v41_dev_aw.sh A|B|C|D|E|R|P|S 5556|5558 [checkpoint_dir_to_resume] \
#          >> logs/local_v41_dev_aw.log 2>&1 &
set -u
cd "$(dirname "$0")/../.." || exit 1
export ANDROID_SDK_ROOT=/opt/homebrew/share/android-commandlinetools ANDROID_HOME=/opt/homebrew/share/android-commandlinetools \
       JAVA_HOME=/opt/homebrew/opt/openjdk@17
V=${1:-}; CP=${2:-}; RESUME=${3:-}
case "$CP" in
  5556) AVD=AndroidWorldAvd; EXTRA="-partition-size 3072"; PORT=8120 ;;
  5558) AVD=AndroidWorldAvd2; EXTRA=""; PORT=8121 ;;
  *) echo "console port must be 5556 or 5558"; exit 1 ;;
esac
GP=$((CP + 3000))
V41=models/lfm3vl2b_v41-GGUF/LFM3-VL-2B-AndroidAgent-v4.1-Q4_K_M.gguf
V42=models/lfm3vl2b_v42-GGUF/LFM3-VL-2B-AndroidAgent-v4.2-Q4_K_M.gguf
case "$V" in
  A) GG=models/lfm3vl2b_v4-GGUF/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf; NAME=lfm3vl2b_v4_guards; G=true ;;
  B) GG=$V41; NAME=lfm3vl2b_v41; G=false ;;
  C) GG=$V41; NAME=lfm3vl2b_v41_guards; G=true ;;
  D) GG=$V42; NAME=lfm3vl2b_v42_guards; G=true ;;
  E) GG=$V42; NAME=lfm3vl2b_v42; G=false ;;
  R) GG=$V42; NAME=lfm3vl2b_v42_rep; G=false ;;
  P) GG=models/lfm3vl2b_v43-dpo-GGUF/LFM3-VL-2B-AndroidAgent-v4.3-dpo-Q4_K_M.gguf; NAME=lfm3vl2b_v43dpo; G=false ;;
  S) GG=models/lfm3vl2b_v43-sft-GGUF/LFM3-VL-2B-AndroidAgent-v4.3-sft-Q4_K_M.gguf; NAME=lfm3vl2b_v43sft; G=false ;;
  *) echo "variant must be A, B, C, D, E, R, P or S"; exit 1 ;;
esac
MM=models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf
OUT=results/androidworld/$NAME
log() { echo "[$(date +%T)] $NAME: $*"; }
[ -s "$GG" ] && [ -s "$MM" ] || { log "model file missing ($GG); NOT STARTED"; exit 1; }
if [ -n "$RESUME" ]; then
  [ -d "$RESUME" ] || { log "resume dir $RESUME missing"; exit 1; }
  CK=(--checkpoint_dir="$RESUME")
else
  [ -e "$OUT" ] && { log "$OUT exists; refusing to mix runs (pass its run_* dir to resume)"; exit 1; }
  CK=()
fi
pgrep -f "[r]un_aw.py.*console_port=$CP( |$)" > /dev/null && { log "emulator $CP busy (run_aw.py running)"; exit 1; }
if ! adb devices | grep -q "emulator-$CP"; then
  nohup "$ANDROID_SDK_ROOT/emulator/emulator" -avd "$AVD" -port "$CP" -grpc "$GP" -no-snapshot -no-window -no-audio \
    -no-boot-anim -gpu swiftshader_indirect $EXTRA > "logs/emulator_v41_$CP.log" 2>&1 < /dev/null &
  t0=$(date +%s)
  until [ "$(adb -s emulator-$CP shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]; do
    [ $(( $(date +%s) - t0 )) -gt 600 ] && { log "emulator $CP did not boot in 600 s"; exit 1; }
    sleep 5
  done
  sleep 20; log "emulator-$CP booted"
fi
curl -s 127.0.0.1:$PORT/health | grep -q ok && { log "port $PORT already in use; NOT STARTED"; exit 1; }
nohup llama-server -m "$GG" --mmproj "$MM" -c 8192 -np 1 -ngl 99 --image-max-tokens 1024 --reasoning-format deepseek \
  --port $PORT --host 127.0.0.1 > "logs/llama_server_$NAME.log" 2>&1 < /dev/null &
SP=$!
t0=$(date +%s)
until curl -s 127.0.0.1:$PORT/health | grep -q ok; do
  kill -0 $SP 2>/dev/null || { log "llama-server exited during startup"; exit 1; }
  [ $(( $(date +%s) - t0 )) -gt 600 ] && { kill $SP; log "llama-server not healthy after 600 s"; exit 1; }
  sleep 3
done
shasum -a 256 "$GG" | cut -c1-16 | sed "s/^/[$(date +%T)] $NAME: model sha256 /"
log "server :$PORT up (pid $SP); seed-30 pass on emulator $CP, guards=$G"
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=$CP --grpc_port=$GP --server_url=http://127.0.0.1:$PORT \
  --agent_label=${NAME}_q4km --enable_thinking=true --prompt_version=v4 --guards=$G --output_path=$OUT ${CK[@]+"${CK[@]}"} 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" >> "logs/aw_run_$NAME.log"
kill $SP 2>/dev/null
D=$(ls -d $OUT/run_*/ 2>/dev/null | tail -1); D=${D%/}
N=$([ -n "$D" ] && ls "$D"/*.pkl.gz 2>/dev/null | wc -l | tr -d ' ' || echo 0)
[ "$N" = 116 ] && log "complete: 116 episodes in $D" || log "INCOMPLETE: $N/116 episodes in ${D:-none}"
