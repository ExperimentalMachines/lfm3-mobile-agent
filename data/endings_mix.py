#!/usr/bin/env python3
"""Round 11 (docs/preregistrations/round-11-checked-endings.md): candidate E-T's fixed continuation mix and the two multi-part probes. Runs inside the
SageMaker job before training (CPU). Seed 11.

Inputs
  * E's training split: experimentalmachines/MobileAgent-SFT-Counterfactual @ 0ace5559, train (185,643 rows, from the Hub)
  * the 1,766 GUI-Odyssey terminal candidates (data/odyssey_endings_terminals.py + data/odyssey_endings_filter.py, exported as
    parquet: episode_id, step_idx, user, jpg) and the calibrated Claude judge's verdicts on them
    (results/v48_dev/claude_ody_terminal_verdicts.jsonl; owner's definition of done, round 10 preregistration 17:10)

Rows
  * judged COMPLETE (947): 200 random -> probe M_done (never trained); the rest -> training rows `status complete`
    (terminal screen + the episode's full history, rebuilt from E's own last training row of the episode, exactly as
    odyssey_endings_terminals.py did) + their counterfactual rows, sft_endings.py's rules:
        stale1  the screen before the last action, that action noted "[no visible change]"   -> redo it
        ahead2/3 (half) a screen 2-3 actions before the end, the full history                 -> that screen's action
        short1/2 (half) the terminal screen, history without its last 1-2 lines               -> `status complete`
  * judged NOT_COMPLETE (819) -> probe M_notdone (never trained; the human stopped, the judge says the goal is not met)
  * E's own real rows of the trained episodes' last 3 positions before the end (the contrast: same goal, not done yet)
  * the rest of the N_MIX rows drawn uniformly from E's training split
Out: OUT/mix, OUT/probe_M_done, OUT/probe_M_notdone (save_to_disk), OUT/mix_stats.json
Usage: python endings_mix.py --term ody_term2.parquet --verdicts claude_ody_terminal_verdicts.jsonl --out OUT
         [--n_mix 32000] [--limit 0] [--shards 0]     (limit: terminal rows per class, shards: first N train shards; tests)
"""
import argparse
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, "..", "train")):
    sys.path.insert(0, p)
import agent_format as af  # noqa: E402
import screen_change as sc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from datasets import Dataset, Image as HFImage, Sequence, concatenate_datasets, load_dataset  # noqa: E402
from huggingface_hub import HfApi  # noqa: E402

REPO, REV = "experimentalmachines/MobileAgent-SFT-Counterfactual", "0ace5559e6c0b808a5ddf4e4ce9831d1d3614471"
SEED, N_DONE_PROBE, HIST = 11, 200, 24
DONE_ACT = {"action_type": "status", "goal_status": "complete"}
DONE = {"role": "assistant", "content": af.action_to_str(DONE_ACT), "reasoning_content": "The goal has been completed."}
ST = Counter()
DIFFS = []  # rebuilt history != the text the judge saw (expected only with --shards)
HB = re.compile(r"(\nPrevious steps:\n)(.*?)(\nWhat is the next action\?)$", re.S)  # = data/sft_counterfactual.py
LINE = re.compile(r"^(\d+)\. (.*)$")


def position(user):  # = data/v46_build.position
    nums = [int(m.group(1)) for m in map(LINE.match, HB.search(user).group(2).split("\n")) if m]
    return nums[-1] if nums else 0


def with_user(m, user, assistant=None):  # = data/v46_build.with_user
    out = [dict(m[0]), {**m[1], "content": user}]
    return out + ([assistant] if assistant is not None else [dict(x) for x in m[2:]])


