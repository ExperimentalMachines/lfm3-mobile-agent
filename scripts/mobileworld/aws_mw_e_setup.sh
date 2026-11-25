#!/bin/bash
# E (v4.6-E) on MobileWorld (docs/PREREG_v46.md 2026-11-25 20:40): create and prepare the AWS environment VM.
# As run 2 / run 3 (scripts/mobileworld/mw_v41_vm_setup.sh), on AWS instead of GCP:
#   * EC2 c8i.4xlarge with nested virtualisation (scripts/mobileworld/aws_mw_launch.sh; powers itself off after MAX_H h)
#   * MobileWorld a026188; env image pinned by digest (the `latest` tag, built 2025-12-24 = the image of run 2), tagged
#     `latest` locally so `mw env run` uses it
#   * ONE container created with run 2's exact command for the LFM3 arm (lfmenv_0)
#   * our agent files (agent_format.py, agent_guards.py, screen_change.py, lfm3_mw_agent.py), the 105-task list and the
#     resume script with run 2's completion rule (run `e`)
#   * the reverse-tunnel key restricted to localhost:18094 (no shell); the model server runs on the Mac
#     (scripts/mobileworld/mac_mw_e_server.sh)
# Usage: bash scripts/mobileworld/aws_mw_e_setup.sh        -> writes logs/aws_mw_e.env
set -euo pipefail
cd "$(dirname "$0")/../.."
MW_COMMIT=a026188; K=$HOME/.ssh/lfm3_mw_tunnel
IMG=ghcr.io/tongyi-mai/mobile_world; DIGEST=sha256:b680380eac98a7ad064707f9653772af18554d201a3e6e7cf8f15d58cdc73240
STATE=logs/aws_mw_e.env
[ -s "$STATE" ] || NAME=lfm3-mw-e MAX_H=${MAX_H:-16} STATE=$STATE bash scripts/mobileworld/aws_mw_launch.sh
source "$STATE"
S() { ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -i "$PEM" "ubuntu@${IP}" "$@"; }
t0=$(date +%s)
until S 'test -f bootstrap_done' 2>/dev/null; do [ $(( $(date +%s) - t0 )) -gt 1200 ] && { echo "bootstrap timeout"; exit 1; }; sleep 10; done
S 'cat kvm_check.txt' | grep -q "KVM acceleration can be used" || { echo "NO KVM on $IP"; exit 1; }
S "test -d MobileWorld/.git || git clone -q https://github.com/Tongyi-MAI/MobileWorld.git; cd MobileWorld && git fetch -q origin && git checkout -q $MW_COMMIT && ~/.local/bin/uv sync -q && printf 'API_KEY=not-used\n' > .env && git log -1 --format='MobileWorld %h'"
S "for i in 1 2 3 4 5 6; do sudo docker pull -q $IMG@$DIGEST > /dev/null 2>&1 && { echo PULL_OK; break; }; sleep 20; done; sudo docker tag $IMG@$DIGEST $IMG:latest && sudo docker image inspect -f '{{index .RepoDigests 0}}' $IMG:latest"
S 'mkdir -p lfm3 traj_logs'
scp -q -i "$PEM" train/agent_format.py train/agent_guards.py train/screen_change.py eval/mobileworld/lfm3_mw_agent.py "ubuntu@${IP}:lfm3/"
scp -q -i "$PEM" results/mobileworld/mw_gui_en.json "ubuntu@${IP}:mw_gui_en.json"
scp -q -i "$PEM" scripts/mobileworld/gcp_mw_resume_vm.sh "ubuntu@${IP}:mw_resume.sh"
S 'cd lfm3 && sha256sum agent_format.py agent_guards.py screen_change.py lfm3_mw_agent.py' && shasum -a 256 train/agent_format.py train/agent_guards.py train/screen_change.py eval/mobileworld/lfm3_mw_agent.py
[ -s "$K" ] || ssh-keygen -q -t ed25519 -N "" -C lfm3-mw-tunnel -f "$K"
S "grep -q lfm3-mw-tunnel ~/.ssh/authorized_keys || echo 'restrict,port-forwarding,permitlisten=\"localhost:18094\",command=\"/bin/false\" $(cat "$K.pub")' >> ~/.ssh/authorized_keys"
ssh -i "$K" -o IdentitiesOnly=yes -o ControlPath=none -o BatchMode=yes -o ConnectTimeout=10 "ubuntu@${IP}" 'echo SHELL_ALLOWED' 2>&1 | grep -q SHELL_ALLOWED && { echo "tunnel key allows a shell: refusing"; exit 1; }
S "sudo docker ps -a --format '{{.Names}}' | grep -q '^lfmenv_0$' || (cd MobileWorld && sudo /home/ubuntu/.local/bin/uv run mw env run --count 1 --name-prefix lfmenv --backend-start-port 6810 --viewer-start-port 7870 --vnc-start-port 5810 --adb-start-port 5566 --launch-interval 20 > ../envrun_lfm.log 2>&1; tail -3 ../envrun_lfm.log | cut -c1-160)"
t0=$(date +%s)
until [ "$(S "sudo docker inspect -f '{{.State.Health.Status}}' lfmenv_0" 2>/dev/null)" = healthy ]; do
  [ $(( $(date +%s) - t0 )) -gt 1200 ] && { echo "lfmenv_0 not healthy after 20 min"; exit 1; }; sleep 20
done
S "sudo docker inspect -f '{{.Image}}' lfmenv_0"
echo "VM lfm3-mw-e ($IP) ready: lfmenv_0 healthy; tunnel key restricted to 18094"
