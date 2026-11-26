#!/usr/bin/env python3
"""Semi-online RL (UI-S1, arXiv 2509.11543) for the LFM3 agent on static trajectories, corrected after the external
review (round 14, docs/preregistrations/round-14-own-history-vs-control.md; round 13's version had the defects C1, M1, M2, M4 of
docs/reviews/codex-adversarial-review-2026-11-26.md). No environment, no teacher: the human trajectories supply the screens.

Episodes: AndroidControl + GUI-Odyssey from E's training split, contiguous steps. AndroidControl keeps the human labels
as they are (the judge's AndroidControl verdicts failed their audit and are not used). GUI-Odyssey gets its judged ending
(done -> `status complete`; unfinished -> Claude's reviewed next action); the probe episodes are excluded. Episodes longer
than --max_steps become a SUFFIX window: the last max_steps steps, with the human's earlier steps as history (intent ->
action, notes on the dataset screens). So every window contains the episode's real ending (review M2).

Rollouts: B episodes x G rollouts in lockstep, own history (24 steps, fine notes), temperature 1.0.
  * reward per step (UI-S1 Eq. 8) with the STRICT matcher (score.strict_match: inside the element box, exact text; M1):
    0.1 parseable + 0.4 right type + 0.5 right action
  * a premature terminal action (`status` or `answer` where the human acted on) ENDS that rollout (as in deployment)
  * another wrong action is patched once with the human's (intent, action) and the rollout continues in a NEW segment;
    a second wrong action ends the rollout
  * return R_t = sum of gamma^(k-t) r_k only up to the end of the step's own NATURAL segment (the step where it went
    wrong, inclusive): no action is credited with reward earned after a human patch (review C1; UI-S1's t_end)
  * advantage A = A_episode + omega * A_step; A_episode = first-segment reward normalised across the G rollouts (applied
    to first-segment steps only); A_step = segment return normalised across the rollouts at the same step
  * loss = - sum A * mean token log-prob of the sampled completion; one AdamW step per batch (on-policy)
--collect OUT (matched control, review recommendation 5): greedy (temperature 0), G = 1, the same episodes and windows;
  at EVERY step where the model's action fails the strict matcher, save (screen, own history) -> the human's action as an
  SFT row, then patch and go on. No training.
"""
import argparse
import io
import json
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
from score import strict_match  # noqa: E402

REPO, REV = "experimentalmachines/MobileAgent-SFT-Counterfactual", "0ace5559e6c0b808a5ddf4e4ce9831d1d3614471"
HB = re.compile(r"\nPrevious steps:\n(.*?)\nWhat is the next action\?$", re.S)
LINE = re.compile(r"^(\d+)\. (.*)$")
TERMINAL = ("status", "answer")


