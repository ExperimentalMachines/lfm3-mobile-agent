"""Round 5, candidate P (docs/PREREG_v41.md, 2026-11-22 17:00): preference pairs from the model's OWN mistakes.

v4.2 decodes greedily (as at inference: thinking on, temperature 0) on a deterministic sample of its own training rows
(v4.2's training data, rebuilt by data/v42_selfhist.py). Where its action fails the AndroidControl scorer's `match`
(eval/androidcontrol/score.py: action type, click within 14% of the screen, text F1 >= 0.5, same scroll direction /
app / status), the row becomes a pair:
  preferred = the human step (intent + action, the row's training target), rejected = v4.2's own step.
Rules (pre-declared): training rows only (every row of the v4.2 training data is a training row; AndroidControl
val/test episode ids and AndroidWorld app names are checked again here); rows whose human step is `wait` are skipped
(noisy labels); intent wording alone never makes a rejection; unparseable outputs are never used as rejections.
Terminal rows (human `status`) are sampled at a fixed share so that "missed stop" mistakes are represented.

Output: a datasets dir with columns images, prompt_json ([system, user] messages, user text without the image),
chosen_json / rejected_json ({"intent", "action"}), kind, source, episode_id, step_idx; plus pairs_stats.json.
Usage (Colab): python v5_pairs.py --data V42_DISK --model V42_MERGED --out PAIRS_DISK --work DIR [--n_rows 16000]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_format as af  # noqa: E402  (copied next to this file on the VM)
from score import match  # noqa: E402

AW_APP_RE = re.compile("|".join([   # same list as data/build_v2_mix.py (AndroidWorld-specific apps)
    r"simple ?calendar", r"\bmarkor\b", r"pro ?expense", r"\bbroccoli\b", r"\bjoplin\b", r"\bosm ?and\b",
    r"retro ?music", r"\bvlc\b", r"simple ?sms", r"audio ?recorder", r"simple ?draw", r"open ?tracks",
    r"simple ?gallery", r"tasks\.org", r"calendar ?pro", r"(voice|sound) ?recorder"]), re.I)


def h01(*parts) -> float:
    return int(hashlib.sha256(":".join(map(str, parts)).encode()).hexdigest()[:12], 16) / 16 ** 12


def last_intent(user_text: str) -> str:
    hist = user_text.partition("Previous steps:\n")[2].partition("\nWhat is the next action?")[0]
    if not hist or hist == "None":
        return ""
    rest = hist.split("\n")[-1].split(". ", 1)[-1]
    return rest.rpartition(" -> ")[0] if " -> " in rest else ""


def parse_output(text: str):
    intent = ""
    if "<think>" in text and "</think>" in text:
        intent = text.split("<think>", 1)[1].split("</think>", 1)[0].strip()
    intent = intent.splitlines()[0][:200] if intent else ""
    return intent, af.parse_action(text)


def kind_of(gt: dict, pred: dict, pi: str, prev_intent: str) -> str:
    g, p = gt["action_type"], pred["action_type"]
    if p in ("status", "answer") and g not in ("status", "answer"):
        return "early_stop"
    if g in ("status", "answer") and p not in ("status", "answer"):
        return "missed_stop"
    if p == "wait":
        return "wait"
    if pi and prev_intent and pi == prev_intent:
        return "copied_intent"
    if g == p:
        return "wrong_target"          # right type, wrong point / text / direction / app / status
    return "wrong_type"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="v4.2 training data (save_to_disk)")
    ap.add_argument("--model", required=True, help="v4.2 merged weights")
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--splits", default="meta/splits.json", help="AndroidControl official split ids")
    ap.add_argument("--n_rows", type=int, default=16000)
    ap.add_argument("--terminal_share", type=float, default=0.15)
    ap.add_argument("--bs", type=int, default=48)
    ap.add_argument("--max_pixels", type=int, default=774400)
    ap.add_argument("--min_pixels", type=int, default=65536)
    ap.add_argument("--max_new_tokens", type=int, default=128)
    ap.add_argument("--seed", default="v5pairs")
    a = ap.parse_args()
    import torch
    from datasets import load_from_disk
    from transformers import AutoModelForImageTextToText, AutoProcessor

    os.makedirs(a.work, exist_ok=True)
    ds = load_from_disk(a.data)
    src, eps, steps, msgs = ds["source"], ds["episode_id"], ds["step_idx"], ds["messages"]
    held = set()
    if os.path.exists(a.splits):
        sp = json.load(open(a.splits))
        held = {str(x) for k in ("test", "validation") for x in sp.get(k, [])}
    # candidate rows: human step not `wait`, no held-out AndroidControl episode, no AndroidWorld app in the goal
    term, nonterm, skipped = [], [], Counter()
    for i, m in enumerate(msgs):
        gt = json.loads(m[2]["content"])
        if gt["action_type"] == "wait":
            skipped["human_wait"] += 1
            continue
        if src[i] == "androidcontrol" and str(eps[i]) in held:
            skipped["heldout_episode"] += 1
            continue
        if AW_APP_RE.search(m[1]["content"].split("Previous steps:")[0]):
            skipped["aw_app"] += 1
            continue
        (term if gt["action_type"] == "status" else nonterm).append(i)
    key = lambda i: h01(a.seed, src[i], eps[i], steps[i], i)
    n_t = min(len(term), int(a.n_rows * a.terminal_share))
    rows = sorted(sorted(term, key=key)[:n_t] + sorted(nonterm, key=key)[:a.n_rows - n_t])
    print(f"candidates: terminal {len(term)}, other {len(nonterm)}; skipped {dict(skipped)}; sampled {len(rows)} "
          f"({n_t} terminal)", flush=True)

    proc = AutoProcessor.from_pretrained(a.model, trust_remote_code=True,
                                         size={"shortest_edge": a.min_pixels, "longest_edge": a.max_pixels})
    proc.tokenizer.padding_side = "left"
    model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16, trust_remote_code=True).to("cuda").eval()
    out_f = f"{a.work}/v5_greedy.jsonl"
    done = set()
    if os.path.exists(out_f):
        done = {json.loads(l)["row"] for l in open(out_f)}
    todo = [i for i in rows if i not in done]
    t0 = time.time()
    with open(out_f, "a") as fo:
        for b in range(0, len(todo), a.bs):
            idx = todo[b:b + a.bs]
            convs = []
            for i in idx:
                m = msgs[i]
                convs.append([{"role": "system", "content": [{"type": "text", "text": m[0]["content"]}]},
                              {"role": "user", "content": [{"type": "image", "image": ds[i]["images"][0]},
                                                           {"type": "text", "text": m[1]["content"]}]}])
            inputs = proc.apply_chat_template(convs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                              return_tensors="pt", padding=True, processor_kwargs={"padding": True},
                                              enable_thinking=True).to("cuda")
            with torch.inference_mode():
                out = model.generate(**inputs, max_new_tokens=a.max_new_tokens, do_sample=False)
            texts = proc.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=False)
            tail_tok = proc.tokenizer.decode(inputs["input_ids"][0][-4:], skip_special_tokens=False)
            for i, txt in zip(idx, texts):
                txt = txt.replace(proc.tokenizer.pad_token or "\x00", "")
                for eos in ("<|im_end|>", "<|endoftext|>"):
                    txt = txt.split(eos)[0]
                if tail_tok.rstrip().endswith("<think>"):
                    txt = "<think>" + txt
                fo.write(json.dumps({"row": i, "text": txt}) + "\n")
            fo.flush()
            if (b // a.bs) % 20 == 0:
                print(f"generated {b + len(idx)}/{len(todo)} in {time.time() - t0:.0f}s", flush=True)

    gen = {}
    for l in open(out_f):
        r = json.loads(l)
        gen[r["row"]] = r["text"]
    keep, kinds, stats = [], Counter(), Counter()
    for i in rows:
        m = msgs[i]
        gt = json.loads(m[2]["content"])
        pi, pa = parse_output(gen[i])
        stats["n"] += 1
        if pa is None:
            stats["unparsed"] += 1
            continue
        if match(pa, gt)[1]:
            stats["match"] += 1
            continue
        k = kind_of(gt, pa, pi, last_intent(m[1]["content"]))
        kinds[k] += 1
        keep.append((i, k, {"intent": m[2].get("reasoning_content") or "", "action": m[2]["content"]},
                     {"intent": pi, "action": af.action_to_str(pa)}))
    stats["pairs"] = len(keep)
    print(json.dumps({"stats": dict(stats), "kinds": dict(kinds)}), flush=True)

    sub = ds.select([i for i, *_ in keep])
    sub = sub.add_column("prompt_json", [json.dumps([msgs[i][0], msgs[i][1]]) for i, *_ in keep])
    sub = sub.add_column("chosen_json", [json.dumps(c) for *_, c, _r in keep])
    sub = sub.add_column("rejected_json", [json.dumps(r) for *_, r in keep])
    sub = sub.add_column("kind", [k for _i, k, *_ in keep])
    sub = sub.remove_columns([c for c in sub.column_names if c not in
                              ("images", "prompt_json", "chosen_json", "rejected_json", "kind", "source", "episode_id", "step_idx")])
    sub.save_to_disk(a.out)
    json.dump({"stats": dict(stats), "kinds": dict(kinds), "skipped_candidates": dict(skipped),
               "sampled": len(rows), "terminal_sampled": n_t, "by_source": dict(Counter(src[i] for i, *_ in keep)),
               "model": a.model, "builder_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()},
              open(f"{a.work}/pairs_stats.json", "w"), indent=1)


if __name__ == "__main__":
    main()
