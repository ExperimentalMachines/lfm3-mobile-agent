#!/usr/bin/env python3
"""Semi-online RL (UI-S1, arXiv 2509.11543) for the LFM3 agent on static trajectories. Round 13 step 2
(docs/PREREG_v411.md). No environment, no teacher: the human trajectories supply the screens.

Per batch: B training episodes (AndroidControl + GUI-Odyssey from E's training split), G rollouts each, in lockstep.
At step t every live rollout sees the dataset screenshot of step t, the goal, the installed apps and ITS OWN history
(its intents and actions; 24 steps; " [no visible change]" notes on the dataset screens, as E's harness) and samples an
action. Step reward (UI-S1 Eq. 8): 0.1 parseable + 0.4 right type + 0.5 right action (eval/androidcontrol/score.match).
A wrong action is patched with the human's (intent, action) in the history once per rollout (patch budget 1, as UI-S1's
final setting); a second wrong action ends the rollout (no later rewards). Return R_t = sum_k gamma^(k-t) r_k.
Advantage A = A_episode + omega * A_step (episode return normalised across the G rollouts; step return normalised across
the rollouts that reached step t). Loss = - sum A * mean token log-prob of the sampled completion; one optimizer step per
batch (on-policy, no clipping needed). LoRA on the language model (as every round since v4).
Episode endings: AndroidControl episodes end with the human's `status complete`; the 113 AndroidControl completes the
judge found unfinished lose that last step. GUI-Odyssey episodes get their judged ending: done -> `status complete`,
unfinished -> the next action Claude wrote (round 12); unjudged endings and the round-11/12 probe episodes are excluded.
Usage (inside the training job): python semi_online_rl.py --model_id E --out OUT --term ody_term2.parquet
  --verdicts V.jsonl --written W.jsonl --acv ACV.jsonl --probe_ids P.json [--batches 150 --B 4 --G 4]
"""
import argparse
import io
import json
import math
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict

import torch
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, "..", "eval", "androidcontrol")):
    sys.path.insert(0, p)
import agent_format as af  # noqa: E402
import screen_change as sc  # noqa: E402
from score import match  # noqa: E402

REPO, REV = "experimentalmachines/MobileAgent-SFT-v4.6", "0ace5559e6c0b808a5ddf4e4ce9831d1d3614471"
HB = re.compile(r"\nPrevious steps:\n(.*?)\nWhat is the next action\?$", re.S)
LINE = re.compile(r"^(\d+)\. (.*)$")


def position(user):
    m = HB.search(user)
    nums = [int(x.group(1)) for x in map(LINE.match, m.group(1).split("\n")) if x] if m else []
    return nums[-1] if nums else 0


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


# ------------------------------------------------------------------ episodes
def build_episodes(a):
    from datasets import Image as HFImage, Sequence, load_dataset
    from huggingface_hub import HfApi
    import pyarrow.parquet as pq
    files = sorted(f for f in HfApi().list_repo_files(REPO, repo_type="dataset", revision=REV) if f.startswith("data/train-"))
    if a.shards:
        files = files[:a.shards]
    ds = load_dataset(REPO, data_files={"train": files}, split="train", revision=REV)
    src, eps_col, stp, msgs = ds["source"], ds["episode_id"], ds["step_idx"], ds["messages"]
    by = defaultdict(list)
    for i, (s, e, k, m) in enumerate(zip(src, eps_col, stp, msgs)):
        e = str(e)
        if "#" in e or s not in ("androidcontrol", "odyssey"):
            continue
        key = int(k) if s == "androidcontrol" else position(m[1]["content"])
        by[(s, e)].append((key, i))
    raw = ds.cast_column("images", Sequence(HFImage(decode=False)))
    acv = {}
    for l in open(a.acv):
        j = json.loads(l)
        acv[(j["episode_id"], int(j["step_idx"]))] = j["verdict"]
    verd = {json.loads(l)["case"]: json.loads(l)["verdict"] for l in open(a.verdicts)}
    written = {json.loads(l)["case"]: json.loads(l) for l in open(a.written)}
    probe = set(json.load(open(a.probe_ids))["episodes"])
    term = {str(t["episode_id"]): t for t in pq.read_table(a.term).to_pylist()}
    st = Counter()
    out = []
    rnd = random.Random(a.seed)
    keys = sorted(by)
    rnd.shuffle(keys)
    for s, e in keys:
        rows = sorted(by[(s, e)])
        if [k for k, _ in rows] != list(range(len(rows))):
            st[f"{s}_not_contiguous"] += 1
            continue
        if s == "odyssey" and e in probe:
            st["odyssey_probe_excluded"] += 1
            continue
        steps = []
        for _, i in rows:
            r = raw[i]
            m = r["messages"]
            steps.append({"jpg": r["images"][0]["bytes"], "gt": json.loads(r["gt_action"]),
                          "bbox": json.loads(r["gt_bbox"]) if r.get("gt_bbox") else None,
                          "intent": (m[2].get("reasoning_content") or "").strip()})
        user0 = raw[rows[0][1]]["messages"][1]["content"]
        if s == "androidcontrol":
            last = steps[-1]["gt"]
            if last["action_type"] == "status" and acv.get((e, len(steps) - 1)) == "NOT_COMPLETE":
                steps = steps[:-1]
                st["ac_unfinished_complete_dropped"] += 1
        else:
            t = term.get(e)
            case = f"ody_{e}_{t['step_idx']}" if t else None
            if not t or case not in verd:
                st["odyssey_no_judged_ending"] += 1
                continue
            if verd[case] == "COMPLETE":
                steps.append({"jpg": t["jpg"], "gt": {"action_type": "status", "goal_status": "complete"}, "bbox": None,
                              "intent": "The goal has been completed."})
            else:
                w = written.get(case)
                if not w or w["status"] != "ok":
                    st["odyssey_unfinished_no_action"] += 1
                    continue
                steps.append({"jpg": t["jpg"], "gt": w["action"], "bbox": None, "intent": w["intent"]})
                st["odyssey_unfinished_with_written_action"] += 1
        if not steps:
            continue
        goal = user0.split("\n", 1)[0][len("Goal: "):]
        al = next((l for l in user0.split("\n") if l.startswith("Installed apps: ")), None)
        out.append({"source": s, "episode": e, "goal": goal,
                    "apps": al[len("Installed apps: "):].split(", ") if al else None, "steps": steps[: a.max_steps]})
        st[f"{s}_episodes"] += 1
    log("episodes", json.dumps(st))
    return out, st


