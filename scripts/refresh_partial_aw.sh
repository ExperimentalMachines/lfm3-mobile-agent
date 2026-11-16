#!/bin/bash
# Refresh <label>.partial.summary.json + <label>.failure_modes.json for AndroidWorld runs still in progress (newest run dir).
cd "$(dirname "$0")/.."
for d in "$@"; do
  D=$(ls -d results/androidworld/$d/run_* 2>/dev/null | tail -1); [ -z "$D" ] && continue
  .venv-aw/bin/python eval/androidworld/summarize_aw.py "$D" --expected 116 --out results/androidworld/$d.partial.summary.json > /dev/null 2>&1
  .venv-aw/bin/python eval/androidworld/failure_modes.py "$D" --out results/androidworld/$d.failure_modes.json > /dev/null 2>&1
  python3 -c "import json;s=json.load(open('results/androidworld/$d.partial.summary.json'))['summary'];print('$d', s['n_episodes'], 'done,', round(s['success_rate']*116), 'successes')"
done
