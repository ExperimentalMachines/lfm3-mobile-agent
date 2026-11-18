#!/bin/bash
# QDC speed benchmark on one Snapdragon 8 Elite Extreme Gen 6 (SM8975) reference phone: pass 1 (v4, guiowl, maiui) then
# pass 2 (maiui, guiowl, v4), 3 timed passes each, worker v5 (remote adb server via the SSH tunnel on $ADB_PORT).
# Pulls leftovers and commits; the QDC session itself is left to the user. Usage: bash scripts/qdc_chain.sh <serial>
cd "$(dirname "$0")/.."
SER=$1; export ADB_PORT=${ADB_PORT:-15037}
RUN=results/qdc/run_$(date +%Y%m%d_%H%M); mkdir -p $RUN; echo $RUN > logs/qdc_run.txt
log() { echo "[$(date +%T)] $*"; }
log "pass 1 (v4 guiowl maiui) -> $RUN/dev0"
REPS=3 bash scripts/devstream_device_v5.sh "$SER" 0 $RUN/dev0 > $RUN/dev0_stdout.log 2>&1
log "pass 2 (maiui guiowl v4) -> $RUN/dev0_pass2"
REPS=3 ORDER_OVERRIDE="maiui guiowl v4" bash scripts/devstream_device_v5.sh "$SER" 0 $RUN/dev0_pass2 > $RUN/dev0_pass2_stdout.log 2>&1
mkdir -p $RUN/phone_final; adb -P $ADB_PORT -s "$SER" shell "ls -la /data/local/tmp/lfm3bench" > $RUN/phone_final/ls.txt 2>&1
for f in $(adb -P $ADB_PORT -s "$SER" shell "ls /data/local/tmp/lfm3bench/*.log" 2>/dev/null | tr -d '\r'); do adb -P $ADB_PORT -s "$SER" pull $f $RUN/phone_final/ > /dev/null 2>&1; done
.venv-aw/bin/python scripts/devstream_report.py $RUN --md $RUN/speed_qdc.md --json $RUN/speed_qdc.json > /dev/null 2>&1
git add $RUN; git commit -q -m "QDC speed benchmark (SM8975, Android 17; ABC/CBA, 3 timed passes each): $RUN

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && log "committed $(git log --oneline -1)"
log "QDC CHAIN DONE"
