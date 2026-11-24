"""Completion judge for the training `status` rows (round 8 audit, docs/PREREG_v46.md). Runs on a GPU (Modal).
Qwen/Qwen3-VL-8B-Instruct (Apache-2.0, pinned) sees ONLY the goal and the final screenshot (not the agent's history,
so it cannot copy completion from it) and answers COMPLETE / NOT_COMPLETE / PENDING / UNSURE plus a one-line reason.
Usage: python judge_terminal.py <terminal.parquet> <out.jsonl> [--episodes ids.json] [--model ID --rev SHA]
"""
import argparse
import io
import json
import os

import pyarrow.parquet as pq
import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

ap = argparse.ArgumentParser()
ap.add_argument("data")
ap.add_argument("out")
ap.add_argument("--episodes", default="", help="JSON list of AndroidControl episode ids to judge (calibration)")
ap.add_argument("--model", default="Qwen/Qwen3-VL-8B-Instruct")
ap.add_argument("--rev", default="0c351dd01ed87e9c1b53cbc748cba10e6187ff3b")
ap.add_argument("--bs", type=int, default=16)
ap.add_argument("--strict_from", default="", help="stage 2: re-judge only the rows this verdicts file calls NOT_COMPLETE, "
                "with the strict prompt (CONTRADICTS / NO_PROOF)")
a = ap.parse_args()

PROMPT = """You check whether a phone task is finished, using ONLY this screenshot.
Task: {goal}
Reply with exactly one of these words on the first line:
COMPLETE - the screenshot shows the task done (the item is saved, sent, set, added, deleted or changed as asked, or the requested information or page is shown).
NOT_COMPLETE - the screenshot shows the task is not done (the asked-for change is not visible, a different item or value is shown, or a required confirmation or step is still missing).
PENDING - the screen is still loading, processing or in progress.
UNSURE - this screenshot cannot show whether the task is done.
On the second line give a one-sentence reason."""
LABELS = ("NOT_COMPLETE", "COMPLETE", "PENDING", "UNSURE")
STRICT = """You check a phone task using ONLY this screenshot.
Task: {goal}
Does something VISIBLE on this screenshot show that the task was NOT done? For example: a different item, value, date,
time or setting than the task asks for is shown; an error message; the screen where the result would appear shows it
missing; the task's text is typed but obviously not submitted.
Reply with exactly one word on the first line:
CONTRADICTS - something visible shows the task is not done.
NO_PROOF - nothing visible contradicts it; the screenshot just does not prove it (the effect is elsewhere, already
happened, or is not shown on this screen).
On the second line give a one-sentence reason."""
STRICT_LABELS = ("CONTRADICTS", "NO_PROOF")

rows = pq.read_table(a.data).to_pylist()
if a.strict_from:
    flagged = {(x["source"], str(x["episode_id"]), int(x["step_idx"])) for x in map(json.loads, open(a.strict_from)) if x["verdict"] == "NOT_COMPLETE"}
    rows = [r for r in rows if (r["source"], str(r["episode_id"]), int(r["step_idx"])) in flagged]
    PROMPT, LABELS = STRICT, STRICT_LABELS
if a.episodes:
    keep = set(json.load(open(a.episodes)))
    rows = [r for r in rows if r["source"] == "androidcontrol" and str(r["episode_id"]) in keep]
done = set()
if os.path.exists(a.out):
    done = {(json.loads(l)["source"], json.loads(l)["episode_id"], json.loads(l)["step_idx"]) for l in open(a.out)}
rows = [r for r in rows if (r["source"], r["episode_id"], r["step_idx"]) not in done]
print("rows to judge", len(rows), flush=True)
proc = AutoProcessor.from_pretrained(a.model, revision=a.rev)
proc.tokenizer.padding_side = "left"
model = AutoModelForImageTextToText.from_pretrained(a.model, revision=a.rev, dtype=torch.bfloat16).to("cuda").eval()
with open(a.out, "a") as fo:
    for i in range(0, len(rows), a.bs):
        b = rows[i:i + a.bs]
        msgs = [[{"role": "user", "content": [{"type": "image", "image": Image.open(io.BytesIO(r["image"])).convert("RGB")},
                                              {"type": "text", "text": PROMPT.format(goal=r["goal"])}]}] for r in b]
        inp = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
                                       padding=True).to("cuda")
        with torch.no_grad():
            out = model.generate(**inp, max_new_tokens=60, do_sample=False)
        texts = proc.batch_decode(out[:, inp["input_ids"].shape[1]:], skip_special_tokens=True)
        for r, t in zip(b, texts):
            first = t.strip().split("\n", 1)[0].upper()
            label = next((x for x in LABELS if x in first.replace(" ", "_")), "UNPARSED")
            fo.write(json.dumps({"source": r["source"], "episode_id": r["episode_id"], "step_idx": r["step_idx"], "goal": r["goal"],
                                 "verdict": label, "text": t.strip()[:300]}) + "\n")
        fo.flush()
        if (i // a.bs) % 50 == 0:
            print(f"{i + len(b)}/{len(rows)}", flush=True)
print("JUDGE DONE", flush=True)
