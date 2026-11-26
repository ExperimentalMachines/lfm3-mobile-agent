#!/usr/bin/env python3
"""Merge a LoRA adapter (train/semi_online_rl.py output) into its base and save weights + processor, as sft_vlm.py does.
Usage: python merge_adapter.py --base E_DIR --adapter RUN/adapter --out RUN/merged"""
import argparse
import glob
import os

import torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True)
ap.add_argument("--adapter", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
model = AutoModelForImageTextToText.from_pretrained(a.base, dtype=torch.bfloat16, trust_remote_code=True)
model = PeftModel.from_pretrained(model, a.adapter).merge_and_unload()
model.save_pretrained(a.out, safe_serialization=True)
AutoProcessor.from_pretrained(a.base, trust_remote_code=True).save_pretrained(a.out)
w = glob.glob(f"{a.out}/*.safetensors")
assert w and all(os.path.getsize(f) > 0 for f in w) and os.path.exists(f"{a.out}/config.json"), "merge export incomplete"
print("MERGED", a.out, flush=True)
