"""Write the conversion receipt <file>.receipt.json that publish_gguf.py checks.
Usage: .venv-convert/bin/python scripts/publish/make_receipt.py <source repo id> <file.gguf> <quantization> [--after-the-fact]
Run from the repository root. The receipt records the source repo, the SHA-256 of its model.safetensors on the Hub, the llama.cpp commit,
the quantization and the SHA-256 of the output. local_export_gguf.sh calls it right after quantizing; --after-the-fact marks a receipt
written later for a file that was already converted (it then only binds the file to the Hub's current weights, it does not prove the conversion).
"""
import hashlib
import json
import subprocess
import sys

from huggingface_hub import HfApi

src, out, q = sys.argv[1:4]
h = hashlib.sha256()
with open(out, "rb") as f:
    for b in iter(lambda: f.read(1 << 24), b""):
        h.update(b)
w = None
if "/" in src and not src.startswith(("/", ".")):
    w = {s.rfilename: s.lfs.sha256 for s in HfApi().model_info(src, files_metadata=True).siblings if s.lfs}.get("model.safetensors")
rev = subprocess.run(["git", "-C", "tools/llama.cpp", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
rc = {"source_repo": src, "source_weights_sha256": w, "llama_cpp_commit": rev, "quantization": q, "output_sha256": h.hexdigest()}
if "--after-the-fact" in sys.argv:
    rc["after_the_fact"] = True
json.dump(rc, open(out + ".receipt.json", "w"), indent=1)
print("receipt written:", out + ".receipt.json")
