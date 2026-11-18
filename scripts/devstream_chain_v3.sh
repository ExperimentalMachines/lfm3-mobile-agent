#!/bin/bash
# Pass 2 for the single-Pixel-9 benchmark after pass 1 (worker v3, already running, 3 timed passes per model):
# reversed order (maiui, guiowl, v4) with 1 timed pass per model (budget: phone CPU ~42 s/step for v4, ~5 min/step for
# GUI-Owl/MAI-UI), then pull leftovers, release the reservation and commit. Usage: bash scripts/devstream_chain_v3.sh <serial> <reservation>
cd "$(dirname "$0")/.."
SER=$1; R=$2; RUN=$(cat logs/devstream_run.txt)
log() { echo "[$(date +%T)] $*"; }
until grep -q "WORKER DONE" $RUN/dev0/worker.log 2>/dev/null; do sleep 30; done
log "pass 1 done; pass 2 (maiui guiowl v4), 1 timed pass each"
REPS=1 ORDER_OVERRIDE="maiui guiowl v4" bash scripts/devstream_device_v4.sh "$SER" 0 $RUN/dev0_pass2 > $RUN/dev0_pass2_stdout.log 2>&1
log "pass 2 done"
mkdir -p $RUN/phone_final; adb -s "$SER" shell "ls -la /data/local/tmp/lfm3bench" > $RUN/phone_final/ls.txt 2>&1
adb -s "$SER" pull /data/local/tmp/lfm3bench/. $RUN/phone_final/ > /dev/null 2>&1
touch logs/devstream_stop
bash scripts/android_cli.sh device remote disconnect $R --project voltaic-psyche-514908-s2 2>&1 | tail -1
bash scripts/android_cli.sh device remote remove $R --project voltaic-psyche-514908-s2 2>&1 | tail -1
log "reservation released"
git add $RUN logs/devstream_reservations.log 2>/dev/null; git commit -q -m "Device-streaming speed benchmark results (Pixel 9, Android 16; pass 1 x3, pass 2 reversed x1): $RUN

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && log "committed $(git log --oneline -1)"
log "CHAIN DONE"
