#!/bin/bash
# Re-run only the episodes of a finished AndroidWorld pass that ended in a harness exception (task setup or checker
# crashed, e.g. a gRPC fork log line mixed into adb output that the SMS validator parses). Same model, flags and
# emulator as the pass; the errored episodes are kept under _harness_errors_first_pass/ for the record, and gRPC
# logging is silenced before Python starts (run_aw.py sets GRPC_VERBOSITY only after gRPC is imported).
# Usage: scripts/androidworld/rerun_harness_errors.sh <run name, e.g. lfm3vl2b_v46e> <gguf> <console port> <server port> [extra run_aw flags...]
set -u
cd "$(dirname "$0")/../.." || exit 1
NAME=$1; GG=$2; CP=$3; PORT=$4; shift 4
export ANDROID_SDK_ROOT=/opt/homebrew/share/android-commandlinetools JAVA_HOME=/opt/homebrew/opt/openjdk@17
GP=$((CP + 3000)); AVD=AndroidWorldAvd; EXTRA="-partition-size 3072"; [ "$CP" = 5558 ] && { AVD=AndroidWorldAvd2; EXTRA=""; }
MM=models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf
D=$(ls -d results/androidworld/$NAME/run_*/ | tail -1); D=${D%/}
log() { echo "[$(date +%T)] rerun $NAME: $*"; }
# AndroidWorld episode pickles are written by our own local harness (trusted local files).
TASKS=$(.venv-aw/bin/python - "$D" <<'PY'
import glob, gzip, os, pickle, sys
print(",".join(sorted(os.path.basename(f)[:-len("_0.pkl.gz")] for f in glob.glob(sys.argv[1] + "/*.pkl.gz")
                      if pickle.load(gzip.open(f))[0].get("exception_info") is not None)))
PY
)
[ -n "$TASKS" ] || { log "no harness errors in $D"; exit 0; }
log "tasks with harness errors: $TASKS"
mkdir -p "$D/_harness_errors_first_pass"
for t in ${TASKS//,/ }; do cp "$D/${t}_0.pkl.gz" "$D/_harness_errors_first_pass/"; done
adb -s emulator-$CP emu kill > /dev/null 2>&1; sleep 10
nohup "$ANDROID_SDK_ROOT/emulator/emulator" -avd "$AVD" -port "$CP" -grpc "$GP" -no-snapshot -no-window -no-audio \
  -no-boot-anim -gpu swiftshader_indirect $EXTRA > "logs/emulator_rerun_$CP.log" 2>&1 < /dev/null &
t0=$(date +%s); until [ "$(adb -s emulator-$CP shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]; do
  [ $(( $(date +%s) - t0 )) -gt 600 ] && { log "emulator did not boot"; exit 1; }; sleep 5; done; sleep 20
nohup llama-server -m "$GG" --mmproj "$MM" -c 8192 -np 1 -ngl 99 --image-max-tokens 1024 --reasoning-format deepseek \
  --port $PORT --host 127.0.0.1 > "logs/llama_server_rerun_$NAME.log" 2>&1 < /dev/null &
SP=$!; until curl -s 127.0.0.1:$PORT/health | grep -q ok; do sleep 2; kill -0 $SP 2>/dev/null || { log "server died"; exit 1; }; done
log "emulator and server up; re-running"
GRPC_VERBOSITY=NONE GRPC_ENABLE_FORK_SUPPORT=0 .venv-aw/bin/python eval/androidworld/run_aw.py --console_port=$CP --grpc_port=$GP \
  --server_url=http://127.0.0.1:$PORT --agent_label=${NAME}_q4km --enable_thinking=true --prompt_version=v4 --guards=false "$@" \
  --output_path=results/androidworld/$NAME --checkpoint_dir="$D" --retry_failed_on_resume=true --tasks="$TASKS" 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" >> "logs/aw_run_${NAME}_rerun.log"
kill $SP 2>/dev/null
log "done: $(.venv-aw/bin/python - "$D" "$TASKS" <<'PY'
import gzip, pickle, sys
for t in sys.argv[2].split(","):
    d = pickle.load(gzip.open(f"{sys.argv[1]}/{t}_0.pkl.gz"))[0]
    print(t, "success" if d["is_successful"] == 1 else "fail", "STILL-ERROR" if d.get("exception_info") is not None else "", end="; ")
PY
)"
