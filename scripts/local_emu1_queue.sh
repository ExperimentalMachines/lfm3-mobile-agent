#!/bin/bash
# Emulator 1 queue: after the sealed GUI-Owl seed-7 arm ends (116 episode files verified; the old runner prints
# "finished" whatever happened), run the preregistered sealed LFM3 v1 seed-1234 arm on emulator 1 (server :8116).
# Usage: nohup bash scripts/local_emu1_queue.sh > logs/local_emu1_queue.log 2>&1 &
set -u
cd /Users/alpha/lfm3-android
CP=5556; GP=8556; PORT=8116
log() { echo "[$(date +%T)] $*"; }
count() { local d; d=$(ls -d "$1"/run_* 2>/dev/null | tail -1); [ -n "$d" ] && ls "$d"/*.pkl.gz 2>/dev/null | wc -l | tr -d ' ' || echo 0; }
log "waiting for the sealed GUI-Owl seed-7 arm to end"
until grep -q "SEALED guiowl_seed7 AndroidWorld finished" logs/local_sealed_guiowl_seed7.log 2>/dev/null; do sleep 60; done
N=$(count results/androidworld_sealed/guiowl_seed7)
[ "$N" = 116 ] || { log "GUI-Owl seed 7 ended with $N/116 episodes: needs the preregistered infrastructure retry; not starting anything"; exit 1; }
until ! pgrep -f "[r]un_aw.py.*console_port=$CP" > /dev/null; do sleep 10; done
log "GUI-Owl seed 7 complete (116); starting SEALED v1_seed1234 on emulator $CP"
bash scripts/local_sealed_aw_v2.sh v1 1234 $CP $GP $PORT >> logs/local_sealed_v1_seed1234.log 2>&1 < /dev/null
log "arm ended: $(tail -1 logs/local_sealed_v1_seed1234.log)"
