#!/bin/bash
# MAI-UI-2B on AndroidWorld seed 30 (DEVELOPMENT seed; extra comparison arm, not part of the sealed protocol), emulator 1.
#   server: $Q (default Q8_0; Q4_K_M breaks MAI-UI's output: empty <thinking> loops, see results/maiui_quant_check.md)
#           + Q8_0 mmproj converted from Tongyi-MAI/MAI-UI-2B @ 5030509 with llama.cpp cd959bae9 (same procedure
#           as GUI-Owl's files), Metal, same flags as GUI-Owl's AndroidWorld server (-c 20480 --image-max-tokens 2600 --jinja)
#   agent : eval/androidworld/maiui_agent.py (official MAI-UI navigation prompt and history format), matched budget:
#           1 screenshot per step at <= 1,048,576 px (= GUI-Owl matched), temperature 0
#   1. smoke: 2 tasks into results/androidworld/_smoke_$NAME (agent errors, unparseable and empty-<thinking> replies checked)
#   2. full seed-30 run into results/androidworld/$NAME
# Usage: nohup bash scripts/androidworld/local_maiui_aw.sh > logs/local_maiui_aw.log 2>&1 &
set -u
cd "$(dirname "$0")/../.." || exit 1
CP=5556; GP=8556; PORT=8119; Q=${Q:-Q8_0}; QL=$(echo "$Q" | tr A-Z a-z); NAME=maiui_2b_matched_$QL; LABEL=maiui_2b_matched1img_$QL
M=models/MAI-UI-2B-GGUF
log() { echo "[$(date +%T)] $*"; }
pgrep -f "[r]un_aw.py.*console_port=$CP" >/dev/null && { log "emulator $CP busy; refusing"; exit 1; }
lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1 && { log "port $PORT in use; refusing"; exit 1; }
[ -e results/androidworld/$NAME ] && { log "results/androidworld/$NAME exists; refusing to mix runs"; exit 1; }
nohup llama-server -m $M/MAI-UI-2B-$Q.gguf --mmproj $M/mmproj-MAI-UI-2B-Q8_0.gguf -c 20480 -np 1 -ngl 99 \
  --image-max-tokens 2600 --jinja --port $PORT --host 127.0.0.1 > logs/llama_server_$NAME.log 2>&1 < /dev/null &
SP=$!
t0=$(date +%s)
until curl -s --max-time 5 127.0.0.1:$PORT/health | grep -q ok; do
  kill -0 $SP 2>/dev/null || { log "server died"; exit 1; }
  [ $(( $(date +%s) - t0 )) -gt 600 ] && { kill $SP; log "server not healthy after 600 s"; exit 1; }
  sleep 3
done
[ "$(lsof -nP -t -iTCP:$PORT -sTCP:LISTEN | head -1)" = "$SP" ] || { kill $SP; log "port $PORT not owned by $SP"; exit 1; }
log "server :$PORT up (pid $SP)"
RUN=(--console_port=$CP --grpc_port=$GP --server_url=http://127.0.0.1:$PORT --agent=maiui --maiui_images=1
     --maiui_max_pixels=1048576 --agent_label=$LABEL)
log "smoke: 2 tasks"
.venv-aw/bin/python eval/androidworld/run_aw.py "${RUN[@]}" --tasks=ContactsAddContact,SystemBrightnessMax \
  --output_path=results/androidworld/_smoke_${NAME} 2>&1 | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" > logs/aw_smoke_maiui.log
SMOKE_GLOB="results/androidworld/_smoke_${NAME}/run_*/" .venv-aw/bin/python - <<'PY' || { kill $SP; log "SMOKE FAILED"; exit 1; }
import glob, gzip, os, pickle
r = sorted(glob.glob(os.environ["SMOKE_GLOB"]))[-1]
eps = [pickle.loads(gzip.decompress(open(f, "rb").read()))[0] for f in glob.glob(r + "*.pkl.gz")]
assert len(eps) == 2, f"{len(eps)} smoke episodes"
for e in eps:
    d = e["episode_data"]; acts = d.get("parsed_action") or []
    bad = sum(1 for a in acts if a is None); errs = [x for x in (d.get("error") or []) if x]
    print(e["task_template"], "steps", len(acts), "unparseable", bad, "errors", errs[:3], "success", e.get("is_successful"))
    assert len(acts) >= 1 and bad < len(acts), "agent produced no usable action"
    mc = d.get("model_content") or []
    empty = sum(1 for c in mc if not c.split("</thinking>")[0].replace("<thinking>", "").strip())
    assert empty <= len(mc) // 4, f"{empty}/{len(mc)} steps with empty <thinking> (degenerate output)"
PY
log "smoke ok; full seed-30 run"
.venv-aw/bin/python eval/androidworld/run_aw.py "${RUN[@]}" --output_path=results/androidworld/$NAME 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" > logs/aw_run_$NAME.log
kill $SP
D=$(ls -d results/androidworld/$NAME/run_*/ 2>/dev/null | tail -1); D=${D%/}
N=$([ -n "$D" ] && ls "$D"/*.pkl.gz 2>/dev/null | wc -l | tr -d ' ' || echo 0)
log "MAI-UI seed-30 run finished: $N/116 episodes in ${D:-none}"