# ------------------------------------------------------------------ model
def load(a):
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForImageTextToText, AutoProcessor
    pk = {"size": {"shortest_edge": 65536, "longest_edge": a.max_pixels}}
    proc = AutoProcessor.from_pretrained(a.model_id, trust_remote_code=True, **pk)
    proc.tokenizer.padding_side = "left"
    dev = "cuda" if torch.cuda.is_available() else "mps"
    model = AutoModelForImageTextToText.from_pretrained(a.model_id, dtype=torch.bfloat16, trust_remote_code=True,
                                                        attn_implementation="sdpa").to(dev)
    cfg = LoraConfig(r=a.lora_r, lora_alpha=a.lora_alpha, lora_dropout=0.0, task_type="CAUSAL_LM",
                     target_modules=r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|in_proj|out_proj|w1|w2|w3)")
    model = get_peft_model(model, cfg)
    if a.resume and os.path.isdir(a.resume):
        from peft import set_peft_model_state_dict
        from safetensors.torch import load_file
        set_peft_model_state_dict(model, load_file(os.path.join(a.resume, "adapter_model.safetensors")))
        log("resumed adapter from", a.resume)
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    model.print_trainable_parameters()
    return proc, model, dev


def conv(goal, apps, hist, jpg, hsteps):
    img = Image.open(io.BytesIO(jpg)).convert("RGB")
    text = af.user_text(goal, hist, apps=apps, history_steps=hsteps)
    return [{"role": "system", "content": [{"type": "text", "text": af.PROMPTS["v4"]}]},
            {"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": text}]}]


def stop_ids(proc):
    tok = proc.tokenizer
    ids = {tok.eos_token_id, tok.pad_token_id}
    for s in ("<|im_end|>", "<|endoftext|>"):
        i = tok.convert_tokens_to_ids(s)
        if isinstance(i, int) and i >= 0 and i != tok.unk_token_id:
            ids.add(i)
    return {i for i in ids if i is not None}


@torch.no_grad()
def sample(proc, model, dev, convs, a, stops):
    model.eval()
    inp = proc.apply_chat_template(convs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
                                   padding=True, processor_kwargs={"padding": True}, enable_thinking=True).to(dev)
    out = model.generate(**inp, max_new_tokens=a.max_new_tokens, do_sample=True, temperature=a.temperature, top_p=1.0)
    gen = out[:, inp["input_ids"].shape[1]:].tolist()
    tail = proc.tokenizer.decode(inp["input_ids"][0][-4:], skip_special_tokens=False)
    res = []
    for g in gen:
        cut = next((j for j, t in enumerate(g) if t in stops), None)
        ids = g[: cut + 1] if cut is not None else g
        txt = proc.tokenizer.decode([t for t in ids if t not in stops], skip_special_tokens=False)
        if tail.rstrip().endswith("<think>"):
            txt = "<think>" + txt
        res.append((ids, txt, cut is not None))
    return res


def split_think(txt):
    if "</think>" in txt:
        th, act = txt.split("</think>", 1)
        return th.replace("<think>", "").strip(), act
    return "", txt


