#!/bin/bash
# Wait for the 0.8B's next hub checkpoint, release its L4 (second account, via the remote host), resume it on the main-account G4.
set -u
cd "$(dirname "$0")/../.." || exit 1
S=/private/tmp/claude-501/-Users-alpha-lfm3-android/4efa3977-532d-411f-ad28-f4737438aa00/scratchpad
WANT=${1:-1150}
until [ "$(uvx --from huggingface_hub python -c "
from huggingface_hub import hf_hub_download; import json
print(json.load(open(hf_hub_download('experimentalmachines/Qwen3.5-0.8B-AndroidControl-LoRA-ckpt','last-checkpoint/trainer_state.json')))['global_step'])" 2>/dev/null)" -ge "$WANT" ]; do sleep 30; done
echo "[$(date +%T)] hub checkpoint >= $WANT; stopping the L4 session"
SSHPASS=$SSHPASS $S/rssh.exp 'cd ~/vl; ./colabw stop -s lfm25l4 < /dev/null 2>&1 | tail -1' 2>&1 | grep -v passphrase
cat > /tmp/seed_eval_q08_$$.py <<'PY'
import os
from huggingface_hub import HfApi, hf_hub_download
tok = open("/content/.hf_token").read().strip()
repo = "experimentalmachines/Qwen3.5-0.8B-AndroidControl"
for f in [f for f in HfApi(token=tok).list_repo_files(repo) if f.startswith("eval/")]:
    hf_hub_download(repo, f, local_dir="/content", token=tok)
print("seeded", sorted(x for x in os.listdir("/content/eval") if "08b" in x or "450m" in x))
PY
colab exec -s g4 -f /tmp/seed_eval_q08_$$.py < /dev/null 2>&1 | grep -E "seeded|Error"; rm -f /tmp/seed_eval_q08_$$.py
bash scripts/training/launch_on_session.sh g4 scripts/training/jobs/qwen35_08b_g4.json
