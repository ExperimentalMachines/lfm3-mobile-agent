#!/bin/bash
# QDC phone speed, round 2 (SM8975, Android 17), identical settings for all three models in each part:
# llama.cpp b12110 CPU, -t 4 -np 1 --cache-ram 0 -fa on, MAI-UI Q8_0 (its Q4_K_M loops), client timeout 3600 s (no re-sends).
#  Option 1 "as evaluated": each model's evaluation image budget (v4 1024, GUI-Owl/MAI-UI 2600), 2 screenshots,
#           mirrored warm-up + 1 timed pass (order v4, GUI-Owl, MAI-UI).
#  Option 2 "equal image budget": all three at --image-max-tokens 1024, 5 screenshots, warm-up + 1 timed pass,
#           pass 1 v4 -> GUI-Owl -> MAI-UI, pass 2 reversed.
# Commits after each part. Usage: bash scripts/qdc_chain2.sh <serial>
cd "$(dirname "$0")/.."
SER=$1
export ADB_PORT=15037 EXTRA_FLAGS="-fa on" MAIUI_Q=Q8_0 CLIENT_TIMEOUT=3600 KEEP_FILES=1 REPS=1
RUN=results/qdc/run_$(date +%Y%m%d_%H%M)_v6; mkdir -p $RUN; echo $RUN > logs/qdc_run2.txt
log() { echo "[$(date +%T)] $*"; }
commit() { for i in 1 2 3; do git add $RUN results/qdc/smoke_v6_* 2>/dev/null && git commit -q -m "QDC round 2: $1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && { log "committed $(git log --oneline -1)"; return; }; sleep 5; done; }
log "option 1 (evaluation image budgets) -> $RUN/opt1_eval"
SHOT_N=2 ORDER_OVERRIDE="v4 guiowl maiui" bash scripts/devstream_device_v6.sh "$SER" 0 $RUN/opt1_eval > $RUN/opt1_stdout.log 2>&1
commit "option 1 (evaluation image budgets, -fa on, MAI-UI Q8_0)"; log "OPTION 1 DONE"
log "option 2 pass 1 (all at 1024 image tokens) -> $RUN/opt2_pass1"
IMG_TOKENS=1024 SHOT_N=5 ORDER_OVERRIDE="v4 guiowl maiui" bash scripts/devstream_device_v6.sh "$SER" 0 $RUN/opt2_pass1 > $RUN/opt2_pass1_stdout.log 2>&1
commit "option 2 pass 1 (equal 1024 image budget)"
log "option 2 pass 2 (reversed) -> $RUN/opt2_pass2"
IMG_TOKENS=1024 SHOT_N=5 ORDER_OVERRIDE="maiui guiowl v4" bash scripts/devstream_device_v6.sh "$SER" 0 $RUN/opt2_pass2 > $RUN/opt2_pass2_stdout.log 2>&1
mkdir -p $RUN/phone_final; adb -P $ADB_PORT -s "$SER" shell "ls -la /data/local/tmp/lfm3bench" > $RUN/phone_final/ls.txt 2>&1
commit "option 2 pass 2 (reversed) + phone listing"
log "QDC CHAIN2 DONE"
