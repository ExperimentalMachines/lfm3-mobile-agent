#!/bin/bash
# Keep a device-streaming reservation alive while the benchmark runs: extend by 20 min whenever fewer than 12 min
# remain (checked every 2 min). Stops when logs/devstream_stop exists. Usage: bash scripts/devstream_keeper.sh <reservation-id>
cd "$(dirname "$0")/.."
R=$1; P=voltaic-psyche-514908-s2
while [ ! -f logs/devstream_stop ]; do
  exp=$(bash scripts/android_cli.sh device remote list --project $P 2>/dev/null | awk -v r=$R '$1==r {print $3, $4}')
  [ -z "$exp" ] && { echo "[$(date +%T)] reservation $R not listed; keeper exiting"; exit 1; }
  left=$(( ( $(date -j -f "%Y-%m-%d %I:%M %p" "$(date +%Y-%m-%d) $exp" +%s 2>/dev/null || echo 0) - $(date +%s) ) / 60 ))
  if [ "$left" -lt 12 ]; then
    bash scripts/android_cli.sh device remote extend --duration=20 $R --project $P 2>&1 | tail -1 | sed "s/^/[$(date +%T)] /"
  fi
  sleep 120
done
echo "[$(date +%T)] stop file present; keeper exiting"
