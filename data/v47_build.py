#!/usr/bin/env python3
"""Round 9 / v4.7 data (docs/PREREG_v47.md): v4.6 + the wait fixes. CPU, build instance, seed 47.

Findings it fixes (analysis/done_audit/wait_detail.py and the AndroidWorld runs, 2026-11-25):
  * In D's AndroidWorld run 17% of steps are `wait`; 83% of those change nothing on screen, and 39% of its waits follow
    another wait (streaks of up to 5). In AndroidControl train only 4.8% of steps after a `wait` are another `wait`.
  * The "[no visible change]" note skips `wait` steps, in the training data and in the agent alike. After a useless wait
    the model sees the same screen and an unmarked wait line, so it decides the same way again.
  * The wait labels themselves are mostly right: before/after pairs show the next screen still loading. 62 of 6,592
    waits sit on a screen that the human then acted on with nothing changed.

Steps:
  1. wait notes  history lines of `wait` steps get " [no visible change]" when the next screen is unchanged (the v4.6
                 rule, train/screen_change.py, positional pairs) in train, gate splits and probes; every other line as is
  2. relabel     a `wait` row whose next screen is unchanged and whose next action is not `wait` takes that next action
                 as its label (same screen, so its coordinates hold)
  3. counterfactual rows, from real (non-counterfactual) episode rows:
       nwait      a screen the human acted on + its history + k = 1 or 2 appended waits noted " [no visible change]"
                                                                            -> the human's action on that screen
       nwaitload  a loading screen (a real `wait` whose next screen changed) + the same appended wait(s) -> `wait`
  4. wait probes from the AndroidControl test split: W0_base (unchanged rows), W1_nwait (W0 + one noted wait, expected:
     not `wait`), W2_loading (real waits whose next screen changed, expected: `wait`)
Usage: python v47_build.py --v46 ~/r8mix/disk --stage ~/r7stage --judge ~/verdicts_final.jsonl --probes ~/r8probes --out ~/r9mix
"""
import argparse
import json
import os
import random
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "train"))
import agent_format as af  # noqa: E402
import screen_change as sc  # noqa: E402
import v46_build as v46  # noqa: E402
from datasets import Dataset, Image as HFImage, Sequence, concatenate_datasets, load_dataset, load_from_disk  # noqa: E402

SEED = 47
N_NWAIT, N_LOAD, P_TWO, MAX_LINES, N_PROBE = 5000, 1500, 0.25, 24, 300
WAIT_ACT = af.action_to_str({"action_type": "wait"})
GATES = ("test_ac_high", "dev_answer", "dev_complete", "dev_androidlens_high", "dev_memgui")
GATE_TAG = {"test_ac_high": "ac_test", "dev_androidlens_high": "androidlens", "dev_memgui": "memgui"}
PROBES = ("T_term", "C2_hist_cut", "C0_base", "C1_hist_done", "C3_stale", "C3n_stale_note")
ST = Counter()


def lines_of(user):
    return v46.HB.search(user).group(2).split("\n")


def set_lines(user, lines):
    m = v46.HB.search(user)
    return user[:m.start(2)] + "\n".join(lines) + user[m.end(2):]


def line_type(line):
    if " -> " not in line:
        return None
    act = line.rsplit(" -> ", 1)[-1]
    if act.endswith(sc.NOTE):
        act = act[: -len(sc.NOTE)]
    try:
        return json.loads(act).get("action_type")
    except Exception:
        return None


def wait_line(j):
    return f"{j}. {v46.WAIT_INTENT} -> {WAIT_ACT}{sc.NOTE}"


def note_waits(user, tag, ep, cmap, key):
    """Note each `wait` history line j whose step (position j-1) left the screen unchanged; other lines untouched."""
    out = []
    for line in lines_of(user):
        mm = v46.LINE.match(line)
        if mm and not line.endswith(sc.NOTE) and line_type(line) == "wait":
            ch = cmap.get((tag, ep, int(mm.group(1)) - 1))
            if ch is False:
                line += sc.NOTE
                ST[f"{key}_wait_notes"] += 1
            elif ch is None:
                ST[f"{key}_wait_lines_unknown_pair"] += 1
            else:
                ST[f"{key}_wait_lines_changed"] += 1
        out.append(line)
    return set_lines(user, out)


