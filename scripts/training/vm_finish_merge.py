"""Finish a training run whose final Hub push failed (2026-11-21, v4.1: "403 Private storage limit reached").

sft_vlm.py's trainer.save_model() saves the LoRA adapter and processor, then (push_to_hub=True) pushes, which raised
before the merge. This does the remaining steps exactly as sft_vlm.py: base model in bf16 on the GPU + the saved
adapter -> merge_and_unload() -> merged/ (safetensors + processor), then the same train_receipt.json, built from the
run's own run_config.json, train_summary.json and final checkpoint state. Usage (Colab): python vm_finish_merge.py OUT_DIR
"""
import glob
import json
import os
import sys

import torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor

out = sys.argv[1]
cfg = json.load(open(f"{out}/logs/run_config.json"))
st = json.load(open(sorted(glob.glob(f"{out}/checkpoint-*/trainer_state.json"),
                           key=lambda p: int(p.split("checkpoint-")[1].split("/")[0]))[-1]))
assert st["global_step"] >= st["max_steps"] > 0, (st["global_step"], st["max_steps"])
assert not os.path.exists(f"{out}/train_receipt.json"), "receipt exists; nothing to finish"
base = AutoModelForImageTextToText.from_pretrained(cfg["model_id"], dtype=torch.bfloat16, trust_remote_code=True,
                                                   attn_implementation="sdpa").to("cuda")
merged = PeftModel.from_pretrained(base, f"{out}/lora").merge_and_unload()
merged.save_pretrained(f"{out}/merged", safe_serialization=True)
AutoProcessor.from_pretrained(f"{out}/lora", trust_remote_code=True).save_pretrained(f"{out}/merged")
w = glob.glob(f"{out}/merged/*.safetensors")
assert w and all(os.path.getsize(f) > 0 for f in w) and os.path.exists(f"{out}/merged/config.json")
json.dump({"args": {k: v for k, v in cfg.items() if k != "provenance"}, "global_step": st["global_step"],
           "max_steps": st["max_steps"], "weights": {os.path.basename(f): os.path.getsize(f) for f in w},
           "summary": json.load(open(f"{out}/logs/train_summary.json")),
           "finished_by": "scripts/training/vm_finish_merge.py (final Hub push failed: private storage limit)"},
          open(f"{out}/train_receipt.json", "w"), indent=2)
print("merged + receipt written:", {os.path.basename(f): os.path.getsize(f) for f in w}, flush=True)
