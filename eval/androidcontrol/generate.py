"""Offline step-level generation on a held-out split (runs on the Colab GPU).

Reads an eval dataset built by data/build_sft_data.py (columns: images, messages,
episode_id, step_idx, gt_action, gt_bbox, split_tag, ...), re-renders the prompt from
messages[:-1] (system+user), generates with HF transformers, and writes one JSONL row
per step with the RAW model output. Scoring happens separately in score.py.
"""

import argparse
import hashlib
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
p.add_argument("--prompt_v4_pool", default="", help="JSON list of training app names: rewrite stored v1 prompts to the "
               "v4 prompt + installed-app list (agent_format.to_v4_messages) for v4 models")
args = p.parse_args()

def _hub_data_files(repo, split, revision=None):
    """v1 repos use data/<split>/*.parquet; push_to_hub (v2) writes data/<split>-NNNNN-of-NNNNN.parquet."""
    from huggingface_hub import HfApi
    files = HfApi().list_repo_files(repo, repo_type="dataset", revision=revision)
    if any(f.startswith(f"data/{split}/") for f in files):
        return {split: f"data/{split}/*.parquet"}
    return {split: f"data/{split}-*.parquet"}


if os.path.isdir(args.data):
    ds = load_from_disk(args.data)
else:
    _repo, _, _split = args.data.partition("@")
    _split, _, _rev = _split.partition("#")  # 'org/repo@split#revision' pins an immutable dataset revision
    _split, _rev = _split or "test", _rev or None
    ds = load_dataset(_repo, data_files=_hub_data_files(_repo, _split, _rev), split=_split, revision=_rev)
for _col, _val in (("mode", "high"), ("gt_bbox", "")):  # v2 dev splits lack these v1 columns
    if _col not in ds.column_names:
        ds = ds.add_column(_col, [_val] * len(ds))
if args.filter_mode:
    ds = ds.filter(lambda m: m == args.filter_mode, input_columns="mode")
if args.subsample_episodes:
    import random as _r
    eps = sorted(set(ds["episode_id"]))
    keep = set(_r.Random(0).sample(eps, min(args.subsample_episodes, len(eps))))
    ds = ds.filter(lambda e: e in keep, input_columns="episode_id")
if args.limit:
    ds = ds.select(range(min(args.limit, len(ds))))
_pk = {"size": {"shortest_edge": args.min_pixels, "longest_edge": args.max_pixels}} if args.max_pixels > 0 else {}
processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=True, **_pk)
processor.tokenizer.padding_side = "left"
model = AutoModelForImageTextToText.from_pretrained(
    args.model, dtype=torch.bfloat16, trust_remote_code=True).to("cuda").eval()

manifest = {"model": args.model, "data": args.data, "n_rows": len(ds), "enable_thinking": args.enable_thinking,
            "max_pixels": args.max_pixels, "filter_mode": args.filter_mode, "subsample_episodes": args.subsample_episodes,
            "limit": args.limit, "max_new_tokens": args.max_new_tokens, "do_sample": False, "min_pixels": args.min_pixels}
if args.prompt_v4_pool:
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "train"))
    import agent_format as af
    _POOL = json.load(open(args.prompt_v4_pool))
    manifest["prompt"] = "v4:" + hashlib.sha256(json.dumps(_POOL).encode()).hexdigest()[:12]


def v4_msgs(r):
    """v4 prompt for a stored v1 row: required apps = open_app names in the history + the gold open_app (if any)."""
    if r["messages"][1]["content"].startswith("Goal: ") and "\nInstalled apps: " in r["messages"][1]["content"]:
        return r["messages"]  # already a v4 row (v4 dev splits)
    req = af.apps_in_text(r["messages"][1]["content"])
    g = json.loads(r["gt_action"]) if isinstance(r.get("gt_action"), str) else (r.get("gt_action") or {})
    if g.get("action_type") == "open_app":
        req.append(g["app_name"])
    return af.to_v4_messages(r["messages"], af.v4_app_list(str(r["episode_id"]), req, _POOL))
import glob as _glob


