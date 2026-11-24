#!/usr/bin/env python3
"""Round 8 / v4.6 data (docs/PREREG_v46.md): v4.5 + the "done but not done yet" fixes. CPU, build instance, seed 46.

Findings it fixes (analysis/done_audit, 2026-11-24):
  * The model decides `status` from its own history: on the same unfinished screen, a history claiming every step raises
    D's done-rate 3.7% -> 53.7%. In every demonstration the history and the screen agree, so the history is a shortcut.
  * Round 6's no-visible-change rule (72x160 mean diff < 1.0) is wrong on 67% of the pairs it flags; 629 `status` rows
    follow a step it marked "[no visible change]".
  * Some AndroidControl `status` rows show a screen that is still loading, or a task that is not done.

Steps:
  1. notes      every history note recomputed with train/screen_change.py (360x800, bars masked, > 0.1% of pixels)
                from the real screens of the episode; a line keeps no note when either screen is unavailable
  2. judge      `status` rows: NOT_COMPLETE (Qwen3-VL-8B judge, goal + final screenshot only) -> dropped;
                PENDING -> relabelled `wait` ("Wait for the screen to finish loading.")
  3. counterfactual rows that separate history from screen, built only from training episodes whose final row is a
     kept `status` / `answer` and whose last action is not scroll / wait:
       stale  screen BEFORE the last action + the full history, last line noted " [no visible change]" (the run-time
              note when an action does nothing)                     -> the expert action on that screen (redo it)
       ahead  screen 2 or 3 steps before the end + the full history (claims steps the screen does not show)
                                                                    -> the expert action on that screen
       short  the judged-COMPLETE final screen + the history without its last 1-2 steps  -> `status complete`
  4. gate splits: notes recomputed; history probes rebuilt from the new test split (analysis/done_audit)
Usage: python v46_build.py --v45 ~/r7mix/disk --stage ~/r7stage --judge verdicts.jsonl --pool app_pool.json --out ~/r8mix
"""
import argparse
import hashlib
import json
import multiprocessing as mp
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
from datasets import Image as HFImage, Sequence, concatenate_datasets, load_from_disk  # noqa: E402

SEED = 46
HB = re.compile(r"(\nPrevious steps:\n)(.*?)(\nWhat is the next action\?)$", re.S)
LINE = re.compile(r"^(\d+)\. (.*)$")
SKIP_TYPES = ("wait", "status", "answer")
WAIT_INTENT = "Wait for the screen to finish loading."
WAITISH = re.compile(r"\b(wait|load|loading|loaded|pause|until|appear|finish)", re.I)  # an intent that describes waiting
ST = Counter()


def base_ep(e):
    return str(e).split("#", 1)[0]


# ---------------------------------------------------------------- 1. screen-change map
_DS = {}


def _pairs_worker(job):
    """job = (dataset key, source tag, episode, [(step, row index), ...]) -> {(tag, ep, step): changed(step, step+1)}"""
    key, tag, ep, steps = job
    ds = _DS[key]
    prev, out = None, {}
    for s, i in steps:
        img = ds[i]["images"]
        cur = sc.prep(img[0]["bytes"]) if img else None
        if prev is not None and prev[0] == s - 1 and cur is not None and prev[1] is not None:
            out[(tag, ep, s - 1)] = sc.changed(prev[1], cur)
        prev = (s, cur)
    return out


def position(user):
    """0-based position of a row in its episode = absolute number of its last history line (0 when there is none).
    GUI-Odyssey and AMEX step numbers are not positions (AMEX counts from 1; merged keyboard steps leave gaps), so
    screens are paired by position: history line j (step at position j-1) is compared with positions j-1 and j."""
    nums = [int(m.group(1)) for m in map(LINE.match, HB.search(user).group(2).split("\n")) if m]
    return nums[-1] if nums else 0


def change_map(sources, workers):
    """sources: [(key, dataset, tag_fn, positional)] -> {(tag, ep, position): screen changed between position and +1}.
    positional=False keys by step_idx (only for AndroidControl's stage rows, whose step numbers are positions)."""
    jobs = []
    for key, ds, tag_fn, positional in sources:
        _DS[key] = ds.cast_column("images", Sequence(HFImage(decode=False))).select_columns(["images"])
        eps = defaultdict(dict)
        pos = [position(m[1]["content"]) for m in ds["messages"]] if positional else [int(s) for s in ds["step_idx"]]
        for i, (src, e, s) in enumerate(zip(ds["source"], ds["episode_id"], pos)):
            eps[(tag_fn(src), base_ep(e))].setdefault(int(s), i)
        for (tag, ep), d in eps.items():
            jobs.append((key, tag, ep, sorted(d.items())))
    out = {}
    with mp.get_context("fork").Pool(workers) as pool:
        for m in pool.imap_unordered(_pairs_worker, jobs, chunksize=64):
            out.update(m)
    return out


