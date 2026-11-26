#!/usr/bin/env python3
"""Round 10 / E-DPO (docs/preregistrations/round-10-multi-part-false-completes.md, 2026-11-25 14:20): candidate rows on which E decodes, from E's own training
split (MobileAgent-SFT-Counterfactual @ 0ace5559, save_to_disk copy), deterministic (seed 49):
  late      real rows, human action not wait/status/answer, among the last 3 action rows of their episode   (8,400)
  other     the same kind of rows elsewhere in the episode                                              (3,600)
  ahead     counterfactual rows "#cf_ahead": a screen 2-3 steps before the end, history claims every step (4,000)
  terminal  real AndroidControl `status complete` rows the stage-1 judge called COMPLETE                (4,000)
Rows whose goal names an AndroidWorld app are skipped (data/dpo_allmistakes_pairs.py's list).
Usage: python stopdpo_candidates.py --train ~/r8mix/disk/train --verdicts ~/verdicts_final.jsonl --out ~/r10/cand
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
import sft_counterfactual as v46  # noqa: E402
from datasets import load_from_disk  # noqa: E402

AW_APP_RE = re.compile("|".join([r"simple ?calendar", r"\bmarkor\b", r"pro ?expense", r"\bbroccoli\b", r"\bjoplin\b",
                                 r"\bosm ?and\b", r"retro ?music", r"\bvlc\b", r"simple ?sms", r"audio ?recorder",
                                 r"simple ?draw", r"open ?tracks", r"simple ?gallery", r"tasks\.org", r"calendar ?pro",
                                 r"(voice|sound) ?recorder"]), re.I)
N = {"late": 8400, "other": 3600, "ahead": 4000, "terminal": 4000}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rnd = random.Random(49)
    ds = load_from_disk(a.train)
    meta = ds.select_columns(["messages", "source", "episode_id", "step_idx", "gt_action"]).to_list()
    verdict = {}
    for l in open(a.verdicts):
        j = json.loads(l)
        verdict[(j["source"], str(j["episode_id"]), int(j["step_idx"]))] = j["verdict"]
    last = defaultdict(int)  # (source, episode) -> position of its last real action row
    for r in meta:
        e = str(r["episode_id"])
        if "#" in e or r["source"] == "screenqa":
            continue
        if json.loads(r["gt_action"])["action_type"] not in ("status", "answer"):
            last[(r["source"], e)] = max(last[(r["source"], e)], v46.position(r["messages"][1]["content"]))
    pools = defaultdict(list)
    st = Counter()
    for i, r in enumerate(meta):
        e = str(r["episode_id"])
        if r["source"] == "screenqa":
            continue
        if AW_APP_RE.search(r["messages"][1]["content"].split("Previous steps:")[0]):
            st["skip_aw_app"] += 1
            continue
        t = json.loads(r["gt_action"])["action_type"]
        if "#cf_ahead" in e:
            pools["ahead"].append(i)
        elif "#" in e:
            continue
        elif t == "status":
            if r["source"] == "androidcontrol" and verdict.get((r["source"], e, int(r["step_idx"]))) == "COMPLETE":
                pools["terminal"].append(i)
        elif t not in ("wait", "answer"):
            p = v46.position(r["messages"][1]["content"])
            pools["late" if p >= last[(r["source"], e)] - 2 else "other"].append(i)
    pick = []
    for k, n in N.items():
        s = sorted(rnd.sample(pools[k], min(n, len(pools[k]))))
        pick += [(i, k) for i in s]
        st[f"pool_{k}"], st[f"picked_{k}"] = len(pools[k]), len(s)
    sub = ds.select([i for i, _ in pick])
    sub = sub.add_column("cand_kind", [k for _, k in pick])
    sub.save_to_disk(os.path.join(a.out, "disk"))
    st["by_source"] = dict(Counter(meta[i]["source"] for i, _ in pick))
    json.dump(st, open(os.path.join(a.out, "stats.json"), "w"), indent=1)
    print("R10_CAND_DONE", json.dumps(st), flush=True)


if __name__ == "__main__":
    main()
