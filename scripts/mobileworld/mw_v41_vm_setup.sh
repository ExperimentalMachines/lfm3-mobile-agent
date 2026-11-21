#!/bin/bash
# v4.1 follow-up (docs/PREREG_v41.md): create and prepare the MobileWorld environment VM for the one follow-up run.
# Same environment as run 2: GCP n2-standard-16 spot VM with nested virtualisation (scripts/mobileworld/gcp_mw_launch.sh),
# MobileWorld a026188 and its env image, ONE container created with run 2's exact command for the v4 arm (lfmenv_0),
# our agent files (agent_format.py, agent_guards.py, lfm3_mw_agent.py), the 105-task list, the resume script with the
# fixed completion rule, and the reverse-tunnel key restricted to localhost:18094 (no shell).
# The external IP is promoted to a static address so a restart keeps it (the Colab tunnel reconnects by itself).
# Usage: bash scripts/mobileworld/mw_v41_vm_setup.sh <colab_public_ip>      -> writes logs/gcp_mw_instance.env
set -euo pipefail
cd "$(dirname "$0")/../.."
CIP=${1:?usage: $0 <colab_public_ip>}
MW_COMMIT=a026188; K=$HOME/.ssh/lfm3_mw_tunnel
NAME=lfm3-mw-gcp-2 MAX_H=${MAX_H:-14} bash scripts/mobileworld/gcp_mw_launch.sh
source logs/gcp_mw_instance.env
G() { gcloud --project "$PROJECT" --quiet "$@"; }
G compute addresses create lfm3-mw-ip2 --region "$REGION" --addresses "$IP" > /dev/null
G compute firewall-rules create lfm3-mw-ssh-colab3 --network lfm3-mw --allow tcp:22 --source-ranges "$CIP/32" > /dev/null
S() { ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -i "$PEM" "ubuntu@${IP}" "$@"; }
t0=$(date +%s)
until S 'test -f bootstrap_done' 2>/dev/null; do [ $(( $(date +%s) - t0 )) -gt 1200 ] && { echo "bootstrap timeout"; exit 1; }; sleep 10; done
S 'cat kvm_check.txt' | grep -q "KVM acceleration can be used" || { echo "NO KVM on $IP"; exit 1; }
S "test -d MobileWorld/.git || git clone -q https://github.com/Tongyi-MAI/MobileWorld.git; cd MobileWorld && git fetch -q origin && git checkout -q $MW_COMMIT && ~/.local/bin/uv sync -q && printf 'API_KEY=not-used\n' > .env && git log --oneline -1"
S 'for i in 1 2 3 4 5 6; do sudo docker pull -q ghcr.io/tongyi-mai/mobile_world:latest > /dev/null 2>&1 && { echo PULL_OK; break; }; sleep 20; done'
S 'mkdir -p lfm3'
scp -q -i "$PEM" train/agent_format.py train/agent_guards.py eval/mobileworld/lfm3_mw_agent.py "ubuntu@${IP}:lfm3/"
scp -q -i "$PEM" results/mobileworld/mw_gui_en.json "ubuntu@${IP}:mw_gui_en.json"
scp -q -i "$PEM" scripts/mobileworld/gcp_mw_resume_vm.sh "ubuntu@${IP}:mw_resume.sh"
S 'cd lfm3 && sha256sum agent_format.py agent_guards.py lfm3_mw_agent.py' && shasum -a 256 train/agent_format.py train/agent_guards.py eval/mobileworld/lfm3_mw_agent.py
[ -s "$K" ] || ssh-keygen -q -t ed25519 -N "" -C lfm3-mw-tunnel -f "$K"
S "grep -q lfm3-mw-tunnel ~/.ssh/authorized_keys || echo 'restrict,port-forwarding,permitlisten=\"localhost:18094\",command=\"/bin/false\" $(cat "$K.pub")' >> ~/.ssh/authorized_keys"
ssh -i "$K" -o BatchMode=yes -o ConnectTimeout=10 "ubuntu@${IP}" 'echo SHELL_ALLOWED' 2>&1 | grep -q SHELL_ALLOWED && { echo "tunnel key allows a shell: refusing"; exit 1; }
S "cd MobileWorld && sudo /home/ubuntu/.local/bin/uv run mw env run --count 1 --name-prefix lfmenv --backend-start-port 6810 --viewer-start-port 7870 --vnc-start-port 5810 --adb-start-port 5566 --launch-interval 20 > ../envrun_lfm.log 2>&1; tail -3 ../envrun_lfm.log | cut -c1-160"
t0=$(date +%s)
until [ "$(S "sudo docker inspect -f '{{.State.Health.Status}}' lfmenv_0" 2>/dev/null)" = healthy ]; do
  [ $(( $(date +%s) - t0 )) -gt 1200 ] && { echo "lfmenv_0 not healthy after 20 min"; exit 1; }; sleep 20
done
echo "VM $NAME ($IP) ready: lfmenv_0 healthy; tunnel key restricted to 18094"
