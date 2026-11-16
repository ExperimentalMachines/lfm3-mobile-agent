#!/bin/bash
# Local watcher: when the base-model offline eval on L4 session lfm3l4e finishes, download its outputs,
# release the L4, then retry A100 (then G4) in the freed session slot.
set -u
S=/private/tmp/claude-501/-Users-alpha-lfm3-android/4efa3977-532d-411f-ad28-f4737438aa00/scratchpad
cd /Users/alpha/lfm3-android
mkdir -p results/androidcontrol
while true; do
  "$S/cl4e" download -s lfm3l4e /content/work/jobs_status.json "$S/l4e_status.json" >/dev/null 2>&1
  if grep -q '"exit' "$S/l4e_status.json" 2>/dev/null && ! grep -q '"running"' "$S/l4e_status.json"; then break; fi
  sleep 120
done
echo "[$(date +%T)] base eval finished: $(cat $S/l4e_status.json)"
for f in lfm3vl2b_base_nothink.jsonl lfm3vl2b_base_nothink.metrics.json lfm3vl2b_base_nothink.jsonl.manifest.json lfm3_base_eval.log; do
  "$S/cl4e" download -s lfm3l4e "/content/eval/$f" "results/androidcontrol/$f" 2>&1 | tail -1
done
"$S/cl4e" stop -s lfm3l4e 2>&1 | tail -1
echo "[$(date +%T)] base eval collected; L4 released"