def position(user):
    m = HB.search(user)
    nums = [int(x.group(1)) for x in map(LINE.match, m.group(1).split("\n")) if x] if m else []
    return nums[-1] if nums else 0


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def note_if_unchanged(hist, prev_step, cur_jpg):
    """Append the no-visible-change note to the last history line (E's harness rule, on dataset screens)."""
    if hist and prev_step["gt"]["action_type"] not in ("wait", "status", "answer") \
            and not sc.changed(sc.prep(prev_step["jpg"]), sc.prep(cur_jpg)):
        i, s = hist[-1]
        if not s.endswith("]"):
            hist[-1] = (i, s + sc.NOTE)


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
    verd = {json.loads(l)["case"]: json.loads(l)["verdict"] for l in open(a.verdicts)}
    written = {json.loads(l)["case"]: json.loads(l) for l in open(a.written)}
    probe = set(json.load(open(a.probe_ids))["episodes"])
    term = {str(t["episode_id"]): t for t in pq.read_table(a.term).to_pylist()}
    st = Counter()
    out = []
    keys = sorted(by)
    random.Random(a.seed).shuffle(keys)
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
        if s == "odyssey":
            t = term.get(e)
            case = f"ody_{e}_{t['step_idx']}" if t else None
            if not t or case not in verd:
                st["odyssey_no_judged_ending"] += 1
                continue
            if verd[case] == "COMPLETE":
                steps.append({"jpg": t["jpg"], "gt": {"action_type": "status", "goal_status": "complete"}, "bbox": None,
                              "intent": "The goal has been completed."})
                st["odyssey_done_ending"] += 1
            else:
                w = written.get(case)
                if not w or w["status"] != "ok":
                    st["odyssey_unfinished_no_action"] += 1
                    continue
                steps.append({"jpg": t["jpg"], "gt": w["action"], "bbox": None, "intent": w["intent"]})
                st["odyssey_unfinished_ending"] += 1
        elif steps[-1]["gt"]["action_type"] == "status":
            st["androidcontrol_status_ending"] += 1
        # suffix window: the ending is always inside (review M2); earlier human steps become history
        w0 = max(0, len(steps) - a.max_steps)
        prefix = []
        for k in range(w0):
            if k > 0:
                note_if_unchanged(prefix, steps[k - 1], steps[k]["jpg"])
            prefix.append((steps[k]["intent"], af.action_to_str(steps[k]["gt"])))
        if w0 > 0:
            note_if_unchanged(prefix, steps[w0 - 1], steps[w0]["jpg"])
            st[f"{s}_suffix_windows"] += 1
        goal = user0.split("\n", 1)[0][len("Goal: "):]
        al = next((l for l in user0.split("\n") if l.startswith("Installed apps: ")), None)
        out.append({"source": s, "episode": e, "goal": goal, "apps": al[len("Installed apps: "):].split(", ") if al else None,
                    "prefix": prefix, "w0": w0, "steps": steps[w0:]})
        st[f"{s}_episodes"] += 1
    log("episodes", json.dumps(st))
    return out, st


# ------------------------------------------------------------------ model
def load(a, lora=True):
    from transformers import AutoModelForImageTextToText, AutoProcessor
    pk = {"size": {"shortest_edge": 65536, "longest_edge": a.max_pixels}}
    proc = AutoProcessor.from_pretrained(a.model_id, trust_remote_code=True, **pk)
    proc.tokenizer.padding_side = "left"
    dev = "cuda" if torch.cuda.is_available() else "mps"
    model = AutoModelForImageTextToText.from_pretrained(a.model_id, dtype=torch.bfloat16, trust_remote_code=True,
                                                        attn_implementation="sdpa").to(dev)
    if not lora:
        model.eval()
        return proc, model, dev
    from peft import LoraConfig, get_peft_model
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
def sample(proc, model, dev, convs, a, stops, greedy=False):
    model.eval()
    inp = proc.apply_chat_template(convs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
                                   padding=True, processor_kwargs={"padding": True}, enable_thinking=True).to(dev)
    kw = {"do_sample": False} if greedy else {"do_sample": True, "temperature": a.temperature, "top_p": 1.0}
    out = model.generate(**inp, max_new_tokens=a.max_new_tokens, **kw)
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
    tm, full = strict_match(pred, gt, bbox)
    return 0.1 + 0.4 * tm + 0.5 * (tm and full), bool(full)


def intent_of(think):
    return af.strip_progress(think.splitlines()[0])[:200] if think else ""


