#!/bin/bash
# Overnight: every 30 min refresh the live MobileWorld counts and the QDC phone report, rebuild + push the run-log docs,
# and commit those result files here. Stops when logs/docs_refresh_stop exists or after 16 h.
cd "$(dirname "$0")/.."
end=$(( $(date +%s) + 16 * 3600 ))
while [ ! -f logs/docs_refresh_stop ] && [ $(date +%s) -lt $end ]; do
  bash scripts/mw_snapshot_r2.sh > /dev/null 2>&1
  python3 scripts/qdc_report_v6.py > /dev/null 2>&1
  bash scripts/update_runs_docs.sh 2>&1 | tail -1 | sed "s/^/[$(date +%T)] docs: /"
  git add results/mobileworld/snapshot.json results/qdc/speed_qdc_v6.md results/qdc/speed_qdc_v6.json > /dev/null 2>&1 && \
    git commit -q -m "Live snapshot: MobileWorld counts, QDC phone report ($(date '+%H:%M'))

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" > /dev/null 2>&1
  sleep 1800
done
echo "[$(date +%T)] docs refresh loop exiting"
