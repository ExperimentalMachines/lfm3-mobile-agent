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
ap.add_argument("--mmlu_n", type=int, default=500)
ap.add_argument("--bs", type=int, default=16)
a = ap.parse_args()
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)

proc = AutoProcessor.from_pretrained(a.model, trust_remote_code=True)
proc.tokenizer.padding_side = "left"
model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16, trust_remote_code=True).to("cuda").eval()
INSTR = "Answer with the option's letter from the given choices directly."


def letter(text):
    text = text.split("</think>")[-1]
    m = re.search(r"\b([A-D])\b", text.strip())
    return m.group(1) if m else None


def run(items, kind):
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
            out = model.generate(**inputs, max_new_tokens=24, do_sample=False)
        texts = proc.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        for it, t in zip(batch, texts):
            p = letter(t)
            res.append({"kind": kind, "id": it["id"], "gold": it["gold"], "pred": p, "raw": t[:80], "correct": p == it["gold"],
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
json.dump(summ, open(a.out + ".summary.json", "w"), indent=1)
print("GENERAL", json.dumps(summ), flush=True)
