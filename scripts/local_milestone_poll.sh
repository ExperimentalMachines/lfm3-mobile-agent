#!/bin/bash
# One line per state change: hub checkpoint step per model, final-model uploads, Modal app states, local GUI-Owl AW run.
S=/private/tmp/claude-501/-Users-alpha-lfm3-android/4efa3977-532d-411f-ad28-f4737438aa00/scratchpad
cd /Users/alpha/lfm3-android
STATE=$S/milestone_state; mkdir -p "$STATE"
emit() { local f="$STATE/$1"; [ "$(cat "$f" 2>/dev/null)" != "$2" ] && { echo "[$(date +%H:%M)] $1: $2"; printf '%s' "$2" > "$f"; }; return 0; }
while true; do
  st=$(uvx --from huggingface_hub python - 2>/dev/null <<'PY'
import json
from huggingface_hub import HfApi, hf_hub_download
api = HfApi()
for name, ck, final in [("lfm3", "LFM3-VL-2B-AndroidControl-LoRA-ckpt", "LFM3-VL-2B-AndroidControl"),
                        ("450m", "LFM2.5-VL-450M-AndroidControl-LoRA-ckpt", "LFM2.5-VL-450M-AndroidControl"),
                        ("qwen2b", "Qwen3.5-2B-AndroidControl-LoRA-ckpt", "Qwen3.5-2B-AndroidControl"),
                        ("qwen08b", "Qwen3.5-0.8B-AndroidControl-LoRA-ckpt", "Qwen3.5-0.8B-AndroidControl")]:
    try:
        s = json.load(open(hf_hub_download("experimentalmachines/" + ck, "last-checkpoint/trainer_state.json", force_download=True)))
        step = f"step {s['global_step']}/{s['max_steps']}"
    except Exception:
        step = "no ckpt yet"
    try:
        fs = api.list_repo_files("experimentalmachines/" + final)
        fin = "merged uploaded" if "config.json" in fs else ("evals:" + str(sum(f.startswith("eval/") for f in fs)))
    except Exception:
        fin = "-"
    print(f"{name}|{step}|{fin}")
PY
)
  echo "$st" | while IFS='|' read -r n step fin; do [ -n "$n" ] && emit "$n" "$step; $fin"; done
  emit modal "$(uvx --from modal modal app list --json 2>/dev/null | python3 -c "import json,sys;d=[x for x in json.load(sys.stdin) if x['description']=='lfm3-android'];print('running:',sum('ephemeral' in x['state'] or 'deployed' in x['state'] for x in d))" 2>/dev/null)"
  if ! pgrep -f "run_aw.py --agent=guiowl --guiowl_images=1" >/dev/null; then emit guiowl "AW run finished/stopped"; fi
  sleep 300
done
