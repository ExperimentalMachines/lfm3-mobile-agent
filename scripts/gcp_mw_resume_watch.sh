#!/bin/bash
# Mac-side watcher for the GCP MobileWorld run 2 (GUI-Owl on mobile_world_env_0, v4 on lfmenv_0). The VM's external IP is
# reserved (lfm3-mw-ip), so a restart keeps it and the Colab reverse tunnel reconnects by itself.
#  * VM RUNNING: when a run's original task list has ended (go_r2.end / v4_r2.end) and nothing of that run is running,
#    restart that run's container (fresh emulator and services) and start mw_resume.sh for it (re-run rule in that file).
#  * VM stopped (12-h max-run limit or spot preemption) before both runs are complete: start it, start both containers,
#    wait until healthy and until the model tunnels answer, then start mw_resume.sh for each incomplete run.
# Exits when guiowl_complete and v4_complete exist on the VM (or after 16 h). Log: logs/gcp_mw_resume_watch.log
set -u
cd /Users/alpha/lfm3-android
source logs/gcp_mw_instance.env
log() { echo "[$(date +%T)] $*"; }
S() { ssh -o ConnectTimeout=15 -o BatchMode=yes -i "$PEM" "ubuntu@${IP}" "$@"; }
status() { gcloud compute instances describe "$NAME" --zone "$ZONE" --format="value(status)" 2>/dev/null; }
ctr() { [ "$1" = guiowl ] && echo mobile_world_env_0 || echo lfmenv_0; }
endf() { [ "$1" = guiowl ] && echo go_r2.end || echo v4_r2.end; }
logroot() { [ "$1" = guiowl ] && echo guiowl_gui_en_r2 || echo v4_gui_en_r2; }
wait_ready() {  # containers healthy + model tunnels answering, up to 20 min
  local t0=$(date +%s)
  until S "for c in $*; do [ \"\$(sudo docker inspect -f '{{.State.Health.Status}}' \$c)\" = healthy ] || exit 1; done; curl -s -m 5 localhost:18092/health | grep -q ok && curl -s -m 5 localhost:18094/health | grep -q ok" 2>/dev/null; do
    [ $(( $(date +%s) - t0 )) -gt 1200 ] && { log "not ready after 20 min ($*)"; return 1; }
    sleep 20
  done
}
launch() {
  local r=$1
  S "nohup bash mw_resume.sh $r > ${r}_resume_\$(date +%H%M).log 2>&1 < /dev/null &" && log "started mw_resume.sh $r"
}
T0=$(date +%s); RESTARTED=0
log "watcher up (pid $$)"
while [ $(( $(date +%s) - T0 )) -lt 57600 ]; do
  st=$(status)
  if [ "$st" = RUNNING ]; then
    done_all=1
    for r in guiowl v4; do
      if S "test -f ${r}_complete" 2>/dev/null; then continue; fi
      done_all=0
      # bracketed patterns so pgrep cannot match the remote shell that runs it
      busy=$(S "if pgrep -f 'mw [e]val.*$(logroot $r)' >/dev/null || pgrep -f 'mw_resume[.]sh $r' >/dev/null; then echo busy; else echo idle; fi" 2>/dev/null)
      [ "$busy" = idle ] || continue
      if [ "$RESTARTED" = 1 ] || S "test -f $(endf $r)" 2>/dev/null; then
        log "$r: original list ended (or VM restarted) and nothing running -> restart $(ctr $r), then resume"
        S "sudo docker restart $(ctr $r) > /dev/null" && wait_ready "$(ctr $r)" && launch $r
      fi
    done
    [ "$done_all" = 1 ] && { log "both runs complete"; exit 0; }
  elif [ "$st" = TERMINATED ] || [ "$st" = STOPPED ]; then
    log "VM is $st with runs incomplete -> starting it"
    gcloud compute instances start "$NAME" --zone "$ZONE" --quiet > /dev/null 2>&1 || { log "start failed; retrying in 2 min"; sleep 120; continue; }
    t0=$(date +%s); until S true 2>/dev/null; do sleep 10; [ $(( $(date +%s) - t0 )) -gt 900 ] && break; done
    S "sudo docker start mobile_world_env_0 lfmenv_0 > /dev/null" && wait_ready mobile_world_env_0 lfmenv_0 && { RESTARTED=1; log "VM, containers and tunnels ready"; }
    continue
  fi
  sleep 120
done
log "watcher time limit reached"
