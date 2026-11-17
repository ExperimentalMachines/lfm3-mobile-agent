#!/bin/bash
# Kill hung child processes of AndroidWorld runs (seen once: an `adb pull` of an app DB during task setup hung for 48 min,
# stalling the whole run). Normal children (adb / file copies) live seconds; anything older than 10 min is hung.
while true; do
  for parent in $(pgrep -f "[r]un_aw.py --console_port"); do
    for child in $(pgrep -P "$parent"); do
      # macOS ps has no etimes; convert etime "[[dd-]hh:]mm:ss" to seconds
      et=$(ps -o etime= -p "$child" 2>/dev/null | tr -d ' ' | awk -F'[-:]' '{n=NF; s=$n+60*$(n-1); if(n>=3)s+=3600*$(n-2); if(n>=4)s+=86400*$(n-3); print s}')
      if [ -n "$et" ] && [ "$et" -gt 600 ]; then
        echo "[$(date +%T)] killing hung child $child (age ${et}s) of run_aw $parent: $(ps -o command= -p "$child" | cut -c1-120)"
        kill "$child"
      fi
    done
  done
  sleep 120
done
