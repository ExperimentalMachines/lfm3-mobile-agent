"""Round 5, candidate P (docs/PREREG_v41.md, 2026-11-22 17:00): step-level DPO on the model's own mistakes (runs ON a
Colab GPU). Start = v4.2's merged weights; a fresh language-only LoRA (r64/α128, projector and vision frozen) is trained
with DPO (sigmoid, β) + w × SFT on the preferred step (TRL loss_type ["sigmoid", "sft"]); the reference is v4.2 itself
(the adapter disabled). Pairs come from data/v5_pairs.py: preferred = the human step, rejected = v4.2's own greedy step.

Texts are rendered with the model's own chat template exactly as at inference (thinking on): prompt = system + user
(image + text) + generation prompt; completion = the rest of the rendered conversation, so the completion starts where
generation starts; each completion ends with exactly one end-of-turn token (checked on a collated batch).

usage: python dpo_vlm.py --model V42_MERGED --pairs PAIRS_DISK --out DIR [--smoke 16]
"""
import argparse
import glob
import json
import os
import shutil
import sys
import time

import torch
from datasets import load_from_disk
from peft import LoraConfig
from transformers import AutoModelForImageTextToText, AutoProcessor, TrainerCallback
from trl import DPOConfig, DPOTrainer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_format as af  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--model", required=True)
p.add_argument("--pairs", required=True)
p.add_argument("--out", required=True)
p.add_argument("--beta", type=float, default=0.1)
p.add_argument("--sft_weight", type=float, default=0.5)
p.add_argument("--lr", type=float, default=2e-5)
p.add_argument("--bs", type=int, default=4)
p.add_argument("--grad_accum", type=int, default=8)
p.add_argument("--epochs", type=float, default=1.0)
p.add_argument("--lora_r", type=int, default=64)
p.add_argument("--lora_alpha", type=int, default=128)
p.add_argument("--target_regex", default=r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|in_proj|out_proj|w1|w2|w3)")
p.add_argument("--max_pixels", type=int, default=774400)
p.add_argument("--min_pixels", type=int, default=65536)
p.add_argument("--smoke", type=int, default=0, help="train on N pairs for 2 steps, check everything, no export")
p.add_argument("--seed", type=int, default=42)
p.add_argument("--kinds", default="", help="comma list of pair kinds to keep (empty = all)")
p.add_argument("--cap_per_kind", default="", help="kind=N,... random cap per kind (seeded)")
a = p.parse_args()
os.makedirs(f"{a.out}/logs", exist_ok=True)
json.dump(vars(a), open(f"{a.out}/logs/run_config.json", "w"), indent=1)

proc = AutoProcessor.from_pretrained(a.model, trust_remote_code=True,
                                     size={"shortest_edge": a.min_pixels, "longest_edge": a.max_pixels})
tok = proc.tokenizer
EOS = tok.eos_token
print("eos token:", repr(EOS), flush=True)


def render(prompt_msgs, comp, keep_end):
    sysm, user = prompt_msgs
    conv = [{"role": "system", "content": [{"type": "text", "text": sysm["content"]}]},
            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": user["content"]}]}]
    pt = proc.apply_chat_template(conv, add_generation_prompt=True, tokenize=False, enable_thinking=True)
    full = proc.apply_chat_template(conv + [{"role": "assistant", "content": [{"type": "text", "text": comp["action"]}],
                                             "reasoning_content": comp["intent"]}],
                                    tokenize=False, enable_thinking=True)
    assert full.startswith(pt), "rendered conversation does not extend the generation prompt"
    c = full[len(pt):].rstrip()
    if c.endswith(EOS):
        c = c[: -len(EOS)]
    assert comp["action"] in c and af.parse_action(c) is not None, ("completion lost its action", c)
    return pt, (c + EOS) if keep_end else c


ds = load_from_disk(a.pairs)
if a.kinds:
    keep = set(a.kinds.split(","))
    ds = ds.filter(lambda k: k in keep, input_columns="kind")
if a.cap_per_kind:
    import random
    rng = random.Random(a.seed)
    caps = {k: int(v) for k, v in (x.split("=") for x in a.cap_per_kind.split(","))}
    by = {}
    for i, k in enumerate(ds["kind"]):
        by.setdefault(k, []).append(i)
    idx = sorted(i for k, v in by.items() for i in (rng.sample(v, caps[k]) if k in caps and len(v) > caps[k] else v))
    ds = ds.select(idx)
from collections import Counter as _C
print("pairs by kind:", dict(_C(ds["kind"])), flush=True)
json.dump(dict(_C(ds["kind"])), open(f"{a.out}/logs/pairs_used.json", "w"))
if a.smoke:
    ds = ds.select(range(min(a.smoke, len(ds))))


def build(keep_end):
    def fn(ex):
        pm = json.loads(ex["prompt_json"])
        pt, ch = render(pm, json.loads(ex["chosen_json"]), keep_end)
        _, rj = render(pm, json.loads(ex["rejected_json"]), keep_end)
        return {"prompt": pt, "chosen": ch, "rejected": rj}
    d = ds.map(fn, desc="render")
    return d.remove_columns([c for c in d.column_names if c not in ("images", "prompt", "chosen", "rejected")])


model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16, trust_remote_code=True,
                                                    attn_implementation="sdpa").to("cuda")
peft_config = LoraConfig(r=a.lora_r, lora_alpha=a.lora_alpha, lora_dropout=0.05, target_modules=a.target_regex,
                         task_type="CAUSAL_LM")


