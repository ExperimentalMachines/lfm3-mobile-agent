"""Round 9 wait audit, part 2: what follows each `wait` step of the training split, and how often `wait` follows each
action type. Splits the wait groups of wait_audit.py by the next action, so each group maps to one fix:
  same_then_act     next screen unchanged, next action a real action   -> the wait was not needed (relabel to that action)
  same_then_wait    next screen unchanged, next action `wait` again    -> static loading screen (keep)
  same_then_done    next screen unchanged, next action `status`/`answer` -> waited on a finished screen (relabel to it)
  changed_then_*    next screen changed (loading finished, toast gone)  -> keep
  no_next           next screen not in the data
Usage: python wait_detail.py <datasets save_to_disk dir> <out.json>
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "train"))
import screen_change as sc  # noqa: E402
from datasets import Image as HFImage, Sequence, load_from_disk  # noqa: E402

HB = re.compile(r"\nPrevious steps:\n(.*?)\nWhat is the next action\?$", re.S)
LINE = re.compile(r"^(\d+)\. ")
ds = load_from_disk(sys.argv[1])
meta = ds.select_columns(["messages", "source", "episode_id", "gt_action"]).to_list()
eps = defaultdict(dict)  # (source, episode) -> {position: (row, action_type)}
for i, r in enumerate(meta):
    e = str(r["episode_id"])
    if "#" in e or r["source"] == "screenqa":
        continue
    nums = [int(m.group(1)) for m in map(LINE.match, HB.search(r["messages"][1]["content"]).group(1).split("\n")) if m]
    eps[(r["source"], e)].setdefault(nums[-1] if nums else 0, (i, json.loads(r["gt_action"])["action_type"]))
raw = ds.cast_column("images", Sequence(HFImage(decode=False))).select_columns(["images"])
cache = {}


def img(i):
    if i not in cache:
        cache[i] = sc.prep(raw[i]["images"][0]["bytes"])
    return cache[i]


after = defaultdict(Counter)  # source -> Counter((prev type, this type == wait))
cnt = Counter()
samples = defaultdict(list)
for (src, e), d in eps.items():
    for p, (i, typ) in d.items():
        prev = d.get(p - 1)
        if prev:
            after[src][(prev[1], typ == "wait")] += 1
        if typ != "wait":
            continue
        nxt = d.get(p + 1)
        if not nxt:
            g = "no_next"
        else:
            same = not sc.changed(img(i), img(nxt[0]))
            kind = "wait" if nxt[1] == "wait" else "done" if nxt[1] in ("status", "answer") else "act"
            g = f"{'same' if same else 'changed'}_then_{kind}"
        cnt[(src, g)] += 1
        if len(samples[g]) < 300:
            samples[g].append({"source": src, "episode_id": e, "position": p})
rate = {}
for src, c in after.items():
    for t in sorted({k[0] for k in c}):
        n = c[(t, True)] + c[(t, False)]
        rate[f"{src}:{t}"] = {"n": n, "wait_next": c[(t, True)], "pct": round(100 * c[(t, True)] / n, 2)}
out = {"counts": {f"{s}:{g}": n for (s, g), n in sorted(cnt.items())}, "wait_after_prev": rate, "samples": samples}
print(json.dumps({"counts": out["counts"], "wait_after_prev": rate}, indent=0))
json.dump(out, open(sys.argv[2], "w"), indent=0)
