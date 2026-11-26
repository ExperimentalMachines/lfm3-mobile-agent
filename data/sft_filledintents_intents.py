"""v3 data = v2 data with every blank training intent filled (runs ON a Colab GPU).

Why: LFM3-VL-2B trained on v2 emitted an empty <think> on 52% of AndroidWorld steps (v1: 0%) because 8,739 v2 rows
(AMEX: no per-step instruction; GUI-Odyssey: model-generated instructions blanked when they contradicted the action)
carry an empty intent. Small agents trained without intents act blindly (MIRAGE: action-only SFT < base).

Fill rule (the action itself is never changed):
  click / long_press -> a teacher VLM (Qwen3-VL-8B-Instruct) sees the training screenshot with a red ring at the
                        recorded point plus the goal, and writes ONE short AndroidControl-style instruction
                        ("Click on the search bar."). Unusable outputs -> the row is dropped (counted).
  scroll / input_text / navigate_* / keyboard_enter / wait / open_app -> deterministic AC-style templates.
History lines are left as they are. Dev splits are copied unchanged (their intents are not scored).

usage: python sft_filledintents_intents.py --src experimentalmachines/MobileAgent-SFT-MultiSource --rev <sha> \
         --out_repo experimentalmachines/MobileAgent-SFT-FilledIntents [--teacher Qwen/Qwen3-VL-8B-Instruct --bs 32]
"""
import argparse
import json
import os
import re
import time
from collections import Counter

import torch
from datasets import DatasetDict, load_dataset
from huggingface_hub import HfApi
from PIL import ImageDraw
from transformers import AutoModelForImageTextToText, AutoProcessor

p = argparse.ArgumentParser()
p.add_argument("--src", required=True)
p.add_argument("--rev", required=True)
p.add_argument("--out_repo", required=True)
p.add_argument("--teacher", default="Qwen/Qwen3-VL-8B-Instruct")
p.add_argument("--bs", type=int, default=32)
p.add_argument("--limit", type=int, default=0, help="debug: label at most N teacher rows")
p.add_argument("--labels_from", default="", help="rebuild from saved labels (stats/v3_intent_labels.json in this "
               "dataset repo) instead of running the teacher; CPU only")
a = p.parse_args()

api = HfApi()
files = api.list_repo_files(a.src, repo_type="dataset", revision=a.rev)
# parallel shard download first (load_dataset fetches shards one by one and stalled once on Modal)
from huggingface_hub import snapshot_download
t_dl = time.time()
local = snapshot_download(a.src, repo_type="dataset", revision=a.rev, allow_patterns=["data/*"], max_workers=16,
                          local_dir="/content/data/v2src")
print(f"downloaded v2 shards in {time.time() - t_dl:.0f}s", flush=True)
splits = {s: [os.path.join(local, f) for f in files if f.startswith(f"data/{s}-")]
          for s in ("train", "dev_odyssey", "dev_amex", "dev_screenqa")}
dd = DatasetDict({s: load_dataset("parquet", data_files={s: fs}, split=s) for s, fs in splits.items()})
train = dd["train"]
print({k: len(v) for k, v in dd.items()}, flush=True)

TEMPL = {
    "scroll": lambda x: {"down": "Scroll down to see more content.", "up": "Scroll up to see the content above.",
                         "left": "Swipe left to see more.", "right": "Swipe right to see more."}[x["direction"]],
    "input_text": lambda x: f"Type '{x['text'].strip()[:60]}' into the text field.",
    "navigate_back": lambda x: "Go back to the previous screen.",
    "navigate_home": lambda x: "Go to the home screen.",
    "keyboard_enter": lambda x: "Press enter to submit.",
    "wait": lambda x: "Wait for the screen to finish loading.",
    "open_app": lambda x: f"Open the {x['app_name']} app.",
}
msgs_col = train["messages"]
acts = [json.loads(g) for g in train["gt_action"]]
blank = [i for i, m in enumerate(msgs_col) if not (m[2].get("reasoning_content") or "").strip()
         and acts[i]["action_type"] not in ("status", "answer")]
teach = [i for i in blank if acts[i]["action_type"] in ("click", "long_press")]
if a.limit:
    teach = teach[: a.limit]
st = Counter(blank_rows=len(blank), teacher_rows=len(teach))
fill = {}
for i in blank:
    t = acts[i]["action_type"]
    if t in TEMPL:
        fill[i] = TEMPL[t](acts[i]); st[f"template_{t}"] += 1

if a.labels_from:
    from huggingface_hub import hf_hub_download
    saved = json.load(open(hf_hub_download(a.labels_from, "stats/v3_intent_labels.json", repo_type="dataset")))
    assert saved["src"] == f"{a.src}@{a.rev}", saved["src"]
    fill = {int(k): v for k, v in saved["fill"].items()}
    teach = []  # skip the teacher loop below
    st["rebuilt_from_saved_labels"] = len(fill)
    st["teacher_ok"] = sum(1 for i in fill if acts[i]["action_type"] in ("click", "long_press"))
    _saved_drop = set(saved["dropped"])
else:
    _saved_drop = set()
proc = AutoProcessor.from_pretrained(a.teacher) if not a.labels_from else None
if proc is not None:
    proc.tokenizer.padding_side = "left"
    model = AutoModelForImageTextToText.from_pretrained(a.teacher, dtype=torch.bfloat16).to("cuda").eval()
