#!/bin/bash
# Keep an idle-looking Colab session alive (jobs run detached via subprocess.Popen, so the kernel is idle) by running a
# trivial cell every 4 minutes; stops when the session disappears. Usage: nohup bash scripts/colab_keepalive_loop.sh <session> &
S=$1
while ~/.local/bin/colab sessions < /dev/null 2>&1 | grep -q "^\[$S\] "; do
  echo "print('keepalive')" | ~/.local/bin/colab exec -s "$S" --timeout 60 > /dev/null 2>&1
  sleep 240
done
echo "[$(date +%T)] session $S gone; keepalive loop exiting"
