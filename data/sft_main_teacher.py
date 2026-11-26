"""v4 teacher labels (runs ON a Colab GPU): navigate-then-answer questions + short ScreenQA answers.

Inputs (uploaded next to this script): v4_candidates.json (data/sft_main_select.py), screenqa_rows.json (ScreenQA rows prepared by a one-off script that was not kept; see tag archive/pre-restructure-2026-11-20).
For each candidate AndroidControl episode, the teacher (Qwen3-VL-8B-Instruct) sees the FINAL screen (the screenshot of the
episode's `status complete` row) and the original goal, and writes a question whose answer is readable on that screen,
a reply-format instruction, the answer copied from the screen, and a one-sentence evidence note. A second, independent
call answers the question from the screenshot alone; the label is kept only if both answers agree (normalised).
ScreenQA full-sentence answers are shortened text-only; a short answer is kept only if it is a substring of the original.

Labels are uploaded to <out_repo>/stats/v4_teacher_labels.json every --save_every items and at the end (persist first).
usage: python sft_main_teacher.py --v3_repo experimentalmachines/MobileAgent-SFT-FilledIntents --v3_rev <sha> --out_repo <repo> [--limit N]
"""
import argparse
import io
import json
import os
import re
import time

import pyarrow.parquet as pq
import torch
from huggingface_hub import HfApi, snapshot_download
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

p = argparse.ArgumentParser()
p.add_argument("--v3_repo", required=True)
p.add_argument("--v3_rev", required=True)
p.add_argument("--out_repo", required=True)
p.add_argument("--teacher", default="Qwen/Qwen3-VL-8B-Instruct")
p.add_argument("--bs", type=int, default=32)
p.add_argument("--limit", type=int, default=0, help="smoke test: at most N candidates and N ScreenQA rows")
p.add_argument("--save_every", type=int, default=500)
a = p.parse_args()
t0 = time.time()
api = HfApi()
cands = json.load(open("/content/work/v4_candidates.json"))["candidates"]
sqa = json.load(open("/content/work/screenqa_rows.json"))["rows"]
if a.limit:
    cands, sqa = cands[: a.limit], sqa[: a.limit]
LABEL_PATH = "stats/v4_teacher_labels.json" if not a.limit else "stats/v4_teacher_labels_SMOKE.json"
shards = sorted({c["shard"] for c in cands})
local = snapshot_download(a.v3_repo, repo_type="dataset", revision=a.v3_rev, allow_patterns=shards, max_workers=16,
                          local_dir="/content/data/v3src")
print(f"downloaded {len(shards)} shards in {time.time() - t0:.0f}s", flush=True)
imgs = {}
for sh in shards:
    want = {c["row_in_shard"] for c in cands if c["shard"] == sh}
    col = pq.ParquetFile(os.path.join(local, sh)).read(columns=["images", "img_sha"])
    ims, shas = col.column("images").to_pylist(), col.column("img_sha").to_pylist()
    for i in want:
        imgs[(sh, i)] = (Image.open(io.BytesIO(ims[i][0]["bytes"])).convert("RGB"), shas[i])
for c in cands:  # the row we read must be the row the selector chose
    assert imgs[(c["shard"], c["row_in_shard"])][1] == c["img_sha"], c["key"]
print(f"loaded {len(imgs)} final screens ({time.time() - t0:.0f}s)", flush=True)

proc = AutoProcessor.from_pretrained(a.teacher)
proc.tokenizer.padding_side = "left"
model = AutoModelForImageTextToText.from_pretrained(a.teacher, dtype=torch.bfloat16).to("cuda").eval()

GEN = """This phone screenshot is the final screen after a user finished this task on their phone: "{goal}"
Write ONE question the user could ask next whose answer is clearly readable on this screen (a number, price, name, date, time, rating, count, status or short phrase), and give the answer copied exactly from the screen.
Rules:
- The answer must be visible text on this screenshot, at most 6 words, copied exactly as shown.
- The question must not contain the answer.
- Do not ask about the status bar, battery, network, the current clock time, colors, icons or the layout.
- If the screen shows no such information (blank, loading, keyboard-only or a pure input form), output {{"none": true}}.
{extra}Output JSON only, no other text:
{{"question": "...", {extra_key}"format": "...", "answer": "...", "evidence": "..."}}
format = one short reply instruction such as "Reply with just the number." or "Reply with just the name." or "Answer in a few words."
evidence = one short sentence saying what the screen shows, e.g. "The product page shows the price as Rs 1,299." """
EXTRA_Q = ('- Also write "direct_question": the same question asked on its own, naming the app and any search terms '
           'from the task so that it can be understood without the task text.\n')
VER = """Answer the question using only text visible on this phone screenshot.
Question: {q} {fmt}
Reply with only the answer copied exactly from the screen. If the answer is not visible, reply NONE."""
SHORT = """Question: {q}
Full answer: {ans}
Rewrite the full answer as the shortest phrase that still answers the question (for example a number, a name, a date or a few words). Use only words from the full answer and add nothing. Output only the short answer."""


