#!/bin/bash
# v4 of the filler: identical to local_emu2_fill_v3.sh except that arms run through scripts/androidworld/local_sealed_aw_v3.sh (bounded,
# PID-bound server start that fails instead of hanging, so GUI-Owl seed 1234 is always resumed; Codex P2-1).
# Emulator 2, after the v4 seed-30 development pass (replaces scripts/androidworld/local_emu2_fill_v2.sh while it waits; the sealed
# GUI-Owl seed-1234 arm is already paused with 33 saved episodes):
#   1. wait for "v4 AndroidWorld seed-30 finished" in logs/local_v4_to_aw.log and for emulator 2 to be free;
#   2. apply the preregistered development gate mechanically (analysis/v4_gate.py; docs/PREREG_v4.md):
#        PASS -> "LFM3 final" = v4: run the SEALED v4 seed-7 arm (prereg: the final model runs seed 7 once frozen);
#        FAIL -> "LFM3 final" = v3 and v1: run the SEALED v3 seed-7 arm (v1 seed 7 already has 116 episodes);
#        gate input error / incomplete seed-30 run -> run no final arm (needs a human decision);
#      v4-RL failed its offline promotion rule (results/v4rl_promotion_offline.json), so it is not a candidate;
#   3. resume the sealed GUI-Owl seed-1234 arm from its run directory.
# Outcomes of sealed arms are never printed here (the sealed runner keeps its output inside the sealed dir).
# Usage: nohup bash scripts/androidworld/local_emu2_fill_v4.sh >> logs/local_emu2_fill.log 2>&1 &
set -u
cd "$(dirname "$0")/../.." || exit 1
CP=5558; GP=8558; LANE=logs/local_v4_to_aw.log
GO=results/androidworld_sealed/guiowl_seed1234; GOLOG=logs/local_sealed_guiowl_seed1234.log
log() { echo "[$(date +%T)] $*"; }
rundir() { local d; d=$(ls -d "$1"/run_*/ 2>/dev/null | tail -1); echo "${d%/}"; }
count() { local d; d=$(rundir "$1"); [ -n "$d" ] && ls "$d"/*.pkl.gz 2>/dev/null | wc -l | tr -d ' ' || echo 0; }
busy() { pgrep -f "[r]un_aw.py.*console_port=$CP" >/dev/null || pgrep -f "^bash scripts/(androidworld/)?local_sealed_aw(_v[23])?.sh [a-z0-9]+ [0-9]+ $CP " >/dev/null; }
RESUME=$(rundir $GO)
[ -d "$RESUME" ] || { log "no GUI-Owl seed-1234 run dir; exiting"; exit 1; }
log "emu2 fill v3 (pid $$): GUI-Owl seed 1234 paused at $(count $GO) episodes ($RESUME); waiting for the v4 seed-30 pass"
until grep -q "v4 AndroidWorld seed-30 finished" "$LANE"; do sleep 60; done
while busy; do sleep 10; done
ARM=""
if grep -q "v4 seed-30 run complete: 116 episodes" "$LANE"; then
  .venv-aw/bin/python analysis/v4_gate.py --v4 results/androidworld/lfm3vl2b_v4 --v4_agent lfm3vl2b_v4_q4km \
    --dev_answer results/v4_dev/hub/eval/lfm3_v4_dev_answer.jsonl --dev_complete results/v4_dev/hub/eval/lfm3_v4_dev_complete.jsonl \
    > results/v4_gate_seed30.txt 2>&1
  RC=$?
  log "v4 gate exit $RC: $(grep -h "\"PASS\"\|GATE INPUT ERROR" results/v4_gate_seed30.txt | tr -d "\n")"
  case $RC in 0) ARM=v4; PORT=8117 ;; 3) ARM=v3; PORT=8118 ;; *) log "gate input error; no final arm started (human decision needed)" ;; esac
else
  log "v4 seed-30 run not complete ($(grep "seed-30 run" "$LANE" | tail -1)); no final arm started (human decision needed)"
fi
if [ -n "$ARM" ]; then
  if [ "$(count results/androidworld_sealed/${ARM}_seed7)" != 0 ]; then
    log "results/androidworld_sealed/${ARM}_seed7 already has episodes; not starting it again"
  else
    log "LFM3 final per the gate = $ARM; starting the SEALED ${ARM}_seed7 arm on emulator $CP"
    bash scripts/androidworld/local_sealed_aw_v3.sh $ARM 7 $CP $GP $PORT >> logs/local_sealed_${ARM}_seed7.log 2>&1 < /dev/null
    log "${ARM}_seed7 ended: $(tail -1 logs/local_sealed_${ARM}_seed7.log) ($(count results/androidworld_sealed/${ARM}_seed7) episodes)"
  fi
fi
while busy; do sleep 10; done
log "resuming guiowl_seed1234 from $RESUME"
bash scripts/androidworld/local_sealed_aw_v3.sh guiowl 1234 $CP $GP 8115 "$RESUME" >> "$GOLOG" 2>&1 < /dev/null
log "guiowl_seed1234 ended: $(tail -1 "$GOLOG") ($(count $GO) episodes)"
