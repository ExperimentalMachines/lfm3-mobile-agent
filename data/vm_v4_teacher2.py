"""v4 teacher pass 2 (Colab GPU): verify the `direct_question` that becomes the training GOAL of question-kind episodes.

Codex's pipeline audit (#5) found that pass 1 verified only `question`, while `direct_question` (unverified) is used as
the goal. Here each direct question must: be one line, not contain the answer, keep the app named in the original goal
(when the goal names one), and be answered from the same final screen by an independent call with a strictly equal
answer (data/v4_answer_check.same_answer). Episodes that fail fall back to the verified compound goal in the builder.
Output: <repo>/stats/v4_direct_check.json  {key: {"ok": bool, "reason": str, "answer2": str}}
"""
import io
import json
import os
import re
import time

import pyarrow.parquet as pq
import torch
from huggingface_hub import HfApi, hf_hub_download, snapshot_download
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

from v4_answer_check import norm, preferred, same_answer

REPO, V3, V3_REV = "alpharomercoma/AndroidAgent-SFT-v4", "alpharomercoma/AndroidAgent-SFT-v3", "565ba76c4b10b6733549151f0fece1f70bc33b9c"
t0 = time.time()
labels = json.load(open(hf_hub_download(REPO, "stats/v4_teacher_labels.json", repo_type="dataset")))
cands = {c["key"]: c for c in json.load(open("/content/work/v4_candidates.json"))["candidates"]}
todo = [k for k, v in labels["qa"].items() if cands[k]["kind"] == "question" and same_answer(v["answer"], v.get("verify_answer"))]
out = {}
APP = re.compile(r"\b(?:on|in|using|with|from|via|at)\s+(?:the\s+)?([A-Z][\w&.'+-]*(?:\s+[A-Z][\w&.'+-]*){0,3})\s+app\b")
pending = []
for k in todo:
    j, g = labels["qa"][k], cands[k]["goal"]
    dq = (j.get("direct_question") or "").strip()
    ans = preferred(j["answer"], j.get("verify_answer"))
    m = APP.search(g)
    if not dq or "\n" in dq or len(dq) > 300:
        out[k] = {"ok": False, "reason": "empty_or_multiline"}
    elif norm(ans) and norm(ans) in norm(dq):
        out[k] = {"ok": False, "reason": "answer_in_question"}
    elif m and m.group(1).lower() not in dq.lower():
        out[k] = {"ok": False, "reason": f"app_missing:{m.group(1)}"}
    else:
        pending.append(k)
print(f"{len(todo)} question-kind labels; {len(pending)} to verify; pre-rejected {len(out)}", flush=True)
shards = sorted({cands[k]["shard"] for k in pending})
local = snapshot_download(V3, repo_type="dataset", revision=V3_REV, allow_patterns=shards, max_workers=16,
                          local_dir="/content/data/v3src")
imgs = {}
for sh in shards:
    col = pq.ParquetFile(os.path.join(local, sh)).read(columns=["images", "img_sha"])
    ims, shas = col.column("images").to_pylist(), col.column("img_sha").to_pylist()
    for k in pending:
        if cands[k]["shard"] == sh:
            i = cands[k]["row_in_shard"]
            assert shas[i] == cands[k]["img_sha"], k
            imgs[k] = Image.open(io.BytesIO(ims[i][0]["bytes"])).convert("RGB")
proc = AutoProcessor.from_pretrained(labels["teacher"])
proc.tokenizer.padding_side = "left"
model = AutoModelForImageTextToText.from_pretrained(labels["teacher"], dtype=torch.bfloat16).to("cuda").eval()
VER = """Answer the question using only text visible on this phone screenshot.
Question: {q} {fmt}
Reply with only the answer copied exactly from the screen. If the answer is not visible, reply NONE."""
for b in range(0, len(pending), 32):
    ks = pending[b:b + 32]
    convs = [[{"role": "user", "content": [{"type": "image", "image": imgs[k]},
                                           {"type": "text", "text": VER.format(q=labels["qa"][k]["direct_question"].strip(),
                                                                               fmt=labels["qa"][k]["format"].strip())}]}]
             for k in ks]
    inputs = proc.apply_chat_template(convs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                      return_tensors="pt", padding=True).to("cuda")
    with torch.inference_mode():
        o = model.generate(**inputs, max_new_tokens=32, do_sample=False)
    texts = [t.strip() for t in proc.batch_decode(o[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)]
    for k, t in zip(ks, texts):
        ans = preferred(labels["qa"][k]["answer"], labels["qa"][k].get("verify_answer"))
        out[k] = {"ok": same_answer(ans, t), "reason": "verified" if same_answer(ans, t) else "answer_mismatch", "answer2": t}
    print(f"{b + len(ks)}/{len(pending)} ({time.time() - t0:.0f}s)", flush=True)
json.dump(out, open("/content/eval/v4_direct_check.json", "w"))
HfApi().upload_file(path_or_fileobj="/content/eval/v4_direct_check.json", path_in_repo="stats/v4_direct_check.json",
                    repo_id=REPO, repo_type="dataset", commit_message="direct-question verification")
from collections import Counter  # noqa: E402

print("DIRECT CHECK DONE", json.dumps(Counter(v["reason"].split(":")[0] for v in out.values())), flush=True)
