#!/bin/bash
# Exit (and print why) when: the v3 chain finishes, the v3 Modal app leaves the running state, or (optional) the
# AndroidWorld run logging to $AW_LOG finishes.
# `modal app list` columns: app-id, description, STATE (field 3: ephemera[l]/deployed/stopped), tasks, created, stopped.
cd /Users/alpha/lfm3-android
APP=$1
check() {
  if grep -q "chain done" logs/v3_modal_chain.log 2>/dev/null; then echo "V3 CHAIN DONE"; return 0; fi
  st=$(uvx --from modal modal app list 2>/dev/null | awk -v a="$APP" '$1 == a {print $3}')
  case "$st" in ephemera*|deployed|"") ;; *) echo "V3 APP STATE $st (chain not done)"; return 0;; esac
  if [ -n "${AW_LOG:-}" ] && grep -q "AndroidWorld finished$" "$AW_LOG" 2>/dev/null; then echo "AW FINISHED ($AW_LOG)"; return 0; fi
  return 1
}
if [ "${2:-}" = "--once" ]; then check && echo "(would exit)" || echo "running: state=$(uvx --from modal modal app list 2>/dev/null | awk -v a="$APP" '$1 == a {print $3}')"; exit 0; fi
until r=$(check); do sleep 180; done
echo "[$(date +%T)] $r"; tail -2 logs/v3_modal_chain.log
