"""Run on a fresh Colab VM (via `colab exec -f`). Installs pinned deps (versions from Liquid's
official LFM3-VL TRL notebook), logs in to HF from /content/.hf_token, reports hardware."""
import os
import subprocess
import sys

def sh(cmd):
    print("+", cmd, flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(r.stdout[-3000:], r.stderr[-3000:], flush=True)
    return r.returncode

sh("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv")
sh("nproc; free -g | head -2; df -h /content | tail -1; ls -la /dev/kvm 2>&1")
pkgs = [
    "torch==2.14.1", "torchvision==0.29.1", "torchao==0.18.0", "trl==1.16.0", "transformers==5.20.2", "peft==0.21.2",
    "accelerate==1.15.0", "datasets==5.1.0", "huggingface-hub==2.3.0", "tokenizers==0.23.3",
    "safetensors==0.8.0", "tensorboard", "pillow", "pyarrow",
]
rc = sh("pip install -q " + " ".join(f'"{p}"' for p in pkgs))
print("pip rc", rc)
if rc != 0:
    raise SystemExit(f"pip install failed rc={rc}")
tok_path = "/content/.hf_token"
if os.path.exists(tok_path):
    tok = open(tok_path).read().strip()
    os.environ["HF_TOKEN"] = tok
    from huggingface_hub import login, whoami
    login(token=tok, add_to_git_credential=False)
    print("HF user:", whoami()["name"])
import importlib.metadata as _md
_want = {"torch": "2.14.1", "transformers": "5.20.2", "trl": "1.16.0", "peft": "0.21.2", "torchao": "0.18.0", "datasets": "5.1.0"}
_bad = {k: _md.version(k) for k, v in _want.items() if not _md.version(k).startswith(v)}
if _bad:
    raise SystemExit(f"version mismatch after bootstrap: {_bad}")
import torch, transformers, trl, peft
print("versions", torch.__version__, transformers.__version__, trl.__version__, peft.__version__,
      "cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
