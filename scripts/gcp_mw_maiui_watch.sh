#!/bin/bash
# Mac-side driver for the MAI-UI-2B MobileWorld run (docs/PREREG_v4.md, 2026-11-19 05:20 entry). Starts only after the
# GUI-Owl and v4 runs are complete (guiowl_complete, v4_complete on the VM) so neither container is shared. A half is
# launched only after its container is healthy AND check_maiui_server.py confirms its tunnel serves MAI-UI Q8_0. MAI-UI's 105 tasks are split
# alternately into two halves run in parallel: maiui_a on mobile_world_env_0 (model server tunnel 18093) and maiui_b on
# lfmenv_0 (identical server, tunnel 18094); both write traj_logs/maiui_gui_en_r2. Each half is launched and completed by
# mw_resume2.sh (= scripts/gcp_mw_resume_vm.sh: same completion rule as GUI-Owl and v4).
#  * VM RUNNING: for each half that is neither complete nor running, restart its container (fresh emulator and services),
#    wait until healthy and its model server answers, then start mw_resume2.sh for it.
#  * VM stopped (12-h max-run limit / preemption): start it, start both containers, then as above.
#  * gcloud unusable (expired login): wait and log every 30 min; nothing is started.
#  * model-server guard (2026-11-19 10:20): a half is (re)launched only while its tunnel serves MAI-UI Q8_0; a running
#    half whose server fails two checks 20 s apart has its mw eval stopped (no completion marker is written while any
#    task still needs an attempt); its unfinished tasks are re-run once the server is back.
# Exits when maiui_a_complete and maiui_b_complete exist (or after 20 h). Log: logs/gcp_mw_maiui_watch.log
set -u
cd /Users/alpha/lfm3-android
source logs/gcp_mw_instance.env
log() { echo "[$(date +%T)] $*"; }
S() { ssh -o ConnectTimeout=15 -o BatchMode=yes -i "$PEM" "ubuntu@${IP}" "$@"; }
status() { gcloud compute instances describe "$NAME" --zone "$ZONE" --format="value(status)" 2>/dev/null; }
ctr() { [ "$1" = maiui_a ] && echo mobile_world_env_0 || echo lfmenv_0; }
port() { [ "$1" = maiui_a ] && echo 18093 || echo 18094; }
ep() { [ "$1" = maiui_a ] && echo mobile_world_env || echo lfmenv; }
wait_ready() {  # $1 = half; container healthy + its model tunnel answering, up to 20 min
  local t0=$(date +%s) c; c=$(ctr "$1")
  # container healthy AND the tunnel's server is MAI-UI-2B Q8_0 / cd959bae9 / n_ctx 20480 (not just any /health "ok")
  until S "[ \"\$(sudo docker inspect -f '{{.State.Health.Status}}' $c)\" = healthy ] && python3 check_maiui_server.py $(port "$1")" > /dev/null 2>&1; do
    [ $(( $(date +%s) - t0 )) -gt 1200 ] && { log "$1: not ready after 20 min"; return 1; }
    sleep 20
  done
}
restart_ctr() {  # $1 = container. A plain `docker restart` can SIGKILL the emulator and leave the AVD's
  # multiinstance.lock / hardware-qemu.ini.lock, after which the emulator refuses to start ("Running multiple emulators
  # with the same AVD", seen 2026-11-19 10:20). So: stop the emulator gracefully, remove leftover locks, then restart.
  S "sudo docker exec $1 sh -c 'adb devices | grep emulator | cut -f1 | xargs -r -I{} adb -s {} emu kill' > /dev/null 2>&1;
     for i in \$(seq 1 30); do sudo docker exec $1 sh -c 'pgrep -f [q]emu-system' > /dev/null || break; sleep 2; done;
     sudo docker exec $1 sh -c 'rm -f /root/.android/avd/*.avd/*.lock' && sudo docker restart $1 > /dev/null"
}
deploy() {  # idempotent: agent wrapper, resume script, server check, the two task halves (validated: 53 + 52, disjoint, = manifest)
  scp -q -o BatchMode=yes -i "$PEM" eval/mobileworld/maiui_mw_agent.py "ubuntu@${IP}:lfm3/maiui_mw_agent.py" &&
  scp -q -o BatchMode=yes -i "$PEM" scripts/gcp_mw_resume_vm.sh "ubuntu@${IP}:mw_resume2.sh" &&
  scp -q -o BatchMode=yes -i "$PEM" scripts/check_maiui_server.py "ubuntu@${IP}:check_maiui_server.py" &&
  S "python3 -c \"import json; t=json.load(open('mw_gui_en.json')); assert len(t)==105==len(set(t)); a,b=t[0::2],t[1::2]; json.dump(a, open('mw_gui_en_maiui_a.json','w')); json.dump(b, open('mw_gui_en_maiui_b.json','w')); A=json.load(open('mw_gui_en_maiui_a.json')); B=json.load(open('mw_gui_en_maiui_b.json')); assert (len(A),len(B))==(53,52) and not set(A)&set(B) and set(A)|set(B)==set(t); print('halves ok', len(A), len(B))\""
}
T0=$(date +%s); last_auth_log=0; deployed=0
log "MAI-UI watcher up (pid $$)"
while [ $(( $(date +%s) - T0 )) -lt 72000 ]; do
  st=$(status)
  if [ -z "$st" ]; then
    [ $(( $(date +%s) - last_auth_log )) -ge 1800 ] && { log "gcloud status unavailable (login expired?); waiting"; last_auth_log=$(date +%s); }
  elif [ "$st" = RUNNING ]; then
    # both earlier runs must be complete before their containers are reused
    if ! S "test -f guiowl_complete && test -f v4_complete" 2>/dev/null; then sleep 120; continue; fi
    if [ "$deployed" != 1 ]; then
      if deploy; then deployed=1; log "deployed agent, mw_resume2.sh, server check and validated task halves"
      else log "deploy/validation FAILED; nothing launched; retrying in 2 min"; sleep 120; continue; fi
    fi
    done_all=1
    for r in maiui_a maiui_b; do
      if S "test -f ${r}_complete" 2>/dev/null; then continue; fi
      done_all=0
      busy=$(S "if pgrep -f 'mw [e]val.*--env_prefix $(ep $r) --log_file_root /home/ubuntu/traj_logs/maiui_gui_en_r2' >/dev/null || pgrep -f 'mw_resume2[.]sh $r' >/dev/null; then echo busy; else echo idle; fi" 2>/dev/null)
      if [ "$busy" = busy ]; then
        # model-server guard: if the half's server (Colab tunnel) fails two checks 20 s apart, stop its mw eval so the
        # task list is not run against a dead server; tasks it ended are re-run later (planner: model_server_unreachable)
        if ! S "python3 check_maiui_server.py $(port $r)" > /dev/null 2>&1; then
          sleep 20
          if ! S "python3 check_maiui_server.py $(port $r)" > /dev/null 2>&1; then
            log "$r: model server on $(port $r) failed two checks -> stopping its mw eval (tasks it ended will be re-run)"
            S "sudo pkill -f 'mw [e]val.*--env_prefix $(ep $r) --log_file_root /home/ubuntu/traj_logs/maiui_gui_en_r2'"
          fi
        fi
        continue
      fi
      [ "$busy" = idle ] || continue
      # do not restart a container or launch while the half's model server is down (e.g. Colab session ended)
      if ! S "python3 check_maiui_server.py $(port $r)" > /dev/null 2>&1; then
        [ $(( $(date +%s) - ${last_srv_log:-0} )) -ge 1800 ] && { log "$r: model server on $(port $r) not serving MAI-UI Q8_0; waiting"; last_srv_log=$(date +%s); }
        continue
      fi
      log "$r: not complete and nothing running -> restart $(ctr $r), then mw_resume2.sh $r"
      restart_ctr $(ctr $r) && wait_ready $r &&
        S "nohup bash mw_resume2.sh $r > ${r}_resume_\$(date +%H%M).log 2>&1 < /dev/null &" && log "started mw_resume2.sh $r"
    done
    [ "$deployed" = 1 ] && [ "$done_all" = 1 ] && { log "both MAI-UI halves complete"; exit 0; }
  elif [ "$st" = TERMINATED ] || [ "$st" = STOPPED ]; then
    # the GUI-Owl watcher (gcp_mw_resume_watch.sh) restarts the VM while GUI-Owl is incomplete; after that, this one does
    if pgrep -f "[g]cp_mw_resume_watch.sh" > /dev/null; then sleep 120; continue; fi
    log "VM is $st -> starting it"
    gcloud compute instances start "$NAME" --zone "$ZONE" --quiet > /dev/null 2>&1 || { log "start failed; retrying in 2 min"; sleep 120; continue; }
    t0=$(date +%s); until S true 2>/dev/null; do sleep 10; [ $(( $(date +%s) - t0 )) -gt 900 ] && break; done
    S "sudo docker start mobile_world_env_0 lfmenv_0 > /dev/null" && log "VM and containers started"
    continue
  fi
  sleep 120
done
log "MAI-UI watcher time limit reached"
