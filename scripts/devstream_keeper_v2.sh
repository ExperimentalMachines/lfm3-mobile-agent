#!/bin/bash
# Keep the reservation alive: every 2 min, if fewer than 12 minutes remain, extend by 20 (v1 mis-parsed the time and
# extended every loop; unused minutes are refunded on release anyway). Stops on logs/devstream_stop.
cd "$(dirname "$0")/.."
R=$1; P=voltaic-psyche-514908-s2
while [ ! -f logs/devstream_stop ]; do
  exp=$(bash scripts/android_cli.sh device remote list --project $P 2>/dev/null | awk -v r=$R '$1==r {print $3" "$4}')
  [ -z "$exp" ] && { echo "[$(date +%T)] $R not listed; exiting"; exit 1; }
  left=$(python3 -c "
import datetime as d, sys
now = d.datetime.now(); t = d.datetime.strptime(sys.argv[1], '%I:%M %p').replace(year=now.year, month=now.month, day=now.day)
print(int((t - now).total_seconds() // 60))" "$exp")
  [ "$left" -lt 12 ] && bash scripts/android_cli.sh device remote extend --duration=20 $R --project $P 2>&1 | tail -1 | sed "s/^/[$(date +%T)] /"
  sleep 120
done
echo "[$(date +%T)] stop file; keeper exiting"
