"""Static-screenshot GRPO for the LFM3-VL Android agent (runs ON a Colab GPU). Adapted from Liquid's official
LFM3-VL GRPO notebook (Liquid4All/cookbook finetuning/notebooks/lfm3_vl_grpo_with_trl.ipynb; same TRL 1.16 / Transformers
5.20 pins), following results/codex/codex_overnight_research.md: start from the merged v4 model, fresh language-only LoRA
r16/a32 (adapter disabled == v4, so the KL reference is v4), beta (KL) 0.001, 4 samples per state, short completions.

Data: a parquet RL pool (data/v4_rl_pool.py) with columns image, prompt (system+user messages exactly as in v4 SFT),
gt_action, kind. Reward: train/rl_reward.py (strict).
usage: python grpo_vlm.py --model <merged v4 dir|hub id> --data <repo>@<rev> --out <dir> [--max_steps N --smoke]
"""
import argparse
import json
import os
import time

import torch
from datasets import load_dataset
from huggingface_hub import HfApi
from peft import LoraConfig
from transformers import AutoModelForImageTextToText, AutoProcessor, TrainerCallback
from trl import GRPOConfig, GRPOTrainer

import rl_reward

p = argparse.ArgumentParser()
p.add_argument("--model", required=True)
p.add_argument("--data", required=True, help="repo@revision of the RL pool dataset")
p.add_argument("--out", required=True)
p.add_argument("--max_steps", type=int, default=200)
p.add_argument("--lr", type=float, default=1e-5)
p.add_argument("--beta", type=float, default=0.001)
p.add_argument("--bs", type=int, default=4)
p.add_argument("--ga", type=int, default=8)
p.add_argument("--gens", type=int, default=4)
p.add_argument("--max_completion", type=int, default=192)
p.add_argument("--max_pixels", type=int, default=774400)
p.add_argument("--save_steps", type=int, default=25)
p.add_argument("--hub_repo", default="", help="push checkpoints/adapter here (durable copy)")
p.add_argument("--smoke", action="store_true", help="tiny run: 4 steps, then reload check")
a = p.parse_args()
t0 = time.time()
repo, rev = a.data.split("@")
ds = load_dataset(repo, split="train", revision=rev)
if a.smoke:
    a.max_steps = 4
print(ds, flush=True)

processor = AutoProcessor.from_pretrained(a.model, trust_remote_code=True,
                                          size={"shortest_edge": 65536, "longest_edge": a.max_pixels})
processor.tokenizer.padding_side = "left"
model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16, trust_remote_code=True,
                                                    attn_implementation="sdpa").to("cuda")
peft_config = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, task_type="CAUSAL_LM",
                         target_modules=r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|in_proj|out_proj|w1|w2|w3)")
kw = dict(
    output_dir=a.out, max_steps=a.max_steps, per_device_train_batch_size=a.bs, gradient_accumulation_steps=a.ga,
    num_generations=a.gens, max_completion_length=a.max_completion, temperature=0.8, top_p=0.95,
    learning_rate=a.lr, lr_scheduler_type="constant_with_warmup", warmup_steps=10 if not a.smoke else 0,
    beta=a.beta, epsilon=0.2, loss_type="dapo", scale_rewards="group", num_iterations=1, max_grad_norm=1.0,
    weight_decay=0.0, bf16=True, gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False},
    use_vllm=False, mask_truncated_completions=True, remove_unused_columns=False, logging_steps=1,
    save_steps=a.save_steps, save_total_limit=3, report_to="none", seed=4,
)
fields = set(GRPOConfig.__dataclass_fields__)
if "use_transformers_continuous_batching" in fields:
    kw["use_transformers_continuous_batching"] = False
if "chat_template_kwargs" in fields:
    kw["chat_template_kwargs"] = {"enable_thinking": True}  # same template mode as v4 SFT/eval (FT_THINK=1)
else:
    print("WARNING: GRPOConfig has no chat_template_kwargs; template default thinking mode used", flush=True)
cfg = GRPOConfig(**{k: v for k, v in kw.items() if k in fields})
print("ignored config keys:", sorted(set(kw) - fields), flush=True)


class Log(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **k):
        if logs:
            keep = {k2: round(v, 4) if isinstance(v, float) else v for k2, v in logs.items()
                    if any(s in k2 for s in ("reward", "kl", "loss", "completion", "entropy", "clip", "learning_rate"))}
            print(f"[{time.time() - t0:.0f}s] step {state.global_step} {json.dumps(keep)}", flush=True)
            os.makedirs(a.out, exist_ok=True)
            with open(os.path.join(a.out, "rl_log.jsonl"), "a") as f:
                f.write(json.dumps({"step": state.global_step, "elapsed_s": round(time.time() - t0), **logs}) + "\n")

    def on_save(self, args, state, control, **k):
        if a.hub_repo:
            try:
                HfApi().upload_folder(folder_path=args.output_dir, repo_id=a.hub_repo, path_in_repo="checkpoints",
                                      allow_patterns=[f"checkpoint-{state.global_step}/*", "rl_log.jsonl"])
            except Exception as e:  # a failed durable copy must be visible but not kill training
                print("checkpoint upload failed:", e, flush=True)


trainer = GRPOTrainer(model=model, reward_funcs=[rl_reward.reward_fn], args=cfg, train_dataset=ds,
                      processing_class=processor, peft_config=peft_config, callbacks=[Log()])
names = [n for n, p_ in trainer.model.named_parameters() if p_.requires_grad]
assert names and all("language_model" in n and "lora_" in n for n in names), names[:5]
print(f"trainable tensors: {len(names)} (all language-model LoRA)", flush=True)
if a.hub_repo:
    HfApi().create_repo(a.hub_repo, private=True, exist_ok=True)
trainer.train()
print(f"trained {a.max_steps} steps in {time.time() - t0:.0f}s; peak GPU {torch.cuda.max_memory_allocated() / 1e9:.1f} GB",
      flush=True)
trainer.save_model(os.path.join(a.out, "lora"))
merged = trainer.model.merge_and_unload()
merged.save_pretrained(os.path.join(a.out, "merged"))
processor.save_pretrained(os.path.join(a.out, "merged"))
for f in os.listdir(a.model) if os.path.isdir(a.model) else []:  # remote code files of the base model
    if f.endswith(".py") or f.endswith(".jinja"):
        import shutil
        shutil.copy(os.path.join(a.model, f), os.path.join(a.out, "merged", f))
# reload check in the same process: the merged model must load and generate a parseable action
m2 = AutoModelForImageTextToText.from_pretrained(os.path.join(a.out, "merged"), dtype=torch.bfloat16,
                                                 trust_remote_code=True).to("cuda").eval()
ex = ds[0]
conv = [{"role": "system", "content": [{"type": "text", "text": ex["prompt"][0]["content"]}]},
        {"role": "user", "content": [{"type": "image", "image": ex["image"]}, {"type": "text", "text": ex["prompt"][1]["content"]}]}]
inp = processor.apply_chat_template([conv], add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
                                    processor_kwargs={"padding": True}, enable_thinking=True).to("cuda")
o = m2.generate(**inp, max_new_tokens=a.max_completion, do_sample=False)
txt = processor.batch_decode(o[:, inp["input_ids"].shape[1]:], skip_special_tokens=False)[0]
print("reload check output:", txt[:200].replace("\n", " "), flush=True)
print("RL DONE", flush=True)
