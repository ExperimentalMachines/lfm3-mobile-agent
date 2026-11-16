#!/bin/bash
# Wait for the current blocking-cell job on <session> to finish, then launch <next_jobs.json> on the same
# session (fresh code re-uploaded first). If the session is gone, allocate a new L4 and bootstrap it.
# Usage: COLAB_BIN=... COLAB_CONFIG=... HF_TOKEN_FILE=... scripts/chain_next_job.sh <session> <next_jobs.json>
set -u
set -o pipefail
SESS=$1; NEXT=$2
cd "$(dirname "$0")/.."
CB=${COLAB_BIN:-$HOME/.local/bin/colab}
C() { "$CB" ${COLAB_CONFIG:+--config "$COLAB_CONFIG"} "$@" < /dev/null 2> >(grep -v "new version\|colab update\|silence this" >&2); }
ST=$(mktemp)
echo "[$(date +%T)] waiting for current job on $SESS"
while true; do
  OUTP=$(C download -s "$SESS" /content/work/jobs_status.json "$ST" 2>&1 || true)
  if echo "$OUTP" | grep -q "lost\|not found\|404"; then
    echo "[$(date +%T)] session $SESS gone"; GONE=1; break
  fi
  RID=$(python3 -c "import json;print(json.load(open('$ST')).get('run_id','none'))" 2>/dev/null || echo "?")
  if grep -q '"running"' "$ST" 2>/dev/null; then SEEN_RID=$RID; fi  # re-bind to the newest live run (restarted predecessors)
  # only an exit of the SAME run we saw running counts (stale statuses from earlier runs are ignored)
  if [ -n "${SEEN_RID:-}" ] && [ "$RID" = "$SEEN_RID" ] && grep -q '"exit' "$ST" 2>/dev/null && ! grep -q '"running"' "$ST"; then
    echo "[$(date +%T)] job finished: $(cat $ST)"
    grep -qE '"exit [1-9]' "$ST" && echo "WARNING: predecessor job FAILED; launching the next (independent) model anyway"
    GONE=0; break
  fi
  sleep 120
done
if [ "$GONE" = 1 ]; then
  export COLAB_CLI_REQUEST_TIMEOUT=900
  for i in 1 2 3 4 5; do C new -s "$SESS" --gpu L4 && break; sleep 60; done
  bash scripts/launch_gpu_jobs.sh "$SESS" "$NEXT"
else
  echo 'import os;os.makedirs("/content/work/meta",exist_ok=True);print("meta ok")' | "$CB" ${COLAB_CONFIG:+--config "$COLAB_CONFIG"} exec -s "$SESS" 2>/dev/null | grep -q "meta ok" || { echo "cannot reach $SESS kernel"; exit 1; }
  for f in train/sft_vlm.py train/agent_format.py train/qwen35_chat_template_gen.jinja eval/androidcontrol/generate.py \
           eval/androidcontrol/score.py eval/general/eval_general.py data/build_general_replay.py scripts/vm_model_pipeline.sh \
           scripts/vm_blocking_jobs.py scripts/vm_eval.sh scripts/vm_train.sh scripts/colab_bootstrap.py data/meta/androidcontrol_test_gt.jsonl data/meta/androidcontrol_test_gt.manifest.json; do
    dst="/content/work/$(basename "$f")"; [[ "$f" == data/meta/* ]] && dst="/content/work/meta/$(basename "$f")"
    [ -f "$f" ] || { echo "missing $f"; exit 1; }
    C upload -s "$SESS" "$f" "$dst" | grep -q Uploaded || { echo "upload failed: $f"; exit 1; }
  done
  C upload -s "$SESS" "$NEXT" /content/work/jobs.json | grep -q Uploaded || { echo "upload failed: jobs.json"; exit 1; }
  nohup "$CB" ${COLAB_CONFIG:+--config "$COLAB_CONFIG"} exec -s "$SESS" --timeout 200000 -f scripts/vm_blocking_jobs.py \
    > "logs/${SESS}_jobs_cell_next.log" 2>&1 < /dev/null &
  PID=$!
  sleep 90
  if grep -q "heartbeat" "logs/${SESS}_jobs_cell_next.log" && kill -0 $PID 2>/dev/null; then
    echo "[$(date +%T)] launched $NEXT on $SESS (pid $PID) — heartbeat confirmed"
  else
    echo "[$(date +%T)] LAUNCH NOT CONFIRMED: $(tail -c 300 logs/${SESS}_jobs_cell_next.log)"; exit 1
  fi
fi
