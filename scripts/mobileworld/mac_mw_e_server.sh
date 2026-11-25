#!/bin/bash
# E (v4.6-E) on MobileWorld (docs/PREREG_v46.md 2026-11-25 20:40): the model server on this Mac + the restricted reverse
# tunnel to the environment VM (scripts/mobileworld/aws_mw_e_setup.sh). llama.cpp cd959bae9 (the Mac's build 12110, the
# commit of every MobileWorld run) with run 2's server flags; the tunnel publishes it as the VM's localhost:18094 only
# (key restricted to that port, no shell), as run 3's Colab tunnel did. A dropped tunnel reconnects after 5 s; a task
# hit by a drop ends as "model server unreachable", which the completion rule re-runs.
# Usage: nohup bash scripts/mobileworld/mac_mw_e_server.sh > logs/mac_mw_e_server.log 2>&1 &
set -u
cd "$(dirname "$0")/../.." || exit 1
source logs/aws_mw_e.env
GG=models/lfm3vl2b_v46e-GGUF/LFM3-VL-2B-MobileAgent-v4.6-E-Q4_K_M.gguf
MM=models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf
[ "$(shasum -a 256 "$GG" | cut -c1-8)" = fa8f2dca ] || { echo "model sha256 is not fa8f2dca (the published E GGUF)"; exit 1; }
lsof -nP -iTCP:18094 -sTCP:LISTEN > /dev/null && { echo "port 18094 already in use"; exit 1; }
nohup llama-server -m "$GG" --mmproj "$MM" -c 8192 --image-max-tokens 1024 --reasoning-format deepseek -np 1 -ngl 99 \
  --cache-ram 0 --port 18094 --host 127.0.0.1 > logs/llama_server_mw_e.log 2>&1 < /dev/null &
SP=$!
until curl -s --max-time 5 127.0.0.1:18094/health | grep -q ok; do kill -0 $SP 2>/dev/null || { echo "server died"; exit 1; }; sleep 3; done
echo "[$(date +%T)] server :18094 up (pid $SP)"
while kill -0 $SP 2>/dev/null; do
  ssh -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes -o BatchMode=yes -o ControlPath=none \
      -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
      -i "$HOME/.ssh/lfm3_mw_tunnel" -N -R 18094:127.0.0.1:18094 "ubuntu@${IP}"
  echo "[$(date +%T)] tunnel ended (exit $?); reconnecting in 5 s"; sleep 5
done
echo "[$(date +%T)] llama-server exited"
