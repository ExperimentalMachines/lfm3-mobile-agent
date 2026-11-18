#!/bin/bash
# One phone of the device-streaming speed benchmark (Firebase / Android Device Streaming, full crossover).
# Phone IDX runs all three models in rotated order (IDX 0: v4, guiowl, maiui; IDX 1: guiowl, maiui, v4; IDX 2: maiui, v4,
# guiowl), so every model is measured on every phone and in every position. Per model:
#   files -> phone (signed GCS URL with curl/wget on the phone, else adb push) + sha256 check against the Mac's copy;
#   llama.cpp b12110 Android arm64 `llama-server` ON THE PHONE (CPU, -t 4, -np 1, --cache-ram 0, model's eval flags);
#   adb forward -> recording proxy (every request/response fsync'ed) -> eval/mobileworld/bench_speed.py (same agent code,
#   same 5 screenshots/goals, 1 mirrored warm-up + 3 passes); server log pulled; files removed from the phone.
# A thermal/CPU-frequency sampler logs the phone every 10 s. Nothing needed for the analysis stays only on the phone.
# v3: the server is started by a Mac-side background `adb shell` (v1/v2 blocked forever: adb waits for the
# phone process even with nohup &), closed after each model; llama.cpp setup skipped if already on the phone.
# ORDER_OVERRIDE="maiui guiowl v4" sets the model order (pass 2 of the single-phone ABC/CBA design).
# Usage: bash scripts/devstream_device_v3.sh <adb-serial> <idx 0..2> <out-dir>
set -u
cd "$(dirname "$0")/.."
SER=$1; IDX=$2; OUT=$3; mkdir -p "$OUT"
A() { adb -s "$SER" "$@"; }
log() { echo "[$(date +%T)] dev$IDX $*" | tee -a "$OUT/worker.log"; }
B=$(cat logs/devstream_bucket.txt); SA=lfm3-devstream-signer@voltaic-psyche-514908-s2.iam.gserviceaccount.com
D=/data/local/tmp/lfm3bench
SHOTS=/private/tmp/claude-501/-Users-alpha-lfm3-android/4efa3977-532d-411f-ad28-f4737438aa00/scratchpad/bench_shots
AGENTS=eval/devicestream/agents
PY=tools/MobileWorld/.venv/bin/python
declare -a ORDER=(${ORDER_OVERRIDE:-v4 guiowl maiui})
MODELS=(); for k in 0 1 2; do MODELS+=("${ORDER[$(( (IDX + k) % 3 ))]}"); done
files_for() { case $1 in
  v4) echo "models/lfm3vl2b_v4-GGUF/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf" ;;
  guiowl) echo "models/GUI-Owl-1.5-2B-GGUF/GUI-Owl-1.5-2B-Instruct.Q4_K_M.gguf models/GUI-Owl-1.5-2B-GGUF/GUI-Owl-1.5-2B-Instruct.mmproj-Q8_0.gguf" ;;
  maiui) echo "models/MAI-UI-2B-GGUF/MAI-UI-2B-Q4_K_M.gguf models/MAI-UI-2B-GGUF/mmproj-MAI-UI-2B-Q8_0.gguf" ;;
esac; }
flags_for() { case $1 in
  v4) echo "-c 8192 --image-max-tokens 1024 --reasoning-format deepseek" ;;
  *) echo "-c 20480 --image-max-tokens 2600 --jinja" ;;
esac; }
agent_for() { case $1 in v4) echo lfm3 ;; guiowl) echo guiowl ;; maiui) echo maiui ;; esac; }
fetch() {  # local file -> $D/<basename>, verified
  local f=$1 b; b=$(basename "$f")
  local want; want=$(shasum -a 256 "$f" | cut -d' ' -f1)
  local url; url=$(gcloud storage sign-url "$B/$b" --impersonate-service-account="$SA" --duration=2h --region=us-central1 --format="value(signed_url)" 2>/dev/null | tail -1)
  if [ -n "$DL" ] && [ -n "$url" ]; then A shell "$DL '$D/$b' '$url'" > /dev/null 2>&1; fi
  local got; got=$(A shell "sha256sum $D/$b 2>/dev/null" | cut -d' ' -f1)
  if [ "$got" != "$want" ]; then
    log "  $b: download ${DL:+failed/mismatch}${DL:-tool missing}; adb push"
    A push "$f" "$D/$b" > /dev/null; got=$(A shell "sha256sum $D/$b" | cut -d' ' -f1)
  fi
  [ "$got" = "$want" ] || { log "  $b: SHA-256 MISMATCH on phone"; return 1; }
  log "  $b verified ($want)"
}
# ---- phone metadata + runtime
A shell "mkdir -p $D"
{ echo "{"; for k in ro.product.model ro.product.device ro.build.fingerprint ro.build.version.sdk ro.soc.model ro.soc.manufacturer; do
    echo "\"$k\": \"$(A shell getprop $k | tr -d '\r')\","; done
  echo "\"mem\": \"$(A shell 'grep MemTotal /proc/meminfo' | tr -s ' ' | tr -d '\r')\","
  echo "\"cpus\": \"$(A shell 'cat /sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_max_freq' | tr '\r\n' '  ')\","
  echo "\"serial\": \"$SER\", \"idx\": $IDX, \"order\": \"${MODELS[*]}\"}"; } > "$OUT/device.json"
