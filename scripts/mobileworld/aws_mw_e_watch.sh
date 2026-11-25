#!/bin/bash
# Mac-side watcher for E's MobileWorld run (docs/PREREG_v46.md 2026-11-25 20:40), the logic of run 3's watcher
# (gcp_mw_v41_watch.sh) on AWS: run `e` on container lfmenv_0, model behind tunnel port 18094.
#  * first pass: start mw_resume.sh e (every task "never started": one mw eval over the 105-task list);
#  * whenever nothing of the run is running and it is not complete: restart lfmenv_0 (fresh emulator), then mw_resume.sh
#    again (its fixed rule decides what is re-run);
#  * VM stopped (its power-off limit): start it, start lfmenv_0, wait until healthy and the tunnel answers.
# Exits when e_complete exists on the VM (or after 20 h).
# Usage: nohup bash scripts/mobileworld/aws_mw_e_watch.sh >> logs/aws_mw_e_watch.log 2>&1 &
set -u
cd "$(dirname "$0")/../.." || exit 1
RUN=e
source logs/aws_mw_e.env
export AWS_PAGER=""
log() { echo "[$(date +%T)] $RUN: $*"; }
S() { ssh -o ConnectTimeout=15 -o BatchMode=yes -i "$PEM" "ubuntu@${IP}" "$@"; }
status() { aws ec2 describe-instances --region "$REGION" --instance-ids "$IID" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null; }
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
  if [ "$st" = running ]; then
    S "test -f ${RUN}_complete" 2>/dev/null && { log "complete"; exit 0; }
    busy=$(S "if pgrep -f 'mw [e]val.*${RUN}_gui_en_r4' >/dev/null || pgrep -f 'mw_resume[.]sh $RUN' >/dev/null; then echo busy; else echo idle; fi" 2>/dev/null)
    if [ "$busy" = idle ]; then
      if S "test -f ${RUN}_resume.start" 2>/dev/null; then
        log "nothing running and not complete -> restart lfmenv_0, then resume"
        S "sudo docker restart lfmenv_0 > /dev/null" && wait_ready && launch
      else
        log "first pass"; wait_ready && launch
      fi
    fi
  elif [ "$st" = stopped ]; then
    log "VM is stopped and the run is incomplete -> starting it"
    aws ec2 start-instances --region "$REGION" --instance-ids "$IID" > /dev/null 2>&1 || { log "start failed; retry in 2 min"; sleep 120; continue; }
    aws ec2 wait instance-running --region "$REGION" --instance-ids "$IID"
    IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$IID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
    sed -i '' "s/^IP=.*/IP=$IP/" logs/aws_mw_e.env
    t0=$(date +%s); until S true 2>/dev/null; do sleep 10; [ $(( $(date +%s) - t0 )) -gt 900 ] && break; done
    log "new IP $IP: restart the Mac tunnel (scripts/mobileworld/mac_mw_e_server.sh) if it does not reconnect"
    S "sudo docker start lfmenv_0 > /dev/null" && wait_ready && log "VM, container and tunnel ready"
    continue
  fi
  sleep 120
done
log "watcher time limit reached"
