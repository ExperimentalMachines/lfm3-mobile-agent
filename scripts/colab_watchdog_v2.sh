#!/bin/bash
# Local watchdog for the overnight Colab v4 (+RL) job (v2, after Codex's recovery audit). Every 120 s:
#  (a) session gone (VM pruned) -> if NO other Colab session exists (a second VM could write the same checkpoint repo),
#      re-provision (G4 > A100 > H100 > L4 last) and relaunch with scripts/v4_relaunch.sh (NO_RL on L4), at most
#      MAX_RELAUNCH times; sft_vlm.py refuses to start from scratch if the hub checkpoint cannot be restored;
#  (b) no local client attached to the kernel -> attach a queued keepalive cell;
#  (c) every job on the VM has exited -> back up /content/eval/* and the run logs locally, wait GRACE_S (FAIL_GRACE_S if a
#      job failed or a download failed; touch logs/.keep_vm_<session> to keep the VM), re-check that the same run is
#      still finished, then stop the VM and verify it is gone.
# Session names are matched exactly ("[name]" in `colab sessions`, "exec -s name --" for clients).
# Usage: nohup bash scripts/colab_watchdog_v2.sh lfm3v4a > logs/colab_watchdog_lfm3v4a.log 2>&1 &
set -u
S=$1; MAX_RELAUNCH=${MAX_RELAUNCH:-3}; GRACE_S=${GRACE_S:-1200}; FAIL_GRACE_S=${FAIL_GRACE_S:-5400}; n=0
cd "$(dirname "$0")/.."
CB=$HOME/.local/bin/colab
C() { "$CB" "$@" < /dev/null 2>&1 | grep -v "new version\|colab update\|silence"; }
log() { echo "[$(date +%T)] $*"; }
TMP=${TMPDIR:-/tmp}/colab_wd2_$S; mkdir -p "$TMP"
BK=results/vm_backup/$S; mkdir -p "$BK/eval"
sessions() { C sessions; }
alive() { sessions | grep -q "^\[$S\] "; }
others() { sessions | grep "^\[" | grep -v "^\[$S\] "; }
status_done() {  # prints run_id and exits 0 iff jobs_status.json exists and no job is running
  rm -f "$TMP/st.json"
  C download -s "$S" /content/work/jobs_status.json "$TMP/st.json" > /dev/null 2>&1 && [ -s "$TMP/st.json" ] && \
    python3 -c "import json,sys; d=json.load(open('$TMP/st.json')); s=d['status']; print(d['run_id'], 'ok' if all(v=='exit 0' for v in s.values()) else 'failed'); sys.exit(0 if s and all(v!='running' for v in s.values()) else 1)"
}
log "watchdog v2 start for $S (pid $$)"
while true; do
  if ! alive; then
    sleep 30; alive && continue   # one transient API failure is not a loss
    if [ -n "$(others)" ]; then log "VM $S gone but other sessions exist; not provisioning (possible second writer): $(others | tr '\n' ' ')"; sleep 300; continue; fi
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
  if R1=$(status_done); then
    log "all jobs exited: $R1 $(cat "$TMP/st.json")"
    bad=0; case "$R1" in *failed) bad=1 ;; esac
    for f in $(C ls -s "$S" content/eval | grep -v "/$"); do
      C download -s "$S" "/content/eval/$f" "$BK/eval/$f" > /dev/null 2>&1 && [ -s "$BK/eval/$f" ] || { log "backup failed: $f"; bad=1; }
    done
    for f in /content/runs/lfm3_v4_pipeline.log /content/runs/rl_hook.log /content/runs/v4rl_train.log /content/runs/rl_smoke.log; do
      C download -s "$S" "$f" "$BK/$(basename "$f")" > /dev/null 2>&1 || log "log download failed: $f"
    done
    g=$GRACE_S; [ $bad = 1 ] && g=$FAIL_GRACE_S
    log "backup in $BK ($(ls "$BK/eval" | wc -l | tr -d ' ') eval files); stopping in ${g}s unless logs/.keep_vm_$S exists"
    sleep "$g"
    [ -f "logs/.keep_vm_$S" ] && { log "keep file present; not stopping"; exit 0; }
    R2=$(status_done) || { log "jobs running again after the grace period; continuing to watch"; continue; }
    [ "${R1%% *}" = "${R2%% *}" ] || { log "a new run ($R2) started during the grace period; continuing to watch"; continue; }
    C stop -s "$S" | tail -1; sleep 10
    if alive; then log "STOP FAILED; retrying"; C stop -s "$S" | tail -1; sleep 10; alive && { log "STOP FAILED twice"; exit 1; }; fi
    log "VM stopped (verified)"; exit 0
  fi
  if ! pgrep -f "[e]xec -s $S --" > /dev/null; then
    log "no client attached; attaching a queued keepalive cell"
    echo "print('keepalive')" | nohup "$CB" exec -s "$S" --timeout 200000 >> "logs/colab_keepalive_$S.log" 2>&1 &
  fi
  sleep 120
done