BAD = re.compile(r"[{}\[\]]|json|coordinate|red (circle|ring)|\bcircle\b|marked|screenshot|\(\d", re.I)


def goal_of(m):
    u = m[1]["content"]
    return u.split("\n", 1)[0].removeprefix("Goal: ").strip()


def ring(img, pt, lp):
    img = img.convert("RGB").copy()
    W, H = img.size
    x, y = pt[0] / 1000 * (W - 1), pt[1] / 1000 * (H - 1)
    r = max(10, int(0.035 * W))
    d = ImageDraw.Draw(img)
    for k in range(3):
        d.ellipse([x - r - k, y - r - k, x + r + k, y + r + k], outline=(255, 0, 0))
    return img


t0 = time.time()
for b in range(0, len(teach), a.bs):
    idx = teach[b:b + a.bs]
    rows = train.select(idx)
    convs = []
    for r in rows:
        act = json.loads(r["gt_action"])
        verb = "long press" if act["action_type"] == "long_press" else "tap"
        q = (f'This phone screenshot is one step of a task. Task goal: "{goal_of(r["messages"])}".\n'
             f"The user's next action is a {verb} on the element inside the red ring.\n"
             "Write the instruction for this single step as ONE short imperative sentence (at most 12 words) that names "
             "the element by its visible text or icon, in this style: \"Click on the search bar.\" / "
             "\"Select the 'Add to cart' button.\" / \"Open the settings menu.\" Do not mention the ring, the screenshot "
             "or coordinates. Output only the sentence.")
        convs.append([{"role": "user", "content": [{"type": "image", "image": ring(r["images"][0], act["point_2d"], verb)},
                                                   {"type": "text", "text": q}]}])
    inputs = proc.apply_chat_template(convs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                      return_tensors="pt", padding=True).to("cuda")
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=32, do_sample=False)
    texts = proc.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    for i, t in zip(idx, texts):
        s = t.strip().splitlines()[0].strip().strip('"').strip() if t.strip() else ""
        if s and not s.endswith("."):
            s += "."
        if not s or BAD.search(s) or len(s.split()) > 20:
            st["teacher_rejected"] += 1
            continue
        fill[i] = s
        st["teacher_ok"] += 1
    if (b // a.bs) % 20 == 0:
        print(f"{b + len(idx)}/{len(teach)} {time.time() - t0:.0f}s  e.g. {texts[0].strip()[:80]!r}", flush=True)

drop = set(i for i in teach if i not in fill) | _saved_drop
st["dropped_rows"] = len(drop)
if proc is not None:  # free the teacher before the multi-process push (forked workers OOM'd on a full GPU)
    del model
    torch.cuda.empty_cache()
# durable copy of the labels BEFORE the slow full-dataset push (a failed upload must not lose the labeling)
os.makedirs("/content/eval", exist_ok=True)
json.dump({"src": f"{a.src}@{a.rev}", "teacher": a.teacher, "fill": {str(k): v for k, v in fill.items()},
           "dropped": sorted(drop)}, open("/content/eval/v3_intent_labels.json", "w"))
api.create_repo(a.out_repo, repo_type="dataset", private=True, exist_ok=True)
if not a.labels_from:
    api.upload_file(path_or_fileobj="/content/eval/v3_intent_labels.json", path_in_repo="stats/v3_intent_labels.json",
                    repo_id=a.out_repo, repo_type="dataset")
print("labels saved" if not a.labels_from else "labels reused", len(fill), flush=True)


def apply(ex, i):
    if i in fill:
        m = ex["messages"]
        m[2]["reasoning_content"] = fill[i]
        ex["messages"] = m
    return ex


new_train = train.map(apply, with_indices=True, num_proc=8)
if drop:
    new_train = new_train.select([i for i in range(len(new_train)) if i not in drop])
left = sum(1 for m in new_train["messages"] if not (m[2].get("reasoning_content") or "").strip())
st["train_rows"], st["blank_intents_left"] = len(new_train), left
_tk = [i for i in sorted(fill) if acts[i]["action_type"] in ("click", "long_press")]
samples = [{"row": i, "source": train[i]["source"], "action": acts[i], "intent": fill[i]} for i in _tk[:300]]
print(json.dumps(st), flush=True)
out = DatasetDict({"train": new_train, **{k: v for k, v in dd.items() if k != "train"}})
api.create_repo(a.out_repo, repo_type="dataset", private=True, exist_ok=True)
# single process: push_to_hub(num_proc>1) spawns workers that re-run this whole top-level script (that is what
# OOM'd the H100 - every worker loaded the teacher - and broke the CPU rebuild). xet high-performance does the speed.
t_up = time.time()
out.push_to_hub(a.out_repo, private=True, max_shard_size="500MB")
print(f"pushed shards in {time.time() - t_up:.0f}s", flush=True)
os.makedirs("/content/eval", exist_ok=True)
json.dump({"stats": st, "src": f"{a.src}@{a.rev}", "teacher": a.teacher, "samples": samples},
          open("/content/eval/v3_intents_stats.json", "w"), indent=1)
api.upload_file(path_or_fileobj="/content/eval/v3_intents_stats.json", path_in_repo="stats/v3_intents.json",
                repo_id=a.out_repo, repo_type="dataset")
print("pushed", a.out_repo, api.dataset_info(a.out_repo).sha, flush=True)