# ------------------------------------------------------------------ rollouts
def advance(eps, RR, t, a, outs_by_job, jobs, st, collect=None):
    """Apply one lockstep step's outputs to the rollouts (shared by RL and --collect)."""
    for (e, g, c), (ids, txt, ended) in zip(jobs, outs_by_job):
        R, stp = RR[e][g], eps[e]["steps"][t]
        think, act = split_think(txt)
        pred = af.parse_action(act) if ended else None
        r, ok = reward(pred, stp["gt"], stp["bbox"])
        R["steps"].append({"t": t, "conv": c, "ids": ids, "r": r, "seg": R["seg"]})
        st["steps"] += 1
        st["steps_ok"] += ok
        premature = bool(pred) and pred["action_type"] in TERMINAL and stp["gt"]["action_type"] not in TERMINAL
        st["premature_terminal"] += premature
        if stp["gt"]["action_type"] == "status":
            st["final_steps"] += 1
            st["final_ok"] += ok
        if collect is not None and not ok:
            collect.append({"images": [{"bytes": stp["jpg"], "path": None}],
                            "messages": [{"role": "system", "content": af.PROMPTS["v4"]},
                                         {"role": "user", "content": af.user_text(eps[e]["goal"], list(R["hist"]), apps=eps[e]["apps"],
                                                                                  history_steps=a.history_steps)},
                                         {"role": "assistant", "content": af.action_to_str(stp["gt"]), "reasoning_content": stp["intent"]}],
                            "kind": "premature_terminal" if premature else "divergence", "source": eps[e]["source"]})
        if ok:
            R["hist"].append((intent_of(think), af.action_to_str(pred)))
        elif premature and collect is None:
            R["alive"] = False                      # a premature `status` / `answer` ends the attempt, as in deployment
            R["ended_premature"] = True
        elif R["patches"] < a.patch:
            R["patches"] += 1
            R["seg"] += 1                           # the continuation is a separate segment (review C1)
            R["hist"].append((stp["intent"], af.action_to_str(stp["gt"])))
        else:
            R["alive"] = False


def run_lockstep(proc, model, dev, eps, a, stops, G, greedy=False, collect=None):
    st = Counter()
    RR = [[{"hist": list(ep["prefix"]), "alive": True, "patches": 0, "seg": 0, "steps": [], "ended_premature": False}
           for _ in range(G)] for ep in eps]
    for t in range(max(len(ep["steps"]) for ep in eps)):
        jobs = []
        for e, ep in enumerate(eps):
            if t >= len(ep["steps"]):
                continue
            live = [g for g in range(G) if RR[e][g]["alive"]]
            if t > 0 and a.notes:
                for g in live:
                    note_if_unchanged(RR[e][g]["hist"], ep["steps"][t - 1], ep["steps"][t]["jpg"])
            jobs += [(e, g, conv(ep["goal"], ep["apps"], list(RR[e][g]["hist"]), ep["steps"][t]["jpg"], a.history_steps))
                     for g in live]
        if not jobs:
            break
        outs = []
        for j in range(0, len(jobs), a.gen_bs):
            outs += sample(proc, model, dev, [c for _, _, c in jobs[j:j + a.gen_bs]], a, stops, greedy=greedy)
        advance(eps, RR, t, a, outs, jobs, st, collect)
    return RR, st


def rollouts(proc, model, dev, eps, a, stops):
    """-> samples {conv, ids, A} with non-zero advantage, stats"""
    G, recs = a.G, []
    RR, st = run_lockstep(proc, model, dev, eps, a, stops, G)
    for e, ep in enumerate(eps):
        R, T = RR[e], len(ep["steps"])
        for g in range(G):
            S = R[g]["steps"]
            for j, s in enumerate(S):              # natural-segment return: nothing after this step's segment ends
                s["ret"] = sum(a.gamma ** (k - j) * S[k]["r"] for k in range(j, len(S)) if S[k]["seg"] == s["seg"])
            R[g]["first_seg"] = sum(s["r"] for s in S if s["seg"] == 0)
            st["episode_return"] += R[g]["first_seg"] / G
            st["completed"] += (not R[g]["patches"]) and not R[g]["ended_premature"] and len(S) == T \
                and all(s["r"] >= 0.999 for s in S)
            st["ended_premature"] += R[g]["ended_premature"]
        tot = [R[g]["first_seg"] for g in range(G)]
        mu = sum(tot) / G
        sd = (sum((x - mu) ** 2 for x in tot) / G) ** 0.5
        for t in range(T):
            here = [s for g in range(G) for s in R[g]["steps"] if s["t"] == t]
            if not here:
                continue
            m = sum(s["ret"] for s in here) / len(here)
            v = (sum((s["ret"] - m) ** 2 for s in here) / len(here)) ** 0.5
            for g in range(G):
                for s in R[g]["steps"]:
                    if s["t"] != t:
                        continue
                    ae = (R[g]["first_seg"] - mu) / sd if (sd > 1e-6 and s["seg"] == 0) else 0.0
                    as_ = (s["ret"] - m) / v if (v > 1e-6 and len(here) > 1) else 0.0
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


