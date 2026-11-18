#!/bin/bash
# Refresh the run-log repo (github.com/alpharomercoma/lfm3-android-runs, private) from this repo's result files:
# registry + tables -> rendered docs -> copies of key results -> commit + push (HTTPS with the gh credential helper).
# A MobileWorld snapshot is taken first if the instances are up (skipped otherwise). Usage: bash scripts/update_runs_docs.sh
set -eu
cd "$(dirname "$0")/.."
R=${RUNS_REPO:-$HOME/lfm3-android-runs}
.venv-aw/bin/python scripts/build_runs_registry.py "$R" --mw results/mobileworld/snapshot.json
cp scripts/build_runs_registry.py "$R/data/"
cp results/speed/speed_t8.md results/speed/speed_t8.json results/v4_gate_seed30.txt results/v4rl_promotion_offline.json \
   results/v4_local_export_manifest.json results/v4rl_local_export_manifest.json results/mobileworld/snapshot.json "$R/results/"
cp docs/PREREG_v4.md "$R/docs/"
for f in results/qdc/speed_qdc_v6.md results/qdc/speed_qdc_v6.json results/sealed_analysis_seed7_prelim.md results/sealed_analysis_seed7_prelim.json \
         results/sealed_analysis_seed7.md results/sealed_analysis_seed7.json results/mobileworld/v4_gui_en_summary.json \
         results/mobileworld/mw_r2_comparison.md results/mobileworld/mw_r2_comparison.json results/mobileworld/guiowl_gui_en_r2_summary.json \
         results/mobileworld/v4_gui_en_r2_summary.json; do
  [ -f "$f" ] && cp "$f" "$R/results/"
done
python3 "$R/data/render_docs.py"
python3 scripts/gen_timeline_audits.py "$R"
cp scripts/gen_timeline_audits.py "$R/data/"
( cd "$R" && grep -rlE "hf_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|PRIVATE KEY" . --exclude-dir=.git && { echo "secret-like string found; not pushing"; exit 1; } || true
  git add -A && git commit -q -m "Refresh run log ($(date '+%Y-%m-%d %H:%M'))" && \
  git -c credential.helper= -c credential.helper='!gh auth git-credential' push -q origin main && git log --oneline -1 )
