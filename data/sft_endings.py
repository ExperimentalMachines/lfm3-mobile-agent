#!/usr/bin/env python3
"""Round 10 / v4.8 data (docs/preregistrations/round-10-multi-part-false-completes.md): v4.7 + GUI-Odyssey completion rows (reviewed, data/odyssey_endings_terminals.py)
+ their counterfactual rows + a progress count "[N left]" at the start of every training target's reasoning; multi-part
probes M_mid / M_done. CPU, build instance, seed 48.

N = actions left after this one before the task is done (0 for the last action and for `status` / `answer`; "5+" when 5
or more), from each episode's full length in its source:
  androidcontrol  stage ac_train: A = number of actions (steps are 0-based)            N = A - 1 - step
  odyssey         raw annotation: COMPLETE at step K (0-based)                           N = K - 1 - step
  amex            Aguvis amex-l2: terminate(success) at image step k (0-based; staged steps are 1-based)  N = k - step
  memgui          training rows: the `status` row's position T                           N = T - 1 - position
  counterfactual  stale / short: 0; ahead k: k - 1; nwait / nwaitload: the base row's N
Episodes whose end is unknown (GUI-Odyssey INCOMPLETE, AMEX without a successful terminate) leave the training split.
Usage: python sft_endings.py --v47 ~/r9mix --ody_term ~/r10/ody_term/disk --ac_stage ~/r7stage/ac_train \
         --ody_ann ~/data/raw/odyssey_ann/annotations --amex_l2 ~/data/raw/aguvis/amex-l2.json --ody_dev ~/r7stage/odyssey_dev \
         --pool ~/r7/data/v4work/app_pool.json --out ~/r10mix
"""
import argparse
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "train"))
import agent_format as af  # noqa: E402
import screen_change as sc  # noqa: E402
import sft_counterfactual as v46  # noqa: E402
from datasets import Dataset, Image as HFImage, Sequence, concatenate_datasets, load_dataset, load_from_disk  # noqa: E402

SEED = 48
N_PROBE = 300
GATES = ("test_ac_high", "dev_answer", "dev_complete", "dev_androidlens_high", "dev_memgui")
ST = Counter()
LIST_RE = re.compile(r"\b[\w'’\-\. ]{2,40},\s*[\w'’\-\. ]{2,40}(,\s*[\w'’\-\. ]{2,40})*,?\s+(and|&)\s+[\w'’\-\. ]{2,40}", re.I)
BLOCK_RE = re.compile(r"(^|\n)\s*(Expense|Recipe|Task|Contact|Event|Note|Item|Song|\d+[\.\)])\s*[:\-]?", re.I)


def multi_item(goal):  # as analysis/done_audit/goal_parts.py
    return bool(LIST_RE.search(goal or "")) or len(BLOCK_RE.findall(goal or "")) >= 2 or bool(re.search(r"\bfollowing\b[^.]*:", goal or "", re.I))


def fmt(n):
    return f"[{n if n < 5 else '5+'} left] "


def goal_of(user):
    return user.split("\n", 1)[0][len("Goal: "):]


def strip_notes(user):
    hm = v46.HB.search(user)
    lines = [l[: -len(sc.NOTE)] if l.endswith(sc.NOTE) else l for l in hm.group(2).split("\n")]
    return user[:hm.start(2)] + "\n".join(lines) + user[hm.end(2):]


