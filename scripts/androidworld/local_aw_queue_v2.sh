#!/bin/bash
# Queue AndroidWorld jobs on one emulator after <wait_pid> exits. Items (fields separated by "|"):
#   arm|<arm>|<seed>|<server_port>                         -> full SEALED arm via scripts/androidworld/local_sealed_aw_v3.sh (skipped if 116 done)
#   rerun|<arm>|<seed>|<server_port>|<out_dir>|<tasks>|[label] -> preregistered single re-run via scripts/androidworld/local_aw_rerun.sh
# This log holds only start/end lines and episode-file counts (no outcomes).
# Usage: nohup bash scripts/androidworld/local_aw_queue_v2.sh <wait_pid> <console_port> <grpc_port> '<item>' ... > logs/x.log 2>&1 &
set -u
cd "$(dirname "$0")/../.." || exit 1
W=$1; CP=$2; GP=$3; shift 3
log() { echo "[$(date +%T)] $*"; }
count() { local d; d=$(ls -d "$1"/run_*/ 2>/dev/null | tail -1); [ -n "$d" ] && ls "$d"*.pkl.gz 2>/dev/null | wc -l | tr -d ' ' || echo 0; }
log "queue on emulator $CP ($# items), waiting for PID $W"
while kill -0 "$W" 2>/dev/null; do sleep 30; done
for item in "$@"; do
  IFS='|' read -r KIND ARM SEED PORT ODIR TASKS LABEL <<< "$item"
  if [ "$KIND" = arm ]; then
    D=results/androidworld_sealed/${ARM}_seed${SEED}
    [ "$(count $D)" -ge 116 ] && { log "${ARM}_seed${SEED} already complete; skipping"; continue; }
    log "start sealed ${ARM}_seed${SEED} (server :$PORT)"
    bash scripts/androidworld/local_sealed_aw_v3.sh "$ARM" "$SEED" "$CP" "$GP" "$PORT" >> logs/local_sealed_${ARM}_seed${SEED}.log 2>&1 < /dev/null
    log "${ARM}_seed${SEED} ended: $(tail -1 logs/local_sealed_${ARM}_seed${SEED}.log | cut -c1-100) ($(count $D) episodes)"
  else
    log "start re-run ${ARM} seed ${SEED}: $TASKS -> $ODIR"
    bash scripts/androidworld/local_aw_rerun.sh "$ARM" "$SEED" "$CP" "$GP" "$PORT" "$ODIR" "$TASKS" "$LABEL" >> logs/local_aw_rerun_${ARM}_seed${SEED}.log 2>&1 < /dev/null
    log "re-run ${ARM} seed ${SEED} ended: $(tail -1 logs/local_aw_rerun_${ARM}_seed${SEED}.log | cut -c1-100)"
  fi
done
log "QUEUE DONE"
