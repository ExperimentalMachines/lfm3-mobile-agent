#!/bin/bash
# Runs ON a Colab GPU VM: serve GUI-Owl-1.5-2B on :8092 and MAI-UI-2B on :8093 (same llama.cpp commit and server flags
# as GUI-Owl's AndroidWorld runs on the Mac, plus -ngl 99; MAI-UI GGUFs converted the same way: Q4_K_M + Q8_0 mmproj)
# and expose them to a MobileWorld env host through a reverse SSH tunnel (remote 18092 / 18093).
# The tunnel key is restricted on the EC2 side to `restrict,port-forwarding,permitlisten="localhost:18092",
# permitlisten="localhost:18093",command="/bin/false"` (no shell, two ports). The env host firewall (AWS security group / GCP firewall) must allow this VM's public IP on port 22.
# Files expected in /content: models/GUI-Owl-1.5-2B-Instruct.Q4_K_M.gguf, models/GUI-Owl-1.5-2B-Instruct.mmproj-Q8_0.gguf,
# models/MAI-UI-2B-Q4_K_M.gguf, models/mmproj-MAI-UI-2B-Q8_0.gguf, tunnel_key. Usage (on the VM): EC2_IP=<ip> nohup bash colab_mw_models.sh > /content/mw_models.log 2>&1 &
set -u
cd /content
EC2_IP=${EC2_IP:?}
if [ ! -x llama.cpp/build/bin/llama-server ]; then
  git clone -q --filter=blob:none https://github.com/ggml-org/llama.cpp.git && cd llama.cpp && git checkout -q cd959bae9 \
    && cmake -B build -DGGML_CUDA=ON -DLLAMA_CURL=OFF -DCMAKE_CUDA_ARCHITECTURES=native > /dev/null \
    && cmake --build build -j "$(nproc)" --target llama-server > build.log 2>&1; echo "BUILD_RC=$?"; cd /content
fi
nohup llama.cpp/build/bin/llama-server -m models/GUI-Owl-1.5-2B-Instruct.Q4_K_M.gguf \
  --mmproj models/GUI-Owl-1.5-2B-Instruct.mmproj-Q8_0.gguf -c 20480 -np 1 -ngl 99 --image-max-tokens 2600 --jinja \
  --port 8092 --host 127.0.0.1 > guiowl_server.log 2>&1 &
nohup llama.cpp/build/bin/llama-server -m models/MAI-UI-2B-Q4_K_M.gguf \
  --mmproj models/mmproj-MAI-UI-2B-Q8_0.gguf -c 20480 -np 1 -ngl 99 --image-max-tokens 2600 --jinja \
  --port 8093 --host 127.0.0.1 > maiui_server.log 2>&1 &
until curl -s --max-time 5 127.0.0.1:8092/health | grep -q ok && curl -s --max-time 5 127.0.0.1:8093/health | grep -q ok; do sleep 3; done
echo "[$(date +%T)] GUI-Owl (:8092) and MAI-UI (:8093) servers up"
chmod 600 tunnel_key
while true; do   # reconnect forever; the EC2 side only allows this one forward
  ssh -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes -o BatchMode=yes -o ControlPath=none \
      -o ServerAliveInterval=15 -o ServerAliveCountMax=4 -o ExitOnForwardFailure=yes \
      -i tunnel_key -N -R 18092:127.0.0.1:8092 -R 18093:127.0.0.1:8093 "ubuntu@${EC2_IP}"
  echo "[$(date +%T)] tunnel dropped (rc $?); reconnecting"; sleep 5
done
