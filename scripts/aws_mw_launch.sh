#!/bin/bash
# Launch one EC2 instance with nested virtualization (KVM) for MobileWorld Android emulators (smoke test, 2026-11-18).
#   - c8i.4xlarge (16 vCPU / 32 GiB; fits the account's 16-vCPU on-demand quota), us-west-2, Ubuntu 24.04, 200 GB gp3
#   - SSH only from this machine's current public IP; key kept in ~/.ssh (never in the repo)
#   - cost guard: the instance powers itself off after MAX_H hours (shutdown behaviour = stop, so the disk is kept)
# Usage: bash scripts/aws_mw_launch.sh            (prints the instance id and public IP; state in logs/aws_mw_instance.env)
#        SPOT=1 NAME=lfm3-mobileworld-2 STATE=logs/aws_mw_instance2.env bash scripts/aws_mw_launch.sh   (spot, second instance)
set -euo pipefail
cd "$(dirname "$0")/.."
R=${REGION:-us-west-2}; TYPE=${TYPE:-c8i.4xlarge}; KEY=lfm3-mw; SG_NAME=lfm3-mw-ssh; MAX_H=${MAX_H:-12}; NAME=${NAME:-lfm3-mobileworld-smoke}; STATE=${STATE:-logs/aws_mw_instance.env}
MARKET=(); [ "${SPOT:-0}" = 1 ] && MARKET=(--instance-market-options "MarketType=spot,SpotOptions={SpotInstanceType=one-time,InstanceInterruptionBehavior=terminate}")
PEM=$HOME/.ssh/$KEY.pem
A() { aws --region "$R" "$@"; }
if [ ! -s "$PEM" ]; then
  A ec2 create-key-pair --key-name $KEY --key-type ed25519 --query KeyMaterial --output text > "$PEM"; chmod 600 "$PEM"
fi
MYIP=$(curl -s https://checkip.amazonaws.com | tr -d '\n')
VPC=$(A ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SG=$(A ec2 describe-security-groups --filters Name=group-name,Values=$SG_NAME Name=vpc-id,Values=$VPC --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
if [ -z "$SG" ] || [ "$SG" = None ]; then
  SG=$(A ec2 create-security-group --group-name $SG_NAME --description "SSH from the lfm3-android Mac only" --vpc-id "$VPC" --query GroupId --output text)
fi
A ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 22 --cidr "$MYIP/32" >/dev/null 2>&1 || true
AMI=$(A ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text)
cat > /tmp/lfm3_mw_userdata.sh <<EOF
#!/bin/bash
shutdown -h +$((MAX_H * 60)) "lfm3-mw cost guard"
apt-get update -y && apt-get install -y docker.io cpu-checker git curl
usermod -aG docker ubuntu
curl -LsSf https://astral.sh/uv/install.sh | sudo -u ubuntu sh
(kvm-ok; ls -l /dev/kvm) > /home/ubuntu/kvm_check.txt 2>&1
touch /home/ubuntu/bootstrap_done
EOF
IID=$(A ec2 run-instances --image-id "$AMI" --instance-type "$TYPE" --key-name $KEY --security-group-ids "$SG" \
  --cpu-options "NestedVirtualization=enabled" ${MARKET[@]+"${MARKET[@]}"} \
  --instance-initiated-shutdown-behavior $([ "${SPOT:-0}" = 1 ] && echo terminate || echo stop) \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":200,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --user-data file:///tmp/lfm3_mw_userdata.sh \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME},{Key=project,Value=lfm3-android}]" \
  --query 'Instances[0].InstanceId' --output text)
A ec2 wait instance-running --instance-ids "$IID"
IP=$(A ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
printf "REGION=%s\nIID=%s\nIP=%s\nPEM=%s\nTYPE=%s\n" "$R" "$IID" "$IP" "$PEM" "$TYPE" > "$STATE"
echo "launched $IID ($TYPE, $R) at $IP; auto power-off in ${MAX_H} h"
