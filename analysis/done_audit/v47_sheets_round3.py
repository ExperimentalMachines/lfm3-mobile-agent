"""Third review by eye of v4.7's new rows (owner: "do 32 more of each"), from the published build, leaving out every
row already reviewed: build A (f1e466a7: 16 per kind with seed 47, then 32 more with seed 48) and build B (420637e9:
nwaitload 16 with seed 47; its nwait rows are build A's). Replays v47_sheets.py's sampling to get those rows, then draws new ones with seed 49.
Each item: the row's screen (red dot at a click) | the episode's real next screen.
Usage: python v47_sheets_round3.py <build A train> <A relabelled.json> <build B train> <B relabelled.json> <out dir> [--n 32]
"""
import argparse
import io
import json
import os
import random
import re
import textwrap

from datasets import Image as HFImage, Sequence, load_from_disk
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("train_a")
ap.add_argument("rel_a")
ap.add_argument("train_b")
ap.add_argument("rel_b")
ap.add_argument("out")
ap.add_argument("--n", type=int, default=32)
a = ap.parse_args()
HB = re.compile(r"\nPrevious steps:\n(.*?)\nWhat is the next action\?$", re.S)
LINE = re.compile(r"^(\d+)\. ")
KINDS = ("nwait", "nwaitload")


def pos(u):
    nums = [int(m.group(1)) for m in map(LINE.match, HB.search(u).group(1).split("\n")) if m]
    return nums[-1] if nums else 0


def load(path):
    ds = load_from_disk(path)
    return ds, ds.select_columns(["messages", "source", "episode_id", "step_idx", "gt_action"]).to_list()


def pools(meta):
    return {k: [i for i, r in enumerate(meta) if f"#cf_{k}" in str(r["episode_id"]) and (k == "nwaitload" or "#cf_nwaitload" not in str(r["episode_id"]))] for k in KINDS}


def cf_key(meta, i, kind):
    r = meta[i]
    return (kind, r["source"], str(r["episode_id"]).split("#cf_")[0], int(r["step_idx"]))


def rel_key(x):
    return ("relabel", x["source"], str(x["episode_id"]), int(x["step_idx"]))


seen = set()
# build A: 16 (seed 47) then 32 more (seed 48) per kind
_, meta_a = load(a.train_a)
rel_a, pool_a = json.load(open(a.rel_a)), pools(meta_a)
r47, r48 = random.Random(47), random.Random(48)
old = r47.sample(rel_a, min(16, len(rel_a)))
more = r48.sample([x for x in rel_a if x not in old], min(32, len(rel_a) - len(old)))
seen |= {rel_key(x) for x in old + more}
for k in KINDS:
    o = r47.sample(pool_a[k], 16)
    m = r48.sample([i for i in pool_a[k] if i not in set(o)], 32)
    seen |= {cf_key(meta_a, i, k) for i in o + m}
del meta_a
# build B: 16 per kind (seed 47)
ds, meta = load(a.train_b)
rel_b, pool_b = json.load(open(a.rel_b)), pools(meta)
r47 = random.Random(47)
r47.sample(rel_b, min(16, len(rel_b)))  # rendered for build B but not viewed: not excluded
for k in KINDS:
    o = r47.sample(pool_b[k], 16)
    if k == "nwaitload":  # only build B's nwaitload sheets were viewed (its nwait rows are build A's)
        seen |= {cf_key(meta, i, k) for i in o}
print("already reviewed:", len(seen))

raw = ds.cast_column("images", Sequence(HFImage(decode=False))).select_columns(["images"])
font = ImageFont.load_default()
os.makedirs(a.out, exist_ok=True)
rows = {}
for i, r in enumerate(meta):
    if "#" not in str(r["episode_id"]):
        rows.setdefault((r["source"], str(r["episode_id"]), pos(r["messages"][1]["content"])), i)


def shot(i, act=None):
    im = Image.open(io.BytesIO(raw[i]["images"][0]["bytes"])).convert("RGB").resize((200, 445))
    if act and "point_2d" in act:
        x, y = act["point_2d"][0] * 200 // 1000, act["point_2d"][1] * 445 // 1000
        ImageDraw.Draw(im).ellipse((x - 6, y - 6, x + 6, y + 6), outline="red", width=3)
    return im


def sheet(items, name):
    for s in range(0, len(items), 8):
        sh = Image.new("RGB", (4 * 420, 2 * 640), "white")
        dr = ImageDraw.Draw(sh)
        for k, (ims, text) in enumerate(items[s:s + 8]):
            X, Y = (k % 4) * 420, (k // 4) * 640
            for j, im in enumerate(ims):
                sh.paste(im, (X + j * 205, Y + 190))
            yy = Y + 2
            for line in text.split("\n"):
                for w in textwrap.wrap(line, 68)[:3]:
                    dr.text((X, yy), w, fill="black", font=font)
                    yy += 12
        sh.save(os.path.join(a.out, f"{name}_{s // 8}.jpg"), quality=85)


r49 = random.Random(49)
picked = {}
rest = [x for x in rel_b if rel_key(x) not in seen]
pick = r49.sample(rest, min(a.n, len(rest)))
items = []
for x in pick:
    i = next(j for (s, e, p), j in rows.items() if s == x["source"] and e == str(x["episode_id"]) and int(meta[j]["step_idx"]) == x["step_idx"])
    p = pos(meta[i]["messages"][1]["content"])
    nxt = rows.get((x["source"], str(x["episode_id"]), p + 1))
    act = json.loads(meta[i]["gt_action"])
    goal = meta[i]["messages"][1]["content"].split("\n", 1)[0][6:]
    items.append(([shot(i, act)] + ([shot(nxt)] if nxt is not None else []),
                  f"#{len(items)} {x['source']} {x['episode_id']} pos {p}\nGOAL: {goal}\nNEW LABEL: {meta[i]['messages'][2]['reasoning_content']} -> {meta[i]['gt_action']}\nleft: wait screen | right: next screen"))
picked["relabel"] = [list(rel_key(x)) for x in pick]
sheet(items, "r3_relabel")
for kind in KINDS:
    rest = [i for i in pool_b[kind] if cf_key(meta, i, kind) not in seen]
    pick = r49.sample(rest, min(a.n, len(rest)))
    items = []
    for i in pick:
        u = meta[i]["messages"][1]["content"]
        e0, k = str(meta[i]["episode_id"]).split("#cf_")
        nxt = rows.get((meta[i]["source"], e0, pos(u) - int(k[-1]) + 1))
        hist = "\n".join(HB.search(u).group(1).split("\n")[-3:])
        act = json.loads(meta[i]["gt_action"])
        items.append(([shot(i, act)] + ([shot(nxt)] if nxt is not None else []),
                      f"#{len(items)} {meta[i]['source']} {meta[i]['episode_id']}\nGOAL: {u.split(chr(10), 1)[0][6:]}\n{hist}\nLABEL: {meta[i]['messages'][2]['reasoning_content']} -> {meta[i]['gt_action']}\nleft: row screen | right: the episode's real next screen"))
    picked[kind] = [list(cf_key(meta, i, kind)) for i in pick]
    sheet(items, f"r3_{kind}")
json.dump({"seen_before": len(seen), "picked": picked}, open(os.path.join(a.out, "r3_picked.json"), "w"), indent=0)
print({k: len(v) for k, v in picked.items()}, "sheets in", a.out)
