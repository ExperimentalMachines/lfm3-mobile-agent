#!/bin/bash
# Pause one sealed AndroidWorld arm so its emulator can be used, keeping its results resumable (AW checkpoint dir).
# Kills ONLY (allowlist): the arm's launcher `bash scripts/local_sealed_aw[_v2].sh <arm> <seed> ...`, its run_aw.py
# (identified by --output_path=results/androidworld_sealed/<arm>_seed<seed>), and the llama-server on <server_port>.
# Usage: bash scripts/pause_sealed_arm.sh <arm> <seed> <server_port> [--dry-run]
set -u
ARM=$1; SEED=$2; PORT=$3; DRY=${4:-}
L=$(pgrep -f "^bash scripts/local_sealed_aw(_v2)?.sh $ARM $SEED ")
R=$(pgrep -f "[r]un_aw.py.*--output_path=results/androidworld_sealed/${ARM}_seed${SEED} ")
S=$(pgrep -f "[l]lama-server.*--port $PORT ")
echo "launcher: ${L:-none} run_aw: ${R:-none} server: ${S:-none}"
[ "$DRY" = "--dry-run" ] && exit 0
for p in $L $R $S; do kill "$p"; done
sleep 5
D=$(ls -d results/androidworld_sealed/${ARM}_seed${SEED}/run_* 2>/dev/null | tail -1)
echo "paused; resume dir: $D ($(ls $D/*.pkl.gz 2>/dev/null | wc -l | tr -d ' ') episodes saved)"
