#!/bin/bash
# Local watchdog for the overnight Colab v4 (+RL) job. Every 120 s:
#  (a) session gone (VM pruned) -> re-provision (G4 > A100 > H100 > L4 last) and relaunch with scripts/v4_relaunch.sh
#      (SFT resumes from the hub checkpoint), at most MAX_RELAUNCH times;
#  (b) no local client attached to the kernel -> attach a queued keepalive cell (2026-11-18: the VM was pruned ~20 min
#      after the jobs cell's websocket dropped, while training was still running);
#  (c) every job on the VM has exited -> download the run logs, wait GRACE_S (touch logs/.keep_vm_<session> to keep the
#      VM), then stop it (an idle VM still burns compute units).
# Usage: nohup bash scripts/colab_watchdog.sh lfm3v4 > logs/colab_watchdog_lfm3v4.log 2>&1 &
set -u
S=$1; MAX_RELAUNCH=${MAX_RELAUNCH:-3}; GRACE_S=${GRACE_S:-1200}; n=0
cd "$(dirname "$0")/.."
CB=/Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/relaunch_failed/bin/colab
C() { "$CB" "$@" < /dev/null 2>&1 | grep -v "new version\|colab update\|silence"; }
log() { echo "[$(date +%T)] $*"; }
TMP=/Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/relaunch_failed/tmp/colab_wd_$S; mkdir -p "$TMP"
alive() { C sessions | grep -q "$S"; }
log "watchdog start for $S (pid $$)"
for AUDIT_TICK in 1 2 3; do
  if ! alive; then
    sleep 30; alive && continue   # one transient API failure is not a loss
    [ $n -ge "$MAX_RELAUNCH" ] && { log "VM LOST; relaunch limit ($MAX_RELAUNCH) reached"; exit 1; }
    n=$((n+1)); log "VM LOST; re-provision + relaunch #$n"
    if bash scripts/colab_get_gpu.sh "$S" 6 >> "logs/colab_get_gpu_${S}_wd.log" 2>&1; then
      tail -1 "logs/colab_get_gpu_${S}_wd.log"
      nr=${NO_RL:-0}; tail -1 "logs/colab_get_gpu_${S}_wd.log" | grep -q "GOT L4" && nr=1   # no GRPO smoke next to SFT on 24 GB
      NO_RL=$nr bash scripts/v4_relaunch.sh "$S" 2>&1 | tail -5
    else
      log "no GPU this round"; sleep 300
    fi
    continue
  fi
  rm -f "$TMP/st.json"
  if C download -s "$S" /content/work/jobs_status.json "$TMP/st.json" > /dev/null 2>&1 && [ -s "$TMP/st.json" ] && \
     python3 -c "import json,sys; s=json.load(open('$TMP/st.json'))['status']; sys.exit(0 if s and all(v!='running' for v in s.values()) else 1)"; then
    log "all jobs exited: $(cat "$TMP/st.json")"
    for f in /content/runs/lfm3_v4_pipeline.log /content/runs/rl_hook.log /content/runs/v4rl_train.log /content/runs/rl_smoke.log; do
      C download -s "$S" "$f" "logs/vm_${S}_$(basename "$f")" > /dev/null
    done
    log "logs saved; stopping the VM in ${GRACE_S}s unless logs/.keep_vm_$S exists"
    sleep "$GRACE_S"
    if [ -f "logs/.keep_vm_$S" ]; then log "keep file present; not stopping"; exit 0; fi
    C stop -s "$S" | tail -1; log "VM stopped"; exit 0
  fi
  if ! pgrep -f "[e]xec -s $S" > /dev/null; then
    log "no client attached; attaching a queued keepalive cell"
    echo "print('keepalive')" | nohup "$CB" exec -s "$S" --timeout 200000 >> "logs/colab_keepalive_$S.log" 2>&1 &
  fi
  sleep 120
done

wait
