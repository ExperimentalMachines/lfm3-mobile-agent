#!/bin/bash
# Stop whatever runs in <session>'s kernel, then launch <jobs.json> there (fresh code), confirm heartbeat.
# Usage: COLAB_BIN=... COLAB_CONFIG=... scripts/training/launch_on_session.sh <session> <jobs.json>
set -u; set -o pipefail
SESS=$1; NEXT=$2
cd "$(dirname "$0")/../.."
CB=${COLAB_BIN:-$HOME/.local/bin/colab}
C() { "$CB" ${COLAB_CONFIG:+--config "$COLAB_CONFIG"} "$@" < /dev/null 2> >(grep -v "new version\|colab update\|silence this" >&2); }
C restart-kernel -s "$SESS" | tail -1
# bracketed patterns so pkill -f cannot match (and kill) the very shell running these commands
echo 'import subprocess,os;print(subprocess.run("pkill -f [s]ft_vlm.py; pkill -f [v]m_train_eval_push; pkill -f [v]m_model_pipeline; pkill -f [g]enerate.py; pkill -f [e]val_general.py; sleep 3; ps aux | grep -cE \"[s]ft_vlm|[g]enerate.py\"",shell=True,capture_output=True,text=True).stdout.strip(), "killed"); os.makedirs("/content/work/meta",exist_ok=True); print("meta", "ok" if os.path.isdir("/content/work/meta") else "MISSING")' \
  | "$CB" ${COLAB_CONFIG:+--config "$COLAB_CONFIG"} exec -s "$SESS" 2>/dev/null | grep -q "meta ok" || { echo "kernel unreachable"; exit 1; }
for f in train/sft_vlm.py train/agent_format.py train/qwen35_chat_template_gen.jinja eval/androidcontrol/generate.py \
         eval/androidcontrol/score.py eval/androidcontrol/score_dev.py eval/general/eval_general.py data/build_general_replay.py scripts/training/vm_model_pipeline.sh scripts/training/vm_logprob_only.sh data/vm_v3_intents.py scripts/training/vm_v3_intents.sh \
         scripts/training/vm_blocking_jobs.py data/meta/androidcontrol_test_gt.jsonl data/meta/androidcontrol_test_gt.manifest.json; do
  dst="/content/work/$(basename "$f")"; [[ "$f" == data/meta/* ]] && dst="/content/work/meta/$(basename "$f")"
  C upload -s "$SESS" "$f" "$dst" | grep -q Uploaded || { echo "upload failed: $f"; exit 1; }
done
for pair in ${EXTRA_FILES:-}; do  # optional "local:remote" pairs, e.g. data/v41_build_parquet.py:/content/work/v41_build_parquet.py
  C upload -s "$SESS" "${pair%%:*}" "${pair#*:}" | grep -q Uploaded || { echo "upload failed: ${pair%%:*}"; exit 1; }
done
C upload -s "$SESS" "$NEXT" /content/work/jobs.json | grep -q Uploaded || { echo "upload failed: jobs.json"; exit 1; }
nohup "$CB" ${COLAB_CONFIG:+--config "$COLAB_CONFIG"} exec -s "$SESS" --timeout 200000 -f scripts/training/vm_blocking_jobs.py \
  > "logs/${SESS}_jobs_cell_$(basename "$NEXT" .json).log" 2>&1 < /dev/null &
PID=$!; sleep 90
if grep -q heartbeat "logs/${SESS}_jobs_cell_$(basename "$NEXT" .json).log" && kill -0 $PID 2>/dev/null; then echo "[$(date +%T)] launched $NEXT on $SESS — heartbeat confirmed"
else echo "LAUNCH NOT CONFIRMED"; exit 1; fi
