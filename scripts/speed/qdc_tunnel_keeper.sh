#!/bin/bash
# Keep the QDC SSH tunnel (local 15037 -> the session's remote adb server 5037) alive while the benchmark runs; never
# binds local 5037 (the shared adb server). Stops when logs/qdc_stop exists. Usage: bash scripts/speed/qdc_tunnel_keeper.sh <key.pem> <remote-host>
cd "$(dirname "$0")/../.."
K=$1; H=$2
while [ ! -f logs/qdc_stop ]; do
  if ! lsof -nP -iTCP:15037 -sTCP:LISTEN > /dev/null 2>&1; then
    echo "[$(date +%T)] tunnel down; reopening"
    nohup ssh -i "$K" -o IdentitiesOnly=yes -o ControlPath=none -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=20 \
      -o ServerAliveCountMax=6 -o ExitOnForwardFailure=yes -L 15037:$H:5037 -N sshtunnel@ssh.qdc.qualcomm.com >> logs/qdc_tunnel.log 2>&1 < /dev/null &
    sleep 10
  fi
  sleep 30
done
echo "[$(date +%T)] stop file; keeper exiting"
