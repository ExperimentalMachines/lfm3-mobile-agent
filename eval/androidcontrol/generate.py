"""Offline step-level generation on a held-out split (runs on the Colab GPU).

Reads an eval dataset built by data/build_sft_data.py (columns: images, messages,
episode_id, step_idx, gt_action, gt_bbox, split_tag, ...), re-renders the prompt from
messages[:-1] (system+user), generates with HF transformers, and writes one JSONL row
per step with the RAW model output. Scoring happens separately in score.py.
"""

import argparse
import json
import os
import time

import torch
from datasets import load_dataset, load_from_disk
from transformers import AutoModelForImageTextToText, AutoProcessor

p = argparse.ArgumentParser()
p.add_argument("--model", required=True)
p.add_argument("--data", required=True)
p.add_argument("--out", required=True)
p.add_argument("--limit", type=int, default=0)
p.add_argument("--bs", type=int, default=32)
p.add_argument("--max_new_tokens", type=int, default=256)
p.add_argument("--enable_thinking", type=int, default=1)
p.add_argument("--max_pixels", type=int, default=880 * 880)
p.add_argument("--min_pixels", type=int, default=256 * 256)
p.add_argument("--filter_mode", default=None, help="only rows with this mode (high/low)")
p.add_argument("--subsample_episodes", type=int, default=0, help="deterministic episode subsample")
args = p.parse_args()

if os.path.isdir(args.data):
    ds = load_from_disk(args.data)
else:
    _repo, _, _split = args.data.partition("@")
    _split = _split or "test"
    ds = load_dataset(_repo, data_files={_split: f"data/{_split}/*.parquet"}, split=_split)
if args.filter_mode:
    ds = ds.filter(lambda m: m == args.filter_mode, input_columns="mode")
if args.subsample_episodes:
    import random as _r
    eps = sorted(set(ds["episode_id"]))
    keep = set(_r.Random(0).sample(eps, min(args.subsample_episodes, len(eps))))
    ds = ds.filter(lambda e: e in keep, input_columns="episode_id")
if args.limit:
    ds = ds.select(range(min(args.limit, len(ds))))
processor = AutoProcessor.from_pretrained(
    args.model, trust_remote_code=True,
    size={"shortest_edge": args.min_pixels, "longest_edge": args.max_pixels})
processor.tokenizer.padding_side = "left"
model = AutoModelForImageTextToText.from_pretrained(
    args.model, dtype=torch.bfloat16, trust_remote_code=True).to("cuda").eval()

manifest = {"model": args.model, "data": args.data, "n_rows": len(ds), "enable_thinking": args.enable_thinking,
            "max_pixels": args.max_pixels, "filter_mode": args.filter_mode, "subsample_episodes": args.subsample_episodes,
            "limit": args.limit, "max_new_tokens": args.max_new_tokens}
mpath = args.out + ".manifest.json"
if os.path.exists(mpath):
    old_m = json.load(open(mpath))
    if old_m["model"] != args.model or old_m["n_rows"] != len(ds):
        raise SystemExit(f"refusing to resume {args.out}: manifest mismatch {old_m} vs {manifest}")
json.dump(manifest, open(mpath, "w"), indent=1)
done = set()
if os.path.exists(args.out):
    for line in open(args.out):
        r = json.loads(line)
        done.add((r["episode_id"], r["step_idx"], r.get("mode", "high")))
fout = open(args.out, "a")


def to_mm(messages, image):
    sys_m, user_m = messages[0], messages[1]
    return [
        {"role": "system", "content": [{"type": "text", "text": sys_m["content"]}]},
        {"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": user_m["content"]}]},
    ]


_e, _s, _m = ds["episode_id"], ds["step_idx"], ds["mode"]
idx = [i for i in range(len(ds)) if (_e[i], _s[i], _m[i]) not in done]
print(f"to generate: {len(idx)} / {len(ds)}", flush=True)
t0 = time.time()
n_tok_in = 0
for b in range(0, len(idx), args.bs):
    rows = [ds[i] for i in idx[b:b + args.bs]]
    convs = [to_mm(r["messages"], r["images"][0]) for r in rows]
    inputs = processor.apply_chat_template(
        convs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
        processor_kwargs={"padding": True}, enable_thinking=bool(args.enable_thinking),
    ).to("cuda")
    n_tok_in += int(inputs["attention_mask"].sum())
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                             repetition_penalty=1.0)
    gen = out[:, inputs["input_ids"].shape[1]:]
    texts = processor.batch_decode(gen, skip_special_tokens=False)
    for r, t in zip(rows, texts):
        t = t.replace(processor.tokenizer.pad_token, "")
        for eos in ("<|im_end|>", "<|endoftext|>"):
            t = t.split(eos)[0]
        rec = {k: r[k] for k in r.keys() if k not in ("images", "messages")}
        rec["output"] = t
        rec["model"] = args.model
        fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    fout.flush()
    el = time.time() - t0
    print(f"{b + len(rows)}/{len(idx)} {el:.0f}s avg_prompt_tok={n_tok_in / (b + len(rows)):.0f}", flush=True)
print("DONE", time.time() - t0, flush=True)