def norm(s):
    s = str(s or "").lower().strip()
    s = re.sub(r"[\"'`.,:;!?()\[\]{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def agree(x, y):
    x, y = norm(x), norm(y)
    if not x or not y or "none" in (x, y):
        return False
    nx, ny = re.sub(r"[^\d.]", "", x), re.sub(r"[^\d.]", "", y)
    if nx and nx == ny and len(nx) >= 1 and re.fullmatch(r"[^a-z]*", x + y):  # purely numeric: digits must match
        return True
    return x == y or (min(len(x), len(y)) >= 3 and (x in y or y in x))


def generate(convs, max_new):
    inputs = proc.apply_chat_template(convs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                      return_tensors="pt", padding=True).to("cuda")
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_new, do_sample=False)
    return [t.strip() for t in proc.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)]


def parse_json(t):
    m = re.search(r"\{.*\}", t, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None


labels = {"src": f"{a.v3_repo}@{a.v3_rev}", "teacher": a.teacher, "qa": {}, "screenqa_short": {}, "stats": {}}
st = labels["stats"]


def save(final=False):
    st["elapsed_s"] = round(time.time() - t0)
    os.makedirs("/content/eval", exist_ok=True)
    path = "/content/eval/v4_teacher_labels.json"
    json.dump(labels, open(path, "w"))
    api.create_repo(a.out_repo, repo_type="dataset", private=True, exist_ok=True)
    api.upload_file(path_or_fileobj=path, path_in_repo=LABEL_PATH, repo_id=a.out_repo, repo_type="dataset",
                    commit_message=("final" if final else "partial") + " v4 teacher labels")
    print(f"saved labels: {len(labels['qa'])} qa, {len(labels['screenqa_short'])} screenqa ({st['elapsed_s']}s)", flush=True)


# 1) question generation + independent verification
done = 0
for b in range(0, len(cands), a.bs):
    chunk = cands[b:b + a.bs]
    convs = []
    for c in chunk:
        q = c["kind"] == "question"
        txt = GEN.format(goal=c["goal"], extra=EXTRA_Q if q else "", extra_key='"direct_question": "...", ' if q else "")
        convs.append([{"role": "user", "content": [{"type": "image", "image": imgs[(c["shard"], c["row_in_shard"])][0]},
                                                   {"type": "text", "text": txt}]}])
    outs = generate(convs, 200)
    ok = []
    for c, t in zip(chunk, outs):
        j = parse_json(t)
        reason = None
        if not j or j.get("none"):
            reason = "none_or_unparsed"
        elif not all(isinstance(j.get(k), str) and j[k].strip() for k in ("question", "format", "answer", "evidence")):
            reason = "missing_field"
        elif c["kind"] == "question" and not (isinstance(j.get("direct_question"), str) and j["direct_question"].strip()):
            reason = "missing_direct_question"
        elif len(j["answer"].split()) > 6 or norm(j["answer"]) in norm(j["question"]):
            reason = "answer_too_long_or_in_question"
        if reason:
            st[f"gen_reject_{reason}"] = st.get(f"gen_reject_{reason}", 0) + 1
            continue
        ok.append((c, j))
    if ok:
        vconvs = [[{"role": "user", "content": [{"type": "image", "image": imgs[(c["shard"], c["row_in_shard"])][0]},
                                                {"type": "text", "text": VER.format(q=j["question"], fmt=j["format"])}]}]
                  for c, j in ok]
        vouts = generate(vconvs, 32)
        for (c, j), v in zip(ok, vouts):
            if agree(j["answer"], v):
                j["verify_answer"] = v
                labels["qa"][c["key"]] = j
                st["qa_kept"] = st.get("qa_kept", 0) + 1
            else:
                st["verify_reject"] = st.get("verify_reject", 0) + 1
    done += len(chunk)
    if (b // a.bs) % 10 == 0:
        print(f"qa {done}/{len(cands)} kept {st.get('qa_kept', 0)} ({time.time() - t0:.0f}s) e.g. {outs[0][:160]!r}", flush=True)
    if done % a.save_every < a.bs:
        save()
save()

# 2) ScreenQA short answers (text only)
for b in range(0, len(sqa), a.bs * 2):
    chunk = sqa[b:b + a.bs * 2]
    convs = [[{"role": "user", "content": [{"type": "text", "text": SHORT.format(q=r["question"], ans=r["answer"])}]}]
             for r in chunk]
    outs = generate(convs, 32)
    for r, t in zip(chunk, outs):
        s = t.splitlines()[0].strip().strip('"').strip() if t else ""
        s = s.rstrip(".") if not r["answer"].strip().endswith("..") else s
        if s and norm(s) and norm(s) in norm(r["answer"]) and len(s) < len(r["answer"]):
            labels["screenqa_short"][r["key"]] = s
            st["sqa_short"] = st.get("sqa_short", 0) + 1
        else:
            st["sqa_kept_long"] = st.get("sqa_kept_long", 0) + 1
    if (b // (a.bs * 2)) % 10 == 0:
        print(f"screenqa {b + len(chunk)}/{len(sqa)} ({time.time() - t0:.0f}s) e.g. {chunk[0]['answer'][:60]!r} -> {outs[0][:60]!r}",
              flush=True)
save(final=True)
print("TEACHER DONE", json.dumps(st), flush=True)
