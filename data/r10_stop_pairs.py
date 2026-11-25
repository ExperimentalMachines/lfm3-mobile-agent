#!/usr/bin/env python3
"""Round 10 / E-DPO (docs/PREREG_v48.md, 2026-11-25 14:20): preference pairs from E's OWN stop decisions.

E decodes greedily (bf16, thinking on, temperature 0, as at inference) on the candidate rows of data/r10_candidates.py.
  early_stop   a non-terminal row (late / other / ahead: the human took another action) where E outputs `status` or
               `answer` -> chosen = the human step (intent + action), rejected = E's step
  missed_stop  a judged-COMPLETE terminal row where E does not output `status complete` -> chosen = the human `status
               complete` step, rejected = E's step
Unparseable outputs never become rejections. Balanced 1:1: the larger kind is cut at random (seed 49).
Generation is adapted from data/v5_pairs.py (round 5), resumable (<work>/greedy.jsonl).
Output: a datasets dir in data/v5_pairs.py's format (images, prompt_json, chosen_json, rejected_json, kind, source,
episode_id, step_idx, cand_kind) + <work>/pairs_stats.json with E's stop rates per candidate kind.
Usage: python r10_stop_pairs.py --cand CAND_DISK --model E_MERGED --out PAIRS_DISK --work DIR
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_format as af  # noqa: E402


def parse_output(text):
    intent = ""
    if "<think>" in text and "</think>" in text:
        intent = text.split("<think>", 1)[1].split("</think>", 1)[0].strip()
    intent = intent.splitlines()[0][:200] if intent else ""
    return intent, af.parse_action(text.split("</think>")[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--max_pixels", type=int, default=774400)
    ap.add_argument("--min_pixels", type=int, default=65536)
    ap.add_argument("--max_new_tokens", type=int, default=128)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    import torch
    from datasets import load_from_disk
    from transformers import AutoModelForImageTextToText, AutoProcessor

    os.makedirs(a.work, exist_ok=True)
    ds = load_from_disk(a.cand)
    if a.limit:
        ds = ds.select(range(min(a.limit, len(ds))))
    msgs, kinds = ds["messages"], ds["cand_kind"]
    proc = AutoProcessor.from_pretrained(a.model, trust_remote_code=True,
                                         size={"shortest_edge": a.min_pixels, "longest_edge": a.max_pixels})
    proc.tokenizer.padding_side = "left"
    model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16, trust_remote_code=True).to("cuda").eval()
    out_f = f"{a.work}/greedy.jsonl"
    done = {json.loads(l)["row"] for l in open(out_f)} if os.path.exists(out_f) else set()
    todo = [i for i in range(len(ds)) if i not in done]
    t0 = time.time()
    with open(out_f, "a") as fo:
        for b in range(0, len(todo), a.bs):
            idx = todo[b:b + a.bs]
            convs = [[{"role": "system", "content": [{"type": "text", "text": msgs[i][0]["content"]}]},
                      {"role": "user", "content": [{"type": "image", "image": ds[i]["images"][0]},
                                                   {"type": "text", "text": msgs[i][1]["content"]}]}] for i in idx]
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
    gen = {json.loads(l)["row"]: json.loads(l)["text"] for l in open(out_f)}
    st, early, missed = Counter(), [], []
    for i in range(len(ds)):
        k = kinds[i]
        gold = json.loads(msgs[i][2]["content"])
        pi, pa = parse_output(gen[i])
        st[f"n_{k}"] += 1
        if pa is None:
            st[f"unparsed_{k}"] += 1
            continue
        chosen = {"intent": msgs[i][2].get("reasoning_content") or "", "action": msgs[i][2]["content"]}
        rejected = {"intent": pi, "action": af.action_to_str(pa)}
        if k == "terminal":
            assert gold["action_type"] == "status", gold
            if not (pa["action_type"] == "status" and pa.get("goal_status") == "complete"):
                missed.append((i, "missed_stop", chosen, rejected))
                st[f"e_missed_stop_{k}"] += 1
        elif pa["action_type"] in ("status", "answer"):
            early.append((i, "early_stop", chosen, rejected))
            st[f"e_early_stop_{k}"] += 1
    rates = {k: round(st.get(f"e_early_stop_{k}", st.get(f"e_missed_stop_{k}", 0)) / max(st[f"n_{k}"], 1), 4)
             for k in ("late", "other", "ahead", "terminal")}
    n = min(len(early), len(missed))
    rnd = random.Random(49)
    keep = sorted(rnd.sample(early, n) + rnd.sample(missed, n), key=lambda x: x[0])
    st["pairs_early_available"], st["pairs_missed_available"], st["pairs_each"] = len(early), len(missed), n
    sub = ds.select([i for i, *_ in keep])
    sub = sub.add_column("prompt_json", [json.dumps([msgs[i][0], msgs[i][1]]) for i, *_ in keep])
    sub = sub.add_column("chosen_json", [json.dumps(c) for *_, c, _r in keep])
    sub = sub.add_column("rejected_json", [json.dumps(r) for *_, r in keep])
    sub = sub.add_column("kind", [k for _i, k, *_ in keep])
    sub = sub.remove_columns([c for c in sub.column_names if c not in
                              ("images", "prompt_json", "chosen_json", "rejected_json", "kind", "source", "episode_id",
                               "step_idx", "cand_kind")])
    sub.save_to_disk(a.out)
    stats = {"stats": dict(st), "e_stop_rates": rates, "pairs": len(keep), "model": a.model,
             "builder_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
    json.dump(stats, open(f"{a.work}/pairs_stats.json", "w"), indent=1)
    print("R10_PAIRS_DONE", json.dumps(stats), flush=True)


if __name__ == "__main__":
    main()