log "phone: $(grep -o '"ro.product.model": "[^"]*"' "$OUT/device.json"), order ${MODELS[*]}"
DL=""
if A shell "command -v curl" | grep -q curl; then DL="curl -sfL -o"; elif A shell "command -v wget" | grep -q wget; then DL="wget -q -O"; fi
log "on-phone downloader: ${DL:-none (adb push)}"
if ! A shell "test -x $D/llama-b12110/llama-server && echo yes" | grep -q yes; then
  fetch tools/llama-android/llama-b12110-bin-android-arm64.tar.gz || exit 1
  A shell "cd $D && tar -xzf llama-b12110-bin-android-arm64.tar.gz && rm llama-b12110-bin-android-arm64.tar.gz && chmod 755 llama-b12110/*"
fi
A shell "cd $D/llama-b12110 && LD_LIBRARY_PATH=. ./llama-server --version" 2>&1 | tr -d '\r' | tee "$OUT/llama_version.txt" | tail -2
grep -q cd959bae9 "$OUT/llama_version.txt" || { log "llama.cpp on the phone is not cd959bae9"; exit 1; }
# ---- thermal / frequency sampler (Mac side; stops when the worker ends)
( while kill -0 $$ 2>/dev/null; do
    t=$(date +%s); bt=$(A shell "dumpsys battery | grep temperature" 2>/dev/null | tr -dc '0-9')
    ts=$(A shell "dumpsys thermalservice | grep -m1 'Thermal Status'" 2>/dev/null | tr -d '\r')
    fq=$(A shell "cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq" 2>/dev/null | tr '\r\n' '  ')
    echo "{\"t\": $t, \"battery_temp_dC\": \"$bt\", \"thermal\": \"$ts\", \"cur_freq_khz\": \"$fq\"}" >> "$OUT/thermal.jsonl"
    sleep 10
  done ) &
SAMP=$!
LPORT=$((18200 + IDX)); PPORT=$((18300 + IDX))
for m in "${MODELS[@]}"; do
  log "== $m"
  set -- $(files_for $m); MF=$1; PF=$2
  fetch "$MF" && fetch "$PF" || { log "$m: files not verified; skipping"; continue; }
  A shell "cd $D/llama-b12110 && LD_LIBRARY_PATH=. exec ./llama-server -m $D/$(basename $MF) --mmproj $D/$(basename $PF) $(flags_for $m) -np 1 -t 4 --cache-ram 0 --host 127.0.0.1 --port 8080 > $D/server_$m.log 2>&1" < /dev/null > /dev/null 2>&1 &
  SRVC=$!   # Mac-side adb client holding the phone server; ends when the server is killed below
  A forward tcp:$LPORT tcp:8080 > /dev/null
  t0=$(date +%s); ok=0
  while [ $(( $(date +%s) - t0 )) -lt 600 ]; do curl -s --max-time 5 127.0.0.1:$LPORT/health | grep -q ok && { ok=1; break; }; sleep 3; done
  [ $ok = 1 ] || { log "$m: server not healthy on the phone"; A pull $D/server_$m.log "$OUT/server_$m.log" > /dev/null 2>&1
                   A shell "pkill -f llama-server" > /dev/null 2>&1; A forward --remove tcp:$LPORT > /dev/null 2>&1; kill $SRVC 2>/dev/null; continue; }
  log "$m: server up on the phone"
  $PY eval/devicestream/record_proxy.py --listen $PPORT --upstream http://127.0.0.1:$LPORT --log "$OUT/requests_$m.jsonl" --device "dev$IDX" --model $m &
  PROXY=$!; sleep 2
  (cd tools/MobileWorld && .venv/bin/python ../../eval/mobileworld/bench_speed.py --agent $(agent_for $m) --url http://127.0.0.1:$PPORT/v1 \
     --shots "$SHOTS" --reps 3 --out "../../$OUT/bench_$m.json" --jsonl "../../$OUT/bench_$m.jsonl" --mirror_warmup \
     --agent_dir ../../$AGENTS) > "$OUT/client_$m.log" 2>&1
  log "$m: bench exit $? ($(wc -l < "$OUT/requests_$m.jsonl" 2>/dev/null | tr -d ' ') recorded requests)"
  A pull $D/server_$m.log "$OUT/server_$m.log" > /dev/null 2>&1
  A shell "pkill -f llama-server" > /dev/null 2>&1; kill $PROXY 2>/dev/null; A forward --remove tcp:$LPORT > /dev/null 2>&1
  sleep 2; kill $SRVC 2>/dev/null; wait $SRVC 2>/dev/null
  A shell "rm -f $D/$(basename $MF) $D/$(basename $PF)"
done
kill $SAMP 2>/dev/null
log "WORKER DONE"
