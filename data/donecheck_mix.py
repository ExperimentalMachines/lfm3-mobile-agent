#!/usr/bin/env python3
"""Round 12 (docs/preregistrations/round-12-done-check.md): candidate E-V's fixed continuation mix and its four probes. Runs inside the SageMaker
job before training (CPU). Seed 12. Round 11's mix (data/endings_mix.py) plus two new kinds of rows:

  * written actions (fix 2): GUI-Odyssey final screens the judge found unfinished -> the next action Claude wrote
    (results/r12_dev/claude_next_actions.jsonl, status ok; analysis/done_audit/claude_next_action.py)
  * done-check rows (fix 1): the usual user text with `What is the next action?` replaced by CHECK_Q; reply
    `<think>reason</think>yes|no`:
      - judged-done GUI-Odyssey endings (training part) -> yes, the judge's reason
      - judged-unfinished endings with a written action -> no, the judge's reason
      - judged-done episodes, the screen one action before the end when that action is a tap / long press / typing /
        Enter / app open -> no, "The last step is still to do: <intent>."
      - AndroidControl `complete` rows the judge checked (round 10, 1,003) -> yes / no, the judge's reason
  * the 113 AndroidControl `complete` rows the judge found unfinished (and their #cf copies) leave the replay pool

Probes (never trained): M_done = round 11's 200 (results/r11_dev/mix_stats.json), M_notdone = the 200 of
results/r12_dev/notdone_split.json; V_done / V_notdone = the same screens with CHECK_Q.
Out: OUT/mix, OUT/probe_{M_done,M_notdone,V_done,V_notdone} (save_to_disk), OUT/mix_stats.json
Usage: python donecheck_mix.py --term ody_term2.parquet --verdicts claude_ody_terminal_verdicts.jsonl --written W.jsonl
         --split notdone_split.json --r11stats r11_mix_stats.json --acv claude_ac_complete_verdicts.jsonl --out OUT
         [--n_mix 32000] [--limit 0] [--shards 0]
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
SEED, HIST = 12, 24
NEXT_Q, CHECK_Q = af.NEXT_Q, af.DONE_CHECK_Q  # the harness asks the same question (eval/androidworld/lfm_agent.py)
DONE_ACT = {"action_type": "status", "goal_status": "complete"}
DONE = {"role": "assistant", "content": af.action_to_str(DONE_ACT), "reasoning_content": "The goal has been completed."}
PRE_END_TYPES = {"click", "long_press", "input_text", "keyboard_enter", "open_app"}
ST = Counter()
DIFFS = []
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


def as_check(user):
    assert user.endswith(NEXT_Q), user[-80:]
    return user[: -len(NEXT_Q)] + CHECK_Q


def check_row(r, answer, reason, eid):
    m = r["messages"]
    reason = " ".join((reason or "").split())[:300] or ("The goal is accomplished." if answer == "yes" else "The goal is not accomplished yet.")
    return dict(r, messages=with_user(m, as_check(m[1]["content"]), {"role": "assistant", "content": answer,
                                                                     "reasoning_content": reason}),
                episode_id=eid, gt_action=json.dumps({"action_type": "done_check", "answer": answer}), is_terminal=False)


def judged(path):
    out = {}
    for l in open(path):
        j = json.loads(l)
        out[j["case"]] = (j["verdict"], "\n".join(j["text"].strip().splitlines()[1:]).strip())
    return out


def main():
    ap = argparse.ArgumentParser()
    for k in ("term", "verdicts", "written", "split", "r11stats", "acv", "out"):
        ap.add_argument(f"--{k}", required=True)
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

    # ---- E's GUI-Odyssey rows by episode and position; AndroidControl `complete` rows by (episode, step)
    src, eps, msgs, gta, stp = train["source"], train["episode_id"], train["messages"], train["gt_action"], train["step_idx"]
    ody = defaultdict(dict)
    ac_done, ac_variants = {}, defaultdict(list)
    for i, (s, e, m, g, k) in enumerate(zip(src, eps, msgs, gta, stp)):
        e = str(e)
        if s == "odyssey" and "#" not in e:
            ody[e][position(m[1]["content"])] = i
        if s == "androidcontrol" and json.loads(g).get("goal_status") == "complete":
            if "#" in e:
                ac_variants[(e.split("#", 1)[0], int(k))].append(i)
            else:
                ac_done[(e, int(k))] = i
    raw = train.cast_column("images", Sequence(HFImage(decode=False)))

    # ---- terminal rows, rebuilt from E's own last row of each episode (= endings_mix.py)
    verd = judged(a.verdicts)
    term = pq.read_table(a.term).to_pylist()
    rows = {"COMPLETE": [], "NOT_COMPLETE": []}
    for t in term:
        e, K = str(t["episode_id"]), int(t["step_idx"])
        v = verd[f"ody_{e}_{K}"][0]
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
                        "gt_action": json.dumps(DONE_ACT), "is_terminal": True, "_last": d, "_case": f"ody_{e}_{K}"})
    ST["judged_complete"], ST["judged_not_complete"] = len(rows["COMPLETE"]), len(rows["NOT_COMPLETE"])
    if not a.shards and (DIFFS or ST["skip_episode_not_in_train"]):
        json.dump(DIFFS[:20], open(os.path.join(a.out + "_diffs.json"), "w"), indent=1)
        raise SystemExit(f"R12_MIX_FAILED: {len(DIFFS)} rebuilt rows differ from the judged text, "
                         f"{ST['skip_episode_not_in_train']} episodes missing ({a.out}_diffs.json)")

    # ---- probes: round 11's M_done, the fixed M_notdone split (smoke: whatever of them was loaded, else a sample)
    r11_done = set(json.load(open(a.r11stats))["probe_M_done"])
    nd_split = json.load(open(a.split))
    nd_probe = set(nd_split["probe_M_notdone"])
    done, notdone = rows["COMPLETE"], rows["NOT_COMPLETE"]
    probe_done = [r for r in done if f"{r['episode_id']}_{r['step_idx']}" in r11_done]
    probe_nd = [r for r in notdone if r["_case"] in nd_probe]
    if a.limit:  # smoke: limited rows rarely include the fixed probes
        if len(probe_done) < 4:
            probe_done = rnd.sample(done, min(10, len(done) // 4))
        if len(probe_nd) < 4:
            probe_nd = rnd.sample(notdone, min(10, len(notdone) // 4))
    elif len(probe_done) != 200 or len(probe_nd) != 200:
        raise SystemExit(f"R12_MIX_FAILED: probes {len(probe_done)} / {len(probe_nd)} (expected 200 / 200)")
    pd_ids, pn_ids = {id(r) for r in probe_done}, {id(r) for r in probe_nd}
    term_train = [r for r in done if id(r) not in pd_ids]
    nd_train = [r for r in notdone if id(r) not in pn_ids]
    ST["probe_M_done"], ST["probe_M_notdone"], ST["terminal_train"] = len(probe_done), len(probe_nd), len(term_train)

    # ---- fix 2: written next actions for the trainable unfinished endings
    written = {}
    for l in open(a.written):
        j = json.loads(l)
        written[j["case"]] = j
    wr, ndcheck = [], []
    for r in nd_train:
        w = written.get(r["_case"])
        if w is None:
            ST["written_missing"] += 1
            continue
        if w["status"] != "ok":
            ST[f"written_dropped_{w['status']}"] += 1
            continue
        act = af.parse_action(af.action_to_str(w["action"]), strict=True)
        assert act is not None, w
        m = r["messages"]
        wr.append(dict(r, messages=with_user(m, m[1]["content"], {"role": "assistant", "content": af.action_to_str(act),
                                                                   "reasoning_content": w["intent"]}),
                       gt_action=json.dumps(act), episode_id=f"{r['episode_id']}#written", is_terminal=False))
        ndcheck.append(check_row(r, "no", verd[r["_case"]][1], f"{r['episode_id']}#check_no_end"))
    ST["written_rows"] = len(wr)

    # ---- round 11's counterfactual rows and E's real rows before the end (= endings_mix.py) + pre-end "no" checks
    cf, must, pre_no = [], [], []
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
        # the screen one action before the end, as E's real row (its own history): not done yet
        lact = json.loads(last["gt_action"])
        if lact.get("action_type") in PRE_END_TYPES:
            intent = (last["messages"][2].get("reasoning_content") or "").strip().rstrip(".")
            reason = f"The last step is still to do: {intent[:1].lower() + intent[1:]}." if intent else None
            pre_no.append(check_row(last, "no", reason, f"{e}#check_no_pre"))
    must = sorted(set(must))
    ST["e_real_rows_before_end"] = len(must)
    yes_end = [check_row(r, "yes", verd[r["_case"]][1], f"{r['episode_id']}#check_yes_end") for r in term_train]

    # ---- AndroidControl `complete` rows the judge checked
    acv = judged(a.acv)
    ac_checks, ac_drop = [], set()
    for case, (v, reason) in acv.items():
        _, e, k = case.split("_")
        i = ac_done.get((e, int(k)))
        if i is None:
            ST["ac_judged_not_in_split"] += 1
            continue
        ans = "yes" if v == "COMPLETE" else "no"
        ac_checks.append(check_row(raw[i], ans, reason, f"{e}#check_{ans}_ac"))
        if v == "NOT_COMPLETE":
            ac_drop.add(i)
            ac_drop.update(ac_variants.get((e, int(k)), []))
    ST["ac_check_rows"], ST["ac_removed_from_replay"] = len(ac_checks), len(ac_drop)
    checks = yes_end + ndcheck + pre_no + ac_checks
    ST["check_yes_end"], ST["check_no_end"], ST["check_no_pre"] = len(yes_end), len(ndcheck), len(pre_no)
    ST["check_yes"] = sum(json.loads(r["gt_action"])["answer"] == "yes" for r in checks)
    ST["check_no"] = len(checks) - ST["check_yes"]

    cols = raw.features

    def to_ds(rs):
        clean = [{k: r.get(k) for k in cols} | {"mode": r.get("mode") or "high", "gt_bbox": r.get("gt_bbox") or ""} for r in rs]
        return Dataset.from_list(clean, features=cols).cast(train.features)
    new = to_ds(term_train + cf + wr + checks)
    must = [i for i in must if i not in ac_drop]
    n_rest = a.n_mix - len(new) - len(must)
    assert n_rest > 0, (a.n_mix, len(new), len(must))
    taken = set(must) | ac_drop
    rest = rnd.sample([i for i in range(len(train)) if i not in taken], n_rest)
    ST["replay_uniform"] = n_rest
    mix = concatenate_datasets([new, train.select(must + rest)]).shuffle(seed=SEED).flatten_indices()

    # ---- checks
    nst = Counter()
    for r in new.select_columns(["messages", "gt_action"]):
        m = r["messages"]
        assert [x["role"] for x in m] == ["system", "user", "assistant"]
        g = json.loads(r["gt_action"])
        if g["action_type"] == "done_check":
            assert m[1]["content"].endswith(CHECK_Q) and m[2]["content"] == g["answer"] and m[2]["reasoning_content"]
            nst["check_" + g["answer"]] += 1
            continue
        act = af.parse_action(m[2]["content"], strict=True)
        assert act is not None and act == g, (m[2]["content"], r["gt_action"])
        assert m[1]["content"].endswith(NEXT_Q)
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
    to_ds(probe_nd).save_to_disk(os.path.join(a.out, "probe_M_notdone"))
    to_ds([check_row(r, "yes", "", r["episode_id"]) for r in probe_done]).save_to_disk(os.path.join(a.out, "probe_V_done"))
    to_ds([check_row(r, "no", "", r["episode_id"]) for r in probe_nd]).save_to_disk(os.path.join(a.out, "probe_V_notdone"))
    json.dump({"stats": ST, "probe_M_done": [f"{r['episode_id']}_{r['step_idx']}" for r in probe_done],
               "probe_M_notdone": [r["_case"] for r in probe_nd]},
              open(os.path.join(a.out, "mix_stats.json"), "w"), indent=1)
    print("R12_MIX_DONE", json.dumps(ST), flush=True)


if __name__ == "__main__":
    main()
