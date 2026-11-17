#!/bin/bash
# Modal H100: (1) teacher-fill v3 intents -> push dataset; (2) pin its revision; (3) LFM3-VL-2B v3 training + evals.
set -u
cd /Users/alpha/lfm3-android
M="uvx --from modal modal"
echo "[$(date +%T)] labeling on Modal H100"
$M run scripts/modal_app.py --job scripts/jobs/v3_intents.intents.json > logs/modal_v3_intents.log 2>&1
grep -a "exit:" logs/modal_v3_intents.log | tail -1
REV=$(uvx --from huggingface_hub python -c "
from huggingface_hub import HfApi; import sys
a=HfApi(); fs=a.list_repo_files('alpharomercoma/AndroidAgent-SFT-v3', repo_type='dataset')
sys.exit(1) if 'stats/v3_intents.json' not in fs else print(a.dataset_info('alpharomercoma/AndroidAgent-SFT-v3').sha)" 2>/dev/null) || { echo "v3 DATA MISSING"; exit 1; }
echo "[$(date +%T)] v3 data @ $REV"
python3 - "$REV" <<'PY'
import json, sys
rev = sys.argv[1]
j = json.load(open("scripts/jobs/lfm3_v2mix_g4_personal.json")); e = j[0]["env"]
e.update({"RUN": "lfm3vl2b-v3mix-lora", "TRAIN_DATA": f"alpharomercoma/AndroidAgent-SFT-v3@train#{rev}",
          "FINAL_REPO": "alpharomercoma/LFM3-VL-2B-AndroidAgent-v3", "CKPT_REPO": "alpharomercoma/LFM3-VL-2B-AndroidAgent-v3-LoRA-ckpt",
          "DEV_REPO": "experimentalmachines/AndroidAgent-SFT-v2", "DEV_REV": "42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a",
          "DEV_MODELS": "FT=lfm3_v3:1", "LOGPROB_FT": "1", "MATCHED_NOTHINK": "0", "WORKERS": "12"})
j[0]["name"] = "lfm3_v3mix"
json.dump(j, open("scripts/jobs/lfm3_v3mix_modal.json", "w"), indent=1); print("pinned", e["TRAIN_DATA"])
PY
echo "[$(date +%T)] v3 training on Modal H100"
$M run --detach scripts/modal_app.py --job scripts/jobs/lfm3_v3mix_modal.json --gpu h100 > logs/modal_lfm3_v3.log 2>&1 &
sleep 120
# detached: survives a local reboot; completion = the last eval artifacts on the hub
until uvx --from huggingface_hub python -c "
from huggingface_hub import HfApi; import sys
fs=HfApi().list_repo_files('alpharomercoma/LFM3-VL-2B-AndroidAgent-v3')
sys.exit(0 if all(f in fs for f in ('eval/lfm3_v3_dev_screenqa.metrics.json','eval/lfm3vl2b-v3mix-lora_ft_general_logprob.summary.json','eval/lfm3vl2b-v3mix-lora_ft.metrics.json')) else 1)" 2>/dev/null; do sleep 180; done
echo "[$(date +%T)] chain done"
