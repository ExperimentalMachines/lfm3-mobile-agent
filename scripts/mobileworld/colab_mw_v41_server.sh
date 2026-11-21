#!/bin/bash
# v4.1 follow-up (docs/PREREG_v41.md). Runs ON a Colab T4 (colab-b account): serve the selected LFM3 GGUF on :8094 with
# exactly the flags of v4's MobileWorld run 2 server, on the same llama.cpp commit, and expose it to the env VM through
# the restricted reverse tunnel (VM localhost:18094 only).
# Files expected in /content/models: $GG and mmproj-LFM3-VL-2B-Q8_0.gguf; /content/tunnel_key.
# Usage (on the VM): VM_IP=<ip> GG=<gguf file name> GG_SHA=<sha256> MM_SHA=<sha256> nohup bash colab_mw_v41_server.sh > /content/mw_v41_server.log 2>&1 &
set -u
cd /content
VM_IP=${VM_IP:?}; GG=${GG:?}; GG_SHA=${GG_SHA:?}; MM_SHA=${MM_SHA:?}
MM=mmproj-LFM3-VL-2B-Q8_0.gguf
[ "$(sha256sum models/$GG | cut -d' ' -f1)" = "$GG_SHA" ] || { echo "SHA MISMATCH $GG"; exit 1; }
[ "$(sha256sum models/$MM | cut -d' ' -f1)" = "$MM_SHA" ] || { echo "SHA MISMATCH $MM"; exit 1; }
echo "model files verified"
if [ ! -x llama.cpp/build/bin/llama-server ]; then
  git clone -q --filter=blob:none https://github.com/ggml-org/llama.cpp.git && cd llama.cpp && git checkout -q cd959bae9 \
    && cmake -B build -DGGML_CUDA=ON -DLLAMA_CURL=OFF -DCMAKE_CUDA_ARCHITECTURES=native > /dev/null \
    && cmake --build build -j "$(nproc)" --target llama-server > build.log 2>&1; echo "BUILD_RC=$?"; cd /content
fi
(cd llama.cpp && git log -1 --format='llama.cpp %h')
nohup llama.cpp/build/bin/llama-server -m models/$GG --mmproj models/$MM -c 8192 --image-max-tokens 1024 \
  --reasoning-format deepseek -np 1 -ngl 99 --cache-ram 0 --port 8094 --host 127.0.0.1 > v41_server.log 2>&1 &
until curl -s --max-time 5 127.0.0.1:8094/health | grep -q ok; do sleep 3; done
echo "[$(date +%T)] server :8094 up ($GG)"
chmod 600 tunnel_key
while true; do   # reconnect forever; the VM side only allows this one forward
  ssh -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes -o BatchMode=yes -o ControlPath=none \
      -o ServerAliveInterval=15 -o ServerAliveCountMax=4 -o ExitOnForwardFailure=yes \
      -i tunnel_key -N -R 18094:127.0.0.1:8094 "ubuntu@${VM_IP}"
  echo "[$(date +%T)] tunnel dropped (rc $?); reconnecting"; sleep 5
done
