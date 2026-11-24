"""SFT (LoRA) of a small VLM into a screenshot-only Android agent. Runs on a Colab A100.

Input: a HF dataset saved with `datasets.save_to_disk` (or a Hub repo) with columns
  images: list[Image]  (exactly one screenshot)
  messages: [{"role":"system",...},{"role":"user",...},{"role":"assistant","content":json_action,"reasoning_content":intent}]
built by data/build_androidcontrol.py from the shared train/agent_format.py.

Every metric TRL logs is appended to <out>/logs/train_log.jsonl and the run config to
<out>/logs/run_config.json, so the numbers survive even if the VM is reclaimed.
"""

import argparse
import json
import os
import sys
import time

import torch
from datasets import load_dataset, load_from_disk, concatenate_datasets
from peft import LoraConfig
from transformers import AutoModelForImageTextToText, AutoProcessor, TrainerCallback
from trl import SFTConfig, SFTTrainer

p = argparse.ArgumentParser()
p.add_argument("--model_id", default="LiquidAI/LFM3-VL-2B")
p.add_argument("--model_revision", default=None, help="Hub commit (40 hex) of --model_id; required for Hub ids because "
               "the model is loaded with trust_remote_code")
p.add_argument("--allow_unpinned", action="store_true", help="explicitly allow a Hub --model_id without --model_revision")
p.add_argument("--train", nargs="+", required=True, help="dataset dirs (save_to_disk) or hub ids")
p.add_argument("--val", default=None)
p.add_argument("--out", required=True)
p.add_argument("--max_pixels", type=int, default=880 * 880)
p.add_argument("--min_pixels", type=int, default=256 * 256)
p.add_argument("--epochs", type=float, default=1.0)
p.add_argument("--max_steps", type=int, default=-1)
p.add_argument("--lr", type=float, default=2e-4)
p.add_argument("--bs", type=int, default=8)
p.add_argument("--grad_accum", type=int, default=4)
p.add_argument("--lora_r", type=int, default=64)
p.add_argument("--lora_alpha", type=int, default=128)
p.add_argument("--target_regex", default=r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|in_proj|out_proj|w1|w2|w3)")
p.add_argument("--modules_to_save", nargs="*", default=["multi_modal_projector"])
p.add_argument("--save_steps", type=int, default=500)
p.add_argument("--eval_steps", type=int, default=500)
p.add_argument("--hub_repo", default=None, help="private hub repo for checkpoint backup")
p.add_argument("--workers", type=int, default=8)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--no_gc", action="store_true", help="disable gradient checkpointing")
p.add_argument("--chat_template_path", default=None, help="override chat template (e.g. Qwen3.5 + generation markers)")
p.add_argument("--max_agent_rows", type=int, default=0, help="random subset of the agent data (0 = all)")
p.add_argument("--replay", nargs="*", default=[], help="general-data replay datasets (save_to_disk dirs) mixed in to limit forgetting")
p.add_argument("--inline_think", action="store_true", help="put intent as <think>..</think> inside content (templates without reasoning_content)")
p.add_argument("--trust_remote_code", action="store_true", default=True)
p.add_argument("--scheduler", default="cosine", choices=["cosine", "wsd"],
               help="wsd = warm-up, constant, linear decay over the last --decay_frac of steps (round 5, candidate S)")
p.add_argument("--decay_frac", type=float, default=0.15)
p.add_argument("--warmup", type=float, default=0.03)
args = p.parse_args()
import re as _re
if (not os.path.isdir(args.model_id) and not args.allow_unpinned
        and not (args.model_revision and _re.fullmatch(r"[0-9a-f]{40}", args.model_revision))):
    p.error("--model_id is a Hub id loaded with trust_remote_code: pass --model_revision <40-hex commit> (or --allow_unpinned)")
if args.scheduler == "wsd" and args.max_steps <= 0:
    sys.exit("--scheduler wsd needs --max_steps")

