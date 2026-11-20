#!/bin/bash
# v4 hand-off v2 (2026-11-18). The merged-v4 upload to the hub failed ("Private storage limit reached"), so the
# merged weights were copied off the Colab VM. This replaces the hub wait of scripts/local_v4_to_aw.sh (archived: tag archive/pre-restructure-2026-11-20) with:
#   1. the source dir must match results/v4_local_export_manifest.json exactly (file set + sha256; written after
#      check_local_merge.py passed and the 14 non-weight files were found byte-identical to the v3 merged release),
#      and check_local_merge.py is re-run against the pinned base and pinned adapter revision;
#   2. phone GGUF export from that dir (same converter/quant/mmproj as v1-v3);
#   3. same hand-off markers in logs/local_v4_to_aw.log for scripts/androidworld/local_emu2_fill_v2.sh ("exported; pausing" -> it
#      pauses the sealed GUI-Owl seed-1234 arm; "v4 AndroidWorld seed-30 finished" -> it resumes that arm). After
#      "exported; pausing" every exit path prints the finished marker, so the sealed arm is never left paused;
#   4. emulator 2 is used only after the sealed arm's launcher, runner and server (:8115) are all gone;
#   5. our own llama-server on :8114 (port must be free first; bounded start; PID-bound health check);
#   6. the seed-30 DEVELOPMENT pass, unchanged (agent label, prompt v4, thinking on, llama-server flags);
#   7. the episode count is reported, INCOMPLETE when it is not 116 (v1 printed "finished" regardless).
# Codex audit: results/codex/v4_local_lane_audit/codex_v4_local_lane_audit.md
# Usage: nohup bash scripts/androidworld/local_v4_to_aw_v2.sh models/hf_local/LFM3-VL-2B-AndroidAgent-v4 >> logs/local_v4_to_aw.log 2>&1 &
set -u
cd "$(dirname "$0")/../.." || exit 1
SP=""; SRC=$1; OUT=models/lfm3vl2b_v4-GGUF; NAME=lfm3vl2b_v4; PORT=8114; CP=5558; GP=8558
GG=$OUT/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf; MM=models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf
BASE=$HOME/.cache/huggingface/hub/models--LiquidAI--LFM3-VL-2B/snapshots/23387beda43c60310348e83e25f78f33c3140d3a/model.safetensors
MAN=results/v4_local_export_manifest.json
log() { echo "[$(date +%T)] $*"; }
release() { [ -n "${SP:-}" ] && kill "$SP" 2>/dev/null; log "$*"; log "v4 AndroidWorld seed-30 finished"; exit 1; }   # only our own server
[ "$(basename "$SRC")" = LFM3-VL-2B-AndroidAgent-v4 ] || { log "EXPORT FAILED (source dir must be named LFM3-VL-2B-AndroidAgent-v4)"; exit 1; }
[ -e results/androidworld/$NAME ] && { log "EXPORT FAILED (results/androidworld/$NAME already exists; refusing to mix runs)"; exit 1; }
[ -e "$GG" ] && { log "EXPORT FAILED ($GG already exists; refusing to reuse an unverified GGUF)"; exit 1; }
.venv-convert/bin/python - "$SRC" "$MAN" <<'PY' || { log "EXPORT FAILED (source dir does not match $MAN)"; exit 1; }
import hashlib, json, os, sys
src, man = sys.argv[1:3]
want = json.load(open(man))["files"]
have = sorted(os.listdir(src))
assert have == sorted(want), f"file set differs: extra {set(have) - set(want)}, missing {set(want) - set(have)}"
for f, h in want.items():
    d = hashlib.sha256()
    with open(os.path.join(src, f), "rb") as fh:
        for b in iter(lambda: fh.read(1 << 24), b""): d.update(b)
    assert d.hexdigest() == h, f"sha256 mismatch: {f}"
print("source dir matches the manifest:", len(want), "files")
PY
AD=$(.venv-convert/bin/python -c "
import json
from huggingface_hub import snapshot_download
m = json.load(open('$MAN'))
print(snapshot_download(m['adapter_repo'], revision=m['adapter_rev'], allow_patterns=['adapter_model.safetensors','adapter_config.json']))") \
  || { log "EXPORT FAILED (adapter download)"; exit 1; }
log "checking $SRC against base + $AD"
.venv-convert/bin/python scripts/publish/check_local_merge.py "$SRC" "$BASE" "$AD" || { log "EXPORT FAILED (merge check)"; exit 1; }
bash scripts/publish/local_export_gguf.sh "$SRC" "$OUT" || { log "EXPORT FAILED"; exit 1; }
[ -s "$GG" ] && [ -s "$MM" ] || { log "EXPORT FAILED (missing $GG)"; exit 1; }
shasum -a 256 "$GG" "$MM"
log "exported; pausing the sealed GUI-Owl seed-1234 arm on emulator $CP (scripts/androidworld/local_emu2_fill_v2.sh resumes it afterwards)"
t0=$(date +%s)
while pgrep -f "[r]un_aw.py.*console_port=$CP" >/dev/null || pgrep -f "^([^ ]*/)?bash ([^ ]*/)?scripts/(androidworld/)?local_sealed_aw(_v[23])?.sh guiowl 1234 $CP " >/dev/null \
      || pgrep -f "[l]lama-server.*--port 8115 " >/dev/null; do
  [ $(( $(date +%s) - t0 )) -gt 1800 ] && release "emulator $CP still busy after 30 min; v4 seed-30 run NOT STARTED"
  sleep 10
done
log "emulator $CP free (sealed arm launcher, runner and server gone)"
curl -s 127.0.0.1:$PORT/health | grep -q ok && release "port $PORT already serving another process; v4 seed-30 run NOT STARTED"
nohup llama-server -m $GG --mmproj $MM -c 8192 -np 1 -ngl 99 --image-max-tokens 1024 \
  --reasoning-format deepseek --port $PORT --host 127.0.0.1 > logs/llama_server_$NAME.log 2>&1 < /dev/null &
SP=$!
t0=$(date +%s)
until curl -s 127.0.0.1:$PORT/health | grep -q ok; do
  kill -0 $SP 2>/dev/null || release "llama-server exited during startup (see logs/llama_server_$NAME.log); v4 seed-30 run NOT STARTED"
  [ $(( $(date +%s) - t0 )) -gt 600 ] && release "llama-server not healthy after 600 s; v4 seed-30 run NOT STARTED"
  sleep 3
done
kill -0 $SP 2>/dev/null && pgrep -f "[l]lama-server.*--port $PORT " | grep -qx "$SP" || release "the server on :$PORT is not the one just started; NOT STARTED"
log "server :$PORT up (pid $SP, $GG); starting v4 seed-30 development pass on emulator $CP"
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=$CP --grpc_port=$GP --server_url=http://127.0.0.1:$PORT \
  --agent_label=lfm3vl2b_v4_q4km --enable_thinking=true --prompt_version=v4 --output_path=results/androidworld/$NAME 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" > logs/aw_run_$NAME.log
kill $SP 2>/dev/null
D=$(ls -d results/androidworld/$NAME/run_*/ 2>/dev/null | tail -1); D=${D%/}
N=$([ -n "$D" ] && ls "$D"/*.pkl.gz 2>/dev/null | wc -l | tr -d ' ' || echo 0)
[ "$N" = 116 ] && log "v4 seed-30 run complete: 116 episodes in $D" || log "v4 seed-30 run INCOMPLETE: $N/116 episodes in ${D:-none}"
log "v4 AndroidWorld seed-30 finished"