def make_plan(eps, a):
    ac = [e for e in eps if e["source"] == "androidcontrol"]
    od = [e for e in eps if e["source"] == "odyssey"]
    n = a.batches * a.B
    n_ac = min(len(ac), round(n * a.ac_share))
    plan = ac[:n_ac] + od[: n - n_ac]
    random.Random(a.seed).shuffle(plan)
    return plan, n_ac


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_id", required=True)
    ap.add_argument("--out", required=True)
    for k in ("term", "verdicts", "written", "probe_ids"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--batches", type=int, default=100)
    ap.add_argument("--B", type=int, default=4)
    ap.add_argument("--G", type=int, default=4)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--gamma", type=float, default=0.5)
    ap.add_argument("--omega", type=float, default=1.0)
    ap.add_argument("--patch", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--max_new_tokens", type=int, default=160)
    ap.add_argument("--gen_bs", type=int, default=16)
    ap.add_argument("--max_steps", type=int, default=12)
    ap.add_argument("--history_steps", type=int, default=24)
    ap.add_argument("--notes", type=int, default=1)
    ap.add_argument("--max_pixels", type=int, default=774400)
    ap.add_argument("--lora_r", type=int, default=64)
    ap.add_argument("--lora_alpha", type=int, default=128)
    ap.add_argument("--ac_share", type=float, default=0.7)
    ap.add_argument("--save_every", type=int, default=5)
    ap.add_argument("--shards", type=int, default=0)
    ap.add_argument("--seed", type=int, default=14)
    ap.add_argument("--resume", default="")
    ap.add_argument("--collect", default="", help="matched control: save divergence rows here (save_to_disk), no training")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    random.seed(a.seed)
    torch.manual_seed(a.seed)
    eps, st0 = build_episodes(a)
    plan, n_ac = make_plan(eps, a)
    json.dump({"episodes": [(e["source"], e["episode"], e["w0"], len(e["steps"])) for e in plan], "build": st0},
              open(os.path.join(a.out, "plan.json"), "w"))
    log(f"plan: {len(plan)} episodes ({n_ac} AndroidControl, {len(plan) - n_ac} GUI-Odyssey); "
        f"suffix windows {sum(e['w0'] > 0 for e in plan)}; endings: status {sum(e['steps'][-1]['gt']['action_type'] == 'status' for e in plan)}")

    if a.collect:
        proc, model, dev = load(a, lora=False)
        stops = stop_ids(proc)
        rows, stc = [], Counter()
        a.patch = 10 ** 6                           # collection patches every miss
        for b in range(0, len(plan), a.B * a.G):
            _, st = run_lockstep(proc, model, dev, plan[b:b + a.B * a.G], a, stops, 1, greedy=True, collect=rows)
            stc.update(st)
            log(f"collect {min(b + a.B * a.G, len(plan))}/{len(plan)} episodes, rows {len(rows)}, {json.dumps(st)}")
        from datasets import Dataset, Features, Image as HFImage, Sequence, Value
        feat = Features({"images": Sequence(HFImage()),
                         "messages": [{"role": Value("string"), "content": Value("string"), "reasoning_content": Value("string")}],
                         "kind": Value("string"), "source": Value("string")})
        for r in rows:
            for m in r["messages"]:
                m.setdefault("reasoning_content", None)
        Dataset.from_list(rows, features=feat).save_to_disk(a.collect)
        json.dump({"rows": len(rows), "kinds": dict(Counter(r["kind"] for r in rows)), "stats": stc},
                  open(os.path.join(a.out, "collect_stats.json"), "w"), indent=1)
        log("COLLECT DONE", len(rows))
        return

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
               "step_acc_strict": round(st["steps_ok"] / max(1, st["steps"]), 4),
               "premature_terminal_per_step": round(st["premature_terminal"] / max(1, st["steps"]), 4),
               "rollouts_ended_premature": st["ended_premature"], "final_ok": f"{st['final_ok']}/{st['final_steps']}",
               "first_segment_return": round(st["episode_return"] / max(1, st["episodes"]), 3),
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