os.makedirs(f"{args.out}/logs", exist_ok=True)
os.environ.setdefault("TENSORBOARD_LOGGING_DIR", f"{args.out}/logs/tb")
def _provenance():
    prov = {}
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        prov["model_sha"] = api.model_info(args.model_id, revision=args.model_revision).sha if not os.path.isdir(args.model_id) else "local"
        for t in args.train + ([args.val] if args.val else []):
            if not os.path.isdir(t):
                prov[f"dataset_sha:{t}"] = api.dataset_info(t.partition("@")[0]).sha
    except Exception as e:
        prov["error"] = repr(e)
    import importlib.metadata as md
    prov["versions"] = {k: md.version(k) for k in ("torch", "transformers", "trl", "peft", "datasets", "accelerate")}
    return prov


json.dump({**vars(args), "provenance": _provenance()}, open(f"{args.out}/logs/run_config.json", "w"), indent=2)


def _hub_data_files(repo, split, revision=None):
    """v1 repos use data/<split>/*.parquet; push_to_hub (v2) writes data/<split>-NNNNN-of-NNNNN.parquet."""
    from huggingface_hub import HfApi
    files = HfApi().list_repo_files(repo, repo_type="dataset", revision=revision)
    if any(f.startswith(f"data/{split}/") for f in files):
        return {split: f"data/{split}/*.parquet"}
    return {split: f"data/{split}-*.parquet"}


def load_any(path):
    """local save_to_disk dir, or 'org/repo@split' on the Hub."""
    if os.path.isdir(path):
        return load_from_disk(path)
    repo, _, split = path.partition("@")
    split, _, rev = split.partition("#")  # 'org/repo@split#revision' pins an immutable dataset revision
    split, rev = split or "train", rev or None
    return load_dataset(repo, data_files=_hub_data_files(repo, split, rev), split=split, revision=rev)


train_ds = concatenate_datasets([load_any(t) for t in args.train]).shuffle(seed=args.seed)
if args.max_agent_rows:
    train_ds = train_ds.select(range(min(args.max_agent_rows, len(train_ds))))
n_agent = len(train_ds)
if args.replay:
    rep = concatenate_datasets([load_any(r) for r in args.replay])
    rep = rep.remove_columns([c for c in rep.column_names if c not in ("images", "messages")])
    train_ds = train_ds.remove_columns([c for c in train_ds.column_names if c not in ("images", "messages")])
    rep = rep.cast(train_ds.features)
    train_ds = concatenate_datasets([train_ds, rep]).shuffle(seed=args.seed)
    print(f"mixed replay: agent={n_agent} replay={len(rep)} ({len(rep) / len(train_ds):.1%})", flush=True)


def _inline(msgs):
    out = []
    for m in msgs:
        m = dict(m)
        if m["role"] == "assistant" and m.get("reasoning_content"):
            m["content"] = f"<think>{m['reasoning_content']}</think>{m['content']}"
        m["reasoning_content"] = None
        out.append(m)
    return out


if args.inline_think:
    train_ds = train_ds.map(lambda m: {"messages": _inline(m)}, input_columns="messages")
val_ds = load_any(args.val) if args.val else None
if args.inline_think and val_ds is not None:
    val_ds = val_ds.map(lambda m: {"messages": _inline(m)}, input_columns="messages")
keep = ["images", "messages"]
train_ds = train_ds.remove_columns([c for c in train_ds.column_names if c not in keep])
if val_ds is not None:
    val_ds = val_ds.remove_columns([c for c in val_ds.column_names if c not in keep])
print(f"train rows={len(train_ds)} val rows={len(val_ds) if val_ds else 0}", flush=True)

_pk = {"size": {"shortest_edge": args.min_pixels, "longest_edge": args.max_pixels}} if args.max_pixels > 0 else {}
processor = AutoProcessor.from_pretrained(args.model_id, revision=args.model_revision, trust_remote_code=True, **_pk)
processor.tokenizer.padding_side = "right"
if args.chat_template_path:
    tpl = open(args.chat_template_path).read()
    processor.chat_template = tpl
    processor.tokenizer.chat_template = tpl
    print("chat template overridden from", args.chat_template_path, flush=True)
