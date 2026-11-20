"""Publish v4 and v4-RL to PRIVATE repos in the experimentalmachines org (2026-11-18, after AndroidAgent-SFT-v2 was made
public and freed ~31 GB of private storage). Uploads the verified local copies (manifests in results/), not VM files.
  experimentalmachines/LFM3-VL-2B-AndroidAgent-v4        merged weights + lora_adapter/ (hub ckpt @58bcb65) + eval/ + manifest
  experimentalmachines/LFM3-VL-2B-AndroidAgent-v4-GGUF   Q4_K_M + base Q8_0 mmproj (the files used on AndroidWorld/MobileWorld)
  experimentalmachines/LFM3-VL-2B-AndroidAgent-v4-RL     merged weights + lora_adapter/ (GRPO r16) + eval/ + manifest (NOT promoted)
  experimentalmachines/LFM3-VL-2B-AndroidAgent-v4-RL-GGUF
Usage: .venv-convert/bin/python scripts/publish/hf_publish_v4.py
"""
import glob
import json
import os
import shutil
import tempfile

from huggingface_hub import HfApi, snapshot_download

api = HfApi()
ORG = "experimentalmachines"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

CARD = """---
license: other
base_model: LiquidAI/LFM3-VL-2B
tags: [android, gui-agent, screen-agent, lfm3-vl]
---
# {name}

{what}

* Base: `LiquidAI/LFM3-VL-2B` @ 23387beda4; LoRA r64/a128 on the language model only (vision tower untouched).
* Training data: `alpharomercoma/AndroidAgent-SFT-v4` @ 337553984e (private); no AndroidWorld tasks, variants,
  trajectories or checkers.
* Prompt: agent_format v4 (system prompt with answer-vs-complete rules + the device's installed-app list); one
  screenshot per step; output = `<think>intent</think>` + one JSON action.
* Provenance: `{manifest}` lists the sha256 of every file here and how the weights were verified
  (bf16(base + scale*B@A) within 1 ulp against the adapter on the hub).
{extra}
Private research artifact (lfm3-android). Licence of the base model applies.
"""


def push(repo, folder, msg):
    api.create_repo(repo, private=True, exist_ok=True)
    assert api.model_info(repo).private, f"{repo} is not private"
    api.upload_folder(folder_path=folder, repo_id=repo, commit_message=msg)
    print("pushed", repo, flush=True)


def stage(files: dict, card: str) -> str:
    d = tempfile.mkdtemp(prefix="hfpub_")
    for dst, src in files.items():
        os.makedirs(os.path.dirname(os.path.join(d, dst)) or d, exist_ok=True)
        os.symlink(os.path.abspath(src), os.path.join(d, dst))
    open(os.path.join(d, "README.md"), "w").write(card)
    return d


# v4
v4 = "models/hf_local/LFM3-VL-2B-AndroidAgent-v4"
ad = snapshot_download("alpharomercoma/LFM3-VL-2B-AndroidAgent-v4b-LoRA-ckpt", revision="58bcb65efa4e395d00c3f910e0184d53566fa35f",
                       allow_patterns=["adapter_model.safetensors", "adapter_config.json"])
files = {f: os.path.join(v4, f) for f in os.listdir(v4)}
files.update({f"lora_adapter/{f}": os.path.join(ad, f) for f in ("adapter_model.safetensors", "adapter_config.json")})
files.update({f"eval/{os.path.basename(f)}": f for f in glob.glob("results/v4_dev/hub/eval/*")})
files.update({f"training_logs/{os.path.basename(f)}": f for f in glob.glob("results/v4_dev/hub/training_logs/*") if os.path.isfile(f)})
files["v4_local_export_manifest.json"] = "results/v4_local_export_manifest.json"
d = stage(files, CARD.format(name="LFM3-VL-2B-AndroidAgent-v4", manifest="v4_local_export_manifest.json",
                             what="On-device, screenshot-only Android agent: LFM3-VL-2B + v4 SFT (1,250 steps). Merged bf16 weights; the LoRA adapter is in `lora_adapter/`.",
                             extra="* Offline (eval/): dev_answer strict 0.868, dev_complete false answers 0/80, AndroidControl test high-level step SR 0.728.\n"))
push(f"{ORG}/LFM3-VL-2B-AndroidAgent-v4", d, "v4 merged weights, LoRA adapter, offline evals, verification manifest")
gg = stage({"LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf": "models/lfm3vl2b_v4-GGUF/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf",
            "mmproj-LFM3-VL-2B-Q8_0.gguf": "models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf"},
           CARD.format(name="LFM3-VL-2B-AndroidAgent-v4-GGUF", manifest="(see the merged repo)",
                       what="llama.cpp files used for AndroidWorld/MobileWorld: Q4_K_M language model (converted from the merged repo with llama.cpp cd959bae9) + the base model's Q8_0 mmproj (LoRA does not touch vision).",
                       extra="* Serve: `llama-server -m LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf --mmproj mmproj-LFM3-VL-2B-Q8_0.gguf -c 8192 --image-max-tokens 1024 --reasoning-format deepseek`\n"))
push(f"{ORG}/LFM3-VL-2B-AndroidAgent-v4-GGUF", gg, "v4 Q4_K_M + mmproj")

# v4-RL (not promoted: failed the preregistered offline rule)
rl = "models/hf_local/LFM3-VL-2B-AndroidAgent-v4-RL"
files = {f: os.path.join(rl, f) for f in os.listdir(rl)}
files.update({f"lora_adapter/{f}": os.path.join("models/hf_local/v4rl_lora", f)
              for f in ("adapter_model.safetensors", "adapter_config.json", "rl_log.jsonl")})
files.update({f"eval/{os.path.basename(f)}": f for f in glob.glob("results/v4rl_dev/*") if os.path.isfile(f) and not os.path.basename(f).startswith("logs_")})
files.update({f"training_logs/{os.path.basename(f)}": f for f in glob.glob("results/v4rl_dev/logs_*")})
files["v4rl_local_export_manifest.json"] = "results/v4rl_local_export_manifest.json"
files["v4rl_promotion_offline.json"] = "results/v4rl_promotion_offline.json"
d = stage(files, CARD.format(name="LFM3-VL-2B-AndroidAgent-v4-RL", manifest="v4rl_local_export_manifest.json",
                             what="v4 + 200 steps of static-screenshot GRPO (LoRA r16/a32, KL 0.001). **Not promoted**: failed the preregistered offline rule (dev_answer +0.022 < +0.05; AndroidControl high-level step SR 0.667 vs 0.728).",
                             extra="* Tokenizer files are v4's (the GRPO trainer had saved a left-padding block; see the manifest).\n"))
push(f"{ORG}/LFM3-VL-2B-AndroidAgent-v4-RL", d, "v4-RL merged weights, GRPO adapter, evals, manifest, promotion record")
gg = stage({"LFM3-VL-2B-AndroidAgent-v4-RL-Q4_K_M.gguf": "models/lfm3vl2b_v4rl-GGUF/LFM3-VL-2B-AndroidAgent-v4-RL-Q4_K_M.gguf",
            "mmproj-LFM3-VL-2B-Q8_0.gguf": "models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf"},
           CARD.format(name="LFM3-VL-2B-AndroidAgent-v4-RL-GGUF", manifest="(see the merged repo)",
                       what="Q4_K_M + base Q8_0 mmproj of v4-RL (not promoted).", extra=""))
push(f"{ORG}/LFM3-VL-2B-AndroidAgent-v4-RL-GGUF", gg, "v4-RL Q4_K_M + mmproj")
print("ALL PUSHED")
