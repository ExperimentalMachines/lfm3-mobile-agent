#!/bin/bash
# Emulator guard for the preregistered single re-runs (docs/PREREG_v4.md 2026-11-19 13:40). An emulator whose guest
# stops answering `adb shell` makes every following AndroidWorld episode crash in setup after adb's 120-s timeouts
# (emulator 2, 2026-11-19 00:35-08:06: 113 setup crashes in v4 seed 1234). Because a re-run is allowed only once, this
# guard probes the emulator every 20 s (15-s bound per probe, read-only `adb shell echo`; the shared adb server is never
# restarted) and, after two consecutive failed probes, kills that emulator's run_aw.py BEFORE a crashed episode can be
# recorded. The interrupted episode leaves no episode file; the remaining tasks are resumed in the same run directory
# after the emulator is restarted (disclosed). Exits when <watch_pid> (the queue/wrapper) is gone.
# Usage: nohup bash scripts/androidworld/aw_emu_guard.sh <console_port> <watch_pid> >> logs/aw_emu_guard_<port>.log 2>&1 &
set -u
CP=$1; W=$2; fails=0
log() { echo "[$(date +%T)] $*"; }
log "guard up for emulator-$CP (watching pid $W)"
while kill -0 "$W" 2>/dev/null; do
  if [ "$(perl -e 'alarm 15; exec @ARGV' adb -P 5037 -s emulator-$CP shell echo ok 2>/dev/null | tr -d '\r')" = ok ]; then
    fails=0
  else
    fails=$((fails + 1)); log "emulator-$CP probe failed ($fails)"
    if [ $fails -ge 2 ]; then
      log "emulator-$CP unresponsive: killing run_aw.py --console_port=$CP"
      pkill -f "[r]un_aw.py --console_port=$CP " ; exit 0
    fi
  fi
  sleep 20
done
log "watched pid $W gone; guard exiting"
