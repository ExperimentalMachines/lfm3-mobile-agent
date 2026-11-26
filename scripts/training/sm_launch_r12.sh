#!/bin/bash
# Launch a round-12 E-V job (docs/PREREG_v410.md): scripts/training/sm_r12.sh with channels code, e (E's merged weights,
# s3://<bucket>/r10/e_merged/) and r12in (s3://<bucket>/r12/in/: ody_term2.parquet, the judge verdicts, the written actions,
# the M_notdone split, round 11 mix stats (M_done ids), the AndroidControl verdicts; uploaded by this script).
# Account id and role are read at run time (not stored in the repo).
# usage: R9_BUCKET=<bucket> [R9_CKPT=<resume name>] sm_launch_r12.sh <job> smoke|full [max_hours] [KEY=VALUE ...]
set -euo pipefail
JOB=$1; MODE=$2; HOURS=${3:-2}; shift 3 || true
B=${R9_BUCKET:?set R9_BUCKET}; R=${R9_REGION:-us-west-2}; INST=${R9_INSTANCE:-ml.g6.2xlarge}
export AWS_PAGER=""
cd "$(dirname "$0")/../.."
ACCT=$(aws sts get-caller-identity --query Account --output text)
CODE=$(mktemp -d); mkdir -p $CODE/meta
cp scripts/training/sm_r12.sh scripts/training/vm_r8_eval.sh scripts/training/sm_r12_gate.py scripts/training/sm_r8_gate.py \
   scripts/training/sm_r7_gate.py data/r12_mix.py train/sft_vlm.py train/agent_format.py train/screen_change.py \
   eval/androidcontrol/generate.py eval/androidcontrol/score.py eval/androidcontrol/score_dev.py eval/androidlens/score_androidlens.py $CODE/
cp scripts/training/v4_reference_r7.json $CODE/v4_reference.json
cp results/v46_dev/e_eval/r8e_offline_gate.json $CODE/e_gate.json
cp data/meta/androidcontrol_test_gt.jsonl data/meta/androidcontrol_test_gt.manifest.json $CODE/meta/
aws s3 sync --delete --only-show-errors $CODE s3://$B/r12/code/$JOB/
rm -rf $CODE
IN=$(mktemp -d)
cp data/r12work/ody_term2.parquet results/v48_dev/claude_ody_terminal_verdicts.jsonl results/r12_dev/claude_next_actions.jsonl \
   results/r12_dev/notdone_split.json results/v48_dev/claude_ac_complete_verdicts.jsonl $IN/
cp results/r11_dev/mix_stats.json $IN/r11_mix_stats.json
aws s3 sync --delete --only-show-errors $IN s3://$B/r12/in/
rm -rf $IN
ENV="\"R12_MODE\": \"$MODE\""
for kv in "$@"; do ENV="$ENV, \"${kv%%=*}\": \"${kv#*=}\""; done
SPEC=$(mktemp)
cat > $SPEC <<JSON
{
 "TrainingJobName": "$JOB",
 "RoleArn": "arn:aws:iam::${ACCT}:role/lfm3-sagemaker-r7",
 "AlgorithmSpecification": {"TrainingImage": "763104351884.dkr.ecr.${R}.amazonaws.com/pytorch-training:2.10.0-gpu-py313-cu130-ubuntu22.04-sagemaker-v2.0",
   "TrainingInputMode": "File", "ContainerEntrypoint": ["bash"], "ContainerArguments": ["/opt/ml/input/data/code/sm_r12.sh"]},
 "InputDataConfig": [{"ChannelName": "code", "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": "s3://${B}/r12/code/${JOB}/", "S3DataDistributionType": "FullyReplicated"}}},
                 {"ChannelName": "e", "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": "s3://${B}/r10/e_merged/", "S3DataDistributionType": "FullyReplicated"}}},
                 {"ChannelName": "r12in", "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": "s3://${B}/r12/in/", "S3DataDistributionType": "FullyReplicated"}}}],
 "OutputDataConfig": {"S3OutputPath": "s3://${B}/r12/output/"},
 "ResourceConfig": {"InstanceType": "${INST}", "InstanceCount": 1, "VolumeSizeInGB": 300},
 "StoppingCondition": {"MaxRuntimeInSeconds": $((HOURS * 3600))},
 "CheckpointConfig": {"S3Uri": "s3://${B}/r12/ckpt/${R9_CKPT:-$JOB}/", "LocalPath": "/opt/ml/checkpoints"},
 "Environment": {$ENV},
 "Tags": [{"Key": "project", "Value": "lfm3"}]
}
JSON
aws sagemaker create-training-job --region $R --cli-input-json file://$SPEC --query TrainingJobArn --output text | sed -E 's/[0-9]{12}/<acct>/'
rm -f $SPEC
