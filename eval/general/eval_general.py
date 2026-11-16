"""General-knowledge retention check (run before and after agent SFT).

* MMStar (Lin-Chen/MMStar, 1,500 vision-indispensable multiple-choice questions)
* MMLU (cais/mmlu all/test, fixed random 500-question subset, text only)
Greedy decoding, answer letter parsed from the first A-D in the reply. Writes per-item JSONL + summary.

Usage: python eval_general.py --model <id|path> --out /content/eval/<name>_general [--mmstar_n 1500 --mmlu_n 500]
"""
import argparse
import base64
import io
import json
import os
import random
import re

import torch
from datasets import load_dataset
from huggingface_hub import hf_hub_download
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--mmstar_n", type=int, default=1500)
ap.add_argument("--mmlu_n", type=int, default=1000)
ap.add_argument("--max_pixels", type=int, default=0, help=">0: identical pixel budget for base and FT (Qwen/LFM3 processors)")
ap.add_argument("--max_new_tokens", type=int, default=64)
ap.add_argument("--mode", default="generate", choices=["generate", "logprob"],
                help="logprob = forced choice over A-D next-token logits (immune to answer-format differences)")
ap.add_argument("--bs", type=int, default=16)
a = ap.parse_args()
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)

_pk = {"size": {"shortest_edge": 256 * 256, "longest_edge": a.max_pixels}} if a.max_pixels > 0 else {}
proc = AutoProcessor.from_pretrained(a.model, trust_remote_code=True, **_pk)
proc.tokenizer.padding_side = "left"
model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16, trust_remote_code=True).to("cuda").eval()
INSTR = "Answer with the option's letter from the given choices directly."


_PATTERNS = [
    re.compile(r"^\s*\(?([A-D])\)?\s*[.):]?\s*$"),                      # whole reply is the letter
    re.compile(r"^\s*\(?([A-D])\)?\s*[.):]\s"),                         # "B. text" / "(B) text"
    re.compile(r"(?i)\banswer\s*(?:is|:)?\s*\(?([A-D])\)?(?![A-Za-z])"),  # "... answer is C"
]


def letter(text):
    """Strict: no answer from unfinished reasoning or incidental capitals (e.g. the article 'A')."""
    if "</think>" in text:
        text = text.split("</think>")[-1]
    elif "<think>" in text:
        return None
    for pat in _PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1)
    return None


_LETTER_IDS = None


def _letter_ids():
    global _LETTER_IDS
    if _LETTER_IDS is None:
        tok = proc.tokenizer
        ids = []
        for L in "ABCD":
            cands = [tok.encode(L, add_special_tokens=False), tok.encode(" " + L, add_special_tokens=False)]
            ids.append([c[0] for c in cands if len(c) == 1])
        _LETTER_IDS = ids
    return _LETTER_IDS


def run_logprob(items, kind):
    res = []
    lid = _letter_ids()
    for b in range(0, len(items), a.bs):
        batch = items[b:b + a.bs]
        convs = [[{"role": "user", "content": ([{"type": "image", "image": it["image"]}] if it.get("image") is not None else [])
                   + [{"type": "text", "text": it["prompt"]}]}] for it in batch]
        kw = {"enable_thinking": False} if "enable_thinking" in (proc.chat_template or "") else {}
        inputs = proc.apply_chat_template(convs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                          return_tensors="pt", padding=True, processor_kwargs={"padding": True}, **kw).to("cuda")
        with torch.inference_mode():
            logits = model(**inputs).logits[:, -1, :].float()
        for it, lg in zip(batch, logits):
            scores = [max(lg[i].item() for i in ids) if ids else -1e9 for ids in lid]
            p = "ABCD"[max(range(4), key=lambda j: scores[j])]
            res.append({"kind": kind, "id": it["id"], "gold": it["gold"], "pred": p, "raw": json.dumps(scores),
                        "correct": p == it["gold"], "category": it.get("category")})
        print(kind, b + len(batch), "/", len(items), flush=True)
    return res


def run(items, kind):
    if a.mode == "logprob":
        return run_logprob(items, kind)
    res = []
    for b in range(0, len(items), a.bs):
        batch = items[b:b + a.bs]
        convs = []
        for it in batch:
            content = ([{"type": "image", "image": it["image"]}] if it.get("image") is not None else []) + \
                      [{"type": "text", "text": it["prompt"]}]
            convs.append([{"role": "user", "content": content}])
        kw = {"enable_thinking": False} if "enable_thinking" in (proc.chat_template or "") else {}
        inputs = proc.apply_chat_template(convs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                          return_tensors="pt", padding=True, processor_kwargs={"padding": True},
                                          **kw).to("cuda")
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=a.max_new_tokens, do_sample=False)
        texts = proc.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        for it, t in zip(batch, texts):
            p = letter(t)
            res.append({"kind": kind, "id": it["id"], "gold": it["gold"], "pred": p, "raw": t, "correct": p == it["gold"],
                        "category": it.get("category")})
        print(kind, b + len(batch), "/", len(items), flush=True)
    return res


# MMStar
tsv = hf_hub_download("Lin-Chen/MMStar", "MMStar.tsv", repo_type="dataset")
import csv, sys
csv.field_size_limit(sys.maxsize)
star = list(csv.DictReader(open(tsv, encoding="utf-8"), delimiter="\t"))
random.Random(0).shuffle(star)
items = []
for r in star[: a.mmstar_n]:
    img = Image.open(io.BytesIO(base64.b64decode(r["image"]))).convert("RGB")
    q = r["question"]
    opts = "".join(f"\n{k}. {r[k]}" for k in "ABCD" if r.get(k))
    items.append({"id": r["index"], "image": img, "prompt": f"{q}{opts}\n{INSTR}", "gold": r["answer"].strip()[:1],
                  "category": r.get("category")})
res = run(items, "mmstar")

# MMLU subset
mm = load_dataset("cais/mmlu", "all", split="test")
idx = random.Random(0).sample(range(len(mm)), a.mmlu_n)
items = []
for i in idx:
    r = mm[i]
    opts = "".join(f"\n{'ABCD'[j]}. {c}" for j, c in enumerate(r["choices"]))
    items.append({"id": i, "prompt": f"{r['question']}{opts}\n{INSTR}", "gold": "ABCD"[r["answer"]], "category": r["subject"]})
res += run(items, "mmlu")

with open(a.out + ".jsonl", "w") as f:
    for r in res:
        f.write(json.dumps(r) + "\n")
summ = {}
for k in ("mmstar", "mmlu"):
    rr = [r for r in res if r["kind"] == k]
    summ[k] = {"n": len(rr), "acc": sum(r["correct"] for r in rr) / max(1, len(rr)),
               "unparsed": sum(r["pred"] is None for r in rr) / max(1, len(rr))}
summ["model"] = a.model
summ["max_pixels"] = a.max_pixels
summ["max_new_tokens"] = a.max_new_tokens
summ["mode"] = a.mode
json.dump(summ, open(a.out + ".summary.json.tmp", "w"), indent=1)
os.replace(a.out + ".summary.json.tmp", a.out + ".summary.json")  # atomic
print("GENERAL", json.dumps(summ), flush=True)
