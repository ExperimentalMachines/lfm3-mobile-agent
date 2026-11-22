"""Publish finished runs as PUBLIC repos on the owner's personal Hugging Face account (owner's request 2026-11-21:
"Upload to public personal"; private storage is full). Runs ON the Colab VM inside the blocking cell.

For each "run_dir:Name" in --runs (waits until the run's train_receipt.json exists):
  alpharomercoma/<Name>       merged weights (root), LoRA adapter (lora_adapter/), training logs (training_logs/),
                              the base model's LICENSE, model card from scripts/publish/cards/<version>.md
The GGUF repos are published from the Mac (4-bit quantization runs there; scripts/publish/local_publish_gguf.sh).
Usage: python vm_publish_public.py --runs "lfm3vl2b-v41-lora:LFM3-VL-2B-AndroidAgent-v4.1 ..."
"""
import argparse
import hashlib
import os
import time

from huggingface_hub import HfApi, hf_hub_download

USER = "alpharomercoma"
BASE_REV = "23387beda43c60310348e83e25f78f33c3140d3a"


def sha(p):
    d = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            d.update(b)
    return d.hexdigest()


def public_repo(api, rid):
    api.create_repo(rid, private=False, exist_ok=True)
    if api.model_info(rid).private:
        api.update_repo_settings(rid, private=False)
    assert not api.model_info(rid).private, rid


def wait_for(path):
    while not os.path.exists(path):
        time.sleep(120)


ap = argparse.ArgumentParser()
ap.add_argument("--runs", required=True)
ap.add_argument("--cards", default="/content/work/meta")
a = ap.parse_args()
api = HfApi()
lic = hf_hub_download("LiquidAI/LFM3-VL-2B", "LICENSE", revision=BASE_REV)
for spec in a.runs.split():
    run, name = spec.split(":")
    ver = name.split("AndroidAgent-", 1)[1]           # e.g. v4.1, v4.3-dpo
    R = f"/content/runs/{run}"
    wait_for(f"{R}/train_receipt.json")
    rid = f"{USER}/{name}"
    public_repo(api, rid)
    api.upload_folder(folder_path=f"{R}/merged", repo_id=rid, commit_message="merged weights (LoRA merged into the base)")
    api.upload_folder(folder_path=f"{R}/lora", repo_id=rid, path_in_repo="lora_adapter", commit_message="LoRA adapter",
                      ignore_patterns=["training_args.bin"])
    api.upload_folder(folder_path=f"{R}/logs", repo_id=rid, path_in_repo="training_logs", commit_message="training logs")
    api.upload_file(path_or_fileobj=lic, path_in_repo="LICENSE", repo_id=rid)
    api.upload_file(path_or_fileobj=f"{a.cards}/card-{ver}.md", path_in_repo="README.md", repo_id=rid, commit_message="model card")
    print(f"[{time.strftime('%T')}] published {rid}", flush=True)
print("all published", flush=True)
