#!/bin/bash
# Launch a GCP VM with nested virtualization (KVM) for MobileWorld Android emulators (2026-11-18; credits project).
#   - n2-standard-16 (16 vCPU / 64 GB) SPOT in us-west1 (Oregon, next to AWS us-west-2), Ubuntu 24.04, 200 GB pd-balanced
#   - its own VPC "lfm3-mw": only SSH (22) from this Mac's public IP (more sources added explicitly, e.g. a Colab VM)
#   - cost guard: --max-run-duration (default 12 h) then STOP; spot preemption also STOPs (disk kept; delete when done)
#   - writes REGION/ZONE/NAME/IP/PEM to $STATE so scripts/aws_mw_setup.sh can bootstrap MobileWorld unchanged
# Usage: bash scripts/gcp_mw_launch.sh    (env: NAME, TYPE, ZONE, MAX_H, STATE)
set -euo pipefail
cd "$(dirname "$0")/.."
P=${PROJECT:-voltaic-psyche-514908-s2}; ZONE=${ZONE:-us-west1-b}; REGION=${ZONE%-*}; TYPE=${TYPE:-n2-standard-16}
NAME=${NAME:-lfm3-mw-gcp-1}; MAX_H=${MAX_H:-12}; STATE=${STATE:-logs/gcp_mw_instance.env}; NET=lfm3-mw
PEM=$HOME/.ssh/lfm3-gcp
G() { gcloud --project "$P" --quiet "$@"; }
[ -s "$PEM" ] || ssh-keygen -q -t ed25519 -N "" -C lfm3-gcp -f "$PEM"
MYIP=$(curl -s https://checkip.amazonaws.com | tr -d '\n')
G compute networks describe $NET >/dev/null 2>&1 || G compute networks create $NET --subnet-mode=auto >/dev/null
G compute firewall-rules describe $NET-ssh-mac >/dev/null 2>&1 || \
  G compute firewall-rules create $NET-ssh-mac --network $NET --allow tcp:22 --source-ranges "$MYIP/32" >/dev/null
cat > /tmp/lfm3_gcp_startup.sh <<'EOF'
#!/bin/bash
[ -f /home/ubuntu/bootstrap_done ] && exit 0
apt-get update -y && apt-get install -y docker.io cpu-checker git curl
usermod -aG docker ubuntu
curl -LsSf https://astral.sh/uv/install.sh | sudo -u ubuntu sh
(kvm-ok; ls -l /dev/kvm) > /home/ubuntu/kvm_check.txt 2>&1
touch /home/ubuntu/bootstrap_done
EOF
G compute instances create "$NAME" --zone "$ZONE" --machine-type "$TYPE" --network "$NET" \
  --enable-nested-virtualization --provisioning-model=SPOT --instance-termination-action=STOP \
  --max-run-duration="${MAX_H}h" \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud --boot-disk-size=200GB --boot-disk-type=pd-balanced \
  --metadata-from-file=startup-script=/tmp/lfm3_gcp_startup.sh --metadata="ssh-keys=ubuntu:$(cat "$PEM.pub")" \
  --labels=project=lfm3-android >/dev/null
IP=$(G compute instances describe "$NAME" --zone "$ZONE" --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
printf "REGION=%s\nZONE=%s\nNAME=%s\nIP=%s\nPEM=%s\nTYPE=%s\nPROJECT=%s\n" "$REGION" "$ZONE" "$NAME" "$IP" "$PEM" "$TYPE" "$P" > "$STATE"
echo "launched $NAME ($TYPE spot, $ZONE) at $IP; stops after ${MAX_H} h"
