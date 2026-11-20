#!/bin/bash
# Queue the remaining SEALED AndroidWorld arms on one emulator (docs/PREREG_v4.md arms: v4 = LFM3 final, guiowl = GUI-Owl
# matched, v1 = reference). Waits for <wait_pid> (the job currently using this emulator) to exit, then runs each
# <arm>:<seed>:<server_port> in order with scripts/androidworld/local_sealed_aw_v3.sh (outcome-filtered; results only in the sealed dir).
# This log holds only start/end lines and episode-file counts. Usage:
#   nohup bash scripts/androidworld/local_sealed_queue.sh <wait_pid> <console_port> <grpc_port> <arm:seed:port> ... > logs/x.log 2>&1 &
set -u
cd "$(dirname "$0")/../.." || exit 1
W=$1; CP=$2; GP=$3; shift 3
log() { echo "[$(date +%T)] $*"; }
count() { local d; d=$(ls -d "$1"/run_*/ 2>/dev/null | tail -1); [ -n "$d" ] && ls "$d"*.pkl.gz 2>/dev/null | wc -l | tr -d ' ' || echo 0; }
log "queue on emulator $CP: $* (waiting for PID $W)"
while kill -0 "$W" 2>/dev/null; do sleep 30; done
for item in "$@"; do
  IFS=: read -r ARM SEED PORT <<< "$item"
  N=$(count results/androidworld_sealed/${ARM}_seed${SEED})
  if [ "$N" -ge 116 ]; then log "${ARM}_seed${SEED} already has $N episodes; skipping"; continue; fi
  log "start ${ARM}_seed${SEED} (server :$PORT)"
  bash scripts/androidworld/local_sealed_aw_v3.sh "$ARM" "$SEED" "$CP" "$GP" "$PORT" >> logs/local_sealed_${ARM}_seed${SEED}.log 2>&1 < /dev/null
  log "${ARM}_seed${SEED} ended: $(tail -1 logs/local_sealed_${ARM}_seed${SEED}.log | cut -c1-120) ($(count results/androidworld_sealed/${ARM}_seed${SEED}) episodes)"
done
log "QUEUE DONE"
