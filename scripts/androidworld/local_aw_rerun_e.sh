#!/bin/bash
# E (v4.6-E) held-out re-runs (docs/preregistrations/round-08-done-from-the-screen.md 2026-11-26 03:49): cold-boot one emulator as
# scripts/androidworld/local_sealed_aw_e.sh does, then scripts/androidworld/local_aw_rerun.sh with arm e. Only that emulator
# is stopped; the shared adb server is never touched.
# Usage: bash scripts/androidworld/local_aw_rerun_e.sh <seed> 5556|5558 <task1,task2,...> > logs/e_rerun_seed<seed>.log 2>&1
set -u; cd "$(dirname "$0")/../.." || exit 1
export ANDROID_SDK_ROOT=/opt/homebrew/share/android-commandlinetools ANDROID_HOME=/opt/homebrew/share/android-commandlinetools JAVA_HOME=/opt/homebrew/opt/openjdk@17
SEED=$1; CP=$2; TASKS=$3
case "$CP" in 5556) AVD=AndroidWorldAvd; EXTRA="-partition-size 3072"; PORT=8120 ;; 5558) AVD=AndroidWorldAvd2; EXTRA=""; PORT=8121 ;; esac
GP=$((CP + 3000))
if adb devices | grep -q "emulator-$CP"; then adb -s emulator-$CP emu kill > /dev/null 2>&1
  t0=$(date +%s); while adb devices | grep -q "emulator-$CP"; do sleep 2; [ $(( $(date +%s) - t0 )) -gt 120 ] && { echo "emulator $CP did not stop"; exit 1; }; done; sleep 5; fi
nohup "$ANDROID_SDK_ROOT/emulator/emulator" -avd "$AVD" -port "$CP" -grpc "$GP" -no-snapshot -no-window -no-audio -no-boot-anim -gpu swiftshader_indirect $EXTRA > "logs/emulator_rerun_e_$CP.log" 2>&1 < /dev/null &
t0=$(date +%s); until [ "$(adb -s emulator-$CP shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]; do [ $(( $(date +%s) - t0 )) -gt 600 ] && { echo "no boot"; exit 1; }; sleep 5; done
sleep 20; echo "[$(date +%T)] emulator-$CP cold-booted"
bash scripts/androidworld/local_aw_rerun.sh e $SEED $CP $GP $PORT results/androidworld_sealed/e_seed${SEED}_rerun "$TASKS"
