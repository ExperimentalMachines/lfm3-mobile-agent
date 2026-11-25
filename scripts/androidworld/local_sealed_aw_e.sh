#!/bin/bash
# E (v4.6-E) on one held-out AndroidWorld seed (docs/PREREG_v46.md, 2026-11-25 20:33; owner decision, post-hoc).
# Same sealing as local_sealed_aw_v3.sh (v4's held-out runs): results in results/androidworld_sealed/e_seed<seed>/, the
# runner's output only inside that folder with outcome lines filtered out, "finished" = exit 0 and 116 episode files.
# Differences: E's model file and harness flags (variant U, as its seed-30 pass), and a cold-booted emulator for every
# pass (as local_v41_dev_aw.sh since 2026-11-22: a second pass on the same emulator loses its accessibility tree).
# Only this pass's own emulator is stopped; the shared adb server is never touched.
# Usage: nohup bash scripts/androidworld/local_sealed_aw_e.sh <seed> 5556|5558 [resume_run_dir] > logs/sealed_e_seed<seed>.log 2>&1 &
set -u
cd "$(dirname "$0")/../.." || exit 1
export ANDROID_SDK_ROOT=/opt/homebrew/share/android-commandlinetools ANDROID_HOME=/opt/homebrew/share/android-commandlinetools \
       JAVA_HOME=/opt/homebrew/opt/openjdk@17
SEED=${1:?seed}; CP=${2:?console port}; RESUME=${3:-}
case "$CP" in
  5556) AVD=AndroidWorldAvd; EXTRA="-partition-size 3072"; PORT=8120 ;;
  5558) AVD=AndroidWorldAvd2; EXTRA=""; PORT=8121 ;;
  *) echo "console port must be 5556 or 5558"; exit 1 ;;
esac
GP=$((CP + 3000))
GG=models/lfm3vl2b_v46e-GGUF/LFM3-VL-2B-MobileAgent-v4.6-E-Q4_K_M.gguf
MM=models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf
NAME=e_seed${SEED}
OUT=results/androidworld_sealed/$NAME
LOG=$OUT/run_output.SEALED.log
FILTER="Task Successful\|Task Failed\|_os_env_vars\|FD from fork\|fork_posix"
log() { echo "[$(date +%T)] $NAME: $*"; }
for f in "$GG" "$MM"; do [ -s "$f" ] || { log "missing $f; NOT STARTED"; exit 1; }; done
[ "$(shasum -a 256 "$GG" | cut -c1-8)" = fa8f2dca ] || { log "model sha256 is not fa8f2dca (the published E GGUF); NOT STARTED"; exit 1; }
if [ -n "$RESUME" ]; then
  [ -d "$RESUME" ] || { log "resume dir $RESUME missing"; exit 1; }
  CK=(--checkpoint_dir="$RESUME")
else
  [ -e "$OUT" ] && { log "$OUT exists; refusing to mix runs (pass its run_* dir to resume)"; exit 1; }
  CK=()
fi
mkdir -p "$OUT"
pgrep -f "[r]un_aw.py.*console_port=$CP( |$)" > /dev/null && { log "emulator $CP busy (run_aw.py running)"; exit 1; }
if adb devices | grep -q "emulator-$CP"; then
  adb -s emulator-$CP emu kill > /dev/null 2>&1
  t0=$(date +%s); while adb devices | grep -q "emulator-$CP"; do sleep 2; [ $(( $(date +%s) - t0 )) -gt 120 ] && { log "emulator $CP did not stop"; exit 1; }; done
  sleep 5; log "emulator-$CP stopped for a cold boot"
fi
nohup "$ANDROID_SDK_ROOT/emulator/emulator" -avd "$AVD" -port "$CP" -grpc "$GP" -no-snapshot -no-window -no-audio \
  -no-boot-anim -gpu swiftshader_indirect $EXTRA > "logs/emulator_sealed_e_$CP.log" 2>&1 < /dev/null &
t0=$(date +%s)
until [ "$(adb -s emulator-$CP shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]; do
  [ $(( $(date +%s) - t0 )) -gt 600 ] && { log "emulator $CP did not boot in 600 s"; exit 1; }
  sleep 5
done
sleep 20; log "emulator-$CP booted"
curl -s 127.0.0.1:$PORT/health | grep -q ok && { log "port $PORT already in use; NOT STARTED"; exit 1; }
nohup llama-server -m "$GG" --mmproj "$MM" -c 8192 -np 1 -ngl 99 --image-max-tokens 1024 --reasoning-format deepseek \
  --port $PORT --host 127.0.0.1 > "logs/llama_server_sealed_$NAME.log" 2>&1 < /dev/null &
SP=$!; t0=$(date +%s)
until curl -s --max-time 5 127.0.0.1:$PORT/health | grep -q ok; do
  kill -0 $SP 2>/dev/null || { log "llama-server exited during startup"; exit 1; }
  [ $(( $(date +%s) - t0 )) -gt 600 ] && { kill $SP; log "llama-server not healthy after 600 s"; exit 1; }
  sleep 3
done
log "server :$PORT up (pid $SP); SEALED seed $SEED on emulator $CP"
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=$CP --grpc_port=$GP --server_url=http://127.0.0.1:$PORT \
  --task_random_seed=$SEED --n_task_combinations=1 --agent=lfm --agent_label=lfm3vl2b_v46e_q4km --enable_thinking=true \
  --prompt_version=v4 --guards=false --history_steps=24 --nochange_notes=true --change_rule=fine \
  --output_path=$OUT ${CK[@]+"${CK[@]}"} 2>&1 | grep --line-buffered -v "$FILTER" >> "$LOG"
RC=${PIPESTATUS[0]}
kill $SP 2>/dev/null
N=$(ls -d $OUT/run_*/ 2>/dev/null | tail -1 | xargs -I{} sh -c 'ls {}*.pkl.gz 2>/dev/null | wc -l' | tr -d ' ')
if [ "$RC" = 0 ] && [ "${N:-0}" = 116 ]; then log "SEALED AndroidWorld finished"
else log "SEALED AndroidWorld FAILED (exit $RC, ${N:-0}/116 episodes)"; exit 1; fi
