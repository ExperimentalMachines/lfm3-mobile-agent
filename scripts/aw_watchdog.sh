#!/bin/bash
# Kill hung child processes of AndroidWorld runs (seen once: an `adb pull` of an app DB during task setup hung for 48 min,
# stalling the whole run). Normal children (adb / file copies) live seconds; anything older than 10 min is hung.
while true; do
  for parent in $(pgrep -f "[r]un_aw.py --console_port"); do
    for child in $(pgrep -P "$parent"); do
      et=$(ps -o etimes= -p "$child" 2>/dev/null | tr -d ' ')
      if [ -n "$et" ] && [ "$et" -gt 600 ]; then
        echo "[$(date +%T)] killing hung child $child (age ${et}s) of run_aw $parent: $(ps -o command= -p "$child" | cut -c1-120)"
        kill "$child"
      fi
    done
  done
  sleep 120
done