model = AutoModelForImageTextToText.from_pretrained(
    args.model_id, revision=args.model_revision, dtype=torch.bfloat16, trust_remote_code=True,
    attn_implementation="sdpa",
).to("cuda")
print(f"params={model.num_parameters():,}", flush=True)
mts = [m for m in args.modules_to_save if any(m in n for n, _ in model.named_modules())]
print("modules_to_save:", mts, flush=True)

peft_config = LoraConfig(
    r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05,
    target_modules=args.target_regex, modules_to_save=mts or None, task_type="CAUSAL_LM",
)


class JsonlLogger(TrainerCallback):
    def __init__(self, path):
        self.path = path
        self.t0 = time.time()

    def on_log(self, a, state, control, logs=None, **kw):
        rec = {"step": state.global_step, "epoch": state.epoch, "elapsed_s": round(time.time() - self.t0, 1),
               "gpu_mem_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2), **(logs or {})}
        with open(self.path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(json.dumps(rec), flush=True)


cfg = SFTConfig(
    output_dir=args.out,
    num_train_epochs=args.epochs,
    max_steps=args.max_steps,
    per_device_train_batch_size=args.bs,
    per_device_eval_batch_size=args.bs,
    gradient_accumulation_steps=args.grad_accum,
    learning_rate=args.lr,
    lr_scheduler_type="warmup_stable_decay" if args.scheduler == "wsd" else "cosine",
    lr_scheduler_kwargs={"num_decay_steps": int(args.decay_frac * args.max_steps), "decay_type": "linear"}
    if args.scheduler == "wsd" else {},
    warmup_steps=args.warmup,
    weight_decay=0.0,
    max_grad_norm=1.0,
    max_length=None,
    assistant_only_loss=True,
    gradient_checkpointing=not args.no_gc,
    bf16=True,
    logging_steps=10,
    logging_first_step=True,
    save_strategy="steps",
    save_steps=args.save_steps,
    save_total_limit=3,
    eval_strategy="steps" if val_ds is not None else "no",
    eval_steps=args.eval_steps,
    dataloader_num_workers=args.workers,
    dataloader_persistent_workers=True,
    report_to=["tensorboard"],
    seed=args.seed,
    push_to_hub=bool(args.hub_repo),
    hub_model_id=args.hub_repo,
    hub_private_repo=True,
    hub_strategy="checkpoint" if args.hub_repo else "every_save",
)

trainer = SFTTrainer(
    model=model, args=cfg, train_dataset=train_ds, eval_dataset=val_ds,
    processing_class=processor, peft_config=peft_config,
    callbacks=[JsonlLogger(f"{args.out}/logs/train_log.jsonl")],
)
trainer.model.print_trainable_parameters()
resume = None
ckpts = [d for d in os.listdir(args.out) if d.startswith("checkpoint-")] if os.path.isdir(args.out) else []
if not ckpts and args.hub_repo:
    # VM was reclaimed? pull the last checkpoint pushed by hub_strategy="checkpoint"
    from huggingface_hub import HfApi, snapshot_download
    from huggingface_hub.errors import RepositoryNotFoundError
    try:
        files = HfApi().list_repo_files(args.hub_repo)
    except RepositoryNotFoundError:
        files = []  # first run: no checkpoint repo yet
    except Exception as e:  # never silently restart from step 0 over an existing checkpoint repo (Codex recovery audit P1)
        raise SystemExit(f"cannot list hub checkpoint repo {args.hub_repo} ({e}); refusing to train from scratch")
    KEYS = ("model_id", "train", "max_pixels", "lr", "bs", "grad_accum", "lora_r", "lora_alpha", "target_regex", "max_steps",
            "epochs", "inline_think", "replay")
    if "run_config.json" in files:  # identity of the run that wrote the checkpoints
        old = json.load(open(snapshot_download(args.hub_repo, allow_patterns=["run_config.json"]) + "/run_config.json"))
        diff = [f"{k}: {old.get(k)!r} != {vars(args).get(k)!r}" for k in KEYS if k in old and old.get(k) != vars(args).get(k)]
        if diff:
            raise SystemExit("hub checkpoints belong to a different run configuration, refusing: " + "; ".join(diff))
    elif files:
        print("WARNING: hub checkpoint repo has no run_config.json; only batch size / max_steps are checked", flush=True)
    else:
        HfApi().create_repo(args.hub_repo, private=True, exist_ok=True)
        HfApi().upload_file(path_or_fileobj=f"{args.out}/logs/run_config.json", path_in_repo="run_config.json",
                            repo_id=args.hub_repo)
    try:
        if "last-checkpoint/trainer_state.json" in files:
            snapshot_download(args.hub_repo, allow_patterns=["last-checkpoint/*"], local_dir=args.out)
            st = json.load(open(f"{args.out}/last-checkpoint/trainer_state.json"))
            bad = []
            if st.get("train_batch_size") not in (None, args.bs):
                bad.append(f"train_batch_size {st.get('train_batch_size')} != {args.bs}")
            if args.max_steps > 0 and st.get("max_steps") not in (None, args.max_steps):
                bad.append(f"max_steps {st.get('max_steps')} != {args.max_steps}")
            if bad:
                raise SystemExit("incompatible hub checkpoint, refusing to resume: " + "; ".join(bad))
            dst = f"{args.out}/checkpoint-{st['global_step']}"
            os.rename(f"{args.out}/last-checkpoint", dst)
            ckpts = [os.path.basename(dst)]
            print(f"restored {dst} from hub", flush=True)
    except SystemExit:
        raise
    except Exception as e:  # a listed checkpoint that cannot be restored must not become a fresh run
        raise SystemExit(f"hub resume failed ({e}); refusing to train from scratch over {args.hub_repo}")
if ckpts:
    resume = True
    print("resuming from latest checkpoint", flush=True)
t0 = time.time()
result = trainer.train(resume_from_checkpoint=resume)
summary = {**result.metrics, "wall_s": time.time() - t0,
           "peak_gpu_mem_gb": torch.cuda.max_memory_allocated() / 1e9,
           "train_rows": len(train_ds)}
if val_ds is not None:
    summary.update(trainer.evaluate())
json.dump(summary, open(f"{args.out}/logs/train_summary.json", "w"), indent=2)
json.dump(trainer.state.log_history, open(f"{args.out}/logs/log_history.json", "w"), indent=2)
print("SUMMARY", json.dumps(summary), flush=True)

trainer.save_model(f"{args.out}/lora")
processor.save_pretrained(f"{args.out}/lora")
merged = trainer.model.merge_and_unload()
merged.save_pretrained(f"{args.out}/merged", safe_serialization=True)
processor.save_pretrained(f"{args.out}/merged")
import glob as _g
_w = _g.glob(f"{args.out}/merged/*.safetensors")
_ok = bool(_w) and all(os.path.getsize(f) > 0 for f in _w) and os.path.exists(f"{args.out}/merged/config.json") \
    and _g.glob(f"{args.out}/lora/adapter_model*") and (_g.glob(f"{args.out}/merged/*tokenizer*") or _g.glob(f"{args.out}/merged/processor_config.json"))
if not _ok:
    raise SystemExit("export verification failed: merged/lora incomplete")
json.dump({"args": vars(args), "global_step": trainer.state.global_step, "max_steps": trainer.state.max_steps,
           "weights": {os.path.basename(f): os.path.getsize(f) for f in _w}, "summary": summary},
          open(f"{args.out}/train_receipt.json", "w"), indent=2)
print("saved lora + merged (receipt written)", flush=True)
