"""Write the conversion receipt <file>.receipt.json that publish_gguf.py checks.

Usage (from the repository root):
  .venv-convert/bin/python scripts/publish/make_receipt.py <hub repo id> <file.gguf> <quantization> --input-dir <downloaded folder> --revision <sha>
  ... [--after-the-fact]   a receipt written later for a file that was already converted (publish_gguf.py then needs --accept_after_the_fact)

local_export_gguf.sh pins the Hub revision before it downloads, hashes the downloaded weights it converts, and calls this right after quantizing.
The receipt binds: the source repo and revision, the SHA-256 of every `*.safetensors` file that was converted, the llama.cpp commit, the
quantization and the SHA-256 of the output. A folder that is not a Hub download (a local export) cannot get a receipt, so it cannot be published.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import subprocess

from huggingface_hub import HfApi


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


ap = argparse.ArgumentParser()
ap.add_argument("repo")
ap.add_argument("gguf")
ap.add_argument("quant")
ap.add_argument("--input-dir")
ap.add_argument("--revision")
ap.add_argument("--after-the-fact", action="store_true", help="receipt written later; without --input-dir it only binds the file to the Hub's current weights")
a = ap.parse_args()
assert "/" in a.repo and not a.repo.startswith(("/", ".")), "the source must be a Hub repo id"
if a.input_dir:
    assert a.revision, "--revision is required with --input-dir"
    files = sorted(glob.glob(os.path.join(a.input_dir, "*.safetensors")))
    assert files, f"no *.safetensors in {a.input_dir}"
    mine = {os.path.basename(f): sha(f) for f in files}
else:
    assert a.after_the_fact, "without --input-dir only an --after-the-fact receipt can be written"
    mine = None
info = HfApi().model_info(a.repo, revision=a.revision, files_metadata=True)
hub = {s.rfilename: s.lfs.sha256 for s in info.siblings if s.lfs and s.rfilename.endswith(".safetensors") and "/" not in s.rfilename}
assert hub, "the Hub repo has no root-level *.safetensors"
if mine is None:
    mine = hub   # weaker: binds the file to the Hub's current weights, not to the weights that were converted
assert mine == hub, "the converted files do not match the pinned Hub revision"
a.revision = info.sha  # store the immutable commit, even if --revision was a branch or tag
assert re.fullmatch(r"[0-9a-f]{40}", a.revision), "Hub did not return a commit SHA"
rev = subprocess.run(["git", "-C", "tools/llama.cpp", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
rc = {"source_repo": a.repo, "source_revision": a.revision, "source_files_sha256": mine, "llama_cpp_commit": rev,
      "quantization": a.quant, "output_sha256": sha(a.gguf)}
if a.after_the_fact:
    rc["after_the_fact"] = True
with open(a.gguf + ".receipt.json", "w") as f:
    json.dump(rc, f, indent=1)
print("receipt written:", a.gguf + ".receipt.json")