def renote(user, tag, ep, cmap):
    """Strip every old note, then note line j (step j-1) when cmap says step j-1 -> j did not change the screen."""
    m = HB.search(user)
    lines = m.group(2).split("\n")
    new = []
    for line in lines:
        if line.endswith(sc.NOTE):
            line = line[: -len(sc.NOTE)]
            ST["notes_old"] += 1
        mm = LINE.match(line)
        if mm:
            j = int(mm.group(1))
            act = line.rsplit(" -> ", 1)[-1] if " -> " in line else mm.group(2)
            try:
                typ = json.loads(act).get("action_type")
            except Exception:
                typ = None
            if typ == "wait" and " -> " in line:  # AndroidControl copies the previous intent onto `wait` steps
                intent = line.split(" -> ", 1)[0].split(". ", 1)[1]
                if not WAITISH.search(intent):
                    line = f"{j}. {WAIT_INTENT} -> {act}"
                    ST["history_wait_intent_relabelled"] += 1
            ch = cmap.get((tag, ep, j - 1))
            if typ not in SKIP_TYPES and ch is False:
                line += sc.NOTE
                ST["notes_new"] += 1
            elif ch is None and typ not in SKIP_TYPES:
                ST["notes_unknown_pair"] += 1
        new.append(line)
    return user[:m.start(2)] + "\n".join(new) + user[m.end(2):]


def map_messages(ds, fn, cols):
    rows = ds.select_columns(cols).to_list()
    return ds.remove_columns(["messages"]).add_column("messages", [fn(r) for r in rows], feature=ds.features["messages"])


def with_user(m, user, assistant=None):
    out = [dict(m[0]), {**m[1], "content": user}]
    return out + ([assistant] if assistant is not None else [dict(x) for x in m[2:]])


