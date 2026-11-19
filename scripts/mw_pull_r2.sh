#!/bin/bash
# Pull MobileWorld run 2 (GUI-Owl, v4 and MAI-UI-2B on the GCP env host) to results/mobileworld/traj_r2/ (git-ignored):
# every attempt folder (final, MobileWorld's own *_backup_* retries, and folders moved aside by mw_resume.sh), the retry
# manifests and the start/end stamps. --full also copies screenshots (needed for the trajectory review; ~6 GB).
# Usage: bash scripts/mw_pull_r2.sh [--full]
set -eu
cd "$(dirname "$0")/.."
source logs/gcp_mw_instance.env
DST=results/mobileworld/traj_r2
mkdir -p "$DST"
EX=(--exclude screenshots --exclude marked_screenshots)
[ "${1:-}" = --full ] && EX=()
rsync -a ${EX[@]+"${EX[@]}"} -e "ssh -o ConnectTimeout=15 -o BatchMode=yes -i $PEM" \
  "ubuntu@${IP}:traj_logs/guiowl_gui_en_r2" "ubuntu@${IP}:traj_logs/v4_gui_en_r2" "ubuntu@${IP}:traj_logs/maiui_gui_en_r2" \
  "ubuntu@${IP}:traj_logs/_interrupted" "$DST/"
rsync -a -e "ssh -o ConnectTimeout=15 -o BatchMode=yes -i $PEM" \
  --include '_retry_manifest_*.jsonl' --exclude '*' "ubuntu@${IP}:traj_logs/" "$DST/"
for f in go_r2.start go_r2.end v4_r2.start v4_r2.end guiowl_resume.start v4_resume.start guiowl_complete v4_complete \
         maiui_a_resume.start maiui_b_resume.start maiui_a_complete maiui_b_complete mw_gui_en_maiui_a.json mw_gui_en_maiui_b.json; do
  scp -q -o BatchMode=yes -i "$PEM" "ubuntu@${IP}:$f" "$DST/$f" 2>/dev/null || true
done
echo "pulled to $DST: $(du -sh "$DST" | cut -f1)"