def reward(pred, gt, bbox):
    if pred is None:
        return 0.0, False
    tm, full = match(pred, gt, bbox)
    return 0.1 + 0.4 * tm + 0.5 * (tm and full), bool(full)


# ------------------------------------------------------------------ rollouts
def rollouts(proc, model, dev, eps, a, stops):
    """-> list of samples {conv, ids, A}, stats. All B x G rollouts of the batch advance in lockstep (one generate call
    per step index, up to a.gen_bs sequences at a time)."""
    G, recs, st = a.G, [], Counter()
    RR = [[{"hist": [], "alive": True, "patches": 0, "steps": []} for _ in range(G)] for _ in eps]
    for t in range(max(len(ep["steps"]) for ep in eps)):
        jobs = []
        for e, ep in enumerate(eps):
            if t >= len(ep["steps"]):
                continue
            R, stp = RR[e], ep["steps"][t]
            live = [g for g in range(G) if R[g]["alive"]]
            if t > 0 and a.notes and live:
                prev = ep["steps"][t - 1]
                if prev["gt"]["action_type"] not in ("wait", "status", "answer") and not sc.changed(sc.prep(prev["jpg"]), sc.prep(stp["jpg"])):
                    for g in live:
                        i, s = R[g]["hist"][-1]
                        if not s.endswith("]"):
                            R[g]["hist"][-1] = (i, s + sc.NOTE)
            jobs += [(e, g, conv(ep["goal"], ep["apps"], list(R[g]["hist"]), stp["jpg"], a.history_steps)) for g in live]
        if not jobs:
            break
        outs = []
        for j in range(0, len(jobs), a.gen_bs):
            outs += sample(proc, model, dev, [c for _, _, c in jobs[j:j + a.gen_bs]], a, stops)
        for (e, g, c), (ids, txt, ended) in zip(jobs, outs):
            R, stp = RR[e], eps[e]["steps"][t]
            think, act = split_think(txt)
            pred = af.parse_action(act) if ended else None
            r, ok = reward(pred, stp["gt"], stp["bbox"])
            R[g]["steps"].append({"t": t, "conv": c, "ids": ids, "r": r})
            st["steps"] += 1
            st["steps_ok"] += ok
            if pred and pred["action_type"] == "status" and stp["gt"]["action_type"] != "status":
                st["premature_status"] += 1
            if stp["gt"]["action_type"] == "status":
                st["final_steps"] += 1
                st["final_ok"] += ok
            if ok:
                intent = af.strip_progress(think.splitlines()[0])[:200] if think else ""
                R[g]["hist"].append((intent, af.action_to_str(pred)))
            elif R[g]["patches"] < a.patch:
                R[g]["patches"] += 1
                R[g]["hist"].append((stp["intent"], af.action_to_str(stp["gt"])))
            else:
                R[g]["alive"] = False
    for e, ep in enumerate(eps):
        R, T = RR[e], len(ep["steps"])
        # returns and advantages
        for g in range(G):
            rs = [s["r"] for s in R[g]["steps"]]
            for j, s in enumerate(R[g]["steps"]):
                s["ret"] = sum(a.gamma ** (k - j) * rs[k] for k in range(j, len(rs)))
            R[g]["total"] = sum(rs)
            st["episode_return"] += R[g]["total"] / G
            st["completed"] += (not R[g]["patches"]) and len(R[g]["steps"]) == T and all(s["r"] >= 0.999 for s in R[g]["steps"])
        tot = [R[g]["total"] for g in range(G)]
        mu, sd = sum(tot) / G, (sum((x - sum(tot) / G) ** 2 for x in tot) / G) ** 0.5
        for t in range(T):
            here = [s for g in range(G) for s in R[g]["steps"] if s["t"] == t]
            if not here:
                continue
            m = sum(s["ret"] for s in here) / len(here)
            v = (sum((s["ret"] - m) ** 2 for s in here) / len(here)) ** 0.5
            for g in range(G):
                for s in R[g]["steps"]:
                    if s["t"] == t:
                        ae = (R[g]["total"] - mu) / (sd + 1e-6) if sd > 1e-6 else 0.0
                        as_ = (s["ret"] - m) / (v + 1e-6) if v > 1e-6 and len(here) > 1 else 0.0
                        s["A"] = ae + a.omega * as_
        for g in range(G):
            recs += [s for s in R[g]["steps"] if abs(s["A"]) > 1e-6]
        st["episodes"] += 1
    return recs, st


