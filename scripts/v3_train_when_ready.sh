#!/bin/bash
# Wait for alpharomercoma/AndroidAgent-SFT-v3 (stats file is uploaded last), pin its revision in the LFM3 v3 job,
# then get a G4 on the main account (adopting it if the CLI times out after assignment), bootstrap and launch.
set -u
cd /Users/alpha/lfm3-android
REPO=alpharomercoma/AndroidAgent-SFT-v3
until REV=$(uvx --from huggingface_hub python -c "
from huggingface_hub import HfApi; import sys
a=HfApi(); fs=a.list_repo_files('$REPO', repo_type='dataset')
sys.exit(1) if 'stats/v3_intents.json' not in fs else print(a.dataset_info('$REPO').sha)" 2>/dev/null); do sleep 120; done
echo "[$(date +%T)] v3 data ready @ $REV"
python3 - "$REV" <<'PY'
import json, sys
rev = sys.argv[1]
j = json.load(open("scripts/jobs/lfm3_v2mix_g4_personal.json")); e = j[0]["env"]
e.update({"RUN": "lfm3vl2b-v3mix-lora", "TRAIN_DATA": f"alpharomercoma/AndroidAgent-SFT-v3@train#{rev}",
          "FINAL_REPO": "alpharomercoma/LFM3-VL-2B-AndroidAgent-v3", "CKPT_REPO": "alpharomercoma/LFM3-VL-2B-AndroidAgent-v3-LoRA-ckpt",
          "DEV_REPO": "experimentalmachines/AndroidAgent-SFT-v2", "DEV_REV": "42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a",
          "DEV_MODELS": "FT=lfm3_v3:1", "LOGPROB_FT": "1", "MATCHED_NOTHINK": "0"})
j[0]["name"] = "lfm3_v3mix"; j[0]["log"] = "/content/runs/lfm3_v3mix_pipeline.log"
json.dump(j, open("scripts/jobs/lfm3_v3mix_g4.json", "w"), indent=1); print("job pinned", e["TRAIN_DATA"])
PY
for i in 1 2 3 4; do
  perl -e 'alarm shift; exec @ARGV' 420 colab new -s g4 --gpu G4 < /dev/null 2>&1 | tail -1
  colab sessions < /dev/null 2>&1 | grep -q "\[g4\]" && break
  ~/.local/share/uv/tools/google-colab-cli/bin/python3 - <<'PY'
from colab_cli.common import state
from colab_cli.state import SessionState
for a in state.client.list_assignments():
    if "g4" in a.endpoint:
        state.store.add(SessionState(name="g4", token=a.runtime_proxy_info.token, url=a.runtime_proxy_info.url, endpoint=a.endpoint,
                                     token_expires_at=a.runtime_proxy_info.expires_at(), variant="GPU", accelerator="G4", machine_shape="STANDARD"))
        print("adopted", a.endpoint)
PY
  colab sessions < /dev/null 2>&1 | grep -q "\[g4\]" && break
  echo "[$(date +%T)] G4 attempt $i failed"; sleep 60
done
colab sessions < /dev/null 2>&1 | grep -q "\[g4\]" || { echo "NO G4"; exit 1; }
bash scripts/gpu_session.sh g4 2>&1 | grep -E "versions|HF user|pip rc|Error" | tail -4
bash scripts/launch_on_session.sh g4 scripts/jobs/lfm3_v3mix_g4.json
