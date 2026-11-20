#!/bin/bash
# Emulator 2 fill, part 2 (replaces scripts/local_emu2_fill.sh (archived) after it started the sealed GUI-Owl seed-1234 arm).
# Bug fixed: v1 picked the resume dir with `ls -d <arm>/run_* | tail -1`, which matches the runner's
# run_output.SEALED.log file (sorts after run_2026...), so the resume would have pointed at a log file. Here only
# directories (run_*/) are considered.
#   1. wait for the v4 lane (logs/local_v4_to_aw.log) to log "exported; pausing" (or EXPORT FAILED -> leave the arm)
#   2. pause the arm (allowlisted pause script), remember its run dir
#   3. after "v4 AndroidWorld seed-30 finished" and no run_aw.py on emulator 2, resume the arm from that dir
# Usage: nohup bash scripts/androidworld/local_emu2_fill_v2.sh >> logs/local_emu2_fill.log 2>&1 &
set -u
cd "$(dirname "$0")/../.." || exit 1
CP=5558; GP=8558; PORT=8115; ARM=guiowl; SEED=1234; LANE=logs/local_v4_to_aw.log
ALOG=logs/local_sealed_${ARM}_seed${SEED}.log; OUT=results/androidworld_sealed/${ARM}_seed${SEED}
log() { echo "[$(date +%T)] $*"; }
rundir() { local d; d=$(ls -d "$OUT"/run_*/ 2>/dev/null | tail -1); echo "${d%/}"; }
count() { local d; d=$(rundir); [ -n "$d" ] && ls "$d"/*.pkl.gz 2>/dev/null | wc -l | tr -d ' ' || echo 0; }
log "emu2 fill v2 (pid $$): watching ${ARM}_seed${SEED} ($(count) episodes) and the v4 lane"
until grep -q "exported; pausing\|EXPORT FAILED" "$LANE"; do
  pgrep -f "^bash scripts/(androidworld/)?local_sealed_aw_v2.sh $ARM $SEED " > /dev/null || { log "arm ended before the v4 hand-off: $(tail -1 "$ALOG")"; exit 0; }
  sleep 20
done
grep -q "EXPORT FAILED" "$LANE" && { log "v4 export failed; leaving the arm running"; exit 1; }
log "v4 lane ready: pausing ${ARM}_seed${SEED}"
bash scripts/androidworld/pause_sealed_arm.sh $ARM $SEED $PORT --dry-run
bash scripts/androidworld/pause_sealed_arm.sh $ARM $SEED $PORT
RESUME=$(rundir)
[ -d "$RESUME" ] || { log "no run dir to resume in $OUT; not resuming"; exit 1; }
log "paused at $(count) episodes (run dir $RESUME); waiting for the v4 seed-30 pass"
until grep -q "v4 AndroidWorld seed-30 finished" "$LANE"; do sleep 60; done
until ! pgrep -f "[r]un_aw.py.*console_port=$CP" > /dev/null; do sleep 10; done
log "resuming ${ARM}_seed${SEED} from $RESUME"
bash scripts/androidworld/local_sealed_aw_v2.sh $ARM $SEED $CP $GP $PORT "$RESUME" >> "$ALOG" 2>&1 < /dev/null
log "arm ended: $(tail -1 "$ALOG")"
