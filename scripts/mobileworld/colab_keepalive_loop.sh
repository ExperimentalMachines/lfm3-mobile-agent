#!/bin/bash
# Keep a Colab model-server session alive (the server runs detached, so the kernel looks idle) by running a trivial
# cell every 4 minutes; exits when the session is gone. Restored from archive tag archive/pre-restructure-2026-11-20
# (scripts/colab_keepalive_loop.sh) with the CLI selectable; default colab-b (credits account, from 2026-11-21).
# Usage: nohup bash scripts/mobileworld/colab_keepalive_loop.sh <session> > logs/colab_keepalive_<session>.log 2>&1 &
S=$1; CB=${COLAB_BIN:-$HOME/.local/bin/colab-b}
while "$CB" sessions < /dev/null 2>&1 | grep -q "^\[$S\] "; do
  echo "print('keepalive')" | "$CB" exec -s "$S" --timeout 60 > /dev/null 2>&1
  sleep 240
done
echo "[$(date +%T)] session $S gone; keepalive loop exiting"
