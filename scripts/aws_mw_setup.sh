#!/bin/bash
# Bootstrap MobileWorld on an instance from scripts/aws_mw_launch.sh: wait for cloud-init, clone MobileWorld (pinned
# commit), uv sync, minimal .env (GUI-only tasks need no API keys), pull the env image with retries, start N containers,
# copy our agent files. Usage: bash scripts/aws_mw_setup.sh logs/aws_mw_instance2.env [N=2]
set -euo pipefail
cd "$(dirname "$0")/.."
source "$1"; N=${2:-2}; MW_COMMIT=a026188
S() { ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -i "$PEM" "ubuntu@${IP}" "$@"; }
until S 'test -f bootstrap_done' 2>/dev/null; do sleep 10; done
S 'cat kvm_check.txt' | grep -q "KVM acceleration can be used" || { echo "NO KVM on $IP"; exit 1; }
S "test -d MobileWorld || { git clone -q https://github.com/Tongyi-MAI/MobileWorld.git && cd MobileWorld && git checkout -q $MW_COMMIT; }; cd MobileWorld && ~/.local/bin/uv sync -q && printf 'API_KEY=not-used\n' > .env && git log --oneline -1"
S 'for i in 1 2 3 4 5 6; do sudo docker pull -q ghcr.io/tongyi-mai/mobile_world:latest > /dev/null 2>&1 && { echo PULL_OK; break; }; sleep 20; done'
S 'mkdir -p lfm3'
scp -q -i "$PEM" train/agent_format.py eval/mobileworld/lfm3_mw_agent.py "ubuntu@${IP}:lfm3/"
S "cd MobileWorld && sudo /home/ubuntu/.local/bin/uv run mw env run --count $N --launch-interval 20 > ../envrun.log 2>&1; tail -6 ../envrun.log"
