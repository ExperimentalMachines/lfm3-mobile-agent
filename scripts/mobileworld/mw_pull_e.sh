#!/bin/bash
# Pull E's MobileWorld run (docs/PREREG_v46.md 2026-11-25 20:40; AWS VM of scripts/mobileworld/aws_mw_e_setup.sh) to
# results/mobileworld/traj_e/: every attempt folder (final, MobileWorld's *_backup_* retries, folders moved aside by
# mw_resume.sh), the retry manifest and the stamps. --full adds screenshots. As scripts/mobileworld/mw_pull_r3.sh.
# Usage: bash scripts/mobileworld/mw_pull_e.sh [--full]
set -eu
cd "$(dirname "$0")/../.."
RUN=e; source logs/aws_mw_e.env
DST=results/mobileworld/traj_e
mkdir -p "$DST"
EX=(--exclude screenshots --exclude marked_screenshots)
[ "${1:-}" = --full ] && EX=()
R="ssh -o ConnectTimeout=15 -o BatchMode=yes -i $PEM"
rsync -a ${EX[@]+"${EX[@]}"} -e "$R" "ubuntu@${IP}:traj_logs/${RUN}_gui_en_r4" "$DST/"
rsync -a ${EX[@]+"${EX[@]}"} -e "$R" "ubuntu@${IP}:traj_logs/_interrupted/" "$DST/_interrupted/" 2>/dev/null || true
rsync -a -e "$R" --include "_retry_manifest_${RUN}.jsonl" --exclude '*' "ubuntu@${IP}:traj_logs/" "$DST/"
for f in ${RUN}_resume.start ${RUN}_complete; do scp -q -o BatchMode=yes -i "$PEM" "ubuntu@${IP}:$f" "$DST/$f" 2>/dev/null || true; done
echo "pulled to $DST: $(du -sh "$DST" | cut -f1)"
