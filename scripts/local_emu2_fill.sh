#!/bin/bash
# Keep emulator 2 busy between the end of the sealed v1 seed-7 arm and the v4 hand-off (scripts/local_v4_to_aw.sh):
#   1. wait for v1 seed 7 to end; require 116 episode files (the old runner prints "finished" whatever happened)
#   2. start the pre-registered GUI-Owl seed-1234 sealed arm on emulator 2 (server :8115), unless the v4 lane already
#      claimed the emulator
#   3. when the v4 lane logs "exported; pausing", pause that arm (allowlisted pause script; the lane waits for no
#      run_aw.py on emulator 2 before starting), and resume it from its checkpoint after the lane's seed-30 pass ends.
# Usage: nohup bash scripts/local_emu2_fill.sh > logs/local_emu2_fill.log 2>&1 &
set -u
cd /Users/alpha/lfm3-android
CP=5558; GP=8558; PORT=8115; ARM=guiowl; SEED=1234; LANE=logs/local_v4_to_aw.log
ALOG=logs/local_sealed_${ARM}_seed${SEED}.log
log() { echo "[$(date +%T)] $*"; }
count() { local d; d=$(ls -d "$1"/run_* 2>/dev/null | tail -1); [ -n "$d" ] && ls "$d"/*.pkl.gz 2>/dev/null | wc -l | tr -d ' ' || echo 0; }
log "waiting for the sealed v1 seed-7 arm to end"
until grep -q "SEALED v1_seed7 AndroidWorld finished" logs/local_sealed_v1_seed7.log 2>/dev/null; do sleep 60; done
N=$(count results/androidworld_sealed/v1_seed7)
[ "$N" = 116 ] || { log "v1 seed 7 ended with $N/116 episodes: needs the preregistered infrastructure retry; not starting anything"; exit 1; }
log "v1 seed 7 complete (116 episodes)"
until ! pgrep -f "[r]un_aw.py.*console_port=$CP" > /dev/null; do sleep 10; done
grep -q "exported; pausing" "$LANE" && { log "v4 lane already owns emulator 2; exiting"; exit 0; }
log "starting SEALED ${ARM}_seed${SEED} on emulator $CP"
nohup bash scripts/local_sealed_aw_v2.sh $ARM $SEED $CP $GP $PORT >> "$ALOG" 2>&1 < /dev/null &
until grep -q "exported; pausing\|EXPORT FAILED" "$LANE"; do
  pgrep -f "^bash scripts/local_sealed_aw_v2.sh $ARM $SEED " > /dev/null || { log "arm ended before the v4 hand-off: $(tail -1 "$ALOG")"; exit 0; }
  sleep 20
done
grep -q "EXPORT FAILED" "$LANE" && { log "v4 export failed; leaving the arm running"; exit 1; }
log "v4 lane ready: pausing ${ARM}_seed${SEED}"
bash scripts/pause_sealed_arm.sh $ARM $SEED $PORT --dry-run
bash scripts/pause_sealed_arm.sh $ARM $SEED $PORT
RESUME=$(ls -d results/androidworld_sealed/${ARM}_seed${SEED}/run_* | tail -1)
log "paused at $(count results/androidworld_sealed/${ARM}_seed${SEED}) episodes; waiting for the v4 seed-30 pass"
until grep -q "v4 AndroidWorld seed-30 finished" "$LANE"; do sleep 60; done
until ! pgrep -f "[r]un_aw.py.*console_port=$CP" > /dev/null; do sleep 10; done
log "resuming ${ARM}_seed${SEED} from $RESUME"
bash scripts/local_sealed_aw_v2.sh $ARM $SEED $CP $GP $PORT "$RESUME" >> "$ALOG" 2>&1 < /dev/null
log "arm ended: $(tail -1 "$ALOG")"
