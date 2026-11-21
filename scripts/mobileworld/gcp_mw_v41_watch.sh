#!/bin/bash
# Mac-side watcher for the v4.1 follow-up MobileWorld run (docs/PREREG_v41.md): one run RUN (v4g|v41|v41g) on container
# lfmenv_0 with the model behind tunnel port 18094. Same logic as run 2's watcher (gcp_mw_resume_watch.sh):
#  * first pass: start mw_resume.sh RUN (every task is "never started", so it runs one mw eval over the 105-task list);
#  * whenever nothing of RUN is running and RUN is not complete: restart lfmenv_0 (fresh emulator), then mw_resume.sh
#    again (its fixed rule decides what is re-run);
#  * VM stopped (max-run limit or spot preemption): start it, start lfmenv_0, wait until healthy and the tunnel answers.
# Exits when RUN_complete exists on the VM (or after 20 h).
# Usage: nohup bash scripts/mobileworld/gcp_mw_v41_watch.sh v41 >> logs/gcp_mw_v41_watch.log 2>&1 &
set -u
cd "$(dirname "$0")/../.." || exit 1
RUN=${1:?usage: $0 v4g|v41|v41g}
source logs/gcp_mw_instance.env
log() { echo "[$(date +%T)] $RUN: $*"; }
S() { ssh -o ConnectTimeout=15 -o BatchMode=yes -i "$PEM" "ubuntu@${IP}" "$@"; }
status() { gcloud compute instances describe "$NAME" --zone "$ZONE" --format="value(status)" 2>/dev/null; }
wait_ready() {
  local t0=$(date +%s)
  until S "[ \"\$(sudo docker inspect -f '{{.State.Health.Status}}' lfmenv_0)\" = healthy ] && curl -s -m 5 localhost:18094/health | grep -q ok" 2>/dev/null; do
    [ $(( $(date +%s) - t0 )) -gt 1200 ] && { log "not ready after 20 min"; return 1; }
    sleep 20
  done
}
launch() { S "nohup bash mw_resume.sh $RUN > ${RUN}_resume_\$(date +%H%M).log 2>&1 < /dev/null &" && log "started mw_resume.sh"; }
T0=$(date +%s)
log "watcher up (pid $$)"
while [ $(( $(date +%s) - T0 )) -lt 72000 ]; do
  st=$(status)
  if [ "$st" = RUNNING ]; then
    S "test -f ${RUN}_complete" 2>/dev/null && { log "complete"; exit 0; }
    busy=$(S "if pgrep -f 'mw [e]val.*${RUN}_gui_en_r3' >/dev/null || pgrep -f 'mw_resume[.]sh $RUN' >/dev/null; then echo busy; else echo idle; fi" 2>/dev/null)
    if [ "$busy" = idle ]; then
      if S "test -f ${RUN}_resume.start" 2>/dev/null; then
        log "nothing running and not complete -> restart lfmenv_0, then resume"
        S "sudo docker restart lfmenv_0 > /dev/null" && wait_ready && launch
      else
        log "first pass"; wait_ready && launch
      fi
    fi
  elif [ "$st" = TERMINATED ] || [ "$st" = STOPPED ]; then
    log "VM is $st and the run is incomplete -> starting it"
    gcloud compute instances start "$NAME" --zone "$ZONE" --quiet > /dev/null 2>&1 || { log "start failed; retry in 2 min"; sleep 120; continue; }
    t0=$(date +%s); until S true 2>/dev/null; do sleep 10; [ $(( $(date +%s) - t0 )) -gt 900 ] && break; done
    S "sudo docker start lfmenv_0 > /dev/null" && wait_ready && log "VM, container and tunnel ready"
    continue
  fi
  sleep 120
done
log "watcher time limit reached"
