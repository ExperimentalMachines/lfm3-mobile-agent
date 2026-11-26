"""v4.2 = fix 4 (2026-11-21, docs/preregistrations/mobileworld-followup-waitrelabel.md): train on the model's own history, without an environment or a teacher.

Semi-online history in the style of UI-S1's patching (arXiv 2509.11543), without RL. For a deterministic subset of
training episodes (AndroidControl / GUI-Odyssey / AMEX), replay each episode on its recorded screens with the current
model (v4.1). Most episodes keep only some steps (earlier builds subsampled steps); a step without a stored screen enters
the history as the human step (a patch), read from the rows' history text:
  * at step t the model sees the goal, the installed-app line and a history made of its OWN earlier outputs, and predicts
    (intent, action);
  * if its action matches the human action (the AndroidControl scorer's rule: eval/androidcontrol/score.py `match`,
    14%-of-screen click radius), its own (intent, action) enters the history; otherwise the human's (intent, action) is
    patched in, so the history always describes actions that lead to the recorded screens;
  * the training row for step t then carries this self-generated history; its target stays the human's intent + action.
The model therefore learns from histories in its own words while being taught the correct next step. Where the model
wrongly predicted `wait` (its typical loop), the row for that step also shows that mistake as the last history step:
a wait leaves the screen unchanged, so the recorded screen and the human target still fit (own-mistake recovery). Rows, images, targets and order are unchanged; only history text differs from v4.1.

Usage (Colab): python sft_ownhistory.py --v41_disk DIR --model MERGED_DIR --work DIR --save_disk OUT_DIR [--rate 0.4]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_format as af  # noqa: E402  (copied next to this file on the VM, as for generate.py)
from score import match  # noqa: E402

SOURCES = {"androidcontrol", "odyssey", "amex"}


def selected(source: str, episode_id: str, rate: float) -> bool:
    h = int(hashlib.sha256(f"selfhist:{source}:{episode_id}".encode()).hexdigest()[:12], 16) / 16 ** 12
    return source in SOURCES and h < rate


def split_user(text: str):
    head, sep, rest = text.partition("Previous steps:\n")
    hist, sep2, tail = rest.partition("\nWhat is the next action?")
    if not sep or not sep2:
        raise ValueError("unexpected user text layout")
    return head + sep, sep2 + tail


def split_lines(text: str):
    head, tail = split_user(text)
    hist = text[len(head):len(text) - len(tail)]
    return head, ([] if hist == "None" else hist.split("\n"))


def parse_output(text: str):
    """generate.py-style decoded text -> (intent, action dict or None)."""
    intent = ""
    if "<think>" in text and "</think>" in text:
        intent = text.split("<think>", 1)[1].split("</think>", 1)[0].strip()
    intent = intent.splitlines()[0][:200] if intent else ""
    return intent, af.parse_action(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v41_disk", required=True)
    ap.add_argument("--v4_glob", required=True, help="v4 train parquet shards, row-aligned with --v41_disk (unaugmented history)")
    ap.add_argument("--model", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--save_disk", required=True)
    ap.add_argument("--rate", type=float, default=0.4)
    ap.add_argument("--bs", type=int, default=48)
    ap.add_argument("--max_pixels", type=int, default=774400)
    ap.add_argument("--min_pixels", type=int, default=65536)
    ap.add_argument("--max_new_tokens", type=int, default=128)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--limit_episodes", type=int, default=0, help="smoke tests only")
    ap.add_argument("--no_generate", action="store_true", help="rebuild from a complete saved state only (round 5); exit if any step would need generation")
    a = ap.parse_args()
    import torch
    from datasets import load_from_disk
    from transformers import AutoModelForImageTextToText, AutoProcessor

    os.makedirs(a.work, exist_ok=True)
    import glob
    import pyarrow.parquet as pq
    from sft_waitrelabel import WAIT_ACT, WAIT_INTENT, WAITY
    ds = load_from_disk(a.v41_disk)
    src, eps, steps, msgs_col = ds["source"], ds["episode_id"], ds["step_idx"], ds["messages"]
    v4 = {"messages": [], "source": [], "episode_id": [], "step_idx": []}
    for f in sorted(glob.glob(a.v4_glob)):
        tb = pq.read_table(f, columns=list(v4)).to_pydict()
        for k2 in v4:
            v4[k2] += tb[k2]
    assert v4["source"] == src and v4["step_idx"] == steps and [str(x) for x in v4["episode_id"]] == [str(x) for x in eps], \
        "v4 shards are not row-aligned with the v4.1 dataset"
    # A row's position in its episode = the number of earlier steps in v4's (unaugmented) history; step_idx is not
    # usable (0-based in AndroidControl, 1-based in GUI-Odyssey). The human (intent, action) of every step comes from
    # v4's history lines (with v4.1's wait relabel, D1) and from the rows' own v4.1 targets. Episodes with duplicate
    # positions (synthetic answer episodes) are skipped.
    def human(intent, act):
        return (WAIT_INTENT, act) if act == WAIT_ACT and intent and not WAITY.search(intent) else (intent, act)

    groups: dict[str, list[tuple[int, int]]] = {}
    pos_of, lines_of = {}, {}
    for i, (s, e) in enumerate(zip(src, eps)):
        if selected(s, str(e), a.rate):
            _, lines = split_lines(v4["messages"][i][1]["content"])
            pos = int(lines[-1].split(". ", 1)[0]) if lines else 0
            pos_of[i], lines_of[i] = pos, lines
            groups.setdefault(f"{s}:{e}", []).append((pos, i))
    episodes, gt = {}, {}
    for e, v in groups.items():
        v.sort()
        if len({p for p, _ in v}) != len(v) or len(v) < 2:
            continue
        g = {}
        for p, i in v:
            for ln in lines_of[i]:
                n, rest = ln.split(". ", 1)
                intent, _, act = rest.rpartition(" -> ") if " -> " in rest else ("", "", rest)
                g.setdefault(int(n) - 1, human(intent, act))
            m = msgs_col[i]
            g[p] = (m[2].get("reasoning_content") or "", m[2]["content"])
        episodes[e], gt[e] = v, g
    if a.limit_episodes:
        episodes = dict(sorted(episodes.items())[:a.limit_episodes])
    n_rows = sum(len(v) for v in episodes.values())
    print(f"selected episodes {len(episodes)} (of {len(groups)} sampled), rows {n_rows}", flush=True)

    state_f = f"{a.work}/selfhist_state.json"
    st = json.load(open(state_f)) if os.path.exists(state_f) else {"round_done": -1, "self": {}, "log": {}, "bad": []}

    def history(e: str, t: int):
        """History for step t of episode e: own/patched entries where a row exists, human entries elsewhere; only the
        last HISTORY_STEPS are shown, earlier ones are placeholders that only fix the numbering. None if a shown step
        has no recoverable human entry."""
        own = st["self"].get(e, {})
        h = []
        for j in range(t):
            if j < t - af.HISTORY_STEPS:
                h.append(("", "{}"))
            elif str(j) in own:
                h.append(tuple(own[str(j)][:2]))
            elif j in gt[e]:
                h.append(gt[e][j])
            else:
                return None
        return h

    max_len = max(len(v) for v in episodes.values())
    if a.no_generate:
        if st["round_done"] < max_len - 2:
            sys.exit(f"--no_generate: saved state stops at round {st['round_done']}, needs {max_len - 2}")
        print(f"rebuilding from saved state (round {st['round_done']}), no generation", flush=True)
    else:
        proc = AutoProcessor.from_pretrained(a.model, trust_remote_code=True,
                                             size={"shortest_edge": a.min_pixels, "longest_edge": a.max_pixels})
        proc.tokenizer.padding_side = "left"
        model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16, trust_remote_code=True).to(a.device).eval()
    t0 = time.time()
    for k in range(st["round_done"] + 1, max_len - 1):   # the k-th stored step of each episode; the last one never feeds a history
        todo = [e for e, rows in episodes.items() if len(rows) > k + 1 and e not in st["bad"]]
        for b in range(0, len(todo), a.bs):
            batch, convs, gts = [], [], []
            for e in todo[b:b + a.bs]:
                t, i = episodes[e][k]
                h = history(e, t)
                if h is None:
                    st["bad"].append(e)
                    continue
                m = msgs_col[i]
                head, tail = split_user(m[1]["content"])
                convs.append([{"role": "system", "content": [{"type": "text", "text": m[0]["content"]}]},
                              {"role": "user", "content": [{"type": "image", "image": ds[i]["images"][0]},
                                                           {"type": "text", "text": head + af.history_text(h) + tail}]}])
                batch.append((e, t))
                gts.append(gt[e][t])
            if not convs:
                continue
            inputs = proc.apply_chat_template(convs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                              return_tensors="pt", padding=True, processor_kwargs={"padding": True},
                                              enable_thinking=True).to(a.device)
            with torch.inference_mode():
                out = model.generate(**inputs, max_new_tokens=a.max_new_tokens, do_sample=False)
            texts = proc.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=False)
            tail_tok = proc.tokenizer.decode(inputs["input_ids"][0][-4:], skip_special_tokens=False)
            for (e, t), txt, (gi, ga) in zip(batch, texts, gts):
                txt = txt.replace(proc.tokenizer.pad_token or "\x00", "")
                for eos in ("<|im_end|>", "<|endoftext|>"):
                    txt = txt.split(eos)[0]
                if tail_tok.rstrip().endswith("<think>"):
                    txt = "<think>" + txt
                pi, pa = parse_output(txt)
                ok = pa is not None and match(pa, json.loads(ga))[1]
                prev = history(e, t) or []
                if ok:
                    entry = [pi, af.action_to_str(pa), 1]
                elif pa is not None and pa["action_type"] == "wait":   # own no-op mistake: kept for a recovery row
                    entry = [gi, ga, 0, pi, af.action_to_str(pa)]
                else:
                    entry = [gi, ga, 0]
                st["self"].setdefault(e, {})[str(t)] = entry
                lg = st["log"].setdefault(str(k), {"n": 0, "match": 0, "pred_wait": 0, "pred_copy": 0, "unparsed": 0})
                lg["n"] += 1
                lg["match"] += ok
                lg["unparsed"] += pa is None
                lg["pred_wait"] += bool(pa and pa["action_type"] == "wait")
                lg["pred_copy"] += bool(prev and pi and pi == prev[-1][0])
        st["round_done"] = k
        json.dump(st, open(state_f + ".tmp", "w"))
        os.replace(state_f + ".tmp", state_f)
        lg = st["log"].get(str(k), {"n": 0})
        if lg["n"]:
            print(f"round {k}: {lg['n']} rows, match {lg['match'] / lg['n']:.3f}, wait {lg['pred_wait']}, "
                  f"copy {lg['pred_copy']}, unparsed {lg['unparsed']}, {time.time() - t0:.0f}s", flush=True)

    # rebuild histories into the rows; targets, images and row order unchanged
    new_text, own_wait_rows = {}, 0
    for e, rows in episodes.items():
        if e in st["bad"]:
            continue
        for t, i in rows:
            h = history(e, t) if t > 0 else []
            mis = st["self"].get(e, {}).get(str(t))
            if h is not None and mis is not None and len(mis) == 5:
                # The model wrongly waited at this step. A wait leaves the screen unchanged, so this row (same screen,
                # same human target) can show the model's own mistake (its intent + wait) as the last history step.
                h = list(h) + [(mis[3], mis[4])]
                own_wait_rows += 1
            if h:
                head, tail = split_user(msgs_col[i][1]["content"])
                new_text[i] = head + af.history_text(h) + tail

    def fn(messages, idx):
        out = []
        for m, i in zip(messages, idx):
            if i in new_text:
                m = [dict(x) for x in m]
                m[1]["content"] = new_text[i]
            out.append(m)
        return {"messages": out}

    ds2 = ds.map(fn, input_columns=["messages"], with_indices=True, batched=True, batch_size=512,
                 features=ds.features, desc="v4.2 rows")
    assert len(ds2) == len(ds)
    ds2.save_to_disk(a.save_disk)
    tot = {k2: sum(v[k2] for v in st["log"].values()) for k2 in ("n", "match", "pred_wait", "pred_copy", "unparsed")}
    own = sum(x[2] for d in st["self"].values() for x in d.values())
    stats = {"rate": a.rate, "episodes": len(episodes), "episodes_skipped_unrecoverable": len(st["bad"]),
             "rows_in_episodes": n_rows, "rows_with_new_history": len(new_text), "rows_own_wait_mistake": own_wait_rows,
             "generated": tot["n"],
             "model_steps_kept": own, "patched": tot["n"] - own, "totals": tot, "by_round": st["log"],
             "model": a.model, "builder_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
    json.dump(stats, open(f"{a.work}/v42_stats.json", "w"), indent=1)
    print(json.dumps({k2: stats[k2] for k2 in ("episodes", "episodes_skipped_unrecoverable", "rows_with_new_history",
                                                 "rows_own_wait_mistake",
                                                 "generated", "model_steps_kept", "patched", "totals")}), flush=True)


if __name__ == "__main__":
    main()
