#!/bin/bash
# Launch a round-10 SageMaker training job (docs/PREREG_v48.md): scripts/training/sm_r10.sh with a code channel and E's
# merged weights (s3://<bucket>/r10/e_merged/); data from the public Hub. Account id and role are read at run time (not stored in the repo).
# usage: R9_BUCKET=<bucket> [R9_REGION=us-west-2] [R9_INSTANCE=ml.g6e.2xlarge] [R9_CKPT=<checkpoint name, to resume another job>] sm_launch_r9.sh <job-name> smoke|full [max_hours] [KEY=VALUE ...]
set -euo pipefail
JOB=$1; MODE=$2; HOURS=${3:-2}; shift 3 || true
B=${R9_BUCKET:?set R9_BUCKET}; R=${R9_REGION:-us-west-2}; INST=${R9_INSTANCE:-ml.g6e.2xlarge}
DREV=${R10_DREV:?set R10_DREV (MobileAgent-SFT-v4.8 commit)}
export AWS_PAGER=""
cd "$(dirname "$0")/../.."
ACCT=$(aws sts get-caller-identity --query Account --output text)
CODE=$(mktemp -d); mkdir -p $CODE/meta
cp scripts/training/sm_r10.sh scripts/training/vm_r10_eval.sh scripts/training/sm_r10_gate.py scripts/training/sm_r8_gate.py scripts/training/sm_r7_gate.py \
   train/sft_vlm.py train/agent_format.py eval/androidcontrol/generate.py eval/androidcontrol/score.py \
   eval/androidcontrol/score_dev.py eval/androidlens/score_androidlens.py $CODE/
cp scripts/training/v4_reference_r7.json $CODE/v4_reference.json
cp data/meta/androidcontrol_test_gt.jsonl data/meta/androidcontrol_test_gt.manifest.json $CODE/meta/
aws s3 sync --delete --only-show-errors $CODE s3://$B/r10/code/$JOB/
rm -rf $CODE
ENV="\"R9_MODE\": \"$MODE\", \"R9_DREV\": \"$DREV\""
for kv in "$@"; do ENV="$ENV, \"${kv%%=*}\": \"${kv#*=}\""; done
cat > /tmp/r10_job_$JOB.json <<JSON
{
 "TrainingJobName": "$JOB",
 "RoleArn": "arn:aws:iam::${ACCT}:role/lfm3-sagemaker-r7",
 "AlgorithmSpecification": {"TrainingImage": "763104351884.dkr.ecr.${R}.amazonaws.com/pytorch-training:2.10.0-gpu-py313-cu130-ubuntu22.04-sagemaker-v2.0",
   "TrainingInputMode": "File", "ContainerEntrypoint": ["bash"], "ContainerArguments": ["/opt/ml/input/data/code/sm_r10.sh"]},
 "InputDataConfig": [{"ChannelName": "code", "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": "s3://${B}/r10/code/${JOB}/", "S3DataDistributionType": "FullyReplicated"}}},
                 {"ChannelName": "e", "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": "s3://${B}/r10/e_merged/", "S3DataDistributionType": "FullyReplicated"}}}],
 "OutputDataConfig": {"S3OutputPath": "s3://${B}/r10/output/"},
 "ResourceConfig": {"InstanceType": "${INST}", "InstanceCount": 1, "VolumeSizeInGB": 300},
 "StoppingCondition": {"MaxRuntimeInSeconds": $((HOURS * 3600))},
 "CheckpointConfig": {"S3Uri": "s3://${B}/r10/ckpt/${R9_CKPT:-$JOB}/", "LocalPath": "/opt/ml/checkpoints"},
 "Environment": {$ENV},
 "Tags": [{"Key": "project", "Value": "lfm3"}]
}
JSON
aws sagemaker create-training-job --region $R --cli-input-json file:///tmp/r10_job_$JOB.json --query TrainingJobArn --output text | sed -E 's/[0-9]{12}/<acct>/'
rm -f /tmp/r10_job_$JOB.json