def policy_loss(proc, model, dev, rec):
    model.train()
    inp = proc.apply_chat_template([rec["conv"]], add_generation_prompt=True, tokenize=True, return_dict=True,
                                   return_tensors="pt", enable_thinking=True).to(dev)
    gen = torch.tensor([rec["ids"]], device=dev)
    ids = torch.cat([inp["input_ids"], gen], dim=1)
    extra = {k: v for k, v in inp.items() if k not in ("input_ids", "attention_mask")}
    out = model(input_ids=ids, attention_mask=torch.ones_like(ids), **extra)
    P = inp["input_ids"].shape[1]
    logits = out.logits[:, P - 1:-1, :].float()
    lp = torch.log_softmax(logits, dim=-1).gather(-1, gen.unsqueeze(-1)).squeeze(-1)
    return -rec["A"] * lp.mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_id", required=True)
    ap.add_argument("--out", required=True)
    for k in ("term", "verdicts", "written", "acv", "probe_ids"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--batches", type=int, default=150)
    ap.add_argument("--B", type=int, default=4)
    ap.add_argument("--G", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--gamma", type=float, default=0.5)
    ap.add_argument("--omega", type=float, default=1.0)
    ap.add_argument("--patch", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--max_new_tokens", type=int, default=160)
    ap.add_argument("--gen_bs", type=int, default=16, help="sequences per generate call")
    ap.add_argument("--max_steps", type=int, default=12)
    ap.add_argument("--history_steps", type=int, default=24)
    ap.add_argument("--notes", type=int, default=1)
    ap.add_argument("--max_pixels", type=int, default=774400)
    ap.add_argument("--lora_r", type=int, default=64)
    ap.add_argument("--lora_alpha", type=int, default=128)
    ap.add_argument("--ac_share", type=float, default=0.7)
    ap.add_argument("--save_every", type=int, default=10)
    ap.add_argument("--shards", type=int, default=0)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--resume", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    random.seed(a.seed)
    torch.manual_seed(a.seed)
    eps, st0 = build_episodes(a)
    ac = [e for e in eps if e["source"] == "androidcontrol"]
    od = [e for e in eps if e["source"] == "odyssey"]
    n = a.batches * a.B
    n_ac = min(len(ac), round(n * a.ac_share))
    plan = ac[:n_ac] + od[: n - n_ac]
    random.Random(a.seed).shuffle(plan)
    json.dump({"episodes": [(e["source"], e["episode"]) for e in plan], "build": st0},
              open(os.path.join(a.out, "plan.json"), "w"))
    log(f"plan: {len(plan)} episodes ({n_ac} AndroidControl, {len(plan) - n_ac} GUI-Odyssey)")
    proc, model, dev = load(a)
    stops = stop_ids(proc)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=0.0)
    state_f = os.path.join(a.out, "state.json")
    start = json.load(open(state_f))["batch"] if os.path.exists(state_f) and a.resume else 0
    if start:
        opt_f = os.path.join(a.resume, "optimizer.pt")
        if os.path.exists(opt_f):
            opt.load_state_dict(torch.load(opt_f, weights_only=True))
    t0 = time.time()
    for b in range(start, a.batches):
        batch = plan[b * a.B:(b + 1) * a.B]
        if not batch:
            break
        tr = time.time()
        recs, st = rollouts(proc, model, dev, batch, a, stops)
        tr = time.time() - tr
        opt.zero_grad(set_to_none=True)
        tl = time.time()
        loss_sum = 0.0
        for rec in recs:
            loss = policy_loss(proc, model, dev, rec) / max(1, len(recs))
            loss.backward()
            loss_sum += float(loss)
        if recs:
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
            opt.step()
        tl = time.time() - tl
        row = {"batch": b + 1, "samples": len(recs), "loss": round(loss_sum, 5),
               "step_acc": round(st["steps_ok"] / max(1, st["steps"]), 4),
               "premature_status_per_step": round(st["premature_status"] / max(1, st["steps"]), 4),
               "final_ok": f"{st['final_ok']}/{st['final_steps']}", "episode_return": round(st["episode_return"] / max(1, st["episodes"]), 3),
               "completed_rollouts": st["completed"], "rollout_s": round(tr), "update_s": round(tl),
               "elapsed_h": round((time.time() - t0) / 3600, 2)}
        if dev == "cuda":
            row["gpu_mem_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
        with open(os.path.join(a.out, "rl_log.jsonl"), "a") as f:
            f.write(json.dumps(row) + "\n")
        log(json.dumps(row))
        if (b + 1) % a.save_every == 0 or b + 1 == a.batches:
            ck = os.path.join(a.out, "adapter")
            model.save_pretrained(ck)
            torch.save(opt.state_dict(), os.path.join(ck, "optimizer.pt"))
            json.dump({"batch": b + 1}, open(state_f, "w"))
            log("saved", ck)
    model.save_pretrained(os.path.join(a.out, "adapter"))
    json.dump({"batch": a.batches, "done": True}, open(state_f, "w"))
    log("RL DONE")


if __name__ == "__main__":
    main()
