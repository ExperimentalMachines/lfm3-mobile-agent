"""History-reliance probes for the "done but not done yet" audit (round 8). From the AndroidControl test split in D's
format (MobileAgent-SFT-v4.5 test_ac_high: 24-step history + notes), build rows that change ONE thing:

  C0  base        rows >= 2 steps before the episode's terminal row, unchanged                (expected: no status)
  C1  hist_done   C0's screenshot, but the history block of the episode's terminal row (all steps "done")
  C2  hist_cut    terminal rows (finished screen), history with its last 2 steps removed     (screen says done)
  C3  stale       terminal rows' full history, but the screenshot BEFORE the last action (the last action "did not
                  take effect", as in the AndroidWorld false completes)                       (expected: not status)
  T   term        terminal rows, unchanged                                                     (expected: status)

A model that judges completion from the screen says `status` on T and C2 and not on C0, C1, C3. A model that copies
completion from the history says `status` on C1 and C3 and less on C2.
Usage: python build_history_probes.py <test parquet files...> --out <dir> [--n 300]
"""
import argparse
import json
import os
import random
import re

import pyarrow as pa
import pyarrow.parquet as pq

ap = argparse.ArgumentParser()
ap.add_argument("files", nargs="+")
ap.add_argument("--out", required=True)
ap.add_argument("--n", type=int, default=300)
a = ap.parse_args()
HB = re.compile(r"(\nPrevious steps:\n)(.*?)(\nWhat is the next action\?)$", re.S)
rows = []
for f in a.files:
    rows += pq.read_table(f).to_pylist()
by_ep = {}
for r in rows:
    by_ep.setdefault(str(r["episode_id"]), {})[int(r["step_idx"])] = r
term = {e: max(s for s, r in d.items() if r["is_terminal"]) for e, d in by_ep.items() if any(r["is_terminal"] for r in d.values())}
rnd = random.Random(80)


def with_hist(r, block, img=None, tag="", note=""):
    u = r["messages"][1]["content"]
    m = HB.search(u)
    new = dict(r)
    new["messages"] = [dict(r["messages"][0]), {**r["messages"][1], "content": u[:m.start(2)] + block + u[m.end(2):]}] + [dict(x) for x in r["messages"][2:]]
    if img is not None:
        new["images"] = img
    new["probe"] = tag
    new["probe_note"] = note
    return new


def hist(r):
    return HB.search(r["messages"][1]["content"]).group(2)


out = {"C0_base": [], "C1_hist_done": [], "C2_hist_cut": [], "C3_stale": [], "T_term": []}
eps = sorted(term)
rnd.shuffle(eps)
for e in eps:
    T = term[e]
    d = by_ep[e]
    tr = d[T]
    th = hist(tr).split("\n")
    if T < 3 or (T - 1) not in d or len([l for l in th if re.match(r"^\d+\. ", l)]) != T:
        continue  # need >= 3 steps and a history block that lists every step (24-step window covers it)
    last_type = json.loads(d[T - 1]["gt_action"])["action_type"]
    if len(out["T_term"]) < a.n:
        out["T_term"].append(dict(tr, probe="T_term", probe_note=""))
    if len(out["C2_hist_cut"]) < a.n:
        out["C2_hist_cut"].append(with_hist(tr, "\n".join(th[:-2]), tag="C2_hist_cut"))
    # C3 only where the last real action changes the screen (not a trailing scroll / wait no-op)
    if last_type not in ("scroll", "wait") and len(out["C3_stale"]) < a.n:
        out["C3_stale"].append(with_hist(tr, "\n".join(th), img=d[T - 1]["images"], tag="C3_stale", note=last_type))
    cand = [s for s in d if not d[s]["is_terminal"] and T - s >= 2]
    if cand and len(out["C0_base"]) < a.n:
        s = rnd.choice(cand)
        out["C0_base"].append(dict(d[s], probe="C0_base", probe_note=str(T - s)))
        out["C1_hist_done"].append(with_hist(d[s], "\n".join(th), tag="C1_hist_done", note=str(T - s)))
os.makedirs(a.out, exist_ok=True)
for k, v in out.items():
    pq.write_table(pa.Table.from_pylist(v), os.path.join(a.out, f"{k}.parquet"))
    print(k, len(v))
