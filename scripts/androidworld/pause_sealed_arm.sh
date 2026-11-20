#!/bin/bash
# Pause one sealed AndroidWorld arm so its emulator can be used, keeping its results resumable (AW checkpoint dir).
# Kills ONLY (allowlist): the arm's launcher `bash scripts/(androidworld/)local_sealed_aw[_v2|_v3].sh <arm> <seed> <cp> <gp> <server_port>`,
# its run_aw.py (identified by its server URL port and --output_path=results/androidworld_sealed/<arm>_seed<seed>), and the
# llama-server on <server_port>. Exits non-zero if nothing matches, a kill fails, or a process is still alive after 30 s.
# Usage: bash scripts/androidworld/pause_sealed_arm.sh <arm> <seed> <server_port> [--dry-run]
set -u
ARM=$1; SEED=$2; PORT=$3; DRY=${4:-}
L=$(pgrep -f "^([^ ]*/)?bash ([^ ]*/)?scripts/(androidworld/)?local_sealed_aw(_v[23])?[.]sh $ARM $SEED [0-9]+ [0-9]+ $PORT( |$)")
R=$(pgrep -f "[r]un_aw.py.*--server_url=http://127.0.0.1:$PORT .*--output_path=results/androidworld_sealed/${ARM}_seed${SEED}( |$)")
S=$(pgrep -f "[l]lama-server.*--port $PORT( |$)")
echo "launcher: ${L:-none} run_aw: ${R:-none} server: ${S:-none}"
[ "$DRY" = "--dry-run" ] && exit 0
[ -n "$L$R" ] || { echo "nothing to pause: no launcher or runner for ${ARM}_seed${SEED} on server port $PORT"; exit 1; }
# alive PID: true unless the process is confirmed gone ("No such process"); permission errors count as alive
alive() { local e; e=$(kill -0 "$1" 2>&1) && return 0; case "$e" in *"No such process"*) return 1 ;; *) return 0 ;; esac; }
still_alive() { local a="" p; for p in $L $R $S; do alive "$p" && a="$a $p"; done; echo "$a"; }
for p in $L $R $S; do kill "$p" 2>/dev/null || ! alive "$p" || { echo "kill $p failed"; exit 1; }; done
for _ in $(seq 30); do [ -z "$(still_alive)" ] && break; sleep 1; done  # bounded wait before the caller may resume
left=$(still_alive)  # re-checked after the last wait
[ -z "$left" ] || { echo "still running after 30 s:$left; NOT paused"; exit 1; }
D=$(ls -d results/androidworld_sealed/${ARM}_seed${SEED}/run_*/ 2>/dev/null | tail -1); D=${D%/}
echo "paused; resume dir: $D ($(ls $D/*.pkl.gz 2>/dev/null | wc -l | tr -d ' ') episodes saved)"