def main():
    ap = argparse.ArgumentParser()
    for k in ("v47", "ody_term", "ac_stage", "ody_ann", "amex_l2", "ody_dev", "pool", "out"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    rnd = random.Random(SEED)
    train = load_from_disk(os.path.join(a.v47, "disk", "train"))
    if a.limit:
        train = train.select(range(min(a.limit, len(train))))
    term = load_from_disk(a.ody_term)
    ST["v47_train"], ST["ody_terminal_reviewed"] = len(train), len(term)

    # ---- 1. episode ends per source
    ac_len = {}
    for e, s, t in zip(load_from_disk(a.ac_stage)["episode_id"], load_from_disk(a.ac_stage)["step_idx"], load_from_disk(a.ac_stage)["is_terminal"]):
        if not t:
            ac_len[str(e)] = max(ac_len.get(str(e), 0), int(s) + 1)
    ody_end = {}
    for f in os.listdir(a.ody_ann):
        d = json.load(open(os.path.join(a.ody_ann, f)))
        if d["steps"]:
            ody_end[str(d["episode_id"])] = int(d["steps"][-1]["step"]) if d["steps"][-1]["action"] == "COMPLETE" else None
    amex_end = {}
    for x in json.load(open(a.amex_l2)):
        if isinstance(x.get("image"), str) and "terminate(status='success')" in x["conversations"][-1]["value"]:
            m = re.match(r"(.+)step(\d+)\.png$", os.path.basename(x["image"]))
            if m:
                amex_end[m.group(1)] = int(m.group(2))
    ST["ac_episodes"], ST["ody_complete_eps"], ST["amex_success_eps"] = len(ac_len), sum(v is not None for v in ody_end.values()), len(amex_end)

    # ---- 2. GUI-Odyssey terminal rows: hold out M_done, the rest join training with their counterfactual rows
    tmeta = term.select_columns(["messages", "episode_id"]).to_list()
    mi = [i for i, r in enumerate(tmeta) if multi_item(goal_of(r["messages"][1]["content"]))]
    rest = [i for i in range(len(term)) if i not in set(mi)]
    held = sorted(rnd.sample(mi, min(N_PROBE, len(mi))) + (rnd.sample(rest, N_PROBE - len(mi)) if len(mi) < N_PROBE else []))
    held_eps = {str(tmeta[i]["episode_id"]) for i in held}
    ST["m_done_held_out"], ST["m_done_multi_item"] = len(held), sum(1 for i in held if i in set(mi))
    term_train = term.select([i for i in range(len(term)) if i not in set(held)])
    meta = train.select_columns(["messages", "source", "episode_id", "step_idx", "gt_action"]).to_list()
    ody_rows = defaultdict(dict)  # episode -> {position: row}
    for i, r in enumerate(meta):
        if r["source"] == "odyssey" and "#" not in str(r["episode_id"]):
            ody_rows[str(r["episode_id"])][v46.position(r["messages"][1]["content"])] = i
    raw = train.cast_column("images", Sequence(HFImage(decode=False)))
    traw = term_train.cast_column("images", Sequence(HFImage(decode=False)))
    cf = []
    for j in range(len(traw)):
        tr = traw[j]
        e = str(tr["episode_id"])
        T = v46.position(tr["messages"][1]["content"])
        d = ody_rows.get(e, {})
        if (T - 1) not in d:
            ST["ody_cf_skipped_no_last_row"] += 1
            continue
        u = tr["messages"][1]["content"]
        hm = v46.HB.search(u)
        lines = hm.group(2).split("\n")
        last = raw[d[T - 1]]
        stale_lines = lines[:-1] + [lines[-1] if lines[-1].endswith(sc.NOTE) else lines[-1] + sc.NOTE]
        cf.append(dict(last, messages=v46.with_user(tr["messages"], u[:hm.start(2)] + "\n".join(stale_lines) + u[hm.end(2):], dict(last["messages"][2])),
                       episode_id=f"{e}#cf_stale1", is_terminal=False))
        ST["ody_cf_stale"] += 1
        for k in (2, 3):
            if (T - k) in d and rnd.random() < 0.5:
                rk = raw[d[T - k]]
                cf.append(dict(rk, messages=v46.with_user(tr["messages"], u, dict(rk["messages"][2])), episode_id=f"{e}#cf_ahead{k}", is_terminal=False))
                ST["ody_cf_ahead"] += 1
                break
        if rnd.random() < 0.5:
            kk = rnd.choice((1, 2))
            short = lines[:-kk] if len(lines) > kk else ["None"]
            cf.append(dict(tr, messages=v46.with_user(tr["messages"], u[:hm.start(2)] + "\n".join(short) + u[hm.end(2):]), episode_id=f"{e}#cf_short{kk}"))
            ST["ody_cf_short"] += 1
    keep_cols = raw.features
    new = Dataset.from_list([{k: r.get(k, "" if k in ("mode", "gt_bbox") else None) for k in keep_cols} | {"mode": "high", "gt_bbox": r.get("gt_bbox") or ""}
                             for r in list(traw) + cf], features=keep_cols).cast(train.features)
    train = concatenate_datasets([train, new])
    ST["ody_terminal_train"], ST["ody_cf_rows"] = len(traw), len(cf)

    # ---- 3. progress count on every training target
    meta = train.select_columns(["messages", "source", "episode_id", "step_idx", "gt_action", "is_terminal"]).to_list()
    mg_end = {}
    for r in meta:
        if r["source"] == "memgui" and "#" not in str(r["episode_id"]) and json.loads(r["gt_action"])["action_type"] == "status":
            mg_end[str(r["episode_id"])] = v46.position(r["messages"][1]["content"])
    mg_max = defaultdict(int)
    for r in meta:
        if r["source"] == "memgui" and "#" not in str(r["episode_id"]):
            mg_max[str(r["episode_id"])] = max(mg_max[str(r["episode_id"])], v46.position(r["messages"][1]["content"]))
    rel = {(x["source"], str(x["episode_id"]), int(x["step_idx"])) for x in json.load(open(os.path.join(a.v47, "relabelled_rows.json")))}

    def base_n(src, e, step, pos, typ):
        if typ in ("status", "answer") or src == "screenqa":
            return 0
        if src == "androidcontrol":
            return None if e not in ac_len else ac_len[e] - 1 - step
        if src == "odyssey":
            K = ody_end.get(e)
            return None if K is None else K - 1 - step
        if src == "amex":
            return None if e not in amex_end else amex_end[e] - step
        if src == "memgui":
            T = mg_end.get(e, mg_max.get(e, pos) + 1)
            return T - 1 - pos
        return None
    ns, drop = [], []
    for i, r in enumerate(meta):
        e = str(r["episode_id"])
        typ = json.loads(r["gt_action"])["action_type"]
        be, kind = (e.split("#cf_") + [""])[:2]
        if kind.startswith(("stale", "short")):
            n = 0
        elif kind.startswith("ahead"):
            n = int(kind[-1]) - 1
        else:  # real rows, nwait / nwaitload (same screen and label as their base row; their appended waits are not progress)
            pos = v46.position(r["messages"][1]["content"]) - (int(kind[-1]) if kind.startswith("nwait") else 0)
            n = base_n(r["source"], be, int(r["step_idx"]), pos, typ)
            if n is not None and kind == "" and (r["source"], e, int(r["step_idx"])) in rel:
                n -= 1  # the relabelled wait does the next action now
        if n is None:
            drop.append(i)
            ST[f"drop_unknown_end_{r['source']}"] += 1
            continue
        if n < 0:
            ST[f"n_negative_clamped_{r['source']}"] += 1
            n = 0
        ns.append((i, n))
        ST[f"n_{min(n, 5)}"] += 1
    keep = [i for i, _ in ns]
    nmap = dict(ns)
    msgs = []
    for i in keep:
        m = [dict(x) for x in meta[i]["messages"]]
        m[2] = {**m[2], "reasoning_content": fmt(nmap[i]) + af.strip_progress(m[2].get("reasoning_content") or "")}
        msgs.append(m)
    train = train.select(keep).remove_columns(["messages"])
    train = train.add_column("messages", msgs, feature=load_from_disk(os.path.join(a.v47, "disk", "train")).features["messages"])
    train = train.shuffle(seed=SEED).flatten_indices()

    # ---- 4. probes: round 9's, plus M_done (held-out terminal rows) and M_mid (GUI-Odyssey test-split rows 1-3 actions before the end)
    probes = {}
    for f in sorted(os.listdir(os.path.join(a.v47, "probes"))):
        probes[f[len("probe_"):-len(".parquet")]] = load_dataset("parquet", data_files=os.path.join(a.v47, "probes", f), split="train")
    probes["M_done"] = term.select(held).add_column("probe", ["M_done"] * len(held)).add_column("probe_note", [""] * len(held))
    dev = load_from_disk(a.ody_dev)
    dmeta = dev.select_columns(["messages", "episode_id", "step_idx", "gt_action"]).to_list()
    cand = []
    for i, r in enumerate(dmeta):
        K = ody_end.get(str(r["episode_id"]))
        if K is None or json.loads(r["gt_action"])["action_type"] == "status":
            continue
        n = K - 1 - int(r["step_idx"])
        if 0 <= n <= 2:  # this row is one of the last three actions before COMPLETE
            cand.append((not multi_item(goal_of(r["messages"][1]["content"])), i))
    cand.sort()
    pick = sorted(i for _, i in cand[:N_PROBE])
    mid = dev.select(pick)
    import sft_fullmix as v45  # the mix's v4 prompt + installed-app list, as every training row has
    pool = json.load(open(a.pool))
    mrows = mid.select_columns(["messages", "episode_id", "gt_action"]).to_list()
    apps = v45.ep_apps((("odyssey", str(r["episode_id"]), r["messages"][1]["content"], r["gt_action"]) for r in mrows), pool)
    mid = v46.map_messages(mid, lambda r: v45.to_v4(v46.with_user(r["messages"], strip_notes(r["messages"][1]["content"])),
                                                    "odyssey", str(r["episode_id"]), apps, pool), ["messages", "episode_id"])
    for r in mid.select_columns(["messages"]):
        assert r["messages"][0]["content"] == af.SYSTEM_PROMPT_V4 and "\nInstalled apps: " in r["messages"][1]["content"]
    probes["M_mid"] = mid.add_column("probe", ["M_mid"] * len(mid)).add_column("probe_note", [""] * len(mid))
    ST["m_mid_rows"], ST["m_mid_multi_item"] = len(mid), sum(1 for f_, _ in cand[:N_PROBE] if not f_)

    # ---- 5. checks
    nh = []
    for r in train.select_columns(["messages", "gt_action"]):
        m = r["messages"]
        assert [x["role"] for x in m] == ["system", "user", "assistant"]
        a_ = af.parse_action(m[2]["content"], strict=True)
        assert a_ is not None and a_ == json.loads(r["gt_action"]), (m[2]["content"], r["gt_action"])
        assert af.progress_of(m[2]["reasoning_content"]) is not None, m[2]["reasoning_content"]
        hl = [l for l in v46.HB.search(m[1]["content"]).group(2).split("\n") if v46.LINE.match(l)]
        assert not any(af.PROGRESS_RE.match(l.split(". ", 1)[1]) for l in hl), "progress leaked into history"
        nh.append(len(hl))
    ST["train_rows"], ST["train_history_max"] = len(train), max(nh)
    ST["train_actions"] = dict(Counter(json.loads(g)["action_type"] for g in train["gt_action"]))
    ST["train_status_by_source"] = dict(Counter(s for s, g in zip(train["source"], train["gt_action"]) if json.loads(g)["action_type"] == "status"))
    os.makedirs(os.path.join(a.out, "probes"), exist_ok=True)
    train.save_to_disk(os.path.join(a.out, "disk", "train"))
    for k in GATES:
        load_from_disk(os.path.join(a.v47, "disk", k)).save_to_disk(os.path.join(a.out, "disk", k))
    for k, d in probes.items():
        if "images" in d.column_names:
            d = d.cast_column("images", Sequence(HFImage()))
        d.to_parquet(os.path.join(a.out, "probes", f"probe_{k}.parquet"))
        ST[f"probe_{k}_rows"] = len(d)
    json.dump(ST, open(os.path.join(a.out, "build_stats.json"), "w"), indent=1)
    print("V48_DONE", json.dumps(ST), flush=True)


if __name__ == "__main__":
    main()
