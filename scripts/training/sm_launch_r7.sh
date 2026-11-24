#!/bin/bash
# Launch the round-7 SageMaker training job (docs/PREREG_v45.md). The data channel must already hold the mix
# (s3://$R7_BUCKET/r7/data/: train, ac_val, gate splits, androidlens/), uploaded from the build instance.
# usage: R7_BUCKET=<bucket> [R7_INSTANCE=ml.g7e.2xlarge] scripts/training/sm_launch_r7.sh <job-name> smoke|full [bs ga] [max_hours]
# Account id and role ARN are read at run time (not stored in the repo).
set -euo pipefail
JOB=$1; MODE=$2; BS=${3:-4}; GA=${4:-8}; HOURS=${5:-3}
B=${R7_BUCKET:?set R7_BUCKET}
INST=${R7_INSTANCE:-ml.g7e.2xlarge}
R=us-west-2
export AWS_PAGER=""
cd "$(dirname "$0")/../.."
ACCT=$(aws sts get-caller-identity --query Account --output text)
ROLE=arn:aws:iam::$ACCT:role/lfm3-sagemaker-r7
IMG=763104351884.dkr.ecr.$R.amazonaws.com/pytorch-training:2.10.0-gpu-py313-cu130-ubuntu22.04-sagemaker-v2.0
CODE=$(mktemp -d)
cp scripts/training/sm_r7.sh scripts/training/sm_r7_gate.py train/sft_vlm.py train/agent_format.py \
   eval/androidcontrol/generate.py eval/androidcontrol/score.py eval/androidcontrol/score_dev.py eval/androidlens/score_androidlens.py \
   data/meta/androidcontrol_test_gt.jsonl data/meta/androidcontrol_test_gt.manifest.json $CODE/
cp scripts/training/v4_reference_r7.json $CODE/v4_reference.json
aws s3 sync --delete --only-show-errors $CODE s3://$B/r7/code/$JOB/
rm -rf $CODE
cat > /tmp/r7_job_$JOB.json <<EOF
{
 "TrainingJobName": "$JOB",
 "RoleArn": "$ROLE",
 "AlgorithmSpecification": {"TrainingImage": "$IMG", "TrainingInputMode": "File",
   "ContainerEntrypoint": ["bash"], "ContainerArguments": ["/opt/ml/input/data/code/sm_r7.sh"]},
 "InputDataConfig": [
   {"ChannelName": "code", "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": "s3://$B/r7/code/$JOB/", "S3DataDistributionType": "FullyReplicated"}}},
   {"ChannelName": "data", "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": "s3://$B/r7/data/", "S3DataDistributionType": "FullyReplicated"}}}
 ],
 "OutputDataConfig": {"S3OutputPath": "s3://$B/r7/output/"},
 "ResourceConfig": {"InstanceType": "$INST", "InstanceCount": 1, "VolumeSizeInGB": 300},
 "StoppingCondition": {"MaxRuntimeInSeconds": $((HOURS * 3600))},
 "CheckpointConfig": {"S3Uri": "s3://$B/r7/ckpt/$JOB/", "LocalPath": "/opt/ml/checkpoints"},
 "Environment": {"R7_MODE": "$MODE", "R7_BS": "$BS", "R7_GA": "$GA"},
 "Tags": [{"Key": "project", "Value": "lfm3"}]
}
EOF
aws sagemaker create-training-job --region $R --cli-input-json file:///tmp/r7_job_$JOB.json --query TrainingJobArn --output text | sed -E 's/[0-9]{12}/<acct>/'
rm -f /tmp/r7_job_$JOB.json