def tag_of(src):
    return "androidcontrol" if src in ("androidcontrol",) else src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v45", required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--judge", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=28)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    rnd = random.Random(SEED)
    lim = (lambda d: d.select(range(min(a.limit, len(d))))) if a.limit else (lambda d: d)
    train = lim(load_from_disk(os.path.join(a.v45, "train")))
    gates = {k: lim(load_from_disk(os.path.join(a.v45, k))) for k in
             ("test_ac_high", "dev_answer", "dev_complete", "dev_androidlens_high", "dev_memgui")}
    ac_stage = load_from_disk(os.path.join(a.stage, "ac_train"))  # every AndroidControl train screen (held-out, cleaned too)
    ST["train_in"] = len(train)

    # ---- 1. change map (AndroidControl train screens from the stage, test screens tagged separately)
    srcs = [("ac_stage", ac_stage, lambda s: "androidcontrol", False),
            ("train", train.filter(lambda s: s != "androidcontrol" and s != "screenqa", input_columns="source"), tag_of, True),
            ("test", gates["test_ac_high"], lambda s: "ac_test", True),
            ("al", gates["dev_androidlens_high"], lambda s: "androidlens", True),
            ("dm", gates["dev_memgui"], lambda s: "memgui", True)]
    cmap = change_map(srcs, a.workers)
    ST["change_pairs"] = len(cmap)
    ST["change_pairs_unchanged"] = sum(1 for v in cmap.values() if not v)

    # ---- 2. judge verdicts on `status` rows
    verdict = {}
    for l in open(a.judge):
        j = json.loads(l)
        verdict[(j["source"], str(j["episode_id"]), int(j["step_idx"]))] = j["verdict"]
    ST.update({f"judge_{k}": v for k, v in Counter(verdict.values()).items()})

    # ---- 3. rewrite train rows: notes, judge actions
    def train_fn(r):
        m = [dict(x) for x in r["messages"]]
        tag, ep = tag_of(r["source"]), base_ep(r["episode_id"])
        if r["source"] != "screenqa":
            m[1]["content"] = renote(m[1]["content"], tag, ep, cmap)
        g = json.loads(r["gt_action"])
        if g["action_type"] == "wait" and not WAITISH.search(m[2].get("reasoning_content") or ""):
            m[2] = {**m[2], "reasoning_content": WAIT_INTENT}
            ST["target_wait_intent_relabelled"] += 1
        if g["action_type"] == "status" and verdict.get((r["source"], str(r["episode_id"]), int(r["step_idx"]))) == "PENDING":
            m[2] = {**m[2], "content": af.action_to_str({"action_type": "wait"}), "reasoning_content": WAIT_INTENT}
        return m
    train = map_messages(train, train_fn, ["messages", "source", "episode_id", "step_idx", "gt_action"])
    pend = [i for i, (s, e, t, g) in enumerate(zip(train["source"], train["episode_id"], train["step_idx"], train["gt_action"]))
            if json.loads(g)["action_type"] == "status" and verdict.get((s, str(e), int(t))) == "PENDING"]
    gt = list(train["gt_action"])
    for i in pend:
        gt[i] = json.dumps({"action_type": "wait"})
    train = train.remove_columns(["gt_action"]).add_column("gt_action", gt)
    ST["status_relabelled_wait_pending"] = len(pend)
    drop = {i for i, (s, e, t, g) in enumerate(zip(train["source"], train["episode_id"], train["step_idx"], train["gt_action"]))
            if json.loads(g)["action_type"] == "status" and verdict.get((s, str(e), int(t))) == "NOT_COMPLETE"}
    ST["status_dropped_not_complete"] = len(drop)
    keep_status_eps = {(s, base_ep(e)) for i, (s, e, g) in enumerate(zip(train["source"], train["episode_id"], train["gt_action"]))
                       if i not in drop and json.loads(g)["action_type"] in ("status", "answer")}
    train = train.select([i for i in range(len(train)) if i not in drop])

    # ---- 4. counterfactual rows from episodes with a kept final row (image bytes kept as they are: no re-encoding)
    raw = train.cast_column("images", Sequence(HFImage(decode=False)))
    idx = defaultdict(dict)  # (source, full episode id) -> {step: row index}
    for i, (s, e, t) in enumerate(zip(train["source"], train["episode_id"], train["step_idx"])):
        if s in ("androidcontrol", "memgui"):
            idx[(s, str(e))][int(t)] = i
    cf = []  # (row index whose image is used, row index of the final row, kind, k)
    for (s, e), d in idx.items():
        if (s, base_ep(e)) not in keep_status_eps or not d:
            continue
        T = max(d)
        fin = raw[d[T]]
        ft = json.loads(fin["gt_action"])["action_type"]
        if ft not in ("status", "answer") or T < 3 or (T - 1) not in d:
            continue
        last = json.loads(raw[d[T - 1]]["gt_action"])
        if last["action_type"] in ("scroll", "wait"):
            continue
        cf.append((d[T - 1], d[T], "stale", 1))
        for k in (2, 3):
            if (T - k) in d and rnd.random() < 0.5:
                cf.append((d[T - k], d[T], "ahead", k))
                break
        if ft == "status" and verdict.get((s, str(e), T)) == "COMPLETE" and rnd.random() < 0.5:
            cf.append((d[T], d[T], "short", rnd.choice((1, 2))))
    ST.update({f"cf_{k}": v for k, v in Counter(c[2] for c in cf).items()})

    def cf_row(c):
        src_i, fin_i, kind, k = c
        img_row, fin = raw[src_i], raw[fin_i]
        m = [dict(x) for x in fin["messages"]]
        u = m[1]["content"]
        hm = HB.search(u)
        lines = hm.group(2).split("\n")
        if kind == "stale":
            if not lines[-1].endswith(sc.NOTE):
                lines[-1] += sc.NOTE
            asst = dict(img_row["messages"][2])
        elif kind == "ahead":
            asst = dict(img_row["messages"][2])
        else:  # short
            lines = lines[:-k] if len(lines) > k else ["None"]
            asst = dict(m[2])
        user = u[:hm.start(2)] + "\n".join(lines) + u[hm.end(2):]
        gt = img_row["gt_action"] if kind != "short" else fin["gt_action"]
        return {"images": img_row["images"], "messages": with_user(m, user, asst), "source": fin["source"],
                "episode_id": f"{fin['episode_id']}#cf_{kind}{k}", "step_idx": int(img_row["step_idx"]), "mode": "high",
                "gt_action": gt, "gt_bbox": "", "is_terminal": kind == "short"}
    from datasets import Dataset
    cf_ds = Dataset.from_list([cf_row(c) for c in cf], features=raw.features).cast(train.features)
    train = concatenate_datasets([train, cf_ds]).shuffle(seed=SEED).flatten_indices()

    # ---- 5. gate splits: notes recomputed
    out_g = {}
    for k, d in gates.items():
        tag = {"test_ac_high": "ac_test", "dev_androidlens_high": "androidlens", "dev_memgui": "memgui"}.get(k, "androidcontrol")
        out_g[k] = map_messages(d, lambda r, tag=tag: with_user(r["messages"], renote(r["messages"][1]["content"], tag, base_ep(r["episode_id"]), cmap)),
                                ["messages", "episode_id"])

    # ---- 6. checks
    for name, d in [("train", train), *out_g.items()]:
        nh = []
        for r in d.select_columns(["messages", "gt_action"]):
            m = r["messages"]
            assert [x["role"] for x in m] == ["system", "user", "assistant"], name
            a_ = af.parse_action(m[2]["content"], strict=True)
            assert a_ is not None and a_ == json.loads(r["gt_action"]), (name, m[2]["content"], r["gt_action"])
            nh.append(sum(1 for l in HB.search(m[1]["content"]).group(2).split("\n") if LINE.match(l)))
        ST[f"{name}_rows"] = len(d)
        ST[f"{name}_history_max"] = max(nh) if nh else 0
    ST["train_actions"] = dict(Counter(json.loads(g)["action_type"] for g in train["gt_action"]))
    ST["train_by_source"] = dict(Counter(train["source"]))
    os.makedirs(a.out, exist_ok=True)
    for k, d in [("train", train), *out_g.items()]:
        d.save_to_disk(os.path.join(a.out, "disk", k))
    json.dump(ST, open(os.path.join(a.out, "build_stats.json"), "w"), indent=1)
    print("V46_DONE", json.dumps(ST), flush=True)


if __name__ == "__main__":
    main()