def set_hist(user, lines):
    hm = HB.search(user)
    return user[:hm.start(2)] + "\n".join(lines) + user[hm.end(2):]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--term", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n_mix", type=int, default=32000)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--shards", type=int, default=0)
    a = ap.parse_args()
    rnd = random.Random(SEED)
    files = sorted(f for f in HfApi().list_repo_files(REPO, repo_type="dataset", revision=REV) if f.startswith("data/train-"))
    if a.shards:
        files = files[:a.shards]
    train = load_dataset(REPO, data_files={"train": files}, split="train", revision=REV)
    ST["e_train_rows"] = len(train)

    # ---- E's GUI-Odyssey rows by episode and position
    src, eps, msgs = train["source"], train["episode_id"], train["messages"]
    ody = defaultdict(dict)
    for i, (s, e, m) in enumerate(zip(src, eps, msgs)):
        if s == "odyssey" and "#" not in str(e):
            ody[str(e)][position(m[1]["content"])] = i
    raw = train.cast_column("images", Sequence(HFImage(decode=False)))

    # ---- terminal rows, rebuilt from E's own last row of each episode
    verd = {}
    for l in open(a.verdicts):
        j = json.loads(l)
        verd[j["case"]] = j["verdict"]
    term = pq.read_table(a.term).to_pylist()
    rows = {"COMPLETE": [], "NOT_COMPLETE": []}
    for t in term:
        e, K = str(t["episode_id"]), int(t["step_idx"])
        v = verd[f"ody_{e}_{K}"]
        if a.limit and len(rows[v]) >= a.limit:
            continue
        d = ody.get(e)
        if not d:
            ST["skip_episode_not_in_train"] += 1
            continue
        p = max(d)
        last = raw[d[p]]
        m = last["messages"]
        line = f"{p + 1}. {m[2].get('reasoning_content') or ''} -> {m[2]['content']}"
        if not sc.changed(sc.prep(last["images"][0]["bytes"]), sc.prep(t["jpg"])):
            line += sc.NOTE
        lines = [l for l in HB.search(m[1]["content"]).group(2).split("\n") if LINE.match(l)] + [line]
        user = set_hist(m[1]["content"], lines[-HIST:])
        ST["user_equals_judged_text"] += user == t["user"]
        if user != t["user"]:
            ST["user_differs_from_judged_text"] += 1
            DIFFS.append({"case": f"ody_{e}_{K}", "rebuilt": user[-600:], "judged": t["user"][-600:]})
        rows[v].append({"images": [{"bytes": t["jpg"], "path": None}], "messages": with_user(m, user, dict(DONE)),
                        "source": "odyssey", "episode_id": e, "step_idx": K, "mode": "high", "gt_bbox": "",
                        "gt_action": json.dumps(DONE_ACT), "is_terminal": True, "_last": d})
    ST["judged_complete"], ST["judged_not_complete"] = len(rows["COMPLETE"]), len(rows["NOT_COMPLETE"])
    if not a.shards and (DIFFS or ST["skip_episode_not_in_train"]):  # full split: every row must be what the judge saw
        json.dump(DIFFS[:20], open(os.path.join(a.out + "_diffs.json"), "w"), indent=1)
        raise SystemExit(f"R11_MIX_FAILED: {len(DIFFS)} rebuilt rows differ from the judged text, "
                         f"{ST['skip_episode_not_in_train']} episodes missing ({a.out}_diffs.json)")
    done = rows["COMPLETE"]
    held = set(rnd.sample(range(len(done)), min(N_DONE_PROBE if not a.limit else a.limit // 4, len(done))))
    probe_done = [r for i, r in enumerate(done) if i in held]
    term_train = [r for i, r in enumerate(done) if i not in held]
    ST["probe_M_done"], ST["probe_M_notdone"], ST["terminal_train"] = len(probe_done), len(rows["NOT_COMPLETE"]), len(term_train)

    # ---- counterfactual rows (sft_endings.py's rules) and E's real rows before the end
    cf, must = [], []
    for tr in term_train:
        e, d = tr["episode_id"], tr["_last"]
        u = tr["messages"][1]["content"]
        T = position(u)
        lines = HB.search(u).group(2).split("\n")
        last = raw[d[T - 1]]
        stale = lines[:-1] + [lines[-1] if lines[-1].endswith(sc.NOTE) else lines[-1] + sc.NOTE]
        cf.append(dict(last, messages=with_user(tr["messages"], set_hist(u, stale), dict(last["messages"][2])),
                       episode_id=f"{e}#cf_stale1", is_terminal=False))
        ST["cf_stale"] += 1
        for k in (2, 3):
            if (T - k) in d and rnd.random() < 0.5:
                rk = raw[d[T - k]]
                cf.append(dict(rk, messages=with_user(tr["messages"], u, dict(rk["messages"][2])), episode_id=f"{e}#cf_ahead{k}",
                               is_terminal=False))
                ST["cf_ahead"] += 1
                break
        if rnd.random() < 0.5:
            kk = rnd.choice((1, 2))
            short = lines[:-kk] if len(lines) > kk else ["None"]
            cf.append(dict(tr, messages=with_user(tr["messages"], set_hist(u, short)), episode_id=f"{e}#cf_short{kk}"))
            ST["cf_short"] += 1
        for k in (1, 2, 3):
            if (T - k) in d:
                must.append(d[T - k])
    must = sorted(set(must))
    ST["e_real_rows_before_end"] = len(must)

    cols = raw.features

    def to_ds(rs):
        clean = [{k: r.get(k) for k in cols} | {"mode": r.get("mode") or "high", "gt_bbox": r.get("gt_bbox") or ""} for r in rs]
        return Dataset.from_list(clean, features=cols).cast(train.features)
    new = to_ds(term_train + cf)
    n_rest = a.n_mix - len(new) - len(must)
    assert n_rest > 0, (a.n_mix, len(new), len(must))
    taken = set(must)
    rest = rnd.sample([i for i in range(len(train)) if i not in taken], n_rest)
    ST["replay_uniform"] = n_rest
    mix = concatenate_datasets([new, train.select(must + rest)]).shuffle(seed=SEED).flatten_indices()

    # ---- checks
    nst = Counter()
    for r in new.select_columns(["messages", "gt_action", "episode_id"]):
        m = r["messages"]
        assert [x["role"] for x in m] == ["system", "user", "assistant"]
        act = af.parse_action(m[2]["content"], strict=True)
        assert act is not None and act == json.loads(r["gt_action"]), (m[2]["content"], r["gt_action"])
        hl = [l for l in HB.search(m[1]["content"]).group(2).split("\n") if LINE.match(l)]
        assert len(hl) <= HIST
        nst[act["action_type"]] += 1
    ST["new_rows"], ST["new_actions"] = len(new), dict(nst)
    ST["mix_rows"] = len(mix)
    ga = Counter(json.loads(g)["action_type"] for g in mix["gt_action"])
    ST["mix_actions"], ST["mix_status_share"] = dict(ga), round(ga["status"] / len(mix), 4)
    ST["e_train_status_share"] = round(sum(json.loads(g)["action_type"] == "status" for g in train["gt_action"]) / len(train), 4)
    os.makedirs(a.out, exist_ok=True)
    mix.save_to_disk(os.path.join(a.out, "mix"))
    to_ds(probe_done).save_to_disk(os.path.join(a.out, "probe_M_done"))
    to_ds(rows["NOT_COMPLETE"]).save_to_disk(os.path.join(a.out, "probe_M_notdone"))
    json.dump({"stats": ST, "probe_M_done": [f"{r['episode_id']}_{r['step_idx']}" for r in probe_done]},
              open(os.path.join(a.out, "mix_stats.json"), "w"), indent=1)
    print("R11_MIX_DONE", json.dumps(ST), flush=True)


if __name__ == "__main__":
    main()