def _fingerprint(model):
    """Distinguish different weights behind the same local path (e.g. after retraining)."""
    if not os.path.isdir(model):
        return "hub:" + model
    h = hashlib.sha256()
    rec = os.path.join(os.path.dirname(model.rstrip("/")), "train_receipt.json")
    if os.path.exists(rec):
        h.update(open(rec, "rb").read())
    for f in sorted(_glob.glob(os.path.join(model, "*.safetensors"))):
        h.update(f"{os.path.basename(f)}:{os.path.getsize(f)}".encode())
        with open(f, "rb") as fh:
            h.update(fh.read(4 << 20))
    return h.hexdigest()[:16]


manifest["model_fingerprint"] = _fingerprint(args.model)
cfg_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
manifest["config_hash"] = cfg_hash
mpath = args.out + ".manifest.json"
push_repo = os.environ.get("EVAL_PUSH_REPO")
if push_repo and not os.path.exists(args.out) and not os.path.exists(mpath):
    # VM was lost? restore the prediction/manifest PAIR from one hub revision; never one without the other
    try:
        from huggingface_hub import HfApi, hf_hub_download
        rev = HfApi().repo_info(push_repo).sha
        stage = "/tmp/_restore"
        got = [hf_hub_download(push_repo, f"eval/{os.path.basename(f)}", revision=rev, local_dir=stage) for f in (mpath, args.out)]
        if json.load(open(got[0])) == manifest:
            os.replace(got[0], mpath)
            os.replace(got[1], args.out)
            print(f"restored partial predictions from hub @ {rev[:8]}", flush=True)
        else:
            print("hub partial has a different manifest; starting fresh", flush=True)
    except Exception as e:
        print("no complete hub partial to restore:", type(e).__name__, flush=True)
if os.path.exists(args.out) and not os.path.exists(mpath):
    raise SystemExit(f"refusing to reuse {args.out}: predictions exist without a manifest (unknown identity)")
if os.path.exists(mpath):
    old_m = json.load(open(mpath))
    if old_m != manifest:
        raise SystemExit(f"refusing to resume {args.out}: manifest differs\nold={old_m}\nnew={manifest}")
else:
    json.dump(manifest, open(mpath, "w"), indent=1)


def _push_partial():
    if not push_repo:
        return
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        for f in (args.out, mpath):
            api.upload_file(path_or_fileobj=f, path_in_repo=f"eval/{os.path.basename(f)}", repo_id=push_repo)
    except Exception as e:
        print("partial push failed:", e, flush=True)


done = set()
if os.path.exists(args.out):
    for line in open(args.out):
        r = json.loads(line)
        if r.get("config_hash") != cfg_hash:
            raise SystemExit(f"refusing to resume {args.out}: row config_hash {r.get('config_hash')} != {cfg_hash}")
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
    convs = [to_mm(v4_msgs(r) if args.prompt_v4_pool else r["messages"], r["images"][0]) for r in rows]
    _kw = {"enable_thinking": bool(args.enable_thinking)} if "enable_thinking" in (processor.chat_template or "") else {}
    inputs = processor.apply_chat_template(
        convs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
        padding=True, processor_kwargs={"padding": True}, **_kw,
    ).to("cuda")
    n_tok_in += int(inputs["attention_mask"].sum())
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                             repetition_penalty=1.0)
    gen = out[:, inputs["input_ids"].shape[1]:]
    texts = processor.batch_decode(gen, skip_special_tokens=False)
    # if the prompt itself opened a think block (template prefill), keep it so an unclosed
    # thought can never be mistaken for a final action by the parser
    _tail = processor.tokenizer.decode(inputs["input_ids"][0][-4:], skip_special_tokens=False)
    if _tail.rstrip().endswith("<think>"):
        texts = ["<think>" + t for t in texts]
    for r, t in zip(rows, texts):
        t = t.replace(processor.tokenizer.pad_token, "")
        for eos in ("<|im_end|>", "<|endoftext|>"):
            t = t.split(eos)[0]
        rec = {k: r[k] for k in r.keys() if k not in ("images", "messages")}
        rec["output"] = t
        rec["model"] = args.model
        rec["config_hash"] = cfg_hash
        fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    fout.flush()
    el = time.time() - t0
    print(f"{b + len(rows)}/{len(idx)} {el:.0f}s avg_prompt_tok={n_tok_in / (b + len(rows)):.0f}", flush=True)
    if (b // args.bs) % 40 == 39:
        _push_partial()
fout.close()
_push_partial()
print("DONE", time.time() - t0, flush=True)