class Log(TrainerCallback):
    t0 = time.time()

    def on_log(self, args, state, control, logs=None, **k):
        rec = {"step": state.global_step, "elapsed_s": round(time.time() - self.t0, 1), **(logs or {})}
        with open(f"{a.out}/logs/train_log.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(json.dumps(rec), flush=True)


def make(train_ds, max_steps=-1):
    cfg = DPOConfig(output_dir=a.out, beta=a.beta, loss_type=["sigmoid", "sft"], loss_weights=[1.0, a.sft_weight],
                    learning_rate=a.lr, per_device_train_batch_size=a.bs, gradient_accumulation_steps=a.grad_accum,
                    num_train_epochs=a.epochs, max_steps=max_steps, lr_scheduler_type="cosine", warmup_steps=0.1,
                    max_length=None, bf16=True, gradient_checkpointing=True, logging_steps=5, save_strategy="no",
                    report_to=[], seed=a.seed, remove_unused_columns=False)
    return DPOTrainer(model=model, args=cfg, train_dataset=train_ds, processing_class=proc, peft_config=peft_config,
                      callbacks=[Log()])


# TRL 1.16 does not pre-tokenize vision datasets (skip_prepare_dataset) and adds no end token there: the collator
# tokenizes prompt (+ images) and completions as given. So completions carry the end-of-turn token themselves; check it
# on a real collated batch: every completion ends with exactly one end token and decodes back to the rendered text.
train_ds = build(keep_end=True)
trainer = make(train_ds, max_steps=2 if a.smoke else -1)
batch = trainer.data_collator([dict(train_ds[0])])
ids, cm = batch["input_ids"], batch["completion_mask"].bool()
for row, want in ((0, train_ds[0]["chosen"]), (1, train_ds[0]["rejected"])):
    comp = ids[row][cm[row]].tolist()
    print(f"completion {row}: {len(comp)} tokens, {tok.decode(comp)!r}", flush=True)
    assert comp[-1] == tok.eos_token_id and (len(comp) < 2 or comp[-2] != tok.eos_token_id), "end token wrong"
    assert tok.decode(comp).strip() == want.strip(), ("completion does not round-trip", tok.decode(comp), want)
print("prompt tokens (with image):", int((~cm[0] & batch["attention_mask"][0].bool()).sum()), flush=True)
names = [n for n, p_ in trainer.model.named_parameters() if p_.requires_grad]
assert names and all("language_model" in n and "lora_" in n for n in names), names[:5]
print(f"trainable tensors: {len(names)} (language-model LoRA only); pairs {len(train_ds)}", flush=True)

t0 = time.time()
res = trainer.train()
summary = {**res.metrics, "wall_s": time.time() - t0, "pairs": len(train_ds),
           "peak_gpu_mem_gb": torch.cuda.max_memory_allocated() / 1e9}
json.dump(summary, open(f"{a.out}/logs/train_summary.json", "w"), indent=1)
json.dump(trainer.state.log_history, open(f"{a.out}/logs/log_history.json", "w"), indent=1)
import math
losses = [h["loss"] for h in trainer.state.log_history if "loss" in h] + [res.metrics.get("train_loss", float("nan"))]
assert all(math.isfinite(x) for x in losses), f"non-finite loss: {losses[-5:]}"
if a.smoke:
    print("SMOKE OK", json.dumps(summary), flush=True)
    sys.exit(0)

trainer.save_model(f"{a.out}/lora")
merged = trainer.model.merge_and_unload()
merged.save_pretrained(f"{a.out}/merged", safe_serialization=True)
proc.save_pretrained(f"{a.out}/merged")
for f in os.listdir(a.model) if os.path.isdir(a.model) else []:   # remote-code files of the start model, if any
    if f.endswith(".py") and not os.path.exists(f"{a.out}/merged/{f}"):
        shutil.copy(os.path.join(a.model, f), f"{a.out}/merged/{f}")
# reload check: the merged model must load and produce a parseable action that ends with the end token
m2 = AutoModelForImageTextToText.from_pretrained(f"{a.out}/merged", dtype=torch.bfloat16, trust_remote_code=True).to("cuda").eval()
pm = json.loads(ds[0]["prompt_json"])
conv = [{"role": "system", "content": [{"type": "text", "text": pm[0]["content"]}]},
        {"role": "user", "content": [{"type": "image", "image": ds[0]["images"][0]}, {"type": "text", "text": pm[1]["content"]}]}]
inp = proc.apply_chat_template([conv], add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
                               processor_kwargs={"padding": True}, enable_thinking=True).to("cuda")
with torch.inference_mode():
    o = m2.generate(**inp, max_new_tokens=96, do_sample=False)
txt = proc.batch_decode(o[:, inp["input_ids"].shape[1]:], skip_special_tokens=False)[0]
print("reload sample:", repr(txt[:200]), flush=True)
assert EOS in txt and af.parse_action(txt.split(EOS)[0]) is not None, "merged model output not parseable or no end token"
w = glob.glob(f"{a.out}/merged/*.safetensors")
json.dump({"args": vars(a), "global_step": trainer.state.global_step, "max_steps": trainer.state.max_steps,
           "weights": {os.path.basename(f): os.path.getsize(f) for f in w}, "summary": summary},
          open(f"{a.out}/train_receipt.json", "w"), indent=1)
print("saved lora + merged (receipt written)", flush=True)
