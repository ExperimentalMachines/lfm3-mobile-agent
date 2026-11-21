#!/bin/bash
# Pull the v4.1 follow-up MobileWorld run (run 3) to results/mobileworld/traj_r3/: every attempt folder (final, MobileWorld's
# *_backup_* retries, folders moved aside by mw_resume.sh), the retry manifest and the stamps. --full adds screenshots.
# Usage: bash scripts/mobileworld/mw_pull_r3.sh v4g|v41|v41g|v42g|v42 [--full]
set -eu
cd "$(dirname "$0")/../.."
RUN=${1:?}; source logs/gcp_mw_instance.env
DST=results/mobileworld/traj_r3
mkdir -p "$DST"
EX=(--exclude screenshots --exclude marked_screenshots)
[ "${2:-}" = --full ] && EX=()
R="ssh -o ConnectTimeout=15 -o BatchMode=yes -i $PEM"
rsync -a ${EX[@]+"${EX[@]}"} -e "$R" "ubuntu@${IP}:traj_logs/${RUN}_gui_en_r3" "$DST/"
rsync -a ${EX[@]+"${EX[@]}"} -e "$R" "ubuntu@${IP}:traj_logs/_interrupted/" "$DST/_interrupted/" 2>/dev/null || true
rsync -a -e "$R" --include "_retry_manifest_${RUN}.jsonl" --exclude '*' "ubuntu@${IP}:traj_logs/" "$DST/"
for f in ${RUN}_resume.start ${RUN}_complete; do scp -q -o BatchMode=yes -i "$PEM" "ubuntu@${IP}:$f" "$DST/$f" 2>/dev/null || true; done
echo "pulled to $DST: $(du -sh "$DST" | cut -f1)"
