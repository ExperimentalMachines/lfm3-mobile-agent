#!/bin/bash
# Regenerate the summary files listed in OUTPUTS below from the committed inputs (episode files, request logs, predictions and
# per-run metric files), then check each output against the committed version (expected: no change, nothing new).
# Not covered: re-scoring raw AndroidControl / general-knowledge predictions into their metric files (eval/ scorers),
# training logs, dataset statistics, and the hand-written docs. MobileWorld is skipped unless its raw trajectories
# (not in git) are present. Needs Python 3.10+ with numpy.
# Usage: bash analysis/reproduce.sh            (PY=/path/to/python to choose the interpreter)
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-python3}
E=results/v4_dev/hub/eval
D=results/devstream/run_20261118_1519
run() { echo "· $*"; "$@" > /dev/null; }
OUTPUTS=(results/sealed_analysis_final.json results/sealed_analysis_final.md results/sealed_sensitivity_final.json
  results/sealed_sensitivity_final.md results/androidworld/dev_seed30_summary.json results/androidworld/dev_seed30_summary.md
  results/v4_gate_seed30.txt results/v4_dev/lfm3_v4_strict.json results/v4rl_promotion_offline.json
  results/general/lfm3vl2b_v4_retention_logprob.json results/SUMMARY.md results/V2_COMPARISON.md
  results/speed/speed_t8.json results/speed/speed_t8.md results/qdc/speed_qdc_v6.json results/qdc/speed_qdc_v6.md
  $D/speed_phone_partial.json $D/speed_phone_partial.md)
MW_OUTPUTS=(results/mobileworld/mw_r2_comparison.json results/mobileworld/mw_r2_comparison.md
  results/mobileworld/v4_gui_en_r2_summary.json results/mobileworld/guiowl_gui_en_r2_summary.json
  results/mobileworld/maiui_gui_en_r2_summary.json)
untracked() { git ls-files --others --exclude-standard -- results | sort; }
BEFORE=$(untracked)

echo "AndroidWorld, held-out (primary) + sensitivity"
run "$PY" analysis/sealed_analysis.py --seeds 7,1234,2026 --out results/sealed_analysis_final
run "$PY" analysis/sealed_sensitivity.py
echo "AndroidWorld, development seed 30 + v4 gate"
run "$PY" analysis/aw_dev_seed30.py
echo "· analysis/main_gate.py > results/v4_gate_seed30.txt"
"$PY" analysis/main_gate.py --v4 results/androidworld/lfm3vl2b_v4 --v4_agent lfm3vl2b_v4_q4km \
  --dev_answer $E/lfm3_v4_dev_answer.jsonl --dev_complete $E/lfm3_v4_dev_complete.jsonl > results/v4_gate_seed30.txt
echo "Offline evaluations"
run "$PY" analysis/strict_dev_metrics.py --answer $E/lfm3_v4_dev_answer.jsonl --complete $E/lfm3_v4_dev_complete.jsonl \
  --out results/v4_dev/lfm3_v4_strict.json
run "$PY" analysis/grpo_promotion.py --v4_dir $E --rl_dir results/v4rl_dev --out results/v4rl_promotion_offline.json
run "$PY" eval/general/paired_retention.py results/general/lfm3vl2b-ac-lora_base_general_logprob.jsonl \
  $E/lfm3vl2b-v4bmix-lora_ft_general_logprob.jsonl results/general/lfm3vl2b_v4_retention_logprob.json
run "$PY" analysis/build_report.py
echo "· analysis/multisource_vs_androidcontrolonly.py > results/V2_COMPARISON.md"
"$PY" analysis/multisource_vs_androidcontrolonly.py > results/V2_COMPARISON.md
echo "Speed"
echo "· analysis/bench_speed_report.py > results/speed/speed_t8.json (+ .md)"
"$PY" analysis/bench_speed_report.py results/speed/results_t8 --md results/speed/speed_t8.md > results/speed/speed_t8.json
run "$PY" analysis/qdc_report.py
run "$PY" analysis/devstream_report.py $D --md $D/speed_phone_partial.md --json $D/speed_phone_partial.json
echo "MobileWorld"
if [ -d results/mobileworld/traj_r2 ]; then
  run "$PY" analysis/mw_summarize_r2.py
  OUTPUTS+=("${MW_OUTPUTS[@]}")
else
  echo "· skipped: raw trajectories (results/mobileworld/traj_r2, 8.6 GB) are not in git"
fi
find analysis -name __pycache__ -type d -prune -exec rm -rf {} +
echo
fail=0
for f in "${OUTPUTS[@]}"; do git ls-files --error-unmatch -- "$f" > /dev/null 2>&1 || { echo "not committed: $f"; fail=1; }; done
git diff --quiet HEAD -- "${OUTPUTS[@]}" || { echo "Differs from HEAD:"; git diff --stat HEAD -- "${OUTPUTS[@]}"; fail=1; }
NEW=$(comm -13 <(echo "$BEFORE") <(untracked))
[ -z "$NEW" ] || { echo "New files the scripts wrote under results/:"; echo "$NEW"; fail=1; }
if [ $fail -eq 0 ]; then
  echo "OK: all ${#OUTPUTS[@]} regenerated files are identical to the committed ones (HEAD), and no new file appeared."
else
  exit 1
fi