def append_waits(user, k):
    lines = lines_of(user)
    p = v46.position(user)
    lines = [l for l in lines if v46.LINE.match(l)] + [wait_line(p + i) for i in range(1, k + 1)]
    return set_lines(user, lines[-MAX_LINES:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v46", required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--judge", required=True)
    ap.add_argument("--probes", required=True, help="dir with the round-8 probe_*.parquet files")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=28)
    ap.add_argument("--limit", type=int, default=0, help="smoke test: first N rows of every input")
    a = ap.parse_args()
    rnd = random.Random(SEED)
    lim = (lambda d: d.select(range(min(a.limit, len(d))))) if a.limit else (lambda d: d)
    train = lim(load_from_disk(os.path.join(a.v46, "train")))
    gates = {k: lim(load_from_disk(os.path.join(a.v46, k))) for k in GATES}
    ac_stage = lim(load_from_disk(os.path.join(a.stage, "ac_train")))
    ST["train_in"] = len(train)

    # ---- 1. change map, real episode rows only (a counterfactual row's screen is not the one at its position)
    real_other = train.filter(lambda s, e: s not in ("androidcontrol", "screenqa") and "#" not in str(e),
                              input_columns=["source", "episode_id"])
    srcs = [("ac_stage", ac_stage, lambda s: "androidcontrol", False),
            ("train", real_other, v46.tag_of, True),
            ("test", gates["test_ac_high"], lambda s: "ac_test", True),
            ("al", gates["dev_androidlens_high"], lambda s: "androidlens", True),
            ("dm", gates["dev_memgui"], lambda s: "memgui", True)]
    cmap = v46.change_map(srcs, a.workers)
    ST["change_pairs"] = len(cmap)

    # ---- 2. wait notes on train
    def train_fn(r):
        if r["source"] == "screenqa":
            return r["messages"]
        return v46.with_user(r["messages"], note_waits(r["messages"][1]["content"], v46.tag_of(r["source"]),
                                                       v46.base_ep(r["episode_id"]), cmap, "train"))
    train = v46.map_messages(train, train_fn, ["messages", "source", "episode_id"])

    # ---- 3. relabel waits that the human followed with an action on the unchanged screen
    verdict = {}
    for l in open(a.judge):
        j = json.loads(l)
        verdict[(j["source"], str(j["episode_id"]), int(j["step_idx"]))] = j["verdict"]
    meta = train.select_columns(["messages", "source", "episode_id", "gt_action", "is_terminal"]).to_list()
    idx = defaultdict(dict)  # (source, episode) -> {position: row}
    for i, r in enumerate(meta):
        if r["source"] != "screenqa" and "#" not in str(r["episode_id"]):
            idx[(r["source"], str(r["episode_id"]))].setdefault(v46.position(r["messages"][1]["content"]), i)
    relabelled = set()
    steps0 = train["step_idx"]
    for (s, e), d in idx.items():
        for p, i in d.items():
            if json.loads(meta[i]["gt_action"])["action_type"] != "wait" or (p + 1) not in d:
                continue
            j = d[p + 1]
            nt = json.loads(meta[j]["gt_action"])["action_type"]
            if cmap.get((v46.tag_of(s), v46.base_ep(e), p)) is False and nt != "wait":
                if nt == "status" and verdict.get((s, e, int(steps0[j]))) != "COMPLETE":
                    ST["wait_kept_next_status_not_judged_complete"] += 1  # e.g. `complete` on a blank screen (review, round 9)
                    continue
                meta[i]["messages"] = v46.with_user(meta[i]["messages"], meta[i]["messages"][1]["content"], dict(meta[j]["messages"][2]))
                meta[i]["gt_action"], meta[i]["is_terminal"] = meta[j]["gt_action"], meta[j]["is_terminal"]
                relabelled.add(i)
                ST[f"wait_relabelled_to_{nt}"] += 1
    train = (train.remove_columns(["messages", "gt_action", "is_terminal"])
             .add_column("messages", [r["messages"] for r in meta], feature=train.features["messages"])
             .add_column("gt_action", [r["gt_action"] for r in meta])
             .add_column("is_terminal", [r["is_terminal"] for r in meta]))
    os.makedirs(a.out, exist_ok=True)
    json.dump([{"source": meta[i]["source"], "episode_id": meta[i]["episode_id"], "step_idx": int(train[i]["step_idx"]),
                "new_label": meta[i]["gt_action"]} for i in sorted(relabelled)], open(os.path.join(a.out, "relabelled_rows.json"), "w"), indent=0)

    # ---- 4. counterfactual rows
    steps = train["step_idx"]
    act_pool, load_pool = [], []
    for (s, e), d in idx.items():
        for p, i in d.items():
            if p < 1 or i in relabelled:
                continue
            t = json.loads(meta[i]["gt_action"])["action_type"]
            last = lines_of(meta[i]["messages"][1]["content"])[-1]
            if t == "wait":
                nx = d.get(p + 1)
                # not before `status` / `answer`: there the screen is mostly the finished one with a toast (review, round 9)
                if cmap.get((v46.tag_of(s), v46.base_ep(e), p)) is True and nx is not None and \
                        json.loads(meta[nx]["gt_action"])["action_type"] not in ("status", "answer"):
                    load_pool.append(i)
            elif line_type(last) != "wait" and (t not in ("status", "answer") or verdict.get((s, e, int(steps[i]))) == "COMPLETE"):
                act_pool.append(i)
    ST["pool_nwait"], ST["pool_nwaitload"] = len(act_pool), len(load_pool)
    picks = [(i, "nwait") for i in rnd.sample(act_pool, min(N_NWAIT, len(act_pool)))] + \
            [(i, "nwaitload") for i in rnd.sample(load_pool, min(N_LOAD, len(load_pool)))]
    raw = train.cast_column("images", Sequence(HFImage(decode=False)))
    cf = []
    for i, kind in picks:
        r = raw[i]
        k = 2 if rnd.random() < P_TWO else 1
        m = r["messages"]
        cf.append({**r, "messages": v46.with_user(m, append_waits(m[1]["content"], k)),
                   "episode_id": f"{r['episode_id']}#cf_{kind}{k}"})
        ST[f"cf_{kind}{k}"] += 1
    cf_ds = Dataset.from_list(cf, features=raw.features).cast(train.features)
    train = concatenate_datasets([train, cf_ds]).shuffle(seed=SEED).flatten_indices()

    # ---- 5. gate splits and round-8 probes: wait notes; new wait probes from the test split
    out_g = {}
    for k, d in gates.items():
        tag = GATE_TAG.get(k, "androidcontrol")
        out_g[k] = v46.map_messages(d, lambda r, tag=tag, k=k: v46.with_user(
            r["messages"], note_waits(r["messages"][1]["content"], tag, v46.base_ep(r["episode_id"]), cmap, k)),
            ["messages", "episode_id"])
    probes = {}
    for p in PROBES:
        d = load_dataset("parquet", data_files=os.path.join(a.probes, f"probe_{p}.parquet"), split="train")
        probes[p] = v46.map_messages(d, lambda r, p=p: v46.with_user(
            r["messages"], note_waits(r["messages"][1]["content"], "ac_test", v46.base_ep(r["episode_id"]), cmap, f"probe_{p}")),
            ["messages", "episode_id"])
    test = out_g["test_ac_high"].cast_column("images", Sequence(HFImage(decode=False)))
    tmeta = test.select_columns(["messages", "episode_id", "gt_action", "is_terminal"]).to_list()
    w0, w2 = [], []
    for i, r in enumerate(tmeta):
        t = json.loads(r["gt_action"])["action_type"]
        p = v46.position(r["messages"][1]["content"])
        if p < 1:
            continue
        if t == "wait" and cmap.get(("ac_test", v46.base_ep(r["episode_id"]), p)) is True:
            w2.append(i)
        elif t not in ("wait", "status", "answer") and not r["is_terminal"] and line_type(lines_of(r["messages"][1]["content"])[-1]) != "wait":
            w0.append(i)
    prnd = random.Random(90)
    w0, w2 = sorted(prnd.sample(w0, min(N_PROBE, len(w0)))), sorted(prnd.sample(w2, min(N_PROBE, len(w2))))

    def probe(rows, tag, k):
        out = []
        for i in rows:
            r = test[i]
            m = r["messages"] if k == 0 else v46.with_user(r["messages"], append_waits(r["messages"][1]["content"], k))
            out.append({**r, "messages": m, "probe": tag, "probe_note": ""})
        return Dataset.from_list(out).cast_column("images", Sequence(HFImage()))
    probes["W0_base"], probes["W1_nwait"], probes["W2_loading"] = probe(w0, "W0_base", 0), probe(w0, "W1_nwait", 1), probe(w2, "W2_loading", 0)

    # ---- 6. checks
    for name, d in [("train", train), *out_g.items(), *((f"probe_{k}", v) for k, v in probes.items())]:
        nh = []
        for r in d.select_columns(["messages", "gt_action", "episode_id"]):
            m = r["messages"]
            assert [x["role"] for x in m] == ["system", "user", "assistant"], name
            a_ = af.parse_action(m[2]["content"], strict=True)
            assert a_ is not None and a_ == json.loads(r["gt_action"]), (name, m[2]["content"], r["gt_action"])
            ls = [l for l in lines_of(m[1]["content"]) if v46.LINE.match(l)]
            nh.append(len(ls))
            nums = [int(v46.LINE.match(l).group(1)) for l in ls]
            if nums and nums != list(range(nums[0], nums[0] + len(nums))):
                ST[f"{name}_history_numbering_gaps"] += 1
            e = str(r["episode_id"])
            if "#cf_nwait" in e:
                assert nums == list(range(nums[0], nums[0] + len(nums))), (name, nums)
                assert ls[-1].endswith(sc.NOTE) and line_type(ls[-1]) == "wait", (name, ls[-1])
                assert (a_["action_type"] == "wait") == ("#cf_nwaitload" in e), (name, e, a_)
        ST[f"{name}_rows"] = len(d)
        ST[f"{name}_history_max"] = max(nh) if nh else 0
    ST["train_actions"] = dict(Counter(json.loads(g)["action_type"] for g in train["gt_action"]))
    for k, d in [("train", train), *out_g.items()]:
        d.save_to_disk(os.path.join(a.out, "disk", k))
    os.makedirs(os.path.join(a.out, "probes"), exist_ok=True)
    for k, d in probes.items():
        d.to_parquet(os.path.join(a.out, "probes", f"probe_{k}.parquet"))
    json.dump(ST, open(os.path.join(a.out, "build_stats.json"), "w"), indent=1)
    print("V47_DONE", json.dumps(ST), flush=True)


if __name__ == "__main__":
    main()
